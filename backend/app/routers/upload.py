from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pandas as pd
import openpyxl
import re
import io
import logging
from pathlib import Path

router = APIRouter()
log    = logging.getLogger(__name__)

UPLOADS_DIR   = Path(__file__).parent.parent / "uploads"
MASTER_FILE   = UPLOADS_DIR / "master.xlsx"
TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "plantilla_pluspetrol.xlsx"

REQUIRED_COLUMNS = [
    "OC/POS",
    "Fecha doc.",
    "Material",
    "Descripción",
    "Proveedor",
    "Comprador OC",
    "F.E según OC",
]

EXCEL_COL_MAP: dict[int, str] = {
    1:  "OC",
    2:  "Pos.",
    3:  "OC/POS",
    4:  "Fecha doc.",
    5:  "Centro",
    6:  "Material",
    7:  "Descripción",
    8:  "UMP",
    9:  "Cant. de pedido",
    10: "Por entregar",
    11: "Comprador OC",          # K: persona interna (no el proveedor externo)
    12: "F.E según OC",
    13: "Fecha Última Modificación.",
    14: "_COBERTURA_",           # N: resuelto dinámicamente en _generate_excel
}


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _normalize_str(text: str) -> str:
    """Limpia \xa0 de SAP, colapsa espacios múltiples, strip."""
    return re.sub(r"\s+", " ", str(text).replace("\xa0", " ")).strip()


def _find_col(cols: list[str], keyword: str) -> str | None:
    kw = keyword.lower()
    return next((c for c in cols if kw in c.lower()), None)


def _fmt_date(val) -> str | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, str):
        return val[:10] if len(val) >= 10 else val
    try:
        return pd.Timestamp(val).strftime("%Y-%m-%d")
    except Exception:
        return None


def classify_risk(dias: int) -> str:
    if dias > 15:
        return "Crítico"
    elif dias > 0:
        return "En riesgo"
    return "En plazo"


def _map_prioridad(val: str) -> str:
    """
    Mapea valores de la columna COBERTURA < 3 meses a Prioridad legible.
    SI / YES / TRUE / 1 → Crítico
    NO / FALSE / 0     → Normal
    Otro valor          → se devuelve tal cual
    """
    v = str(val).strip().upper()
    if v in ("SI", "SÍ", "YES", "TRUE", "1", "X", "S"):
        return "Crítico"
    if v in ("NO", "FALSE", "0", "N"):
        return "Normal"
    if v in ("", "NAN", "NONE", "NAT"):
        return ""
    return v  # pass-through para valores como "Alta", "Media", etc.


