# DronaAI.fit

A web application where **coaches** build personalized workout and diet plans for their **customers**, driven by deterministic health calculators.

Design docs: [High-Level Design](docs/HIGH_LEVEL_DESIGN.md) · [Business Requirements](docs/BUSINESS_REQUIREMENTS.md) · [AI Layer Roadmap](docs/AI_LAYER_ROADMAP.md)

**Setting up for the first time? Follow [SETUP.md](SETUP.md).**

---

## What's built

### Authentication
- Sessions use **httpOnly cookies** that JavaScript can't read: a 15-minute access token and a 30-day refresh token. The refresh token is rotated on every use and only sent to `/auth/*`.
- Every session is stored server-side, so logout takes effect immediately. **Log out on all devices** ends every session. Changing your email or role signs out your other devices.
- Replaying an already-used refresh token is treated as theft and ends that session.
- Passwords hashed with bcrypt; complexity enforced (8+ chars, uppercase, number, special).
- Signing up logs you straight in — the app sends no email.
- Two roles: **customer** and **coach**. Each gets its own profile table.
- First-time users are forced to complete their profile before anything else opens up.

### Consent & safety
- **Share codes** — a coach can only add a customer who gives them their code. There is no way to browse or discover other users.
- **Plan approval** — a coach's plan stays hidden until the customer accepts it, along with a medical disclaimer. The API withholds the plan body, so this isn't just a UI gate.
- **Medical disclaimer** must be accepted at registration.
- **Age limit** of 18–70 enforced at registration (BRD FR-7.6).

### Your data (GDPR, BRD FR-1.9 / FR-1.10)
- **Download my data** — profile, plans, measurements, progress logs, requests, notifications and sign-in sessions as one JSON file.
- **Delete account** — password-confirmed and permanent. The `users` row is deleted and foreign keys cascade to everything the user owns.
- When a coach deletes their account, their customers are released and notified. They keep their plans and request history.
- **Leave coach** — a customer can remove their coach's access at any time. Pending requests are closed and the coach is notified. To change coach, the customer then gives their share code to the new coach.

### Customer experience
- Sign-up collects name, email, password, date of birth, gender and country.
- First login opens a **step-by-step onboarding wizard** (BRD FR-1.5) covering body measurements, activity level, goal, diet (type, budget, restrictions), health (medical conditions, stress, injuries) and workout preferences (experience, gym or home, days per week), followed by a review step.
- Injuries are structured records (BRD 4.1.6): body part, severity, recovery status, optional date and notes.
- Choosing a medical condition shows a medical disclaimer and adds a doctor's-check note to every plan.
- `full_name` is derived from first + last name; **age is derived from date of birth**, so it never goes stale.
- After onboarding, everything can be edited on the profile page. If the customer has a coach, the coach is told about the change (FR-1.8).
- Read-only view of the plans their coach created for them; they can ask for meal swaps, workout changes, report injuries or ask questions through **Requests**.
- **My Stats** (FR-2.11): all 10 calculators on one page, current measurements, and a breakdown of the daily calorie target. Every result has a **"How this is calculated"** panel showing the formula with the customer's own numbers (FR-8.1).
- **Metric or imperial** (FR-2.12): a per-account setting. Weight in kg or lb, height in cm or feet and inches, circumferences in cm or inches, for both entry and display. Data is always stored in metric.

### Progress tracking & weekly reviews
- **Daily check-in**: tick off planned exercises, log other activity, mark each meal as followed / something else / skipped, and record mood, energy, soreness, sleep and weight.
- Dashboard with streak, workout and meal adherence, sleep, and weight and wellness charts. Body measurements have their own trends page.
- **Weekly review** (FR-5.6), created automatically after each week with at least 3 logged days:
  - Summarises adherence, wellness and the weekly weight trend against the rate the goal expects.
  - Suggests a calorie change (FR-5.7) when weight is off track: ±50–200 kcal per review, ±500 kcal in total.
  - Flags losing more than 1 kg/week or gaining more than 0.5 kg/week.
  - Suggests no calorie change when fewer than 70% of meals followed the plan.
  - The coach applies or dismisses the suggestion.
  - Full rules are in [BRD 7.5.1](docs/BUSINESS_REQUIREMENTS.md).

