# TimeDrop

TimeDrop is an India-first last-mile delivery scheduling platform prototype.

The pilot must only handle parcels that TimeDrop is explicitly authorized to receive and handle. Use synthetic data during development.

## Current milestone

- FastAPI application with Swagger/OpenAPI documentation
- SQLAlchemy persistence with SQLite for local development and PostgreSQL support
- Alembic versioned database migrations, including a non-destructive baseline adoption migration for existing pilot databases
- Docker Compose development environment with PostgreSQL 16 and a non-root FastAPI container
- Customer registration and JWT login
- Separate role-based customer and operations web portals
- Customer parcel creation, personal parcel list, and delivery booking management
- Operations delivery-slot management and booking register
- Delivery partner accounts provisioned by operations admins
- Parcel assignment to active delivery partners (only after a delivery slot is booked)
- Partner-only assignment inbox and controlled delivery status transitions
- Append-only delivery event history with actor, timestamps, status changes and failure notes
- One-time-code proof of delivery with 30-minute expiry, hashed storage and five-attempt lockout
- Argon2 password hashing and role-based access control

## Delivery partner API

All endpoints are under `/api/v1/delivery`.

| Method | Endpoint | Access |
|---|---|---|
| POST | `/partners` | Admin |
| GET | `/partners` | Admin |
| POST | `/parcels/{parcel_id}/assignments` | Admin |
| GET | `/assignments` | Admin |
| GET | `/my-assignments` | Delivery partner |
| PATCH | `/assignments/{assignment_id}/status` | Assigned delivery partner |
| GET | `/assignments/{assignment_id}/events` | Admin, assigned partner, or parcel owner |
| POST | `/parcels/{parcel_id}/delivery-code` | Parcel owner; only while out for delivery |
| POST | `/assignments/{assignment_id}/proof` | Assigned delivery partner |

Operations creates partner accounts; public registration always creates customers. Assignments require an active booking and an active, available partner. A partner can only see and update their own assignments. The allowed lifecycle is assigned → accepted → out_for_delivery → delivered, with failed as an allowed terminal outcome from assigned, accepted, or out_for_delivery. Failed updates require a reason, which is persisted on the assignment. Delivery events are written when operations assigns a parcel and when a partner changes delivery status. The operations and partner portals display the event timeline. This is an append-only application event history, not a tamper-proof audit log. For proof of delivery, the parcel owner generates a six-digit code while the parcel is out for delivery. The code expires after 30 minutes, is stored only as an Argon2 hash, and is invalidated after five incorrect attempts or successful verification. A partner must submit the code and recipient name to complete delivery; the server records the recipient and timestamp and writes a proof event. Code delivery is currently shown inside the authenticated customer portal; SMS/email delivery and photo/signature evidence are not included.

## Run on Windows PowerShell

Create and activate a virtual environment:

```powershell
py -3 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\\requirements-dev.txt
```

Copy `.env.example` to `.env`. Local non-Docker development uses SQLite by default. Set `APP_ENV=production`, a unique `SECRET_KEY` of at least 32 characters, and the production `CORS_ORIGINS` before deployment. Production mode rejects the development secret and SQLite. Never commit `.env`.

### Option A: Run with SQLite (existing local workflow)

Apply database migrations from the repository root:

```powershell
$env:PYTHONPATH = "backend"
python -m alembic -c backend\\alembic.ini upgrade head
python -m alembic -c backend\\alembic.ini current
```

The first migration creates missing tables and conditionally adds the ownership, delivery-failure, and proof-of-delivery fields introduced in earlier pilot versions. It is designed to preserve existing rows; it does not delete or recreate the database.

Start the API after migrations:

```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --app-dir backend
```

Open Swagger UI at http://127.0.0.1:8000/docs.

### Option B: Run the API and PostgreSQL with Docker Compose

Install and start Docker Desktop, then run these commands from the repository root:

