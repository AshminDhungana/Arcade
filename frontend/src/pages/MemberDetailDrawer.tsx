import { useState } from 'react';
import { Wallet } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Table, Th, Td } from '@/components/ui/Table';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatPaise } from '@/hooks/useFormatPaise';
import { toast } from '@/store/toastStore';
import type { Member, Package, WalletTransaction } from '@/types/members';
import type { SessionResponse } from '@/types/session';
import type { MemberTab } from './Members';
import { useFeatureFlagStore } from '@/store/featureFlagStore';

interface MemberDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  member: Member;
  activeTab: MemberTab;
  onTabChange: (tab: MemberTab) => void;
  packages: Package[];
  sessions: SessionResponse[];
  walletTransactions: WalletTransaction[];
  onTopup: (member: Member, rupees: number) => Promise<void>;
  onPurchasePackage: (member: Member, pkg: Package) => Promise<void>;
  isTopupPending: boolean;
  isPurchasePending: boolean;
}

const formatDate = (iso: string) => new Date(iso).toLocaleString('en-IN', {
  day: '2-digit', month: 'short', year: 'numeric',
  hour: '2-digit', minute: '2-digit', hour12: true,
});

const formatDuration = (seconds: number) => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
};

const renderSignedAmount = (amount: number) => {
  return amount < 0 ? '-' + formatPaise(Math.abs(amount)) : formatPaise(amount);
};

export function MemberDetailDrawer({
  open,
  onClose,
  member,
  activeTab,
  onTabChange,
  packages,
  sessions,
  walletTransactions,
  onTopup,
  onPurchasePackage,
  isTopupPending,
  isPurchasePending,
}: MemberDetailDrawerProps) {
  const [topupAmount, setTopupAmount] = useState('');
  const packagesEnabled = useFeatureFlagStore((s) => s.flags.enable_packages);
  const allTabs: { id: MemberTab; label: string }[] = [
    { id: 'sessions', label: 'Sessions' },
    { id: 'wallet', label: 'Wallet' },
    { id: 'packages', label: 'Packages' },
    { id: 'topup', label: 'Top-up' },
  ];
  const visibleTabs = allTabs.filter((t) => t.id !== 'packages' || packagesEnabled);

  const handleTopupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const rupees = parseFloat(topupAmount);
    if (isNaN(rupees) || rupees <= 0) {
      toast.error('Enter a valid amount');
      return;
    }
    await onTopup(member, rupees);
    setTopupAmount('');
  };

  const renderSessionsTab = () => {
    if (sessions.length === 0) {
      return <EmptyState message="No sessions yet." />;
    }
    return (
      <Table>
        <thead>
          <tr className="border-b border-border">
            <Th>Started</Th>
            <Th>Ended</Th>
            <Th>Duration</Th>
            <Th>Status</Th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => {
            const started = new Date(s.started_at);
            const ended = s.ended_at ? new Date(s.ended_at) : null;
            const duration = ended
              ? Math.floor((ended.getTime() - started.getTime()) / 1000)
              : Math.floor((Date.now() - started.getTime()) / 1000);
            return (
              <tr key={s.id} className="border-b border-border">
                <Td className="whitespace-nowrap">{formatDate(s.started_at)}</Td>
                <Td className="whitespace-nowrap">{s.ended_at ? formatDate(s.ended_at) : 'Active'}</Td>
                <Td>{formatDuration(duration)}</Td>
                <Td className="capitalize text-muted-foreground">{s.status.toLowerCase()}</Td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    );
  };

  const renderWalletTab = () => {
    if (walletTransactions.length === 0) {
      return <EmptyState message="No wallet transactions." />;
    }
    return (
      <Table>
        <thead>
          <tr className="border-b border-border">
            <Th>Type</Th>
            <Th className="text-right">Amount</Th>
            <Th className="text-right">Balance After</Th>
            <Th>Method</Th>
            <Th className="whitespace-nowrap">Date</Th>
          </tr>
        </thead>
        <tbody>
          {walletTransactions.map((tx) => (
            <tr key={tx.id} className="border-b border-border">
              <Td className="font-medium capitalize">{tx.type.toLowerCase().replace(/_/g, ' ')}</Td>
              <Td className="text-right font-medium tabular-nums">
                {renderSignedAmount(tx.amount_paise)}
              </Td>
              <Td className="text-right tabular-nums">{formatPaise(tx.balance_after_paise)}</Td>
              <Td className="text-muted-foreground">{tx.payment_method}</Td>
              <Td className="whitespace-nowrap text-muted-foreground">{formatDate(tx.created_at)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    );
  };

  const renderPackagesTab = () => {
    if (packages.length === 0) {
      return <EmptyState message="No packages available." />;
    }
    return (
      <Table>
        <thead>
          <tr className="border-b border-border">
            <Th>Name</Th>
            <Th>Type</Th>
            <Th className="text-right">Price</Th>
            <Th>Validity</Th>
            <Th>Minutes</Th>
            <Th className="text-right">Action</Th>
          </tr>
        </thead>
        <tbody>
          {packages.filter((p) => p.is_active).map((pkg) => (
            <tr key={pkg.id} className="border-b border-border">
              <Td className="font-medium">{pkg.name}</Td>
              <Td className="text-xs text-muted-foreground capitalize">{pkg.type.toLowerCase().replace('_', ' ')}</Td>
              <Td className="text-right tabular-nums">{formatPaise(pkg.price_paise)}</Td>
              <Td className="text-muted-foreground">
                {pkg.valid_days ? `${pkg.valid_days} days` : 'No expiry'}
              </Td>
              <Td className="tabular-nums text-muted-foreground">{pkg.total_minutes}</Td>
              <Td className="text-right">
                <Button
                  variant="secondary"
                  onClick={() => onPurchasePackage(member, pkg)}
                  disabled={isPurchasePending}
                >
                  Buy
                </Button>
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
    );
  };

  const renderTopupTab = () => (
    <form onSubmit={handleTopupSubmit} className="space-y-4 max-w-sm">
      <Input
        label="Amount (₹)"
        name="topup_amount"
        type="number"
        step="1"
        min="1"
        value={topupAmount}
        onChange={(e) => setTopupAmount(e.target.value)}
        placeholder="500"
        icon={<Wallet className="h-4 w-4" />}
      />
      <div className="flex justify-end pt-2">
        <Button type="submit" variant="primary" loading={isTopupPending}>
          <Wallet className="h-4 w-4 mr-2" />
          Top Up Wallet
        </Button>
      </div>
    </form>
  );

  const title = `${member.name} · ${member.phone} · Wallet: ${formatPaise(member.wallet_balance_paise)}`;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      children={
        <div className="max-h-[60vh] overflow-y-auto">
          <Tabs value={activeTab} onValueChange={(id) => onTabChange(id as MemberTab)} className="w-full">
            <TabsList>
              {visibleTabs.map((t) => (
                <TabsTrigger key={t.id} value={t.id}>{t.label}</TabsTrigger>
              ))}
            </TabsList>
            <TabsContent value="sessions">{renderSessionsTab()}</TabsContent>
            <TabsContent value="wallet">{renderWalletTab()}</TabsContent>
            <TabsContent value="packages">{renderPackagesTab()}</TabsContent>
            <TabsContent value="topup">{renderTopupTab()}</TabsContent>
          </Tabs>
        </div>
      }
    />
  );
}
