"""
Router de chatbot — POST /api/chat
Usa los datos del Excel en memoria (master.xlsx) para responder preguntas sobre OCs.
Soporta contexto conversacional via campo `ctx`.
"""
import re
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
log    = logging.getLogger(__name__)


# ── Modelos ───────────────────────────────────────────────────────────────────

class ChatAction(BaseModel):
    label:        str
    filter_key:   str   # "supplier" | "risk" | "only_critical" | "search"
    filter_value: str


class ChatRequest(BaseModel):
    question: str
    ctx:      str = ""  # contexto previo, e.g. "proveedor:EMERSON" o "risk:Crítico"


class ChatResponse(BaseModel):
    answer:  str
    actions: list[ChatAction] = []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    t = str(text).lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        t = t.replace(a, b)
    return t


def _parse_ctx(ctx: str) -> dict:
    """Convierte 'proveedor:EMERSON risk:Crítico' → {'proveedor': 'EMERSON', 'risk': 'Crítico'}"""
    result = {}
    for part in ctx.split("|"):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            result[k.strip().lower()] = v.strip()
    return result


def _parse_and_filter(question: str, df, ctx: dict) -> tuple[list[dict], str, dict]:
    """
    Interpreta la pregunta + contexto y filtra el DataFrame.
    Retorna (registros, descripción, contexto_actualizado).
    """
    import pandas as pd

    q    = _normalize(question)
    desc = "todas las órdenes"

    # Detectar columnas por nombre flexible
    col_dias = next((c for c in df.columns if "retraso" in c.lower()), None)
    col_prov = next((c for c in df.columns if "proveedor" in c.lower()), None)
    col_oc   = next((c for c in df.columns if "oc/pos" in c.lower()), None)
    col_prio = next((c for c in df.columns if "prioridad" in c.lower()), None)

    filtered    = df.copy()
    new_ctx     = dict(ctx)  # heredar contexto anterior

    # ── 1. Filtro de riesgo / retraso ─────────────────────────────────────────
    if any(kw in q for kw in ["critic", "critico", "criticas", "criticos"]):
        if col_dias:
            dias_num = pd.to_numeric(filtered[col_dias], errors="coerce").fillna(0)
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
        # Heredar filtro de riesgo del contexto si no hay keyword nueva
        risk = ctx["risk"]
        if risk == "Crítico" and col_dias:
            filtered = filtered[pd.to_numeric(filtered[col_dias], errors="coerce").fillna(0) > 15]
        elif risk == "En riesgo" and col_dias:
            dias_num = pd.to_numeric(filtered[col_dias], errors="coerce").fillna(0)
            filtered = filtered[(dias_num > 0) & (dias_num <= 15)]
        desc = f"órdenes {risk.lower()}"

    # ── 2. Filtro por proveedor ────────────────────────────────────────────────
    prov_found = None

    # Buscar "proveedor X" en la pregunta
    if col_prov:
        m = re.search(r"(?:proveedor|supplier)\s+([a-zA-Z0-9\s\-\.]+?)(?:\s|$|\?)", q)
        if m:
            pq        = m.group(1).strip()
            prov_mask = filtered[col_prov].apply(lambda x: pq in _normalize(str(x)))
            if prov_mask.any():
                filtered   = filtered[prov_mask]
                prov_found = filtered[col_prov].iloc[0] if len(filtered) > 0 else pq
                desc       = f"órdenes del proveedor '{prov_found}'"

    # Buscar nombre de proveedor literal en la pregunta
    if prov_found is None and col_prov:
        proveedores = df[col_prov].dropna().unique()
        for prov in sorted(proveedores, key=len, reverse=True):  # más largos primero
            if prov and _normalize(str(prov)) in q:
                filtered   = filtered[filtered[col_prov] == prov]
                prov_found = str(prov)
                desc       = f"órdenes del proveedor '{prov}'"
                break

    # Usar proveedor del contexto si la pregunta parece un follow-up
    if prov_found is None and ctx.get("proveedor") and col_prov:
        is_followup = any(q.startswith(kw) for kw in ["y ", "¿y", "cuales", "cuáles", "que tal", "qué tal", "y las", "y los"])
        if is_followup:
            prov        = ctx["proveedor"]
            prov_mask   = filtered[col_prov].apply(lambda x: _normalize(prov) in _normalize(str(x)))
            if prov_mask.any():
                filtered   = filtered[prov_mask]
                prov_found = prov
                desc       = f"órdenes del proveedor '{prov}'"

    if prov_found:
        new_ctx["proveedor"] = prov_found

    # ── 3. Búsqueda por número de OC ──────────────────────────────────────────
    oc_match = re.search(r"\b(3[24]\d{7,})\b", question)
    if oc_match and col_oc:
        oc_num   = oc_match.group(1)
        filtered = df[df[col_oc].astype(str).str.contains(oc_num, na=False)]
        desc     = f"OC {oc_num}"
        new_ctx.pop("proveedor", None)

    # ── Serializar ────────────────────────────────────────────────────────────
    out = filtered.copy()
    for col in out.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        out[col] = out[col].dt.strftime("%Y-%m-%d").where(out[col].notna(), other=None)

    records = out.fillna("").to_dict(orient="records")
    return records, desc, new_ctx


