import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { Activity, ArrowRight, LockKeyhole } from "lucide-react";
import { getMe, login } from "../api";
import { useAuth } from "../auth";

export default function Login() {
  const { user, setAuth } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const tokenResponse = await login(email, password);
      const user = await getMe(tokenResponse.access_token);
      if (user.role !== "admin") throw new Error("This sign-in is restricted to operations administrators.");
      localStorage.setItem("timedrop_token", tokenResponse.access_token);
      setAuth({ token: tokenResponse.access_token, user, loading: false });
    } catch (err) { setError(err instanceof Error ? err.message : "Sign-in failed."); }
    finally { setBusy(false); }
  }
  return <div className="login-screen"><div className="login-panel"><div className="login-brand"><div className="brand-mark"><Activity size={22} /></div><span>time<span className="brand-accent">drop</span></span></div><div className="login-eyebrow">OPERATIONS PORTAL</div><h1>Welcome back.</h1><p className="login-subtitle">Sign in to manage your delivery operations.</p><form onSubmit={submit} className="login-form"><label>Email address</label><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required autoComplete="username" /><label>Password</label><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" required autoComplete="current-password" />{error && <div className="form-error">{error}</div>}<button className="primary-button login-submit" disabled={busy}>{busy ? "Signing in..." : "Sign in"}<ArrowRight size={17} /></button></form><div className="login-security"><LockKeyhole size={14} /> Secure access for authorized operations staff</div></div><div className="login-aside"><div className="aside-orb orb-one" /><div className="aside-orb orb-two" /><div className="aside-content"><div className="aside-kicker">DELIVERY, IN SYNC.</div><h2>Every parcel.<br />Every promise.<br /><span>On time.</span></h2><p>One clear view of your delivery operations, from first scan to final doorstep.</p><div className="aside-footer">BUILT FOR BETTER LAST-MILE OPERATIONS</div></div></div></div>;
}