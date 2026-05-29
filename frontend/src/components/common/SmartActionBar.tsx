import type { ReactNode } from "react";

export function SmartActionBar({ children }: { children: ReactNode }) {
  return <footer className="smart-action-bar">{children}</footer>;
}
