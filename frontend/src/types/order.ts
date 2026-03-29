export type RiskLevel = "En plazo" | "En riesgo" | "Crítico";

export interface Order {
  id:            number;
  oc_pos:        string;
  proveedor:     string;       // empresa externa (columna "Proveedor" del Excel)
  comprador_oc:  string;       // persona interna (columna "Comprador OC")
  descripcion:   string;
  material:      string;
  fe_segun_oc:   string | null;
  ultima_fe:     string | null;
  prioridad:     string;
  estado:        string;
  motivo_estado: string | null;
  comentarios:   string | null;
  dias_retraso:  number;
  ai_risk:       RiskLevel;
  ai_summary:    string | null;
}

export interface UploadSummary {
  total:     number;
  suppliers: number;
  delayed:   number;
  critical:  number;
}

export interface Supplier {
  name:  string;
  email: string;
}
