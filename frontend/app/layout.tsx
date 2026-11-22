import type { Metadata } from "next";
import { IBM_Plex_Sans, Geist_Mono, Source_Sans_3 } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

const responseFont = Source_Sans_3({
  variable: "--font-response",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Core Orchestrator — Multi-Agent Chat",
  description:
    "A multi-agent chatbot powered by LangGraph orchestration, FastAPI SSE streaming, and live MCP tool servers. A calm workspace for ideas, research, and everyday questions.",
  openGraph: {
    title: "Core Orchestrator",
    description:
      "Multi-agent chatbot with LangGraph, FastAPI streaming, and MCP tool integration.",
    type: "website",
    locale: "en_US",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${plexSans.variable} ${geistMono.variable} ${responseFont.variable} h-full antialiased`}
    >
      <body className="bg-background font-sans text-foreground antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
