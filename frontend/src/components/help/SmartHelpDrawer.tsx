import { Alert, Drawer, Space, Tag, Typography } from "antd";
import { getScreenHelp } from "../../help/smartReturnProHelpRegistry";
import type { ScreenHelpEntry } from "./types";

const AUDIENCE_LABELS: Record<string, string> = {
  internal: "내부 운영자용",
  client: "고객사용",
  both: "공용",
};

interface SmartHelpDrawerProps {
  screenKey: string;
  open: boolean;
  onClose: () => void;
}

/**
 * 화면 도움말 Drawer. 본문은 smartReturnProHelpRegistry에서 가져온다.
 * registry에 없는 screenKey면 안내 문구만 표시하고 화면을 깨뜨리지 않는다.
 */
export function SmartHelpDrawer({ screenKey, open, onClose }: SmartHelpDrawerProps) {
  const entry = getScreenHelp(screenKey);

  return (
    <Drawer
      title={entry ? `도움말 · ${entry.title}` : "도움말"}
      open={open}
      onClose={onClose}
      width={420}
      destroyOnClose
    >
      {entry ? <HelpContent entry={entry} /> : <Alert type="info" showIcon message="이 화면의 도움말이 아직 준비되지 않았습니다." />}
    </Drawer>
  );
}

function HelpContent({ entry }: { entry: ScreenHelpEntry }) {
  return (
    <Space direction="vertical" size={14} style={{ width: "100%" }}>
      <Space size={6} wrap>
        <Tag color="blue">{AUDIENCE_LABELS[entry.audience] || entry.audience}</Tag>
        {entry.draft ? <Tag color="orange">초안</Tag> : null}
      </Space>
      <Typography.Text>{entry.summary}</Typography.Text>

      {entry.warnings.length > 0 ? (
        <Alert
          type="warning"
          showIcon
          message="주의하세요"
          description={
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {entry.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          }
        />
      ) : null}

      {entry.sections.map((section) => (
        <div key={section.heading}>
          <Typography.Title level={5} style={{ marginBottom: 6 }}>
            {section.heading}
          </Typography.Title>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {section.items.map((item) => (
              <li key={item} style={{ marginBottom: 4 }}>
                <Typography.Text>{item}</Typography.Text>
              </li>
            ))}
          </ul>
        </div>
      ))}

      <RelatedScreens relatedKeys={entry.relatedScreens} />
    </Space>
  );
}

/** 관련 화면 태그 목록. registry에 등록된 화면만 보여줘 내부 키가 사용자에게 노출되지 않게 한다. */
function RelatedScreens({ relatedKeys }: { relatedKeys: string[] }) {
  const registered = relatedKeys
    .map((relatedKey) => getScreenHelp(relatedKey))
    .filter((related): related is NonNullable<typeof related> => Boolean(related));
  if (registered.length === 0) {
    return null;
  }
  return (
    <div>
      <Typography.Title level={5} style={{ marginBottom: 6 }}>
        관련 화면
      </Typography.Title>
      <Space size={6} wrap>
        {registered.map((related) => (
          <Tag key={related.screenKey}>{related.title}</Tag>
        ))}
      </Space>
    </div>
  );
}
