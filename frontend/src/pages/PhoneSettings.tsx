import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, ShieldCheck, Smartphone } from "lucide-react";
import { getPhoneStatus, requestPhoneCode, verifyPhoneCode, updateSmsConsent } from "../api";
import { useAuth } from "../auth";

type PhoneStatus = { phone_number: string | null; phone_verified: boolean; sms_notifications_consent: boolean };

export default function PhoneSettings() {
  const { token } = useAuth();
  const [status, setStatus] = useState<PhoneStatus | null>(null);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [developmentCode, setDevelopmentCode] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!token) return;
    try { const value = await getPhoneStatus(token); setStatus(value); setPhone(value.phone_number || ""); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to load phone settings."); }
  }
  useEffect(() => { void load(); }, [token]);

  async function requestCode(event: FormEvent) {
    event.preventDefault(); if (!token) return;
    setBusy(true); setError(""); setNotice(""); setDevelopmentCode("");
    try {
      const result = await requestPhoneCode(token, phone);
      setNotice(result.message);
      setDevelopmentCode(result.development_code || "");
      setCode("");
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to request a code."); }
    finally { setBusy(false); }
  }
  async function verify(event: FormEvent) {
    event.preventDefault(); if (!token) return;
    setBusy(true); setError(""); setNotice("");
    try { setStatus(await verifyPhoneCode(token, code)); setCode(""); setDevelopmentCode(""); setNotice("Phone number verified successfully."); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to verify phone number."); }
    finally { setBusy(false); }
  }
  async function consent(enabled: boolean) {
    if (!token) return;
    setBusy(true); setError(""); setNotice("");
    try { setStatus(await updateSmsConsent(token, enabled)); setNotice(enabled ? "SMS notification consent enabled." : "SMS notification consent withdrawn."); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to update consent."); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><div><div className="eyebrow">ACCOUNT / CONTACT PREFERENCES</div><h1>Phone & SMS settings</h1><p>Verify your mobile number and choose whether TimeDrop may send delivery updates by SMS.</p></div></div>
    {error && <div className="alert-error">{error}</div>}{notice && <div className="alert-success">{notice}</div>}
    <section className="panel customer-form-panel">
      <div className="panel-heading"><div><h2><Smartphone size={17}/> Mobile number</h2><p>Use an Indian mobile number that you control. Verification is separate from SMS marketing or notification consent.</p></div></div>
      <form className="customer-form" onSubmit={requestCode}>
        <label>Mobile number<input required value={phone} onChange={e=>setPhone(e.target.value)} placeholder="9876543210 or +919876543210" /></label>
        <div className="customer-form-actions"><span>{status?.phone_verified ? "Verified number" : "A new code invalidates any previous code."}</span><button className="primary-button" disabled={busy || !phone.trim()}>Request verification code</button></div>
      </form>
      {developmentCode && <div className="alert-success">Development OTP: <strong>{developmentCode}</strong> · No SMS was sent. This code is exposed only in development.</div>}
      <form className="customer-form" onSubmit={verify}>
        <label>6-digit verification code<input required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e=>setCode(e.target.value)} placeholder="Enter code" /></label>
        <div className="customer-form-actions"><span>Code expires after 5 minutes and allows up to 5 attempts.</span><button className="primary-button" disabled={busy || code.length!==6}>Verify phone</button></div>
      </form>
      {status?.phone_verified && <div className="alert-success"><CheckCircle2 size={16}/> {status.phone_number} is verified.</div>}
    </section>
    <section className="panel customer-form-panel">
      <div className="panel-heading"><div><h2><ShieldCheck size={17}/> SMS notification consent</h2><p>Optional. You can withdraw consent at any time. Verification alone does not enable SMS.</p></div></div>
      <div className="customer-form-actions"><span>{status?.sms_notifications_consent ? "SMS notifications are enabled." : "SMS notifications are disabled."}</span><button className={status?.sms_notifications_consent ? "secondary-button" : "primary-button"} disabled={busy || !status?.phone_verified} onClick={()=>void consent(!status?.sms_notifications_consent)}>{status?.sms_notifications_consent ? "Withdraw consent" : "Enable SMS notifications"}</button></div>
      <p className="cell-sub">SMS delivery is not active yet. TimeDrop is collecting verified contact details and explicit consent; messages will only be sent after the approved MSG91 and Indian DLT setup is completed.</p>
    </section>
  </>;
}
