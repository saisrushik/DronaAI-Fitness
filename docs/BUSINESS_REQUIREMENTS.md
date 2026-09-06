# Fitness Assistant — Business Requirements Document (BRD)

**Version:** 1.0
**Date:** 2026-09-04
**Status:** Draft
**Related Documents:** [High-Level Design](HIGH_LEVEL_DESIGN.md)

---

## 1. Purpose & Scope

This document captures the detailed business requirements for the **Fitness Assistant** system. It expands on the High-Level Design by defining:

- Business goals and success criteria
- Complete user profile attributes
- Fitness and nutrition calculators
- Indian food adoption requirements
- Detailed functional requirements

The HLD is a living reference; this BRD is the source of truth for **what** the system must do from a business perspective.

### 1.1 Scope (In Scope for MVP)
- Web application (React) with backend API (FastAPI)
- User onboarding, profile management, and preference collection
- Deterministic fitness calculators (BMI, BMR, TDEE, macros, body fat, ideal weight, lean body mass, heart rate zones)
- AI-generated personalized workout and diet plans
- Indian regional food adaptation for diet plans
- Progress tracking and plan adaptation
- AI chat assistant for user questions

### 1.2 Out of Scope (MVP)
- Native mobile applications (planned for Phase 5)
- Wearable device integration
- Clinical/medical-grade recommendations for users with chronic conditions (diabetes, cardiac issues, pregnancy)
- Social/community features
- Payment/subscription features

---

## 2. Business Goals

### 2.1 Primary Business Goals

| ID | Goal | Description | Success Metric |
|---|---|---|---|
| BG-1 | Personalization | Every plan must be uniquely tailored to the individual's profile, goals, and constraints. | ≥ 90% of plans use user-specific parameters (no generic defaults). |
| BG-2 | Cultural Relevance | Diet plans must adapt to user's regional cuisine, especially Indian foods across regions. | ≥ 80% of diet plan items are region-appropriate for Indian users. |
| BG-3 | Safety First | No plan should recommend unsafe practices (extreme deficits, injury-aggravating exercises). | 100% of unsafe recommendations blocked by guardrails. |
| BG-4 | Explainability | Every recommendation includes the "why" behind it. | 100% of plans include rationale/reasoning text. |
| BG-5 | Adaptivity | Plans adapt based on user progress and feedback. | Weekly plan review triggered automatically. |
| BG-6 | Accessibility | The MVP should be free to use during the beta phase. | Zero user-facing cost; infrastructure on free tiers. |
| BG-7 | Trust | Users should feel confident acting on AI recommendations. | ≥ 4.2/5 average trust rating in post-plan survey. |

### 2.2 Secondary Business Goals

| ID | Goal | Description |
|---|---|---|
| BG-8 | Retention | Users return to log progress and adjust plans regularly. |
| BG-9 | Data-driven Learning | Aggregate anonymized data to improve AI recommendations over time. |
| BG-10 | Cost Efficiency | LLM cost per active user stays under $0.10/month. |

---

## 3. Target Users & Personas

### 3.1 Primary Personas

**Persona 1: The Beginner (Ravi, 28, Male)**
- Sedentary desk job, wants to lose 10 kg.
- No gym experience; prefers home workouts.
- Vegetarian, South Indian.
- Needs guidance on exercise form and portion sizes.

**Persona 2: The Recomposer (Priya, 32, Female)**
- Moderately active, wants to lose fat and gain muscle simultaneously.
- Trains 3–4 times/week at a gym.
- Eggetarian, North Indian.
- Wants macro tracking and progressive workout plans.

**Persona 3: The Lean Bulker (Arjun, 24, Male)**
- Skinny, wants to gain 8 kg of muscle mass.
- Trains 5 times/week.
- Non-vegetarian, prefers whole foods.
- Needs calorie surplus plan and progressive overload workouts.

**Persona 4: The Maintainer (Sneha, 38, Female)**
- Achieved goal weight, wants to maintain fitness.
- Runs 3 times/week + yoga.
- Vegan.
- Needs balanced maintenance plan.

