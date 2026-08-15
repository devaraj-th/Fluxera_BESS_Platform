import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fluxera Procurement Assurance",
  description: "Evidence-led pre-bid requirement review",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
