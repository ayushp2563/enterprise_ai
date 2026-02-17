'use client';

import { useState } from 'react';
import { useUsers, useDeactivateUser } from '@/lib/hooks/useUsers';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { InviteEmployee } from './InviteEmployee';
import { toast } from 'sonner';
import { Users, Loader2, UserX, CheckCircle2, XCircle } from 'lucide-react';
import { format } from 'date-fns';

export function EmployeeList() {
  const { data: users, isLoading } = useUsers();
  const { mutate: deactivateUser, isPending: isDeactivating } = useDeactivateUser();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDeactivate, setUserToDeactivate] = useState<number | null>(null);

  const handleDeactivate = () => {
    if (userToDeactivate) {
      deactivateUser(userToDeactivate, {
        onSuccess: () => {
          toast.success('User deactivated successfully');
          setDeleteDialogOpen(false);
          setUserToDeactivate(null);
        },
        onError: (error: any) => {
          toast.error(error.response?.data?.detail || 'Failed to deactivate user');
        },
      });
    }
  };

  const getRoleBadge = (role: string) => {
    const variants: Record<string, { variant: any; label: string }> = {
      company_admin: { variant: 'default', label: 'Admin' },
      hr_manager: { variant: 'secondary', label: 'HR Manager' },
      employee: { variant: 'outline', label: 'Employee' },
    };
    const config = variants[role] || variants.employee;
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Employees</CardTitle>
              <CardDescription>Manage your team members and their roles</CardDescription>
            </div>
            <InviteEmployee />
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : !Array.isArray(users) || users.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No employees yet</p>
              <p className="text-sm mt-2">Invite your first team member to get started</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Array.isArray(users) && users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.full_name}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>{getRoleBadge(user.role)}</TableCell>
                    <TableCell>
                      {user.is_active ? (
                        <div className="flex items-center gap-1 text-green-600">
                          <CheckCircle2 className="w-4 h-4" />
                          <span className="text-sm">Active</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <XCircle className="w-4 h-4" />
                          <span className="text-sm">Inactive</span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {format(new Date(user.created_at), 'MMM d, yyyy')}
                    </TableCell>
                    <TableCell className="text-right">
                      {user.is_active && user.role !== 'company_admin' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setUserToDeactivate(user.id);
                            setDeleteDialogOpen(true);
                          }}
                          disabled={isDeactivating}
                        >
                          <UserX className="w-4 h-4 mr-2" />
                          Deactivate
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deactivate User</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to deactivate this user? They will no longer be able to access the system.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeactivate} className="bg-destructive text-destructive-foreground">
              Deactivate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
