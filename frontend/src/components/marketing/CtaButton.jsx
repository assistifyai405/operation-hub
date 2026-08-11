import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

const variants = {
  primary: "bg-brand-500 text-white shadow-brand hover:bg-brand-600",
  secondary: "border border-white/15 bg-white/[0.04] text-zinc-100 hover:border-brand-500/40 hover:bg-brand-500/10",
  ghost: "text-zinc-300 hover:bg-white/[0.06] hover:text-white",
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
