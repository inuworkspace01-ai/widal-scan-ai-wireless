import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "WIDAL-SCAN AI — Wireless Edition",
  description: "AI-assisted Widal image documentation and laboratory workflow prototype.",
  applicationName: "WIDAL-SCAN AI",
  manifest: "/manifest.webmanifest",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="id"><body>{children}</body></html>;
}