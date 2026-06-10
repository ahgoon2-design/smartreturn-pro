import { CheckCircleOutlined, LockOutlined } from "@ant-design/icons";
import { Badge, Button, Card, Col, Row, Segmented, Space, Table, Tag, Typography, message } from "antd";
import type { TableColumnsType } from "antd";
import { useState } from "react";
import { SmartDataSection } from "../../components/common/SmartDataSection";
import { SmartPage } from "../../components/common/SmartPage";
import { SmartPageHeader } from "../../components/common/SmartPageHeader";
import {
  ADDON_ROWS,
  PLAN_FEATURE_ROWS,
  PLAN_METRIC_ROWS,
  PLAN_TIERS,
  formatPlanPrice,
} from "./planCatalog";
import type { AddonRow, FeatureLevel, PlanFeatureRow, PlanMetricRow, PlanTier } from "./planCatalog";

type BillingCycle = "monthly" | "yearly";

const FEATURE_TONE: Record<FeatureLevel, { color: string; locked?: boolean }> = {
  included: { color: "green" },
  advanced: { color: "geekblue" },
  limited: { color: "gold" },
  locked: { color: "default", locked: true },
  consult: { color: "purple" },
};

/** 기능 제공 수준을 색상 배지로 표현한다. */
function PlanFeatureBadge({ level, text }: { level: FeatureLevel; text: string }) {
  const tone = FEATURE_TONE[level];
  return (
    <Tag color={tone.color} icon={tone.locked ? <LockOutlined /> : undefined} style={{ margin: 0 }}>
      {text}
    </Tag>
  );
}

function PlanCard({ plan, cycle }: { plan: PlanTier; cycle: BillingCycle }) {
  const price = formatPlanPrice(plan, cycle);
  const isRecommended = plan.badge?.tone === "recommend";

  function handleCta() {
    if (plan.cta.kind === "consult") {
      message.info("상담 문의는 담당자 연결 후 제공됩니다. (결제 연동 준비 중)");
      return;
    }
    message.info("플랜 업그레이드 결제 연동은 준비 중입니다. 담당자에게 문의해 주세요.");
  }

  const card = (
    <Card
      className="plan-card"
      style={isRecommended ? { borderColor: "#3b5bdb", borderWidth: 2 } : undefined}
      title={
        <Space direction="vertical" size={2} style={{ display: "flex" }}>
          <Typography.Text strong style={{ fontSize: 16 }}>
            {plan.name}
          </Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12, whiteSpace: "normal", fontWeight: 400 }}>
            {plan.tagline}
          </Typography.Text>
        </Space>
      }
    >
      <Typography.Title level={4} style={{ marginTop: 0, marginBottom: price.note ? 0 : 12 }}>
        {price.primary}
      </Typography.Title>
      {price.note ? (
        <Typography.Text type="secondary" style={{ display: "block", marginBottom: 12, fontSize: 12 }}>
          {price.note}
        </Typography.Text>
      ) : null}

      <Space direction="vertical" size={6} style={{ display: "flex", marginBottom: 16 }}>
        {plan.highlights.map((line) => (
          <Space key={line} size={6} align="start">
            <CheckCircleOutlined style={{ color: "#2f9e44", marginTop: 3 }} />
            <Typography.Text>{line}</Typography.Text>
          </Space>
        ))}
      </Space>

      <Button type={isRecommended ? "primary" : "default"} block onClick={handleCta}>
        {plan.cta.label}
      </Button>
    </Card>
  );

  if (plan.badge) {
    return (
      <Badge.Ribbon text={plan.badge.text} color={plan.badge.tone === "recommend" ? "#3b5bdb" : "#e8590c"}>
        {card}
      </Badge.Ribbon>
    );
  }
  return card;
}

export function PricingPlansPage() {
  const [cycle, setCycle] = useState<BillingCycle>("monthly");

  const planColumns = PLAN_TIERS.map((plan) => ({
    title: plan.name,
    key: plan.id,
    align: "center" as const,
  }));

  const metricColumns: TableColumnsType<PlanMetricRow> = [
    { title: "한도 항목", dataIndex: "label", key: "label", fixed: "left", width: 160 },
    ...planColumns.map((col) => ({
      ...col,
      render: (_: unknown, record: PlanMetricRow) => record.values[col.key],
    })),
  ];

  const featureColumns: TableColumnsType<PlanFeatureRow> = [
    { title: "기능", dataIndex: "label", key: "label", fixed: "left", width: 160 },
    ...planColumns.map((col) => ({
      ...col,
      render: (_: unknown, record: PlanFeatureRow) => {
        const cell = record.values[col.key];
        return <PlanFeatureBadge level={cell.level} text={cell.text} />;
      },
    })),
  ];

  const addonColumns: TableColumnsType<AddonRow> = [
    { title: "항목", dataIndex: "item", key: "item" },
    { title: "기준", dataIndex: "basis", key: "basis", width: 160 },
    { title: "추가 요금", dataIndex: "price", key: "price", width: 160, align: "right" },
  ];

  return (
    <SmartPage>
      <SmartPageHeader
        title="스마트리턴프로 요금제"
        description="반품 처리량, SKU, 고객사 수, API 연동, 사진 보관기간에 따라 플랜을 선택하세요."
        extra={
          <Segmented
            value={cycle}
            onChange={(value) => setCycle(value as BillingCycle)}
            options={[
              { label: "월간", value: "monthly" },
              { label: "연간(2개월 할인)", value: "yearly" },
            ]}
          />
        }
      />

      <Row gutter={[16, 16]}>
        {PLAN_TIERS.map((plan) => (
          <Col xs={24} md={12} xl={6} key={plan.id}>
            <PlanCard plan={plan} cycle={cycle} />
          </Col>
        ))}
      </Row>

      <SmartDataSection size="small" title="플랜별 한도 비교">
        <Table<PlanMetricRow>
          columns={metricColumns}
          dataSource={PLAN_METRIC_ROWS}
          rowKey="label"
          size="small"
          pagination={false}
          scroll={{ x: 720 }}
        />
      </SmartDataSection>

      <SmartDataSection size="small" title="기능 비교">
        <Table<PlanFeatureRow>
          columns={featureColumns}
          dataSource={PLAN_FEATURE_ROWS}
          rowKey="label"
          size="small"
          pagination={false}
          scroll={{ x: 720 }}
        />
        <Typography.Paragraph type="secondary" className="smart-paragraph-note">
          잠금/제한 기능은 상위 플랜에서 해제됩니다. Basic은 미지원 기능도 숨기지 않고 잠금으로 표시하며, 실제 사용 제한(plan enforcement)은
          다음 작업에서 backend `plan_limits` 기준으로 적용할 예정입니다.
        </Typography.Paragraph>
      </SmartDataSection>

      <SmartDataSection size="small" title="추가 과금표">
        <Table<AddonRow>
          columns={addonColumns}
          dataSource={ADDON_ROWS}
          rowKey="item"
          size="small"
          pagination={false}
          scroll={{ x: 560 }}
        />
        <Typography.Paragraph type="secondary" className="smart-paragraph-note">
          추가 과금표는 안내용 표시이며, 실제 청구/결제 로직과는 연결되어 있지 않습니다.
        </Typography.Paragraph>
      </SmartDataSection>
    </SmartPage>
  );
}