---

## 4. User Profile Attributes

### 4.1 Complete Profile Schema

#### 4.1.1 Demographic Attributes
| Attribute | Type | Constraints | Required | Notes |
|---|---|---|---|---|
| `first_name` | string | 1–50 chars | Yes | For personalization |
| `last_name` | string | 1–50 chars | No | Optional |
| `email` | string | Valid email format, unique | Yes | Used for login |
| `date_of_birth` | date | Age must be 18–70 | Yes | Age derived from this |
| `gender` | enum | `male`, `female` | Yes | Affects BMR/calorie calculations |
| `country` | string | ISO country code | Yes | Default: `IN` |

#### 4.1.2 Physiological Attributes
| Attribute | Type | Constraints | Required | Notes |
|---|---|---|---|---|
| `height_cm` | float | 100–250 | Yes | Support cm and ft/in input |
| `weight_kg` | float | 30–250 | Yes | Support kg and lbs input |
| `waist_cm` | float | 40–200 | No | For body fat estimation (Navy method) |
| `neck_cm` | float | 20–60 | No | For body fat estimation (Navy method) |
| `hip_cm` | float | 40–200 | No | Female only, for Navy method |

#### 4.1.3 Activity Level
| Value | Multiplier | Description |
|---|---|---|
| `sedentary` | 1.2 | Little to no exercise, desk job |
| `lightly_active` | 1.375 | Light exercise 1–3 days/week |
| `moderately_active` | 1.55 | Moderate exercise 3–5 days/week |
| `very_active` | 1.725 | Hard exercise 6–7 days/week |
| `extremely_active` | 1.9 | Very hard exercise + physical job or 2× training/day |

#### 4.1.4 Fitness Goals
| Goal Type | Description | Calorie Target |
|---|---|---|
| `lose_fat` | Reduce body fat | TDEE − 300 to 500 kcal |
| `lean_bulk` | Gain muscle with minimal fat | TDEE + 200 to 300 kcal |
| `aggressive_bulk` | Maximum muscle gain (higher fat gain acceptable) | TDEE + 400 to 500 kcal |
| `maintain` | Maintain current weight and composition | TDEE ± 100 kcal |
| `recomp` | Recomposition — lose fat and gain muscle | TDEE ± 100 kcal (high protein) |
| `general_fitness` | Overall health improvement | TDEE (balanced) |
| `endurance` | Improve cardiovascular fitness | TDEE + carb emphasis |
| `strength` | Maximal strength gains | TDEE + 100 to 200 kcal |

#### 4.1.5 Dietary Preferences
| Attribute | Type | Values | Notes |
|---|---|---|---|
| `diet_type` | enum | `vegetarian`, `non_vegetarian`, `eggetarian`, `vegan` | Primary diet |
| `budget_level` | enum | `low`, `medium`, `high` | Ingredient cost consideration |

#### 4.1.6 Health & Injury History
| Attribute | Type | Description |
|---|---|---|
| `injuries` | array of objects | List of injuries with details |
| `injuries[].body_part` | enum | `knee`, `lower_back`, `upper_back`, `shoulder`, `elbow`, `wrist`, `hip`, `ankle`, `neck`, `other` |
| `injuries[].severity` | enum | `mild`, `moderate`, `severe`, `chronic` |
| `injuries[].date_of_injury` | date | Optional |
| `injuries[].recovery_status` | enum | `recovered`, `recovering`, `active_pain` |
| `injuries[].notes` | text | Free text |
| `medical_conditions` | array | e.g., `hypertension`, `pcos`, `thyroid`, `asthma` — triggers medical disclaimer |
| `stress_level` | enum | `low`, `medium`, `high` | Affects training volume recommendations |

---

## 5. Fitness & Nutrition Calculators

All calculators are **deterministic** (no LLM involvement). They serve as ground-truth inputs to the AI planning agents.

### 5.1 BMI (Body Mass Index)

**Formula:**
$$BMI = \frac{weight_{kg}}{(height_m)^2}$$

