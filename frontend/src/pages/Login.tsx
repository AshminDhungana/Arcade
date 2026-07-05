import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, User, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { login, AuthError } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';

/**
 * Format a duration in seconds as "MM:SS" for the lockout countdown.
 */
function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export default function Login() {
  const navigate = useNavigate();
  const storeLogin = useAuthStore((state) => state.login);

  const [staffId, setStaffId] = useState('');
  const [pin, setPin] = useState('');
  const [showPin, setShowPin] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lockoutSeconds, setLockoutSeconds] = useState<number | null>(null);
  const [failureCount, setFailureCount] = useState(0);

  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearCountdown = useCallback(() => {
    if (countdownRef.current !== null) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
  }, []);

  const startCountdown = useCallback(
    (seconds: number) => {
      clearCountdown();
      setLockoutSeconds(seconds);
      countdownRef.current = setInterval(() => {
        setLockoutSeconds((prev) => {
          if (prev === null || prev <= 1) {
            clearCountdown();
            return null;
          }
          return prev - 1;
        });
      }, 1000);
    },
    [clearCountdown],
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!staffId.trim() || !pin.trim()) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const response = await login(staffId.trim(), pin.trim());
      storeLogin(response.access_token, response.staff);
      setFailureCount(0);
      navigate('/', { replace: true });
    } catch (err) {
      if (err instanceof AuthError) {
        if (err.status === 429 && err.retryAfter !== null) {
          setError('Too many failed login attempts. Please try again later.');
          startCountdown(err.retryAfter);
        } else if (err.status === 401) {
          const newCount = failureCount + 1;
          setFailureCount(newCount);
          if (newCount >= 5) {
            setError('Account temporarily locked due to multiple failed attempts.');
          } else {
            setError(`Invalid staff ID or PIN. (${5 - newCount} attempts remaining)`);
          }
        } else {
          setError(err.message || 'Authentication failed.');
        }
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Clean up countdown on unmount
  useEffect(() => {
    return () => {
      clearCountdown();
    };
  }, [clearCountdown]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900 p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-800 p-8 shadow-lg">
        {/* Header */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/20">
            <Lock className="h-6 w-6 text-blue-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Arcade</h1>
          <p className="mt-1 text-sm text-slate-400">Staff Sign In</p>
        </div>

        {/* Lockout banner */}
        {lockoutSeconds !== null && (
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-500/10 p-3 text-sm text-red-400">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">Account locked</p>
              <p className="mt-0.5">
                Too many failed attempts. Retry after: {' '}
                <span className="font-mono font-semibold">
                  {formatCountdown(lockoutSeconds)}
                </span>
              </p>
            </div>
          </div>
        )}

        {/* Error banner */}
        {error !== null && lockoutSeconds === null && (
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-500/10 p-3 text-sm text-red-400">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Staff ID */}
          <div>
            <label
              htmlFor="staffId"
              className="mb-1 block text-sm font-medium text-slate-300"
            >
              Staff ID
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                id="staffId"
                type="text"
                autoComplete="off"
                value={staffId}
                onChange={(e) => setStaffId(e.target.value)}
                onFocus={() => {
                  setError(null);
                }}
                className="w-full rounded-lg border border-slate-600 bg-slate-700 py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Enter your staff ID"
                required
              />
            </div>
          </div>

          {/* PIN */}
          <div>
            <label
              htmlFor="pin"
              className="mb-1 block text-sm font-medium text-slate-300"
            >
              PIN
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                id="pin"
                type={showPin ? 'text' : 'password'}
                autoComplete="off"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                onFocus={() => {
                  setError(null);
                }}
                className="w-full rounded-lg border border-slate-600 bg-slate-700 py-2.5 pl-10 pr-10 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Enter your PIN"
                required
                minLength={4}
                maxLength={20}
              />
              <button
                type="button"
                onClick={() => setShowPin((prev) => !prev)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                aria-label={showPin ? 'Hide PIN' : 'Show PIN'}
              >
                {showPin ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={isSubmitting || lockoutSeconds !== null}
            className="flex w-full items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
