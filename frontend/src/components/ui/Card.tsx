import { cn } from "@/lib/utils";
export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("card p-5", className)}>{children}</div>;
}
