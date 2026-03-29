"""
Router de chatbot — POST /api/chat

Flujo de datos:
1. Intenta usar data_store (DataFrame en memoria, cargado al hacer upload).
2. Si el store está vacío, intenta leer master.xlsx desde disco como fallback.
3. Si tampoco hay disco → responde "Primero sube el Excel".

Las preguntas simples de conteo (total, críticas, resumen, proveedores)
se responden directamente sin pasar por IA, para garantizar exactitud.
"""
import re
import logging
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
log    = logging.getLogger(__name__)


# ── Modelos ───────────────────────────────────────────────────────────────────

class ChatAction(BaseModel):
    label:        str
    filter_key:   str
    filter_value: str


class ChatRequest(BaseModel):
    question: str
    ctx:      str = ""


class ChatResponse(BaseModel):
    answer:  str
    actions: list[ChatAction] = []


# ── Helpers de texto ──────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    t = str(text).lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        t = t.replace(a, b)
    return t


def _parse_ctx(ctx: str) -> dict:
    result = {}
    for part in ctx.split("|"):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            result[k.strip().lower()] = v.strip()
    return result


# ── Respuestas directas (sin IA) ──────────────────────────────────────────────
# Preguntas simples de conteo se responden usando el DataFrame directamente.
# Esto garantiza que los números sean siempre exactos y sin latencia de IA.

def _try_direct_answer(question: str, df: pd.DataFrame, summary: dict) -> str | None:
    """
    Retorna una respuesta directa si la pregunta es de conteo simple.
    Retorna None si la pregunta necesita procesamiento más complejo.
    """
    q = _normalize(question)

    col_dias = next((c for c in df.columns if "retraso" in c.lower()), None)
    col_prov = next((c for c in df.columns if "proveedor" in c.lower()), None)

    dias_num = (
        pd.to_numeric(df[col_dias], errors="coerce").fillna(0)
        if col_dias else pd.Series(0, index=df.index)
    )

    total    = len(df)
    criticas = int((dias_num > 15).sum())
    en_riesgo = int(((dias_num > 0) & (dias_num <= 15)).sum())
    en_plazo  = int((dias_num <= 0).sum())

    # ── "cuántas órdenes" / "total" / "cuántas hay" ──────────────────────────
    if any(kw in q for kw in ["cuantas ordenes", "cuantas hay", "total de ordenes",
                               "total ordenes", "cuantas oc", "numero de ordenes"]):
        return f"Hay **{total}** órdenes de compra en total."

    # ── "cuántas críticas" ────────────────────────────────────────────────────
    if any(kw in q for kw in ["cuantas criticas", "cuantas son criticas",
                               "ordenes criticas", "total criticas"]):
        pct = round(criticas / total * 100) if total else 0
        return (
            f"Hay **{criticas}** órdenes críticas (más de 15 días de retraso), "
            f"que representan el **{pct}%** del total."
        )

    # ── "cuántas en riesgo" / "retrasadas" ───────────────────────────────────
    if any(kw in q for kw in ["cuantas en riesgo", "cuantas retrasadas",
                               "cuantas con retraso", "en riesgo"]):
        return (
            f"Hay **{en_riesgo}** órdenes en riesgo (1 a 15 días de retraso) "
            f"y **{criticas}** críticas (más de 15 días)."
        )

    # ── "cuántas en plazo" ────────────────────────────────────────────────────
    if any(kw in q for kw in ["cuantas en plazo", "en plazo", "a tiempo"]):
        return f"Hay **{en_plazo}** órdenes en plazo de las {total} totales."

    # ── "resumen" / "summary" ─────────────────────────────────────────────────
    if any(kw in q for kw in ["resumen", "summary", "estado general",
                               "como estamos", "panorama"]):
        pct_crit = round(criticas / total * 100) if total else 0
        provs = len(df[col_prov].dropna().unique()) if col_prov else summary.get("suppliers", 0)
        return (
            f"**Resumen general:**\n"
            f"- Total OCs: **{total}**\n"
            f"- Críticas (+15d): **{criticas}** ({pct_crit}%)\n"
            f"- En riesgo (1–15d): **{en_riesgo}**\n"
            f"- En plazo: **{en_plazo}**\n"
            f"- Proveedores activos: **{provs}**"
        )

    # ── "proveedores" ─────────────────────────────────────────────────────────
    if any(kw in q for kw in ["proveedores", "lista de proveedores",
                               "que proveedores", "cuantos proveedores"]):
        if col_prov:
            provs = sorted(df[col_prov].dropna().unique().tolist())
            if "cuantos" in q or "cantidad" in q:
                return f"Hay **{len(provs)}** proveedores activos."
            preview = provs[:10]
            resto   = len(provs) - 10
            lines   = [f"**{len(provs)} proveedores activos:**"]
            lines  += [f"  • {p}" for p in preview]
            if resto > 0:
                lines.append(f"  … y {resto} más.")
            return "\n".join(lines)

    return None  # pregunta compleja → pasar al pipeline de IA / fallback


