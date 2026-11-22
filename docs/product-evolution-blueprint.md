# TimeDrop — Product evolution blueprint

TimeDrop is being developed as an end-to-end last-mile delivery operating platform, not only a parcel booking interface. The product should make every physical handover, customer communication, delivery movement and exception traceable.

## Product pillars

1. **Customer confidence:** live delivery map, credible arrival windows, proactive delay updates, self-service support, claim tracking, printable receipts and delivery evidence.
2. **Partner-first operations:** mobile-first delivery workspace, explicit shift/location consent, GPS sharing only during active work, offline-tolerant workflows, handover signatures and fair dispute handling.
3. **Evidence-led custody:** append-only custody events, signed handovers, condition and photo evidence, tamper-evident document records, and a transparent investigation process.
4. **Operational control tower:** fleet map, route sequencing, workload balancing, exception queues, SLA risk and auditable interventions.
5. **Trust and resilience:** role-based access, privacy by design, secure document access, retention policies, observability, backups and recovery drills.

## Delivery roadmap

| Phase | Capability | Product outcome |
|---|---|---|
| 52 | Live-location API foundation | Secure partner GPS ingestion and owner-scoped location reads |
| 53 | Customer live map + partner location controls | Map marker, route context, stale-state handling, ETA window, opt-in and stop-sharing controls |
| 54 | Support centre and claims | Case creation, issue categories, evidence attachments, case timeline, status, assignment and resolution |
| 55 | Printable document service | PDF registration receipts, booking confirmations, custody slips, delivery proof and claim documents with verification IDs |
| 56 | Digital handover signatures | Partner and receiving-party signatures, consent text, timestamps, device/session metadata and linked custody events |
| 57 | Operations control tower | Live fleet view, exception management, route re-planning, SLA risk and partner workload visibility |
| 58 | Customer/partner mobile experience | Installable PWA, permission education, resilient uploads, offline queue and push notification readiness |
| 59 | Trust, security and launch readiness | Privacy review, retention controls, abuse prevention, load tests, accessibility, incident response and pilot gates |

## Design principles

- Do not fake live data. Every map point and ETA must include its source and freshness.
- Do not expose partner location outside an active delivery assignment.
- Use the least-privilege model: parcel owners see their own parcel; partners see their own assignments; operations access is audited.
- Signatures prove that a person acknowledged a specific event. They do not by themselves prove negligence or authorize automatic wage deductions.
- A claim must be investigated with evidence, a response opportunity and an auditable decision.
- Documents must be generated from server-side records, carry a unique verification reference and be reproducible for authorized users.
- Design for Indian operating conditions: variable network quality, two-wheeler delivery, PIN-code zones, multilingual-ready content and low-end Android devices.
- Use standards-based APIs and provider adapters so mapping, routing, SMS, storage and PDF vendors can be changed without rewriting core workflows.

## External technical references

- Google Routes API supports route computation, route matrices and traffic-aware durations; traffic-aware routing is a separately billed capability and should be enabled only when the product economics justify it: https://developers.google.com/maps/documentation/routes
- Google documents the accuracy/latency trade-off between traffic-unaware, traffic-aware and traffic-aware-optimal routing: https://developers.google.com/maps/documentation/routes/config_trade_offs
- Mapbox Navigation documentation describes location snapping, off-route detection and predictive/offline map caching, useful patterns for a future partner mobile client: https://docs.mapbox.com/android/navigation/guides/device-location/ and https://docs.mapbox.com/android/navigation/guides/advanced/offline/

These are architectural references, not a commitment to a paid provider. Provider selection should follow a cost, coverage, data-processing and licensing review for Indian service areas.
