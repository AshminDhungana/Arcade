import * as React from "react";
import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string | null;
  icon?: React.ReactNode;
}

export function Input({ label, error, icon, id, className, ...props }: InputProps) {
  const inputId = id ?? props.name;
  return (
    <div>
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-foreground">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {icon}
          </span>
        )}
        <input
          id={inputId}
          aria-invalid={!!error}
          className={cn(
            "flex h-11 w-full rounded-md border border-input bg-popover/60 py-2.5 text-sm text-foreground transition-colors",
            "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-ring",
            icon ? "pl-10" : "px-3.5",
            "pr-4",
            error ? "border-destructive focus-visible:ring-destructive" : "",
            className,
          )}
          {...props}
        />
      </div>
      {error && (
        <p role="alert" className="mt-1.5 flex items-center gap-1 text-xs text-destructive">
          <AlertCircle className="size-3" />
          {error}
        </p>
      )}
    </div>
  );
}
