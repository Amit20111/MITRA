import type { Metadata } from "next";
import "./globals.css";
import "./mitra-theme.css";
export const metadata: Metadata = {
  icons: { icon: "/icon.svg" },
  title: "MITRA — Your personal agent",
  description:
    "A thoughtful workspace for getting things done. Plan, review, and follow every step with MITRA.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
