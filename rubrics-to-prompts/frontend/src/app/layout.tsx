import type { Metadata } from "next";
import { Geist, Geist_Mono, Prata } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const prata = Prata({
  weight: "400",
  variable: "--font-prata",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PromptGen - OSCE Rubric Converter | Oski",
  description: "Transform OSCE exam rubrics into AI-ready prompts with intelligent OCR processing and automated generation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${prata.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
