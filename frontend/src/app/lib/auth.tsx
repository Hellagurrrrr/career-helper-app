import React from "react";
import { apiRequest, clearTokens, errorMessage, getAccessToken, getRefreshToken, setTokens } from "./api";
import { queryClient } from "./query-client";

/** Drop every cached server query. Called when the session ends so the next
 *  user (or the logged-out app) never sees the previous user's data. */
function clearServerCache() {
  queryClient.clear();
}

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  createdAt: number;
};

export type AuthResult = { ok: true } | { ok: false; error: string };

type AuthResponse = {
  user: AuthUser;
  tokens: { accessToken: string; refreshToken: string };
};

type AuthContextValue = {
  currentUser: AuthUser | null;
  loading: boolean;
  register: (input: { name: string; email: string; password: string }) => Promise<AuthResult>;
  login: (email: string, password: string) => Promise<AuthResult>;
  logout: () => Promise<void>;
  changePassword: (current: string, next: string) => Promise<AuthResult>;
  deleteAccount: () => Promise<void>;
  resetDemoData: () => Promise<AuthResult>;
  updateNotificationPreference: (enabled: boolean) => Promise<AuthResult>;
  refreshCurrentUser: () => Promise<void>;
};

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = React.useState<AuthUser | null>(null);
  const [loading, setLoading] = React.useState(() => Boolean(getAccessToken() || getRefreshToken()));

  const refreshCurrentUser = React.useCallback(async () => {
    if (!getAccessToken() && !getRefreshToken()) {
      setCurrentUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const user = await apiRequest<AuthUser>("/auth/me");
      setCurrentUser(user);
    } catch {
      clearTokens();
      setCurrentUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refreshCurrentUser();
  }, [refreshCurrentUser]);

  const register = React.useCallback(
    async ({ name, email, password }: { name: string; email: string; password: string }): Promise<AuthResult> => {
      try {
        const response = await apiRequest<AuthResponse>("/auth/register", {
          method: "POST",
          auth: false,
          body: { name, email, password },
        });
        setTokens(response.tokens);
        setCurrentUser(response.user);
        return { ok: true };
      } catch (error) {
        return { ok: false, error: errorMessage(error, "Registration failed.") };
      }
    },
    []
  );

  const login = React.useCallback(async (email: string, password: string): Promise<AuthResult> => {
    try {
      const response = await apiRequest<AuthResponse>("/auth/login", {
        method: "POST",
        auth: false,
        body: { email, password },
      });
      setTokens(response.tokens);
      setCurrentUser(response.user);
      return { ok: true };
    } catch (error) {
      return { ok: false, error: errorMessage(error, "Sign in failed.") };
    }
  }, []);

  const logout = React.useCallback(async () => {
    try {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        await apiRequest<void>("/auth/logout", {
          method: "POST",
          body: { refreshToken },
        });
      }
    } catch {
      // Local logout should still complete if the server token is already invalid.
    } finally {
      clearTokens();
      setCurrentUser(null);
      clearServerCache();
    }
  }, []);

  const changePassword = React.useCallback(async (current: string, next: string): Promise<AuthResult> => {
    try {
      await apiRequest("/settings/password", {
        method: "POST",
        body: { currentPassword: current, newPassword: next },
      });
      clearTokens();
      setCurrentUser(null);
      clearServerCache();
      return { ok: true };
    } catch (error) {
      return { ok: false, error: errorMessage(error, "Password update failed.") };
    }
  }, []);

  const deleteAccount = React.useCallback(async () => {
    try {
      await apiRequest<void>("/settings/account", { method: "DELETE" });
    } finally {
      clearTokens();
      setCurrentUser(null);
      clearServerCache();
    }
  }, []);

  const resetDemoData = React.useCallback(async (): Promise<AuthResult> => {
    try {
      await apiRequest("/settings/reset-demo-data", { method: "POST" });
      // Account stays, demo data is wiped server-side -> refetch everything.
      void queryClient.invalidateQueries();
      return { ok: true };
    } catch (error) {
      return { ok: false, error: errorMessage(error, "Reset failed.") };
    }
  }, []);

  const updateNotificationPreference = React.useCallback(async (enabled: boolean): Promise<AuthResult> => {
    try {
      await apiRequest("/settings/notifications", {
        method: "PUT",
        body: { enabled },
      });
      return { ok: true };
    } catch (error) {
      return { ok: false, error: errorMessage(error, "Could not update notification preference.") };
    }
  }, []);

  const value = React.useMemo(
    () => ({
      currentUser,
      loading,
      register,
      login,
      logout,
      changePassword,
      deleteAccount,
      resetDemoData,
      updateNotificationPreference,
      refreshCurrentUser,
    }),
    [
      currentUser,
      loading,
      register,
      login,
      logout,
      changePassword,
      deleteAccount,
      resetDemoData,
      updateNotificationPreference,
      refreshCurrentUser,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return ctx;
}
