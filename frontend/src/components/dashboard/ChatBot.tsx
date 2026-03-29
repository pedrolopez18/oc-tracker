"use client";
import { useState, useRef, useEffect, FormEvent, Fragment } from "react";
import { sendChat } from "@/lib/api";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ChatAction {
  label:        string;
  filter_key:   string;
  filter_value: string;
}

interface Message {
  role:     "user" | "bot";
  text:     string;
  actions?: ChatAction[];
}

interface Props {
  onFilterChange?: (key: string, value: string) => void;
  suppliers?:      string[];
}

// ── Context serializer ────────────────────────────────────────────────────────

function serializeCtx(ctx: Record<string, string>): string {
  return Object.entries(ctx)
    .filter(([, v]) => v)
    .map(([k, v]) => `${k}:${v}`)
    .join("|");
}

// ── Detect follow-up question ─────────────────────────────────────────────────

const FOLLOWUP_PREFIXES = ["y ", "¿y", "y las", "y los", "cuáles", "cuales", "qué tal", "que tal", "¿cuá", "¿que"];

function isFollowUp(q: string): boolean {
  const lq = q.toLowerCase().trim();
  return FOLLOWUP_PREFIXES.some(p => lq.startsWith(p));
}

// ── Render text with **bold** markdown ───────────────────────────────────────

function RichText({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, li) => (
        <Fragment key={li}>
          {li > 0 && <br />}
          {line.split(/(\*\*[^*]+\*\*)/).map((part, pi) =>
            part.startsWith("**") && part.endsWith("**")
              ? <strong key={pi} className="font-semibold">{part.slice(2, -2)}</strong>
              : part
          )}
        </Fragment>
      ))}
    </>
  );
}

// ── Suggestions ───────────────────────────────────────────────────────────────

const SUGGESTIONS = [
  "Órdenes críticas",
  "Órdenes retrasadas",
  "¿Cuántas hay en plazo?",
  "Resumen general",
];

// ── ChatBot component ─────────────────────────────────────────────────────────

