"use client";
import { useState, useRef, useEffect, type ReactNode } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type ColumnFiltersState,
  type Column,
} from "@tanstack/react-table";
import Link from "next/link";
import { Order } from "@/types/order";
import { riskBadge, riskColor, priorityBadge, estadoBadge, formatDate, cn } from "@/lib/utils";

// ── Tooltip (CSS-only, no JS overhead) ───────────────────────────────────────
// Aparece arriba del texto al hacer hover. Usa group-hover/tip de Tailwind v3.2+

function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  if (!text || text === "—") return <>{children}</>;
  return (
    <div className="relative group/tip">
      {children}
      <div
        className={cn(
          // Oculto por defecto → visible en hover
          "pointer-events-none absolute bottom-full left-0 mb-2 z-[300]",
          "opacity-0 group-hover/tip:opacity-100",
          "transition-opacity duration-150",
          // Estilo del tooltip
          "bg-gray-900 text-white text-xs rounded-xl px-3 py-2.5",
          "shadow-xl w-max max-w-[360px] whitespace-normal leading-relaxed"
        )}
      >
        {text}
        {/* Flecha apuntando hacia abajo */}
        <span className="absolute top-full left-5 -translate-y-px border-4 border-transparent border-t-gray-900" />
      </div>
    </div>
  );
}

// ── Column filter + sort dropdown ─────────────────────────────────────────────

