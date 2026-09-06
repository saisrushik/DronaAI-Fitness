# DronaAI.fit

A web application where **coaches** build personalized workout and diet plans for their **customers**, driven by deterministic health calculators.

Design docs: [High-Level Design](docs/HIGH_LEVEL_DESIGN.md) · [Business Requirements](docs/BUSINESS_REQUIREMENTS.md)

**Setting up for the first time? Follow [SETUP.md](SETUP.md).**

---

## What's built

### Authentication
- Session stored in an **httpOnly cookie** — not readable by JavaScript.
- Passwords hashed with bcrypt; complexity enforced (8+ chars, uppercase, number, special).
- **Email verification** required before first login.
- **Password reset** by emailed link. Tokens are purpose-scoped, so a reset link can't be used as a session.
- Logout clears the cookie server-side.
- Two roles: **customer** and **coach**. Each gets its own profile table.
- First-time users are forced to complete their profile before anything else opens up.

### Consent & safety
- **Share codes** — a coach can only add a customer who gives them their code. There is no way to browse or discover other users.
- **Plan approval** — a coach's plan stays hidden until the customer accepts it, along with a medical disclaimer. The API withholds the plan body, so this isn't just a UI gate.
- **Medical disclaimer** must be accepted at registration.
- **Age limit** of 18–70 enforced at registration (BRD FR-7.6).

### Customer experience
- Sign-up collects first name, last name, email, date of birth, gender, height, weight, waist, neck and hip.
- `full_name` is derived from first + last name; **age is derived from date of birth**, so it never goes stale.
- Profile page for goals, activity level, diet type, allergies and injury history.
- Read-only view of the plans their coach created for them.

### Coach experience
- Customer dashboard: roster with each customer's key metrics and plan counts.
- Adds customers by entering the share code the customer gave them.
- Customer detail page with the full profile, all health metrics, and plan generation.
- **Only coaches can generate plans**, and only for customers on their own roster.

### Health metrics (all 10 calculators from BRD section 5)

| Metric | Method |
|---|---|
| BMI | Shown with both WHO and Asian/Indian classifications |
| BMR | Mifflin-St Jeor |
| TDEE | BMR × activity multiplier |
| Calorie target | Goal-adjusted, with safety floors (1500 kcal men / 1200 women) |
| Macros | Protein g/kg by goal, fat 25% of calories (min 0.8 g/kg), carbs remainder |
| Body fat % | US Navy method (waist, neck, + hip for women) |
| Lean body mass | Boer formula |
| Ideal weight | Devine formula |
| Healthy weight range | WHO and Asian BMI bands |
| Heart rate zones | Tanaka max HR, 5 zones |

### Plan generation
Rule-based for now — the AI agent layer replaces this in a later phase.

**Workout plans** pick a split from the customer's goal and **remove exercises that would aggravate declared injuries** (e.g. knee surgery removes squats and lunges), listing what was removed and why.

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
│   │   │   └── routes/         # auth, coach, plans, health
│   │   ├── core/               # Config and JWT/password helpers
│   │   ├── db/                 # Models and async session
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── services/           # Calculators, food catalog, plan generator
│   └── scripts/                # seed.py, reset_data.py
├── frontend/src/
│   ├── components/             # Navbar, Layout, plan views, metrics panel
│   ├── context/AuthContext.tsx # Auth state + token handling
│   ├── lib/api.ts              # Fetch wrapper that attaches the JWT
│   └── pages/                  # Landing, auth, profile, plans, coach pages
└── docs/
```

---

## Data model

```
users (auth)
  ├─ 1:1 → coaches
  └─ 1:1 → customers

