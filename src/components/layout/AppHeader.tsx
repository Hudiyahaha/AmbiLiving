"use client";

import { EnvironmentSelector } from "@/components/layout/EnvironmentSelector";
import { useEnvironment } from "@/context/EnvironmentContext";

interface AppHeaderProps {
  title: string;
}

export function AppHeader({ title }: AppHeaderProps) {
  const { currentHome } = useEnvironment();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-surface/80 px-6 backdrop-blur-sm">
      <div>
        <h1 className="font-display text-xl font-semibold tracking-tight text-foreground">
          {title}
        </h1>
        <p className="text-xs text-muted">{currentHome.name}</p>
      </div>
      <EnvironmentSelector />
    </header>
  );
}
