import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Reel Factory",
  description: "Content intelligence and AI-assisted Reel production.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
