import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { changePassword as changePasswordApi, fetchAuthContext, login as loginApi } from "../api/auth";
import { clearStoredAccessToken, hasStoredAccessToken, setStoredAccessToken, setUnauthorizedHandler } from "../api/client";
import type { AuthContextResponse, ChangePasswordRequest, ChangePasswordResponse, LoginRequest } from "../types/auth";

interface AuthContextValue {
  loading: boolean;
  authContext: AuthContextResponse | null;
  isAuthenticated: boolean;
  role: string;
  permissions: string[];
  mustChangePassword: boolean;
  error: string;
  login: (request: LoginRequest) => Promise<AuthContextResponse>;
  logout: () => void;
  refreshAuthContext: () => Promise<AuthContextResponse | null>;
  changePassword: (request: ChangePasswordRequest) => Promise<ChangePasswordResponse>;
  hasPermission: (permission: string) => boolean;
  canAccess: (permissions?: string[]) => boolean;
  clearAuth: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(hasStoredAccessToken());
  const [authContext, setAuthContext] = useState<AuthContextResponse | null>(null);
  const [error, setError] = useState("");

  const clearAuth = useCallback(() => {
    clearStoredAccessToken();
    setAuthContext(null);
  }, []);

  const refreshAuthContext = useCallback(async () => {
    if (!hasStoredAccessToken()) {
      setAuthContext(null);
      setLoading(false);
      return null;
    }
    setLoading(true);
    setError("");
    try {
      const nextContext = await fetchAuthContext();
      setAuthContext(nextContext);
      return nextContext;
    } catch {
      clearAuth();
      setError("인증 정보를 확인하지 못했습니다. 다시 로그인해 주세요.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [clearAuth]);

  const login = useCallback(
    async (request: LoginRequest) => {
      setLoading(true);
      setError("");
      try {
        const response = await loginApi(request);
        setStoredAccessToken(response.access_token);
        const nextContext = await refreshAuthContext();
        if (!nextContext) {
          throw new Error("AUTH_CONTEXT_LOAD_FAILED");
        }
        return nextContext;
      } catch (err) {
        clearAuth();
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [clearAuth, refreshAuthContext],
  );

  const changePassword = useCallback(
    async (request: ChangePasswordRequest) => {
      const response = await changePasswordApi(request);
      await refreshAuthContext();
      return response;
    },
    [refreshAuthContext],
  );

  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setAuthContext(null);
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    void refreshAuthContext();
  }, [refreshAuthContext]);

  const permissions = authContext?.permissions || [];
  const role = authContext?.roles?.[0] || "";
  const mustChangePassword = Boolean(authContext?.must_change_password);

  const hasPermission = useCallback(
    (permission: string) => {
      if (authContext?.roles?.includes("SUPER_ADMIN")) {
        return true;
      }
      return permissions.includes(permission);
    },
    [authContext?.roles, permissions],
  );

  const canAccess = useCallback(
    (requiredPermissions?: string[]) => {
      if (!requiredPermissions || requiredPermissions.length === 0) {
        return true;
      }
      return requiredPermissions.every((permission) => hasPermission(permission));
    },
    [hasPermission],
  );

  const value = useMemo(
    () => ({
      loading,
      authContext,
      isAuthenticated: Boolean(authContext),
      role,
      permissions,
      mustChangePassword,
      error,
      login,
      logout,
      refreshAuthContext,
      changePassword,
      hasPermission,
      canAccess,
      clearAuth,
    }),
    [
      authContext,
      canAccess,
      changePassword,
      clearAuth,
      error,
      hasPermission,
      loading,
      login,
      logout,
      mustChangePassword,
      permissions,
      refreshAuthContext,
      role,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth는 AuthProvider 안에서만 사용할 수 있습니다.");
  }
  return value;
}
