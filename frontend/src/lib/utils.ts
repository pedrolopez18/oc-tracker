import { type ClassValue, clsx } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function riskColor(risk: string) {
  return {
    "Crítico":   "border-l-red-500   bg-red-50/40",
    "En riesgo": "border-l-amber-400 bg-amber-50/30",
    "En plazo":  "border-l-green-500",
  }[risk] ?? "";
}

export function riskBadge(risk: string) {
  return {
    "Crítico":   "bg-red-100   text-red-800   border border-red-200",
    "En riesgo": "bg-amber-100 text-amber-800 border border-amber-200",
    "En plazo":  "bg-green-100 text-green-800 border border-green-200",
  }[risk] ?? "bg-gray-100 text-gray-600 border border-gray-200";
}

export function priorityBadge(p: string) {
  const pu = (p ?? "").toUpperCase().trim();
  if (pu === "CRITICO" || pu === "CRÍTICO" || pu === "URGENTE")
    return "bg-red-100 text-red-800 border border-red-200";
  if (pu === "MIPAYA" || pu === "PPL")
    return "bg-amber-100 text-amber-800 border border-amber-200";
  if (pu === "LABORATORIO")
    return "bg-blue-100 text-blue-800 border border-blue-200";
  if (pu === "NORMAL" || pu === "NO" || pu === "N")
    return "bg-gray-100 text-gray-600 border border-gray-200";
  if (!pu)
    return "bg-gray-100 text-gray-400 border border-gray-200";
  return "bg-purple-50 text-purple-700 border border-purple-200";
}

export function estadoBadge(estado: string) {
  const e = (estado ?? "").toLowerCase();
  if (!e || e === "nan" || e === "") return "bg-gray-100 text-gray-400 border border-gray-200";
  if (e.includes("entregado") || e.includes("cerrado") || e.includes("clsd") || e.includes("complet") || e.includes("recibido"))
    return "bg-green-100 text-green-800 border border-green-200";
  if (e.includes("proceso") || e.includes("tránsito") || e.includes("transit") || e.includes("curso"))
    return "bg-blue-100 text-blue-800 border border-blue-200";
  if (e.includes("pendiente") || e.includes("abierto") || e.includes("open") || e.includes("espera"))
    return "bg-amber-100 text-amber-800 border border-amber-200";
  if (e.includes("cancel") || e.includes("rechaz") || e.includes("error"))
    return "bg-red-100 text-red-800 border border-red-200";
  return "bg-gray-100 text-gray-700 border border-gray-200";
}

export function formatDate(d: string | null | undefined) {
  if (!d) return "—";
  try {
    return new Date(d + "T12:00:00").toLocaleDateString("es-PE", {
      day: "2-digit", month: "2-digit", year: "numeric",
    });
  } catch {
    return d;
  }
}
