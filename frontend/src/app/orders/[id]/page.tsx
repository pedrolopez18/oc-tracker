"use client";
import { useEffect, useState } from "react";
import { getOcDetail } from "@/lib/api";
import { Order } from "@/types/order";
import { riskBadge, priorityBadge, formatDate, cn } from "@/lib/utils";
import { ArrowLeft, Building2, User, Calendar, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import Link from "next/link";

function RiskIcon({ risk }: { risk: string }) {
  if (risk === "Crítico")   return <AlertTriangle size={16} className="text-red-500" />;
  if (risk === "En riesgo") return <Clock size={16} className="text-amber-500" />;
  return <CheckCircle2 size={16} className="text-green-500" />;
}

function Field({ label, value, mono = false }: { label: string; value?: string | null; mono?: boolean }) {
  return (
    <div>
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">{label}</p>
      <p className={cn("text-sm text-gray-800", mono && "font-mono")}>{value || "—"}</p>
    </div>
  );
}

export default function OrderDetailPage({ params }: { params: { id: string } }) {
  const [order,   setOrder]   = useState<Order | null>(null);
  const [error,   setError]   = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const oc_pos = decodeURIComponent(params.id);
    getOcDetail(oc_pos)
      .then(r => setOrder(r.data))
      .catch(() => setError("No se encontró la OC o el backend no está disponible."))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return (
    <div className="flex items-center justify-center py-20">
      <div className="w-5 h-5 rounded-full border-2 border-brand border-t-transparent animate-spin" />
    </div>
  );

  if (error || !order) return (
    <div className="max-w-2xl">
      <Link href="/" className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-600 mb-5">
        <ArrowLeft size={14} /> Volver
      </Link>
      <div className="card p-8 text-center">
        <p className="text-sm text-gray-500">{error || "OC no encontrada."}</p>
      </div>
    </div>
  );

  return (
    <div className="max-w-3xl space-y-4">
      {/* Breadcrumb */}
      <Link href="/" className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-700 transition-colors w-fit">
        <ArrowLeft size={14} /> Volver al dashboard
      </Link>

      {/* Header card */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">OC / Posición</p>
            <h1 className="text-2xl font-mono font-bold text-gray-900">{order.oc_pos}</h1>
            <p className="text-sm text-gray-500 mt-1">{order.descripcion}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2">
              <RiskIcon risk={order.ai_risk} />
              <span className={cn("badge text-sm px-3 py-1", riskBadge(order.ai_risk))}>
                {order.ai_risk}
              </span>
            </div>
            {order.prioridad && (
              <span className={cn("badge", priorityBadge(order.prioridad))}>
                {order.prioridad}
              </span>
            )}
          </div>
        </div>

        {/* Días de retraso banner */}
        {order.dias_retraso > 0 && (
          <div className={cn(
            "rounded-lg px-4 py-3 mb-5 flex items-center gap-3",
            order.dias_retraso > 15
              ? "bg-red-50 border border-red-200"
              : "bg-amber-50 border border-amber-200"
          )}>
            <AlertTriangle size={16} className={order.dias_retraso > 15 ? "text-red-500" : "text-amber-500"} />
            <p className={cn("text-sm font-semibold",
              order.dias_retraso > 15 ? "text-red-700" : "text-amber-700")}>
              {order.dias_retraso} días de retraso respecto a F.E según OC
            </p>
          </div>
        )}

        {/* Grid de datos */}
        <div className="grid grid-cols-2 gap-x-8 gap-y-4">
          <div className="col-span-2 flex items-center gap-2 pb-2 border-b border-gray-100">
            <Building2 size={14} className="text-gray-400" />
            <span className="text-xs text-gray-400 uppercase tracking-wide">Proveedor</span>
            <span className="text-sm font-semibold text-gray-800 ml-1">{order.proveedor}</span>
          </div>

          <div className="flex items-center gap-2">
            <User size={14} className="text-gray-400" />
            <div>
              <p className="text-xs text-gray-400">Comprador OC</p>
              <p className="text-sm text-gray-700">{order.comprador_oc || "—"}</p>
            </div>
          </div>

          <Field label="Material"     value={order.material} mono />
          <Field label="Estado"       value={order.estado} />
          <Field label="Motivo"       value={order.motivo_estado} />

          <div className="flex items-center gap-2">
            <Calendar size={14} className="text-gray-400" />
            <div>
              <p className="text-xs text-gray-400">F.E según OC</p>
              <p className="text-sm text-gray-700">{formatDate(order.fe_segun_oc)}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Calendar size={14} className="text-gray-400" />
            <div>
              <p className="text-xs text-gray-400">Última confirmada</p>
              <p className="text-sm text-gray-700">{formatDate(order.ultima_fe)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Comentarios */}
      <div className="card p-5">
        <p className="text-sm font-semibold text-gray-700 mb-3">Comentarios de la activación</p>
        {order.comentarios && order.comentarios.trim()
          ? (
            <pre className="text-xs text-gray-600 whitespace-pre-wrap leading-relaxed
                            font-mono bg-gray-50 rounded-lg p-4 border border-gray-100">
              {order.comentarios}
            </pre>
          )
          : <p className="text-xs text-gray-400 italic">Sin comentarios registrados.</p>
        }
      </div>
    </div>
  );
}
