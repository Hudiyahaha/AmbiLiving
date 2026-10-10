import type { ReactNode } from "react";

interface PagePlaceholderProps {
  title: string;
  description: string;
}

export function PagePlaceholder({ title, description }: PagePlaceholderProps) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-8 shadow-sm">
      <h2 className="font-display text-lg font-semibold text-foreground">
        {title}
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
        {description}
      </p>
      <p className="mt-6 text-xs font-medium uppercase tracking-wide text-accent">
        Coming in a later step
      </p>
    </div>
  );
}

export function SectionCard({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-foreground">{title}</h2>
      {children}
    </section>
  );
}
