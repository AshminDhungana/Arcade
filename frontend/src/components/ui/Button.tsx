import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type Variant = 'primary' | 'secondary' | 'emerald' | 'danger';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
  children: ReactNode;
}

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-500 focus:ring-blue-500',
  secondary: 'bg-slate-700 text-slate-200 hover:bg-slate-600 focus:ring-slate-400',
  emerald: 'bg-emerald-600 text-white hover:bg-emerald-500 focus:ring-emerald-500',
  danger: 'bg-red-600 text-white hover:bg-red-500 focus:ring-red-500',
};

export function Button({
  variant = 'primary',
  loading,
  disabled,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cn(
        'inline-flex min-h-[40px] items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-800 disabled:cursor-not-allowed disabled:opacity-50',
        VARIANTS[variant],
        className
      )}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}
