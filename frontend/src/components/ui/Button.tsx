import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
}

export function Button({ variant = "primary", className, children, ...props }: Props) {
  return (
    <button
      className={cn(
        variant === "primary"   && "btn-primary",
        variant === "secondary" && "btn-secondary",
        variant === "ghost"     && "btn-ghost",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
