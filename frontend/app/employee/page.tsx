'use client';

import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardHeader } from '@/components/layout/DashboardHeader';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function EmployeePage() {
  return (
    <ProtectedRoute allowedRoles={['employee', 'hr_manager', 'company_admin']}>
      <div className="flex flex-col h-screen">
        <DashboardHeader />
        
        <div className="flex-1 overflow-hidden p-6">
          <Tabs defaultValue="chat" className="h-full flex flex-col">
            <TabsList className="grid w-full max-w-md grid-cols-2">
              <TabsTrigger value="chat">Ask Questions</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="flex-1 mt-4">
              <Card className="h-full flex flex-col">
                <CardHeader>
                  <CardTitle>Policy Assistant</CardTitle>
                  <CardDescription>
                    Ask questions about company policies and get instant answers
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col min-h-0">
                  <ChatInterface />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="history" className="flex-1 mt-4">
              <Card className="h-full">
                <CardHeader>
                  <CardTitle>Query History</CardTitle>
                  <CardDescription>
                    View your previous questions and answers
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center text-muted-foreground py-8">
                    Query history coming soon...
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </ProtectedRoute>
  );
}