**Classification (WHO + Asian-specific for Indian users):**
| Category | WHO (kg/m²) | Asian/Indian (kg/m²) |
|---|---|---|
| Underweight | < 18.5 | < 18.5 |
| Normal | 18.5–24.9 | 18.5–22.9 |
| Overweight | 25.0–29.9 | 23.0–24.9 |
| Obese Class I | 30.0–34.9 | 25.0–29.9 |
| Obese Class II | 35.0–39.9 | ≥ 30.0 |
| Obese Class III | ≥ 40.0 | — |

**Business rule:** For users in India, use Asian classification by default and show both.

### 5.2 BMR (Basal Metabolic Rate)

**Formula (Mifflin-St Jeor):**
$$BMR_{male} = 10w + 6.25h - 5a + 5$$
$$BMR_{female} = 10w + 6.25h - 5a - 161$$

Where $w$ = weight (kg), $h$ = height (cm), $a$ = age (years).

### 5.3 TDEE (Total Daily Energy Expenditure)

**Formula:**
$$TDEE = BMR \times activity\_multiplier$$

Uses the activity multipliers from section 4.1.3.

### 5.4 Calorie Target (Goal-Based)

| Goal | Calorie Adjustment |
|---|---|
| `lose_fat` | TDEE − 500 (aggressive) or TDEE − 300 (moderate) |
| `lean_bulk` | TDEE + 250 |
| `aggressive_bulk` | TDEE + 500 |
| `maintain` | TDEE |
| `recomp` | TDEE (with high protein) |
| `general_fitness` | TDEE |

**Safety guardrails:**
- Never recommend below **1200 kcal** for women or **1500 kcal** for men.
- Never recommend more than **1 kg/week loss** or **0.5 kg/week gain**.
- Show medical disclaimer if calculated deficit exceeds 750 kcal/day.

### 5.5 Macronutrient Split

**Protein target (goal-based):**
| Goal | Protein (g/kg body weight) |
|---|---|
| `lose_fat` | 2.0–2.4 |
| `lean_bulk` / `aggressive_bulk` | 1.6–2.2 |
| `maintain` / `general_fitness` | 1.4–1.8 |
| `recomp` | 2.2–2.6 |
| `endurance` | 1.4–1.7 |

**Fat target:** 20–35% of total calories (minimum 0.8 g/kg body weight).

**Carbs:** Remaining calories after protein and fat.

**Formulas:**
$$Protein_{kcal} = Protein_g \times 4$$
$$Fat_{kcal} = Fat_g \times 9$$
$$Carbs_{kcal} = TargetCalories - Protein_{kcal} - Fat_{kcal}$$
$$Carbs_g = \frac{Carbs_{kcal}}{4}$$

### 5.6 Body Fat Percentage

**Formula (US Navy Method):**

For men:
$$BF\% = 495 / (1.0324 - 0.19077 \log_{10}(waist - neck) + 0.15456 \log_{10}(height)) - 450$$

For women:
$$BF\% = 495 / (1.29579 - 0.35004 \log_{10}(waist + hip - neck) + 0.22100 \log_{10}(height)) - 450$$

All measurements in cm. Requires `waist_cm`, `neck_cm` (and `hip_cm` for women).

**Body Fat Classification:**
| Category | Male | Female |
|---|---|---|
| Essential fat | 2–5% | 10–13% |
| Athletes | 6–13% | 14–20% |
| Fitness | 14–17% | 21–24% |
| Average | 18–24% | 25–31% |
| Obese | ≥ 25% | ≥ 32% |

### 5.7 Lean Body Mass (LBM)

**Formula (Boer):**
$$LBM_{male} = 0.407 \times weight + 0.267 \times height - 19.2$$
$$LBM_{female} = 0.252 \times weight + 0.473 \times height - 48.3$$

Weight in kg, height in cm.

### 5.8 Ideal Body Weight (IBW)

**Formula (Devine):**
$$IBW_{male} = 50 + 2.3 \times (height_{inches} - 60)$$
$$IBW_{female} = 45.5 + 2.3 \times (height_{inches} - 60)$$