export function ChatBot({ onFilterChange, suppliers = [] }: Props) {
  const [open,     setOpen]     = useState(false);
  const [messages, setMessages] = useState<Message[]>([{
    role: "bot",
    text: "Hola, soy tu asistente de OCs.\nPuedes preguntarme sobre órdenes retrasadas, críticas, por proveedor o número de OC.",
  }]);
  const [input,   setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const [chatCtx, setChatCtx] = useState<Record<string, string>>({});
  const bottomRef             = useRef<HTMLDivElement>(null);
  const inputRef              = useRef<HTMLInputElement>(null);

  // Auto-scroll
  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  // Focus input when opening
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  // Extract proveedor from text using known suppliers list
  function extractProveedor(text: string): string | undefined {
    const upper = text.toUpperCase();
    return suppliers.find(s => s && upper.includes(s.toUpperCase()));
  }

  async function handleSubmit(e: FormEvent, preset?: string) {
    e.preventDefault();
    const rawQ = (preset ?? input).trim();
    if (!rawQ || loading) return;

    setInput("");

    // For follow-ups, prepend context to the question sent to backend
    // (display remains the original user text)
    let questionToSend = rawQ;
    if (isFollowUp(rawQ) && Object.keys(chatCtx).length > 0) {
      const ctxParts: string[] = [];
      if (chatCtx.proveedor) ctxParts.push(`proveedor ${chatCtx.proveedor}`);
      if (chatCtx.risk)      ctxParts.push(chatCtx.risk);
      const stripped = rawQ.replace(/^(¿y|y)\s+/i, "");
      questionToSend = ctxParts.length > 0 ? `${ctxParts.join(" ")} ${stripped}` : rawQ;
    }

    setMessages(prev => [...prev, { role: "user", text: rawQ }]);
    setLoading(true);

    // Update ctx from user message
    const provFromQ = extractProveedor(rawQ);
    if (provFromQ) setChatCtx(c => ({ ...c, proveedor: provFromQ }));

    try {
      const res = await sendChat(questionToSend, serializeCtx(chatCtx));
      const { answer, actions = [] } = res.data as { answer: string; actions: ChatAction[] };

      setMessages(prev => [...prev, { role: "bot", text: answer, actions }]);

      // Update ctx from response
      const provFromR = extractProveedor(answer);
      if (provFromR) setChatCtx(c => ({ ...c, proveedor: provFromR }));

    } catch {
      setMessages(prev => [...prev, {
        role: "bot",
        text: "No se pudo conectar con el servidor.\nAsegúrate de que el backend esté corriendo en localhost:8000.",
      }]);
    } finally {
      setLoading(false);
    }
  }

  function handleAction(action: ChatAction) {
    onFilterChange?.(action.filter_key, action.filter_value);
    // Visual feedback: add mini-message
    setMessages(prev => [...prev, {
      role: "bot",
      text: `Filtro aplicado: ${action.label} ✓`,
    }]);
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(o => !o)}
        className={cn(
          "fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-xl",
          "flex items-center justify-center text-white transition-all duration-200",
          open ? "bg-gray-600 rotate-90" : "bg-brand hover:scale-105"
        )}
        aria-label="Abrir asistente"
      >
        <span className="text-xl">{open ? "✕" : "💬"}</span>
      </button>

      {/* Chat panel — mobile: fullscreen bottom sheet | desktop: floating */}
      {open && (
        <div className={cn(
          "fixed z-50 bg-white border border-gray-200 shadow-2xl flex flex-col overflow-hidden",
          // Mobile: full screen
          "inset-x-0 bottom-0 rounded-t-2xl max-h-[85dvh]",
          // Desktop: floating panel
          "sm:inset-x-auto sm:bottom-24 sm:right-6 sm:w-96 sm:rounded-2xl sm:max-h-[600px]"
        )}>
          {/* Header */}
          <div className="bg-brand px-4 py-3 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <div>
                <p className="text-white font-semibold text-sm leading-tight">Asistente OC Tracker</p>
                <p className="text-blue-200 text-[11px] leading-tight">Consulta tus órdenes en lenguaje natural</p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-blue-200 hover:text-white text-lg leading-none"
            >
              ✕
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
            {messages.map((m, i) => (
              <div key={i} className={cn("flex gap-2", m.role === "user" ? "justify-end" : "justify-start")}>
                {m.role === "bot" && (
                  <div className="w-6 h-6 rounded-full bg-brand/10 flex items-center justify-center shrink-0 mt-0.5 text-xs">
                    🤖
                  </div>
                )}
                <div className={cn(
                  "px-3.5 py-2.5 rounded-2xl text-sm max-w-[85%] leading-relaxed",
                  m.role === "user"
                    ? "bg-brand text-white rounded-br-sm"
                    : "bg-gray-100 text-gray-800 rounded-bl-sm"
                )}>
                  <RichText text={m.text} />

                  {/* Action buttons */}
                  {m.role === "bot" && m.actions && m.actions.length > 0 && (
                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                      {m.actions.map((a, ai) => (
                        <button
                          key={ai}
                          onClick={() => handleAction(a)}
                          className="text-xs bg-white text-brand px-2.5 py-1 rounded-full border border-brand/25 hover:bg-brand/5 transition-colors font-medium shadow-sm"
                        >
                          {a.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className="flex justify-start gap-2">
                <div className="w-6 h-6 rounded-full bg-brand/10 flex items-center justify-center shrink-0 mt-0.5 text-xs">
                  🤖
                </div>
                <div className="bg-gray-100 px-4 py-3 rounded-2xl rounded-bl-sm flex items-center gap-1.5">
                  {[0, 1, 2].map(i => (
                    <div
                      key={i}
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Quick suggestions */}
          <div className="px-3 pt-2 pb-1 flex gap-1.5 flex-wrap shrink-0 border-t border-gray-100">
            {SUGGESTIONS.map(s => (
              <button
                key={s}
                onClick={e => handleSubmit(e, s)}
                disabled={loading}
                className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-2.5 py-1 rounded-full transition-colors disabled:opacity-50 shrink-0"
              >
                {s}
              </button>
            ))}
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="p-3 flex gap-2 shrink-0">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Pregunta sobre tus OCs..."
              disabled={loading}
              className="flex-1 text-sm border border-gray-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand/50 disabled:opacity-50 transition-all"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-brand text-white w-10 h-10 rounded-xl text-base font-bold hover:bg-brand-dark disabled:opacity-40 transition-colors shrink-0 flex items-center justify-center"
            >
              →
            </button>
          </form>
        </div>
      )}
    </>
  );
}
