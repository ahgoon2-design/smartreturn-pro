import type { ReactNode } from "react";

interface SmartScanPanelProps {
  ariaLabel: string;
  children: ReactNode;
  className?: string;
}

export function SmartScanPanel({ ariaLabel, children, className }: SmartScanPanelProps) {
  const scanPanelClassName = ["smart-scan-panel", className].filter(Boolean).join(" ");
  return (
    <section className={scanPanelClassName} aria-label={ariaLabel}>
      {children}
    </section>
  );
}
