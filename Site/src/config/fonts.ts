import { Fira_Code as FontMono, Inter as FontSans, Space_Mono as FontMonoSpace } from "next/font/google";

export const fontSans = FontSans({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const fontMono = FontMono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const fontMonoSpace = FontMonoSpace({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-mono-space",
});