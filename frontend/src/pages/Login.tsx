import { useState, useRef, useCallback, useEffect, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Lock, User, AlertCircle, Eye, EyeOff, Sun, Moon } from "lucide-react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { login, AuthError } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import NeonGridBackground from "@/components/login/NeonGridBackground";
import Signature from "@/components/Signature";

type LoginTheme = "light" | "dark";
const THEME_KEY = "arcade-login-theme";

function getInitialTheme(): LoginTheme {
  const stored = localStorage.getItem(THEME_KEY);
  return stored === "light" || stored === "dark" ? stored : "dark";
}

function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export default function Login() {
  const navigate = useNavigate();
  const storeLogin = useAuthStore((state) => state.login);

  const [staffId, setStaffId] = useState("");
  const [pin, setPin] = useState("");
  const [showPin, setShowPin] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lockoutSeconds, setLockoutSeconds] = useState<number | null>(null);
  const [failureCount, setFailureCount] = useState(0);
  const [theme, setTheme] = useState<LoginTheme>(getInitialTheme);

  const reduceMotion = useReducedMotion();
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

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

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!staffId.trim() || !pin.trim()) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await login(staffId.trim(), pin.trim());
      storeLogin(response.access_token, response.staff);
      setFailureCount(0);
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof AuthError) {
        if (err.status === 429 && err.retryAfter !== null) {
          setError("Too many failed login attempts. Please try again later.");
          startCountdown(err.retryAfter);
        } else if (err.status === 401) {
          const newCount = failureCount + 1;
          setFailureCount(newCount);
          if (newCount >= 5) {
            setError("Account temporarily locked due to multiple failed attempts.");
          } else {
            setError(`Invalid staff ID or PIN. (${5 - newCount} attempts remaining)`);
          }
        } else {
          setError(err.message || "Authentication failed.");
        }
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    return () => clearCountdown();
  }, [clearCountdown]);

  return (
    <div className="login-root relative min-h-screen overflow-hidden" data-theme={theme}>
      <NeonGridBackground />

      <div className="relative z-10 flex min-h-screen items-center justify-center p-4">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 24 }}
          className="w-full max-w-md rounded-2xl border border-border bg-card/95 p-6 shadow-2xl backdrop-blur-sm sm:p-8"
        >
          <div className="mb-6 flex flex-col items-center text-center">
            <h1 className="text-2xl font-bold text-foreground">Arcade</h1>
            <p className="mt-1 text-sm text-muted-foreground">Staff Sign In</p>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            title="Toggle theme"
            className="relative mb-4 rounded-2xl shadow-lg outline-none transition focus-visible:ring-2 focus-visible:ring-ring"
          >
            <img
              src="/arcade_icon.svg"
              alt=""
              aria-hidden="true"
              className="h-14 w-14 rounded-2xl"
            />
            <span className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-card text-foreground shadow ring-1 ring-border">
              <AnimatePresence mode="wait" initial={false}>
                {theme === "dark" ? (
                  <motion.span
                    key="moon"
                    initial={reduceMotion ? false : { rotate: -90, opacity: 0 }}
                    animate={{ rotate: 0, opacity: 1 }}
                    exit={reduceMotion ? undefined : { rotate: 90, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Moon className="size-3.5" />
                  </motion.span>
                ) : (
                  <motion.span
                    key="sun"
                    initial={reduceMotion ? false : { rotate: 90, opacity: 0 }}
                    animate={{ rotate: 0, opacity: 1 }}
                    exit={reduceMotion ? undefined : { rotate: -90, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Sun className="size-3.5" />
                  </motion.span>
                )}
              </AnimatePresence>
            </span>
          </button>

          {lockoutSeconds !== null && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <div>
                <p className="font-medium">Account locked</p>
                <p className="mt-0.5">
                  Too many failed attempts. Retry after:{" "}
                  <span className="font-mono font-semibold">{formatCountdown(lockoutSeconds)}</span>
                </p>
              </div>
            </Alert>
          )}

          {error !== null && lockoutSeconds === null && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <p>{error}</p>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              id="staffId"
              label="Staff ID"
              icon={<User className="size-4" />}
              type="text"
              autoComplete="off"
              value={staffId}
              onChange={(e) => setStaffId(e.target.value)}
              onFocus={() => setError(null)}
              placeholder="Enter your staff ID"
              required
            />
            <Input
              id="pin"
              label="PIN"
              icon={<Lock className="size-4" />}
              type={showPin ? "text" : "password"}
              autoComplete="off"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              onFocus={() => setError(null)}
              placeholder="Enter your PIN"
              required
              minLength={4}
              maxLength={20}
              trailing={
                <button
                  type="button"
                  onClick={() => setShowPin((prev) => !prev)}
                  className="absolute right-2 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                  aria-label={showPin ? "Hide password" : "Show password"}
                >
                  {showPin ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              }
            />
            <Button type="submit" disabled={isSubmitting || lockoutSeconds !== null} loading={isSubmitting} className="w-full">
              {isSubmitting ? "Signing in..." : "Sign In"}
            </Button>
          </form>
        </motion.div>
      </div>

      <Signature className="pointer-events-none absolute bottom-4 right-4 z-10 h-8 w-auto text-foreground opacity-80 drop-shadow-sm sm:h-10" />
    </div>
  );
}
