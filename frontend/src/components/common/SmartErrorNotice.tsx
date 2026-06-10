import { Alert } from "antd";

export function SmartErrorNotice({ message }: { message?: string }) {
  if (!message) {
    return null;
  }
  return <Alert className="smart-error-notice" type="error" message={message} showIcon />;
}
