import { useState } from 'react';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import {
  useMenuItems,
  useCreateMenuItem,
  useUpdateMenuItem,
  useDeleteMenuItem,
} from '@/api/settings';
import { Button } from '@/components/ui/Button';
import { Table, Th, Td } from '@/components/ui/Table';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Switch } from '@/components/ui/Switch';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { formatPaise } from '@/hooks/useFormatPaise';
import { toast } from '@/store/toastStore';
import type { MenuItem } from '@/types/settings';

interface MenuFormData {
  name: string;
  category: string;
  price: string; // rupees, as typed
  stock_quantity: string;
  low_stock_threshold: string;
  is_available: boolean;
}

function emptyForm(): MenuFormData {
  return {
    name: '',
    category: '',
    price: '',
    stock_quantity: '',
    low_stock_threshold: '',
    is_available: true,
  };
}

function formFromItem(item: MenuItem): MenuFormData {
  return {
    name: item.name,
    category: item.category ?? '',
    price: (item.price_paise / 100).toFixed(2),
    stock_quantity: item.stock_quantity == null ? '' : String(item.stock_quantity),
    low_stock_threshold:
      item.low_stock_threshold == null ? '' : String(item.low_stock_threshold),
    is_available: item.is_available,
  };
}

function isAuthError(msg: string): boolean {
  return msg.includes('403') || msg.includes('401');
}

