'use client';

import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardHeader } from '@/components/layout/DashboardHeader';
import { DocumentUpload } from '@/components/admin/DocumentUpload';
import { DocumentList } from '@/components/admin/DocumentList';
import { EmployeeList } from '@/components/admin/EmployeeList';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useCategories } from '@/lib/hooks/useDocuments';
import { FileText, Users, Settings } from 'lucide-react';

export default function AdminPage() {
  const { data: categories = [] } = useCategories();

  return (
    <ProtectedRoute allowedRoles={['company_admin']}>
      <div className="flex flex-col h-screen">
        <DashboardHeader />
        
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            <div>
              <h2 className="text-3xl font-bold tracking-tight">Admin Dashboard</h2>
              <p className="text-muted-foreground">
                Manage your company's documents, employees, and settings
              </p>
            </div>

            <Tabs defaultValue="documents" className="space-y-6">
              <TabsList className="grid w-full max-w-md grid-cols-3">
                <TabsTrigger value="documents">
                  <FileText className="w-4 h-4 mr-2" />
                  Documents
                </TabsTrigger>
                <TabsTrigger value="employees">
                  <Users className="w-4 h-4 mr-2" />
                  Employees
                </TabsTrigger>
                <TabsTrigger value="settings">
                  <Settings className="w-4 h-4 mr-2" />
                  Settings
                </TabsTrigger>
              </TabsList>

              <TabsContent value="documents" className="space-y-6">
                <div className="grid gap-6 md:grid-cols-2">
                  <DocumentUpload categories={categories} />
                  <div className="md:col-span-2">
                    <DocumentList />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="employees">
                <EmployeeList />
              </TabsContent>

              <TabsContent value="settings">
                <div className="text-center py-12 text-muted-foreground">
                  <Settings className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <h3 className="text-lg font-semibold mb-2">Settings Coming Soon</h3>
                  <p className="text-sm">
                    Company settings and configuration options will be available here
                  </p>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
