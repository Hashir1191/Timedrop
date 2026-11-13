import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Activity, ArrowRight, CalendarClock, CheckCircle2, Eye, EyeOff, LockKeyhole, Package, UserPlus } from "lucide-react";
import { getMe, login, register } from "../api";
import { useAuth } from "../auth";

export default function Login() {
  const { user, setAuth } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  if (user) return <Navigate to="/" replace />;
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      if (mode === "register") await register({ email, full_name: name, password });
      const tokenResponse = await login(email, password);
      const currentUser = await getMe(tokenResponse.access_token);
      localStorage.setItem("timedrop_token", tokenResponse.access_token);
      setAuth({ token: tokenResponse.access_token, user: currentUser, loading: false });
      navigate("/", { replace: true });
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to continue."); }
    finally { setBusy(false); }
  }
  return <div className="login-screen"><div className="login-panel">
    <div className="login-brand"><div className="brand-mark"><Activity size={22} /></div><span>time<span className="brand-accent">drop</span></span></div>
    <div className="login-eyebrow">{mode === "login" ? "CUSTOMER & OPERATIONS PORTAL" : "CREATE YOUR ACCOUNT"}</div>
    <h1>{mode === "login" ? "Welcome back." : "Let's get started."}</h1>
    <p className="login-subtitle">{mode === "login" ? "Sign in to manage your deliveries or operations." : "Create a customer account to register and schedule parcels."}</p>
    <form onSubmit={submit} className="login-form">
      {mode === "register" && <><label htmlFor="login-full-name">Full name</label><input id="login-full-name" value={name} onChange={e=>setName(e.target.value)} placeholder="Your full name" required minLength={2} autoComplete="name"/></>}
      <label htmlFor="login-email">Email address</label><input id="login-email" type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" required autoComplete="username"/>
      <label htmlFor="login-password">Password</label><div className="login-password-control"><input id="login-password" type={showPassword?"text":"password"} value={password} onChange={e=>setPassword(e.target.value)} placeholder={mode==="register"?"At least 8 characters":"Enter your password"} required minLength={mode==="register"?8:1} autoComplete={mode==="register"?"new-password":"current-password"}/><button type="button" className="login-password-toggle" aria-label={showPassword?"Hide password":"Show password"} aria-pressed={showPassword} onClick={()=>setShowPassword(value=>!value)}>{showPassword?<EyeOff size={16}/>:<Eye size={16}/>}</button></div>
      {error && <div className="form-error" role="alert" aria-live="polite">{error}</div>}
      <button className="primary-button login-submit" disabled={busy}>{busy ? "Please wait..." : mode==="login"?"Sign in":"Create account"}{mode==="login"?<ArrowRight size={17}/>:<UserPlus size={17}/>}</button>
    </form>
    <button type="button" className="auth-mode-toggle" onClick={()=>{setMode(mode==="login"?"register":"login");setError("");}}>{mode==="login"?"New to TimeDrop? Create a customer account":"Already registered? Sign in"}</button>
    <div className="login-security"><LockKeyhole size={14}/> Secure sign-in with your TimeDrop account</div>
  </div><div className="login-aside"><div className="aside-orb orb-one"/><div className="aside-orb orb-two"/><div className="aside-content"><div className="aside-kicker">DELIVERY, IN SYNC.</div><h2>Every parcel.<br/>Every promise.<br/><span>On time.</span></h2><p>One clear view of your delivery journey, from parcel registration to the doorstep.</p><div className="login-feature-list"><span><Package size={15}/> Parcel visibility</span><span><CalendarClock size={15}/> Flexible delivery scheduling</span><span><CheckCircle2 size={15}/> Verified handovers</span></div><div className="aside-footer">BUILT FOR BETTER LAST-MILE OPERATIONS</div></div></div></div>;
}
