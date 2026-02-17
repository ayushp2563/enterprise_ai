'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/context/AuthContext';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      // Redirect to appropriate dashboard
      if (user.role === 'company_admin') {
        router.push('/admin');
      } else if (user.role === 'hr_manager') {
        router.push('/hr');
      } else {
        router.push('/employee');
      }
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="max-w-4xl mx-auto px-4 text-center space-y-8">
        <div className="space-y-4">
          <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            Enterprise AI Assistant
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Empower your employees with instant access to company policies and HR support through intelligent AI-powered assistance
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/login">
            <Button size="lg" className="w-full sm:w-auto">
              Sign In
            </Button>
          </Link>
          <Link href="/register">
            <Button size="lg" variant="outline" className="w-full sm:w-auto">
              Register Company
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
          <div className="p-6 bg-white rounded-lg shadow-sm border">
            <div className="text-3xl mb-2">🤖</div>
            <h3 className="font-semibold mb-2">AI-Powered Q&A</h3>
            <p className="text-sm text-muted-foreground">
              Get instant answers to policy questions with confidence scoring
            </p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow-sm border">
            <div className="text-3xl mb-2">🔒</div>
            <h3 className="font-semibold mb-2">Multi-Tenant Security</h3>
            <p className="text-sm text-muted-foreground">
              Complete data isolation with role-based access control
            </p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow-sm border">
            <div className="text-3xl mb-2">📊</div>
            <h3 className="font-semibold mb-2">HR Escalation</h3>
            <p className="text-sm text-muted-foreground">
              Automatic escalation for sensitive or unusual queries
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