def load_master_df() -> pd.DataFrame:
    """
    Carga master.xlsx y aplica toda la normalización necesaria.
    Es la única fuente de verdad para todos los endpoints.
    """
    if not MASTER_FILE.exists():
        raise HTTPException(
            status_code=400,
            detail="No hay datos cargados. Sube el Excel primero."
        )
    try:
        df = pd.read_excel(
            MASTER_FILE,
            sheet_name="Base",
            header=5,
            engine="openpyxl",
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error leyendo master.xlsx: {e}")

    # ── 1. Normalizar nombres de columna ──────────────────────────────
    df.columns = df.columns.astype(str).map(_normalize_str)

    # ── 2. Eliminar filas completamente vacías ────────────────────────
    df = df.dropna(how="all").reset_index(drop=True)

    # ── 3. Estado: leer "STATUS de OC" (o cualquier col con "status") ──
    _NAN_VALS = {"nan", "none", "nat", "n/a", "na", "-", ""}

    if "Estado" not in df.columns:
        col_status = _find_col(list(df.columns), "status")
        if col_status:
            df["Estado"] = df[col_status]
            log.info("Columna 'Estado' mapeada desde '%s'", col_status)
        else:
            df["Estado"] = ""
            log.warning("Columna 'STATUS de OC' no encontrada. Columnas disponibles: %s", list(df.columns))

    # Limpiar Estado: trim, quitar NaN/nan/None → string vacío, normalizar \xa0
    df["Estado"] = (
        df["Estado"]
        .apply(lambda x: _normalize_str(str(x)) if pd.notna(x) else "")
        .apply(lambda x: "" if x.lower() in _NAN_VALS else x)
    )
    print("Estado únicos:", df["Estado"].unique().tolist())
    log.info("Estado únicos: %s", df["Estado"].unique().tolist())

    # ── 4. Prioridad: SIEMPRE desde "COBERTURA < 3 meses" ────────────
    #  Ignorar cualquier columna "Prioridad" pre-existente del SAP (suele estar vacía).
    #  Valores reales: CRITICO, LABORATORIO, MIPAYA, PPL, URGENTE
    col_cob = _find_col(list(df.columns), "cobertura")
    print(f"[DEBUG] Columna COBERTURA detectada: '{col_cob}'")
    if col_cob:
        df["Prioridad"] = (
            df[col_cob]
            .apply(lambda x: _normalize_str(str(x)).upper() if pd.notna(x) else "")
            .apply(lambda x: "" if x.lower() in _NAN_VALS else x)
        )
        print("Prioridades únicas:", df["Prioridad"].unique().tolist())
        log.info("Columna 'Prioridad' mapeada desde '%s': %s", col_cob, df["Prioridad"].unique().tolist())
    else:
        if "PRIORIDAD" in df.columns:
            df.rename(columns={"PRIORIDAD": "Prioridad"}, inplace=True)
        if "Prioridad" not in df.columns:
            df["Prioridad"] = ""
        print("[WARN] Columna 'COBERTURA < 3 meses' no encontrada. Columnas disponibles:", list(df.columns))

    # ── 5. Normalizar Proveedor: limpia \xa0, quita "nan" ─────────────
    if "Proveedor" in df.columns:
        df["Proveedor"] = df["Proveedor"].apply(
            lambda x: _normalize_str(str(x)) if pd.notna(x) else ""
        )
        df = df[~df["Proveedor"].isin(["", "nan", "NaN", "NAN"])].reset_index(drop=True)

    # ── 6. Días de retraso ────────────────────────────────────────────
    #  Detectar columnas por keyword (no hardcoded) para evitar fallos por nombre exacto
    #  fecha_base = "Últ. confirmada" si es válida, sino "F.E según OC"
    COL_FE_OC  = "F.E según OC"
    today      = pd.Timestamp.now().normalize()

    # Detección robusta: iterar columna por columna buscando "confirmada"
    print(f"[DEBUG] Todas las columnas disponibles: {list(df.columns)}")
    col_ultima = None
    for col in df.columns:
        if "confirmada" in col.lower():
            col_ultima = col
            break
    print(f"[DEBUG] Columna confirmada FINAL: '{col_ultima}'")

    # Limpiar valores inválidos en "Últ. confirmada" antes de parsear
    _INVALID_TIME = {"00:00:00", "0:00:00", "00:00", "nan", "nat", "none", ""}
    if col_ultima:
        df[col_ultima] = df[col_ultima].apply(
            lambda x: None if str(x).strip().lower() in _INVALID_TIME else x
        )

    fecha_confirmada = (
        pd.to_datetime(df[col_ultima], errors="coerce")
        if col_ultima
        else pd.Series(pd.NaT, index=df.index)
    )
    fecha_oc = (
        pd.to_datetime(df[COL_FE_OC], errors="coerce")
        if COL_FE_OC in df.columns
        else pd.Series(pd.NaT, index=df.index)
    )

    print("Confirmadas (head):", fecha_confirmada.head(5).tolist())
    print("FE OC     (head):", fecha_oc.head(5).tolist())

    # Días retraso: usa "Últ. confirmada" si existe y es válida, si no "F.E según OC"
    fecha_base = fecha_confirmada.where(fecha_confirmada.notna(), other=fecha_oc)
    df["Días de retraso"] = (today - fecha_base).dt.days.clip(lower=0).fillna(0).astype(int)
    print("Dias retraso stats:", df["Días de retraso"].describe().to_dict())
    log.info("Dias retraso stats: %s", df["Días de retraso"].describe().to_dict())

    return df


def _generate_excel(df_subset: pd.DataFrame) -> bytes:
    """Rellena la plantilla con df_subset. Fechas sin timestamp."""
    if not TEMPLATE_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Plantilla no encontrada: {TEMPLATE_PATH}"
        )

    # Resolver col 14 dinámicamente: buscar la columna real "COBERTURA < 3 meses"
    col_map = dict(EXCEL_COL_MAP)
    col_cob = _find_col(list(df_subset.columns), "cobertura")
    if col_cob:
        col_map[14] = col_cob
    else:
        del col_map[14]   # omitir si no existe en este subset

    wb = openpyxl.load_workbook(TEMPLATE_PATH)
    ws = wb.active

    # Columnas que deben quedar en blanco si no tienen fecha válida
    _BLANK_IF_EMPTY = {"Última F.E confirmada por el proveedor"}
    _INVALID_TIME   = {"00:00:00", "0:00:00", "00:00", ""}

    for row_idx, (_, row) in enumerate(df_subset.iterrows(), start=8):
        for col_idx, col_name in col_map.items():
            if col_name not in df_subset.columns:
                continue
            value = row[col_name]
            try:
                if pd.isna(value):
                    value = None
            except (TypeError, ValueError):
                pass
            # datetime → solo fecha (evita "2024-01-15 00:00:00" en Excel)
            if hasattr(value, "date"):
                value = value.date()
            # Para "Últ. confirmada": si es inválido o es hora sin fecha → blank
            if col_name in _BLANK_IF_EMPTY:
                s = str(value).strip() if value is not None else ""
                if s in _INVALID_TIME or s.startswith("00:00"):
                    value = None
            ws.cell(row=row_idx, column=col_idx).value = value

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────
# POST /  →  upload + proceso
# ─────────────────────────────────────────

