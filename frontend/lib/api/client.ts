import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import type { TokenResponse } from "@/types/auth";

const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SESSION_KEY = "enterprise-ai-session";

type StoredSession = Pick<TokenResponse, "access_token" | "refresh_token">;

let session: StoredSession | null = null;
let refreshPromise: Promise<string> | null = null;

if (typeof window !== "undefined") {
  const stored = window.sessionStorage.getItem(SESSION_KEY);
  if (stored) {
    try {
      session = JSON.parse(stored) as StoredSession;
    } catch {
      window.sessionStorage.removeItem(SESSION_KEY);
    }
  }
}

export const apiClient = axios.create({
  baseURL,
  timeout: 60_000,
});

export function getSession() {
  return session;
}

export function setSession(tokens: StoredSession) {
  session = tokens;
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(tokens));
  }
}

export function clearSession() {
  session = null;
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(SESSION_KEY);
  }
}

apiClient.interceptors.request.use((config) => {
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

async function refreshAccessToken() {
  if (!session?.refresh_token) {
    throw new Error("No refresh session");
  }
  const response = await axios.post<TokenResponse>(
    `${baseURL}/api/auth/refresh`,
    { refresh_token: session.refresh_token },
    { timeout: 30_000 },
  );
  setSession(response.data);
  return response.data.access_token;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as (InternalAxiosRequestConfig & {
      _retried?: boolean;
    }) | undefined;
    if (error.response?.status !== 401 || !request || request._retried) {
      throw error;
    }

    request._retried = true;
    refreshPromise ??= refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
    try {
      request.headers.Authorization = `Bearer ${await refreshPromise}`;
      return await apiClient(request);
    } catch (refreshError) {
      clearSession();
      throw refreshError;
    }
  },
);
