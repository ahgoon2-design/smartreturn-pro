import { Card } from "antd";
import type { CardProps } from "antd";

export function SmartDataSection({ className, ...props }: CardProps) {
  const sectionClassName = ["smart-work-panel", className].filter(Boolean).join(" ");
  return <Card className={sectionClassName} {...props} />;
}