@router.post("/")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=422, detail="Solo se aceptan archivos .xlsx o .xls")

    contents = await file.read()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_FILE.write_bytes(contents)
    log.info("Excel guardado: %s", MASTER_FILE)

    df = load_master_df()

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Columnas faltantes: {missing}. Detectadas: {df.columns.tolist()}"
        )

    col_ret  = _find_col(list(df.columns), "retraso")
    delayed  = int((pd.to_numeric(df[col_ret], errors="coerce").fillna(0) > 0).sum())  if col_ret else 0
    critical = int((pd.to_numeric(df[col_ret], errors="coerce").fillna(0) > 15).sum()) if col_ret else 0
    proveedores = sorted(df["Proveedor"].dropna().unique().tolist())

    summary = {
        "total":     len(df),
        "delayed":   delayed,
        "critical":  critical,
        "suppliers": len(proveedores),
    }

    # ── Guardar en store compartido (para que /chat lo use sin leer disco) ────
    from app.store import data_store
    data_store.set(df, summary, proveedores)
    log.info("Store actualizado: %d filas, %d proveedores", len(df), len(proveedores))

    return {"status": "ok", "summary": summary, "proveedores": proveedores}


# ─────────────────────────────────────────
# GET /ocs?proveedor=XXX
# ─────────────────────────────────────────

@router.get("/ocs")
def get_ocs(proveedor: str = Query(default="")):
    df   = load_master_df()
    cols = list(df.columns)

    if "Proveedor" not in cols:
        return {"data": []}

    if proveedor.strip():
        prov_norm   = _normalize_str(proveedor)
        df["_norm"] = df["Proveedor"].apply(_normalize_str)
        df = df[df["_norm"] == prov_norm].drop(columns=["_norm"])

    always = [
        "OC/POS", "Proveedor", "Comprador OC", "Descripción", "Material",
        "F.E según OC", "Estado", "Prioridad", "Días de retraso",
    ]
    for kw in ["modificaci", "comentarios", "motivo", "ultima"]:
        c = _find_col(cols, kw)
        if c and c not in always:
            always.append(c)

    columnas = [c for c in always if c in df.columns]

    df = df.copy()
    for col in columnas:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d").where(df[col].notna(), other=None)

    data = df[columnas].fillna("").to_dict(orient="records")
    return {"data": data}


# ─────────────────────────────────────────
# GET /oc-detail?oc_pos=XXX
# ─────────────────────────────────────────

