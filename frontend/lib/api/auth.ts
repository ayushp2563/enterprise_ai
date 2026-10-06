import { apiClient } from "./client";
import type {
  InvitationAcceptRequest,
  LoginRequest,
  RegisterCompanyRequest,
  TokenResponse,
  User,
} from "@/types/auth";

export async function loginRequest(payload: LoginRequest) {
  return (await apiClient.post<TokenResponse>("/api/auth/login", payload)).data;
}

export async function registerCompanyRequest(payload: RegisterCompanyRequest) {
  return (
    await apiClient.post<TokenResponse>("/api/auth/register-company", payload)
  ).data;
}

export async function acceptInvitationRequest(
  payload: InvitationAcceptRequest,
) {
  return (
    await apiClient.post<TokenResponse>(
      "/api/auth/accept-invitation",
      payload,
    )
  ).data;
}

export async function getCurrentUserRequest() {
  return (await apiClient.get<User>("/api/auth/me")).data;
}

export async function logoutRequest(refreshToken: string) {
  await apiClient.post("/api/auth/logout", { refresh_token: refreshToken });
}
