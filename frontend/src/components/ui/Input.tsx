import { AlertCircle } from 'lucide-react';

interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
  name: string;
  id?: string;
  placeholder?: string;
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  className?: string;
}

export function Input({
  label,
  error,
  icon,
  name,
  id,
  placeholder,
  type = 'text',
  className = '',
  ...props
}: InputProps) {
  const inputId = id ?? name;
  const errorId = error ? `${inputId}-error` : undefined;
  const describedBy = errorId ? errorId : undefined;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-slate-200 mb-1">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            {icon}
          </div>
        )}
        <input
          id={inputId}
          name={name}
          type={type}
          placeholder={placeholder}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedBy}
          className={`w-full border border-slate-600 bg-slate-700 text-slate-100 placeholder:text-slate-500 rounded-md
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:opacity-50 disabled:cursor-not-allowed transition-colors
            ${icon ? 'pl-10' : 'pl-4'} pr-4 py-2 ${className}`}
          {...props}
        />
      </div>
      {error && (
        <p
          id={errorId}
          role="alert"
          className="mt-1.5 flex items-center gap-1.5 text-sm text-red-400"
        >
          <AlertCircle className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  );
}
