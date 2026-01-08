import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Upscaled Cross-List | Multi-Marketplace Inventory Management",
  description: "Cross-list your inventory across 10+ marketplaces with AI-powered optimization",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
