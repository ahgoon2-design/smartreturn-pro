import { LockOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Form, Input, Space, Typography } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { ROUTE_PATHS } from "../../routes/routePaths";
import type { ChangePasswordRequest } from "../../types/auth";

export function PasswordChangeRequiredPage() {
  const [form] = Form.useForm<ChangePasswordRequest>();
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { changePassword, logout } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(values: ChangePasswordRequest) {
    setSubmitting(true);
    setErrorMessage("");
    setNotice("");
    try {
      await changePassword(values);
      setNotice("비밀번호가 변경되었습니다.");
      navigate(ROUTE_PATHS.importPreview, { replace: true });
    } catch (error) {
      setErrorMessage(toPasswordErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  function handleLogout() {
    logout();
    navigate(ROUTE_PATHS.login, { replace: true });
  }

  return (
    <main className="smart-auth-page">
      <Card className="smart-auth-card">
        <Typography.Text className="smart-app-eyebrow">SmartReturn Pro</Typography.Text>
        <Typography.Title level={3}>비밀번호 변경 필요</Typography.Title>
        <Typography.Paragraph type="secondary">계속 사용하려면 먼저 비밀번호를 변경해 주세요.</Typography.Paragraph>
        {errorMessage ? <Alert className="smart-error-notice" type="error" message={errorMessage} showIcon /> : null}
        {notice ? <Alert className="smart-error-notice" type="success" message={notice} showIcon /> : null}
        <Form form={form} layout="vertical" onFinish={handleSubmit} autoComplete="off">
          <Form.Item label="현재 비밀번호" name="current_password" rules={[{ required: true, message: "현재 비밀번호를 입력해 주세요." }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Form.Item label="새 비밀번호" name="new_password" rules={[{ required: true, message: "새 비밀번호를 입력해 주세요." }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            label="새 비밀번호 확인"
            name="new_password_confirm"
            dependencies={["new_password"]}
            rules={[
              { required: true, message: "새 비밀번호를 한 번 더 입력해 주세요." },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("new_password") === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error("새 비밀번호가 서로 다릅니다."));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} autoComplete="new-password" />
          </Form.Item>
          <Space className="smart-auth-actions">
            <Button type="primary" htmlType="submit" loading={submitting}>
              변경
            </Button>
            <Button onClick={handleLogout}>로그아웃</Button>
          </Space>
        </Form>
      </Card>
    </main>
  );
}

function toPasswordErrorMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.resultCode === "VALIDATION_ERROR") {
      return "입력값을 다시 확인해 주세요.";
    }
    return error.message || "비밀번호 변경 중 오류가 발생했습니다.";
  }
  return "비밀번호 변경 중 오류가 발생했습니다.";
}
