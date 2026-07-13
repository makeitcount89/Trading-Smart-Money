import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smart Money Concepts — Multi-Stock Dashboard",
  description:
    "LuxAlgo Smart Money Concepts structure & order-block detection across a configurable stock universe, ranked by proximity to the nearest bullish order block.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[var(--page-plane)] font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
