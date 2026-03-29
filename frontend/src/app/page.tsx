"use client";
import { useState, useMemo, useEffect, useCallback } from "react";
import { MetricsRow }     from "@/components/dashboard/MetricsRow";
import { UploadDropzone } from "@/components/dashboard/UploadDropzone";
import { ActionBar }      from "@/components/dashboard/ActionBar";
import { EmailModal }     from "@/components/dashboard/EmailModal";
import { ChatBot }        from "@/components/dashboard/ChatBot";
import { FilterBar }      from "@/components/orders/FilterBar";
import { OCTable }        from "@/components/orders/OCTable";
import { RiskLegend }     from "@/components/ui/RiskLegend";
import { getOcs }         from "@/lib/api";
import { Order, RiskLevel } from "@/types/order";

// ─── Claves de localStorage ───────────────────────────────────────────────
const LS_FILTERS   = "oc_filters";
const LS_ORDERS    = "oc_orders";
const LS_SUPPLIERS = "oc_suppliers";

const DEFAULT_FILTERS = {
  supplier:      "",
  priority:      "",
  risk:          "",
  search:        "",
  only_critical: false,
};

// ─── Mapeo fila cruda → Order ─────────────────────────────────────────────
function mapRawToOrder(raw: Record<string, any>, index: number): Order {
  const dias = Number(raw["Días de retraso"] ?? 0) || 0;

  const aiRisk: RiskLevel =
    dias > 15 ? "Crítico" : dias > 0 ? "En riesgo" : "En plazo";

  const toDateStr = (val: any): string | null => {
    if (!val || val === "") return null;
    const s = String(val);
    return /^\d{4}-\d{2}-\d{2}/.test(s) ? s.slice(0, 10) : null;
  };

  const rawPrioridad = String(raw["Prioridad"] ?? "");

  return {
    id:            index,
    oc_pos:        String(raw["OC/POS"]                        ?? ""),
    proveedor:     String(raw["Proveedor"]                     ?? ""),
    comprador_oc:  String(raw["Comprador OC"]                  ?? ""),
    descripcion:   String(raw["Descripción"]                   ?? ""),
    material:      String(raw["Material"]                      ?? ""),
    fe_segun_oc:   toDateStr(raw["F.E según OC"]),
    ultima_fe:     toDateStr(
                     raw["Última F.E confirmada por el proveedor"] ||
                     raw["Fecha Última Modificación."]
                   ),
    prioridad:     rawPrioridad,
    estado:        String(raw["Estado"]                        ?? ""),
    motivo_estado: String(raw["Motivo del estado"]             ?? ""),
    comentarios:   String(raw["Comentarios de la Activación"]  ?? ""),
    dias_retraso:  dias,
    ai_risk:       aiRisk,
    ai_summary:    null,
  };
}

// ─── Componente principal ─────────────────────────────────────────────────
export default function DashboardPage() {
  const [orders,    setOrders]    = useState<Order[]>([]);
  const [suppliers, setSuppliers] = useState<string[]>([]);
  const [filters,   setFilters]   = useState(DEFAULT_FILTERS);
  const [showEmail, setShowEmail] = useState(false);
  const [hydrated,  setHydrated]  = useState(false);

  // ── Restaurar estado desde localStorage al montar ─────────────────
  useEffect(() => {
    try {
      const f = localStorage.getItem(LS_FILTERS);
      if (f) setFilters(JSON.parse(f));
      const s = localStorage.getItem(LS_SUPPLIERS);
      if (s) setSuppliers(JSON.parse(s));
      const o = localStorage.getItem(LS_ORDERS);
      if (o) setOrders(JSON.parse(o));
    } catch { /* ignore */ }
    setHydrated(true);
  }, []);

  // ── Persistir filtros en localStorage cuando cambian ─────────────
  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(LS_FILTERS, JSON.stringify(filters));
  }, [filters, hydrated]);

  // ── Cargar todas las OCs del backend ─────────────────────────────
  const loadAllOcs = useCallback(async () => {
    try {
      const { data } = await getOcs("");
      const rows = (data.data as Record<string, any>[]).map(mapRawToOrder);
      setOrders(rows);
      localStorage.setItem(LS_ORDERS, JSON.stringify(rows));
    } catch { /* backend no disponible */ }
  }, []);

  function handleUploadSuccess(uploadData: any) {
    const provs = uploadData.proveedores ?? [];
    setSuppliers(provs);
    localStorage.setItem(LS_SUPPLIERS, JSON.stringify(provs));
    loadAllOcs();
  }

  // ── Callback del chatbot: actualiza filtros globales ──────────────
  function handleChatFilter(key: string, value: string) {
    if (key === "only_critical") {
      setFilters(prev => ({ ...prev, only_critical: value === "true" }));
    } else {
      // Limpiar filtros relacionados si se pasa vacío en "supplier"
      if (key === "supplier" && value === "") {
        setFilters(DEFAULT_FILTERS);
      } else {
        setFilters(prev => ({ ...prev, [key]: value }));
      }
    }
    // Scroll suave hacia la tabla
    document.getElementById("oc-table-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ── Prioridades únicas para el dropdown ──────────────────────────
  const priorities = useMemo(() =>
    [...new Set(orders.map(o => o.prioridad).filter(Boolean))].sort()
  , [orders]);

  // ── Filtrado en cliente ───────────────────────────────────────────
  const filtered = useMemo(() => orders.filter(o => {
    if (filters.supplier      && o.proveedor   !== filters.supplier) return false;
    if (filters.priority      && o.prioridad   !== filters.priority) return false;
    if (filters.risk          && o.ai_risk     !== filters.risk)     return false;
    if (filters.only_critical && o.dias_retraso <= 15)               return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      if (
        !o.oc_pos.toLowerCase().includes(q) &&
        !o.proveedor.toLowerCase().includes(q) &&
        !o.descripcion.toLowerCase().includes(q) &&
        !o.material.toLowerCase().includes(q)
      ) return false;
    }
    return true;
  }), [orders, filters]);

  // ── KPIs dinámicos ────────────────────────────────────────────────
  const kpis = useMemo(() => ({
    total:     filtered.length,
    delayed:   filtered.filter(o => o.dias_retraso > 0).length,
    critical:  filtered.filter(o => o.dias_retraso > 15).length,
    suppliers: new Set(filtered.map(o => o.proveedor).filter(Boolean)).size,
  }), [filtered]);

  if (!hydrated) return null;

  return (
    <>
      {/* KPIs */}
      <MetricsRow {...kpis} />

      <UploadDropzone onSuccess={handleUploadSuccess} onFileReady={() => {}} />

      <ActionBar
        selectedSupplier={filters.supplier || undefined}
        onSendEmails={() => setShowEmail(true)}
      />

      {/* Filtros globales */}
      <FilterBar filters={filters} suppliers={suppliers} priorities={priorities} onChange={setFilters} />

      {/* Leyenda de riesgo */}
      <div className="mb-3">
        <RiskLegend />
      </div>

      <p className="text-xs text-gray-400 mb-2">{filtered.length} órdenes</p>

      {/* Tabla */}
      <div id="oc-table-section">
        <OCTable orders={filtered} />
      </div>

      {showEmail && (
        <EmailModal
          onClose={() => setShowEmail(false)}
          selectedSupplier={filters.supplier}
          allSuppliers={suppliers}
        />
      )}

      {/* Chatbot con integración de filtros */}
      <ChatBot
        onFilterChange={handleChatFilter}
        suppliers={suppliers}
      />
    </>
  );
}
