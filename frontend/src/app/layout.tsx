import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Image from "next/image";
import logo from "@/assets/logo_pluspetrol_2026.png";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "OC Tracker Supply Chain — Pluspetrol",
  description: "Seguimiento de órdenes de compra",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={inter.className}>
        <header className="sticky top-0 z-10 bg-brand shadow-md">
          <div className="max-w-screen-2xl mx-auto px-6 h-14 flex items-center justify-between">

            {/* Logo + nombre */}
            <div className="flex items-center gap-3">
              {/* Logo en contenedor blanco para contraste con fondo azul */}
              <div className="bg-white rounded-lg p-1 flex items-center justify-center shadow-sm shrink-0">
                <Image
                  src={logo}
                  alt="Pluspetrol"
                  height={32}
                  className="h-10 w-auto object-contain"
                  priority
                />
              </div>

              {/* Texto corporativo */}
              <div>
                <p className="text-white font-bold text-[15px] leading-none tracking-wide">
                  Pluspetrol
                </p>
                <p className="text-blue-200 text-[11px] leading-none mt-0.5">
                  OC Tracker Supply Chain
                </p>
              </div>
            </div>

            {/* Badge de entorno */}
            <span className="text-xs bg-white/10 text-blue-100 px-3 py-1 rounded-full border border-white/20">
              Sistema de Seguimiento
            </span>

          </div>
        </header>

        <main className="max-w-screen-2xl mx-auto px-6 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
