import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fluxera | BESS Intelligence Platform",
  description: "Procurement Intelligence for evidence-led BESS decisions",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
