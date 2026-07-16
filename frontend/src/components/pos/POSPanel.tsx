import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { useMenu, useSessionItems, useAddPosItem, useRemovePosItem } from '@/api/pos';
import { MenuGrid } from './MenuGrid';
import { SessionTab } from './SessionTab';

interface POSPanelProps {
  sessionId: string;
}

/** POS Panel orchestrator — wires menu grid and session tab with mutations.
 *  Gated by the `enable_pos` feature flag. */
export function POSPanel({ sessionId }: POSPanelProps) {
  const posEnabled = useFeatureFlagStore((s) => s.flags.enable_pos);
  const inventoryEnabled = useFeatureFlagStore((s) => s.flags.enable_inventory);

  const menuQuery = useMenu();
  const sessionItemsQuery = useSessionItems(sessionId);
  const addMutation = useAddPosItem();
  const removeMutation = useRemovePosItem();

  const isMutating = addMutation.isPending || removeMutation.isPending;

  // Guard: if POS is disabled, render nothing
  if (!posEnabled) {
    return null;
  }

  const handleAddItem = (menuItemId: string) => {
    addMutation.mutate({
      session_id: sessionId,
      menu_item_id: menuItemId,
      quantity: 1,
    });
  };

  const handleRemoveOne = (posItemId: string, sid: string) => {
    removeMutation.mutate({ posItemId, sessionId: sid });
  };

  const handleRemoveAll = (_menuItemId: string, sid: string, posItemIds: string[]) => {
    // Remove all rows for this menu item
    for (const id of posItemIds) {
      removeMutation.mutate({ posItemId: id, sessionId: sid });
    }
  };

  return (
    <div className="flex h-full flex-col gap-4 md:flex-row" data-testid="pos-panel">
      {/* Menu Grid — left side */}
      <div className="flex-1 min-w-0 md:flex-[3]">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Menu
        </h3>
        <MenuGrid
          items={menuQuery.data}
          isLoading={menuQuery.isLoading}
          isError={menuQuery.isError}
          onRetry={() => menuQuery.refetch()}
          onAddItem={handleAddItem}
          inventoryEnabled={inventoryEnabled}
        />
      </div>

      {/* Session Tab — right side */}
      <div className="flex-1 min-w-0 border-l border-slate-700/50 pl-4 md:flex-[2] md:border-l md:pl-4">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Session Tab
        </h3>
        <SessionTab
          items={sessionItemsQuery.data}
          menuItems={menuQuery.data}
          isLoading={sessionItemsQuery.isLoading}
          isError={sessionItemsQuery.isError}
          onRetry={() => sessionItemsQuery.refetch()}
          onAdd={handleAddItem}
          onRemoveOne={handleRemoveOne}
          onRemoveAll={handleRemoveAll}
          isMutating={isMutating}
        />
      </div>

      {/* Error toasts (inline) */}
      {addMutation.isError && (
        <div className="fixed bottom-4 right-4 z-[60] rounded-lg border border-red-800/50 bg-red-900/90 px-4 py-3 text-sm text-red-200 shadow-xl backdrop-blur-sm">
          {addMutation.error.message}
        </div>
      )}
      {removeMutation.isError && (
        <div className="fixed bottom-4 right-4 z-[60] rounded-lg border border-red-800/50 bg-red-900/90 px-4 py-3 text-sm text-red-200 shadow-xl backdrop-blur-sm">
          {removeMutation.error.message}
        </div>
      )}
    </div>
  );
}
