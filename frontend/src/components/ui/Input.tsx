import type { InputHTMLAttributes, ReactNode } from 'react';
import { AlertCircle } from 'lucide-react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string; error?: string | null; icon?: ReactNode;
}
export function Input({ label, error, icon, id, className = '', ...rest }: InputProps) {
  const inputId = id ?? rest.name;
  return (
    <div>
      {label && <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-slate-300">{label}</label>}
      <div className="relative">
        {icon && <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">{icon}</span>}
        <input
          id={inputId} aria-invalid={!!error}
          className={`w-full rounded-lg border border-slate-600 bg-slate-700 py-2.5 ${icon ? 'pl-10' : 'px-3'} pr-4 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 ${error ? 'border-red-500' : ''} ${className}`}
          {...rest}
        />
      </div>
      {error && <p role="alert" className="mt-1 flex items-center gap-1 text-xs text-red-400"><AlertCircle className="h-3 w-3" />{error}</p>}
    </div>
  );
}
