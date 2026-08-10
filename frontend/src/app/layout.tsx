import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Knowledge Base",
  description: "A personal knowledge base with wikilinks, backlinks, and AI fact-checking.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <header className="border-b border-border-subtle">
          <div className="mx-auto flex max-w-2xl items-center justify-between px-4 py-4">
            <Link
              href="/"
              className="font-mono text-sm font-semibold tracking-wider text-foreground hover:text-accent"
            >
              KNOWLEDGE BASE
            </Link>
            <Link href="/graph" className="text-sm text-muted hover:text-accent">
              Graph
            </Link>
          </div>
        </header>
        <div className="flex-1">{children}</div>
      </body>
    </html>
  );
}
