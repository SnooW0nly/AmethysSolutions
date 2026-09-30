import { notFound, redirect } from "next/navigation";
import { siteConfig } from "@/config/site";

type Props = {
  params: { slug?: string[] };
};

export default function SocialRedirect({ params }: Props) {
  const key = (params.slug?.[0] ?? "").toLowerCase();
  const url = (siteConfig.socials as Record<string, string>)[key];

  if (!url) {
    notFound();
  }

  redirect(url);
}


