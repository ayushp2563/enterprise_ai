'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    domain: '',
    admin_email: '',
    admin_password: '',
    admin_full_name: '',
  });
  const [loading, setLoading] = useState(false);
  const { registerCompany } = useAuth();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Auto-generate slug from company name
    if (name === 'name') {
      const slug = value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/(^-|-$)/g, '');
      setFormData((prev) => ({ ...prev, slug }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await registerCompany(formData);
      toast.success('Company registered successfully!');
    } catch (error: any) {
      console.error('Registration error:', error);
      const errorMessage = error.response?.data?.detail || 'Registration failed. Please try again.';
      toast.error(Array.isArray(errorMessage) ? errorMessage[0].msg : errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8">
      <Card className="w-full max-w-2xl">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">Register your company</CardTitle>
          <CardDescription>
            Create a new workspace for your organization
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2 col-span-2">
                <Label htmlFor="name">Company Name *</Label>
                <Input
                  id="name"
                  name="name"
                  placeholder="Acme Corporation"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  disabled={loading}
                />
              </div>

              <div className="space-y-2 col-span-2">
                <Label htmlFor="slug">Company Slug *</Label>
                <Input
                  id="slug"
                  name="slug"
                  placeholder="acme-corp"
                  value={formData.slug}
                  onChange={handleChange}
                  required
                  disabled={loading}
                  pattern="[a-z0-9-]+"
                />
                <p className="text-xs text-muted-foreground">
                  Used in URLs. Only lowercase letters, numbers, and hyphens.
                </p>
              </div>

              <div className="space-y-2 col-span-2">
                <Label htmlFor="domain">Company Domain</Label>
                <Input
                  id="domain"
                  name="domain"
                  placeholder="acme.com"
                  value={formData.domain}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>

              <div className="space-y-2 col-span-2">
                <Label htmlFor="admin_full_name">Admin Full Name *</Label>
                <Input
                  id="admin_full_name"
                  name="admin_full_name"
                  placeholder="John Doe"
                  value={formData.admin_full_name}
                  onChange={handleChange}
                  required
                  disabled={loading}
                />
              </div>

              <div className="space-y-2 col-span-2">
                <Label htmlFor="admin_email">Admin Email *</Label>
                <Input
                  id="admin_email"
                  name="admin_email"
                  type="email"
                  placeholder="admin@acme.com"
                  value={formData.admin_email}
                  onChange={handleChange}
                  required
                  disabled={loading}
                />
              </div>

              <div className="space-y-2 col-span-2">
                <Label htmlFor="admin_password">Admin Password *</Label>
                <Input
                  id="admin_password"
                  name="admin_password"
                  type="password"
                  placeholder="••••••••"
                  value={formData.admin_password}
                  onChange={handleChange}
                  required
                  minLength={8}
                  maxLength={15}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  Minimum 8 characters, maximum 15 characters
                </p>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Company
            </Button>
            <div className="text-sm text-center text-muted-foreground">
              Already have an account?{' '}
              <Link href="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
