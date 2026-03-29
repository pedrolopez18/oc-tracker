"use client";

const ITEMS = [
  { dot: "bg-green-500", label: "En plazo",  desc: "0 días de atraso" },
  { dot: "bg-amber-400", label: "En riesgo", desc: "1 – 15 días de atraso" },
  { dot: "bg-red-500",   label: "Crítico",   desc: "Más de 15 días de atraso" },
];

export function RiskLegend() {
  return (
    <div className="flex items-center gap-4 flex-wrap px-3 py-2 bg-white rounded-lg border border-gray-200 text-xs text-gray-500 w-fit">
      <span className="font-semibold text-gray-600 mr-1">Riesgo:</span>
      {ITEMS.map(({ dot, label, desc }) => (
        <span key={label} className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${dot} flex-shrink-0`} />
          <span className="font-medium text-gray-700">{label}</span>
          <span className="text-gray-400">({desc})</span>
        </span>
      ))}
    </div>
  );
}