# ── Filtrado de DataFrame ─────────────────────────────────────────────────────

def _parse_and_filter(question: str, df: pd.DataFrame, ctx: dict) -> tuple[list[dict], str, dict]:
    q        = _normalize(question)
    desc     = "todas las órdenes"
    new_ctx  = dict(ctx)

    col_dias = next((c for c in df.columns if "retraso" in c.lower()), None)
    col_prov = next((c for c in df.columns if "proveedor" in c.lower()), None)
    col_oc   = next((c for c in df.columns if "oc/pos" in c.lower()), None)
    col_prio = next((c for c in df.columns if "prioridad" in c.lower()), None)

    filtered = df.copy()

    # Filtro por riesgo
    if any(kw in q for kw in ["critic", "critico", "criticas", "criticos"]):
        if col_dias:
            dias_num  = pd.to_numeric(filtered[col_dias], errors="coerce").fillna(0)
            prio_crit = filtered[col_prio].astype(str).str.upper().str.contains("CRIT", na=False) if col_prio else pd.Series(False, index=filtered.index)
            filtered  = filtered[(dias_num > 15) | prio_crit]
        desc = "órdenes críticas"
        new_ctx["risk"] = "Crítico"

    elif any(kw in q for kw in ["retrasad", "retraso", "atrasad"]):
        if col_dias:
            filtered = filtered[pd.to_numeric(filtered[col_dias], errors="coerce").fillna(0) > 0]
        desc = "órdenes retrasadas"
        new_ctx["risk"] = "En riesgo"

    elif any(kw in q for kw in ["riesgo", "en riesgo"]):
        if col_dias:
            dias_num = pd.to_numeric(filtered[col_dias], errors="coerce").fillna(0)
            filtered = filtered[(dias_num > 0) & (dias_num <= 15)]
        desc = "órdenes en riesgo"
        new_ctx["risk"] = "En riesgo"

    elif any(kw in q for kw in ["plazo", "en plazo", "a tiempo"]):
        if col_dias:
            filtered = filtered[pd.to_numeric(filtered[col_dias], errors="coerce").fillna(0) <= 0]
        desc = "órdenes en plazo"
        new_ctx.pop("risk", None)

    elif ctx.get("risk"):
        risk = ctx["risk"]
        if risk == "Crítico" and col_dias:
            filtered = filtered[pd.to_numeric(filtered[col_dias], errors="coerce").fillna(0) > 15]
        elif risk == "En riesgo" and col_dias:
            dias_num = pd.to_numeric(filtered[col_dias], errors="coerce").fillna(0)
            filtered = filtered[(dias_num > 0) & (dias_num <= 15)]
        desc = f"órdenes {risk.lower()}"

    # Filtro por proveedor
    prov_found = None
    if col_prov:
        m = re.search(r"(?:proveedor|supplier)\s+([a-zA-Z0-9\s\-\.]+?)(?:\s|$|\?)", q)
        if m:
            pq        = m.group(1).strip()
            mask      = filtered[col_prov].apply(lambda x: pq in _normalize(str(x)))
            if mask.any():
                filtered   = filtered[mask]
                prov_found = filtered[col_prov].iloc[0]
                desc       = f"órdenes del proveedor '{prov_found}'"

    if prov_found is None and col_prov:
        for prov in sorted(df[col_prov].dropna().unique(), key=len, reverse=True):
            if prov and _normalize(str(prov)) in q:
                filtered   = filtered[filtered[col_prov] == prov]
                prov_found = str(prov)
                desc       = f"órdenes del proveedor '{prov}'"
                break

    if prov_found is None and ctx.get("proveedor") and col_prov:
        if any(q.startswith(kw) for kw in ["y ", "¿y", "cuales", "cuáles", "que tal", "y las", "y los"]):
            prov  = ctx["proveedor"]
            mask  = filtered[col_prov].apply(lambda x: _normalize(prov) in _normalize(str(x)))
            if mask.any():
                filtered   = filtered[mask]
                prov_found = prov
                desc       = f"órdenes del proveedor '{prov}'"

    if prov_found:
        new_ctx["proveedor"] = prov_found

    # Búsqueda por número de OC
    oc_match = re.search(r"\b(3[24]\d{7,})\b", question)
    if oc_match and col_oc:
        oc_num   = oc_match.group(1)
        filtered = df[df[col_oc].astype(str).str.contains(oc_num, na=False)]
        desc     = f"OC {oc_num}"
        new_ctx.pop("proveedor", None)

    # Serializar
    out = filtered.copy()
    for col in out.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        out[col] = out[col].dt.strftime("%Y-%m-%d").where(out[col].notna(), other=None)

    return out.fillna("").to_dict(orient="records"), desc, new_ctx


