"use client";
import { Package, Clock, AlertTriangle, Building2 } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";

interface Props { total: number; delayed: number; critical: number; suppliers: number }

export function MetricsRow({ total, delayed, critical, suppliers }: Props) {
  const delayedPct  = total > 0 ? Math.round(delayed  / total * 100) : 0;
  const criticalPct = total > 0 ? Math.round(critical / total * 100) : 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <MetricCard
        label="Total OCs"
        value={total}
        variant="info"
        icon={<Package size={18} />}
      />
      <MetricCard
        label="Con retraso"
        value={delayed}
        variant="warning"
        subtitle={total > 0 ? `${delayedPct}% del total` : undefined}
        icon={<Clock size={18} />}
      />
      <MetricCard
        label="Críticas +15d"
        value={critical}
        variant="danger"
        subtitle={total > 0 ? `${criticalPct}% del total` : undefined}
        icon={<AlertTriangle size={18} />}
      />
      <MetricCard
        label="Proveedores"
        value={suppliers}
        variant="default"
        icon={<Building2 size={18} />}
      />
    </div>
  );
}
