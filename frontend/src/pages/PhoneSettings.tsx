import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, ShieldCheck, Smartphone } from "lucide-react";
import { getPhoneStatus, requestPhoneCode, resendPhoneCode, verifyPhoneCode, updateSmsConsent } from "../api";
import { useAuth } from "../auth";

type PhoneStatus = { phone_number: string | null; phone_verified: boolean; sms_notifications_consent: boolean };

export default function PhoneSettings() {
  const { token } = useAuth();
  const [status, setStatus] = useState<PhoneStatus | null>(null);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [developmentCode, setDevelopmentCode] = useState("");
  const [deliveryMode, setDeliveryMode] = useState("");
  const [challengeActive, setChallengeActive] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    if (!token) return;
    try { const value = await getPhoneStatus(token); setStatus(value); setPhone(value.phone_number || ""); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load phone settings."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [token]);

  function applyChallenge(result: { message: string; development_code?: string; delivery_mode?: string }) {
    setNotice(result.message);
    setDevelopmentCode(result.development_code || "");
    setDeliveryMode(result.delivery_mode || "msg91");
    setChallengeActive(true);
    setCode("");
  }

  async function requestCode(event: FormEvent) {
    event.preventDefault(); if (!token) return;
    setBusy(true); setError(""); setNotice(""); setDevelopmentCode("");
    try { const result = await requestPhoneCode(token, phone); applyChallenge(result); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to request a code."); }
    finally { setBusy(false); }
  }
  async function resendCode() {
    if (!token) return;
    setBusy(true); setError(""); setNotice(""); setDevelopmentCode("");
    try { applyChallenge(await resendPhoneCode(token)); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to resend a code."); }
    finally { setBusy(false); }
  }
  async function verify(event: FormEvent) {
    event.preventDefault(); if (!token) return;
    setBusy(true); setError(""); setNotice("");
    try {
      setStatus(await verifyPhoneCode(token, code));
      setCode(""); setDevelopmentCode(""); setChallengeActive(false);
      setNotice("Phone number verified successfully.");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to verify phone number."); }
    finally { setBusy(false); }
  }
  async function consent(enabled: boolean) {
    if (!token) return;
    setBusy(true); setError(""); setNotice("");
    try { setStatus(await updateSmsConsent(token, enabled)); setNotice(enabled ? "SMS notification consent enabled." : "SMS notification consent withdrawn."); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to update consent."); }
    finally { setBusy(false); }
  }

  return <div className="phone-settings-workspace">
    <div className="page-heading"><div><div className="eyebrow">ACCOUNT / CONTACT PREFERENCES</div><h1>Phone & SMS settings</h1><p>Verify your mobile number and choose whether TimeDrop may send delivery updates by SMS.</p></div></div>
    <section className="phone-settings-overview">
      <div className="phone-overview-item"><span className="phone-overview-icon"><Smartphone size={17}/></span><div><small>PHONE VERIFICATION</small><strong>{loading?"Loading…":status?.phone_verified?"Verified":"Not verified"}</strong><span>{status?.phone_number||"No mobile number added"}</span></div><span className={`phone-overview-state ${status?.phone_verified?"verified":""}`}>{status?.phone_verified?"Verified":"Action needed"}</span></div>
      <div className="phone-overview-item"><span className="phone-overview-icon sms"><ShieldCheck size={17}/></span><div><small>SMS NOTIFICATIONS</small><strong>{status?.sms_notifications_consent?"Enabled":"Disabled"}</strong><span>Optional delivery updates by text</span></div><span className={`phone-overview-state ${status?.sms_notifications_consent?"verified":""}`}>{status?.sms_notifications_consent?"Opted in":"Opted out"}</span></div>
    </section>
    {error && <div className="alert-error" role="alert">{error}</div>}{notice && <div className="alert-success" role="status">{notice}</div>}
    <section className="panel customer-form-panel">
      <div className="panel-heading"><div><h2><Smartphone size={17}/> Mobile number</h2><p>Use an Indian mobile number that you control. Verification is separate from SMS notification consent.</p></div></div>
      <form className="customer-form" onSubmit={requestCode}>
        <label htmlFor="phone-number">Mobile number<input id="phone-number" required autoComplete="tel" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="9876543210 or +919876543210" /></label>
        <div className="customer-form-actions"><span>{status?.phone_verified ? "Verified number" : "Request a code to verify this number."}</span><button className="primary-button" disabled={busy || !phone.trim()}>Send verification code</button></div>
      </form>
      {deliveryMode === "msg91" && challengeActive && <div className="cell-sub">A verification code was sent by SMS. Enter the code below. TimeDrop does not store or display the provider-generated OTP.</div>}
      {developmentCode && <div className="alert-success">Development OTP: <strong>{developmentCode}</strong> · No SMS was sent. This is available only in local development.</div>}
      {challengeActive && <form className="customer-form" onSubmit={verify}>
        <label htmlFor="phone-verification-code">6-digit verification code<input id="phone-verification-code" required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e=>setCode(e.target.value)} placeholder="Enter code" /></label>
        <div className="customer-form-actions">
          <span>Code expires after {5} minutes. Up to 5 verification attempts are allowed.</span>
          <div className="button-row"><button type="button" className="secondary-button" disabled={busy} onClick={()=>void resendCode()}>Resend code</button><button className="primary-button" disabled={busy || code.length!==6}>Verify phone</button></div>
        </div>
      </form>}
      {status?.phone_verified && <div className="alert-success"><CheckCircle2 size={16}/> {status.phone_number} is verified.</div>}
    </section>
    <section className="panel customer-form-panel">
      <div className="panel-heading"><div><h2><ShieldCheck size={17}/> SMS notification consent</h2><p>Optional. You can withdraw consent at any time. Verification alone does not enable SMS.</p></div></div>
      <div className="customer-form-actions"><span>{status?.sms_notifications_consent ? "SMS notifications are enabled." : "SMS notifications are disabled."}</span><button className={status?.sms_notifications_consent ? "secondary-button" : "primary-button"} disabled={busy || !status?.phone_verified} onClick={()=>void consent(!status?.sms_notifications_consent)}>{status?.sms_notifications_consent ? "Withdraw consent" : "Enable SMS notifications"}</button></div>
      <p className="cell-sub">Transactional SMS also requires the approved MSG91 Flow and Indian DLT configuration. Phone verification and notification consent remain separate.</p>
    </section>
  </div>;
}
