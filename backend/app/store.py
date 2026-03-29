"""
Store en memoria — persiste el DataFrame del último Excel subido
durante la vida del proceso FastAPI.

Por qué existe este módulo:
- Render free tier tiene filesystem efímero (se borra al reiniciar).
- load_master_df() lee desde disco → falla si el contenedor se reinició.
- Guardando el df en memoria, upload y chat comparten los datos
  mientras el proceso esté vivo, sin tocar disco en cada request.

Limitación conocida: si Render reinicia el contenedor (inactividad >15 min
en free tier), el store se vacía y el usuario debe volver a subir el Excel.
"""
from __future__ import annotations
import pandas as pd
from typing import Optional


class _DataStore:
    """Singleton — una única instancia compartida por todos los módulos."""

    def __init__(self) -> None:
        self._df:          Optional[pd.DataFrame] = None
        self._summary:     dict                   = {}
        self._proveedores: list[str]              = []

    # ── Escritura (llamada desde upload.py) ───────────────────────────────────

    def set(
        self,
        df:          pd.DataFrame,
        summary:     dict,
        proveedores: list[str],
    ) -> None:
        self._df          = df.copy()
        self._summary     = dict(summary)
        self._proveedores = list(proveedores)

    # ── Lectura (llamada desde chat.py) ───────────────────────────────────────

    @property
    def df(self) -> Optional[pd.DataFrame]:
        return self._df

    @property
    def summary(self) -> dict:
        return self._summary

    @property
    def proveedores(self) -> list[str]:
        return self._proveedores

    @property
    def has_data(self) -> bool:
        return self._df is not None and not self._df.empty


# Instancia única importada por upload.py y chat.py
data_store = _DataStore()
