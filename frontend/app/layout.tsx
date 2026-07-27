import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import { Eye } from "lucide-react";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Glance",
  description: "A hover-first executive assistant for Gmail, Calendar and Tasks.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-bg text-text">
        <header className="flex items-center gap-6 border-b border-border px-4 py-2.5">
          <Link href="/" className="flex items-center gap-2 text-sm font-semibold">
            <Eye size={16} className="text-accent" /> Glance
          </Link>
          <nav className="flex gap-4 text-sm text-muted">
            <Link href="/" className="hover:text-text">
              Dashboard
            </Link>
            <Link href="/approvals" className="hover:text-text">
              Approvals
            </Link>
            <Link href="/audit" className="hover:text-text">
              Audit
            </Link>
          </nav>
        </header>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
