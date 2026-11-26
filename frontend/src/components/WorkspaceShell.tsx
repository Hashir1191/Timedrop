import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Bell, ChevronRight, LogOut, Menu, X, type LucideIcon } from "lucide-react";
import { useAuth } from "../auth";
import NotificationBell from "./NotificationBell";
import BrandLogo from "./BrandLogo";

export type WorkspaceLink = { to: string; label: string; icon: LucideIcon; end?: boolean };
export default function WorkspaceShell({ role, links, footer }: { role: string; links: WorkspaceLink[]; footer: string }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const current = links.find((item) => item.to === location.pathname)?.label
    || (location.pathname.startsWith("/schedule/") ? "Schedule delivery" : "Workspace");
  const initials = (user?.full_name || "TD").split(/\\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase();

  return <div className={`td-workspace td-workspace-${role}`}>
    <button className="td-mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} data-open={mobileOpen} />
    <aside className={`td-workspace-sidebar ${mobileOpen ? "is-open" : ""}`}>
      <div className="td-workspace-brand"><BrandLogo className="brand-logo" /><button className="td-mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={19}/></button></div>
      <div className="td-workspace-context"><span className="td-context-indicator"/><div><small>YOUR WORKSPACE</small><strong>{role === "admin" ? "Operations control" : role === "merchant" ? "Merchant studio" : role === "delivery_partner" ? "Partner hub" : "Personal deliveries"}</strong></div></div>
      <nav className="td-workspace-nav" aria-label={`${role} navigation`}>
        <span className="td-nav-caption">MENU</span>
        {links.map(({to,label,icon:Icon,end}) => <NavLink key={to} to={to} end={end} onClick={() => setMobileOpen(false)} className={({isActive}) => `td-workspace-link ${isActive ? "is-active" : ""}`}>
          <Icon size={18} strokeWidth={1.8}/><span>{label}</span>{location.pathname === to && <ChevronRight size={14} className="td-link-chevron"/>}
        </NavLink>)}
      </nav>
      <div className="td-workspace-sidebar-bottom"><div className="td-sidebar-promise"><span><Bell size={15}/></span><div><strong>Stay in the loop</strong><small>Updates appear in your notification centre.</small></div></div><span className="td-workspace-version">{footer}</span></div>
    </aside>
    <main className="td-workspace-main">
      <header className="td-workspace-topbar">
        <button className="td-mobile-trigger" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20}/></button>
        <div className="td-topbar-heading"><span>{role === "admin" ? "OPERATIONS" : role === "merchant" ? "BUSINESS" : role === "delivery_partner" ? "DELIVERY PARTNER" : "MY ACCOUNT"}</span><strong>{current}</strong></div>
        <div className="td-topbar-actions"><span className="td-secure-label"><i/> Secure workspace</span><NotificationBell/><div className="td-user-chip"><span className="td-user-avatar">{initials}</span><span><strong>{user?.full_name || "TimeDrop user"}</strong><small>{role.replace("_", " ")}</small></span></div><button className="td-signout" onClick={logout} title="Sign out" aria-label="Sign out"><LogOut size={17}/></button></div>
      </header>
      <div className="td-workspace-content"><Outlet/></div>
    </main>
  </div>;
}
