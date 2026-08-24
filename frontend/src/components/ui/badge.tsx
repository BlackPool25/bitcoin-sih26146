import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "critical" | "high" | "medium" | "low" | "default" | "secondary" | "outline" | "destructive";

const variantClasses: Record<BadgeVariant, string> = {
  critical: "bg-red-600 text-white border-transparent hover:bg-red-700",
  high: "bg-orange-500 text-white border-transparent hover:bg-orange-600",
  medium: "bg-amber-500 text-white border-transparent hover:bg-amber-600",
  low: "bg-slate-500 text-white border-transparent hover:bg-slate-600",
  default: "bg-primary text-primary-foreground border-transparent",
  secondary: "bg-secondary text-secondary-foreground",
  outline: "border text-foreground",
  destructive: "bg-destructive text-destructive-foreground border-transparent hover:bg-destructive/90",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps): React.JSX.Element {
  return (
    <span
      data-slot="badge"
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