### Coach experience
- Customer dashboard: roster with each customer's key metrics and plan counts.
- Adds customers by entering the share code the customer gave them.
- Customer detail page with the full profile, health and injury details, all health metrics, weekly reviews and plan generation.
- Reviews customer requests, approves meal swaps (adding nutrition for new foods) and edits meals directly.
- **Applies or dismisses** weekly-review calorie suggestions. Applying one changes the customer's calorie target straight away.
- A banner offers **Regenerate** when a plan is older than a profile change or an applied calorie adjustment.
- **Only coaches can generate plans**, and only for customers on their own roster.

### Health metrics (all 10 calculators from BRD section 5)

| Metric | Method |
|---|---|
| BMI | WHO and Asian/Indian classifications; the Asian one is shown first for customers in India |
| BMR | Mifflin-St Jeor |
| TDEE | BMR × activity multiplier |
| Calorie target | Adjusted for each of the 8 BRD goals (e.g. lean bulk +250, aggressive bulk +500, strength +150), plus any coach adjustment from weekly reviews, with safety floors (1500 kcal men / 1200 women) |
| Macros | Protein g/kg by goal (recomp highest at 2.4), fat 25% of calories (20% for endurance; min 0.8 g/kg), carbs remainder |
| Body fat % | US Navy method (waist, neck, + hip for women) |
| Lean body mass | Boer formula |
| Ideal weight | Devine formula |
| Healthy weight range | WHO and Asian BMI bands |
| Heart rate zones | Tanaka max HR, 5 zones |

### Plan generation
Rule-based for now — the AI agent layer replaces this in a later phase.

**Workout plans** are built from the customer's goal and preferences:
- Each of the 8 goals has its own sessions and rep range (e.g. strength 3–5 reps, endurance 15–20).
- Days per week (2–6) trims or repeats the sessions across the week.
- Experience sets the volume: beginners get one set fewer, advanced lifters one more. High stress removes one set.
- Home training swaps gym lifts for bodyweight and resistance-band exercises.
- Exercises that load an injured body part are removed, and the plan lists what was removed and why.

**Diet plans** are a full week: 7 days × 4 sessions (breakfast, lunch, snack, dinner).
- Menus rotate so no two consecutive days repeat.
- Portions scale to each session's calorie share, clamped to stay realistic.
- Respects diet type (vegetarian / eggetarian / non-vegetarian / vegan) and filters out allergens.
- Protein, carbs and fat shown **per item, per session, per day and per week**.
- UI is a nested accordion: click a weekday → see 4 sessions → click a session → see the menu.

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router |
| Backend | Python 3.11, FastAPI, Pydantic v2 |
| Database | PostgreSQL 17 (Supabase free tier), SQLAlchemy 2 async, Alembic |
| Auth | PyJWT + bcrypt |
| Package manager | `uv` (backend), `npm` (frontend) |

---

## Project structure

```
.
├── backend/
│   ├── alembic/versions/       # Database migrations
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py         # Auth dependencies + role guards
│   │   │   └── routes/         # auth, coach, plans, progress, measurements, requests, notifications, health
│   │   ├── core/               # Config, JWT/password helpers, rate limits
│   │   ├── db/                 # Models and async session
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── services/           # Calculators, plan generator, weekly review, sessions, data export
│   └── scripts/                # seed.py, reset_data.py, create_app_role.py
├── frontend/src/
│   ├── components/             # Navbar, plan views, metrics panel, onboarding wizard, unit inputs
│   ├── context/                # Auth and notification state
│   ├── lib/                    # API client (with token refresh), units, profile options
│   └── pages/                  # Landing, auth, profile, stats, plans, progress, coach pages
└── docs/
```

---

## Data model

