import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Activity, LayoutDashboard, LogOut, Package, PlusCircle, UserRound, Smartphone } from "lucide-react";
import { useAuth } from "../auth";
import NotificationBell from "./NotificationBell";

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/my-parcels", label: "My parcels", icon: Package },
  { to: "/new-parcel", label: "Create parcel", icon: PlusCircle },
  { to: "/phone-settings", label: "Phone & SMS", icon: Smartphone },
];

export default function CustomerLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const page = links.find((item) => item.to === location.pathname)?.label || (location.pathname.startsWith("/schedule/") ? "Schedule delivery" : "Delivery");
  return <div className="app-shell customer-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Activity size={20} /></div><span>time<span className="brand-accent">drop</span></span></div>
      <div className="workspace-label">YOUR ACCOUNT</div>
      <nav className="side-nav">{links.map(({to,label,icon:Icon,end}) =>
        <NavLink key={to} to={to} end={end} className={({isActive}) => `nav-link ${isActive ? "active" : ""}`}>
          <Icon size={18} strokeWidth={1.8}/><span>{label}</span>
        </NavLink>)}</nav>
      <div className="sidebar-bottom"><span className="version">TIMEDROP · CUSTOMER PORTAL</span></div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div className="mobile-brand">TimeDrop</div><div className="breadcrumb">Customer portal <span>/</span> <strong>{page}</strong></div>
        <div className="profile"><NotificationBell/><div className="avatar"><UserRound size={16}/></div><div className="profile-copy"><strong>{user?.full_name}</strong><span>Customer account</span></div><button className="icon-button logout-button" onClick={logout} title="Sign out"><LogOut size={17}/></button></div>
      </header>
      <div className="page-content"><Outlet/></div>
    </main>
  </div>;
}