```powershell
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

Compose starts PostgreSQL 16 with a persistent named volume, waits for its health check, builds the API image, applies Alembic migrations, and then starts FastAPI. The API is available at http://localhost:8000 and Swagger UI at http://localhost:8000/docs. PostgreSQL is exposed on localhost:5432 for database tools. The frontend can continue running locally with the steps in the Frontend section.

For the local Compose environment, the defaults are intentionally development-only. Override `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `SECRET_KEY`, and ports through the root `.env` file before sharing the environment or exposing it beyond your machine. Use a URL-safe PostgreSQL password; if it contains reserved URL characters, percent-encode it when constructing a connection URL.

Stop containers while retaining the database volume:

```powershell
docker compose down
```

Stop containers and permanently delete the Compose database volume (destructive; only for disposable local data):

```powershell
docker compose down -v
```

**SQLite data is not copied automatically into PostgreSQL.** The two databases are separate. Keep using SQLite for your existing pilot data until you are ready to perform a planned migration. Do not run `docker compose down -v` if you need to preserve PostgreSQL data.

#### Optional: transfer existing SQLite data to PostgreSQL

This is a deliberate, separate operation. First stop the API and any process that can write to SQLite, and make a backup:

```powershell
Copy-Item .\\timedrop.db .\\timedrop-before-postgres-migration.db
```

Start the Compose database and API so the PostgreSQL schema is created:

```powershell
docker compose up --build -d
docker compose ps
```

Run a read-only preflight (replace the example password with the value in your local `.env`):

```powershell
$env:PYTHONPATH = "backend"
python backend\\scripts\\migrate_sqlite_to_postgres.py --source .\\timedrop.db --target-url "postgresql+psycopg://timedrop_user:change-this-local-docker-password@localhost:5432/timedrop"
```

The preflight checks that both databases have the same Alembic revision, the same business tables and columns, and that every PostgreSQL business table is empty. It prints the source row counts and changes no data.

Only after reviewing a successful preflight, repeat the command with `--execute`:

```powershell
python backend\\scripts\\migrate_sqlite_to_postgres.py --source .\\timedrop.db --target-url "postgresql+psycopg://timedrop_user:change-this-local-docker-password@localhost:5432/timedrop" --execute
```

The utility reads SQLite in read-only mode, copies rows in foreign-key dependency order, preserves primary keys, updates PostgreSQL integer sequences, and writes all copied rows in one PostgreSQL transaction. It refuses to overwrite a non-empty target or proceed when schema/revision checks fail. Keep the SQLite backup until you have separately verified the PostgreSQL data and application behavior. Use a URL-safe password in the connection URL; percent-encode reserved URL characters.

