import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Activity, CalendarClock, BarChart3, ChevronDown, LayoutDashboard, LogOut, Package, PackageCheck, Truck, Users, Warehouse } from "lucide-react";
import { useAuth } from "../auth";
import NotificationBell from "./NotificationBell";
const navItems=[
 {to:"/",label:"Overview",icon:LayoutDashboard,end:true},
 {to:"/parcels",label:"Parcels",icon:Package},
 {to:"/intake",label:"Parcel intake",icon:PackageCheck},
 {to:"/warehouse",label:"Warehouse",icon:Warehouse},
 {to:"/analytics",label:"Analytics",icon:BarChart3},
 {to:"/slots",label:"Delivery slots",icon:CalendarClock},
 {to:"/bookings",label:"Bookings",icon:Truck},
 {to:"/delivery-partners",label:"Delivery partners",icon:Users},
];
export default function Layout(){
 const {user,logout}=useAuth();const location=useLocation();const page=navItems.find(item=>item.to===location.pathname)?.label||"Operations";
 return <div className="app-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark"><Activity size={20}/></div><span>time<span className="brand-accent">drop</span></span></div><div className="workspace-label">WORKSPACE</div><nav className="side-nav">{navItems.map(({to,label,icon:Icon,end})=><NavLink key={to} to={to} end={end} className={({isActive})=>`nav-link ${isActive?"active":""}`}><Icon size={18} strokeWidth={1.8}/><span>{label}</span></NavLink>)}</nav><div className="sidebar-bottom"><div className="sidebar-help"><div className="help-icon">?</div><div><strong>Need a hand?</strong><span>Check API documentation</span></div></div><span className="version">TIMEDROP PILOT · v0.2</span></div></aside><main className="main-area"><header className="topbar"><div className="mobile-brand">TimeDrop</div><div className="breadcrumb">Operations <span>/</span> <strong>{page}</strong></div><div className="profile"><NotificationBell/><div className="avatar">{user?.full_name?.slice(0,1).toUpperCase()||"O"}</div><div className="profile-copy"><strong>{user?.full_name}</strong><span>Operations admin</span></div><ChevronDown size={15}/><button className="icon-button logout-button" onClick={logout} title="Sign out"><LogOut size={17}/></button></div></header><div className="page-content"><Outlet/></div></main></div>;
}
