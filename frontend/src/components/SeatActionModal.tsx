import type { Seat } from '@/types/seat';
import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { Loader2, Play, Power, Settings, ShoppingCart, Heart, User, X, Lock, Unlock } from 'lucide-react';
import { MemberSearch } from './MemberSearch';
import { useStartSession } from '@/api/sessions';
import { generateEnrollCode, regenerateOverridePin, forceOverlay, setMaintenance, clearMaintenance, useSeat } from '@/api/seats';
import { toast } from '@/store/toastStore';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { useAuthStore } from '@/store/authStore';
import type { Member } from '@/types/members';

interface SeatActionModalProps {
  seat: Seat;
  onClose: () => void;
}

/** Modal displayed when a seat card is clicked.
 *  Displays seat details and a list of available actions.
 *  For AVAILABLE seats, shows MemberSearch to pick a member before starting a session. */
export function SeatActionModal({ seat, onClose }: SeatActionModalProps) {
  const [member, setMember] = useState<Member | null>(null);
  const [assignedMinutes, setAssignedMinutes] = useState<string>('');
  const [forceOverlayLoading, setForceOverlayLoading] = useState<'on' | 'off' | null>(null);
  const [maintenanceMode, setMaintenanceMode] = useState<'idle' | 'note'>('idle');
  const [maintenanceNote, setMaintenanceNote] = useState('');
  const [maintenancePending, setMaintenancePending] = useState(false);
  const [now, setNow] = useState<Date>(() => new Date());
  const startSession = useStartSession();
  const memberRequired = useFeatureFlagStore((s) => s.flags.require_member_for_session);
  const assignedTimeEnabled = useFeatureFlagStore((s) => s.flags.enable_assigned_time_limit);
  const isAdmin = useAuthStore((s) => s.staff?.role === 'ADMIN');

  // Use useSeat hook for real-time data with prop as initialData
  const { data: seatData } = useSeat(seat.id, { initialData: seat });

  // Use seatData (fresh from query) or fall back to seat prop
  const currentSeat = seatData ?? seat;

  const isMaintenance = currentSeat.status === 'MAINTENANCE';

  // Tick once per second while the seat is under maintenance so the
  // downtime display stays live (cleared on unmount / status change).
  useEffect(() => {
    if (!isMaintenance || !currentSeat.maintenance_since) return;
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, [isMaintenance, currentSeat.maintenance_since]);

  const handleStartSession = () => {
    const parsed = assignedMinutes.trim() === '' ? null : Number(assignedMinutes);
    startSession.mutate(
      { seat_id: currentSeat.id, member_id: member?.id ?? null, assigned_minutes: parsed },
      {
        onSuccess: () => {
          toast.success('Session started');
          onClose();
        },
        onError: (err) => {
          toast.error(err.message ?? 'Failed to start session');
        },
      },
    );
  };

  const handleForceOverlayOn = async () => {
    setForceOverlayLoading('on');
    try {
      await forceOverlay(currentSeat.id, true);
      toast.success('Force overlay ON');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setForceOverlayLoading(null);
    }
  };

  const handleForceOverlayOff = async () => {
    setForceOverlayLoading('off');
    try {
      await forceOverlay(currentSeat.id, false);
      toast.success('Force overlay OFF');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setForceOverlayLoading(null);
    }
  };

  const handleSetMaintenance = async () => {
    setMaintenancePending(true);
    try {
      await setMaintenance(currentSeat.id, maintenanceNote.trim() || null);
      toast.success('Seat marked for maintenance');
      setMaintenanceNote('');
      setMaintenanceMode('idle');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setMaintenancePending(false);
    }
  };

  const handleClearMaintenance = async () => {
    setMaintenancePending(true);
    try {
      await clearMaintenance(currentSeat.id);
      toast.success('Maintenance cleared');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setMaintenancePending(false);
    }
  };

  const abortMaintenanceNote = () => {
    setMaintenanceNote('');
    setMaintenanceMode('idle');
  };

  // Ticking downtime display: local clock vs the server's maintenance_since
  const sinceMs = currentSeat.maintenance_since
    ? new Date(currentSeat.maintenance_since).getTime()
    : null;
  const downtimeSeconds =
    sinceMs !== null ? Math.max(0, (now.getTime() - sinceMs) / 1000) : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="seat-modal-title"
    >
      <div className="w-full max-w-md rounded-lg bg-card p-6 shadow-xl border border-border">
        <header className="mb-4 flex items-center justify-between">
          <h2 id="seat-modal-title" className="text-xl font-bold text-card-foreground">
            {currentSeat.name}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground hover:bg-secondary hover:text-card-foreground"
            aria-label="Close modal"
          >
            <span className="text-xl leading-none" aria-hidden="true">×</span>
          </button>
        </header>

        <section className="mb-4 space-y-2 text-sm text-muted-foreground">
          <p>Status: <span className="text-card-foreground font-medium">{currentSeat.status.replace('_', ' ')}</span></p>
          <p>Zone: <span className="text-card-foreground">{currentSeat.zone_name ?? currentSeat.zone_id}</span></p>
          {currentSeat.notes && <p data-testid="seat-notes">Note: {currentSeat.notes}</p>}
        </section>

        <nav aria-label="Seat actions" className="grid grid-cols-2 gap-2">
          {(currentSeat.status === 'AVAILABLE' || currentSeat.status === 'ONLINE') && (
            <>
              <div className="col-span-2 space-y-2">
                <MemberSearch onSelect={setMember} placeholder="Search members by name or phone…" />
                {member && (
                  <div className="flex items-center gap-2 rounded-lg bg-secondary px-3 py-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium text-secondary-foreground">{member.name}</span>
                    <button
                      type="button"
                      onClick={() => setMember(null)}
                      className="ml-auto text-muted-foreground hover:text-card-foreground focus:outline-none focus:ring-2 focus:ring-blue-500 rounded p-0.5"
                      aria-label="Clear selected member"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                )}
              {assignedTimeEnabled && (
                <div className="col-span-2">
                  <label
                    className="block text-xs font-medium text-muted-foreground"
                    htmlFor="assign-time-limit"
                  >
                    Assign time limit (minutes)
                  </label>
                  <input
                    id="assign-time-limit"
                    type="number"
                    min={1}
                    value={assignedMinutes}
                    onChange={(e) => setAssignedMinutes(e.target.value)}
                    placeholder="e.g. 120"
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-card-foreground"
                  />
                </div>
              )}
              </div>
              <ActionButton
                icon={<Play className="h-5 w-5" />}
                label="Start Session"
                variant="primary"
                onClick={handleStartSession}
                disabled={(!member && memberRequired) || startSession.isPending}
              >
                {startSession.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
              </ActionButton>
            </>
          )}
          <ActionButton icon={<ShoppingCart className="h-5 w-5" />} label="Checkout" variant="emerald" />
          <ActionButton icon={<Power className="h-5 w-5" />} label="Wake-on-LAN" variant="secondary" />
          <ActionButton icon={<Heart className="h-5 w-5" />} label="View Health" variant="secondary" />
          {isAdmin && isMaintenance && (
            <div className="col-span-2 space-y-2">
              {downtimeSeconds !== null && (
                <p
                  data-testid="maintenance-since"
                  className="rounded-lg bg-amber-500/10 px-3 py-2 text-sm text-amber-400"
                >
                  In maintenance since{' '}
                  <span className="font-medium">{new Date(currentSeat.maintenance_since!).toLocaleTimeString()}</span>{' '}
                  · <span className="font-mono">{formatDuration(downtimeSeconds)}</span>
                </p>
              )}
              <ActionButton
                icon={<Settings className="h-5 w-5" />}
                label="Clear Maintenance"
                variant="secondary"
                onClick={handleClearMaintenance}
                disabled={maintenancePending}
              >
                {maintenancePending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
              </ActionButton>
            </div>
          )}
          {isAdmin && !isMaintenance && maintenanceMode === 'note' && (
            <div className="col-span-2 space-y-2">
              <label
                className="block text-xs font-medium text-muted-foreground"
                htmlFor="maintenance-note"
              >
                Maintenance note
              </label>
              <input
                id="maintenance-note"
                aria-label="Maintenance note"
                autoFocus
                value={maintenanceNote}
                onChange={(e) => setMaintenanceNote(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') abortMaintenanceNote();
                }}
                placeholder="Reason for maintenance…"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-card-foreground"
              />
              <div className="flex gap-2">
                <ActionButton
                  icon={<Settings className="h-5 w-5" />}
                  label="Confirm"
                  variant="primary"
                  onClick={handleSetMaintenance}
                  disabled={maintenancePending}
                />
                <ActionButton
                  label="Cancel"
                  variant="secondary"
                  onClick={abortMaintenanceNote}
                  disabled={maintenancePending}
                />
              </div>
            </div>
          )}
          {isAdmin && !isMaintenance && maintenanceMode === 'idle' && (
            <ActionButton
              icon={<Settings className="h-5 w-5" />}
              label="Maintenance"
              variant="secondary"
              onClick={() => setMaintenanceMode('note')}
            />
          )}
          <ActionButton icon={<Settings className="h-5 w-5" />} label="Enroll Code" variant="secondary" onClick={async () => {
            try {
              const { code } = await generateEnrollCode(currentSeat.id);
              toast.success(`Enroll code for ${currentSeat.name}: ${code}`, {
                persistent: true,
                dismissLabel: 'Dismiss enroll code',
                onClick: async () => {
                  try {
                    await navigator.clipboard.writeText(code);
                    toast.info('Copied to clipboard!');
                  } catch {
                    toast.error('Failed to copy');
                  }
                },
              });
            } catch (e) { toast.error((e as Error).message); }
          }} />
          <ActionButton icon={<Settings className="h-5 w-5" />} label="Regenerate Override PIN" variant="secondary" onClick={async () => {
            try {
              const { override_pin } = await regenerateOverridePin(currentSeat.id);
              toast.success(`New override PIN for ${currentSeat.name}: ${override_pin} (shown once)`);
            } catch (e) { toast.error((e as Error).message); }
          }} />
          {/* Force Overlay buttons — available for all statuses */}
          <ActionButton
            icon={<Lock className="h-5 w-5" />}
            label="Force Overlay On"
            variant="secondary"
            onClick={handleForceOverlayOn}
            disabled={forceOverlayLoading === 'on'}
          >
            {forceOverlayLoading === 'on' && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
          </ActionButton>
          <ActionButton
            icon={<Unlock className="h-5 w-5" />}
            label="Force Overlay Off"
            variant="secondary"
            onClick={handleForceOverlayOff}
            disabled={forceOverlayLoading === 'off'}
          >
            {forceOverlayLoading === 'off' && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
          </ActionButton>
        </nav>
      </div>
    </div>
  );
}

interface ActionButtonProps {
  icon?: ReactNode;
  label: string;
  variant: 'primary' | 'secondary' | 'emerald';
  onClick?: () => void;
  disabled?: boolean;
  children?: ReactNode;
}

/** Format a duration in seconds as MM:SS or H:MM:SS for the downtime line. */
function formatDuration(totalSeconds: number): string {
  const s = Math.floor(totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
}

function ActionButton({ icon, label, variant, onClick, disabled, children }: ActionButtonProps) {
  const base = 'flex min-h-11 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-background';
  const styles = {
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90 focus:ring-primary disabled:bg-primary/50 disabled:cursor-not-allowed',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80 focus:ring-secondary-foreground/20 disabled:bg-secondary/50 disabled:cursor-not-allowed',
    emerald: 'bg-emerald-600 text-white hover:bg-emerald-500 focus:ring-emerald-500 disabled:bg-emerald-600/50 disabled:cursor-not-allowed',
  };

  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`${base} ${styles[variant]}`}>
      {icon}
      <span>{label}</span>
      {children}
    </button>
  );
}
