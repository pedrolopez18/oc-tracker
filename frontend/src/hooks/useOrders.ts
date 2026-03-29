"use client";
import { useState, useEffect } from "react";
import { getOrders } from "@/lib/api";
import { Order } from "@/types/order";

export function useOrders() {
  const [orders,  setOrders]  = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");

  async function load(params?: Record<string, string | boolean>) {
    setLoading(true);
    try {
      const { data } = await getOrders(params);
      setOrders(data);
    } catch { setError("Error cargando órdenes"); }
    finally  { setLoading(false); }
  }

  useEffect(() => { load(); }, []);
  return { orders, loading, error, reload: load };
}
