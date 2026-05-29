import { Typography } from "antd";
import type { ReactNode } from "react";

interface SmartPageHeaderProps {
  title: string;
  description?: string;
  extra?: ReactNode;
}

export function SmartPageHeader({ title, description, extra }: SmartPageHeaderProps) {
  return (
    <header className="smart-page-header">
      <div>
        <Typography.Title level={3}>{title}</Typography.Title>
        {description ? <Typography.Paragraph>{description}</Typography.Paragraph> : null}
      </div>
      {extra ? <div className="smart-page-header-extra">{extra}</div> : null}
    </header>
  );
}
