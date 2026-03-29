"""
Router de chatbot — POST /api/chat

Flujo:
1. Detecta intención (provider_info, top_providers, summary, count, recommendation…)
2. Fuzzy match de proveedor (normalización + coincidencia parcial + tokens)
3. Aplica filtros sobre el DataFrame
4. Genera respuesta natural con insights automáticos
5. Devuelve acciones sugeridas para el frontend
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


# ── Normalización ─────────────────────────────────────────────────────────────

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


# ── Fuzzy Provider Match ──────────────────────────────────────────────────────

def _find_provider(query: str, providers: list[str]) -> str | None:
    """
    Busca el proveedor más cercano a `query`.
    Orden de prioridad:
      1. Match exacto normalizado
      2. Query contenido en nombre del proveedor (min 3 chars)
      3. Nombre del proveedor contenido en query (min 3 chars)
      4. Overlap de tokens con al menos 1 token significativo (>= 4 chars)
    """
    q = _normalize(query)
    if not q or len(q) < 2:
        return None

    # 1. Exacto
    for p in providers:
        if _normalize(p) == q:
            return p

    # 2. Query dentro del nombre del proveedor
    if len(q) >= 3:
        for p in sorted(providers, key=len, reverse=True):
            if q in _normalize(p):
                return p

    # 3. Nombre del proveedor dentro del query
    for p in sorted(providers, key=len, reverse=True):
        pn = _normalize(p)
        if len(pn) >= 3 and pn in q:
            return p

    # 4. Overlap de tokens
    q_tokens = set(q.split())
    best_match = None
    best_score = 0
    for p in providers:
        p_tokens = set(_normalize(p).split())
        shared   = q_tokens & p_tokens
        overlap  = len(shared)
        if overlap > best_score:
            meaningful = any(len(t) >= 4 for t in shared)
            if meaningful:
                best_score = overlap
                best_match = p
    return best_match


def _suggest_providers(query: str, providers: list[str], n: int = 3) -> list[str]:
    """Sugerencias cuando no hay match: prefijo de 3+ chars."""
    q = _normalize(query)
    seen: list[str] = []
    for p in providers:
        pn = _normalize(p)
        if (len(q) >= 3 and q[:3] in pn) or (len(pn) >= 3 and pn[:3] in q):
            seen.append(p)
        if len(seen) >= n:
            break
    return seen


# ── Detección de Intención ────────────────────────────────────────────────────

_RISK_KEYWORDS = {
    "critico":  ["critic", "critico", "critica", "criticas", "criticos"],
    "riesgo":   ["en riesgo", "riesgo", "retrasad", "retraso", "atrasad", "tarde"],
    "plazo":    ["en plazo", "a tiempo", "plazo", "puntual"],
}

_SUMMARY_KW      = ["resumen", "summary", "estado general", "como estamos", "panorama", "overview"]
_RECOM_KW        = ["que hacer", "recomendacion", "recomiendo", "acciones", "priorizar", "sugerencia", "siguiente paso", "plan"]
_TOP_KW          = ["top", "ranking", "peor", "peores", "mas retraso", "mayor retraso", "mas critico", "mas retras"]
_BEST_KW         = ["mejor", "mejores", "bien", "buen", "mas en plazo", "sin retraso", "cumple"]
_COUNT_KW        = ["cuantas", "cuantos", "total", "numero de", "cantidad", "cuantas hay", "cuantas son"]
_PROV_LIST_KW    = ["proveedores", "lista de proveedores", "que proveedores", "cuantos proveedores"]


def _extract_risk(q: str) -> str | None:
    for risk, keywords in _RISK_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return risk
    return None


def _detect_intent(q_norm: str, ctx: dict, providers: list[str]) -> dict:
    """
    Retorna:
      type: summary | count | provider_info | top_providers | best_providers |
            recommendation | filter_only | provider_list | unknown
      provider:     str | None
      risk_filter:  "critico" | "riesgo" | "plazo" | None
      top_n:        int
    """
    intent: dict = {
        "type":        "unknown",
        "provider":    None,
        "risk_filter": None,
        "top_n":       5,
    }

    risk = _extract_risk(q_norm)
    intent["risk_filter"] = risk

    # top N
    m = re.search(r"top\s*(\d+)", q_norm)
    if m:
        intent["top_n"] = int(m.group(1))

    # ── Tipos sin proveedor ───────────────────────────────────────────────────
    if any(kw in q_norm for kw in _SUMMARY_KW):
        intent["type"] = "summary"
        return intent

    if any(kw in q_norm for kw in _RECOM_KW):
        intent["type"] = "recommendation"
        return intent

    if any(kw in q_norm for kw in _TOP_KW):
        intent["type"] = "top_providers"
        return intent

    if any(kw in q_norm for kw in _BEST_KW):
        intent["type"] = "best_providers"
        return intent

    if any(kw in q_norm for kw in _PROV_LIST_KW) and not risk:
        intent["type"] = "provider_list"
        return intent

    # ── Conteo general ────────────────────────────────────────────────────────
    if any(kw in q_norm for kw in _COUNT_KW):
        found = _find_provider(q_norm, providers)
        if found:
            intent["provider"] = found
            intent["type"] = "provider_info"
        else:
            intent["type"] = "count"
        return intent

    # ── Buscar proveedor en la query ──────────────────────────────────────────
    found_prov = _find_provider(q_norm, providers)
    ctx_prov   = ctx.get("proveedor")

    if found_prov:
        intent["provider"] = found_prov
        intent["type"] = "provider_info"
        return intent

    # Solo riesgo (con o sin contexto de proveedor previo)
    if risk:
        intent["type"] = "filter_only"
        # Continuar contexto de proveedor si viene de pregunta anterior
        if ctx_prov and any(q_norm.startswith(kw) for kw in [
            "y ", "las ", "los ", "cuales", "cuantas", "cuantos", "que tal", "y las", "y los",
        ]):
            intent["provider"] = ctx_prov
            intent["type"] = "provider_info"
        elif ctx_prov:
            # si la pregunta es SOLO el riesgo (1-2 palabras), asumir contexto
            words = [w for w in q_norm.split() if len(w) > 2]
            if len(words) <= 2:
                intent["provider"] = ctx_prov
                intent["type"] = "provider_info"
        return intent

    # Pregunta corta (1-3 palabras): podría ser nombre de proveedor incompleto
    words = q_norm.split()
    if 1 <= len(words) <= 3:
        non_stopwords = [w for w in words if w not in {
            "hay", "son", "estan", "tiene", "cuanto", "como", "que",
            "cual", "dame", "ver", "muestra", "muéstrame", "dime",
        }]
        candidate = " ".join(non_stopwords)
        possible  = _find_provider(candidate, providers)
        if possible:
            intent["provider"] = possible
            intent["type"] = "provider_info"
            return intent

    return intent


# ── Columnas clave ────────────────────────────────────────────────────────────

def _get_cols(df: pd.DataFrame) -> dict:
    c = df.columns.tolist()
    return {
        "dias":   next((x for x in c if "retraso" in x.lower()), None),
        "prov":   next((x for x in c if "proveedor" in x.lower()), None),
        "oc":     next((x for x in c if "oc/pos" in x.lower()), None),
        "prio":   next((x for x in c if "prioridad" in x.lower()), None),
        "estado": next((x for x in c if "estado" in x.lower()), None),
        "desc":   next((x for x in c if "descripci" in x.lower()), None),
    }


# ── Filtrado ──────────────────────────────────────────────────────────────────

def _apply_filters(
    df: pd.DataFrame,
    provider:    str | None,
    risk_filter: str | None,
    cols:        dict,
) -> pd.DataFrame:
    result = df.copy()

    if provider and cols["prov"]:
        pn   = _normalize(provider)
        mask = result[cols["prov"]].apply(lambda x: _normalize(str(x)) == pn)
        if not mask.any():
            mask = result[cols["prov"]].apply(lambda x: pn in _normalize(str(x)))
        result = result[mask]

    if risk_filter and cols["dias"]:
        dias = pd.to_numeric(result[cols["dias"]], errors="coerce").fillna(0)
        if risk_filter == "critico":
            result = result[dias > 15]
        elif risk_filter == "riesgo":
            result = result[(dias > 0) & (dias <= 15)]
        elif risk_filter == "plazo":
            result = result[dias <= 0]

    return result


# ── Estadísticas ──────────────────────────────────────────────────────────────

def _stats(df: pd.DataFrame, cols: dict) -> dict:
    total = len(df)
    if cols["dias"] and total:
        dias      = pd.to_numeric(df[cols["dias"]], errors="coerce").fillna(0)
        criticas  = int((dias > 15).sum())
        en_riesgo = int(((dias > 0) & (dias <= 15)).sum())
        en_plazo  = int((dias <= 0).sum())
        tard      = dias[dias > 0]
        avg_dias  = round(float(tard.mean()), 1) if not tard.empty else 0.0
        max_dias  = int(dias.max())
    else:
        criticas = en_riesgo = en_plazo = max_dias = 0
        avg_dias = 0.0

    return {
        "total":        total,
        "criticas":     criticas,
        "en_riesgo":    en_riesgo,
        "en_plazo":     en_plazo,
        "pct_criticas": round(criticas / total * 100) if total else 0,
        "pct_riesgo":   round(en_riesgo / total * 100) if total else 0,
        "avg_dias":     avg_dias,
        "max_dias":     max_dias,
    }


def _insight(stats: dict, subject: str = "El portafolio") -> str:
    pct   = stats["pct_criticas"]
    total = stats["total"]
    if total == 0:
        return ""
    if pct >= 50:
        return (f"{subject} tiene **{pct}% de críticas** — situación urgente. "
                "Se recomienda escalamiento inmediato.")
    elif pct >= 30:
        return (f"{subject} tiene **{pct}% de críticas** — nivel de alerta. "
                "Revisar con el proveedor esta semana.")
    elif pct >= 15:
        return (f"{subject} muestra señales de riesgo (**{pct}% críticas**). "
                "Monitorear de cerca.")
    elif pct == 0 and stats["en_riesgo"] == 0:
        return f"{subject} está **al día** — sin retrasos. Buen desempeño."
    else:
        return f"{subject} presenta **{pct}% de críticas** — dentro de límites aceptables."


# ── Generadores de respuesta ──────────────────────────────────────────────────

def _resp_summary(df: pd.DataFrame, cols: dict) -> str:
    s    = _stats(df, cols)
    provs = len(df[cols["prov"]].dropna().unique()) if cols["prov"] else "?"
    lines = [
        "**Resumen general del portafolio:**",
        f"- Total OCs: **{s['total']}**",
        f"- Críticas (+15d): **{s['criticas']}** ({s['pct_criticas']}%)",
        f"- En riesgo (1–15d): **{s['en_riesgo']}** ({s['pct_riesgo']}%)",
        f"- En plazo: **{s['en_plazo']}**",
        f"- Proveedores activos: **{provs}**",
        f"- Retraso promedio (OCs tardías): **{s['avg_dias']} días**",
        "",
        _insight(s),
    ]
    return "\n".join(x for x in lines if x is not None)


def _resp_provider(
    df_filt: pd.DataFrame,
    provider: str,
    risk_filter: str | None,
    cols: dict,
) -> str:
    s = _stats(df_filt, cols)
    if s["total"] == 0:
        return f"No se encontraron órdenes para **{provider}**."

    risk_label = {
        "critico": " críticas",
        "riesgo":  " en riesgo",
        "plazo":   " en plazo",
        None:      "",
    }.get(risk_filter, "")

    subj  = f"**{provider}**"
    lines = [f"{subj}{(' —' + risk_label) if risk_label else ''}:"]

    if risk_filter:
        lines.append(f"- **{s['total']}** OCs{risk_label}")
    else:
        lines += [
            f"- Total OCs: **{s['total']}**",
            f"- Críticas (+15d): **{s['criticas']}** ({s['pct_criticas']}%)",
            f"- En riesgo (1–15d): **{s['en_riesgo']}** ({s['pct_riesgo']}%)",
            f"- En plazo: **{s['en_plazo']}**",
        ]
        if s["max_dias"] > 0:
            lines.append(f"- Mayor retraso: **{s['max_dias']} días**")

    ins = _insight(s, subj)
    if ins:
        lines += ["", ins]

    return "\n".join(lines)


def _resp_top_providers(
    df:    pd.DataFrame,
    cols:  dict,
    top_n: int  = 5,
    mode:  str  = "worst",
) -> str:
    if not cols["prov"] or not cols["dias"]:
        return "No hay datos suficientes para calcular el ranking."

    grp = (
        df.groupby(cols["prov"])
        .agg(
            total=(cols["prov"], "count"),
            criticas=(
                cols["dias"],
                lambda x: int((pd.to_numeric(x, errors="coerce").fillna(0) > 15).sum()),
            ),
            avg_dias=(
                cols["dias"],
                lambda x: round(float(pd.to_numeric(x, errors="coerce").fillna(0).mean()), 1),
            ),
        )
        .reset_index()
    )

    if mode == "best":
        grp   = grp[grp["criticas"] == 0].sort_values("total", ascending=False)
        title = f"**Top {min(top_n, len(grp))} proveedores sin retrasos críticos:**"
    else:
        grp   = grp.sort_values(["criticas", "avg_dias"], ascending=False)
        title = f"**Top {min(top_n, len(grp))} proveedores con más retrasos:**"

    top = grp.head(top_n)
    if top.empty:
        return "No hay proveedores que cumplan este criterio."

    lines = [title]
    for i, (_, row) in enumerate(top.iterrows(), 1):
        pct  = round(row["criticas"] / row["total"] * 100) if row["total"] else 0
        name = str(row[cols["prov"]])[:32]
        if mode == "best":
            lines.append(f"{i}. **{name}** — {int(row['total'])} OCs, todas en plazo")
        else:
            lines.append(
                f"{i}. **{name}** — {int(row['criticas'])} críticas "
                f"({pct}%), avg {row['avg_dias']}d retraso"
            )

    return "\n".join(lines)


def _resp_provider_list(df: pd.DataFrame, cols: dict) -> str:
    if not cols["prov"]:
        return "No se encontró columna de proveedor."
    provs = sorted(df[cols["prov"]].dropna().unique().tolist())
    if not provs:
        return "No hay proveedores registrados."
    preview = provs[:12]
    resto   = len(provs) - 12
    lines   = [f"**{len(provs)} proveedores activos:**"]
    lines  += [f"  • {p}" for p in preview]
    if resto > 0:
        lines.append(f"  … y {resto} más.")
    return "\n".join(lines)


def _resp_recommendation(df: pd.DataFrame, cols: dict) -> str:
    if not cols["prov"] or not cols["dias"]:
        return "No hay datos suficientes para generar recomendaciones."

    s = _stats(df, cols)

    grp = (
        df.groupby(cols["prov"])
        .agg(
            criticas=(
                cols["dias"],
                lambda x: int((pd.to_numeric(x, errors="coerce").fillna(0) > 15).sum()),
            ),
            total=(cols["prov"], "count"),
        )
        .reset_index()
    )
    grp["pct"] = grp.apply(
        lambda r: round(r["criticas"] / r["total"] * 100) if r["total"] else 0, axis=1
    )
    top3 = grp.sort_values("criticas", ascending=False).head(3)

    lines = ["**Recomendaciones de acción:**", ""]
    alert = (
        f"⚠ **Situación crítica**: {s['pct_criticas']}% del portafolio en estado crítico."
        if s["pct_criticas"] >= 30
        else f"Estado general: {s['criticas']} OCs críticas ({s['pct_criticas']}% del total)."
    )
    lines.append(alert)
    lines += ["", "**Proveedores a priorizar:**"]
    for _, row in top3.iterrows():
        name = str(row[cols["prov"]])[:32]
        lines.append(
            f"  • **{name}** — {int(row['criticas'])} críticas ({row['pct']}%) → contactar esta semana"
        )
    lines += [
        "",
        "**Acciones sugeridas:**",
        "  1. Solicitar confirmación de fechas a proveedores con >50% críticas",
        "  2. Revisar disponibilidad de materiales críticos para planta",
        "  3. Escalar OCs con >30 días de retraso a gestión de compras",
    ]
    return "\n".join(lines)


def _resp_filter_only(
    df_filt: pd.DataFrame,
    risk_filter: str | None,
    cols: dict,
) -> str:
    risk_label = {
        "critico": "críticas",
        "riesgo":  "en riesgo",
        "plazo":   "en plazo",
    }.get(risk_filter or "", "")

    s = _stats(df_filt, cols)
    answer = f"Hay **{s['total']}** órdenes {risk_label}."

    if risk_filter in ("critico", "riesgo") and cols["prov"] and s["total"]:
        top = (
            df_filt.groupby(cols["prov"])
            .size()
            .sort_values(ascending=False)
            .head(5)
        )
        if not top.empty:
            lines = [answer, "", "**Proveedores más afectados:**"]
            for prov, cnt in top.items():
                lines.append(f"  • **{prov}** — {int(cnt)} OCs")
            answer = "\n".join(lines)

    return answer


def _resp_count(
    df_filt:     pd.DataFrame,
    risk_filter: str | None,
    provider:    str | None,
    cols:        dict,
) -> str:
    s = _stats(df_filt, cols)

    ctx_parts: list[str] = []
    if provider:
        ctx_parts.append(f"del proveedor **{provider}**")
    risk_map = {"critico": "críticas", "riesgo": "en riesgo", "plazo": "en plazo"}
    if risk_filter:
        ctx_parts.append(f"en estado **{risk_map[risk_filter]}**")

    suffix = " " + " ".join(ctx_parts) if ctx_parts else ""
    n = {
        "critico": s["criticas"],
        "riesgo":  s["en_riesgo"],
        "plazo":   s["en_plazo"],
    }.get(risk_filter or "", s["total"])

    return f"Hay **{n}** órdenes{suffix}."


def _resp_unknown(df: pd.DataFrame, cols: dict, question: str, providers: list[str]) -> str:
    # último intento: fuzzy sobre la pregunta completa
    maybe = _find_provider(_normalize(question), providers)
    if maybe:
        df_p = _apply_filters(df, maybe, None, cols)
        return _resp_provider(df_p, maybe, None, cols)

    # sugerencias si parece nombre de proveedor
    words = _normalize(question).split()
    if 1 <= len(words) <= 3:
        suggestions = _suggest_providers(_normalize(question), providers)
        if suggestions:
            sug_str = ", ".join(f"**{s}**" for s in suggestions)
            return f"No encontré '{question}'. ¿Quisiste decir: {sug_str}?"

    s = _stats(df, cols)
    return (
        f"No entendí la pregunta. Estado actual: **{s['total']}** OCs en total, "
        f"**{s['criticas']}** críticas ({s['pct_criticas']}%).\n"
        "Puedes preguntar por un proveedor, pedir el **resumen**, "
        "el **top 5**, o escribir **recomendaciones**."
    )


# ── Acciones para el frontend ─────────────────────────────────────────────────

def _build_actions(
    df_filt: pd.DataFrame,
    intent:  dict,
    cols:    dict,
) -> list[ChatAction]:
    actions: list[ChatAction] = []
    provider = intent.get("provider")
    risk     = intent.get("risk_filter")
    itype    = intent.get("type")

    if provider:
        actions.append(
            ChatAction(label=f"Filtrar {provider[:20]}", filter_key="supplier", filter_value=provider)
        )

    if itype in ("provider_info", "summary", "filter_only") and not risk:
        if cols["dias"]:
            dias   = pd.to_numeric(df_filt[cols["dias"]], errors="coerce").fillna(0)
            n_crit = int((dias > 15).sum())
            if n_crit:
                actions.append(
                    ChatAction(label=f"Ver {n_crit} críticas", filter_key="only_critical", filter_value="true")
                )

    if provider or risk:
        actions.append(
            ChatAction(label="Ver todas las OCs", filter_key="supplier", filter_value="")
        )

    return actions


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    from app.store import data_store

    question = req.question.strip()
    if not question:
        return ChatResponse(answer="Por favor escribe una pregunta.")

    ctx = _parse_ctx(req.ctx)

    # ── 1. Obtener DataFrame ──────────────────────────────────────────────────
    df = data_store.df
    if df is None:
        try:
            from app.routers.upload import load_master_df
            df = load_master_df()
            data_store.set(df, {}, [])
            log.info("Store recuperado desde disco (%d filas)", len(df))
        except Exception:
            return ChatResponse(
                answer=(
                    "No hay datos cargados.\n"
                    "Por favor sube el Excel maestro usando el botón de carga."
                )
            )

    providers: list[str] = data_store.proveedores
    if not providers:
        col_prov = next((c for c in df.columns if "proveedor" in c.lower()), None)
        if col_prov:
            providers = sorted(df[col_prov].dropna().unique().tolist())

    cols   = _get_cols(df)
    q_norm = _normalize(question)

    # ── 2. Detectar intención ─────────────────────────────────────────────────
    intent = _detect_intent(q_norm, ctx, providers)
    log.info("Intención detectada: %s | prov=%s | risk=%s",
             intent["type"], intent["provider"], intent["risk_filter"])

    # ── 3. Aplicar filtros ────────────────────────────────────────────────────
    df_filt = _apply_filters(df, intent["provider"], intent["risk_filter"], cols)

    # ── 4. Generar respuesta según intención ──────────────────────────────────
    itype = intent["type"]

    if itype == "summary":
        answer = _resp_summary(df, cols)

    elif itype == "recommendation":
        answer = _resp_recommendation(df, cols)

    elif itype == "top_providers":
        answer = _resp_top_providers(df, cols, intent["top_n"], mode="worst")

    elif itype == "best_providers":
        answer = _resp_top_providers(df, cols, intent["top_n"], mode="best")

    elif itype == "provider_list":
        answer = _resp_provider_list(df, cols)

    elif itype == "provider_info":
        answer = _resp_provider(df_filt, intent["provider"], intent["risk_filter"], cols)

    elif itype == "filter_only":
        answer = _resp_filter_only(df_filt, intent["risk_filter"], cols)

    elif itype == "count":
        answer = _resp_count(df_filt, intent["risk_filter"], intent["provider"], cols)

    else:
        answer = _resp_unknown(df, cols, question, providers)

    # ── 5. Actualizar contexto conversacional ─────────────────────────────────
    new_ctx = dict(ctx)
    if intent["provider"]:
        new_ctx["proveedor"] = intent["provider"]
    elif itype in ("summary", "recommendation", "top_providers", "best_providers", "provider_list"):
        new_ctx.pop("proveedor", None)
        new_ctx.pop("risk", None)

    if intent["risk_filter"]:
        new_ctx["risk"] = intent["risk_filter"]
    elif itype in ("summary", "recommendation", "top_providers", "best_providers"):
        new_ctx.pop("risk", None)

    # ── 6. Acciones sugeridas para el frontend ────────────────────────────────
    actions = _build_actions(df_filt, intent, cols)

    return ChatResponse(answer=answer, actions=actions)
