import axios from "axios";

const BACKEND =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

const api = axios.create({ baseURL: `${BACKEND}/api` });

export const uploadExcel = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return axios.post(`${BACKEND}/api/upload/`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getOcs = (proveedor: string) =>
  axios.get(`${BACKEND}/api/upload/ocs`, { params: { proveedor } });

export const getOcDetail = (oc_pos: string) =>
  axios.get(`${BACKEND}/api/upload/oc-detail`, { params: { oc_pos } });

export const downloadTemplate = (proveedor?: string) =>
  axios.get(`${BACKEND}/api/upload/template`, {
    params: proveedor ? { proveedor } : {},
    responseType: "blob",
  });

export interface SendEmailsPayload {
  to:        string;
  cc?:       string;
  subject:   string;
  body:      string;
  proveedor?: string;   // vacío = todos, valor = solo ese proveedor
}

export const sendEmails = (payload: SendEmailsPayload) =>
  axios.post(`${BACKEND}/api/upload/send-emails`, payload);

export const getOrders = (params?: Record<string, string | boolean>) =>
  api.get("/orders/", { params });

export const getOrder = (oc_pos: string) =>
  api.get(`/orders/${encodeURIComponent(oc_pos)}`);

export const getSuppliers = () =>
  api.get("/suppliers/");

export const updateSupplierEmail = (name: string, email: string) =>
  api.put(`/suppliers/${encodeURIComponent(name)}/email`, null, { params: { email } });

export const generateZip = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/suppliers/generate-zip", form, { responseType: "blob" });
};

export const getRisks = () =>
  api.get("/ai/risks");

export const summarizeOrder = (oc_pos: string) =>
  api.post(`/ai/summarize/${encodeURIComponent(oc_pos)}`);

export const sendChat = (question: string, ctx: string = "") =>
  axios.post(`${BACKEND}/api/chat/`, { question, ctx });
