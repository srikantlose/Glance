import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import { ShaderBackground } from "@/components/ShaderBackground";
import { PointerProvider } from "@/lib/pointer";
import { AgentPointer } from "@/components/AgentPointer";
import { PointerPrompt } from "@/components/PointerPrompt";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const DESCRIPTION = "A hover-first executive assistant for Gmail, Calendar and Tasks.";

export const metadata: Metadata = {
  title: "Glance",
  description: DESCRIPTION,
  // the full render carries the wordmark and reads properly at card size, which is
  // exactly where the 30px nav mark can't go
  openGraph: {
    title: "Glance",
    description: DESCRIPTION,
    images: [{ url: "/screen.png", width: 1024, height: 1024, alt: "Glance" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Glance",
    description: DESCRIPTION,
    images: ["/screen.png"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
        />
      </head>
      <body className="font-body-md text-body-md flex min-h-screen flex-col text-on-surface md:flex-row">
        <ShaderBackground />
        <PointerProvider>
          <div className="relative z-10 flex min-h-screen w-full flex-col md:flex-row">
            <AppShell>{children}</AppShell>
          </div>
          <AgentPointer />
          <PointerPrompt />
        </PointerProvider>
      </body>
    </html>
  );
}