Run tests after the development phase is complete:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\\tests -v
```

## Frontend

The React + Vite + TypeScript frontend lives in `frontend/`.

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Keep the API running in a separate terminal. For the Docker Compose backend, the frontend still runs locally and calls the API at localhost:8000.

## Security and operations

- Never commit `.env` or share passwords/access tokens.
- Configure HTTPS and set `CORS_ORIGINS` to only the trusted frontend origins before external use.
- Configure `DATABASE_URL` for PostgreSQL in deployed environments; SQLite remains the local non-Docker development default.
- The PostgreSQL driver and Alembic are installed from `backend/requirements.txt`.
- Apply database migrations as a deployment step before starting new application instances; the API intentionally does not mutate the schema at startup. The Compose command applies migrations for this single-instance local development setup.
- Back up the database before applying migrations to any environment containing important data.
- Replace localStorage token storage with a production-grade session design before production.
- Do not accept, store, transport, or deliver third-party marketplace parcels unless the relevant seller, carrier, and operational parties have explicitly authorized the arrangement.

## In-app notifications

TimeDrop stores user-scoped in-app notifications for key booking and delivery events. The inbox is available to customers, delivery partners, and operations users in the application header. Notifications are created in the same database transaction as the underlying booking or delivery change.

Current events include booking creation/rescheduling/cancellation, delivery partner assignment, partner acceptance, out-for-delivery, failed delivery, and proof-verified completion.

Authenticated API endpoints:
- `GET /api/v1/notifications/` — list the signed-in user's latest notifications; supports `unread_only=true` and `limit`.
- `GET /api/v1/notifications/unread-count` — get the user's unread count.
- `PATCH /api/v1/notifications/{id}/read` — mark one of the signed-in user's notifications as read.
- `POST /api/v1/notifications/read-all` — mark all of the signed-in user's notifications as read.

## External notification delivery

The durable `notification_deliveries` outbox supports email through Resend and transactional SMS through MSG91 Flow. Jobs are created atomically with the in-app notification, claimed by the background worker, retried with exponential backoff, and marked sent or failed. Email requires `RESEND_API_KEY` and `NOTIFICATION_FROM_EMAIL`.

### MSG91 SMS setup

SMS remains disabled by default. To enable it, configure these values in the uncommitted root `.env` file and in the deployment secret store:

- `MSG91_AUTH_KEY`: MSG91 account auth key.
- `MSG91_FLOW_TEMPLATE_ID`: the approved MSG91 Flow/template ID.
- `SMS_NOTIFICATIONS_ENABLED=true`: explicit feature switch; defaults to false.

The MSG91 Flow must have two variables with these exact case-sensitive names: `VAR1` for the notification title and `VAR2` for the notification message. The template text must be approved and match the Indian DLT-registered entity, sender/header, and template details. Do not enable the feature until MSG91 reports the template as DLT-verified. TimeDrop sends only to the account's own normalized Indian mobile number, and only when `phone_verified_at` and `sms_consent_at` are both present. Parcel recipient numbers and the legacy delivery-partner contact field are never used as SMS recipients. Withdrawing consent prevents future SMS jobs; it does not cancel messages already submitted to the provider.

The worker uses MSG91's Flow endpoint `POST https://control.msg91.com/api/v5/flow` with the `authkey` header, `template_id`, and a recipient object containing `mobiles`, `VAR1`, and `VAR2`. Provider failures are recorded in the outbox and retried using the same idempotency key at the application layer. MSG91 acceptance is not proof of handset delivery; use MSG91 delivery logs for final delivery status. See the [MSG91 Send SMS API](https://docs.msg91.com/sms/send-sms) and [MSG91 DLT template setup guide](https://msg91.com/help/template/how-to-create-flow-id-to-send-sms-via-api).

### Phone verification and SMS consent

Customer and delivery-partner accounts can manage a mobile number at **Phone & SMS** in their portal. The API normalizes Indian mobile numbers to +91 format, prevents a number from being linked to multiple accounts, invalidates older challenges when a new code is requested, stores only an Argon2 hash, expires codes after five minutes, limits verification to five attempts, and rate-limits requests to three per account per 15 minutes.

Endpoints (authenticated):
- `GET /api/v1/phone-verification/me` — current phone verification and SMS consent state.
- `POST /api/v1/phone-verification/request` — request a verification challenge.
- `POST /api/v1/phone-verification/verify` — verify a six-digit code.
- `PUT /api/v1/phone-verification/sms-consent` — explicitly enable or withdraw SMS notification consent.

**Development mode:** no SMS is sent for OTP verification. With `PHONE_OTP_EXPOSE_IN_DEVELOPMENT=true`, the API returns a development-only OTP in its response so the workflow can be exercised locally. Production mode currently rejects OTP requests; a production-grade MSG91 OTP verification flow is a separate prerequisite before production onboarding. Transactional delivery SMS is a separate feature and requires both verified phone status and explicit SMS consent.


## Delivery ETA and customer tracking

Delivery partners can publish or revise an estimated arrival window from their assignment card. Operations admins can also update the ETA through the authenticated API:

- `PATCH /api/v1/delivery/assignments/{assignment_id}/eta` — accepts timezone-aware `estimated_delivery_start` and `estimated_delivery_end` timestamps.
- `GET /api/v1/delivery/my-tracking` — returns assignment progress and ETA only for parcels owned by the signed-in customer.

ETA changes are rejected for completed or failed assignments, are recorded in the append-only delivery event history, and create an in-app notification for the parcel owner. The customer portal displays the current estimate and delivery event timeline. This is an operator/partner-maintained estimate, not GPS-based live tracking; no continuous location collection is performed.

Apply the new Alembic migration before using this feature.


## Route planning and assignment recommendations

Operations admins can generate a non-binding route/assignment proposal for a delivery date:

