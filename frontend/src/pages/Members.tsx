import { useState } from 'react';
import { Plus } from 'lucide-react';
import { useMembers, useCreateMember, useTopupWallet, usePackages, usePurchasePackage, useMemberSessions, useWalletTransactions } from '@/api/members';
import { MemberSearch } from '@/components/MemberSearch';
import { CreateMemberModal } from './CreateMemberModal';
import { MemberDetailDrawer } from './MemberDetailDrawer';
import { formatPaise } from '@/hooks/useFormatPaise';
import { Button } from '@/components/ui/Button';
import { Table, Th, Td } from '@/components/ui/Table';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { toast } from '@/store/toastStore';
import type { Member, Package, MemberTier } from '@/types/members';

export type MemberTab = 'sessions' | 'wallet' | 'packages' | 'topup';

export function MembersPage() {
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<MemberTab>('sessions');

  const { data: members = [], isLoading, isError, refetch } = useMembers('');
  const createMember = useCreateMember();
  const topupWallet = useTopupWallet();
  const { data: packages = [] } = usePackages();
  const purchasePackage = usePurchasePackage();

  const memberSessions = useMemberSessions(selectedMember?.id ?? '');
  const walletTransactions = useWalletTransactions(selectedMember?.id ?? '');

  const handleMemberSelect = (member: Member) => {
    setSelectedMember(member);
    setActiveTab('sessions');
  };

  const handleCreateMember = async (name: string, phone: string) => {
    try {
      await createMember.mutateAsync({ name, phone });
      toast.success('Member created successfully');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create member';
      if (msg.includes('409')) {
        toast.error('A member with that phone already exists.');
      } else {
        toast.error(msg);
      }
      throw err;
    }
  };

  const handleCreateSuccess = () => {
    setIsCreateModalOpen(false);
    refetch();
  };

  const handleTopup = async (member: Member, rupees: number) => {
    if (rupees <= 0) {
      toast.error('Amount must be positive');
      return;
    }
    const amount_paise = Math.round(rupees * 100);
    try {
      await topupWallet.mutateAsync({ id: member.id, amount_paise, payment_method: 'CASH' });
      toast.success(`₹${rupees.toFixed(2)} added to wallet`);
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to top up wallet';
      toast.error(msg);
    }
  };

  const handlePurchasePackage = async (member: Member, pkg: Package) => {
    try {
      await purchasePackage.mutateAsync({ id: member.id, package_id: pkg.id, payment_method: 'WALLET' });
      toast.success(`Purchased ${pkg.name}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to purchase package';
      toast.error(msg);
    }
  };

  const renderMemberTier = (tier: MemberTier) => {
    const colors: Record<MemberTier, string> = {
      BRONZE: 'bg-warning/15 text-warning',
      SILVER: 'bg-muted text-muted-foreground',
      GOLD: 'bg-success/15 text-success',
    };
    return <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[tier]}`}>{tier}</span>;
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState message="Failed to load members." onRetry={() => refetch()} />
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-20 border-b border-border bg-card/95 px-6 py-4 backdrop-blur-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="text-xl font-bold text-foreground">Members</h1>
          <div className="flex w-full flex-1 flex-col gap-3 sm:max-w-2xl sm:flex-row sm:items-center">
            <div className="w-full sm:flex-1 sm:max-w-md">
              <MemberSearch onSelect={handleMemberSelect} />
            </div>
            <Button variant="emerald" className="w-full sm:w-auto" onClick={() => setIsCreateModalOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Member
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl space-y-6 p-6">
        {members.length === 0 ? (
          <EmptyState message="No members yet. Create one or search by name/phone." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-border">
                <Th className="text-left">Name</Th>
                <Th className="text-left">Phone</Th>
                <Th className="text-right">Wallet</Th>
                <Th className="text-left">Tier</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id} className="border-b border-border hover:bg-secondary/50">
                  <Td className="font-medium">{m.name}</Td>
                  <Td className="text-muted-foreground tabular-nums">{m.phone}</Td>
                  <Td className="text-right font-medium tabular-nums text-success">
                    {formatPaise(m.wallet_balance_paise)}
                  </Td>
                  <Td>{renderMemberTier(m.tier)}</Td>
                  <Td className="text-right">
                    <Button
                      variant="secondary"
                      onClick={() => handleMemberSelect(m)}
                    >
                      Manage
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}

        <CreateMemberModal
          open={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSubmit={handleCreateMember}
          onSuccess={handleCreateSuccess}
          isLoading={createMember.isPending}
        />

        {selectedMember && (
          <MemberDetailDrawer
            open={true}
            onClose={() => setSelectedMember(null)}
            member={selectedMember}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            packages={packages}
            sessions={memberSessions.data ?? []}
            walletTransactions={walletTransactions.data ?? []}
            onTopup={handleTopup}
            onPurchasePackage={handlePurchasePackage}
            isTopupPending={topupWallet.isPending}
            isPurchasePending={purchasePackage.isPending}
          />
        )}
      </main>
    </div>
  );
}

export default MembersPage;
