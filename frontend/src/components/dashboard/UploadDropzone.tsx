"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud } from "lucide-react";
import { uploadExcel } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";

interface Props { onSuccess: (summary: any) => void; onFileReady: (file: File) => void }

export function UploadDropzone({ onSuccess, onFileReady }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setLoading(true); setError("");
    onFileReady(file);
    try {
      const { data } = await uploadExcel(file);
      if (data.status === "ok") onSuccess(data);
      else setError(data.error || "Error procesando");
    } catch { setError("No se pudo conectar con el servidor"); }
    finally { setLoading(false); }
  }, [onSuccess, onFileReady]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"] },
    maxFiles: 1,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors mb-5
        ${isDragActive ? "border-brand bg-green-50" : "border-gray-200 bg-white hover:border-gray-300"}`}
    >
      <input {...getInputProps()} />
      <UploadCloud className="mx-auto mb-2 text-gray-300" size={32} />
      {loading ? <Spinner /> : (
        <>
          <p className="text-sm font-medium text-gray-600">
            {isDragActive ? "Suelta el Excel aquí" : "Arrastra tu Excel maestro o haz clic para buscar"}
          </p>
          <p className="text-xs text-gray-400 mt-1">Solo archivos .xlsx</p>
        </>
      )}
      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
    </div>
  );
}
