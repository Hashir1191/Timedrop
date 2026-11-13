import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity, ArrowRight, ArrowUpRight, Boxes, Check, CheckCircle2,
  Clock3, Layers3, MapPin, Menu, Package, Route, ShieldCheck, Truck, X,
} from "lucide-react";

const capabilities = [
  { icon: Package, number: "01", title: "One place for every parcel", description: "Register incoming parcels, organize delivery bookings, and keep every shipment's details easy to find.", tone: "blue" },
  { icon: Route, number: "02", title: "Smarter delivery coordination", description: "Bring delivery slots, partner availability, assignment capacity, and route recommendations together.", tone: "violet" },
  { icon: Activity, number: "03", title: "A clearer delivery journey", description: "Give customers a useful activity timeline while teams stay informed about handovers and delivery outcomes.", tone: "mint" },
];
const audiences = [
  { icon: Package, title: "For customers", text: "Book a delivery window and follow parcel progress from one simple portal." },
  { icon: Truck, title: "For delivery partners", text: "See assigned work, manage availability, and update delivery outcomes." },
  { icon: Boxes, title: "For operations teams", text: "Coordinate intake, warehouse custody, fleet capacity, and performance." },
];

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);
  return (
    <main className="td-landing">
      <div className="td-announcement"><span className="td-announcement-dot" />A more considered way to coordinate the last mile<ArrowUpRight size={13} aria-hidden="true" /></div>
      <header className="td-marketing-header">
        <Link className="td-wordmark" to="/" aria-label="TimeDrop home" onClick={closeMenu}><span className="td-wordmark-icon"><Activity size={19} strokeWidth={2.5} /></span><span>time<span>drop</span></span></Link>
        <button className="td-mobile-menu" type="button" aria-label={menuOpen ? "Close navigation" : "Open navigation"} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={20} /> : <Menu size={20} />}</button>
        <nav className={"td-marketing-nav " + (menuOpen ? "is-open" : "")} aria-label="Main navigation">
          <a href="#platform" onClick={closeMenu}>Platform</a><a href="#how-it-works" onClick={closeMenu}>How it works</a><a href="#teams" onClick={closeMenu}>Who it's for</a>
          <Link className="td-nav-login" to="/login" onClick={closeMenu}>Sign in</Link><Link className="td-nav-cta" to="/login" onClick={closeMenu}>Get started <ArrowRight size={15} /></Link>
        </nav>
      </header>

      <section className="td-hero">
        <div className="td-hero-copy">
          <div className="td-kicker"><span /> DELIVERY, IN SYNC.</div>
          <h1>Make every delivery feel <em>effortless.</em></h1>
          <p className="td-hero-description">From the first scan to the final doorstep, TimeDrop brings parcels, people, and delivery plans into one beautifully clear workspace.</p>
          <div className="td-hero-actions"><Link className="td-primary-cta" to="/login">Explore TimeDrop <ArrowRight size={17} /></Link><a className="td-secondary-cta" href="#platform">Discover the platform <ArrowUpRight size={16} /></a></div>
          <div className="td-trust-row"><span><CheckCircle2 size={15} /> Clear parcel visibility</span><span><CheckCircle2 size={15} /> Coordinated delivery teams</span></div>
        </div>

        <div className="td-hero-visual" aria-label="Illustrative preview of the TimeDrop delivery workspace">
          <div className="td-visual-glow" />
          <div className="td-preview-window">
            <div className="td-preview-topbar"><div className="td-preview-brand"><span><Activity size={13} /></span> timedrop <i>WORKSPACE PREVIEW</i></div><div className="td-preview-user"><span /> Operations view</div></div>
            <div className="td-preview-body">
              <aside className="td-preview-sidebar"><span className="active"><Layers3 size={14} /></span><span><Package size={14} /></span><span><Truck size={14} /></span><span><Activity size={14} /></span></aside>
              <div className="td-preview-content">
                <div className="td-preview-heading"><div><small>OVERVIEW</small><strong>Delivery overview</strong></div><span>Today <Clock3 size={12} /></span></div>
                <div className="td-preview-stats"><div><small>PARCEL FLOW</small><strong>In motion</strong><span className="td-stat-line"><i /></span></div><div><small>DELIVERY WINDOWS</small><strong>Organized</strong><span className="td-stat-note"><Check size={11} /> Slot-aware</span></div></div>
                <div className="td-preview-map"><div className="td-map-grid" /><svg viewBox="0 0 420 150" role="img" aria-label="Illustrative route connecting four delivery stops"><path d="M42 108 C90 105 93 43 158 52 S240 127 290 80 S350 42 378 31" className="td-map-route-shadow" /><path d="M42 108 C90 105 93 43 158 52 S240 127 290 80 S350 42 378 31" className="td-map-route" /><circle cx="42" cy="108" r="7" /><circle cx="158" cy="52" r="7" /><circle cx="290" cy="80" r="7" /><circle cx="378" cy="31" r="7" /><text x="27" y="132">01</text><text x="145" y="31">02</text><text x="277" y="104">03</text><text x="365" y="15">04</text></svg><span className="td-map-caption"><MapPin size={11} /> Route planning preview</span></div>
                <div className="td-preview-activity"><div className="td-activity-title">Delivery activity <span>WORKFLOW PREVIEW</span></div><div className="td-activity-row"><span className="td-activity-icon blue"><Package size={13} /></span><div><strong>Parcel registered</strong><small>Ready for scheduling</small></div><b>01</b></div><div className="td-activity-row"><span className="td-activity-icon violet"><Route size={13} /></span><div><strong>Delivery coordinated</strong><small>Slot and partner aligned</small></div><b>02</b></div></div>
              </div>
            </div>
          </div>
          <div className="td-floating-card td-floating-top"><span className="td-floating-icon"><ShieldCheck size={17} /></span><div><strong>Every step connected</strong><small>One shared workflow</small></div></div>
          <div className="td-floating-card td-floating-bottom"><span className="td-floating-icon mint"><Clock3 size={17} /></span><div><strong>Delivery, on your time</strong><small>Scheduling made clearer</small></div></div>
          <div className="td-hero-footnote">A connected view for customers and delivery teams</div>
        </div>
      </section>

      <section className="td-logo-strip" aria-label="Platform principles"><span>BUILT AROUND THE DELIVERY JOURNEY</span><div><Package size={16} /> PARCEL VISIBILITY</div><div><Clock3 size={16} /> DELIVERY SCHEDULING</div><div><Route size={16} /> TEAM COORDINATION</div><div><ShieldCheck size={16} /> OPERATIONAL CONTROL</div></section>

      <section className="td-section td-platform-section" id="platform">
        <div className="td-section-heading"><div className="td-kicker"><span /> THE PLATFORM</div><h2>All the moving parts.<br /><em>One clear picture.</em></h2><p>Delivery work gets complicated when information lives in different places. TimeDrop brings the key steps into a connected workflow.</p></div>
        <div className="td-capability-grid">{capabilities.map((item) => { const Icon = item.icon; return <article className="td-capability-card" key={item.number}><div className={"td-capability-icon " + item.tone}><Icon size={21} /></div><div className="td-capability-number">{item.number}</div><h3>{item.title}</h3><p>{item.description}</p><span className="td-card-arrow"><ArrowUpRight size={17} /></span></article>; })}</div>
      </section>

      <section className="td-how-section" id="how-it-works">
        <div className="td-how-inner">
          <div className="td-how-copy"><div className="td-kicker light"><span /> A CONNECTED WORKFLOW</div><h2>From parcel intake<br />to <em>doorstep.</em></h2><p>Keep each handoff visible. Give every team the context they need to move the delivery forward.</p><Link className="td-light-cta" to="/login">See your workspace <ArrowRight size={16} /></Link></div>
          <div className="td-journey"><div className="td-journey-line" />
            <div className="td-journey-step"><span><Package size={17} /></span><div><small>STEP 01</small><strong>Receive & register</strong><p>Capture parcel details and record the initial handover.</p></div><Check size={16} /></div>
            <div className="td-journey-step"><span><Clock3 size={17} /></span><div><small>STEP 02</small><strong>Schedule & coordinate</strong><p>Match delivery windows with partner availability and capacity.</p></div><Check size={16} /></div>
            <div className="td-journey-step"><span><Truck size={17} /></span><div><small>STEP 03</small><strong>Assign & deliver</strong><p>Give partners a focused view of their delivery tasks.</p></div><Check size={16} /></div>
            <div className="td-journey-step"><span><ShieldCheck size={17} /></span><div><small>STEP 04</small><strong>Confirm & learn</strong><p>Keep delivery outcomes and operational performance visible.</p></div><Check size={16} /></div>
          </div>
        </div>
      </section>

      <section className="td-section td-teams-section" id="teams"><div className="td-section-heading centered"><div className="td-kicker"><span /> ONE PLATFORM, CONNECTED TEAMS</div><h2>Designed around the people<br />who <em>make delivery happen.</em></h2></div>
        <div className="td-audience-grid">{audiences.map((item) => { const Icon = item.icon; return <article className="td-audience-card" key={item.title}><span><Icon size={22} /></span><h3>{item.title}</h3><p>{item.text}</p><Link to="/login" aria-label={"Open TimeDrop for " + item.title.toLowerCase()}>Open workspace <ArrowUpRight size={15} /></Link></article>; })}</div>
      </section>

      <section className="td-final-cta"><div className="td-final-orb" /><div className="td-kicker light"><span /> YOUR DELIVERY WORKSPACE</div><h2>Make room for a<br /><em>better delivery day.</em></h2><p>Bring your parcel journey into focus with TimeDrop.</p><Link className="td-primary-cta" to="/login">Get started with TimeDrop <ArrowRight size={17} /></Link></section>

      <footer className="td-footer"><Link className="td-wordmark" to="/" aria-label="TimeDrop home"><span className="td-wordmark-icon"><Activity size={18} /></span><span>time<span>drop</span></span></Link><p>Thoughtful coordination for the last mile.</p><div><a href="#platform">Platform</a><a href="#how-it-works">How it works</a><Link to="/login">Sign in</Link></div><small>© {new Date().getFullYear()} TimeDrop. Built for better delivery experiences.</small></footer>
    </main>
  );
}
