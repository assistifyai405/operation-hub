import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi, setAccessToken, getAccessToken } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = unauth, object = authed

  const bootstrap = useCallback(async () => {
    try {
      if (getAccessToken()) {
        const me = await authApi.me();
        setUser(me);
        return;
      }
    } catch (_) { /* fall through to refresh */ }
    try {
      const data = await authApi.refresh();
      setAccessToken(data.accessToken, true);
      setUser(data.user);
    } catch (_) {
      setAccessToken(null);
      setUser(false);
    }
  }, []);

  useEffect(() => { bootstrap(); }, [bootstrap]);

  const login = useCallback(async (email, password, remember = true) => {
    const data = await authApi.login({ email, password, remember });
    setAccessToken(data.accessToken, remember);
    setUser(data.user);
    return data;
  }, []);

  const register = useCallback(async (payload) => {
    const data = await authApi.register(payload);
    setAccessToken(data.accessToken, true);
    setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch (_) {}
    setAccessToken(null);
    setUser(false);
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await authApi.me();
    setUser(me);
    return me;
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
