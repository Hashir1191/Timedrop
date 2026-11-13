import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Activity, CalendarClock, LogOut, Package, UserRound, Smartphone } from "lucide-react";
import { useAuth } from "../auth";
import NotificationBell from "./NotificationBell";
export default function PartnerLayout(){
 const {user,logout}=useAuth();
 const location=useLocation();
 const page=location.pathname==="/availability"?"Availability":location.pathname==="/phone-settings"?"Phone & SMS":"My deliveries";
 return <div className="app-shell customer-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark"><Activity size={20}/></div><span>time<span className="brand-accent">drop</span></span></div><div className="workspace-label">DELIVERY WORKSPACE</div><nav className="side-nav"><NavLink to="/" end className={({isActive})=>`nav-link ${isActive?"active":""}`}><Package size={18}/><span>My deliveries</span></NavLink><NavLink to="/phone-settings" className={({isActive})=>`nav-link ${isActive?"active":""}`}><Smartphone size={18}/><span>Phone & SMS</span></NavLink><NavLink to="/availability" className={({isActive})=>`nav-link ${isActive?"active":""}`}><CalendarClock size={18}/><span>Availability</span></NavLink></nav><div className="sidebar-bottom"><span className="version">TIMEDROP · PARTNER PORTAL</span></div></aside><main className="main-area"><header className="topbar"><div className="mobile-brand">TimeDrop</div><div className="breadcrumb">Delivery partner <span>/</span> <strong>{page}</strong></div><div className="profile"><NotificationBell/><div className="avatar"><UserRound size={16}/></div><div className="profile-copy"><strong>{user?.full_name}</strong><span>Delivery partner</span></div><button className="icon-button logout-button" onClick={logout} title="Sign out" aria-label="Sign out"><LogOut size={17}/></button></div></header><div className="page-content"><Outlet/></div></main></div>;
}
