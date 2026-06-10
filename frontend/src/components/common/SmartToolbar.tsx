import type { ReactNode } from "react";

interface SmartToolbarProps {
  ariaLabel?: string;
  children: ReactNode;
  className?: string;
}

export function SmartToolbar({ ariaLabel, children, className }: SmartToolbarProps) {
  const toolbarClassName = ["smart-toolbar", className].filter(Boolean).join(" ");
  return (
    <section className={toolbarClassName} aria-label={ariaLabel}>
      {children}
    </section>
  );
}