function MenuFormModal({
  open,
  onClose,
  title,
  initial,
  submitLabel,
  onSubmit,
  isLoading,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  initial: MenuFormData;
  submitLabel: string;
  onSubmit: (payload: Omit<MenuItem, 'id'>) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<MenuFormData>(initial);
  const [errors, setErrors] = useState<Partial<Record<keyof MenuFormData, string>>>({});

  const handleChange = (field: keyof MenuFormData, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const validate = (): boolean => {
    const next: Partial<Record<keyof MenuFormData, string>> = {};
    if (!formData.name.trim()) next.name = 'Name is required';
    const priceNum = Number(formData.price);
    if (formData.price === '' || Number.isNaN(priceNum)) {
      next.price = 'Price is required';
    } else if (priceNum < 0) {
      next.price = 'Price cannot be negative';
    }
    if (formData.stock_quantity !== '' && Number(formData.stock_quantity) < 0) {
      next.stock_quantity = 'Stock cannot be negative';
    }
    if (formData.low_stock_threshold !== '' && Number(formData.low_stock_threshold) < 0) {
      next.low_stock_threshold = 'Threshold cannot be negative';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    onSubmit({
      name: formData.name.trim(),
      category: formData.category.trim() === '' ? null : formData.category.trim(),
      price_paise: Math.round(Number(formData.price) * 100),
      stock_quantity:
        formData.stock_quantity === '' ? null : Number(formData.stock_quantity),
      low_stock_threshold:
        formData.low_stock_threshold === '' ? null : Number(formData.low_stock_threshold),
      is_available: formData.is_available,
    });
  };

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          name="name"
          label="Name"
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          error={errors.name ?? null}
          placeholder="e.g. Cola"
          autoFocus
        />
        <Input
          name="category"
          label="Category (optional)"
          value={formData.category}
          onChange={(e) => handleChange('category', e.target.value)}
          placeholder="e.g. Beverages"
        />
        <Input
          name="price"
          label="Price (Rs.)"
          type="number"
          step="0.01"
          min="0"
          value={formData.price}
          onChange={(e) => handleChange('price', e.target.value)}
          error={errors.price ?? null}
          placeholder="0.00"
        />
        <Input
          name="stock_quantity"
          label="Stock quantity (optional)"
          type="number"
          min="0"
          value={formData.stock_quantity}
          onChange={(e) => handleChange('stock_quantity', e.target.value)}
          error={errors.stock_quantity ?? null}
          placeholder="e.g. 50"
        />
        <Input
          name="low_stock_threshold"
          label="Low stock threshold (optional)"
          type="number"
          min="0"
          value={formData.low_stock_threshold}
          onChange={(e) => handleChange('low_stock_threshold', e.target.value)}
          error={errors.low_stock_threshold ?? null}
          placeholder="e.g. 10"
        />
        <Switch
          checked={formData.is_available}
          onCheckedChange={(v) => handleChange('is_available', v)}
          label="Available"
          description="Show this item as available for sale"
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="emerald" loading={isLoading}>
            {submitLabel}
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
      <p className="mb-4 text-slate-300">{message}</p>
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

function availabilityBadge(isAvailable: boolean) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        isAvailable
          ? 'bg-emerald-900/30 text-emerald-300'
          : 'bg-slate-700 text-slate-400'
      }`}
    >
      {isAvailable ? 'Available' : 'Unavailable'}
    </span>
  );
}

export function MenuTab() {
  const [addOpen, setAddOpen] = useState(false);
  const [editItem, setEditItem] = useState<MenuItem | null>(null);
  const [deleteItem, setDeleteItem] = useState<MenuItem | null>(null);

  const { data: items = [], isLoading, isError, refetch } = useMenuItems();
  const createItem = useCreateMenuItem();
  const updateItem = useUpdateMenuItem();
  const deleteItemMut = useDeleteMenuItem();

  const handleError = (err: unknown, fallback: string) => {
    const msg = err instanceof Error ? err.message : fallback;
    toast.error(isAuthError(msg) ? 'Admin required' : msg);
  };

  const handleCreate = async (payload: Omit<MenuItem, 'id'>) => {
    try {
      await createItem.mutateAsync(payload);
      toast.success('Menu item created');
      setAddOpen(false);
      refetch();
    } catch (err) {
      handleError(err, 'Failed to create menu item');
    }
  };

  const handleUpdate = async (payload: Omit<MenuItem, 'id'>) => {
    if (!editItem) return;
    try {
      await updateItem.mutateAsync({ id: editItem.id, data: payload });
      toast.success('Menu item updated');
      setEditItem(null);
      refetch();
    } catch (err) {
      handleError(err, 'Failed to update menu item');
    }
  };

  const handleToggleAvailable = async (item: MenuItem) => {
    try {
      await updateItem.mutateAsync({
        id: item.id,
        data: { is_available: !item.is_available },
      });
      toast.success(item.is_available ? 'Item marked unavailable' : 'Item marked available');
      refetch();
    } catch (err) {
      handleError(err, 'Failed to update availability');
    }
  };

  const handleDelete = async () => {
    if (!deleteItem) return;
    try {
      await deleteItemMut.mutateAsync(deleteItem.id);
      toast.success(`${deleteItem.name} deleted`);
      setDeleteItem(null);
      refetch();
    } catch (err) {
      handleError(err, 'Failed to delete menu item');
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold text-white">Menu</h1>
        </div>
        <div className="flex h-64 items-center justify-center text-slate-400">Loading…</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-white">Menu</h1>
        <Button variant="emerald" onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Item
        </Button>
      </div>

      {isError && (
        <ErrorState message="Failed to load menu. Admin required." onRetry={refetch} />
      )}

      <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        {items.length === 0 ? (
          <EmptyState message="No menu items yet. Add one to get started." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-slate-700">
                <Th className="text-left">Name</Th>
                <Th className="text-left">Category</Th>
                <Th className="text-right">Price</Th>
                <Th className="text-left">Available</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                  <Td className="font-medium">{item.name}</Td>
                  <Td>{item.category ?? '—'}</Td>
                  <Td className="text-right tabular-nums">{formatPaise(item.price_paise)}</Td>
                  <Td>
                    <div className="flex items-center gap-3">
                      <Switch
                        checked={item.is_available}
                        disabled={updateItem.isPending}
                        onCheckedChange={() => handleToggleAvailable(item)}
                        label={`Toggle availability for ${item.name}`}
                      />
                      {availabilityBadge(item.is_available)}
                    </div>
                  </Td>
                  <Td className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="secondary"
                        aria-label={`Edit ${item.name}`}
                        onClick={() => setEditItem(item)}
                      >
                        <Pencil className="h-4 w-4 mr-1" />
                        Edit
                      </Button>
                      <Button
                        variant="danger"
                        aria-label={`Delete ${item.name}`}
                        onClick={() => setDeleteItem(item)}
                        disabled={deleteItemMut.isPending}
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        Delete
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </section>

      {/* Add Item Modal */}
      {addOpen && (
        <MenuFormModal
          open={addOpen}
          onClose={() => setAddOpen(false)}
          title="Add Menu Item"
          initial={emptyForm()}
          submitLabel="Create"
          onSubmit={handleCreate}
          isLoading={createItem.isPending}
        />
      )}

      {/* Edit Item Modal */}
      {editItem && (
        <MenuFormModal
          open={!!editItem}
          onClose={() => setEditItem(null)}
          title="Edit Menu Item"
          initial={formFromItem(editItem)}
          submitLabel="Save"
          onSubmit={handleUpdate}
          isLoading={updateItem.isPending}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteItem && (
        <ConfirmationModal
          open={!!deleteItem}
          onClose={() => setDeleteItem(null)}
          title="Delete Menu Item"
          message={`Are you sure you want to delete "${deleteItem.name}"? This cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={handleDelete}
          isLoading={deleteItemMut.isPending}
        />
      )}
    </div>
  );
}

export default MenuTab;
