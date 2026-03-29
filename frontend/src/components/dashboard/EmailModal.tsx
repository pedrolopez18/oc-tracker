"use client";
import { useState } from "react";
import { X, Send, AlertCircle, CheckCircle2, Users, User } from "lucide-react";
import { sendEmails } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  onClose:          () => void;
  selectedSupplier?: string;   // proveedor seleccionado en el dropdown (o vacío = todos)
  allSuppliers:     string[];  // lista completa para mostrar conteo
}

type Step = "form" | "confirm" | "result";

const DEFAULT_SUBJECT = "Seguimiento de órdenes de compra — Pluspetrol";
const DEFAULT_BODY    =
  "Estimado proveedor,\n\nAdjunto encontrará el seguimiento actualizado de sus órdenes de compra.\n\nQuedamos atentos a sus consultas.\n\nSaludos cordiales,\nEquipo Supply Chain — Pluspetrol";

export function EmailModal({ onClose, selectedSupplier, allSuppliers }: Props) {
  const [step,    setStep]    = useState<Step>("form");
  const [form,    setForm]    = useState({
    to:      "",
    cc:      "",
    subject: DEFAULT_SUBJECT,
    body:    DEFAULT_BODY,
  });
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState<any>(null);
  const [error,   setError]   = useState("");

  const setField = (k: keyof typeof form, v: string) =>
    setForm(f => ({ ...f, [k]: v }));

  // ¿A quién se enviará?
  const targetSupplier = selectedSupplier?.trim() || "";
  const targetCount    = targetSupplier ? 1 : allSuppliers.length;
  const targetLabel    = targetSupplier
    ? targetSupplier
    : `${allSuppliers.length} proveedor${allSuppliers.length !== 1 ? "es" : ""}`;

  function goToConfirm() {
    if (!form.to.trim()) { setError("El campo 'Para' es obligatorio."); return; }
    setError("");
    setStep("confirm");
  }

  async function handleSend() {
    setLoading(true);
    setError("");
    try {
      const { data } = await sendEmails({
        to:        form.to,
        cc:        form.cc,
        subject:   form.subject,
        body:      form.body,
        proveedor: targetSupplier,   // vacío = todos
      });
      setResult(data);
      setStep("result");
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Error al enviar correos.";
      setError(detail);
      setStep("form");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
          <div className="flex items-center gap-2">
            <Send size={16} className="text-brand" />
            <h2 className="text-base font-semibold text-gray-800">Enviar correos a proveedores</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Destinatario resumen (siempre visible) */}
        <div className={cn(
          "mx-6 mt-4 px-4 py-3 rounded-lg flex items-center gap-3 text-sm flex-shrink-0",
          targetSupplier
            ? "bg-brand/5 border border-brand/20"
            : "bg-gray-50 border border-gray-200"
        )}>
          {targetSupplier
            ? <User  size={16} className="text-brand flex-shrink-0" />
            : <Users size={16} className="text-gray-500 flex-shrink-0" />
          }
          <div>
            <p className="font-medium text-gray-800">
              {targetSupplier ? "Proveedor seleccionado" : "Todos los proveedores"}
            </p>
            <p className="text-gray-500 text-xs mt-0.5 truncate max-w-[320px]">
              {targetLabel}
            </p>
          </div>
        </div>

        {/* Contenido scrollable */}
        <div className="px-6 py-4 overflow-y-auto flex-1">

          {/* ── STEP: form ── */}
          {step === "form" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">
                  Enviar a <span className="text-red-400">*</span>
                </label>
                <input
                  className="input w-full"
                  placeholder="correo@empresa.com"
                  value={form.to}
                  onChange={e => setField("to", e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">CC (opcional)</label>
                <input
                  className="input w-full"
                  placeholder="copia@empresa.com"
                  value={form.cc}
                  onChange={e => setField("cc", e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">Asunto</label>
                <input
                  className="input w-full"
                  value={form.subject}
                  onChange={e => setField("subject", e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">Mensaje</label>
                <textarea
                  className="input w-full h-28 resize-none text-xs leading-relaxed"
                  value={form.body}
                  onChange={e => setField("body", e.target.value)}
                />
                <p className="text-xs text-gray-400 mt-1">
                  Se enviará un Excel separado por cada proveedor, adjunto al correo.
                </p>
              </div>

              {error && (
                <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  <AlertCircle size={13} />
                  {error}
                </div>
              )}
            </div>
          )}

          {/* ── STEP: confirm ── */}
          {step === "confirm" && (
            <div className="space-y-4 py-2">
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm">
                <p className="font-semibold text-amber-800 mb-2">Confirmar envío</p>
                <p className="text-amber-700">
                  Se enviarán <span className="font-bold">{targetCount}</span> correo(s) a{" "}
                  <span className="font-medium">{form.to}</span>
                  {form.cc && <>, CC: <span className="font-medium">{form.cc}</span></>}.
                </p>
                <p className="text-amber-600 text-xs mt-2">
                  Cada correo llevará el Excel de seguimiento del proveedor como adjunto.
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-500 space-y-1">
                <p><span className="font-semibold">Asunto:</span> {form.subject}</p>
                {targetSupplier && (
                  <p><span className="font-semibold">Proveedor:</span> {targetSupplier}</p>
                )}
              </div>
            </div>
          )}

          {/* ── STEP: result ── */}
          {step === "result" && result && (
            <div className="space-y-3 py-2">
              <div className={cn(
                "rounded-xl p-4 flex items-start gap-3",
                result.errors === 0
                  ? "bg-green-50 border border-green-200"
                  : "bg-amber-50 border border-amber-200"
              )}>
                <CheckCircle2 size={18} className={result.errors === 0 ? "text-green-600" : "text-amber-500"} />
                <div>
                  <p className={cn("font-semibold text-sm", result.errors === 0 ? "text-green-800" : "text-amber-800")}>
                    Proceso completado
                  </p>
                  <p className="text-sm mt-0.5">
                    <span className="font-medium text-green-700">Enviados: {result.sent}</span>
                    {result.errors > 0 && (
                      <> · <span className="font-medium text-red-600">Errores: {result.errors}</span></>
                    )}
                  </p>
                </div>
              </div>

              {result.errors > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 max-h-28 overflow-y-auto">
                  <p className="text-xs font-semibold text-red-700 mb-1">Detalles de errores:</p>
                  {result.detail
                    .filter((r: any) => r.status === "error")
                    .map((r: any) => (
                      <p key={r.supplier} className="text-xs text-red-600 truncate">
                        · {r.supplier}: {r.reason}
                      </p>
                    ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer con botones */}
        <div className="px-6 py-4 border-t border-gray-100 flex gap-2 flex-shrink-0">
          {step === "form" && (
            <>
              <button onClick={goToConfirm} className="btn-primary flex-1 flex items-center justify-center gap-2">
                <Send size={14} />
                Continuar
              </button>
              <button onClick={onClose} className="btn-secondary">Cancelar</button>
            </>
          )}
          {step === "confirm" && (
            <>
              <button
                onClick={handleSend}
                disabled={loading}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                <Send size={14} />
                {loading ? `Enviando ${targetCount} correo(s)...` : `Enviar ${targetCount} correo(s)`}
              </button>
              <button onClick={() => setStep("form")} disabled={loading} className="btn-secondary">
                Atrás
              </button>
            </>
          )}
          {step === "result" && (
            <button onClick={onClose} className="btn-primary flex-1">Cerrar</button>
          )}
        </div>

      </div>
    </div>
  );
}