coaches 1 ─── N customers        # one coach trains many customers
customers 1 ─── N workout_diet_plans
```

| Table | Holds |
|---|---|
| `users` | email, password_hash, first_name, last_name, role, email_verified, disclaimer_accepted_at |
| `coaches` | specialization, years_experience, bio |
| `customers` | share_code, date_of_birth, gender, height, weight, waist, neck, hip, activity_level, primary_goal, diet_type, dietary_preferences (JSONB), health_injury_history (JSONB), `coach_id` |
| `workout_diet_plans` | plan_type, title, content (JSONB), approved_at, `customer_id`, `coach_id` |

---

## API

All routes are prefixed with `/api/v1`. Interactive docs at http://localhost:8000/docs.

| Method | Endpoint | Access |
|---|---|---|
| POST | `/auth/register` | Public |
| POST | `/auth/verify-email` | Public |
| POST | `/auth/resend-verification` | Public |
| POST | `/auth/login` | Public — sets the session cookie |
| POST | `/auth/logout` | Public — clears the cookie |
| POST | `/auth/forgot-password` | Public |
| POST | `/auth/reset-password` | Public |
| GET | `/auth/me` | Authenticated |
| PUT | `/auth/me/customer-profile` | Customer |
| PUT | `/auth/me/coach-profile` | Coach |
| GET | `/coach/customers` | Coach |
| POST | `/coach/customers/link` | Coach — add by share code |
| GET | `/coach/customers/{id}` | Coach — own customers only |
| POST | `/coach/customers/{id}/plans` | Coach — own customers only |
| GET | `/plans/mine` | Customer — content withheld until approved |
| POST | `/plans/{id}/approve` | Customer |
| GET | `/plans/my-coach` | Customer |
| GET | `/health`, `/ready` | Public |

Authorization is enforced server-side, not just hidden in the UI: customers get `403` on coach endpoints, and coaches get `403` on customers who aren't theirs.

`/auth/*` accepts the session cookie or an `Authorization: Bearer` header, so scripts and tests can still call the API directly.

---

## Demo accounts

All seeded accounts use the password `Password123!` and are pre-verified.

| Email | Role | Notes |
|---|---|---|
| `coach.maria@example.com` | Coach | 3 customers |
| `coach.raj@example.com` | Coach | 1 customer |
| `alex@example.com` | Customer | Non-vegetarian, no dairy, lower back pain |
| `priya@example.com` | Customer | Vegetarian, peanut allergy |
| `diego@example.com` | Customer | Eggetarian, knee surgery |
| `lena@example.com` | Customer | Vegan, endurance goal |
| `sam@example.com` | Customer | No coach, incomplete profile — tests the first-login flow |

Each seeded customer gets a workout plan (pre-approved) and a diet plan (left pending, so you can
see the approval step). Share codes are printed when you run the seed script.

---

## Production hardening

| Measure | Status |
|---|---|
| httpOnly cookie sessions | Done |
| Password complexity | Done |
| Email verification + password reset | Done |
| Rate limiting (10 logins/min, 5 registrations/hour) | Done |
| Consent required before a coach sees customer data | Done |
| Plan contents withheld until the customer approves | Done |
| Medical disclaimer + 18–70 age limit | Done |
| Security headers (nosniff, DENY framing, HSTS in prod) | Done |
| API docs disabled in production | Done |
| Least-privilege database role | Done — run `python -m scripts.create_app_role` |
| Test suite (46 tests: auth, authorization, calculators, plan safety) | Done |
| CI on push and PR | Done |

Still outstanding, and worth doing before a large launch:

| Area | Outstanding |
|---|---|
| Session revocation | Sessions stay valid until they expire; no server-side denylist |
| GDPR | No data export or account deletion (BRD FR-1.9, FR-1.10) |
| Guardrail audit | Interventions aren't logged (BRD FR-7.7) |
| Observability | No structured logging or error tracking (Sentry) |
| Scale | Coach customer lists are unpaginated |

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

Phases 1–3 of the HLD are partly delivered. Still to come:

- AI agent layer (LangGraph) replacing the rule-based generators
- Chat assistant (UI shell exists, not yet wired to a model)
- Progress logging and weekly plan adaptation
- Indian regional cuisine support (BRD section 6)
- Refresh tokens, email verification, password reset
