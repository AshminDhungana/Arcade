import * as React from "react";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import { cn } from "@/lib/utils";

export interface SwitchProps {
  checked: boolean;
  disabled?: boolean;
  onCheckedChange: (v: boolean) => void;
  label?: string;
  description?: string;
}

export function Switch({ checked, disabled, onCheckedChange, label, description }: SwitchProps) {
  return (
    <label className={cn("flex items-center justify-between gap-4", disabled ? "opacity-50" : "cursor-pointer")}>
      {(label || description) && (
        <span>
          {label && <span className="block text-sm font-medium text-foreground">{label}</span>}
          {description && <span className="block text-xs text-muted-foreground">{description}</span>}
        </span>
      )}
      <SwitchPrimitive.Root
        checked={checked}
        disabled={disabled}
        onCheckedChange={onCheckedChange}
        aria-label={label}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            onCheckedChange(!checked);
          }
        }}
        className={cn(
          "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          "data-[state=checked]:bg-success data-[state=unchecked]:bg-secondary",
        )}
      >
        <SwitchPrimitive.Thumb className="pointer-events-none block h-4 w-4 translate-x-1 rounded-full bg-white shadow transition-transform data-[state=checked]:translate-x-6" />
      </SwitchPrimitive.Root>
    </label>
  );
}
