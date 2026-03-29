"use client";
import { useEffect, useState } from "react";
import ReactSelect, { type SingleValue, type StylesConfig } from "react-select";
import { cn } from "@/lib/utils";

interface Filters {
  supplier:      string;
  priority:      string;
  risk:          string;
  search:        string;
  only_critical: boolean;
}

interface Props {
  filters:    Filters;
  suppliers:  string[];
  priorities: string[];
  onChange:   (f: Filters) => void;
}

type Opt = { value: string; label: string };

// ── Estilos de react-select para coincidir con el design system ───────────────
// Usamos la prop `styles` (CSS-in-JS) en lugar de classNames para máximo control
// sin necesidad de configurar Tailwind para purgar clases dinámicas de librerías.

function buildStyles(isFocused: boolean): StylesConfig<Opt, false> {
  return {
    // Contenedor externo
    container: base => ({
      ...base,
      minWidth: "220px",
    }),
    // El "input" visible (la caja)
    control: (base, state) => ({
      ...base,
      minHeight: "38px",
      borderRadius: "0.5rem",          // rounded-lg
      borderColor: state.isFocused ? "#003087" : "#e5e7eb",
      borderWidth: "1px",
      boxShadow: state.isFocused ? "0 0 0 3px rgba(0,48,135,0.10)" : "none",
      backgroundColor: "#ffffff",
      paddingLeft: "4px",
      paddingRight: "2px",
      cursor: "pointer",
      transition: "border-color 150ms, box-shadow 150ms",
      "&:hover": { borderColor: state.isFocused ? "#003087" : "#d1d5db" },
    }),
    // Texto del placeholder
    placeholder: base => ({
      ...base,
      color: "#9ca3af",
      fontSize: "0.875rem",
    }),
    // Valor seleccionado
    singleValue: base => ({
      ...base,
      color: "#1f2937",
      fontSize: "0.875rem",
      fontWeight: 500,
    }),
    // Campo de texto para buscar
    input: base => ({
      ...base,
      color: "#1f2937",
      fontSize: "0.875rem",
    }),
    // Dropdown container
    menu: base => ({
      ...base,
      borderRadius: "0.75rem",
      border: "1px solid #e5e7eb",
      boxShadow: "0 20px 25px -5px rgba(0,0,0,0.10), 0 8px 10px -6px rgba(0,0,0,0.08)",
      marginTop: "4px",
      overflow: "hidden",
      zIndex: 100,
    }),
    // Lista de opciones
    menuList: base => ({
      ...base,
      padding: "4px",
      maxHeight: "260px",
    }),
    // Cada opción
    option: (base, state) => ({
      ...base,
      borderRadius: "0.5rem",
      fontSize: "0.875rem",
      padding: "8px 12px",
      cursor: "pointer",
      backgroundColor: state.isSelected
        ? "#003087"
        : state.isFocused
        ? "#f0f4fb"
        : "transparent",
      color: state.isSelected ? "#ffffff" : "#374151",
      fontWeight: state.isSelected ? 600 : 400,
      "&:active": { backgroundColor: state.isSelected ? "#002060" : "#e8eef8" },
    }),
    // Sin separador entre valor y flechas
    indicatorSeparator: () => ({ display: "none" }),
    // Flecha desplegable
    dropdownIndicator: base => ({
      ...base,
      color: "#9ca3af",
      padding: "0 6px",
      "&:hover": { color: "#6b7280" },
    }),
    // Botón "×" para limpiar
    clearIndicator: base => ({
      ...base,
      color: "#d1d5db",
      padding: "0 4px",
      "&:hover": { color: "#ef4444" },
    }),
    // Sin resultados
    noOptionsMessage: base => ({
      ...base,
      color: "#9ca3af",
      fontSize: "0.875rem",
      padding: "12px",
    }),
  };
}

// ── Componente ────────────────────────────────────────────────────────────────

export function FilterBar({ filters, suppliers, priorities, onChange }: Props) {
  const set = (key: keyof Filters, val: any) => onChange({ ...filters, [key]: val });

  // Construir opciones para react-select
  const supplierOptions: Opt[] = suppliers.map(s => ({ value: s, label: s }));

  // Valor actual como Opt | null (react-select necesita el objeto, no solo el string)
  const selectedSupplier: Opt | null =
    filters.supplier ? { value: filters.supplier, label: filters.supplier } : null;

  const handleSupplierChange = (opt: SingleValue<Opt>) => {
    set("supplier", opt?.value ?? "");
  };

  return (
    <div className="flex gap-2 flex-wrap items-center mb-3 p-3 bg-white rounded-xl border border-gray-200">

      {/* ── Proveedor — react-select con búsqueda ─────────────────────── */}
      <ReactSelect<Opt, false>
        instanceId="supplier-select"   // evita warning de SSR hydration
        options={supplierOptions}
        value={selectedSupplier}
        onChange={handleSupplierChange}
        placeholder="Todos los proveedores"
        isClearable
        isSearchable
        noOptionsMessage={() => "Sin coincidencias"}
        styles={buildStyles(false)}
      />

      {/* ── Prioridad ──────────────────────────────────────────────────── */}
      <select
        className="input text-sm"
        value={filters.priority}
        onChange={e => set("priority", e.target.value)}
      >
        <option value="">Todas las prioridades</option>
        {priorities.map(p => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      {/* ── Riesgo ─────────────────────────────────────────────────────── */}
      <select
        className="input text-sm"
        value={filters.risk}
        onChange={e => set("risk", e.target.value)}
      >
        <option value="">Todos los riesgos</option>
        <option value="Crítico">🔴 Crítico</option>
        <option value="En riesgo">🟡 En riesgo</option>
        <option value="En plazo">🟢 En plazo</option>
      </select>

      {/* ── Búsqueda libre ─────────────────────────────────────────────── */}
      <input
        className="input flex-1 min-w-[200px]"
        placeholder="Buscar OC, material, descripción..."
        value={filters.search}
        onChange={e => set("search", e.target.value)}
      />

      {/* ── Solo críticas ──────────────────────────────────────────────── */}
      <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer px-2 py-1.5 rounded-lg hover:bg-gray-50 border border-gray-200 select-none whitespace-nowrap">
        <input
          type="checkbox"
          checked={filters.only_critical}
          onChange={e => set("only_critical", e.target.checked)}
          className="accent-red-500"
        />
        Solo críticas
      </label>
    </div>
  );
}
