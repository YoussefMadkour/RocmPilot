import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RocmPilot Studio",
  description: "AI migration & validation cockpit for AMD GPU readiness",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