def _build_actions(filtered_data: list[dict], filter_desc: str, ctx: dict) -> list[ChatAction]:
    actions: list[ChatAction] = []
    if not filtered_data:
        return actions

    prov = ctx.get("proveedor")
    if prov:
        actions.append(ChatAction(label=f"Filtrar por {prov[:22]}", filter_key="supplier", filter_value=prov))

    if "critico" not in filter_desc.lower():
        n_crit = sum(1 for r in filtered_data if int(r.get("Días de retraso", r.get("dias_retraso", 0)) or 0) > 15)
        if n_crit:
            actions.append(ChatAction(label=f"Ver {n_crit} críticas", filter_key="only_critical", filter_value="true"))

    if prov or ctx.get("risk"):
        actions.append(ChatAction(label="Ver todas las OCs", filter_key="supplier", filter_value=""))

    return actions


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    from app.store import data_store
    from app.services.ai_service import generate_chat_response

    question = req.question.strip()
    if not question:
        return ChatResponse(answer="Por favor escribe una pregunta.")

    ctx = _parse_ctx(req.ctx)

    # ── 1. Obtener DataFrame ──────────────────────────────────────────────────
    # Prioridad: store en memoria → fallback a disco → error amigable

    df = data_store.df

    if df is None:
        # Intento de recuperación desde disco (puede existir del deploy anterior)
        try:
            from app.routers.upload import load_master_df
            df = load_master_df()
            # Poblar store para futuras llamadas en este proceso
            data_store.set(df, {}, [])
            log.info("Store recuperado desde disco (%d filas)", len(df))
        except Exception:
            return ChatResponse(
                answer=(
                    "No hay datos cargados.\n"
                    "Por favor sube el Excel maestro usando el botón de carga."
                )
            )

    # ── 2. Respuestas directas (sin IA, garantizan exactitud) ─────────────────
    direct = _try_direct_answer(question, df, data_store.summary)
    if direct:
        return ChatResponse(answer=direct)

    # ── 3. Filtrado + respuesta con IA / fallback ─────────────────────────────
    try:
        filtered_records, filter_desc, new_ctx = _parse_and_filter(question, df, ctx)
    except Exception as e:
        log.error("Error filtrando: %s", e)
        filtered_records = df.fillna("").to_dict(orient="records")[:50]
        filter_desc      = "todas las órdenes"
        new_ctx          = ctx

    try:
        answer = generate_chat_response(question, filtered_records, filter_desc)
    except Exception as e:
        log.error("Error generando respuesta: %s", e)
        n      = len(filtered_records)
        answer = f"Se encontraron {n} órdenes para '{filter_desc}'." if n else "No se encontraron resultados."

    actions = _build_actions(filtered_records, filter_desc, new_ctx)
    return ChatResponse(answer=answer, actions=actions)
