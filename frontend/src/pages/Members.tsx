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
      BRONZE: 'bg-amber-900/50 text-amber-300',
      SILVER: 'bg-slate-200/20 text-slate-300',
      GOLD: 'bg-yellow-900/50 text-yellow-300',
    };
    return <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[tier]}`}>{tier}</span>;
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-white">Members</h1>
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <MemberSearch onSelect={handleMemberSelect} />
        </div>
        <Button variant="emerald" onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Member
        </Button>
      </div>

      {/* Members Table */}
      {members.length === 0 ? (
        <EmptyState message="No members yet. Create one or search by name/phone." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-slate-700">
              <Th className="text-left">Name</Th>
              <Th className="text-left">Phone</Th>
              <Th className="text-right">Wallet</Th>
              <Th className="text-left">Tier</Th>
              <Th className="text-right">Actions</Th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                <Td className="font-medium">{m.name}</Td>
                <Td className="text-slate-400 tabular-nums">{m.phone}</Td>
                <Td className="text-right font-medium tabular-nums text-emerald-400">
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

      {/* Create Member Modal */}
      <CreateMemberModal
        open={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateMember}
        onSuccess={handleCreateSuccess}
        isLoading={createMember.isPending}
      />

      {/* Member Detail Modal (Drawer) */}
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
    </div>
  );
}

export default MembersPage;