```
users (auth)
  ├─ 1:1 → coaches
  └─ 1:1 → customers

coaches 1 ─── N customers        # one coach trains many customers
customers 1 ─── N workout_diet_plans, body_measurements, progress_logs,
                  customer_requests, weekly_reviews
```

| Table | Holds |
|---|---|
| `users` | email, password_hash, first_name, last_name, role, unit_system (metric/imperial), disclaimer_accepted_at |
| `auth_sessions` | One row per signed-in device: current/previous refresh token id, expires_at, revoked_at, `user_id` |
| `coaches` | specialization, years_experience, bio |
| `customers` | share_code, date_of_birth, gender, country, height, weight, waist, neck, hip, activity_level, primary_goal, diet_type, budget_level, stress_level, training_experience, training_location, training_days_per_week, dietary_preferences (JSONB), medical_conditions (JSONB), injuries (JSONB: body_part, severity, recovery_status, date_of_injury, notes), profile_updated_at, calorie_adjustment (kcal/day from weekly reviews), `coach_id` |
| `workout_diet_plans` | plan_type, title, content (JSONB), approved_at, `customer_id`, `coach_id` (cleared if the coach deletes their account) |
| `body_measurements` | recorded_at, weight, height, waist, neck, hip — one row per weigh-in or measurement |
| `progress_logs` | One row per customer per day: workout (JSONB), meals (JSONB), mood, energy, soreness, sleep_hours, notes |
| `customer_requests` | request_type (meal/workout/injury/query), status, description, requested/approved meals (JSONB), coach_note |
| `notifications` | message, read_at, optional `request_id` |
| `weekly_reviews` | period_start/end, stats (JSONB), summary, recommended_adjustment, status (open/applied/dismissed/superseded/none) |

---

## API

All routes are prefixed with `/api/v1`. Interactive docs at http://localhost:8000/docs.

