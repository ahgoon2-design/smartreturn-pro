import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { ROUTE_PATHS } from "../../routes/routePaths";
import type { LoginRequest } from "../../types/auth";

interface LocationState {
  from?: {
    pathname?: string;
  };
}

export function LoginPage() {
  const [form] = Form.useForm<LoginRequest>();
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState | null;

  async function handleSubmit(values: LoginRequest) {
    setSubmitting(true);
    setErrorMessage("");
    try {
      const context = await login(values);
      if (context.must_change_password) {
        navigate(ROUTE_PATHS.passwordChange, { replace: true });
        return;
      }
      navigate(resolveRedirectPath(state?.from?.pathname), { replace: true });
    } catch (error) {
      setErrorMessage(toLoginErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="smart-auth-page">
      <Card className="smart-auth-card">
        <Typography.Text className="smart-app-eyebrow">SmartReturn Pro</Typography.Text>
        <Typography.Title level={3}>로그인</Typography.Title>
        <Typography.Paragraph type="secondary">
          반품 전문 흐름과 OMS/WMS 운영을 함께 보는 통합 플랫폼입니다.
        </Typography.Paragraph>
        {errorMessage ? <Alert className="smart-error-notice" type="error" message={errorMessage} showIcon /> : null}
        <Form form={form} layout="vertical" onFinish={handleSubmit} autoComplete="off">
          <Form.Item label="사용자 ID" name="login_id" rules={[{ required: true, message: "사용자 ID를 입력해 주세요." }]}>
            <Input prefix={<UserOutlined />} placeholder="login_id" autoComplete="username" />
          </Form.Item>
          <Form.Item label="비밀번호" name="password" rules={[{ required: true, message: "비밀번호를 입력해 주세요." }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="비밀번호" autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting} block>
            로그인
          </Button>
        </Form>
      </Card>
    </main>
  );
}

function resolveRedirectPath(path?: string) {
  if (!path || path === ROUTE_PATHS.login || path === ROUTE_PATHS.passwordChange) {
    return ROUTE_PATHS.dashboard;
  }
  return path;
}

function toLoginErrorMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.status === 401 || error.resultCode === "LOGIN_FAILED") {
      return "사용자 ID 또는 비밀번호를 확인해 주세요.";
    }
    if (error.status === 422 || error.resultCode === "VALIDATION_ERROR") {
      return "입력값을 다시 확인해 주세요.";
    }
    return error.message || "로그인 중 오류가 발생했습니다.";
  }
  return "로그인 중 오류가 발생했습니다.";
}