def _build_actions(filtered_data: list[dict], filter_desc: str, ctx: dict) -> list[ChatAction]:
    """Genera botones de acción contextuales para el frontend."""
    actions: list[ChatAction] = []
    n = len(filtered_data)
    if n == 0:
        return actions

    prov = ctx.get("proveedor")

    # Ver órdenes del proveedor en tabla
    if prov:
        actions.append(ChatAction(
            label=f"Filtrar por {prov[:22]}",
            filter_key="supplier",
            filter_value=prov,
        ))

    # Ver solo críticas si hay y no ya estamos en ese filtro
    if "critico" not in filter_desc.lower():
        criticas = sum(1 for r in filtered_data if int(r.get("Días de retraso", r.get("dias_retraso", 0)) or 0) > 15)
        if criticas > 0:
            actions.append(ChatAction(
                label=f"Ver {criticas} críticas",
                filter_key="only_critical",
                filter_value="true",
            ))

    # Limpiar filtros si hay contexto activo
    if prov or ctx.get("risk"):
        actions.append(ChatAction(
            label="Ver todas las OCs",
            filter_key="supplier",
            filter_value="",
        ))

    return actions


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    from app.routers.upload import load_master_df
    from app.services.ai_service import generate_chat_response
    from fastapi import HTTPException

    question = req.question.strip()
    if not question:
        return ChatResponse(answer="Por favor escribe una pregunta.")

    # Parsear contexto previo
    ctx = _parse_ctx(req.ctx)

    # Cargar datos
    try:
        df = load_master_df()
    except HTTPException as e:
        if e.status_code == 400:
            return ChatResponse(answer="No hay datos cargados. Por favor sube el Excel primero.")
        return ChatResponse(answer=f"Error al cargar datos: {e.detail}")
    except Exception as e:
        log.error("Error cargando master_df en chat: %s", e)
        return ChatResponse(answer="Error interno al cargar los datos.")

    # Filtrar
    try:
        filtered_records, filter_desc, new_ctx = _parse_and_filter(question, df, ctx)
    except Exception as e:
        log.error("Error filtrando en chat: %s", e)
        filtered_records = df.fillna("").to_dict(orient="records")[:50]
        filter_desc      = "todas las órdenes"
        new_ctx          = ctx

    # Generar respuesta
    try:
        answer = generate_chat_response(question, filtered_records, filter_desc)
    except Exception as e:
        log.error("Error generando respuesta: %s", e)
        n      = len(filtered_records)
        answer = f"Se encontraron {n} órdenes." if n else "No se encontraron resultados."

    # Generar acciones
    actions = _build_actions(filtered_records, filter_desc, new_ctx)

    return ChatResponse(answer=answer, actions=actions)