- `GET /api/v1/delivery/route-plan?delivery_date=YYYY-MM-DD` — returns booked, scheduled parcels that do not already have an active assignment, along with suggested partners and proposed stop sequence.

The first version uses a transparent heuristic: it balances active partner workload, groups parcels sharing the same first three PIN-code digits, and avoids assigning a partner to overlapping booked delivery slots. Operations must explicitly apply each suggested assignment; generating a plan does not create or change assignments.

### Map-based route optimization (optional)

The planner can optionally use OpenStreetMap Nominatim for address geocoding and OSRM for driving-route optimization. For each suggested partner, OSRM's trip service reorders geocoded stops and returns road-leg distance and duration estimates. The operations screen shows coordinates, road estimates, and a link to open the proposed route in OpenStreetMap. If a destination cannot be geocoded or a provider is unavailable, that stop remains in the plan and the existing PIN-prefix heuristic is retained as a fallback.

Map routing is **disabled by default**. To enable it, set these values in the uncommitted root `.env` file:

```dotenv
ROUTE_MAPPING_ENABLED=true
ROUTE_GEOCODER_URL=https://nominatim.openstreetmap.org/search
ROUTE_ROUTER_URL=https://router.project-osrm.org
ROUTE_PROVIDER_USER_AGENT=TimeDrop/1.0 (route-planning; contact: your-monitored-email@example.com)
ROUTE_GEOCODE_TIMEOUT_SECONDS=8
```

Replace the sample User-Agent with a descriptive application identifier and a monitored contact address. Apply the new Alembic migration before using the feature:

```powershell
$env:PYTHONPATH = "backend"
python -m alembic -c backend\\alembic.ini upgrade head
```

Address coordinates are cached in the `route_geocode_cache` table using a SHA-256 hash of the normalized address; the original address is not copied into the cache table. When mapping is enabled, the delivery address is sent to the configured geocoding provider and coordinates are sent to the configured routing provider. Keep mapping disabled unless your privacy notice and operational policy permit this processing. Do not send sensitive or real customer addresses to public demo services without authorization.

The public Nominatim service has a strict usage policy (including a maximum of one request per second and a descriptive User-Agent); the public OSRM demo server has no production availability guarantee. These public endpoints are suitable only for low-volume development and evaluation. For production, use a compliant hosted provider or self-host the geocoder/router, configure the URLs accordingly, and review provider retention, rate limits, coverage, and service terms. Road estimates do not include live traffic and are not turn-by-turn navigation.

## Production phone OTP verification

Phone verification uses MSG91's OTP API when the application is not in local development OTP mode. Configure `MSG91_AUTH_KEY` and `MSG91_OTP_TEMPLATE_ID` in the deployment secret store. The OTP template must be created in the MSG91 OTP section and contain the `##OTP##` placeholder. The API requests a six-digit code with the configured expiry; MSG91 generates and stores the production OTP. TimeDrop does not generate, store, log, or return the production OTP.

- `POST /api/v1/phone-verification/request` sends a provider-generated OTP.
- `POST /api/v1/phone-verification/resend` requests a replacement OTP for the account's current phone number. It is subject to the same account-level rate limit.
- `POST /api/v1/phone-verification/verify` verifies the submitted code with MSG91. The application checks the provider response `type`; HTTP 200 alone does not mean the OTP is valid.
- The existing local challenge row tracks the application's expiry, attempt limit, and request rate. The actual production OTP remains managed by MSG91.

For local development only, set `APP_ENV=development` and `PHONE_OTP_EXPOSE_IN_DEVELOPMENT=true` to use the local six-digit OTP response without sending SMS. To exercise MSG91 from a non-production environment, set `PHONE_OTP_EXPOSE_IN_DEVELOPMENT=false` and configure the MSG91 auth key and OTP template ID. Never enable development OTP exposure in production. Production must set `APP_ENV=production`; in that mode the development OTP path is always disabled.

