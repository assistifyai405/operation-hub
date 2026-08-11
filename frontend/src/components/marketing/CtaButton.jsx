import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

const variants = {
  primary: "bg-[var(--theme-brand)] text-white shadow-brand-soft hover:bg-[var(--theme-brand-hover)]",
  secondary: "border border-[var(--theme-border-strong)] bg-[var(--theme-surface)] text-[var(--theme-text-primary)] hover:border-[var(--theme-brand-border)] hover:bg-[var(--theme-brand-soft)]",
  ghost: "text-[var(--theme-text-secondary)] hover:bg-[var(--theme-surface-muted)] hover:text-[var(--theme-text-primary)]",
};

export default function CtaButton({
  to,
  children,
  variant = "primary",
  showArrow = false,
  className = "",
  ...props
}) {
  return (
    <Link
      to={to}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-colors ${variants[variant] || variants.primary} ${className}`}
      {...props}
    >
      {children}
      {showArrow ? <ArrowRight className="h-4 w-4" aria-hidden="true" /> : null}
    </Link>
  );
}
