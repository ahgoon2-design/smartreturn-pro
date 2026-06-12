import { CheckCircleOutlined, LockOutlined, ScanOutlined, ShopOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Checkbox, Form, Input, Typography } from "antd";
import type { InputRef } from "antd";
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiClientError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { resolveHomePathForUser } from "../../routes/RouteGuard";
import { ROUTE_PATHS } from "../../routes/routePaths";
import type { AuthContextResponse, LoginRequest } from "../../types/auth";

interface LocationState {
  from?: {
    pathname?: string;
  };
}

// 마지막 로그인 ID만 기억한다. 비밀번호는 절대 저장하지 않는다.
const LAST_LOGIN_ID_STORAGE_KEY = "smartreturn.pro.lastLoginId";

const HERO_METRICS = [
  { icon: <ScanOutlined />, label: "반품 처리", value: "운송장 스캔 기반 입고/판정" },
  { icon: <CheckCircleOutlined />, label: "재고 반영", value: "일마감 이후 안전 반영" },
  { icon: <ShopOutlined />, label: "고객 포털", value: "고객사는 자기 자료만 조회" },
];

const IDLE_STATUS = "사용자 ID와 비밀번호로 로그인하세요.";
const LOADING_STATUS = "사용자 정보를 확인하고 있습니다.";

export function LoginPage() {
  const [form] = Form.useForm<LoginRequest>();
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [rememberLoginId, setRememberLoginId] = useState(() => Boolean(readLastLoginId()));
  const loginIdInputRef = useRef<InputRef | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState | null;

  useEffect(() => {
    const lastLoginId = readLastLoginId();
    if (lastLoginId) {
      form.setFieldsValue({ login_id: lastLoginId });
    }
    loginIdInputRef.current?.focus({ cursor: "end" });
  }, [form]);

  async function handleSubmit(values: LoginRequest) {
    setSubmitting(true);
    setErrorMessage("");
    try {
      const context = await login(values);
      persistLastLoginId(rememberLoginId ? values.login_id : null);
      if (context.must_change_password) {
        navigate(ROUTE_PATHS.passwordChange, { replace: true });
        return;
      }
      navigate(resolvePostLoginPath(context, state?.from?.pathname), { replace: true });
    } catch (error) {
      setErrorMessage(toLoginErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  const statusType = errorMessage ? "error" : submitting ? "info" : "info";
  const statusText = errorMessage || (submitting ? LOADING_STATUS : IDLE_STATUS);

  return (
    <main className="smart-auth-page">
      <div className="smart-auth-login-panel">
        <section className="smart-auth-login-hero" aria-label="SmartReturn Pro 소개">
          <Typography.Text className="smart-app-eyebrow">SmartReturn Pro</Typography.Text>
          <Typography.Title level={2} className="smart-auth-login-title">
            반품 운영 플랫폼 로그인
          </Typography.Title>
          <Typography.Paragraph type="secondary" className="smart-auth-login-desc">
            반품 입고, 판정, 일마감, 재고 반영을 한 흐름으로 관리합니다.
          </Typography.Paragraph>
          <div className="smart-auth-login-metrics">
            {HERO_METRICS.map((metric) => (
              <div key={metric.label} className="smart-auth-login-metric">
                <span className="smart-auth-login-metric-icon">{metric.icon}</span>
                <div>
                  <Typography.Text type="secondary" className="smart-auth-login-metric-label">
                    {metric.label}
                  </Typography.Text>
                  <Typography.Text strong className="smart-auth-login-metric-value">
                    {metric.value}
                  </Typography.Text>
                </div>
              </div>
            ))}
          </div>
        </section>

        <Card className="smart-auth-card smart-auth-login-card">
          <Typography.Title level={4} className="smart-auth-login-form-title">
            계정 확인
          </Typography.Title>
          <Form form={form} layout="vertical" onFinish={handleSubmit} autoComplete="off" requiredMark={false}>
            <Form.Item label="사용자 ID" name="login_id" rules={[{ required: true, message: "사용자 ID를 입력해 주세요." }]}>
              <Input
                ref={loginIdInputRef}
                size="large"
                prefix={<UserOutlined />}
                placeholder="사용자 ID"
                autoComplete="username"
              />
            </Form.Item>
            <Form.Item label="비밀번호" name="password" rules={[{ required: true, message: "비밀번호를 입력해 주세요." }]}>
              <Input.Password size="large" prefix={<LockOutlined />} placeholder="비밀번호" autoComplete="current-password" />
            </Form.Item>
            <div className="smart-auth-login-actions">
              <Checkbox checked={rememberLoginId} onChange={(event) => setRememberLoginId(event.target.checked)}>
                마지막 로그인 ID 기억
              </Checkbox>
              <Button type="primary" size="large" htmlType="submit" loading={submitting} className="smart-auth-login-submit">
                {submitting ? "확인 중" : "로그인"}
              </Button>
            </div>
          </Form>
          <Alert
            className="smart-auth-login-status"
            type={statusType}
            showIcon
            message={statusText}
            role={errorMessage ? "alert" : "status"}
          />
        </Card>
      </div>
    </main>
  );
}

function readLastLoginId() {
  try {
    return localStorage.getItem(LAST_LOGIN_ID_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

function persistLastLoginId(loginId: string | null) {
  try {
    if (loginId && loginId.trim()) {
      localStorage.setItem(LAST_LOGIN_ID_STORAGE_KEY, loginId.trim());
    } else {
      localStorage.removeItem(LAST_LOGIN_ID_STORAGE_KEY);
    }
  } catch {
    // localStorage를 쓸 수 없는 환경에서도 로그인 자체는 막지 않는다.
  }
}

function resolvePostLoginPath(context: AuthContextResponse, fromPath?: string) {
  const home = resolveHomePathForUser({
    isClientUser: context.is_client_user,
    isInternalUser: context.is_internal_user,
    isPlatformAdmin: context.is_platform_admin,
  });
  // 고객 사용자는 직전 내부 경로로 되돌리지 않고 고객 포털로 보낸다.
  if (context.is_client_user) {
    return home;
  }
  if (!fromPath || fromPath === ROUTE_PATHS.login || fromPath === ROUTE_PATHS.passwordChange) {
    return home;
  }
  return fromPath;
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
