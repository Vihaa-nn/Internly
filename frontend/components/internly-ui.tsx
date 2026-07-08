import { Zap } from "lucide-react";
import { cn } from "@/lib/utils";

export function BrandMark({ size = "md" }: { size?: "sm" | "md" }) {
  const dim = size === "sm" ? "w-7 h-7 rounded-lg text-sm" : "w-8 h-8 rounded-[10px] text-base";
  return (
    <div
      className={cn("logo-glow flex items-center justify-center text-white flex-shrink-0", dim)}
      style={{ background: "linear-gradient(135deg, #6366f1 0%, #818cf8 100%)" }}
    >
      <Zap className={size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4"} strokeWidth={2.5} />
    </div>
  );
}

export function BrandTitle({ className }: { className?: string }) {
  return (
    <span className={cn("text-[1.05rem] font-black tracking-tight text-foreground", className)}>
      Internly
    </span>
  );
}

export function GlassCard({
  children,
  className,
  hover = false,
}: {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div
      className={cn(
        "glass-card p-6",
        hover && "transition-all duration-200 hover:border-primary/40 hover:shadow-lg cursor-default",
        className
      )}
    >
      {children}
    </div>
  );
}

export function Eyebrow({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={cn("eyebrow mb-3", className)}>{children}</p>;
}

export function SectionTitle({
  eyebrow,
  title,
  sub,
}: {
  eyebrow: string;
  title: string;
  sub: string;
}) {
  return (
    <div className="mb-6">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 className="text-[1.45rem] font-black text-foreground mb-1 tracking-tight">{title}</h2>
      <p className="text-muted-foreground text-[0.84rem]">{sub}</p>
    </div>
  );
}

export function PrimaryCta({
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "btn-cta w-full py-3 rounded-xl font-bold text-[0.9rem] disabled:opacity-60 disabled:cursor-not-allowed",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function SecondaryBtn({
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "btn-secondary w-full py-2 rounded-[10px] text-[0.82rem] cursor-pointer",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