### 5.9 Healthy Weight Range

Based on BMI 18.5–22.9 (Asian) or 18.5–24.9 (WHO):
$$WeightMin = BMI_{min} \times height_m^2$$
$$WeightMax = BMI_{max} \times height_m^2$$

Show both ranges for Indian users.

### 5.10 Heart Rate Zones

**Formula (Tanaka):**
$$HR_{max} = 208 - 0.7 \times age$$

**Zones (% of HR max):**
| Zone | Name | % of HR max | Purpose |
|---|---|---|---|
| Zone 1 | Very Light (Recovery) | 50–60% | Active recovery, warm-up |
| Zone 2 | Light (Aerobic base) | 60–70% | Fat burn, endurance base |
| Zone 3 | Moderate (Aerobic) | 70–80% | Aerobic fitness, cardiovascular |
| Zone 4 | Hard (Threshold) | 80–90% | Lactate threshold, performance |
| Zone 5 | Maximum (Anaerobic) | 90–100% | VO2 max, sprint intervals |

### 5.11 Calculator Summary Table

| Calculator | Inputs Required | Output |
|---|---|---|
| BMI | height, weight | BMI value + classification |
| BMR | age, gender, height, weight | Calories/day at rest |
| TDEE | BMR, activity_level | Daily calorie need |
| Calorie Target | TDEE, goal | Target daily calories |
| Macros | target_calories, weight, goal | Protein/fat/carb grams |
| Body Fat % | height, gender, waist, neck (+ hip for women) | BF% + classification |
| LBM | weight, height, gender | LBM in kg |
| Ideal Weight | height, gender | IBW |
| Healthy Weight | height | Weight range (WHO + Asian) |
| Heart Rate Zones | age | Zone HR ranges |

---

## 6. Indian Food Adoption

### 6.1 Rationale

Generic fitness apps recommend Western foods (oatmeal, quinoa, kale) that many Indian users find unfamiliar, expensive, or culturally inappropriate. The Fitness Assistant must generate diet plans that:
- Use familiar Indian ingredients and dishes.
- Respect regional cuisine preferences.
- Match Indian cooking practices (masala, oil usage, roti/rice staples).
- Provide portion sizes in Indian units (katori, cup, roti count, glass).

### 6.2 Regional Cuisine Support

| Region | Staple Foods | Example Dishes |
|---|---|---|
| **North India** | Wheat (roti/paratha), dal, paneer, dahi | Rajma chawal, chole, paneer bhurji, dal makhani |
| **South India** | Rice, coconut, lentils, tamarind | Idli, dosa, sambar, rasam, curd rice, upma |
| **West India** | Bajra, jowar, groundnut, jaggery | Dhokla, thepla, pav bhaji, misal, undhiyu |
| **East India** | Rice, fish, mustard oil, greens | Fish curry, luchi, aloo posto, macher jhol |
| **Northeast India** | Rice, bamboo shoots, fermented foods | Momos, thukpa, bamboo shoot curry |
| **Punjab** | Wheat, dairy, ghee | Sarson da saag, makki roti, lassi, chole bhature |
| **Gujarat** | Bajra, jowar, jaggery, ghee | Khaman, dhokla, thepla, undhiyu |
| **Maharashtra** | Rice, wheat, groundnut | Puran poli, misal pav, vada pav, poha |
| **Kerala** | Rice, coconut, seafood | Puttu, appam, avial, meen curry |
| **Bengal** | Rice, fish, mustard | Machher jhol, shukto, mishti doi |
| **Tamil Nadu** | Rice, tamarind, coconut | Idli, dosa, pongal, kootu, sambar |
| **Andhra/Telangana** | Rice, chilli, tamarind | Pesarattu, gongura pachadi, hyderabadi biryani |
| **Karnataka** | Ragi, rice, coconut | Ragi mudde, bisi bele bath, neer dosa |

### 6.3 Diet Plan Requirements for Indian Foods

