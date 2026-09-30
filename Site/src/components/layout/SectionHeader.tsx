"use client";

import { ReactNode } from "react";

export function SectionHeader({ title, description, actions }: { title?: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        {title ? <h2 className="text-base font-semibold">{title}</h2> : null}
        {description ? <div className="text-sm text-foreground/70">{description}</div> : null}
      </div>
      <div className="flex items-center gap-2">{actions}</div>
    </div>
  );
}


