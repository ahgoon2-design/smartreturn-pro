import { QuestionCircleOutlined } from "@ant-design/icons";
import { Button } from "antd";
import { useState } from "react";
import { getScreenHelp } from "../../help/smartReturnProHelpRegistry";
import { SmartHelpDrawer } from "./SmartHelpDrawer";

interface SmartHelpButtonProps {
  screenKey: string;
}

/**
 * 화면 제목 영역에 붙이는 도움말 버튼.
 * registry에 도움말이 없는 screenKey면 버튼 자체를 그리지 않는다(화면 안 깨짐).
 */
export function SmartHelpButton({ screenKey }: SmartHelpButtonProps) {
  const [open, setOpen] = useState(false);

  if (!getScreenHelp(screenKey)) {
    return null;
  }

  return (
    <>
      <Button icon={<QuestionCircleOutlined />} onClick={() => setOpen(true)}>
        도움말
      </Button>
      <SmartHelpDrawer screenKey={screenKey} open={open} onClose={() => setOpen(false)} />
    </>
  );
}