| Requirement | Description |
|---|---|
| **Ingredient localization** | Use Indian ingredient names (e.g., "besan" not "chickpea flour"). |
| **Portion units** | Use katori (150ml), cup (200ml), roti/chapati count, glass (250ml), plate. |
| **Common substitutes** | Suggest local equivalents (e.g., paneer instead of tofu, curd instead of Greek yogurt, ragi instead of quinoa). |
| **Cooking method awareness** | Account for oil in tempering, ghee in cooking, deep-frying in traditional dishes. |
| **Meal timing** | Support typical Indian meal patterns (breakfast, lunch, evening snack + chai, dinner). |
| **Fasting practices** | Support Ekadashi, Karva Chauth, Ramadan (Sehri/Iftar), Navratri, intermittent fasting. |
| **Religious restrictions** | Support Jain (no root vegetables, no onion/garlic), Hindu (no beef), Muslim (halal, no pork), Sikh (no beef), Christian (Lent). |
| **Seasonal variations** | Prefer seasonal produce (mangoes in summer, sarson in winter). |

### 6.4 Indian Nutrition Database Requirements

- Local ingredient nutrition data sourced from **IFCT 2017 (Indian Food Composition Tables)** by NIN.
- Common dish macros pre-computed for 200+ popular Indian dishes.
- Support for household measurements (1 katori dal ≈ 150ml ≈ 150 kcal for typical toor dal).
- Regional variation flags (e.g., North Indian rajma vs South Indian rasam nutrition).

### 6.5 Sample Diet Plan Format for Indian User

```
Breakfast (7:30 AM) — 450 kcal
  • 2 medium idli (150g) — 156 kcal, 3g protein
  • 1 katori sambar (150ml) — 100 kcal, 6g protein
  • 2 tbsp coconut chutney — 60 kcal, 1g protein
  • 1 cup filter coffee with 1 tsp sugar — 80 kcal
  Rationale: Fermented idli aids digestion; sambar provides protein from lentils.

Mid-morning snack (10:30 AM) — 150 kcal
  • 1 medium banana — 90 kcal, 1g protein
  • 8 almonds — 60 kcal, 2g protein

Lunch (1:00 PM) — 650 kcal
  • 3 medium chapati (90g) — 250 kcal, 8g protein
  • 1 katori dal tadka (150ml) — 150 kcal, 9g protein
  • 1 katori mixed vegetable sabzi (150g) — 100 kcal, 3g protein
  • 1 katori curd (150ml) — 100 kcal, 6g protein
  • Salad + 1 tsp ghee for tempering
  Rationale: Balanced macro plate with plant-based proteins and complex carbs.

...
```

---

## 7. Detailed Functional Requirements

### 7.1 User Onboarding & Profile

| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | User can register with email + password (min 8 chars, 1 uppercase, 1 number, 1 special char). | Must |
| FR-1.2 | User can verify email via a link sent post-registration. | Should |
| FR-1.3 | User can log in and receive JWT access + refresh tokens. | Must |
| FR-1.4 | User can reset password via email link. | Must |
| FR-1.5 | New user completes multi-step onboarding: demographics → physiology → activity → goals → dietary prefs → injuries → workout prefs. | Must |
| FR-1.6 | User can update any profile field at any time. | Must |
| FR-1.7 | Profile updates trigger recalculation of BMR/TDEE/macros. | Must |
| FR-1.8 | Profile updates trigger optional re-generation of workout/diet plan. | Should |
| FR-1.9 | User can export their full profile + history as JSON (GDPR). | Should |
| FR-1.10 | User can delete their account and all data (GDPR). | Must |

### 7.2 Calculators

| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | System calculates BMI on profile save; shows WHO + Asian classifications for Indian users. | Must |
| FR-2.2 | System calculates BMR using Mifflin-St Jeor. | Must |
| FR-2.3 | System calculates TDEE using activity multiplier. | Must |
| FR-2.4 | System calculates calorie target based on goal with safety floors (1200/1500 kcal). | Must |
| FR-2.5 | System calculates macros using goal-based protein target and 20–35% fat range. | Must |
| FR-2.6 | System estimates body fat % using US Navy method (waist, neck, height, + hip for women). | Should |
| FR-2.7 | System calculates LBM using Boer formula. | Should |
| FR-2.8 | System calculates ideal body weight using Devine formula. | Should |
| FR-2.9 | System shows healthy weight range for user's height (WHO + Asian BMI ranges). | Must |
| FR-2.10 | System calculates 5 heart rate zones using Tanaka max HR formula (% of HR max). | Should |
| FR-2.11 | All calculator outputs are shown on a dedicated "My Stats" dashboard page. | Must |
| FR-2.12 | Calculator results include unit conversions (kg ↔ lbs, cm ↔ ft/in). | Must |

### 7.3 Workout Plan Generation

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | System generates workout plan based on: goal, experience, injuries. | Must |
| FR-3.2 | Plan includes: split type (PPL, Upper/Lower, Full Body, etc.), exercises, sets, reps, rest periods. | Must |
| FR-3.3 | Plan avoids exercises that aggravate declared injuries. | Must (safety) |
| FR-3.4 | Plan includes warm-up, main session, and cool-down/stretching. | Must |
| FR-3.5 | Plan includes progression guidance (add weight, reps, or sets weekly). | Should |
| FR-3.6 | Plan includes textual rationale explaining choices. | Must |
| FR-3.7 | User can regenerate the plan with different preferences. | Must |
| FR-3.8 | User can view exercise-level details (form cues, video link, muscle group). | Should |
| FR-3.9 | System supports plan types: strength, hypertrophy, HIIT, yoga, cardio, calisthenics, functional. | Must |
| FR-3.10 | Plan is versioned; history preserved for audit. | Must |

### 7.4 Diet Plan Generation

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | System generates diet plan matching target calories and macros. | Must |
| FR-4.2 | Plan respects diet type (veg/non-veg/vegan/etc.). | Must (safety) |
| FR-4.3 | Plan adapts to Indian region and cuisine preferences. | Must |
| FR-4.4 | Plan uses Indian household portion units (katori, roti, cup, glass). | Must |
| FR-4.5 | Plan includes breakfast, lunch, and dinner. | Must |
| FR-4.6 | Each meal includes calorie + macro breakdown per item. | Must |
| FR-4.7 | Plan includes hydration recommendations (glasses of water). | Should |
| FR-4.8 | Plan includes textual rationale for meal choices. | Must |
| FR-4.9 | User can request substitutions ("give me a Bengali version of lunch"). | Should |
| FR-4.10 | Plan avoids suggested calorie totals below safety floors. | Must (safety) |
| FR-4.12 | Plan is versioned; history preserved. | Must |

### 7.5 Progress Tracking & Adaptation

| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | User can log daily weight. | Must |
| FR-5.2 | User can log completed workouts (which exercises, sets, weights, reps). | Must |
| FR-5.3 | User can log meals eaten (from plan or custom). | Must |
| FR-5.4 | User can log optional metrics: mood, sleep, energy, soreness. | Should |
| FR-5.5 | System shows progress dashboard: weight chart, adherence %, streak. | Must |
| FR-5.6 | System triggers weekly plan review after 7 days of logs. | Must |
| FR-5.7 | System adapts calorie target if actual weight change deviates from expected. | Should |
| FR-5.8 | System adapts workout progression based on logged performance. | Should |
| FR-5.9 | System sends optional reminder notifications (email or in-app). | Should |

### 7.6 AI Chat Assistant

| ID | Requirement | Priority |
|---|---|---|
| FR-6.1 | User can chat with the AI assistant in natural language. | Must |
| FR-6.2 | Assistant has access to user's profile, current plans, and recent progress. | Must |
| FR-6.3 | Assistant can answer: exercise form questions, food substitutions, motivation, plan modifications. | Must |
| FR-6.4 | Assistant refuses medical diagnosis questions and redirects to a doctor. | Must (safety) |
| FR-6.5 | Chat history is stored and searchable. | Should |
| FR-6.6 | Assistant supports multiple languages (English, Hindi initially). | Should |