| Method | Endpoint | Access |
|---|---|---|
| POST | `/auth/register` | Public — creates the account and starts a session |
| POST | `/auth/login` | Public — starts a session (access + refresh cookies) |
| POST | `/auth/refresh` | Refresh cookie — rotates it and issues a new access cookie |
| POST | `/auth/logout` | Public — ends this session and clears the cookies |
| POST | `/auth/logout-all` | Authenticated — ends every session for the account |
| GET | `/auth/me` | Authenticated |
| PUT | `/auth/me/account` | Authenticated — name, email, role, gender, date of birth, country |
| PUT | `/auth/me/preferences` | Authenticated — metric or imperial units |
| GET | `/auth/me/export` | Authenticated — downloads all of the user's data as JSON |
| POST | `/auth/me/delete` | Authenticated — password-confirmed permanent deletion |
| PUT | `/auth/me/customer-profile` | Customer |
| PUT | `/auth/me/coach-profile` | Coach |
| GET | `/coach/customers` | Coach |
| POST | `/coach/customers/link` | Coach — add by share code |
| GET | `/coach/customers/{id}` | Coach — own customers only; includes weekly reviews |
| POST | `/coach/customers/{id}/remove` | Coach — ends coaching |
| POST | `/coach/customers/{id}/plans` | Coach — own customers only |
| PUT, DELETE | `/coach/plans/{id}/meals` | Coach — edit or remove one meal of a diet plan |
| POST | `/coach/reviews/{id}/apply` | Coach — apply a weekly review's calorie suggestion |
| POST | `/coach/reviews/{id}/dismiss` | Coach — keep the current calorie target |
| GET | `/plans/mine` | Customer — content withheld until approved |
| POST | `/plans/{id}/approve` | Customer |
| GET | `/plans/my-coach` | Customer |
| POST | `/plans/my-coach/leave` | Customer — ends coaching |
| GET, POST | `/measurements` | Customer — measurement history / log a measurement |
| GET | `/progress` | Customer — daily check-ins |
| PUT | `/progress/{date}` | Customer — save a day's check-in |
| POST | `/progress/{date}/exercises` | Customer — tick a planned exercise on or off |
| GET | `/progress/reviews` | Customer — weekly reviews (creates this week's when due) |
| GET, POST | `/requests` | Coach or customer — list / customer raises a request |
| POST | `/requests/meal` | Customer — meal swap request |
| POST | `/requests/{id}/approve-meal`, `/resolve`, `/reject` | Coach |
| GET | `/notifications` | Authenticated |
| POST | `/notifications/{id}/read`, `/notifications/read-all` | Authenticated |
| GET | `/health`, `/ready` | Public |

Authorization is enforced server-side, not just hidden in the UI: customers get `403` on coach endpoints, and coaches get `403` on customers who aren't theirs.

The API accepts the access cookie or an `Authorization: Bearer` header carrying the same access token, so scripts and tests can still call it directly.

---

## Demo accounts

All seeded accounts use the password `Password123!`.

| Email | Role | Notes |
|---|---|---|
| `coach.maria@example.com` | Coach | 3 customers |
| `coach.raj@example.com` | Coach | 1 customer |
| `alex@example.com` | Customer | UK, lose fat, beginner, high stress, lower back injury, no dairy |
| `priya@example.com` | Customer | India, lean bulk, vegetarian, PCOS, peanut allergy |
| `diego@example.com` | Customer | Mexico, lose fat, trains at home, hypertension, recovered knee surgery |
| `lena@example.com` | Customer | India, endurance, vegan, advanced, 5 days a week |
| `sam@example.com` | Customer | No coach, sign-up details only — goes through the onboarding wizard |

Each seeded customer gets a workout plan (pre-approved) and a diet plan (left pending, so you can
see the approval step). Share codes are printed when you run the seed script.

---

## Production hardening

| Measure | Status |
|---|---|
| httpOnly cookie sessions | Done |
| Server-side session revocation, short-lived access tokens, rotating refresh tokens | Done |
| Password complexity | Done |
| Rate limiting (10 logins/min, 5 registrations/hour) | Done |
| Consent required before a coach sees customer data | Done |
| Customers can withdraw coach access themselves | Done |
| Data export and account deletion (GDPR) | Done |
| Plan contents withheld until the customer approves | Done |
| Medical disclaimer + 18–70 age limit | Done |
| Security headers (nosniff, DENY framing, HSTS in prod) | Done |
| API docs disabled in production | Done |
| Least-privilege database role | Done — run `python -m scripts.create_app_role`. It can delete only from `users`, for account deletion |
| Test suite (auth, sessions, account deletion, authorization, calculators, plan safety, onboarding, weekly reviews, production settings) | Done |
| CI on push and PR (tests, migrations on real Postgres, frontend build) | Done |
| Unsafe production settings stop the deploy | Done |

Still outstanding, and worth doing before a large launch:

| Area | Outstanding |
|---|---|
| Passwords | No password change or reset flow (BRD FR-1.4) |
| Guardrail audit | Interventions aren't logged (BRD FR-7.7) |
| Observability | No structured logging or error tracking (Sentry) |
| Scale | Coach customer lists are unpaginated; revoked/expired `auth_sessions` rows aren't pruned |

See [SETUP.md](SETUP.md#deploying) for the deployment guide.

---

## Everyday commands

```powershell
# Backend (from backend/)
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --reload-dir app
pytest

python -m scripts.seed          # insert demo data (skips existing accounts)
python -m scripts.reset_data    # wipe all users, coaches, customers and plans

alembic revision --autogenerate -m "message"   # after changing a model
alembic upgrade head                            # apply migrations

# Frontend (from frontend/)
npm run dev
npm run typecheck
npm run build
```

---

## Roadmap

Phases 1–3 of the HLD are partly delivered (see [BRD section 14](docs/BUSINESS_REQUIREMENTS.md) for the status of each requirement and [leftover_work.md](leftover_work.md) for what's left). Still to come:

- AI agent layer (LangGraph) replacing the rule-based generators
- Chat assistant (UI shell exists, not yet wired to a model)
- Check-in and weigh-in reminders (FR-5.9) and workout progression from logged performance (FR-5.8)
- Indian regional cuisine support (BRD section 6)
