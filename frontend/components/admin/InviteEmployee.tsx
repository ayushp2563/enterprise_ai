'use client';

import { useState } from 'react';
import { useInviteUser } from '@/lib/hooks/useUsers';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { UserPlus, Loader2, Copy, Check } from 'lucide-react';

export function InviteEmployee() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<'employee' | 'hr_manager'>('employee');
  const [invitationLink, setInvitationLink] = useState('');
  const [copied, setCopied] = useState(false);

  const { mutate: inviteUser, isPending } = useInviteUser();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    inviteUser(
      { email, full_name: fullName, role },
      {
        onSuccess: (data) => {
          const link = `${window.location.origin}/accept-invitation?token=${data.invitation_token}`;
          setInvitationLink(link);
          toast.success(`Invitation sent to ${email}`);
          
          // Reset form but keep dialog open to show invitation link
          setEmail('');
          setFullName('');
          setRole('employee');
        },
        onError: (error: any) => {
          toast.error(error.response?.data?.detail || 'Failed to send invitation');
        },
      }
    );
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(invitationLink);
    setCopied(true);
    toast.success('Invitation link copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setOpen(false);
    setInvitationLink('');
    setEmail('');
    setFullName('');
    setRole('employee');
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <UserPlus className="mr-2 h-4 w-4" />
          Invite Employee
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Invite Employee</DialogTitle>
          <DialogDescription>
            Send an invitation to a new team member. They'll receive an email with a link to set up their account.
          </DialogDescription>
        </DialogHeader>

        {invitationLink ? (
          <div className="space-y-4">
            <div className="bg-muted p-4 rounded-lg">
              <p className="text-sm font-medium mb-2">Invitation Link</p>
              <div className="flex items-center gap-2">
                <Input value={invitationLink} readOnly className="font-mono text-xs" />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={copyToClipboard}
                >
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Share this link with the invitee. It expires in 7 days.
              </p>
            </div>
            <DialogFooter>
              <Button onClick={handleClose}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="fullName">Full Name *</Label>
                <Input
                  id="fullName"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Doe"
                  required
                  disabled={isPending}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email *</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@company.com"
                  required
                  disabled={isPending}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="role">Role *</Label>
                <Select value={role} onValueChange={(value: any) => setRole(value)} disabled={isPending}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="employee">Employee</SelectItem>
                    <SelectItem value="hr_manager">HR Manager</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose} disabled={isPending}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Send Invitation
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
