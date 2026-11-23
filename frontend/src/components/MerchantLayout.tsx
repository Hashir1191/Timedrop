import { NavLink, Outlet, useLocation } from "react-router-dom";
import { LayoutDashboard, LogOut, Package, PlusCircle, Settings, UserRound } from "lucide-react";
import { useAuth } from "../auth";
import NotificationBell from "./NotificationBell";
import BrandLogo from "./BrandLogo";

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/shipments", label: "Shipments", icon: Package },
  { to: "/new-shipment", label: "Create shipment", icon: PlusCircle },
  { to: "/phone-settings", label: "Account settings", icon: Settings },
];

export default function MerchantLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const page = links.find((item) => item.to === location.pathname)?.label || "Merchant workspace";
  return <div className="app-shell merchant-shell">
    <aside className="sidebar merchant-sidebar">
      <div className="brand"><BrandLogo className="brand-logo"/></div>
      <div className="workspace-label">BUSINESS WORKSPACE</div>
      <nav className="side-nav">{links.map(({to,label,icon:Icon,end}) => <NavLink key={to} to={to} end={end} className={({isActive}) => `nav-link ${isActive ? "active" : ""}`}><Icon size={18} strokeWidth={1.8}/><span>{label}</span></NavLink>)}</nav>
      <div className="sidebar-bottom"><div className="merchant-sidebar-note"><strong>Growing with TimeDrop</strong><span>One workspace for every delivery</span></div><span className="version">TIMEDROP · MERCHANT PORTAL</span></div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div className="mobile-brand"><BrandLogo className="brand-logo"/></div><div className="breadcrumb">Merchant portal <span>/</span> <strong>{page}</strong></div>
        <div className="profile"><NotificationBell/><div className="avatar"><UserRound size={16}/></div><div className="profile-copy"><strong>{user?.full_name}</strong><span>Business account</span></div><button className="icon-button logout-button" onClick={logout} title="Sign out" aria-label="Sign out"><LogOut size={17}/></button></div>
      </header>
      <div className="page-content"><Outlet/></div>
    </main>
  </div>;
}