The MSG91 OTP API requires an approved OTP template and configured sender/DLT setup for Indian delivery. See the [MSG91 SendOTP API](https://docs.msg91.com/otp/sendotp), [Verify OTP API](https://docs.msg91.com/en/otp/verify-otp), and [OTP configuration guide](https://msg91.com/help/sendotp/step-by-step-process-to-configure-otp).


## Operations parcel intake and custody

Operations administrators can register a parcel at the point it is physically received through **Parcel intake** in the admin portal. Intake captures the tracking number, recipient and destination details, optional link to an existing customer account, source of the parcel, observed package condition, and an optional note.

The authenticated operations API is:
- `POST /api/v1/operations/intake` — register a parcel and append its initial `received` custody event.
- `GET /api/v1/operations/intake` — list the latest 100 operations intake records.
- `GET /api/v1/operations/parcels/{parcel_id}/custody` — retrieve the parcel's append-only custody history.
- `POST /api/v1/operations/parcels/{parcel_id}/release` — record handover to the assigned delivery partner. A parcel must have an active `assigned` delivery assignment before release.

Every custody event records the acting operations user and timestamp. Intake is limited to existing customer accounts when an account email is supplied; the API does not create customer accounts implicitly. The first release records the assigned partner's name. Repeated release attempts are rejected.

This is an application-level operational event history, not a tamper-proof audit ledger. The pilot should use synthetic parcel details until the workflow, authorization, and retention requirements have been reviewed. Only receive parcels TimeDrop is explicitly authorized to handle.


## Failed delivery returns to operations

When a delivery attempt fails after a parcel has been handed to a partner, operations must record the parcel's physical return before assigning it again. The operations custody screen exposes **Receive failed parcel** after the partner reports a failed delivery and the custody history shows a prior partner release.

- `POST /api/v1/operations/parcels/{parcel_id}/return` — operations-only receipt of a failed parcel from its assigned delivery partner. Requires `package_condition` (`intact`, `damaged`, or `opened`) and an inspection note.
- The API appends a `returned` custody event with the partner name, operations actor, timestamp, inspected condition, and note. Parcel status becomes `returned_to_operations`.
- Reassignment is blocked while the latest custody event is `released`; operations must first record the physical return. After return, the parcel can be explicitly reassigned and released again.
- This records an operator-confirmed physical handover; it does not independently verify the parcel's location or automatically retry delivery.


## Warehouse management

The operations workspace includes a warehouse inventory page with live parcel counts, search by tracking number/recipient/city/PIN, status filtering, and storage-bin assignment.

- `GET /api/v1/operations/warehouse/summary` — live totals for parcels, parcels currently in operations custody, bin assignments, parcels awaiting storage, damaged/opened inspections, out-for-delivery, delivered, and failed.
- `GET /api/v1/operations/warehouse/parcels?q=&parcel_status=&location=` — search and filter up to 200 parcels. Use `location=unassigned` to find parcels without a storage bin.
- `PATCH /api/v1/operations/warehouse/parcels/{parcel_id}/location` — set or clear a storage-bin code while the latest custody event is `received` or `returned`.

Storage-bin values are operator-entered labels (for example `A-01-02`), not a live warehouse-location or barcode system. The migration adds nullable `parcels.warehouse_location`.


## Customer parcel activity timeline

The customer portal's parcel history now combines parcel registration, the current booking state, delivery assignment/status/ETA events, and operations custody handovers into one chronological timeline.

- `GET /api/v1/parcels/{parcel_id}/timeline` — returns a customer-safe activity history for the signed-in parcel owner (or operations admin).
- The endpoint checks parcel ownership and returns 404 for another customer's parcel.
- Internal custody notes, raw failure notes, delivery verification codes, and recipient contact details are not included in the timeline.
- The customer **My parcels** page exposes the unified history under **Full parcel activity**. This is event-based progress, not GPS/live-location tracking.


## Operations analytics and partner performance

The admin **Analytics** workspace summarizes recorded parcel and delivery-assignment activity over a selected inclusive date range (maximum 366 calendar days).

- `GET /api/v1/operations/analytics?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — returns parcels created, assignments created, delivered/failed/active assignments, delivery success rate, average completed-delivery duration, partner-level performance, and daily assignment/outcome counts.
- Date filtering is based on parcel creation and assignment creation timestamps. Delivery success rate uses terminal assignments (delivered + failed) as its denominator; active assignments are excluded.
- Average delivery duration is calculated only for delivered assignments with a recorded `delivered_at` timestamp and non-negative elapsed time.
- Partner metrics include assignments created within the selected period, delivered/failed/active counts, terminal-outcome success rate, and average duration where available.
- Daily delivered counts use `delivered_at`; failed counts use the assignment's last update timestamp because the current schema does not have a dedicated failure timestamp.
- All analytics endpoints are admin-only and read existing records; they do not change parcel or assignment state.


## Partner capacity-aware assignment

Delivery partners have an operations-configured **maximum active assignment** limit (1–50, default 5). The limit is shown in the delivery team register and can be set when an administrator creates a partner account.

- The route planner excludes partners already at their active assignment limit.
- The manual assignment API enforces the same limit, so bypassing a recommendation does not bypass capacity.
- Assignment creation also rejects overlapping booked delivery windows for the same partner on the same date.
- Active load includes assignments in `assigned`, `accepted`, or `out_for_delivery`; delivered and failed assignments do not consume capacity.
- PIN-prefix grouping remains a locality heuristic, not a verified service-zone boundary. Partner capacity and slot compatibility are hard constraints; geographic grouping is a ranking preference.

The migration adds `delivery_partners.max_active_assignments` with a default of 5 for existing partner records. Apply Alembic migrations before using the updated API.


## Phase 12 — Actionable notifications and partner task workspace

Notifications now include a safe, same-origin application destination. Selecting a customer parcel notification opens **My parcels** with the related parcel highlighted; selecting a delivery-partner notification opens the partner delivery workspace. Notifications without a supported destination remain readable and can still be marked as read. Existing notification ownership checks remain unchanged.

The partner delivery workspace now defaults to active assignments, supports filtering between active, completed/failed, and all deliveries, and allows searching by tracking ID, recipient name, city, or PIN. Results are ordered by booked delivery date and time to make the next operational tasks easier to scan.

The migration adds nullable `notifications.action_url`; existing notifications remain valid and simply have no destination. Notification destinations are generated server-side from the authenticated recipient role and parcel ID; external URLs are not accepted by the UI navigation handler.


## Phase 13 — Delivery partner weekly availability

Delivery partners can configure recurring weekly working windows using local delivery-slot time. Availability is optional for existing partners: until a partner enables a schedule, the previous availability and assignment behavior is preserved.

- `GET /api/v1/delivery/my-availability` — read the signed-in partner's schedule.
- `PUT /api/v1/delivery/my-availability` — replace the partner's weekly schedule and enable or disable schedule enforcement.
- `GET /api/v1/delivery/partners/{partner_id}/availability` — operations-only view of a partner's schedule.
- Weekdays use Python's ISO-style weekday numbering: Monday `0` through Sunday `6`.
- Multiple non-overlapping windows can be configured per weekday. A booked delivery slot must fit fully inside one active availability window.
- Enabling a schedule with no active windows makes the partner unavailable for new assignments. Disabling the schedule restores the legacy behavior without deleting the saved windows.
- Manual assignment and route-plan recommendations use the same availability rule. Existing active assignments are not cancelled when a partner changes their future availability.
- The partner can manage only their own schedule; only operations administrators can view another partner's schedule.

Apply the Alembic migration before using this feature:

```powershell
$env:PYTHONPATH = "backend"
python -m alembic -c backend\\alembic.ini upgrade head
```


## Phase 14 — UI foundation and partner availability workspace

The frontend now has a shared visual foundation in `frontend/src/design-system.css`, layered over the existing styles so the current role-based portals can be modernized incrementally without a risky rewrite. It introduces consistent brand tokens, refined navigation and application surfaces, improved focus states, reduced-motion handling, and responsive shell refinements.

Delivery partners can manage their weekly availability from **Availability** in the partner workspace. The page supports enabling/disabling schedule enforcement, adding multiple windows per weekday, pausing individual windows, and saving the schedule through the Phase 13 API. Client-side checks flag invalid or overlapping time windows before submission.

The visual system is intentionally dependency-light for this first pass. Existing React, TypeScript, Vite, Tailwind, and Lucide dependencies remain in place; additional UI libraries will be introduced only where they add a clear product benefit.


## Phase 15 — Customer portal experience

The customer overview and parcel directory have been refreshed around a more product-focused delivery experience.

- The customer dashboard presents a branded welcome area, live account metrics, recent parcel cards, and direct actions to create or manage deliveries.
- The parcel directory supports search by tracking number, recipient, city, and PIN, plus filters for all, in-progress, delivered, and cancelled parcels.
- Parcel cards present destination, registration date, customer-visible ETA when available, booking actions, and the existing customer-safe activity timeline.
- Delivery-code generation remains available only while a parcel is out for delivery.
- Loading, empty, error, and narrow-screen states have dedicated layouts. The interface continues to use API-backed values rather than fabricated dashboard metrics.

The refresh is implemented with the existing React and TypeScript components and a dedicated `customer-portal.css` layer. No backend API or database migration is required.


## Phase 16 — Delivery partner workspace

The delivery-partner home screen now uses a task-focused layout with an operational welcome panel, a summary of the partner's weekly availability, API-backed assignment metrics, and a searchable delivery queue.

- Assignment cards organize tracking ID, recipient, destination, booked slot, and customer ETA.
- Partners can publish ETA updates, accept assignments, start deliveries, record failed attempts, and verify delivery using the existing one-time customer code.
- Assignment history remains available on each card.
- The dashboard reads the saved weekly availability and links directly to schedule management.
- Responsive layouts keep assignment actions and recipient verification usable on smaller screens.

The work is presentation-layer only and uses the existing partner APIs. No database migration is required.


## Phase 17 — Operations dashboard and analytics UI

The operations landing page now has a branded control-center layout with API-backed parcel metrics, recent parcel activity, and today's delivery-slot utilization. Quick actions lead to parcel intake, parcel register, warehouse inventory, and performance analytics.

The analytics screen now uses the shared operations visual language for its date filters, KPI cards, daily outcome visualization, and partner performance table. The existing date-range limits, metric definitions, and data sources are unchanged; no illustrative or fabricated KPI values are introduced.


## Phase 18 — Warehouse inventory experience

The warehouse workspace now uses responsive parcel cards instead of a wide inventory table. Operations can search and filter inventory, inspect each parcel's recipient, destination, status, and storage bin, and edit bin assignments inline without browser prompt dialogs.

The eight warehouse summary metrics remain backed by the existing warehouse summary API. Loading, empty, success, and error states are presented in the page, while the backend continues to enforce physical-custody rules for storage-location changes. No API or database migration is required.


## Phase 19 — Parcel register and operations intake UI

The admin parcel register now presents responsive parcel cards with tracking, recipient, destination, registration date, status, and an inline status editor. Search and status filters remain API-backed, and status changes continue to use the server's existing workflow validation.

The operations intake and custody workspace receives a consistent form, inventory-history, and custody-timeline presentation. Receipt, release, and failed-parcel return actions are unchanged; physical custody events remain recorded through the existing APIs.


## Phase 20 — Fleet and scheduling workspaces

The delivery fleet, delivery-slot, and booking pages now share a more consistent operational layout. Partner provisioning forms, capacity summaries, route-plan tables, available slot cards, booking filters, reschedule controls, and cancellation actions receive responsive styling while retaining their existing API behavior.

The route planner remains a recommendation workflow requiring an operations user to apply assignments. Slot capacity, partner assignment capacity, and booking constraints continue to be enforced by the backend.


## Phase 21 — Customer parcel creation and booking flow

The customer parcel-creation page now uses a guided first-step layout with grouped recipient, address, and parcel-reference fields, plus a clear two-step progress indicator. The slot-selection page now presents the parcel summary, current booking, date selection, available capacity, selected-window confirmation, and reschedule/cancellation actions in a more focused flow.

All parcel creation, booking, rescheduling, cancellation, and slot-availability operations continue to use the existing APIs and server-side rules. Loading, no-slot, error, and narrow-screen states are included. No backend API or database migration is required.
