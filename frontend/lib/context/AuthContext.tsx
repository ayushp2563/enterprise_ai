"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import {
  getCurrentUserRequest,
  loginRequest,
  logoutRequest,
  registerCompanyRequest,
} from "@/lib/api/auth";
import {
  clearSession,
  getSession,
  setSession,
} from "@/lib/api/client";
import type {
  LoginRequest,
  RegisterCompanyRequest,
  User,
} from "@/types/auth";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (payload: LoginRequest) => Promise<User>;
  registerCompany: (payload: RegisterCompanyRequest) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function homeForRole(role: User["role"]) {
  if (role === "owner") return "/admin";
  if (role === "admin") return "/hr";
  return "/employee";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let mounted = true;
    async function restore() {
      if (!getSession()) {
        setLoading(false);
        return;
      }
      try {
        const currentUser = await getCurrentUserRequest();
        if (mounted) setUser(currentUser);
      } catch {
        clearSession();
      } finally {
        if (mounted) setLoading(false);
      }
    }
    void restore();
    return () => {
      mounted = false;
    };
  }, []);

  const establishSession = useCallback(
    (response: Awaited<ReturnType<typeof loginRequest>>) => {
      setSession(response);
      setUser(response.user);
      router.replace(homeForRole(response.user.role));
      return response.user;
    },
    [router],
  );

  const login = useCallback(
    async (payload: LoginRequest) => establishSession(await loginRequest(payload)),
    [establishSession],
  );

  const registerCompany = useCallback(
    async (payload: RegisterCompanyRequest) =>
      establishSession(await registerCompanyRequest(payload)),
    [establishSession],
  );

  const logout = useCallback(async () => {
    const refreshToken = getSession()?.refresh_token;
    try {
      if (refreshToken) await logoutRequest(refreshToken);
    } finally {
      clearSession();
      setUser(null);
      router.replace("/login");
    }
  }, [router]);

  const value = useMemo(
    () => ({ user, loading, login, registerCompany, logout }),
    [user, loading, login, registerCompany, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
