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
  title: "Thesis Tracker",
  description: "Write an investment thesis. An agent checks it against the news.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <header className="border-b border-border-subtle">
          <div className="mx-auto max-w-2xl px-4 py-4">
            <Link
              href="/"
              className="font-mono text-sm font-semibold tracking-wider text-foreground hover:text-accent"
            >
              THESIS TRACKER
            </Link>
          </div>
        </header>
        <div className="flex-1">{children}</div>
      </body>
    </html>
  );
}