### 7.7 Safety & Guardrails

| ID | Requirement | Priority |
|---|---|---|
| FR-7.1 | Guardrails block any plan with calories below safety floor. | Must |
| FR-7.2 | Guardrails block workout plans containing exercises listed as unsafe for user's injuries. | Must |
| FR-7.3 | System shows medical disclaimer during onboarding and on every generated plan. | Must |
| FR-7.4 | System requires acknowledgement of disclaimer before first plan generation. | Must |
| FR-7.5 | System auto-enables "safe mode" (reduced intensity, no aggressive deficit) for declared chronic conditions. | Must |
| FR-7.6 | System refuses to generate plans for users under 18 or over 70 (MVP). | Must |
| FR-7.7 | System logs all guardrail interventions for audit. | Must |

### 7.8 Explainability

| ID | Requirement | Priority |
|---|---|---|
| FR-8.1 | Every calculator result includes a "How this is calculated" tooltip. | Must |
| FR-8.2 | Every workout plan includes rationale per exercise category. | Must |
| FR-8.3 | Every diet plan includes rationale per meal. | Must |
| FR-8.4 | User can view "Why this plan?" explanation on plan detail page. | Must |

---

## 8. Assumptions

- Users provide truthful profile data. The system trusts user input for MVP.
- Users are physically capable of following a general fitness plan unless they declare an injury or condition.
- Indian food nutrition data (IFCT 2017) is sufficient for MVP; will expand later.
- Users have basic English literacy; multilingual support is progressive.
- Users have access to a smartphone or laptop with internet.

---

## 9. Constraints

- **Legal:** No medical claims; system is fitness guidance only, not medical advice.
- **Age:** MVP restricted to users aged 18–70.
- **Language:** English UI first; other Indian languages added progressively.
- **Region:** MVP optimized for Indian users; global support in later phases.
- **Cost:** Infrastructure must run on free tiers during MVP.

---

## 10. Dependencies

| Dependency | Purpose |
|---|---|
| IFCT 2017 (NIN) | Indian food nutrition database |
| Exercise reference library (open source) | Exercise database with form cues |
| LLM providers (Groq, OpenAI, Azure, Ollama) | AI agent execution |
| MLflow | Experiment tracking |
| PostgreSQL | Primary data store |
| Vercel, Render, Supabase, etc. | Free-tier hosting |

---

## 11. Acceptance Criteria (High-Level for MVP Release)

- [ ] User can register, log in, complete onboarding, view their calculated stats.
- [ ] All 10 calculators (BMI, BMR, TDEE, calorie target, macros, body fat, LBM, ideal weight, healthy weight, heart rate zones) produce correct values verified against manual calculations for 20 test profiles.
- [ ] AI generates workout plans matching user preferences and avoiding injury-aggravating exercises in 100% of test cases.
- [ ] AI generates diet plans in Indian format for Indian users in 100% of test cases.
- [ ] Guardrails block unsafe calorie targets in 100% of test cases.
- [ ] User can log progress and view a dashboard.
- [ ] AI chat assistant responds appropriately to 20 predefined test queries.
- [ ] System deployed on free-tier hosting and accessible via public URL.
- [ ] All P0/Must-have requirements implemented and tested.

---

## 12. Open Questions

| # | Question | Owner | Status |
|---|---|---|---|
| Q-1 | Should we integrate with Google Fit / Apple Health in MVP? | Product | Open |
| Q-2 | Should the AI chat assistant remember conversations across sessions? | Product | Open |
| Q-3 | What is the primary language for launch — English only or English + Hindi? | Product | Open |
| Q-4 | Should we offer a "coach review" feature where a human reviews the AI plan? | Product | Open |
| Q-5 | Are we sourcing exercise videos or just descriptions in MVP? | Product | Open |

---

## 13. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-04 | Fitness Assistant Team | Initial draft |

---

**End of Document**
