'use client';

import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardHeader } from '@/components/layout/DashboardHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function HRPage() {
  return (
    <ProtectedRoute allowedRoles={['hr_manager', 'company_admin']}>
      <div className="flex flex-col h-screen">
        <DashboardHeader />
        
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            <div>
              <h2 className="text-3xl font-bold tracking-tight">HR Dashboard</h2>
              <p className="text-muted-foreground">
                Manage escalations and view analytics
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Escalation Queue</CardTitle>
                  <CardDescription>Review and respond to escalated queries</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">Coming soon</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Analytics</CardTitle>
                  <CardDescription>View query metrics and insights</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">Coming soon</p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
