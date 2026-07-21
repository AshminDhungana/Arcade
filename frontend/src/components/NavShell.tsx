import { NavLink, useNavigate } from "react-router-dom";
import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useFeatureFlagStore } from "@/store/featureFlagStore";
import { useAuthStore } from "@/store/authStore";
import type { ReactNode } from "react";
import type { IconName } from "@/components/ui/Icon";
import { Sheet } from "@/components/ui/Sheet";
import { Icon } from "@/components/ui/Icon";

const NAV = [
  { to: "/", label: "Dashboard", icon: "LayoutDashboard", flag: null },
  { to: "/members", label: "Members", icon: "Users", flag: "enable_members" as const },
  { to: "/analytics", label: "Analytics", icon: "BarChart3", flag: null },
  { to: "/events", label: "Events", icon: "CalendarDays", flag: "enable_tournaments" as const },
  { to: "/settings", label: "Settings", icon: "Settings", flag: null },
];

export function NavShell({ children }: { children: ReactNode }) {
  const flags = useFeatureFlagStore((s) => s.flags);
  const items = NAV.filter((n) => !n.flag || flags[n.flag]);
  const [menuOpen, setMenuOpen] = useState(false);

  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const navLinks = (
    <nav className="flex flex-col gap-1" aria-label="Primary">
      {items.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          end={n.to === "/"}
          onClick={() => setMenuOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors ${
              isActive
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            }`
          }
        >
          <Icon name={n.icon as IconName} size={16} variant="stroke" aria-hidden={true} />
          {n.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="bg-background flex min-h-screen md:flex">
      <aside className="bg-card hidden w-60 shrink-0 flex-col border-r border-border p-3 md:flex">
        <div className="mb-2 flex items-center gap-2 px-3 py-2">
          <Icon name="GamepadDirectional" size={32} variant="stroke" aria-hidden={true} />
          <h1 className="text-lg font-bold text-foreground">Arcade</h1>
        </div>
        {navLinks}
        <button
          type="button"
          onClick={handleLogout}
          aria-label="Logout"
          title="Logout"
          className="flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors text-muted-foreground hover:bg-secondary hover:text-foreground mt-auto"
        >
          <Icon name="Unlock" size={16} variant="stroke" aria-hidden={true} />
        </button>
      </aside>

      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-card px-4 py-3 md:hidden">
        <div className="flex items-center gap-2">
          <Icon name="GamepadDirectional" size={28} variant="stroke" aria-hidden={true} />
          <h1 className="text-lg font-bold text-foreground">Arcade</h1>
        </div>
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
          aria-expanded={menuOpen}
          className="flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          <Icon name="Menu" size={20} variant="stroke" aria-hidden={true} />
        </button>
      </div>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <Dialog.Title className="sr-only">Arcade menu</Dialog.Title>
        <div className="flex items-center justify-between border-b border-border px-3 py-2">
          <div className="flex items-center gap-2 px-3 py-2">
            <Icon name="GamepadDirectional" size={32} variant="stroke" aria-hidden={true} />
            <h1 className="text-lg font-bold text-foreground">Arcade</h1>
          </div>
          <button
            type="button"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
            className="flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <Icon name="X" size={20} variant="stroke" aria-hidden={true} />
          </button>
        </div>
        {navLinks}
        <button
          type="button"
          onClick={handleLogout}
          aria-label="Logout"
          className="flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors text-muted-foreground hover:bg-secondary hover:text-foreground w-full mt-auto"
        >
          <Icon name="Unlock" size={16} variant="stroke" aria-hidden={true} />
          <span>Logout</span>
        </button>
      </Sheet>

      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
