import type { Metadata } from "next";
import { Outfit, Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-display",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Core Orchestrator — Multi-Agent Chat",
  description:
    "A multi-agent chatbot powered by LangGraph orchestration, FastAPI SSE streaming, and live MCP tool servers. Built with an editorial-minimalist interface.",
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
      className={`${outfit.variable} ${inter.variable} ${jetbrainsMono.variable} ${spaceGrotesk.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-black text-[#ECECED] font-sans antialiased selection:bg-[#C3982C]/30 selection:text-white flex flex-col">
        {children}
      </body>
    </html>
  );
}
