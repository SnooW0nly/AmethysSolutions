import { Metadata, Viewport } from "next";
import Script from "next/script";
import "@/styles/globals.css";
import "@fortawesome/fontawesome-svg-core/styles.css";

import { Providers } from "./providers";
import LayoutClient from "@/components/LayoutClient";

import { fontSans } from "@/config/fonts";
import clsx from "clsx";
import { siteConfig } from "@/config/site";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_URL || "https://amethysapplications.com.br"),
  title: {
    default: siteConfig.name,
    template: `%s - ${siteConfig.name}`,
  },
  description: siteConfig.description,
  icons: {
    icon: "/amethys.png",
  },
  openGraph: {
    title: siteConfig.name,
    description: siteConfig.description,
    type: "website",
    images: [
      {
        url: "/thumbnail.png",
        width: 1200,
        height: 630,
        alt: "Amethys Solutions",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: siteConfig.name,
    description: siteConfig.description,
    images: [
      "/thumbnail.png",
    ],
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#5c5ef0" },
    { media: "(prefers-color-scheme: dark)", color: "#5c5ef0" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html suppressHydrationWarning lang="en">
      <head />
      <body className={clsx("min-h-screen text-foreground bg-background font-sans antialiased focus:outline-none", fontSans.variable)}>
        <Providers themeProps={{ attribute: "class", defaultTheme: "dark" }}>
          <LayoutClient>{children}</LayoutClient>
        </Providers>

        <Script id="ascii-banner" strategy="afterInteractive">{`/* seu banner ascii */`}</Script>
      </body>
    </html>
  );
}
