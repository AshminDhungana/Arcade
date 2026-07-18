import type { Seat } from '@/types/seat';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { Loader2, Pause, Play, Power, Settings, ShoppingCart, Heart, User, X, Lock, Unlock } from 'lucide-react';
import { MemberSearch } from './MemberSearch';
import { useStartSession } from '@/api/sessions';
import { generateEnrollCode, regenerateOverridePin, forceOverlay } from '@/api/seats';
import { toast } from '@/store/toastStore';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
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
  const startSession = useStartSession();
  const memberRequired = useFeatureFlagStore((s) => s.flags.require_member_for_session);
  const assignedTimeEnabled = useFeatureFlagStore((s) => s.flags.enable_assigned_time_limit);

  const handleStartSession = () => {
    const parsed = assignedMinutes.trim() === '' ? null : Number(assignedMinutes);
    startSession.mutate(
      { seat_id: seat.id, member_id: member?.id ?? null, assigned_minutes: parsed },
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
      await forceOverlay(seat.id, true);
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
      await forceOverlay(seat.id, false);
      toast.success('Force overlay OFF');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setForceOverlayLoading(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="seat-modal-title"
    >
      <div className="w-full max-w-md rounded-lg bg-slate-800 p-6 shadow-xl border border-slate-700">
        <header className="mb-4 flex items-center justify-between">
          <h2 id="seat-modal-title" className="text-xl font-bold text-white">
            {seat.name}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-700 hover:text-white"
            aria-label="Close modal"
          >
            <span className="text-xl leading-none" aria-hidden="true">×</span>
          </button>
        </header>

        <section className="mb-4 space-y-2 text-sm text-slate-300">
          <p>Status: <span className="text-white font-medium">{seat.status.replace('_', ' ')}</span></p>
          <p>Zone: <span className="text-white">{seat.zone_id}</span></p>
          {seat.notes && <p data-testid="seat-notes">Note: {seat.notes}</p>}
        </section>

        <nav aria-label="Seat actions" className="grid grid-cols-2 gap-2">
          {seat.status === 'AVAILABLE' && (
            <>
              <div className="col-span-2 space-y-2">
                <MemberSearch onSelect={setMember} placeholder="Search members by name or phone…" />
                {member && (
                  <div className="flex items-center gap-2 rounded-lg bg-slate-700 px-3 py-2">
                    <User className="h-4 w-4 text-slate-400" />
                    <span className="font-medium text-slate-200">{member.name}</span>
                    <button
                      type="button"
                      onClick={() => setMember(null)}
                      className="ml-auto text-slate-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 rounded p-0.5"
                      aria-label="Clear selected member"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                )}
              {assignedTimeEnabled && (
                <div className="col-span-2">
                  <label
                    className="block text-xs font-medium text-slate-400"
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
                    className="mt-1 w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white"
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
          {seat.status === 'IN_USE' && (
            <ActionButton icon={<Pause className="h-5 w-5" />} label="Pause Session" variant="secondary" />
          )}
          {seat.status === 'PAUSED' && (
            <ActionButton icon={<Play className="h-5 w-5" />} label="Resume Session" variant="secondary" />
          )}
          <ActionButton icon={<ShoppingCart className="h-5 w-5" />} label="Checkout" variant="emerald" />
          <ActionButton icon={<Power className="h-5 w-5" />} label="Wake-on-LAN" variant="secondary" />
          <ActionButton icon={<Heart className="h-5 w-5" />} label="View Health" variant="secondary" />
          <ActionButton icon={<Settings className="h-5 w-5" />} label="Maintenance" variant="secondary" />
          <ActionButton icon={<Settings className="h-5 w-5" />} label="Enroll Code" variant="secondary" onClick={async () => {
            try {
              const { code } = await generateEnrollCode(seat.id);
              toast.success(`Enroll code for ${seat.name}: ${code}`);
            } catch (e) { toast.error((e as Error).message); }
          }} />
          <ActionButton icon={<Settings className="h-5 w-5" />} label="Regenerate Override PIN" variant="secondary" onClick={async () => {
            try {
              const { override_pin } = await regenerateOverridePin(seat.id);
              toast.success(`New override PIN for ${seat.name}: ${override_pin} (shown once)`);
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
  icon: ReactNode;
  label: string;
  variant: 'primary' | 'secondary' | 'emerald';
  onClick?: () => void;
  disabled?: boolean;
  children?: ReactNode;
}

function ActionButton({ icon, label, variant, onClick, disabled, children }: ActionButtonProps) {
  const base = 'flex min-h-11 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-800';
  const styles = {
    primary: 'bg-blue-600 text-white hover:bg-blue-500 focus:ring-blue-500 disabled:bg-blue-600/50 disabled:cursor-not-allowed',
    secondary: 'bg-slate-700 text-slate-200 hover:bg-slate-600 focus:ring-slate-400 disabled:bg-slate-700/50 disabled:cursor-not-allowed',
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
