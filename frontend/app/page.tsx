'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/context/AuthContext';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { MessageSquare, Shield, Bell } from 'lucide-react';

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
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen relative overflow-hidden">
      {/* Decorative background blobs */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-primary/20 blur-[120px] animate-pulse-glow" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] rounded-full bg-purple-500/20 blur-[100px] animate-float animation-delay-2000" />

      <div className="z-10 max-w-5xl mx-auto px-4 text-center space-y-12 animate-fade-in-up">
        <div className="space-y-6">
          <div className="inline-flex items-center rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-sm font-medium text-primary mb-4 backdrop-blur-md">
            ✨ Next-Generation Policy Management
          </div>
          <h1 className="text-6xl md:text-7xl font-bold tracking-tight bg-gradient-to-br from-foreground via-foreground/90 to-muted-foreground/50 bg-clip-text text-transparent font-sans" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
            Enterprise AI Assistant
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto leading-relaxed font-light">
            Empower your team with instant, intelligent answers to company policies and seamless HR support through an advanced RAG architecture.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          <Link href="/login">
            <Button size="lg" className="w-full sm:w-auto text-lg h-14 px-8 rounded-xl shadow-[0_0_20px_rgba(37,99,235,0.3)] hover:shadow-[0_0_30px_rgba(37,99,235,0.5)] transition-all duration-300 hover:-translate-y-1">
              Sign In to Workspace
            </Button>
          </Link>
          <Link href="/register">
            <Button size="lg" variant="outline" className="w-full sm:w-auto text-lg h-14 px-8 rounded-xl glass-panel hover:bg-muted/50 transition-all duration-300 hover:-translate-y-1">
              Register Company
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-24 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
          <div className="glass-panel p-8 rounded-2xl text-left hover:bg-white/5 dark:hover:bg-white/5 transition-all duration-300 hover:-translate-y-2 group cursor-default">
            <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 group-hover:bg-primary group-hover:text-primary-foreground shadow-lg shadow-primary/20">
              <MessageSquare className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold mb-3 tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>AI-Powered Q&A</h3>
            <p className="text-muted-foreground leading-relaxed">
              Get instant, highly accurate answers to complex policy questions backed by confidence scoring and source citations.
            </p>
          </div>
          <div className="glass-panel p-8 rounded-2xl text-left hover:bg-white/5 dark:hover:bg-white/5 transition-all duration-300 hover:-translate-y-2 group cursor-default">
            <div className="h-12 w-12 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 group-hover:bg-purple-600 group-hover:text-white shadow-lg shadow-purple-500/20">
              <Shield className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold mb-3 tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>Multi-Tenant Security</h3>
            <p className="text-muted-foreground leading-relaxed">
              Enterprise-grade data isolation with robust role-based access control protecting sensitive company documents.
            </p>
          </div>
          <div className="glass-panel p-8 rounded-2xl text-left hover:bg-white/5 dark:hover:bg-white/5 transition-all duration-300 hover:-translate-y-2 group cursor-default">
            <div className="h-12 w-12 rounded-xl bg-orange-500/10 text-orange-600 dark:text-orange-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 group-hover:bg-orange-600 group-hover:text-white shadow-lg shadow-orange-500/20">
              <Bell className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold mb-3 tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>HR Escalation</h3>
            <p className="text-muted-foreground leading-relaxed">
              Intelligent automatic routing and escalation for sensitive or unusual queries seamlessly handled by human HR staff.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
