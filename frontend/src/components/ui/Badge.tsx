import { cn } from "@/lib/utils";
export function Badge({ label, className }: { label: string; className?: string }) {
  return <span className={cn("badge", className)}>{label}</span>;
}