function ColMenu({ column }: { column: Column<Order, unknown> }) {
  const [open, setOpen]   = useState(false);
  const ref               = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);

  const sorted    = column.getIsSorted();
  const filterVal = (column.getFilterValue() as string) ?? "";
  const isActive  = filterVal.length > 0 || !!sorted;

  return (
    <div ref={ref} className="relative inline-flex">
      <button
        onClick={() => setOpen(o => !o)}
        title="Ordenar / Filtrar"
        className={cn(
          "ml-1 w-5 h-5 rounded text-[11px] leading-none flex items-center justify-center transition-colors",
          isActive ? "text-brand bg-brand/10" : "text-gray-300 hover:text-gray-500 hover:bg-gray-100"
        )}
      >
        {sorted === "asc" ? "↑" : sorted === "desc" ? "↓" : "⇅"}
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-52 z-[200] bg-white rounded-xl border border-gray-200 shadow-2xl overflow-hidden">
          <div className="p-1.5 border-b border-gray-100">
            <button
              className={cn("w-full text-left text-xs px-3 py-2 rounded-lg hover:bg-gray-50 flex items-center gap-2", sorted === "asc" && "bg-brand/5 text-brand font-semibold")}
              onClick={() => { column.toggleSorting(false); setOpen(false); }}
            >
              <span>↑</span> Ordenar A → Z
            </button>
            <button
              className={cn("w-full text-left text-xs px-3 py-2 rounded-lg hover:bg-gray-50 flex items-center gap-2", sorted === "desc" && "bg-brand/5 text-brand font-semibold")}
              onClick={() => { column.toggleSorting(true); setOpen(false); }}
            >
              <span>↓</span> Ordenar Z → A
            </button>
            {sorted && (
              <button
                className="w-full text-left text-xs px-3 py-2 rounded-lg hover:bg-gray-50 text-gray-400 flex items-center gap-2"
                onClick={() => { column.clearSorting(); setOpen(false); }}
              >
                <span>↕</span> Quitar orden
              </button>
            )}
          </div>

          {column.getCanFilter() && (
            <div className="p-2">
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider px-1 mb-1.5">
                Filtrar columna
              </p>
              <input
                autoFocus
                value={filterVal}
                onChange={e => column.setFilterValue(e.target.value)}
                placeholder="Buscar en esta columna..."
                className="w-full text-xs border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-brand/60 focus:ring-1 focus:ring-brand/20"
                onClick={e => e.stopPropagation()}
              />
              {filterVal && (
                <button
                  className="mt-1.5 text-[11px] text-red-500 hover:text-red-700 px-1"
                  onClick={() => column.setFilterValue("")}
                >
                  ✕ Quitar filtro
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Mobile card ───────────────────────────────────────────────────────────────

function MobileCard({ o }: { o: Order }) {
  return (
    <div className={cn(
      "bg-white rounded-xl border border-l-4 border-gray-200 p-4 shadow-sm",
      riskColor(o.ai_risk)
    )}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <Link
          href={`/orders/${encodeURIComponent(o.oc_pos)}`}
          className="font-mono text-xs font-bold text-brand hover:underline"
        >
          {o.oc_pos}
        </Link>
        <span className={cn("badge shrink-0", riskBadge(o.ai_risk))}>{o.ai_risk}</span>
      </div>
      <p className="text-sm font-semibold text-gray-800 truncate">{o.proveedor}</p>
      {/* Descripción completa en móvil — 3 líneas máximo */}
      <p className="text-xs text-gray-500 line-clamp-3 mt-0.5 leading-relaxed">
        {o.descripcion || "—"}
      </p>
      <div className="mt-3 flex gap-x-4 gap-y-1 flex-wrap text-xs text-gray-500">
        <span>FE OC: {formatDate(o.fe_segun_oc)}</span>
        {o.ultima_fe && <span>Conf.: {formatDate(o.ultima_fe)}</span>}
      </div>
      <div className="mt-2 flex items-center gap-2 flex-wrap">
        {o.prioridad && (
          <span className={cn("badge", priorityBadge(o.prioridad))}>{o.prioridad}</span>
        )}
        {o.estado && o.estado !== "nan" && (
          <span className={cn("badge truncate max-w-[140px]", estadoBadge(o.estado))} title={o.estado}>
            {o.estado}
          </span>
        )}
        <span className={cn(
          "ml-auto text-xs font-bold",
          o.dias_retraso > 15 ? "text-red-600" : o.dias_retraso > 0 ? "text-amber-600" : "text-green-600"
        )}>
          {o.dias_retraso > 0 ? `+${o.dias_retraso}d` : "En plazo"}
        </span>
      </div>
    </div>
  );
}

// ── Column definitions ────────────────────────────────────────────────────────

const ch = createColumnHelper<Order>();

const COLUMNS = [
  // ── OC/POS — ancho fijo, fuente mono
  ch.accessor("oc_pos", {
    header: "OC/POS",
    filterFn: "includesString",
    cell: i => (
      <Link
        href={`/orders/${encodeURIComponent(i.getValue())}`}
        className="font-mono text-xs font-bold text-brand hover:underline whitespace-nowrap"
      >
        {i.getValue()}
      </Link>
    ),
  }),

  // ── Proveedor — truncado con tooltip
  ch.accessor("proveedor", {
    header: "Proveedor",
    filterFn: "includesString",
    cell: i => {
      const val = i.getValue();
      return (
        <Tooltip text={val}>
          <span className="font-medium text-gray-800 max-w-[200px] truncate block">
            {val}
          </span>
        </Tooltip>
      );
    },
  }),

  // ── Descripción — columna ANCHA, 2 líneas + tooltip completo
  ch.accessor("descripcion", {
    header: "Descripción",
    filterFn: "includesString",
    cell: i => {
      const val = i.getValue() || "—";
      return (
        <Tooltip text={val !== "—" ? val : ""}>
          {/* min-w fuerza la columna a ser más ancha que las demás */}
          <div className="min-w-[300px] max-w-[420px]">
            <span className={cn(
              "text-gray-600 text-sm leading-snug block",
              // 2 líneas máximo, con "..." al final si se corta
              "overflow-hidden",
              "[display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2]"
            )}>
              {val}
            </span>
          </div>
        </Tooltip>
      );
    },
  }),

  // ── Fechas — compactas, sin wrap
  ch.accessor("fe_segun_oc", {
    header: "F.E según OC",
    filterFn: "includesString",
    cell: i => (
      <span className="text-gray-500 whitespace-nowrap text-xs">
        {formatDate(i.getValue())}
      </span>
    ),
  }),
  ch.accessor("ultima_fe", {
    header: "Últ. confirmada",
    filterFn: "includesString",
    cell: i => (
      <span className="text-gray-500 whitespace-nowrap text-xs">
        {formatDate(i.getValue())}
      </span>
    ),
  }),

  // ── Prioridad — badge
  ch.accessor("prioridad", {
    header: "Prioridad",
    filterFn: "includesString",
    cell: i => i.getValue()
      ? <span className={cn("badge whitespace-nowrap", priorityBadge(i.getValue()))}>{i.getValue()}</span>
      : <span className="text-gray-300 text-xs">—</span>,
  }),

  // ── Estado — badge truncado con tooltip
  ch.accessor("estado", {
    header: "Estado",
    filterFn: "includesString",
    cell: i => {
      const val = i.getValue();
      if (!val || val === "nan") return <span className="text-gray-300 text-xs">—</span>;
      return (
        <Tooltip text={val}>
          <span className={cn("badge truncate block max-w-[160px]", estadoBadge(val))}>
            {val}
          </span>
        </Tooltip>
      );
    },
  }),

  // ── Riesgo — badge
  ch.accessor("ai_risk", {
    header: "Riesgo",
    filterFn: "includesString",
    cell: i => (
      <span className={cn("badge whitespace-nowrap", riskBadge(i.getValue()))}>
        {i.getValue()}
      </span>
    ),
  }),

  // ── Días retraso — solo sort, sin filtro de texto
  ch.accessor("dias_retraso", {
    header: "Días retraso",
    enableColumnFilter: false,
    sortingFn: "basic",
    cell: i => {
      const d = i.getValue();
      return (
        <span className={cn(
          "font-semibold whitespace-nowrap text-xs tabular-nums",
          d > 15 ? "text-red-600" : d > 0 ? "text-amber-600" : "text-green-600"
        )}>
          {d > 0 ? `+${d}d` : "En plazo"}
        </span>
      );
    },
  }),
];

// ── Main component ────────────────────────────────────────────────────────────

export function OCTable({ orders }: { orders: Order[] }) {
  const [sorting,       setSorting]       = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  const table = useReactTable({
    data:                  orders,
    columns:               COLUMNS,
    state:                 { sorting, columnFilters },
    onSortingChange:       setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel:       getCoreRowModel(),
    getSortedRowModel:     getSortedRowModel(),
    getFilteredRowModel:   getFilteredRowModel(),
  });

  const rows         = table.getRowModel().rows;
  const hasColFilter = columnFilters.length > 0;

  if (!orders.length) {
    return (
      <div className="card p-12 text-center">
        <p className="text-sm text-gray-400">Sin resultados para los filtros aplicados.</p>
        <p className="text-xs text-gray-300 mt-1">Sube un Excel o ajusta los filtros.</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      {/* Banner cuando hay filtros de columna activos */}
      {hasColFilter && (
        <div className="px-4 py-2 border-b border-brand/10 bg-brand/5 flex items-center justify-between">
          <span className="text-xs text-brand font-medium">
            {columnFilters.length} filtro{columnFilters.length > 1 ? "s" : ""} de columna activo{columnFilters.length > 1 ? "s" : ""}
          </span>
          <button
            onClick={() => setColumnFilters([])}
            className="text-xs text-red-500 hover:text-red-700 font-medium"
          >
            ✕ Quitar todos
          </button>
        </div>
      )}

      {/* ── Mobile: cards ──────────────────────────────────────────────── */}
      <div className="sm:hidden p-3 space-y-3">
        {rows.length === 0
          ? <p className="text-sm text-gray-400 text-center py-6">Sin resultados.</p>
          : rows.map(row => <MobileCard key={row.id} o={row.original} />)
        }
      </div>

      {/* ── Desktop: table ─────────────────────────────────────────────── */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          {/* Header sticky con sombra sutil */}
          <thead className="sticky top-0 z-10 bg-white" style={{ boxShadow: "0 1px 0 0 #e5e7eb" }}>
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id}>
                {hg.headers.map(h => (
                  <th
                    key={h.id}
                    className="px-5 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap select-none bg-gray-50/80"
                  >
                    <div className="flex items-center gap-0.5">
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      <ColMenu column={h.column} />
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>

          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length} className="px-5 py-10 text-center text-sm text-gray-400">
                  Sin resultados para los filtros de columna activos.
                </td>
              </tr>
            ) : (
              rows.map((row, idx) => (
                <tr
                  key={row.id}
                  className={cn(
                    "border-l-4 transition-colors group",
                    // Filas alternas con fondo muy sutil
                    idx % 2 === 0 ? "bg-white" : "bg-gray-50/40",
                    "hover:bg-blue-50/40",
                    riskColor(row.original.ai_risk)
                  )}
                >
                  {row.getVisibleCells().map(cell => (
                    <td
                      key={cell.id}
                      // Padding más generoso + borde inferior suave
                      className="px-5 py-4 border-b border-gray-100"
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100 bg-gray-50/60 flex items-center justify-between">
        <p className="text-xs text-gray-400">
          {rows.length !== orders.length
            ? <><span className="font-semibold text-brand">{rows.length}</span> de {orders.length} órdenes</>
            : <>{orders.length} órdenes</>
          }
        </p>
        {(hasColFilter || sorting.length > 0) && (
          <button
            onClick={() => { setColumnFilters([]); setSorting([]); }}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Restaurar tabla
          </button>
        )}
      </div>
    </div>
  );
}