@router.get("/oc-detail")
def get_oc_detail(oc_pos: str = Query(...)):
    df          = load_master_df()
    oc_pos_norm = _normalize_str(oc_pos)
    subset      = df[df["OC/POS"].astype(str).apply(_normalize_str) == oc_pos_norm]

    if subset.empty:
        raise HTTPException(status_code=404, detail=f"OC no encontrada: {oc_pos}")

    row  = subset.iloc[0]
    dias = int(row.get("Días de retraso", 0) or 0)

    return {
        "id":            0,
        "oc_pos":        str(row.get("OC/POS", "")                               or ""),
        "proveedor":     str(row.get("Proveedor", "")                             or ""),
        "comprador_oc":  str(row.get("Comprador OC", "")                          or ""),
        "descripcion":   str(row.get("Descripción", "")                           or ""),
        "material":      str(row.get("Material", "")                              or ""),
        "fe_segun_oc":   _fmt_date(row.get("F.E según OC")),
        "ultima_fe":     _fmt_date(row.get("Última F.E confirmada por el proveedor")
                                   or row.get("Fecha Última Modificación.")),
        "prioridad":     str(row.get("Prioridad", "")                             or ""),
        "estado":        str(row.get("Estado", "")                                or ""),
        "motivo_estado": str(row.get("Motivo del estado", "")                     or ""),
        "comentarios":   str(row.get("Comentarios de la Activación", "")          or ""),
        "dias_retraso":  dias,
        "ai_risk":       classify_risk(dias),
        "ai_summary":    None,
    }


# ─────────────────────────────────────────
# GET /template?proveedor=XXX
# ─────────────────────────────────────────

@router.get("/template")
def download_template(proveedor: str = Query(default="")):
    df = load_master_df()

    if "Proveedor" not in df.columns:
        raise HTTPException(status_code=422, detail="Columna 'Proveedor' no encontrada.")

    if proveedor.strip():
        prov_norm   = _normalize_str(proveedor)
        df["_norm"] = df["Proveedor"].apply(_normalize_str)
        df = df[df["_norm"] == prov_norm].drop(columns=["_norm"])

    if df.empty:
        raise HTTPException(status_code=404,
                            detail=f"Sin filas para proveedor '{proveedor}'.")

    log.info("Plantilla: '%s' (%d filas)", proveedor or "TODOS", len(df))
    excel_bytes = _generate_excel(df)
    filename    = f"seguimiento_{proveedor.strip()}.xlsx" if proveedor.strip() else "seguimiento.xlsx"
    filename    = re.sub(r'[\\/*?:"<>|]', "_", filename)

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────
# POST /send-emails
# ─────────────────────────────────────────

class EmailRequest(BaseModel):
    to:        str
    cc:        str = ""
    subject:   str
    body:      str
    proveedor: str = ""   # vacío = todos, si tiene valor = solo ese proveedor


@router.post("/send-emails")
def send_emails(req: EmailRequest):
    from app.services.email_service import send_supplier_email
    from app.config import get_settings

    if not req.to.strip():
        raise HTTPException(status_code=422, detail="El campo 'Para' es obligatorio.")

    cfg = get_settings()
    if not cfg.smtp_user or not cfg.smtp_password:
        raise HTTPException(
            status_code=501,
            detail="SMTP no configurado. Agrega SMTP_USER y SMTP_PASSWORD en backend/.env"
        )

    df = load_master_df()
    if "Proveedor" not in df.columns:
        raise HTTPException(status_code=422, detail="Columna 'Proveedor' no encontrada.")

    # ── Filtrar por proveedor si se especificó ──
    if req.proveedor.strip():
        prov_norm   = _normalize_str(req.proveedor)
        df["_norm"] = df["Proveedor"].apply(_normalize_str)
        df = df[df["_norm"] == prov_norm].drop(columns=["_norm"])
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontraron OCs para el proveedor '{req.proveedor}'."
            )

    proveedores = sorted(df["Proveedor"].dropna().unique().tolist())
    results     = []

    for proveedor in proveedores:
        df_prov     = df[df["Proveedor"] == proveedor]
        excel_bytes = _generate_excel(df_prov)
        safe_name   = re.sub(r'[\\/*?:"<>|]', "_", proveedor)
        filename    = f"OC_{safe_name}.xlsx"

        result = send_supplier_email(
            supplier    = proveedor,
            email_to    = req.to,
            cc          = req.cc,
            subject     = req.subject,
            excel_bytes = excel_bytes,
            body        = f"{req.body}\n\nProveedor: {proveedor}",
            filename    = filename,
        )
        results.append({"supplier": proveedor, **result})
        log.info("Email → %s | proveedor: %s | status: %s",
                 req.to, proveedor, result.get("status"))

    sent   = sum(1 for r in results if r.get("status") == "sent")
    errors = len(results) - sent

    return {
        "sent":        sent,
        "errors":      errors,
        "total_proveedores": len(proveedores),
        "detail":      results,
    }
