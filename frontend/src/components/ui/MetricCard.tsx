import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface Props {
  label:     string;
  value:     number | string;
  variant?:  "default" | "danger" | "warning" | "success" | "info";
  icon?:     ReactNode;
  subtitle?: string;
}

const styles = {
  default: { bar: "bg-gray-400",   value: "text-gray-800",   bg: "bg-gray-50/60",    icon: "bg-gray-100 text-gray-500" },
  danger:  { bar: "bg-red-500",    value: "text-red-600",    bg: "bg-red-50/60",     icon: "bg-red-100 text-red-500" },
  warning: { bar: "bg-amber-400",  value: "text-amber-600",  bg: "bg-amber-50/60",   icon: "bg-amber-100 text-amber-500" },
  success: { bar: "bg-green-500",  value: "text-green-600",  bg: "bg-green-50/60",   icon: "bg-green-100 text-green-600" },
  info:    { bar: "bg-brand",      value: "text-brand",      bg: "bg-brand-light/40", icon: "bg-brand/10 text-brand" },
};

export function MetricCard({ label, value, variant = "default", icon, subtitle }: Props) {
  const s = styles[variant];
  return (
    <div className={cn(
      "bg-white rounded-2xl p-5 border border-gray-200 shadow-sm relative overflow-hidden transition-shadow hover:shadow-md",
      s.bg
    )}>
      {/* Left color bar */}
      <div className={cn("absolute left-0 top-0 bottom-0 w-1.5 rounded-l-2xl", s.bar)} />

      <div className="flex items-start justify-between pl-2">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 leading-none">
            {label}
          </p>
          <p className={cn("text-4xl font-bold tabular-nums leading-none", s.value)}>
            {typeof value === "number" ? value.toLocaleString("es") : value}
          </p>
          {subtitle && (
            <p className="text-xs text-gray-400 mt-2 leading-none">{subtitle}</p>
          )}
        </div>

        {icon && (
          <div className={cn("p-2.5 rounded-xl shrink-0", s.icon)}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
