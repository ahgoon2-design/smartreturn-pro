import { Card, Statistic, Typography } from "antd";
import type { ReactNode } from "react";

interface SmartSummaryCardProps {
  label: string;
  value: string | number;
  description?: string;
  icon?: ReactNode;
  tone?: "info" | "success" | "warning" | "danger" | "system" | "neutral";
}

export function SmartSummaryCard({ label, value, description, icon, tone = "info" }: SmartSummaryCardProps) {
  const cardClassName = ["smart-summary-card", `smart-summary-card--${tone}`].join(" ");
  return (
    <Card className={cardClassName} size="small">
      <div className="smart-summary-card__body">
        <div className="smart-summary-card__main">
          <Statistic title={label} value={value} />
          {description ? <Typography.Text className="smart-summary-card__description">{description}</Typography.Text> : null}
        </div>
        {icon ? <span className="smart-summary-card__icon" aria-hidden="true">{icon}</span> : null}
      </div>
    </Card>
  );
}
