import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";
import type { User } from "@/types/auth";

type MembershipRole = User["role"];

interface InvitationCreated {
  id: number;
  company_id: number;
  email: string;
  role: MembershipRole;
  invitation_token: string;
  expires_at: string;
}

export function useUsers() {
  return useQuery({
    queryKey: ["users"],
    queryFn: async () => (await apiClient.get<User[]>("/api/users/")).data,
  });
}

export function useInviteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      email: string;
      role: "member" | "admin";
      full_name?: string;
    }) =>
      (
        await apiClient.post<InvitationCreated>("/api/users/invite", {
          email: payload.email,
          role: payload.role,
        })
      ).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: number) => {
      await apiClient.delete(`/api/users/${userId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });
}
