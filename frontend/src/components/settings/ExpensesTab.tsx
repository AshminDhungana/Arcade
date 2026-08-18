import { useState } from 'react';
import { Plus, Trash2, Calendar, FileText } from 'lucide-react';
import {
  useExpenses,
  useCreateExpense,
  useDeleteExpense,
} from '@/api/settings';
import { Button } from '@/components/ui/Button';
import { Table, Th, Td } from '@/components/ui/Table';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { toast } from '@/store/toastStore';
import { formatPaise } from '@/hooks/useFormatPaise';
import type { Expense, ExpenseCategory } from '@/types/settings';

const CATEGORY_OPTIONS: { value: ExpenseCategory; label: string }[] = [
  { value: 'RENT', label: 'Rent' },
  { value: 'ELECTRICITY', label: 'Electricity' },
  { value: 'RESTOCK', label: 'Restock' },
  { value: 'WAGES', label: 'Wages' },
  { value: 'MAINTENANCE', label: 'Maintenance' },
  { value: 'MARKETING', label: 'Marketing' },
  { value: 'OTHER', label: 'Other' },
];

interface ExpenseFormData {
  date: string;
  category: ExpenseCategory;
  amount_paise: number;
  note: string;
}

function ExpenseFormModal({
  open,
  onClose,
  title,
  onSubmit,
  isLoading,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  onSubmit: (data: ExpenseFormData) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<ExpenseFormData>({
    date: new Date().toISOString().split('T')[0],
    category: 'OTHER',
    amount_paise: 0,
    note: '',
  });
  const [errors, setErrors] = useState<Partial<Record<keyof ExpenseFormData, string>>>({});

  const handleChange = (field: keyof ExpenseFormData, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof ExpenseFormData, string>> = {};
    if (!formData.date) newErrors.date = 'Date is required';
    if (!formData.category) newErrors.category = 'Category is required';
    if (!formData.amount_paise || formData.amount_paise <= 0) {
      newErrors.amount_paise = 'Amount must be greater than 0';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    onSubmit(formData);
  };

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="date" className="mb-1 block text-sm font-medium text-foreground">
            Date
          </label>
          <input
            id="date"
            type="date"
            value={formData.date}
            onChange={(e) => handleChange('date', e.target.value)}
            className="w-full rounded-lg border border-input bg-popover py-2.5 px-3 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
            aria-invalid={!!errors.date}
          />
          {errors.date && (
            <p role="alert" className="mt-1 flex items-center gap-1 text-xs text-red-400">
              {errors.date}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="category" className="mb-1 block text-sm font-medium text-foreground">
            Category
          </label>
          <select
            id="category"
            value={formData.category}
            onChange={(e) => handleChange('category', e.target.value as ExpenseCategory)}
            className="w-full rounded-lg border border-input bg-popover py-2.5 px-3 pr-8 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
            aria-invalid={!!errors.category}
          >
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {errors.category && (
            <p role="alert" className="mt-1 flex items-center gap-1 text-xs text-red-400">
              {errors.category}
            </p>
          )}
        </div>

        <Input
          name="amount"
          label="Amount (in currency units, e.g. 5000.00)"
          type="number"
          step="0.01"
          min="0.01"
          value={formData.amount_paise / 100}
          onChange={(e) => handleChange('amount_paise', Math.round(parseFloat(e.target.value || '0') * 100))}
          error={errors.amount_paise ?? null}
          placeholder="5000.00"
          autoFocus
        />

        <Input
          name="note"
          label="Note (optional)"
          value={formData.note}
          onChange={(e) => handleChange('note', e.target.value)}
          placeholder="e.g. August rent"
          maxLength={1000}
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="emerald" loading={isLoading}>
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ConfirmationModal({
  open,
  onClose,
  title,
  message,
  confirmLabel,
  onConfirm,
  isLoading,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  isLoading: boolean;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="mb-4 text-foreground">{message}</p>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose} disabled={isLoading}>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm} loading={isLoading}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

function categoryBadge(category: ExpenseCategory) {
  const variants: Record<ExpenseCategory, string> = {
    RENT: 'bg-purple-900/30 text-purple-300',
    ELECTRICITY: 'bg-yellow-900/30 text-yellow-300',
    RESTOCK: 'bg-blue-900/30 text-blue-300',
    WAGES: 'bg-emerald-900/30 text-emerald-300',
    MAINTENANCE: 'bg-orange-900/30 text-orange-300',
    MARKETING: 'bg-pink-900/30 text-pink-300',
    OTHER: 'bg-secondary text-muted-foreground',
  };
  const labels: Record<ExpenseCategory, string> = {
    RENT: 'Rent',
    ELECTRICITY: 'Electricity',
    RESTOCK: 'Restock',
    WAGES: 'Wages',
    MAINTENANCE: 'Maintenance',
    MARKETING: 'Marketing',
    OTHER: 'Other',
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variants[category]}`}>
      {labels[category]}
    </span>
  );
}

export function ExpensesTab() {
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmExpenseId, setConfirmExpenseId] = useState<string | null>(null);
  const [confirmExpenseNote, setConfirmExpenseNote] = useState('');

  const { data: expenses = [], isLoading, isError, refetch } = useExpenses();
  const createExpense = useCreateExpense();
  const deleteExpense = useDeleteExpense();

  const handleSubmit = async (data: ExpenseFormData) => {
    try {
      await createExpense.mutateAsync({
        date: data.date,
        category: data.category,
        amount_paise: data.amount_paise,
        note: data.note || null,
      });
      toast.success('Expense created successfully');
      setModalOpen(false);
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create expense';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  const openDeleteConfirm = (expense: Expense) => {
    setConfirmExpenseId(expense.id);
    setConfirmExpenseNote(expense.note ?? `Expense ${expense.id}`);
    setConfirmOpen(true);
  };

  const handleDelete = async () => {
    if (!confirmExpenseId) return;
    try {
      await deleteExpense.mutateAsync(confirmExpenseId);
      toast.success('Expense deleted');
      setConfirmOpen(false);
      setConfirmExpenseId(null);
      setConfirmExpenseNote('');
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete expense';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold text-foreground">Expenses</h1>
        </div>
        <div className="flex h-64 items-center justify-center text-muted-foreground">Loading…</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-foreground">Expenses</h1>
        <Button variant="emerald" onClick={() => setModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Expense
        </Button>
      </div>

      {isError && <ErrorState message="Failed to load expenses. Admin required." onRetry={refetch} />}

      <section className="rounded-xl border border-border bg-card p-5">
        {expenses.length === 0 ? (
          <EmptyState message="No expenses yet. Add one to get started." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-border">
                <Th className="text-left">Date</Th>
                <Th className="text-left">Category</Th>
                <Th className="text-right">Amount</Th>
                <Th className="text-left">Note</Th>
                <Th className="text-left">Logged By</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((expense) => (
                <tr key={expense.id} className="border-b border-border hover:bg-secondary">
                  <Td className="font-medium">
                    <Calendar className="h-4 w-4 mr-1 inline-block" />
                    {new Date(expense.date).toLocaleDateString()}
                  </Td>
                  <Td>{categoryBadge(expense.category)}</Td>
                  <Td className="text-right font-mono text-foreground">
                    {formatPaise(expense.amount_paise)}
                  </Td>
                  <Td className="max-w-xs truncate">
                    {expense.note ? (
                      <>
                        <FileText className="h-4 w-4 mr-1 inline-block text-muted-foreground" />
                        {expense.note}
                      </>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </Td>
                  <Td>{expense.logged_by_staff_name ?? expense.logged_by_staff_id}</Td>
                  <Td className="text-right">
                    <Button
                      variant="secondary"
                      size="sm"
                      aria-label={`Delete expense ${expense.id}`}
                      onClick={() => openDeleteConfirm(expense)}
                      disabled={deleteExpense.isPending}
                    >
                      <Trash2 className="h-4 w-4 text-red-400" />
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </section>

      {/* Create Expense Modal */}
      <ExpenseFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Add Expense"
        onSubmit={handleSubmit}
        isLoading={createExpense.isPending}
      />

      {/* Delete Confirmation Modal */}
      {confirmOpen && confirmExpenseId && (
        <ConfirmationModal
          open={confirmOpen}
          onClose={() => {
            setConfirmOpen(false);
            setConfirmExpenseId(null);
            setConfirmExpenseNote('');
          }}
          title="Delete Expense"
          message={`Are you sure you want to delete "${confirmExpenseNote}"? This action cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={handleDelete}
          isLoading={deleteExpense.isPending}
        />
      )}
    </div>
  );
}

export default ExpensesTab;
