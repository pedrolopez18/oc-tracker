"""
GET /api/report — exporta un subconjunto del Excel como archivo .xlsx descargable.

Parámetros de query (todos opcionales):
  proveedor  — filtrar por nombre de proveedor (fuzzy match)
  estado     — "critico" | "riesgo" | "plazo"

Ejemplos:
  /api/report
  /api/report?proveedor=Siemens
  /api/report?estado=critico
  /api/report?proveedor=Emerson&estado=critico
"""
import io
import re
import logging
import pandas as pd
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()
log    = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    t = str(text).lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        t = t.replace(a, b)
    return t


@router.get("/")
def export_report(
    proveedor: str | None = Query(default=None, description="Nombre o parte del proveedor"),
    estado:    str | None = Query(default=None, description="critico | riesgo | plazo"),
):
    from app.store import data_store

    df = data_store.df
    if df is None:
        try:
            from app.routers.upload import load_master_df
            df = load_master_df()
            data_store.set(df, {}, [])
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="No hay datos cargados. Sube el Excel primero."
            )

    result   = df.copy()
    col_prov = next((c for c in result.columns if "proveedor" in c.lower()), None)
    col_dias = next((c for c in result.columns if "retraso" in c.lower()), None)

    filename_parts = ["reporte_oc"]

    # ── Filtro por proveedor (fuzzy) ──────────────────────────────────────────
    if proveedor and col_prov:
        pq   = _normalize(proveedor)
        mask = result[col_prov].apply(lambda x: pq in _normalize(str(x)))
        result = result[mask]
        if result.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontraron órdenes para el proveedor '{proveedor}'."
            )
        safe_name = re.sub(r"[^\w\-]", "_", proveedor[:24])
        filename_parts.append(safe_name)

    # ── Filtro por estado ─────────────────────────────────────────────────────
    if estado and col_dias:
        dias = pd.to_numeric(result[col_dias], errors="coerce").fillna(0)
        en   = _normalize(estado)
        if "crit" in en:
            result = result[dias > 15]
            filename_parts.append("critico")
        elif "riesgo" in en or "retras" in en:
            result = result[(dias > 0) & (dias <= 15)]
            filename_parts.append("riesgo")
        elif "plazo" in en or "tiempo" in en:
            result = result[dias <= 0]
            filename_parts.append("en_plazo")

        if result.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No hay órdenes con estado '{estado}' para los filtros aplicados."
            )

    # ── Serializar fechas ─────────────────────────────────────────────────────
    for col in result.select_dtypes(
        include=["datetime64[ns]", "datetime64[ns, UTC]"]
    ).columns:
        result[col] = result[col].dt.strftime("%Y-%m-%d").where(result[col].notna(), other=None)

    # ── Generar Excel en memoria ──────────────────────────────────────────────
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        result.fillna("").to_excel(writer, index=False, sheet_name="Reporte OC")
    buf.seek(0)

    filename = "_".join(filename_parts) + ".xlsx"
    log.info("Exportando reporte: %s (%d filas)", filename, len(result))

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
