import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { fetchAuthContext } from "../api/auth";
import { clearStoredAccessToken, hasStoredAccessToken } from "../api/client";
import type { AuthContextResponse } from "../types/auth";

interface AuthContextValue {
  loading: boolean;
  authContext: AuthContextResponse | null;
  isAuthenticated: boolean;
  refreshAuthContext: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(false);
  const [authContext, setAuthContext] = useState<AuthContextResponse | null>(null);

  const refreshAuthContext = useCallback(async () => {
    if (!hasStoredAccessToken()) {
      setAuthContext(null);
      return;
    }
    setLoading(true);
    try {
      const nextContext = await fetchAuthContext();
      setAuthContext(nextContext);
    } catch {
      setAuthContext(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    clearStoredAccessToken();
    setAuthContext(null);
  }, []);

  useEffect(() => {
    void refreshAuthContext();
  }, [refreshAuthContext]);

  const value = useMemo(
    () => ({
      loading,
      authContext,
      isAuthenticated: Boolean(authContext),
      refreshAuthContext,
      logout,
    }),
    [authContext, loading, logout, refreshAuthContext],
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
