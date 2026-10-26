import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORACLE | Software Diagnostic & Fault Isolation Platform",
  description:
    "An extensible platform for inspecting software systems, identifying faults, testing components independently, and producing evidence-backed diagnoses.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-zinc-200 dark:selection:bg-zinc-800">
        {children}
      </body>
    </html>
  );
}
