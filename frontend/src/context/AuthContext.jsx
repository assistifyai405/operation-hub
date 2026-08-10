import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi, clearLegacyTokenStorage, bootstrapSession } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = unauth, object = authed

  const bootstrap = useCallback(async () => {
    clearLegacyTokenStorage();
    try {
      const u = await bootstrapSession();
      if (u) {
        setUser(u);
        return;
      }
    } catch (_) {
      /* fall through */
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch (_) {
      setUser(false);
    }
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const login = useCallback(async (email, password, remember = true) => {
    clearLegacyTokenStorage();
    const data = await authApi.login({ email, password, remember });
    setUser(data.user);
    return data;
  }, []);

  const register = useCallback(async (payload) => {
    clearLegacyTokenStorage();
    const data = await authApi.register(payload);
    setUser(data.user);
    return data;
  }, []);

  const demo = useCallback(async () => {
    clearLegacyTokenStorage();
    const data = await authApi.demo();
    setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (_) {
      /* ignore */
    }
    clearLegacyTokenStorage();
    setUser(false);
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await authApi.me();
    setUser(me);
    return me;
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser, login, register, demo, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
