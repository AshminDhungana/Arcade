import { useState } from 'react';
import { Calendar, TrendingDown, TrendingUp, ChevronDown, ChevronUp, CreditCard, Coins, ArrowDownLeft, ArrowUpRight } from 'lucide-react';
import {
  usePLSummary,
  usePLMonthly,
} from '@/api/analytics';
import { formatPaise } from '@/hooks/useFormatPaise';
import { Button } from '@/components/ui/Button';
import { Table, Th, Td } from '@/components/ui/Table';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import type { PLMonthParams } from '@/types/analytics';

const CATEGORY_LABELS: Record<string, string> = {
  RENT: 'Rent',
  ELECTRICITY: 'Electricity',
  RESTOCK: 'Restock',
  WAGES: 'Wages',
  MAINTENANCE: 'Maintenance',
  MARKETING: 'Marketing',
  OTHER: 'Other',
};

export function PLTab() {
  const [selectedMonth, setSelectedMonth] = useState<PLMonthParams>({
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
  });
  const [showMonthPicker, setShowMonthPicker] = useState(false);

  const { data: plSummary, isLoading, isError, refetch } = usePLSummary(
    selectedMonth.year === new Date().getFullYear() && selectedMonth.month === new Date().getMonth() + 1
      ? undefined
      : `${selectedMonth.year}-${String(selectedMonth.month).padStart(2, '0')}-01`,
    selectedMonth.year === new Date().getFullYear() && selectedMonth.month === new Date().getMonth() + 1
      ? undefined
      : `${selectedMonth.year}-${String(selectedMonth.month).padStart(2, '0')}-31`
  );

  const { data: monthlyPl, isLoading: monthlyLoading } = usePLMonthly(selectedMonth);

  // Use monthly data if available, otherwise use summary
  const data = monthlyPl ?? plSummary;

  if (isLoading || monthlyLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold text-foreground">Profit & Loss</h1>
        </div>
        <div className="flex h-64 items-center justify-center text-muted-foreground">Loading…</div>
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState message="Failed to load P&L data. Admin required." onRetry={refetch} />
    );
  }

  const revenue = data?.total_revenue_paise ?? 0;
  const expenses = data?.total_expenses_paise ?? 0;
  const grossProfit = data?.gross_profit_paise ?? 0;
  const netProfit = data?.net_profit_paise ?? 0;
  const expensesByCategory = data?.expenses_by_category ?? {};

  const monthLabel = new Date(selectedMonth.year, selectedMonth.month - 1).toLocaleString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-foreground">Profit & Loss</h1>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowMonthPicker(!showMonthPicker)}
              className="flex items-center gap-2"
            >
              <Calendar className="h-4 w-4" />
              {monthLabel}
              <ChevronDown className="h-4 w-4" />
            </Button>
            {showMonthPicker && (
              <div className="absolute right-0 mt-1 z-10 rounded-lg border border-border bg-popover p-2 shadow-lg">
                <div className="grid grid-cols-4 gap-1">
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                    <button
                      key={m}
                      onClick={() => {
                        setSelectedMonth((prev) => ({ ...prev, month: m }));
                        setShowMonthPicker(false);
                      }}
                      className={`px-2 py-1 text-sm rounded ${
                        m === selectedMonth.month
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-secondary'
                      }`}
                    >
                      {new Date(selectedMonth.year, m - 1).toLocaleString('en-US', { month: 'short' })}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setSelectedMonth((prev) => ({ ...prev, year: prev.year - 1 }))}
            aria-label="Previous year"
          >
            <ChevronUp className="h-4 w-4" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setSelectedMonth((prev) => ({ ...prev, year: prev.year + 1 }))}
            aria-label="Next year"
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setSelectedMonth({ year: new Date().getFullYear(), month: new Date().getMonth() + 1 })}
          >
            This Month
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          title="Total Revenue"
          value={formatPaise(revenue)}
          icon={<CreditCard className="h-5 w-5 text-emerald-400" />}
          trend={<TrendingUp className="h-4 w-4 text-emerald-400" />}
        />
        <SummaryCard
          title="Total Expenses"
          value={formatPaise(expenses)}
          icon={<Coins className="h-5 w-5 text-red-400" />}
          trend={<TrendingDown className="h-4 w-4 text-red-400" />}
        />
        <SummaryCard
          title="Gross Profit"
          value={formatPaise(grossProfit)}
          icon={<ArrowUpRight className="h-5 w-5 text-blue-400" />}
        />
        <SummaryCard
          title="Net Profit"
          value={formatPaise(netProfit)}
          icon={netProfit >= 0 ? (
            <ArrowUpRight className="h-5 w-5 text-emerald-400" />
          ) : (
            <ArrowDownLeft className="h-5 w-5 text-red-400" />
          )}
          isNegative={netProfit < 0}
        />
      </div>

      {/* Category Breakdown */}
      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="mb-4 text-lg font-medium text-foreground">Expenses by Category</h2>
        {Object.keys(expensesByCategory).length === 0 ? (
          <EmptyState message="No expenses recorded for this period." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-border">
                <Th className="text-left">Category</Th>
                <Th className="text-right">Amount</Th>
                <Th className="text-right">% of Expenses</Th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(expensesByCategory)
                .sort(([, a], [, b]) => b - a)
                .map(([category, amount]) => (
                  <tr key={category} className="border-b border-border hover:bg-secondary">
                    <Td className="font-medium capitalize">{CATEGORY_LABELS[category] ?? category}</Td>
                    <Td className="text-right font-mono text-foreground">{formatPaise(amount)}</Td>
                    <Td className="text-right text-muted-foreground">
                      {expenses > 0 ? ((amount / expenses) * 100).toFixed(1) : '0'}%
                    </Td>
                  </tr>
                ))}
              <tr className="border-t border-border font-semibold">
                <Td>Total</Td>
                <Td className="text-right font-mono text-foreground">{formatPaise(expenses)}</Td>
                <Td className="text-right text-muted-foreground">100%</Td>
              </tr>
            </tbody>
          </Table>
        )}
      </section>
    </div>
  );
}

interface SummaryCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  trend?: React.ReactNode;
  isNegative?: boolean;
}

function SummaryCard({ title, value, icon, trend, isNegative = false }: SummaryCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">{title}</div>
        <div className="p-2 rounded-lg bg-secondary/50">{icon}</div>
      </div>
      <div className="mt-3 flex items-baseline justify-between gap-2">
        <div className={`text-2xl font-bold ${isNegative ? 'text-red-400' : 'text-foreground'}`}>
          {value}
        </div>
        {trend && <div className="text-sm">{trend}</div>}
      </div>
    </div>
  );
}

export default PLTab;
