import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { authApi, authStorage } from "../api/client";
import type { AuthUser } from "../types/api";

interface AuthContextValue {
  user: AuthUser | null;
  login: (organization: string, username: string, password: string) => Promise<void>;
  register: (payload: {
    organization_name: string;
    industry?: string;
    username: string;
    email: string;
    password: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => authStorage.user());
  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      login: async (organization, username, password) => {
        const tokens = await authApi.login(organization, username, password);
        authStorage.save(tokens);
        setUser(tokens.user);
      },
      register: async (payload) => {
        const tokens = await authApi.register(payload);
        authStorage.save(tokens);
        setUser(tokens.user);
      },
      logout: async () => {
        const refresh = authStorage.refresh();
        try {
          if (refresh) await authApi.logout(refresh);
        } finally {
          authStorage.clear();
          setUser(null);
        }
      },
    }),
    [user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
