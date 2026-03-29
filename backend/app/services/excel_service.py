import pandas as pd
import io
import uuid
from fastapi import HTTPException
from datetime import datetime

# Columnas mínimas que parse_excel necesita (para el ZIP por proveedor)
REQUIRED_COLUMNS = [
    "OC", "OC/POS", "Fecha doc.", "Centro", "Material",
    "Descripción", "UMP", "Cant. de pedido", "Por entregar",
    "Proveedor",       # empresa externa
    "Comprador OC",    # persona interna
    "F.E según OC",
    "Última F.E confirmada por el proveedor",
    "Estado", "Motivo del estado", "Días de retraso"
]

COLUMN_MAP = {
    "OC": "oc", "Pos": "pos", "OC/POS": "oc_pos",
    "Fecha doc.": "fecha_doc", "Centro": "centro",
    "Material": "material", "Descripción": "descripcion",
    "UMP": "ump", "Cant. de pedido": "cant_pedido",
    "Por entregar": "por_entregar",
    "Proveedor": "proveedor",
    "Comprador OC": "comprador_oc",
    "F.E según OC": "fe_segun_oc",
    "Última F.E confirmada por el proveedor": "ultima_fe",
    "Prioridad": "prioridad",
    "Comentarios de la Activación": "comentarios",
    "Estado": "estado", "Motivo del estado": "motivo_estado",
    "Días de retraso": "dias_retraso"
}


def parse_excel(file_bytes: bytes) -> tuple[pd.DataFrame, str]:
    """Lee el Excel original. Retorna (DataFrame, batch_id)."""
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl",
                           sheet_name="Base", header=5)
        df.columns = df.columns.astype(str).str.strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"No se pudo leer el archivo: {e}")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Columnas faltantes en el Excel: {missing}"
        )

    # Recalcular días de retraso siempre
    today = pd.Timestamp.now().normalize()
    fe    = pd.to_datetime(df["F.E según OC"], errors="coerce")
    df["Días de retraso"] = (today - fe).dt.days.clip(lower=0).fillna(0).astype(int)

    for col in ["Fecha doc.", "F.E según OC",
                "Última F.E confirmada por el proveedor"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["Proveedor"] = df["Proveedor"].astype(str).str.strip()

    batch_id = str(uuid.uuid4())
    return df, batch_id


def classify_risk(dias_retraso: int) -> str:
    if dias_retraso > 15:
        return "Crítico"
    elif dias_retraso > 0:
        return "En riesgo"
    return "En plazo"


def df_to_records(df: pd.DataFrame, batch_id: str) -> list[dict]:
    """Convierte DataFrame a lista de dicts para DB."""
    dias = pd.to_numeric(df.get("Días de retraso", 0), errors="coerce").fillna(0).astype(int)

    def _str(col: str) -> pd.Series:
        return df[col].astype(str).fillna("") if col in df.columns else pd.Series([""] * len(df))

    def _date(col: str) -> pd.Series:
        s = pd.to_datetime(df[col], errors="coerce") if col in df.columns else pd.Series([None] * len(df))
        return s.where(s.notna(), other=None)

    records_df = pd.DataFrame({
        "batch_id":      batch_id,
        "oc":            _str("OC"),
        "pos":           _str("Pos"),
        "oc_pos":        _str("OC/POS"),
        "fecha_doc":     _date("Fecha doc."),
        "centro":        _str("Centro"),
        "material":      _str("Material"),
        "descripcion":   _str("Descripción"),
        "ump":           _str("UMP"),
        "cant_pedido":   df.get("Cant. de pedido"),
        "por_entregar":  df.get("Por entregar"),
        "proveedor":     _str("Proveedor"),
        "comprador_oc":  _str("Comprador OC"),
        "fe_segun_oc":   _date("F.E según OC"),
        "ultima_fe":     _date("Última F.E confirmada por el proveedor"),
        "prioridad":     _str("Prioridad"),
        "comentarios":   _str("Comentarios de la Activación"),
        "estado":        _str("Estado"),
        "motivo_estado": _str("Motivo del estado"),
        "dias_retraso":  dias,
        "ai_risk":       dias.apply(classify_risk),
    })
    return records_df.to_dict(orient="records")


def generate_supplier_excel(df: pd.DataFrame, proveedor: str) -> bytes:
    """Genera Excel para un proveedor con fechas formateadas (sin timestamps)."""
    df_prov = df[df["Proveedor"] == proveedor].copy()

    # Convertir columnas datetime a solo fecha (evita timestamps en el Excel)
    for col in df_prov.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        df_prov[col] = df_prov[col].dt.strftime("%d/%m/%Y").where(df_prov[col].notna(), other=None)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_prov.to_excel(writer, index=False, sheet_name="Seguimiento OC")
        ws = writer.sheets["Seguimiento OC"]
        for col in ws.columns:
            max_len = max(
                (len(str(cell.value or "")) for cell in col), default=10
            )
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)
    return output.getvalue()


def split_by_supplier(df: pd.DataFrame) -> dict[str, bytes]:
    """Genera un Excel por cada proveedor (empresa externa)."""
    proveedores = [p for p in df["Proveedor"].dropna().unique() if str(p).strip()]
    return {p: generate_supplier_excel(df, p) for p in proveedores}
