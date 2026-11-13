import { useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Activity, ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, UserPlus } from "lucide-react";
import { getMe, login, register } from "../api";
import { useAuth } from "../auth";

export default function Login() {
  const { user, setAuth } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") await register({ email, full_name: name, password });
      const tokenResponse = await login(email, password);
      const currentUser = await getMe(tokenResponse.access_token);
      localStorage.setItem("timedrop_token", tokenResponse.access_token);
      setAuth({ token: tokenResponse.access_token, user: currentUser, loading: false });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to continue.");
    } finally {
      setBusy(false);
    }
  }

  const registering = mode === "register";

  return (
    <div className="login-screen auth-experience-screen">
      <div className="login-panel auth-experience-panel">
        <div className="auth-topline">
          <Link className="login-brand auth-brand-link" to="/" aria-label="Back to TimeDrop home">
            <span className="brand-mark"><Activity size={22} /></span>
            <span>time<span className="brand-accent">drop</span></span>
          </Link>
          <Link className="auth-back-link" to="/"><ArrowLeft size={14} /> Home</Link>
        </div>

        <div className="auth-form-intro">
          <div className="login-eyebrow">{registering ? "JOIN THE TIMEDROP COMMUNITY" : "YOUR DELIVERY WORKSPACE"}</div>
          <h1>{registering ? "Let's get started." : "Welcome back."}</h1>
          <p className="login-subtitle">
            {registering
              ? "Create a customer account to register parcels and schedule deliveries."
              : "Sign in to pick up where your delivery journey left off."}
          </p>
        </div>

        <form onSubmit={submit} className="login-form auth-login-form">
          {registering && (
            <div className="auth-field">
              <label htmlFor="auth-full-name">Full name</label>
              <input id="auth-full-name" value={name} onChange={event => setName(event.target.value)} placeholder="Your full name" required minLength={2} autoComplete="name" />
            </div>
          )}
          <div className="auth-field">
            <label htmlFor="auth-email">Email address</label>
            <input id="auth-email" type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" required autoComplete="username" />
          </div>
          <div className="auth-field">
            <label htmlFor="auth-password">Password</label>
            <div className="auth-password-wrap">
              <input id="auth-password" type={showPassword ? "text" : "password"} value={password} onChange={event => setPassword(event.target.value)} placeholder={registering ? "At least 8 characters" : "Enter your password"} required minLength={registering ? 8 : 1} autoComplete={registering ? "new-password" : "current-password"} />
              <button type="button" className="auth-password-toggle" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
            {registering && <span className="auth-field-hint">Use at least 8 characters for your password.</span>}
          </div>

          {error && <div className="form-error auth-form-error" role="alert" aria-live="polite">{error}</div>}
          <button className="primary-button login-submit auth-submit" disabled={busy}>
            {busy ? "Please wait…" : registering ? "Create customer account" : "Sign in to TimeDrop"}
            {registering ? <UserPlus size={17} /> : <ArrowRight size={17} />}
          </button>
        </form>

        <div className="auth-switch-row">
          <span>{registering ? "Already have an account?" : "New to TimeDrop?"}</span>
          <button type="button" className="auth-mode-toggle" onClick={() => { setMode(registering ? "login" : "register"); setError(""); setShowPassword(false); }}>
            {registering ? "Sign in" : "Create a customer account"}
          </button>
        </div>

        <div className="login-security"><LockKeyhole size={14} /> Secure sign-in with your TimeDrop account</div>
        <p className="auth-registration-note">Customer registration is open here. Delivery partner and operations accounts are provisioned by the operations team.</p>
      </div>

      <div className="login-aside auth-experience-aside">
        <div className="aside-orb orb-one" /><div className="aside-orb orb-two" />
        <div className="aside-content">
          <div className="aside-kicker">DELIVERY, IN SYNC.</div>
          <h2>Every parcel.<br />Every promise.<br /><span>On time.</span></h2>
          <p>One clear view of your delivery journey, from parcel registration to the doorstep.</p>
          <div className="auth-aside-points"><span><Activity size={15} /> One connected workspace</span><span><LockKeyhole size={15} /> Account-aware access</span></div>
          <div className="aside-footer">BUILT FOR BETTER LAST-MILE OPERATIONS</div>
        </div>
      </div>
    </div>
  );
}
