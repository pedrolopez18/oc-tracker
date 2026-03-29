"""
Servicio de IA — anthropic es opcional.
Si no está instalado o no hay API key → fallback con texto Python puro.
"""
import json
import logging

log = logging.getLogger(__name__)

# ── Import opcional de anthropic ──────────────────────────────────────────────
try:
    import anthropic as _anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False
    log.info("anthropic no instalado — se usará fallback.")


def _get_client():
    from app.config import get_settings
    api_key = get_settings().anthropic_api_key
    if not _ANTHROPIC_AVAILABLE or not api_key:
        return None
    try:
        return _anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        log.warning("No se pudo crear cliente Anthropic: %s", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Funciones originales (con fallback)
# ─────────────────────────────────────────────────────────────────────────────

def summarize_comments(comments: str) -> str:
    if not comments or len(comments.strip()) < 20:
        return comments
    client = _get_client()
    if client is None:
        return comments[:200] + ("..." if len(comments) > 200 else "")
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content":
                f"Eres analista de supply chain. Resume en máximo 2 líneas este historial "
                f"de seguimiento de OC. Sé directo, menciona el estado actual y el riesgo "
                f"principal. Solo el resumen, sin preámbulos.\n\n{comments}"
            }]
        )
        return msg.content[0].text
    except Exception as e:
        log.warning("Error en summarize_comments: %s", e)
        return comments[:200] + ("..." if len(comments) > 200 else "")


def detect_risks(orders: list[dict]) -> dict:
    client = _get_client()
    if client is None:
        critical = [o["proveedor"] for o in orders if o.get("dias_retraso", 0) > 15]
        return {
            "critical_suppliers":  list(set(critical)),
            "main_risks":          ["Retrasos superiores a 15 días detectados"] if critical else [],
            "recommended_actions": ["Contactar proveedores con retraso crítico"] if critical else [],
        }
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=600,
            messages=[{"role": "user", "content":
                f"Analiza estas órdenes de compra y responde SOLO con JSON válido (sin markdown):\n"
                f"{{\n"
                f"  \"critical_suppliers\": [\"lista de proveedores con riesgo alto\"],\n"
                f"  \"main_risks\": [\"riesgo 1\", \"riesgo 2\"],\n"
                f"  \"recommended_actions\": [\"acción 1\", \"acción 2\"]\n"
                f"}}\n\nDatos:\n{json.dumps(orders[:50], ensure_ascii=False, default=str)}"
            }]
        )
        return json.loads(msg.content[0].text)
    except Exception as e:
        log.warning("Error en detect_risks: %s", e)
        return {"critical_suppliers": [], "main_risks": [], "recommended_actions": []}


def generate_email_body(supplier: str, orders: list[dict]) -> str:
    delayed = [o for o in orders if o.get("dias_retraso", 0) > 0]
    client  = _get_client()
    if client is None:
        return (
            f"Estimado proveedor {supplier},\n\n"
            f"Le contactamos en relación a {len(orders)} órdenes de compra pendientes"
            + (f", de las cuales {len(delayed)} presentan retraso." if delayed else ".")
            + "\n\nLe solicitamos confirmación de las fechas de entrega.\n\nSaludos."
        )
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content":
                f"Redacta un correo de seguimiento de órdenes de compra para el proveedor "
                f"\"{supplier}\". Tono profesional, en español. Incluye: saludo formal, "
                f"referencia a {len(orders)} OCs adjuntas, mención de {len(delayed)} OCs "
                f"con retraso si aplica, solicitud de confirmación de fechas, cierre formal. "
                f"Solo el texto del correo, sin asunto ni markdown."
            }]
        )
        return msg.content[0].text
    except Exception as e:
        log.warning("Error en generate_email_body: %s", e)
        return f"Estimado proveedor {supplier},\n\nAdjuntamos {len(orders)} OCs para su seguimiento.\n\nSaludos."


# ─────────────────────────────────────────────────────────────────────────────
# Chatbot — función principal
# ─────────────────────────────────────────────────────────────────────────────

def generate_chat_response(question: str, filtered_data: list[dict], filter_desc: str = "") -> str:
    """
    Genera respuesta para el chatbot.
    Con API key → Claude. Sin API key → fallback Python con lenguaje natural.
    """
    client = _get_client()
    if client is None:
        return _fallback_chat_response(question, filtered_data, filter_desc)

    sample  = filtered_data[:80]
    context = json.dumps(sample, ensure_ascii=False, default=str)

    system_prompt = (
        "Eres un asistente de supply chain especializado en órdenes de compra (OC) para Pluspetrol. "
        "Respondes siempre en español, de forma directa y profesional. "
        "Usa lenguaje natural: no listes variables sino frases completas. "
        "Cuando mencionas cantidades importantes, escríbelas en negrita con **número**. "
        "Añade insights de negocio cuando sean relevantes (e.g. porcentaje de riesgo, impacto en cadena de suministro). "
        "Si no hay resultados, dilo claramente con sugerencias de qué consultar."
    )
    user_message = (
        f"Pregunta: {question}\n"
        f"Contexto de filtro aplicado: {filter_desc or 'ninguno'}\n"
        f"Total de resultados: {len(filtered_data)}\n\n"
        f"Datos (muestra):\n{context}\n\n"
        f"Responde la pregunta de forma natural y útil."
    )

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=600,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return msg.content[0].text
    except Exception as e:
        log.warning("Error llamando a Claude: %s", e)
        return _fallback_chat_response(question, filtered_data, filter_desc)


