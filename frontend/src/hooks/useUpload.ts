"use client";
import { useState } from "react";
import { uploadExcel } from "@/lib/api";

export function useUpload(onSuccess?: (summary: any) => void) {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");

  async function upload(file: File) {
    setLoading(true); setError("");
    try {
      const { data } = await uploadExcel(file);
      if (data.status === "ok") onSuccess?.(data.summary);
      else setError(data.error || "Error procesando");
    } catch { setError("Error de conexión"); }
    finally  { setLoading(false); }
  }

  return { upload, loading, error };
}
