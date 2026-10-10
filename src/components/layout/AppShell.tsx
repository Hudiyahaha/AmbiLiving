"use client";

import { usePathname } from "next/navigation";
import { AppHeader } from "@/components/layout/AppHeader";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { EnvironmentProvider } from "@/context/EnvironmentContext";
import { SettingsProvider } from "@/context/SettingsContext";

const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/monitoring": "Monitoring",
  "/activities": "Activity History",
  "/anomalies": "Anomalies",
  "/homes": "Homes",
  "/settings": "Settings",
};

function titleForPath(pathname: string): string {
  return pageTitles[pathname] ?? "AmbiLiving";
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <SettingsProvider>
      <EnvironmentProvider>
        <div className="app-shell-bg flex min-h-screen">
          <AppSidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <AppHeader title={titleForPath(pathname)} />
            <main className="flex-1 overflow-auto p-6">{children}</main>
          </div>
        </div>
      </EnvironmentProvider>
    </SettingsProvider>
  );
}