def _fallback_chat_response(question: str, filtered_data: list[dict], filter_desc: str = "") -> str:
    """Respuesta sin IA: lenguaje natural generado con Python puro."""
    n = len(filtered_data)

    if n == 0:
        return (
            "No se encontraron órdenes de compra para esa consulta.\n"
            "Puedes preguntar por proveedor, número de OC, órdenes críticas o retrasadas."
        )

    def _get(r: dict, *keys: str, default=0):
        for k in keys:
            if k in r:
                return r[k]
        return default

    # Estadísticas
    criticas  = [r for r in filtered_data if int(_get(r, "Días de retraso", "dias_retraso") or 0) > 15]
    en_riesgo = [r for r in filtered_data if 0 < int(_get(r, "Días de retraso", "dias_retraso") or 0) <= 15]
    en_plazo  = [r for r in filtered_data if int(_get(r, "Días de retraso", "dias_retraso") or 0) <= 0]

    proveedores = list({
        str(_get(r, "Proveedor", "proveedor", default=""))
        for r in filtered_data
        if _get(r, "Proveedor", "proveedor", default="")
    })

    single_prov = proveedores[0] if len(proveedores) == 1 else None

    # ── Apertura ──────────────────────────────────────────────────────────────
    if single_prov:
        opening = f"El proveedor **{single_prov}** tiene **{n}** orden{'es' if n != 1 else ''} registrada{'s' if n != 1 else ''}."
    elif "critic" in filter_desc.lower():
        opening = f"Se detectaron **{n}** órdenes críticas (más de 15 días de retraso)."
    elif "retrasa" in filter_desc.lower():
        opening = f"Hay **{n}** órdenes con retraso actualmente."
    elif "plazo" in filter_desc.lower():
        opening = f"Se encontraron **{n}** órdenes en plazo."
    else:
        opening = f"Hay **{n}** órdenes de compra en el sistema."

    lines = [opening]

    # ── Breakdown de riesgo ───────────────────────────────────────────────────
    if n > 0:
        breakdown = []
        if criticas:
            pct = round(len(criticas) / n * 100)
            breakdown.append(f"**{len(criticas)} críticas** (+15d) — {pct}% del total")
        if en_riesgo:
            breakdown.append(f"**{len(en_riesgo)} en riesgo** (1–15d)")
        if en_plazo:
            breakdown.append(f"**{len(en_plazo)} en plazo** ✓")

        if breakdown:
            lines.append("\n" + " · ".join(breakdown))

    # ── Insight de negocio ────────────────────────────────────────────────────
    if criticas and len(criticas) >= 5:
        pct = round(len(criticas) / n * 100)
        lines.append(
            f"\n⚠️ {pct}% de las órdenes {'de este proveedor ' if single_prov else ''}están en estado crítico. "
            f"Se recomienda priorizar el seguimiento."
        )
    elif criticas and single_prov:
        lines.append(
            f"\nEl proveedor tiene {len(criticas)} orden{'es' if len(criticas) != 1 else ''} crítica{'s' if len(criticas) != 1 else ''} "
            f"que requiere{'n' if len(criticas) != 1 else ''} atención inmediata."
        )
    elif not criticas and not en_riesgo and single_prov:
        lines.append(f"\nTodas las órdenes de {single_prov} están actualmente en plazo.")

    # ── Detalle si pocos resultados ───────────────────────────────────────────
    if 1 <= n <= 8:
        lines.append("\nDetalle:")
        for r in filtered_data:
            oc   = str(_get(r, "OC/POS", "oc_pos", default=""))
            prov = str(_get(r, "Proveedor", "proveedor", default=""))
            dias = int(_get(r, "Días de retraso", "dias_retraso") or 0)
            est  = str(_get(r, "Estado", "estado", default=""))
            prov_str = f" | {prov}" if not single_prov else ""
            lines.append(f"  • **{oc}**{prov_str} | {f'+{dias}d retraso' if dias > 0 else 'En plazo'}{f' | {est}' if est else ''}")

    return "\n".join(lines)
