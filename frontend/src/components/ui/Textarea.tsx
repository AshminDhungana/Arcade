import * as React from "react";
import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string | null;
  icon?: React.ReactNode;
}

export function Textarea({ label, error, icon, id, className, ...props }: TextareaProps) {
  const textareaId = id ?? props.name;
  return (
    <div>
      {label && (
        <label htmlFor={textareaId} className="mb-1.5 block text-sm font-medium text-foreground">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <span className="pointer-events-none absolute left-3 top-3 text-muted-foreground">
            {icon}
          </span>
        )}
        <textarea
          id={textareaId}
          aria-invalid={!!error}
          className={cn(
            "flex w-full rounded-md border border-input bg-popover/60 p-2.5 text-sm text-foreground transition-colors",
            "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-ring",
            icon ? "pl-10" : "px-3.5",
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
