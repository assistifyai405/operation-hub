export default function SectionHeading({
  eyebrow,
  title,
  body,
  align = "center",
  className = "",
}) {
  const alignment = align === "left" ? "text-left" : "mx-auto text-center";

  return (
    <div className={`max-w-3xl ${alignment} ${className}`}>
      {eyebrow ? (
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--theme-brand)]">
          {eyebrow}
        </p>
      ) : null}
      <h2 className="mt-3 text-3xl font-bold tracking-tight text-[var(--theme-text-primary)] sm:text-4xl">
        {title}
      </h2>
      {body ? (
        <p className="mt-4 text-base leading-7 text-[var(--theme-text-secondary)] sm:text-lg">
          {body}
        </p>
      ) : null}
    </div>
  );
}
