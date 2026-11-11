import "./styles.css";
import type { Metadata, Viewport } from "next";
import AppShell from "./app-shell";

export const metadata: Metadata = {
  title: "Mushroom Farm App",
  // A private working tool: keep it out of search engines.
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
