import type { Metadata } from "next";
import { Chakra_Petch, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";

// Type roles per frontend/DESIGN.md: HUD display / readable body / data mono.
const display = Chakra_Petch({
  weight: ["600", "700"],
  subsets: ["latin"],
  variable: "--font-display",
});
const body = IBM_Plex_Sans({
  weight: ["400", "500", "600"],
  subsets: ["latin"],
  variable: "--font-body",
});
const mono = IBM_Plex_Mono({
  weight: ["400", "500"],
  subsets: ["latin"],
  variable: "--font-mono",
});

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
    <html
      lang="en"
      className={`dark ${display.variable} ${body.variable} ${mono.variable}`}
      // Browser extensions (e.g. data-jetski-tab-id) mutate <html> attributes
      // before React hydrates, causing a false-positive hydration warning.
      // Our own attributes here are static, so suppressing is safe and scoped
      // to this element only.
      suppressHydrationWarning
    >
      <body className="font-sans">
        <header className="border-b border-edge">
          <div className="mx-auto flex max-w-6xl items-baseline gap-3 px-6 py-4">
            <span className="font-display text-lg font-bold tracking-widest">
              ROCMPILOT<span className="text-accent"> STUDIO</span>
            </span>
            <span className="hidden font-mono text-xs text-ink-dim sm:inline">
              CUDA-first repo → AMD-ready container
            </span>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
