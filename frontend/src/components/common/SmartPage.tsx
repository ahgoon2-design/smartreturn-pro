import type { ReactNode } from "react";

export function SmartPage({ children }: { children: ReactNode }) {
  return <section className="smart-page">{children}</section>;
}
