"use client";

import { ReactNode } from "react";

export function AdminLayout({ children, isLoading }: { children: ReactNode; isLoading: boolean }) {
  return (
    <div className="flex flex-col md:flex-row gap-1 md:gap-10 mt-5" style={{ opacity: isLoading ? 0 : 1 }}>
      {children}
    </div>
  );
}


