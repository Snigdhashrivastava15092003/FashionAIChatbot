import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fashion AI | Premium Personal Stylist",
  description:
    "Fashion AI delivers polished outfit recommendations tailored to your personality, budget, occasion, and style preferences.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
