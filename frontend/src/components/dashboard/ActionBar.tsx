"use client";
import { useState } from "react";
import { Download, Mail } from "lucide-react";
import { downloadTemplate } from "@/lib/api";

interface Props {
  selectedSupplier?: string;
  onSendEmails: () => void;
}

export function ActionBar({ selectedSupplier, onSendEmails }: Props) {
  const [loadingDownload, setLoadingDownload] = useState(false);
  const [downloadError,   setDownloadError]   = useState("");

  async function handleDownload() {
    setLoadingDownload(true);
    setDownloadError("");
    try {
      const { data } = await downloadTemplate(selectedSupplier || undefined);
      const url      = URL.createObjectURL(new Blob([data]));
      const filename = selectedSupplier
        ? `seguimiento_${selectedSupplier}.xlsx`
        : "seguimiento.xlsx";
      const a    = document.createElement("a");
      a.href     = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      const blob: Blob | undefined = err?.response?.data;
      const msg = blob
        ? await blob.text().then(t => { try { return JSON.parse(t).detail; } catch { return t; } })
        : "No hay datos cargados. Sube el Excel primero.";
      setDownloadError(msg);
    } finally {
      setLoadingDownload(false);
    }
  }

  return (
    <div className="flex items-center gap-3 flex-wrap mb-5">
      <button
        onClick={handleDownload}
        disabled={loadingDownload}
        className="btn-secondary flex items-center gap-2"
      >
        <Download size={15} />
        {loadingDownload
          ? "Generando..."
          : selectedSupplier
            ? `Descargar – ${selectedSupplier}`
            : "Descargar plantillas por proveedor"}
      </button>

      <button
        onClick={onSendEmails}
        className="btn-primary flex items-center gap-2"
      >
        <Mail size={15} />
        Enviar correos automáticamente
      </button>

      {downloadError && (
        <span className="text-xs text-red-500">{downloadError}</span>
      )}
    </div>
  );
}
