import { Card, Statistic } from "antd";

interface SmartSummaryCardProps {
  label: string;
  value: string | number;
}

export function SmartSummaryCard({ label, value }: SmartSummaryCardProps) {
  return (
    <Card className="smart-summary-card" size="small">
      <Statistic title={label} value={value} />
    </Card>
  );
}
