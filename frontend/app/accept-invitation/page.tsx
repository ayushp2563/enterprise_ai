"use client";

import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import { toast } from "sonner";

import { acceptInvitationRequest } from "@/lib/api/auth";
import { setSession } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function InvitationForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const token = searchParams.get("token") || "";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      toast.error("Invitation token is missing");
      return;
    }
    setSubmitting(true);
    try {
      const response = await acceptInvitationRequest({
        token,
        full_name: fullName,
        password,
      });
      setSession(response);
      toast.success("Invitation accepted");
      router.replace(response.user.role === "member" ? "/employee" : "/admin");
    } catch (error: unknown) {
      toast.error(
        axios.isAxiosError(error)
          ? error.response?.data?.detail || "Invitation could not be accepted"
          : "Invitation could not be accepted",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Join your organization</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="full-name">Full name</Label>
              <Input
                id="full-name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Account password</Label>
              <Input
                id="password"
                type="password"
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                Existing users must enter their current password.
              </p>
            </div>
            <Button className="w-full" disabled={submitting || !token}>
              {submitting ? "Joining…" : "Accept invitation"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}

export default function AcceptInvitationPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center">Loading invitation…</div>}>
      <InvitationForm />
    </Suspense>
  );
}
