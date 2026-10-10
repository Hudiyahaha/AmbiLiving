"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  Home,
  LayoutDashboard,
  Radar,
  Settings,
} from "lucide-react";
import { useSettings } from "@/context/SettingsContext";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/monitoring", label: "Monitoring", icon: Radar },
  { href: "/activities", label: "Activity History", icon: Activity },
  { href: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { href: "/homes", label: "Homes", icon: Home },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export function AppSidebar() {
  const pathname = usePathname();
  const { settings } = useSettings();

  return (
    <aside className="flex w-60 shrink-0 flex-col bg-sidebar text-white">
      <div className="border-b border-white/10 px-5 py-6">
        <Link href="/" className="block">
          <p className="font-display text-2xl font-semibold tracking-tight text-white">
            AmbiLiving
          </p>
          <p className="mt-1 text-xs text-sidebar-muted">
            Home activity monitoring
          </p>
        </Link>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-4" aria-label="Main">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive =
            pathname === href || pathname.startsWith(`${href}/`);

          return (
            <Link
              key={href}
              href={href}
              className={[
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-active text-white"
                  : "text-sidebar-muted hover:bg-sidebar-hover hover:text-white",
              ].join(" ")}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/10 px-5 py-4">
        <p className="text-sm font-medium text-white">{settings.caregiverName}</p>
        <p className="mt-0.5 text-xs text-sidebar-muted">Caregiver view · PoC</p>
        <Link
          href="/"
          className="mt-3 inline-block text-xs text-sidebar-muted underline-offset-2 hover:text-white hover:underline"
        >
          ← Product home
        </Link>
      </div>
    </aside>
  );
}
