import { useEffect, useState, useCallback } from 'react';
import type { Seat } from '@/types/seat';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { POSPanel } from './pos/POSPanel';
import { CheckoutPanel } from './invoice/CheckoutPanel';
import { X, ShoppingCart, CreditCard, Terminal } from 'lucide-react';

type DrawerTab = 'pos' | 'checkout' | 'commands';

interface SessionDrawerProps {
  seat: Seat;
  sessionId: string;
  onClose: () => void;
}

/** Slide-out drawer for IN_USE seats — contains POS, Checkout, and Commands tabs. */
export function SessionDrawer({ seat, sessionId, onClose }: SessionDrawerProps) {
  const posEnabled = useFeatureFlagStore((s) => s.flags.enable_pos);
  const [activeTab, setActiveTab] = useState<DrawerTab>(posEnabled ? 'pos' : 'checkout');
  const [isOpen, setIsOpen] = useState(false);

  // Animate open on mount
  useEffect(() => {
    // Small delay to trigger CSS transition
    const timer = setTimeout(() => setIsOpen(true), 10);
    return () => clearTimeout(timer);
  }, []);

  // Close with animation
  const handleClose = useCallback(() => {
    setIsOpen(false);
    setTimeout(onClose, 300); // Wait for slide-out animation
  }, [onClose]);

  // Escape key handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleClose]);

  // Available tabs (POS only if enabled)
  const tabs: { id: DrawerTab; label: string; icon: React.ReactNode }[] = [
    ...(posEnabled
      ? [{ id: 'pos' as DrawerTab, label: 'POS', icon: <ShoppingCart className="h-4 w-4" /> }]
      : []),
    { id: 'checkout', label: 'Checkout', icon: <CreditCard className="h-4 w-4" /> },
    { id: 'commands', label: 'Commands', icon: <Terminal className="h-4 w-4" /> },
  ];

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0'
        }`}
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-2xl flex-col border-l border-slate-700 bg-slate-900 shadow-2xl transition-transform duration-300 ease-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        {/* Header */}
        <header className="flex items-center justify-between border-b border-slate-700 bg-slate-800 px-5 py-4">
          <div>
            <h2 id="drawer-title" className="text-lg font-bold text-white">
              {seat.name}
            </h2>
            <p className="text-xs text-slate-400">
              Session active · {seat.is_console ? 'Console' : 'PC'}
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-700 hover:text-white"
            aria-label="Close drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        {/* Tab switcher */}
        <nav className="flex overflow-x-auto border-b border-slate-700 bg-slate-800/50 px-5" aria-label="Drawer tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex shrink-0 items-center gap-2 whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:border-slate-600 hover:text-slate-200'
              }`}
              aria-selected={activeTab === tab.id}
              role="tab"
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Tab content */}
        <div className="flex-1 overflow-hidden p-5">
          {activeTab === 'pos' && posEnabled && (
            <POSPanel sessionId={sessionId} />
          )}
          {activeTab === 'checkout' && (
            <CheckoutPanel sessionId={sessionId} onClose={handleClose} />
          )}
          {activeTab === 'commands' && (
            <PlaceholderTab
              icon={<Terminal className="h-8 w-8" />}
              title="Commands"
              description="Remote commands and seat controls coming in a future update"
            />
          )}
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Placeholder tab content
// ---------------------------------------------------------------------------

function PlaceholderTab({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="mb-4 rounded-2xl bg-slate-800 p-5 text-slate-500">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-slate-300">{title}</h3>
      <p className="mt-2 max-w-xs text-sm text-slate-500">{description}</p>
    </div>
  );
}
