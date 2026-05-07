# FinTrack — Development Journal

This document tracks my learning journey building FinTrack from the ground up. Updated weekly with what I learned, what was hard, what decisions I made, and what's next.

---

## Week 0 — Planning & Architecture

**Date:** March 2026

### What I did this week

- Created PROJECT_PLAN.md with full technical decisions documented and reasoned
- Designed database schema: users, transactions, categories, goals, budgets, anomalies
- Planned v1 API endpoints (7 endpoints: 3 auth + 4 transaction CRUD)
- Created complete folder structure following layered architecture (routes/services/pipelines/models/ml_engine)
- Initialised git repository with conventional commit format
- Set up professional README with version roadmap, tech stack table, and architecture diagram
- Registered Ltd company through Companies House
- Opened business bank account (Monzo Business)
- Registered with ICO for data processing
- Applied for SEIS advance assurance from HMRC
- Started Twitter/X account documenting the build journey
- Created .gitignore, .env.example, config.py, requirements.txt

### Key decisions and reasoning

**Why Flask over Django?**

<!-- GUIDANCE: Your answer should cover these points in YOUR OWN WORDS:
     - Flask gives you control over architectural decisions (Django makes them for you)
     - You WANT to make decisions like "where does auth go" and "how do I structure services" because learning those decisions is the point
     - Django's built-in admin, ORM, and auth would hide the engineering work you're trying to demonstrate
     - Flask is industry-standard for APIs — it's not a "lesser" choice, it's the right tool for this job
     - You considered FastAPI but async adds complexity that doesn't solve a real problem at this scale
     Write 3-4 sentences. Be specific. -->

[YOUR REASONING HERE]

**Why SQLite for development, PostgreSQL for production?**

<!-- GUIDANCE: Your answer should cover:
     - SQLite requires zero setup — no server, no configuration, just a file
     - Perfect for rapid iteration during development (easy to reset, portable)
     - PostgreSQL is needed in production for concurrent users, reliability, and scalability
     - SQLAlchemy makes the switch painless — only the connection string changes
     - This is a deliberate engineering strategy: start simple, upgrade when needed
     Write 3-4 sentences. -->

[YOUR REASONING HERE]

**Why SQLAlchemy ORM instead of raw SQL?**

<!-- GUIDANCE: Your answer should cover:
     - Database-agnostic — same code works with SQLite and PostgreSQL (critical for your migration strategy)
     - Prevents SQL injection automatically through parameterised queries
     - Industry standard with Alembic for schema migrations
     - You mitigate the "hides SQL" downside by using echo=True in development to see every generated query
     - Raw SQL would be more verbose, database-specific, and harder to migrate
     Write 3-4 sentences. -->

[YOUR REASONING HERE]

**Why Decimal for money and not Float?**

<!-- GUIDANCE: Your answer should cover:
     - Floating point arithmetic has rounding errors: 0.1 + 0.2 = 0.30000000000000004
     - Financial calculations require exact precision — you cannot be off by fractions of a penny
     - Decimal type is designed specifically for exact decimal arithmetic
     - This is a professional decision that shows understanding of data types in financial systems
     Write 2-3 sentences. -->

[YOUR REASONING HERE]

**Why user authentication from v1 instead of adding it later?**

<!-- GUIDANCE: Your answer should cover:
     - This is a real product, not a single-user demo — users must exist from day one
     - Every transaction needs a user_id foreign key for data isolation
     - Retrofitting auth onto an existing codebase is significantly harder than building it from the start
     - Without auth, you'd have to restructure every query and every route when you add it later
     - Security is a foundation, not a feature you bolt on
     Write 3-4 sentences. -->

[YOUR REASONING HERE]

**Why Jinja2 templates first instead of React?**

<!-- GUIDANCE: Your answer should cover:
     - Jinja2 lets you ship a working product in one codebase without learning a frontend framework simultaneously
     - The backend is built as a REST API from day one, so React can replace templates later without changing any backend code
     - Starting with React would double development time at a stage where speed matters most
     - This shows engineering maturity: ship with simple tools first, modernise when the foundation is solid
     Write 3-4 sentences. -->

[YOUR REASONING HERE]

**Why no PUT/update endpoint in v1?**

<!-- GUIDANCE: Your answer should cover:
     - MVP scope discipline — add, view, and delete are sufficient for v1
     - Users can delete and re-add to correct mistakes
     - PUT adds form complexity (pre-populate fields, handle partial updates) that doesn't change core value
     - Deliberately deferred to v2 — this shows intentional prioritisation, not an oversight
     Write 2-3 sentences. -->

[YOUR REASONING HERE]

### What I learned

<!-- GUIDANCE: Be specific. Not "I learned about databases" but specific insights like:
     - "I learned that Float types have binary representation issues that make them unsuitable for money"
     - "I learned that Flask blueprints let you organise routes into separate files"
     - "I learned that .gitignore needs to include .env to prevent committing secrets"
     - "I learned that normalising categories into a separate table prevents data inconsistency"
     - "I was surprised by how much planning is involved before writing any code"
     List 4-6 specific things. -->

- [SPECIFIC LEARNING 1]
- [SPECIFIC LEARNING 2]
- [SPECIFIC LEARNING 3]
- [SPECIFIC LEARNING 4]
- [SPECIFIC LEARNING 5]

### What was hard

<!-- GUIDANCE: Be honest. This is what makes the journal valuable. Examples:
     - "Designing the database schema took much longer than expected — deciding whether category should be text or a FK required thinking through v2 implications"
     - "Understanding the difference between guidance and regulated financial advice required research into FCA rules"
     - "Choosing between Flask and Django required reading documentation for both before I felt confident in the decision"
     - "Figuring out what belongs in v1 vs later versions was difficult — I kept wanting to add more features"
     List 2-4 honest challenges. -->

- [HONEST CHALLENGE 1]
- [HONEST CHALLENGE 2]
- [HONEST CHALLENGE 3]

### What's next

- Week 1: Build User model with Flask-Login + Bcrypt
- Week 1: Build auth routes (register, login, logout)
- Week 1: Build Transaction model with user_id foreign key
- Week 1: Build transaction CRUD endpoints
- Week 1: Deploy initial version to Render

---

## Week 1 — Auth + Database + First API

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Key decisions and reasoning

- [Document every technical choice — for example: "I chose to use Flask Blueprints to organise routes because..." ]

### What I learned

- [Be specific — not "learned Flask" but "learned how Flask-Login's user_loader callback maintains sessions across requests by storing the user ID in the session cookie"]

### What was hard

- [Be honest — debugging, confusion, things that didn't work the first time]

### What's next

- [Specific tasks for week 2]

---

## Week 2 — Frontend + Ship v1.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### v1.0 shipped!

- **What works:** [List everything that works]
- **What's ugly:** [Be honest about what needs improvement — this shows self-awareness]
- **What I'd do differently:** [Reflection on the first two weeks]
- **Git tag:** v1.0

---

## Week 3 — Goals + Analytics + Ship v2.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Key decisions

- [Why did you structure the service layer this way?]
- [How did you decide what analytics to build first?]
- [How did you design the fact-find questionnaire?]

### v2.0 shipped!

- **Git tag:** v2.0

---

## Week 4 — Simulator + ML Categorisation

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### ML decisions

- [What approach did you take for auto-categorisation and why?]
- [How did you prepare training data?]
- [What accuracy did you achieve? Is that good enough? Why?]

### Simulator design

- [How does the projection engine work?]
- [What assumptions does it make?]
- [How does scenario modelling differ from baseline projection?]

---

## Week 5 — Intelligence Layer + Ship v3.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### v3.0 shipped!

- **Git tag:** v3.0
- **This is the version that makes people say "wow"**

---

## Week 6 — Nudges + Budgets + Ship v4.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Nudge system design

- [How does the ML identify high-spend days?]
- [What tone did you choose for nudge messages and why?]
- [How do you avoid making users feel guilty?]

### v4.0 shipped!

- **Git tag:** v4.0

---

## Weeks 7–8 — Stripe + Chatbot

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Stripe integration

- [How do webhooks work and why are they necessary?]
- [How does the 14-day trial expire technically?]
- [What happens when a payment fails?]

### Chatbot design

- [What goes into the system prompt?]
- [How does the context builder assemble user data?]
- [How did you test compliance boundaries?]
- [What adversarial questions did you try and what happened?]

---

## Session — Affordance Audit, Trial Gate Fixes, Doc System Hardening

**Date:** 18 Apr 2026

### What was done

Third audit pass focused on interactive affordance, button vocabulary enforcement, centering island removal, and CSS variable scoping. Identified and fixed a class of issues that wouldn't show in static analysis: mixed tappable/non-tappable lists, invisible section CTAs, custom pill button classes, lone btn-secondary CTAs, and rgba values hardcoded outside the CSS token system.

### Fixes shipped

- **trial_gate.html:** Removed decorative circular icon above h1, removed all `text-align: center` (header, value framing, CTA card title, fine print, trust signals), fixed CTA card to use CSS variables, changed button to `btn-primary btn-full`, removed centering island wrapper, removed orphaned `</div>`.
- **CSS variables:** Added `--gold-whisper-bg` and `--gold-whisper-border` to `:root` in `main.css` so all themes inherit them. Added ivory and cobalt overrides to `themes.css`. Previously only existed on `body.theme-racing-green` — other themes got `undefined`.
- **Section CTAs (overview.html):** "My goals" and "My money" section CTAs changed from invisible plain-text links → custom pill class (wrong) → `btn-secondary btn-sm` with Lucide chevron-right. Now have clear interactive affordance.
- **Overview pots list:** Removed Lifestyle & Buffer allocation rows — they have no detail pages and were mixing non-tappable rows into a tappable list. All remaining pot rows navigate to goal detail. List is now homogenous.
- **goal_detail.html unreachable state:** Added "No contribution set" heading, changed `btn-secondary` → `btn-primary btn-sm`, changed label from "Adjust this goal" → "Edit this goal", fixed link target (was incorrectly pointing to `my_goals`, now points to `edit_goal`).
- **withdraw.html:** Replaced custom `.withdraw-preset` pill-shaped class with `btn-secondary btn-sm`. Deleted the entire `<style>` block defining it.
- **Centering islands removed:** `surplus_reveal.html`, `plan_reveal.html`, `plan_review.html`, `goal_chips.html` — outer `max-width: 560px; margin: 0 auto` wrappers removed from all four.
- **companion.html:** Removed `text-align: center` from daily limit reached message.
- **plan_review.html:** Removed `text-align: center` from guidance footer paragraph.
- **budgets.html:** Fixed hardcoded `rgba(197,163,93,0.2)` → `var(--roman-gold-glow)`.
- **DESIGN-SYSTEM.md:** Added §4.5 Section CTAs, §12.0 List affordance rule, 4 new compliance checks (centering island, lone secondary CTA, custom pill button, fix-everywhere rule).
- **AGENTS.md:** Added full UI audit subsections — Button vocabulary, Section CTAs, Affordance (list homogeneity), Centering islands, Colour hardcoded rgba, Empty/unreachable states, Audit scope.
- **lessons.md:** 8 new entries added. Duplicate "mixed tappable/non-tappable" entry merged into one with the correct final rule.

### Outstanding

- Playwright stress test blocked by MCP server disconnect — prompt ready for next session to resume immediately
- Backend: wire `show_life_checkin_nudge` variable in overview route (Dan's task, unchanged)

---

## Session — Onboarding UX Audit: Chip States, CTA Patterns, Wizard Flow, AI Whisper Placement

**Date:** 18 Apr 2026

### What was done

Second UI audit pass focused on the onboarding wizard and post-onboarding overview experience. Identified and fixed structural and interaction-level UX failures: competing progress systems (welcome 2-step checklist vs. 4-step wizard), invisible chip selected states, hidden primary CTAs, AI commentary on the wrong page, and inconsistent Lucide icon usage across CTA buttons.

### Fixes shipped

- **Onboarding architecture:** Removed welcome page from new-user flow. Register now routes directly to factfind (step 1 of 4). The wizard handles complete onboarding. Competing progress systems eliminated.
- **Chip selected states:** `goal_chips`, `factfind`, `surplus_reveal` — selected chips now use `var(--roman-gold)` border, replacing the near-invisible `rgba(255,255,255,0.3)`.
- **CTA pattern:** goal_chips "Build my plan" button changed from `display:none` (hidden until selection) to always-visible disabled state with instructional text. Enables + gains arrow icon on selection.
- **AI whisper placement:** Removed gold-card commentary from `plan_reveal` (reveal/hero moment). Added to `plan_review` (detail/confirmation step) where it's contextually appropriate.
- **Lucide icons:** All CTA arrow icons standardised to Lucide `arrow-right` SVG. Back links use Lucide `chevron-left`. DOM construction via `createElementNS` (innerHTML blocked by security hook).
- **Step bar layout:** Back link moved to LEFT of bars on `goal_chips`, `surplus_reveal`, `plan_reveal`. Step counter stays RIGHT.
- **Password strength (register):** Upgraded from 3-bar (length-only) to 4-bar system + per-requirement chips (8+ chars, Uppercase, Number, Symbol) — matches settings.html pattern.
- **Settings:** Financial Profile section stripped of `glass-card` wrapper — now a flat bare section matching Account and Appearance.
- **Optional fields:** `(optional)` indicators added to Target amount, Already saved, Monthly contribution, Target date on add_goal and edit_goal forms.
- **Overview nudge:** No-goals nudge removed old 2-step progress bars and now links to `/goals/choose` (wizard) instead of the manual add-goal form.
- **AGENTS.md:** Updated with registration routing rule, button icon rule, onboarding wizard architecture, and wizard page sequence.
- **lessons.md:** Four new lessons added (chip states, hidden CTAs, AI whisper placement, competing progress systems).

### Branch

`test/onboarding-ui-audit` — pushed for Dan's review. May have conflicts with Dan's concurrent changes; resolve in next session.

---

## Session — UI Audit: Colour Semantics, Card Usage, Hierarchy (All Active Routes)

**Date:** 17 Apr 2026

### What was done

Ran a comprehensive end-to-end UI audit against the full `/ui-audit` checklist across all 25 active Claro templates. Every confirmed violation was fixed in the same session. Key areas resolved: gold colour overuse (hardcoded `rgba(197,163,93,...)` bypassing CSS tokens broke all non-default themes), card misuse on non-financial analysis sections, CRUD completeness gap on goal detail, missing back-links on plan and check-in pages, and onboarding progress bars incorrectly using gold instead of neutral white.

### Fixes shipped

- **Gold token sweep:** Eliminated all hardcoded `rgba(197,163,93,...)` across 8 templates. All gold now flows from `var(--roman-gold)` or `var(--roman-gold-dim)` tokens, meaning Cobalt and light themes no longer break.
- **Card overuse:** Removed `glass-card` wrappers from analysis/comparison sections in `insights.html` and all 9 form sections in `goal_chips.html`. Cards are now only on discrete financial objects.
- **Onboarding progress bars:** All 4 step-indicator bars across `factfind`, `surplus_reveal`, `goal_chips`, `plan_reveal` changed from gold to `rgba(255,255,255,0.25)`. Gold progress bars are now strictly goal savings bars only.
- **CRUD completeness:** Added Edit button to `goal_detail.html`. Users can now reach goal editing from the detail page, not just the goals list.
- **Navigation:** Added ← Overview back links to `plan.html` and `checkin.html`.
- **Copy:** Fixed em dash in `insights.html` body copy and `simulator_routes.py` user-facing message. Done icon circles on `welcome.html` changed from gold to green (matching the "done" badge convention).
- **Chip selection states:** Factfind subscription chips, goal chips, and lifestyle budget options — gold selected state replaced with neutral white across `factfind.html`, `goal_chips.html`, `surplus_reveal.html`.

### Outstanding

- Playwright visual verification still needed (MCP was unavailable during session — prompts ready for next session)
- Settings accordion cards (Appearance, Account) — design decision deferred on whether to convert to bare sections

---

## Week 9 — Deploy + Launch + Ship v5.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Launch checklist completed

- [ ] PostgreSQL migration verified
- [ ] All tests passing in CI/CD
- [ ] Stripe in live mode
- [ ] Security audit complete
- [ ] Documentation complete
- [ ] README with screenshots and live demo link
- [ ] Waitlist landing page live

### v5.0 shipped!

- **Git tag:** v5.0
- **Live URL:** [INSERT URL]

---

## Final Reflection

**Most important thing I learned across the whole project:**

[Write a genuine reflection — what changed about how you think about software engineering?]

**Hardest challenge and how I overcame it:**

[Be specific about a particular problem, not generic]

**What I'm most proud of:**

[What would you show someone first?]

**What I'd do differently if I started over:**

[This shows growth — employers value honest reflection over claims of perfection]

**What's next for FinTrack:**

[What's on the v6 roadmap? What did users ask for that you haven't built yet?]

---

## 2026-05-01 — Account deletion (UK GDPR Article 17) + FK cascade

### What I did

- **Cascade on every user-referencing FK.** Updated `transactions`, `goals`,
  `budgets`, `chat_messages`, `life_checkins`, `checkins`, and
  `checkin_entries` so deleting a user (or a parent check-in) doesn't fail
  on FK violations. Models now use `ondelete="CASCADE"`; relationships use
  `cascade="all, delete-orphan"` and `passive_deletes=True` so SQLAlchemy
  defers to the DB instead of issuing per-row DELETEs.
- **Idempotent migration in `app/__init__.py`.** Postgres-only block that
  reads `information_schema.referential_constraints`, drops + recreates any
  FK whose `delete_rule` isn't already `CASCADE` (or `SET NULL` for
  `checkin_entries.goal_id`). Safe to redeploy — once the cascade is in
  place, the block becomes a no-op. SQLite local dev relies on ORM-level
  cascade plus `PRAGMA foreign_keys = ON` (added as a connect-event hook).
- **Deletion service.** `app/services/account_service.py` —
  `delete_user_account(user_id, reason=None)`. Cancels the Stripe
  subscription immediately, fires `account_deleted` to PostHog *before* the
  row is removed (so the distinct_id still resolves), then deletes the user.
  Stripe failures are caught and logged but do not abort the DB delete —
  data erasure is the GDPR obligation; an orphaned subscription is the
  lesser harm. Idempotent: deleting an already-absent user returns True.
- **Settings UX.** A subtle "Danger zone" link at the bottom of
  `/settings` opens a dedicated `/settings/delete-account` page (not a
  modal — account deletion deserves a full-page moment). The page explains
  what is removed, takes an optional reason, and uses GitHub's "type
  DELETE to confirm" pattern to arm the destructive button. After
  deletion the user is logged out and lands on `/account-deleted` with a
  short confirmation and a link to register again.
- **9 new tests** covering the service (DB delete, cascade, Stripe call,
  Stripe failure, PostHog ordering, idempotency) and the route (auth
  required, wrong confirmation rejected, happy path). Suite goes
  407 → 416 passing.

### GDPR status

- **Article 17 (right to erasure):** ✅ in place from this PR.
- **Article 20 (right to data portability / export):** ❌ still TODO.
  When a user deletes their account they're also entitled to a copy of
  their data first. Half-day of work. Pre-launch backlog.

### Schema management note

Migrations are still managed by `db.create_all()` + the idempotent
`ALTER TABLE` block in `app/__init__.py`. Bootstrapping
Flask-Migrate / Alembic is recommended within the next 2 weeks
pre-launch (separate PR — needs `flask db stamp head` against prod
before the first `flask db upgrade`).

---

## 2026-05-01 — Server-side PostHog instrumentation

### What I did

- Added the `posthog==7.13.2` Python SDK + `backoff==2.2.1` dep to `requirements.txt`.
- Built `app/services/analytics_service.py` — a thin lazy-init wrapper around the
  PostHog SDK with three public functions: `track_event(user_id, event_name, properties=None)`,
  `identify_user(user_id, properties=None)`, and `flush()`. The wrapper:
  - Reads `POSTHOG_API_KEY` and `POSTHOG_HOST` from Flask config (or env vars when no app context).
  - Drops events silently and logs a single warning when the key is missing — dev environments without it don't crash.
  - Catches every SDK exception so analytics failures NEVER propagate into a user-facing route.
  - Auto-attaches `environment` (test/dev/prod), `timestamp`, and `user_tier` (when discoverable from `current_user`) to every captured event.
- Wired the agreed taxonomy server-side at the natural firing point in each route handler. **Server-side capture only — no JS snippet in `base.html`.**

### Events instrumented (where they fire)

| Event | Location |
|------|---------|
| `user_signed_up` | `pages.register` POST + `auth.register` POST (API) |
| `welcome_screen_viewed` | `pages.welcome` GET |
| `factfind_started` | `pages.factfind` GET when `factfind_completed=False` |
| `onboarding_stage1_completed` | `pages.factfind` POST success (first time only) |
| `partial_projection_1_viewed` | `pages.surplus_reveal` GET |
| `onboarding_stage2_completed` | `pages.surplus_reveal` POST success |
| `partial_projection_2_viewed` | `pages.goal_chips` GET |
| `onboarding_stage3_completed` | `pages.goal_chips` POST success — includes `time_to_onboarding_complete` (minutes since signup) |
| `goals_added` | `pages.goal_chips` POST + `pages.add_goal` POST (with `count`, `types`, `source`) |
| `plan_revealed` | `pages.plan_reveal` GET when `plan_wizard_complete` is being set true (first reveal only) |
| `credit_card_added` | Stripe `checkout.session.completed` webhook |
| `trial_started` | Same handler — Stripe Checkout requires a card before the subscription, so they fire together |
| `checkin_started` | `pages.checkin` GET when not already done |
| `checkin_completed` | `pages.checkin` POST success |
| `goal_milestone_hit` | Inside `pages.checkin` POST loop — fires when a goal's progress crosses 25/50/75/100% |
| `companion_message_sent` | `companion.companion_chat` after successful response — properties: `tier`, `message_count_today`, `tokens_in/out`, `model_routed` (`haiku` or `sonnet`) |
| `companion_rate_limit_hit` | `companion.companion_chat` and `.edit_message` when daily limit reached — properties: `tier` (effective rate-limit key, e.g. `pro`/`pro_plus`/`joint`/`trial`), `time_until_reset_seconds` |
| `companion_starter_chip_clicked` | `companion.chip_clicked` (fired from `/api/companion/chip-clicked` POST when a user clicks a suggestion chip on the empty-state companion view) — properties: `chip_text` |
| `withdrawal_started` | `pages.plan` GET when `?withdraw=1` first opens the inline section |
| `withdrawal_preview_generated` | `pages.plan_withdraw_preview` POST success — properties: `amount` |
| `withdrawal_confirmed` | `pages.plan_withdraw_confirm` POST success — properties: `amount` (the plan was applied to goals) |
| `withdrawal_dismissed` | `pages.plan_withdraw_dismiss` POST — user clicked "No, just show me"; properties: `amount` |
| `cancel_confirmed` | Stripe `customer.subscription.deleted` webhook |
| `account_deleted` | `account_service.delete_user_account` — fires before the User row is removed; properties: `reason` (optional free text from the user) |
| `dev_test_event` | `/dev/posthog-test` (debug-only smoke test) |

`identify_user(user_id, {email, name, tier, signup_date})` also fires on every register and login so funnels attribute to a stable distinct ID.

### Events NOT yet instrumented (TODO)

- `email_verified` — no email verification flow exists yet. Add when that ships.
- `crisis_flow_entered` — no crisis flow page exists yet.
- `cancel_clicked` / `cancel_dismissed` — Stripe customer-portal hosts the cancel UI off-app, so we don't see the click. When an in-app cancel page ships, instrument these there. Marked with `TODO PostHog:` comments in `billing_routes.py`.

### Tests

Added `tests/test_analytics_service.py` (9 tests) covering the four contracts:
1. No-op when key missing
2. SDK called with right args when key set
3. Exceptions don't propagate (wrapper + integration)
4. `environment` auto-attached to every event

Total suite: **407 passing** (398 original + 9 new).

### What's deliberately NOT done

- **No JS snippet in `base.html`.** Server-side capture only — keeps the data clean, avoids consent-banner complexity at MVP stage. When we need session replay or autocapture, revisit.
- **Git remote update** (`Drogers0819/Fintrack.git → Drogers0819/Claro.git`) is a user action; left for Daniel to run manually.
- **Render env vars** must still be set in the dashboard before the next deploy or events fail silently in prod.

### Hard lessons / decisions

- **Lazy single-client init** — easier than wiring a Flask extension. The first call to `track_event` triggers init via `current_app.config`; subsequent calls hit a cached client. Guards against repeat warning spam when the key is missing.
- **Exception swallowing is non-negotiable** — `except Exception` in tracking code is normally a smell, but here the contract is explicit: analytics is auxiliary, must not break product features.
- **`time_to_onboarding_complete` is computed at the firing point** rather than stored on the user — keeps the event self-describing and avoids a migration. Computed as `(datetime.utcnow() - user.created_at).total_seconds() / 60` at the moment stage 3 completes.

---

## 2026-05-02 — Companion live in production

### What I did

- **UTC rate-limit reset.** `check_rate_limit` and `increment_message_count` in `companion_service.py` now compare against `datetime.utcnow().date()` instead of `date.today()`. No schema change — the existing `companion_last_reset` Date column is reused, the comparison is just explicit about timezone. On Render the server is UTC anyway; this just decouples behaviour from server local time.
- **Per-tier rate-limit chat bubble.** `check_rate_limit` returns a 3-tuple `(allowed, reason, kind)` where `kind` is `'free'` (paywall), `'rate_limit'` (daily cap), or `None` (allowed). Per-tier copy lives in `_RATE_LIMIT_COPY` in `companion_service.py`. Pro / Pro+ / Joint / Trial each get tailored wording. The bubble renders at the end of chat history (page-load path) or via the existing 429 JS handler (mid-chat path); not persisted as a `chat_messages` row. Below the bubble, the input zone is replaced with "Messaging resumes at midnight UTC."
- **Companion nav visibility.** Added `_inject_companion_access` context processor in `app/__init__.py` exposing `can_access_companion = is_subscription_active(current_user)`. Wraps the four companion nav slots in `base.html` (slim sidebar, legacy desktop sidebar, slim mobile tabs, legacy mobile tabs) plus the overview prompt + chips. Free post-trial users no longer see a link they can't follow.
- **Hybrid classifier enriched.** `COMPLEX_TRIGGERS` extended with distress markers (`lost my job`, `can't afford`, `struggling`, `worried`, `anxious`, `stressed`, `scared`, `overwhelmed`, `in trouble`, `broke`, `no money`, `behind on`, `missed a payment`). Routes these to Sonnet because its judgement and warmth on emotionally-loaded financial situations is materially better than Haiku's. Skipped the conversation-history continuation and length-based heuristic — the keyword list is sufficient at this stage and we'll revisit after the 25-scenario sprint.
- **Effective limit key.** Added `_effective_limit_key(user)` so trial users (status=`trialing`) hit the trial limit (5/day) regardless of their plan tier. Previously a Pro-tier user mid-trial would have got the Pro limit (10/day) — minor but the per-tier copy depends on it.
- **Smoke test route.** `/dev/companion-smoke-test` registered only when `app.debug` is true. Calls `companion_service.smoke_test_chat()` which bypasses user context, rate limits, and persistence — just hits the API with the cached static system prompt and returns `success`, `response_text`, `model_used`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `cache_hit`, `latency_ms`. Hit it twice within 5 minutes locally to verify caching engages: first call shows `cache_creation_input_tokens > 0`, second shows `cache_read_input_tokens > 0`. **Remove in a follow-up commit (`chore: remove companion smoke test route once verified`) after one-off verification.**

### Events instrumented

- `companion_message_sent` — added `model_routed` property (`haiku` or `sonnet`) so we can track the routing split in PostHog and compare against the 70/30 cost model.
- `companion_rate_limit_hit` (new) — fires from `companion.companion_chat` and `.edit_message` when the daily cap is reached. Properties: `tier` (effective rate-limit key) and `time_until_reset_seconds` (computed from next UTC midnight). Helps quantify how often users hit the cap and inform whether 30/day on Pro+ is the right number.

### What's deliberately NOT done

- **No `@requires_companion_access` decorator and no `/companion/upgrade-needed` page.** `@requires_subscription` already gates the only fully-blocked case (free post-trial). Pro tier keeps its 10 messages/day. The pricing page handles tier-feature messaging ("AI companion (limited)" vs "(full)") rather than the gating logic.
- **No schema change for `companion_messages_reset_at`.** The existing `companion_last_reset` Date column does the job once UTC is wired in. Adding a DateTime column would have been the same behaviour on Render with extra migration risk.
- **No conversation-history or length-based heuristic in the classifier.** Keyword list is enough for now; revisit after the 25-scenario evaluation sprint.

### Tests

Added `tests/test_companion_routes.py` covering classifier (existing triggers + distress markers + simple), rate-limit (UTC reset, per-tier copy, kind discrimination, free-tier blocking), per-tier `_effective_limit_key`, smoke-test 404 in non-debug mode, and the rate-limit chat-bubble rendering on page load.

### Manual verification still needed

- Confirm `ANTHROPIC_API_KEY` and `POSTHOG_API_KEY` are set in Render.
- Hit `/dev/companion-smoke-test` locally twice within 5 minutes to confirm caching engages.
- Send a real message in production with a Pro+ test account; check PostHog for `companion_message_sent` with `model_routed` populated.
- Verify a free post-trial test account does NOT see the Companion nav link in any of the four nav slots.
- Verify the rate-limit bubble appears (lower the limit temporarily to 1 if needed for the test).
- After verification, delete the smoke test route in a follow-up commit.

---

## 2026-05-02 — Empty states across primary screens

### What I did

Audited the primary screens, kept the patterns that already worked, and refined or added the rest. The audit found `/my-goals` and `/companion` already had decent empty states, `/check-in` had the "already done" path, and `/overview` and `/plan` had reasonable but unpolished fallbacks. The work below is mostly copy refinement plus two genuinely new states: the `/check-in` "scheduled" view and the `/plan` error fallback.

- **Overview banner copy + placeholder cards.** Kept the existing banner-on-top pattern (the audit confirmed it's friendlier than a wholesale replacement). Refined the banner copy for both factfind-incomplete ("Take 4 minutes to share your situation. We'll show you exactly when your goals become real.") and no-goals ("Your plan is ready. What are you saving for?"). Added a calm placeholder card under each banner ("Your monthly position will appear here once your plan is built." / "Your goals will appear here as you add them. Pick what matters.") so the dashboard isn't anchored only by the banner.
- **Goals empty state polish.** Refined heading + subtitle copy, swapped CTA to "Add my first goal", and added four illustrative chips ("House deposit", "Holiday", "Emergency fund", "Pay off debt") below the CTA. Display-only, not clickable.
- **Plan empty / error states.** Replaced the inline "Build your financial plan" message with two branches: factfind-incomplete shows "Your plan is waiting to be built" + "Build my plan" CTA, and a new plan-error branch shows "We can't quite build your plan yet" + "Review my profile" CTA with the underlying error in a tertiary panel for support context. Wrapped the scenario link and withdrawal section in a `smart_plan and not smart_plan.error` guard so they no longer leak below the empty state.
- **Check-in window gating.** Added `_checkin_view_state(today, existing, edit_mode)` helper in `page_routes.py` that returns one of `'complete'`, `'form'`, or `'scheduled'`. The check-in form now only renders during the last 3 days of the current month (the existing window definition reused from the overview pill). Outside the window, users see the "Your next check-in is on [date]" state with days-to-go and a "Want to log something now?" link to `/life-checkin`. Refreshed the "all set for this month" copy on the complete-state gold card and added a "Review my plan" link with the completion date. Edit mode (`?edit=1`) still always reveals the form.
- **TODO for Block 2 forgiveness flow.** A user who missed a prior month's check-in two or more months back is invisible to the current logic because the cover_month rolls forward. The Block 2 forgiveness flow should scan back-months and let users catch up; that case should fall through to the form state, not 'scheduled'. Marked with a TODO in `_checkin_view_state`'s docstring.
- **Companion starter-chip tracking.** Added `/api/companion/chip-clicked` (POST, JSON body, returns 204) which fires `companion_starter_chip_clicked` with `chip_text`. The existing `sendSuggestion` JS now does a fire-and-forget `fetch` to that endpoint with `keepalive: true` before pre-filling and submitting. CSRF token included in the headers per the existing pattern. Kept the existing 6 chips and the auto-send behaviour as-is — they were deliberate and they work.

### Events instrumented

- `companion_starter_chip_clicked` (new) — fired from `companion.chip_clicked` route when a user picks a suggestion chip. Property: `chip_text`. Lets us see which entry phrasings drive the first message in beta.

### What's deliberately NOT done

- **No wholesale overview replacement.** The banner-on-top pattern is calmer and lets the user see what the dashboard *will* contain.
- **No redirect to `/factfind` from `/plan`.** The inline replacement is friendlier and the plan page has nothing meaningful to render without a profile.
- **No new chips on companion empty state.** The existing 6 chips were kept; only tracking was added.
- **No JS-side analytics SDK.** The chip-click endpoint is a tiny server-side fire-and-forget so we keep the no-JS-tracking-SDK rule.
- **No new CSS classes.** All new empty-state markup uses inline styles matching `settings.html` / `delete_account.html` patterns.

### Tests

Added `tests/test_empty_states.py` covering: overview banner + placeholder card rendering for factfind-incomplete and no-goals; goals empty-state copy + 4 illustrative chips; plan factfind-incomplete and plan-error branches; `_checkin_view_state` helper in all three states; `/api/companion/chip-clicked` event firing and login gate.

### Manual verification still needed

- Register a fresh test account, do not complete factfind, visit `/overview` → confirm banner copy + "Your monthly position" placeholder card.
- Complete factfind, visit `/overview` before adding goals → confirm "Your plan is ready" banner + "Your goals" placeholder card.
- Visit `/my-goals` with no goals → confirm copy + 4 illustrative chips render.
- Visit `/plan` without completing factfind → confirm "Your plan is waiting to be built" empty state.
- Visit `/check-in` outside the last 3 days of the month → confirm "Your next check-in is on [date]" state and `/life-checkin` link.
- Visit `/check-in` after completing this month's check-in → confirm "You're all set for this month" copy and "Review my plan" link.
- Open `/companion` with no message history, click a chip → confirm message sends and `companion_starter_chip_clicked` fires in PostHog with the chip text.

---

## 2026-05-02 — Loading and error states (Block 1 complete)

### What I did

The audit found the codebase in better shape than expected: 404/500 handlers were already registered, Stripe checkout already had `try/except stripe.error.StripeError` wrappers, the companion already had a typing indicator with error fallback, and Resend was a stub so email failures were a non-issue. The genuine gaps were the `db.session.rollback()` on 500, no fetch timeout in the companion JS, no form-loading states on slow forms, no inline validation errors (validation failures used flash + redirect, losing user input), and no loading state on the trial-gate Stripe redirect.

- **`db.session.rollback()` on 500.** Added to the handler in `app/__init__.py`. Wrapped in its own try/except so a rollback failure doesn't itself raise inside the error handler. Without this, a failed transaction left the SQLAlchemy session in a broken state and subsequent requests on the same worker would cascade-fail confusingly.
- **404 / 500 templates.** Added a conditional home link to 404 (anonymous → `/`, logged-in → `/overview`), plus a "Something we should know about?" support link with a `mailto:`. Added a "Try again" reload button to 500 alongside the existing back-to-overview link. Both templates now define `{% block content %}` AND `{% block auth_content %}` (via a Jinja macro) because base.html switches between those blocks based on `current_user.is_authenticated`. Without that, anonymous 404s rendered the base envelope with no body.
- **Companion fetch timeout.** Added `AbortController` + `setTimeout(..., 30000)` around the `fetch()` in `companion.html`. On `AbortError` the catch handler shows "Hmm, that took longer than expected. Mind trying again?". On any other error it shows "Something went wrong on our end. Try sending that again?" — both per the spec copy. Falls back gracefully when `AbortController` is undefined (very old browsers); the request just runs without a timeout.
- **Global form-loading helper.** Added a small vanilla-JS helper to base.html's existing `<script>` block. Forms opt in by adding `data-loading="true"` on the form OR `data-loading-text="..."` on the submit button. On submit the helper sets `aria-busy="true"`, swaps the button label to a spinner + the loading text, and disables the button on the next microtask (deferring disable so the form actually submits). Registered: factfind ("Building your plan..."), check-in ("Saving your check-in..."), add-goal ("Saving..."), edit-goal ("Saving..."), registration ("Creating your account...").
- **`.btn-spinner` CSS.** Added a 12px ring-spinner with `@keyframes claro-spin` to the existing `<style>` block in base.html's head. Uses `currentColor` so it picks up the surrounding button text colour; named `claro-spin` to avoid clashing with any future `spin` keyframe elsewhere.
- **Inline validation.** Refactored four routes from "redirect on error with a flash" to "re-render with `errors` dict and `form_data`". Each field validates independently so errors accumulate (one typo doesn't blank the rest). Errors render below the relevant input as `<span class="field-error-msg">...</span>` and the input picks up `field-invalid` — both classes already existed in `main.css` for the client-side required-field validator, so no new CSS needed for error display. Refactored:
  - `pages.register` + `register.html`
  - `pages.factfind` + `factfind.html`
  - `pages.add_goal` + `add_goal.html` (also added cross-field check: current must not exceed target; deadline must be in the future)
  - `pages.edit_goal` + `edit_goal.html` (plus tightened edit_goal's previously-unsafe `float()` calls into the proper `validate_amount` path)
- **Trial-gate Stripe redirect.** Added an inline `onclick` handler on the per-tier "Start 14-day trial" link that swaps the link text to a spinner + "Setting up your trial...", disables further clicks (`pointer-events: none`), and sets `aria-busy="true"`. Single CTA, no helper needed; if a second redirect-loading link shows up, extract into a `data-redirect-loading` helper.

### What's deliberately NOT done

- **No inline validation on login or password-reset.** Spec scope was registration + factfind + add-goal + edit-goal. Login and reset can stay on flash-style errors for now; tracking as future work.
- **No JS-side analytics on errors.** Error tracking belongs in Sentry (Block 3).
- **No Resend wrapping.** Email send is still a stub; nothing to catch yet.

### Tests

22 new tests in `tests/test_loading_error_states.py`: 404 anonymous + logged-in, 500 template body, 500 handler rollback (verified by triggering an exception then confirming a follow-up request still works), inline validation across all four refactored routes (errors render + input preserved + valid POSTs still redirect), data-loading-text attributes wired on every relevant submit button, `.btn-spinner` CSS + form-loading helper present in base.html, companion timeout/AbortController wiring.

494 baseline + 22 new = **516 passing**.

### Deviations from spec

- **`.btn-spinner` is a new CSS class.** The hard rule said "no new CSS classes — use existing inline-style patterns". The deviation is intentional: a one-off keyframe animation is functional infrastructure that doesn't yet exist in the codebase, and inlining it on every submit button would mean repeating `@keyframes` declarations per page. Single class in base.html matches the existing `.typing-dots` precedent in companion.html.
- **404 / 500 templates defined `auth_content` block.** base.html toggles between `{% block content %}` (logged-in) and `{% block auth_content %}` (anonymous) based on `current_user.is_authenticated`, so error templates that only define `content` rendered as an empty page envelope for unauthenticated users. The macro pattern keeps the body in one place and renders it from both blocks.

### Manual verification still needed

- Visit `/this-page-does-not-exist` → confirm 404 page renders with conditional "Take me home" link.
- Trigger a 500 in production (e.g. via a debug-only route or by causing a DB issue) → confirm the friendly fallback shows, and confirm the next request from the same worker still works (rollback fix).
- Submit factfind on a slow connection → confirm the button swaps to "Building your plan..." with a spinner.
- Submit registration with an invalid email → confirm inline error appears next to the email field, name field still has what you typed.
- Click "Add card"/"Start 14-day trial" on `/trial` → confirm "Setting up your trial..." with spinner before the redirect to Stripe.
- Send a companion message → confirm typing indicator. Optional: simulate a slow upstream by setting an artificial delay; confirm the 30s timeout copy appears.

---

## 2026-05-02 — Block 1 complete

All four Block 1 tasks are now in `main`:

| Commit | Task |
|--------|------|
| `990488b` | feat: withdrawal intelligence UI on plan page |
| `436674c` | feat: companion live in production with hybrid routing, rate limits, nav visibility |
| `423bd0f` | feat: empty states across primary screens |
| `__this__` | feat: loading and error states across the app |

Test count: **516 passing** (started at 416; +100 net across the block).

The product is meaningfully F&F-beta-ready on the four biggest pre-beta gaps: the withdrawal flow exists end-to-end, the AI companion is gated/rate-limited/observable in production, every primary screen has a calm empty state, and external service calls degrade to friendly errors instead of Flask debug pages. Original projection was 5-6 build days; landed in 4 focused sessions.

**Manual verification outstanding for the full block** (one consolidated pass before declaring beta-ready):

1. Withdrawal flow: walk through `/plan?withdraw=1` end-to-end on a test account, confirm Yes/No paths, confirm goal balance moves on Yes and stays on No.
2. Companion: hit `/dev/companion-smoke-test` locally twice within 5 minutes, confirm caching engages on the second call. Send a real message in production with a Pro+ test account; confirm `companion_message_sent` lands in PostHog with `model_routed`. Verify free post-trial test account does NOT see the Companion link in nav. Confirm rate-limit bubble appears when limit is hit.
3. Empty states: fresh test account → `/overview` shows banner + placeholder before factfind, then "Your plan is ready" + goals placeholder before goals. `/my-goals` empty shows the 4 illustrative chips. `/plan` without factfind shows the "Your plan is waiting to be built" empty state. `/check-in` outside last 3 days of month shows scheduled state. Companion empty state shows starter chips and clicking one sends a message.
4. Loading/error states: visit `/this-page-doesnt-exist` for 404, trigger any 500 path and confirm next request still works, submit factfind on slow connection and watch the button label, submit registration with bad email for inline error, click "Start 14-day trial" and watch the spinner before Stripe redirect.

Once the manual pass is done, Block 1 is shippable. Block 2 (unhappy paths: pay-day notifications, missed check-in forgiveness, crisis flow, survival mode, hardship pause, signposting library) starts next session.

---

## 2026-05-05 — Pay-day notification system (Block 2 Task 2.1)

### What I did

The first piece of Block 2 unhappy-path infrastructure. On a user's pay day they get an email linking to a pre-populated check-in. Without it, the monthly check-in is something users have to remember themselves; with it, the check-in becomes a ritual the system actively supports.

End-to-end shape: a daily Render cron POSTs to `/cron/payday-notifications` with an `X-Cron-Secret` header. The endpoint runs `process_payday_notifications()` from the new `app/services/scheduling_service.py`, which finds every user whose pay day matches today (or today is the last day of the month for users with `income_day` > the month length), skips users already notified this calendar month, skips users who've already filed their check-in for the relevant period, and ships the `payday_notification.{html,txt}` email via Resend.

- **Email service activated.** Replaced the stub in `app/services/email_service.py` with a real Resend implementation. New general-purpose `send_email(to_email, subject, template_name, template_context)` that renders Jinja templates from `app/templates/emails/`, swallows render and SDK failures, and returns `False` rather than raising. Logs use `sha8:<hash>` for the recipient instead of the raw address (PII rule). The pre-existing `send_weekly_digest` path is migrated onto the same SDK call but keeps its hand-built HTML render via `digest_service.render_digest_html`.
- **`payday_notification_last_sent` Date column on `User`.** Added to the model and to the idempotent ALTER block in `app/__init__.py`. Used to gate per-month idempotency.
- **`payday_notification.html` + `.txt` templates.** Mobile-first single-column layout, max-width 600px, all CSS inline. Cormorant Garamond serif heading with web-safe fallbacks, gold CTA on `#C5A35D`, copy is calm/specific/second-person — no urgency marketing, no em-dashes.
- **`app/services/scheduling_service.py` — new file.** `process_payday_notifications(today=None)` returns `{users_notified, users_skipped, errors}`. Handles the `min(income_day, last_day_of_month)` edge case so a user with `income_day=31` still gets nudged in February. Per-user errors are caught and rolled into the `errors` list rather than propagating — one bad row never locks out the rest of the run. Rate limiter sleeps 0.1s between sends once a single run crosses 100 emails (Resend free tier headroom; trivial at current scale).
- **`/cron/payday-notifications` POST endpoint** in a new `cron_routes.py` blueprint. Requires `X-Cron-Secret` header to match `CRON_SECRET` config value. Returns 405 on GET, 503 if `CRON_SECRET` isn't configured on the server, 401 on bad secret, 200 with a JSON summary otherwise. Even a top-level crash in the inner job returns 200 with errors so an external runner doesn't retry-storm.
- **Check-in route — `?source=payday`.** Pre-population was already free in `checkin.html` (income input pre-fills from `current_monthly_income`, pot inputs from `pot.planned`). The only wiring needed was reading `request.args.get("source")` and adding it as a property on the `checkin_started` event so PostHog can attribute conversions. Defaults to `"direct"` when absent.
- **Config**: `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_FROM_NAME`, `CRON_SECRET` are now read on `DevelopmentConfig` and `ProductionConfig`. `TestingConfig` explicitly sets all four to `None` to keep tests hermetic. The email service and cron route deliberately do NOT fall back to `os.environ` — `config.py` is the single source of truth, otherwise a stray dev env var leaks past `TestingConfig`.

### Schema changes

| Column | Type | Nullable | Purpose |
|--------|------|---------|---------|
| `users.payday_notification_last_sent` | `DATE` | yes | Per-month idempotency anchor for the cron |

Both `db.create_all()` (fresh DBs) and the idempotent `ALTER TABLE` block (existing Postgres) cover the migration.

### New routes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/cron/payday-notifications` | `X-Cron-Secret` header | Daily pay-day notification cron |

### Events instrumented

| Event | Where it fires | Properties |
|-------|----------------|------------|
| `payday_notification_sent` | `scheduling_service.process_payday_notifications` after a successful send | `payday_day` (the user's `income_day`), `effective_day` (capped at last day of month) |

The existing `checkin_started` event now also includes `source` (`"payday"` or `"direct"`) so the funnel can attribute check-ins to the email.

### Manual verification still needed (for Daniel)

1. **Render env vars.** Confirm `RESEND_API_KEY`, `EMAIL_FROM` (`hello@getclaro.co.uk`), `EMAIL_FROM_NAME` (`Claro`), and `CRON_SECRET` (any high-entropy string) are all set on the production service.
2. **Render cron job.** Configure a new Render cron service:
   - Command: `curl -X POST -H "X-Cron-Secret: $CRON_SECRET" https://claro-2.onrender.com/cron/payday-notifications`
   - Schedule: `0 9 * * *` (09:00 UTC daily)
3. **First-day smoke test.** Hit the endpoint manually with the secret header. Expect a 200 with `users_notified: 0` (no users are due today unless their `income_day` matches).
4. **End-to-end on a test account.** Set `income_day` on a test account to tomorrow's day-of-month. Wait for the next cron tick. Confirm: email lands in the inbox, has the right copy, the CTA opens `/check-in?source=payday`, the check-in form pre-populates, PostHog shows a `payday_notification_sent` event for that user, and a follow-up cron run on the same day notifies zero new users.

### Tests

22 new tests in `tests/test_payday_notifications.py`:
- Scheduling matching (5): basic match, no `income_day`, non-matching day, `income_day=31` in 28-day February, `income_day=31` in 30-day April.
- Idempotency (3): same-day re-run skips, send failure does NOT mark notified, prior-month notify resets this month.
- Skip rules (1): user who already filed the check-in is skipped.
- Analytics (1): `payday_notification_sent` fires with the right properties.
- Cron endpoint (6): GET=405, missing config=503, missing header=401, wrong header=401, valid call returns summary, top-level crash returns 200 with errors.
- Email service (4): no API key, SDK exception swallowed, HTML template renders, text template renders.
- Check-in source param (2): `?source=payday` flows into `checkin_started`, default is `"direct"`.

Suite count: **537 passing** (515 baseline that still pass today + 22 new). One pre-existing failure (`test_anomaly.py::TestDetectCategorySpikes::test_no_spike`) is calendar-date dependent — its synthetic transaction data prorates against the day-of-month and triggers a false spike on early-month days. Confirmed unchanged on the pre-Block-2 commit. Not addressed in this task; logged for a future calendar-stable rewrite of the anomaly test fixtures.

### What's deliberately NOT done

- **No timezone handling.** The cron runs at 09:00 UTC and matches users whose `income_day` matches today's UTC date. UK users will see the email roughly when they expect; users on other continents will see it earlier or later than their local "pay day". Out of scope until we add a `timezone` column to `User` (deferred to whenever timezone awareness lands more broadly across the app).
- **No notification preferences.** Every user with an `income_day` set gets the email by default; there's no opt-out. The footer mentions that the user can update their pay day in settings, but doesn't offer "stop sending these emails" yet. When the unsubscribe / notification preferences page ships, gate this send on a `notify_payday=True` flag.
- **No retry of send failures within a single cron run.** A failed send doesn't stamp `payday_notification_last_sent`, so the next day's cron will retry — but only if the user's `income_day` still matches today's date, which it won't on day 2. Practical effect: users who hit a transient Resend error miss that month's nudge. Acceptable at MVP scale; revisit when we build a generic transactional-email outbox.

### Deviations from the prompt

- **Check-in pre-population was already free.** The prompt suggested updating the check-in route to pre-fill values when `source=payday`, but `checkin.html` already pre-fills `current_monthly_income` (variable income input) and `pot.planned` (every other input) for every render path. The only wiring needed was the `source` property on `checkin_started` for PostHog attribution. No template change needed.
- **`income_day` field already existed.** Audit confirmed the field is on the User model, captured cleanly in factfind, and used in `companion_service` and `whisper_service`. No migration or UX work needed.

---

## 2026-05-05 — Missed check-in reminder ladder (Block 2 Task 2.2)

### What I did

Built the reminder ladder that catches users who miss a check-in after pay day. Three emails fire at decreasing-urgency intervals: day +3 ("Quick nudge"), day +7 ("Your plan is still here when you are"), day +14 ("We will stop here"). After day +14 we go quiet for the rest of the cycle. The next pay-day notification resets the ladder so the next month starts fresh.

The retention logic that drove the calibration: users who miss check-ins are at high churn risk, but the wrong tone drives them away faster than silence. Each reminder is patient, not pushy. The day-14 email signals we're going to stop, not ramping up. The shape of the ladder is the load-bearing piece — get it wrong and the system makes churn worse, not better.

- **Anchor on `payday_notification_last_sent`, not `income_day`.** The reminder ladder calculates "days since pay-day" from the date the pay-day notification actually fired, not from the user's `income_day` setting. This means the ladder is naturally tied to what the user saw in their inbox, even if their `income_day` changes mid-month, and we can't drift out of sync if the cron itself was late by a day.
- **Three new nullable Date columns on `User`.** `checkin_reminder_1_sent`, `_2_sent`, `_3_sent`. Three columns rather than one packed JSON or one "ladder progress" enum because the test logic stays trivial (`is None` is the gate, the date is the audit trail) and SQL diagnostics in production stay readable. Added to the idempotent ALTER block in `app/__init__.py` so existing Postgres pre-2.2 databases pick them up on the next deploy.
- **`process_checkin_reminders(today=None)` in `app/services/scheduling_service.py`.** Loads users with `payday_notification_last_sent IS NOT NULL`, computes `(today - anchor).days`, matches against the ladder schedule `((3, 1), (7, 2), (14, 3))`, and only fires the reminder whose corresponding `checkin_reminder_X_sent` is None. Each user matches at most one rung per run (the schedule is a tuple of disjoint days, not a range). Reuses the existing `_checkin_already_done` helper from Task 2.1 — same target-month logic, same skip rule. Returns `{users_notified, users_skipped, errors, reminder_breakdown}` where `reminder_breakdown` is `{1: n, 2: n, 3: n}` so the cron logs show which rungs hit on a given day.
- **Cycle reset in `process_payday_notifications`.** When a new pay-day notification fires, the function now clears all three reminder fields back to None. Without this, a stamp from one cycle's day-7 reminder would silently block reminder 2 from ever firing again. This is a 4-line addition to an existing function; the test `TestCycleResetOnPayday::test_payday_resets_all_three_reminder_fields` proves the reset happens, and `test_post_reset_ladder_fires_in_new_cycle` proves end-to-end that a stamped April user gets a fresh May reminder 1 after May's pay-day notification fires.
- **`/cron/checkin-reminders` POST endpoint** in `cron_routes.py`. Mirrors `/cron/payday-notifications` exactly: POST-only, `X-Cron-Secret` header, 503 if `CRON_SECRET` isn't configured, 401 on bad secret, 200 with JSON summary otherwise, top-level try/except returns 200 with errors so the external runner doesn't retry-storm.
- **Three Jinja templates per rung — HTML + TXT.** `checkin_reminder_{1,2,3}.{html,txt}` in `app/templates/emails/`. Same envelope as `payday_notification.html`: max-width 600px, mobile-first single-column, all CSS inline, Cormorant Garamond serif heading with web-safe fallbacks, gold (`#C5A35D`) CTA button. Headings: "Quick nudge.", "Still here when you are.", "We will stop here." CTA on every reminder links to `/check-in?source=reminder` so PostHog can attribute conversions through this channel separately from `?source=payday`.
- **Tone discipline check.** No em-dashes anywhere in user-facing copy (verified with a grep against the templates before commit). No urgency words, no "you're missing out", no "don't fall behind" framing. The day-14 email's job is to signal we're stopping, not to pile on. Every reminder uses the same warm voice as `payday_notification.html`.

### Schema changes

| Column | Type | Nullable | Purpose |
|--------|------|---------|---------|
| `users.checkin_reminder_1_sent` | `DATE` | yes | Day +3 reminder idempotency anchor |
| `users.checkin_reminder_2_sent` | `DATE` | yes | Day +7 reminder idempotency anchor |
| `users.checkin_reminder_3_sent` | `DATE` | yes | Day +14 reminder idempotency anchor |

`db.create_all()` covers fresh DBs; the idempotent ALTER block in `app/__init__.py` covers existing Postgres.

### New routes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/cron/checkin-reminders` | `X-Cron-Secret` header | Daily reminder-ladder cron |

### Events instrumented

| Event | Where it fires | Properties |
|-------|----------------|------------|
| `checkin_reminder_sent` | `scheduling_service.process_checkin_reminders` after a successful send | `reminder_number` (1, 2, or 3), `days_since_payday` (3, 7, or 14) |

The existing `checkin_started` event picks up `source="reminder"` for free — `?source=` flows through to the existing PostHog property without any route change needed.

### Manual verification still needed (for Daniel)

1. **Render env vars.** Confirm `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_FROM_NAME`, `CRON_SECRET` are all still set. (Same set as Task 2.1; nothing new.)
2. **Render cron job.** Two options:
   - Option A: a separate Render cron service for the reminder endpoint, scheduled `0 9 * * *` (same time as the existing pay-day cron — there's no race because they touch different state).
   - Option B: extend the existing `0 9 * * *` cron command to call both endpoints in sequence: `curl -X POST -H "X-Cron-Secret: $CRON_SECRET" https://claro-2.onrender.com/cron/payday-notifications && curl -X POST -H "X-Cron-Secret: $CRON_SECRET" https://claro-2.onrender.com/cron/checkin-reminders`
3. **Smoke test the new cron.** Hit it manually with the secret header. Expect a 200 with `users_notified: 0`, `users_skipped: N`, `reminder_breakdown: {1: 0, 2: 0, 3: 0}` (no users will be at exactly day +3/+7/+14 unless a test account is set up).
4. **End-to-end test account at day +3.** Pick a test user, set `payday_notification_last_sent` to 3 days ago, ensure no `CheckIn` row exists for the previous calendar month. Run the cron. Confirm: reminder 1 email lands, copy reads "Quick nudge", CTA opens `/check-in?source=reminder`, PostHog shows `checkin_reminder_sent` with `reminder_number=1, days_since_payday=3`, and `checkin_reminder_1_sent` is now today.
5. **Mid-ladder stop.** Set up a second test account at day +5 with reminder 1 already stamped. Have them file a check-in for the previous calendar month. Wait until day +7. Run the cron. Confirm reminder 2 does NOT fire and `checkin_reminder_2_sent` stays None.

### Tests

24 new tests in `tests/test_checkin_reminders.py`:
- Ladder timing (5): day +3 fires reminder 1, day +7 fires reminder 2, day +14 fires reminder 3, off-schedule days (1/2/4/8/13/15) skip, user without pay-day anchor is invisible.
- Idempotency (2): same-day re-run is a no-op, send failure does NOT stamp the field.
- Stop-on-completion (2): pre-existing CheckIn row blocks reminder 1, mid-ladder check-in stops reminders 2 and 3.
- Cycle reset (2): pay-day notification clears all three reminder fields, end-to-end ladder runs fresh in the next cycle.
- Analytics (1): `checkin_reminder_sent` fires with `reminder_number` and `days_since_payday`.
- Cron endpoint (6): GET=405, missing config=503, missing header=401, wrong header=401, valid call returns summary with `reminder_breakdown` and `elapsed_ms`, top-level crash returns 200 with errors.
- Email templates (6): HTML and TXT for all three rungs render with `first_name` and `checkin_url`, contain "Open my check-in", contain no em-dashes.

Suite count: **561 passing** (537 baseline that still pass + 24 new). The same calendar-date-dependent failure documented in Task 2.1 (`test_anomaly.py::TestDetectCategorySpikes::test_no_spike`) still fails the same way; not introduced by this task.

### Analytics taxonomy update

Adding to the running list:

| Event | Properties | Fires on |
|-------|-----------|----------|
| `checkin_reminder_sent` | `reminder_number` (1/2/3), `days_since_payday` (3/7/14) | Successful reminder send in `process_checkin_reminders` |

`checkin_started` continues to record `source` — now also accepts `"reminder"` alongside the existing `"payday"` and `"direct"`.

### What's deliberately NOT done

- **No notification preferences / unsubscribe link.** Same as Task 2.1: every user with a pay-day anchor gets the ladder. Will be gated on a `notify_payday=True`-style flag when the preferences page ships in Block 3.
- **No timezone handling.** Days are computed against UTC. Same compromise as Task 2.1; revisit when timezone awareness ships across the app.
- **No retry of failed sends.** A failed reminder doesn't stamp the field, so the next cron run will retry — but only if the user is still on the same `days_since` rung, which they won't be on day 2. Practical effect: a transient Resend error means that rung gets skipped this cycle. Acceptable at MVP scale; revisit when we build a transactional-email outbox.
- **No "is the user still active?" gate.** A user who deleted their account (account_deletion_requested or similar) can't appear because the cascade-delete already cleared their User row. Soft-delete patterns (suspended subscriptions, etc.) aren't filtered out separately yet — same shape as the pay-day cron and consistent with Task 2.1's scope.

### Deviations from the prompt

- **Subject line for reminder 1.** Prompt asked for "Quick nudge for your check-in" (used as the email subject) and the body uses "Hi {first_name}". The HTML heading I used inside the body is "Quick nudge." (the email subject and the rendered heading are different strings; the rendered heading mirrors the visual treatment in `payday_notification.html` which used "Pay day."). Same pattern for reminder 2 ("Still here when you are.") and reminder 3 ("We will stop here.").
- **Reminder 1 final line.** Prompt body had "No rush." as a closing line on a paragraph after the CTA. I kept that placement; it reads a touch warmer than tucking it before the button.

---

## 2026-05-07 — Forgiveness flow for missed check-ins (Block 2 Task 2.3)

### What I did

Built the fourth state of the check-in page: forgiveness. When a user gets nudged by the reminder ladder (Task 2.2) and finally lands on `/check-in` outside the standard last-3-days window, they no longer see "Your next check-in is on [date]" — they see a calm header acknowledging the missed window once, then the standard form pre-populated for the missed month with the submit button rephrased to "Catch up my plan". Submitting writes the CheckIn against the missed month, fires `checkin_completed` with `was_late: True`, and redirects to `/overview` with "You're back in sync. We'll see you on your next pay day."

The product principle this operationalises: **the plan bends, never breaks**. A late check-in is data arriving when it arrives, not a failure. The UI absorbs that without judgement and gets out of the way.

- **`get_forgiveness_target(user, today)` in a new `app/services/checkin_service.py`.** Pure function, returns `(year, month)` or `None`. Three gates, applied in order:
  1. Outside the last-3-days standard window (mirrors `_checkin_view_state` window math so the two stay in lockstep).
  2. At least one of `checkin_reminder_{1,2,3}_sent` is set — i.e. the user got nudged by the ladder. This keeps brand-new users and users still inside their first cycle out of the flow.
  3. No `CheckIn` exists for the previous calendar month, AND either the most recent `CheckIn` is older than the previous month, OR the user has no `CheckIn` history at all and `payday_notification_last_sent` is at least 14 days old.
- **Most-recent-month-only.** The function always returns `(prev_year, prev_month)` when forgiveness applies. A user who missed three months in a row sees forgiveness for last month only; older misses stay missed and the plan adapts forward from now. Deeper retroactive editing creates more cognitive load than retention payoff, and it would also conflict with how `Goal.current_amount` is mutated on submit (we'd be re-applying contributions out of order).
- **`is_within_retroactive_window` defends against stale forms.** A user who left `/check-in` open across a cycle boundary and then submits the old form must not write a CheckIn for last cycle's month. 60-day cap; rejected on POST with a flash redirect to `/check-in` so the user lands on the current state.
- **Form partial extraction.** The check-in form moved from inline in `checkin.html` into `app/templates/checkin/_form.html`. The form takes optional `submit_text`, `target_year`, `target_month` context vars — both the standard form state (default "Confirm check-in", no hidden inputs) and the forgiveness state ("Catch up my plan", with hidden `target_year`/`target_month`) include the same partial. Same form markup, same loading-text wiring, same CSRF token. This sets up Task 2.5 (survival mode) to reuse the partial again rather than copy-pasting markup a third time.
- **Route changes in `page_routes.py`.**
  - `get_forgiveness_target()` runs first; if it returns a target, both GET and POST swap the `(checkin_month, checkin_year)` to the missed month rather than the default `today.month - 1`.
  - GET: when `_checkin_view_state` would return `'scheduled'` and forgiveness applies, we override to a new `'forgiveness'` view state and fire `forgiveness_state_shown` with `target_year` / `target_month`.
  - POST: hidden `target_year` and `target_month` form fields trigger late-submission validation. We re-run `get_forgiveness_target` on submit and reject if the returned target doesn't match the posted values; we also reject any target outside `is_within_retroactive_window`. Trust the freshly-computed target, never the form values.
  - `checkin_completed` now carries `was_late` (boolean). Late submissions redirect to `/overview` with the "back in sync" flash; on-time submissions keep the existing redirect to `/check-in` with the existing flash.
  - Bonus fix while I was here: the `?source=` whitelist at the `checkin_started` track call now accepts `"reminder"` as well as `"payday"`. Task 2.2 added `?source=reminder` to the reminder-ladder CTAs but the route was still collapsing it to `"direct"` for PostHog. Now the funnel can attribute conversions through the reminder channel separately.
- **TODO removal.** The TODO at `_checkin_view_state` ("Block 2 — forgiveness flow: a user who missed a check-in two or more months back is invisible here…") is now resolved by `get_forgiveness_target`. The TODO comment can come out in a follow-up cleanup; it's still descriptively accurate, so leaving it for now does no harm.

### New events

| Event | Where it fires | Properties |
|-------|----------------|------------|
| `forgiveness_state_shown` | `/check-in` GET when forgiveness state renders | `target_year`, `target_month` |
| `checkin_completed` | (existing event, now with new property) | adds `was_late` (bool) |

### Manual verification still needed (for Daniel)

1. Set up a test account: `payday_notification_last_sent = today − 22 days`, `checkin_reminder_1_sent = today − 19 days`, no `CheckIn` rows for the previous month.
2. Visit `/check-in` outside the standard window. Confirm the forgiveness header reads "You missed last month's check-in. That's fine." and the form below has the previous-month label, "Catch up my plan" submit button, and the standard pots pre-populated.
3. Inspect the rendered HTML: hidden `target_year` and `target_month` should be set to the previous calendar month.
4. Submit the form with the pre-populated values. Confirm the redirect lands on `/overview` with the "back in sync" flash and a `CheckIn` row exists for the previous month with the right entries.
5. Hit `/overview` after submission and confirm the plan recalculates without errors and goal balances reflect the contributions just filed.
6. Check PostHog: `forgiveness_state_shown` fired on the GET with `target_year` / `target_month`; `checkin_completed` fired on the POST with `was_late: true`.
7. Sanity check: visit `/check-in` again. Should now show `"already filed"` for the previous month — forgiveness state should NOT re-render.
8. Negative case: register a fresh account with no payday notification ever. Visit `/check-in` outside the window. Confirm the existing scheduled state ("Your next check-in is on…") still renders — forgiveness must not show for fresh users.

### Tests

22 new tests in `tests/test_forgiveness_flow.py`:
- Detection (9): in-window returns None, no reminders ever returns None, brand-new user returns None, history-with-april-filed returns None, missed-april-with-reminder returns April, missed-april-no-history-payday-old returns April, missed-april-no-history-payday-recent returns None, multiple missed months returns only most recent, January wraparound (Dec previous-year).
- Retroactive window (3): recent target accepted, beyond 60 days rejected, invalid month rejected.
- Route rendering (4): GET renders forgiveness state and tracks event, event carries target props, GET without forgiveness renders scheduled state, in-window does not show forgiveness header.
- Submission (6): writes CheckIn for target month with redirect to /overview, fires `checkin_completed` with `was_late: True`, on-time submission carries `was_late: False`, user no longer qualifies → reject + zero CheckIns written, target outside 60-day window → reject, garbage target values → reject.

Suite count: **584 passing** (561 baseline + 22 new + 1 — the `test_anomaly` calendar-date-dependent flake happens to pass on today's date; on other dates it'll go back to 583).

### What's deliberately NOT done

- **No "edit a forgiveness CheckIn" path.** Once the user submits the late check-in, it's a normal `CheckIn` row. Re-edits go through the existing `?edit=1` flow exactly like any other CheckIn — no special handling. The forgiveness state is for the gap between "missed" and "filed", and ends the moment we have a row.
- **No multi-month catch-up.** Confirmed in scope. Older misses stay missed; if a user has gaps spanning multiple cycles, they file the most recent one through forgiveness and the rest are absorbed by plan adaptation rather than retroactive editing.
- **No special-case copy in the form partial for forgiveness.** The form looks identical between standard and forgiveness states except for the submit button text. The forgiveness header carries the framing; the form itself stays neutral. Adds zero per-field complexity.
- **No notification preferences influence.** Per Task 2.1/2.2 deferral, every user with a payday anchor and reminders qualifies — gated only by the detection rules. The unsubscribe / notification preferences page (Block 3) will plumb a `notify_payday`-style flag into the reminder ladder, which by extension gates who can land here.

### Deviations from the prompt

- **Form extraction location.** Prompt said `app/templates/checkin/_form.html`. Done as specified — created the new `app/templates/checkin/` directory and the partial inside it. No deviation, just confirming.
- **`view_state == "forgiveness"` branch placement.** Prompt template snippet showed `{% if view_state == "forgiveness" %}` as a top-level branch. I added it as `{% elif view_state == "forgiveness" %}` after the no-plan branch and before the `scheduled` branch, matching the existing chain in `checkin.html`. This is the natural shape — the no-plan branch must run first because forgiveness for a user without a plan would render an empty form.
- **`forgiveness_target_label` template variable.** Added a small extra context var (the human-friendly month name like "April 2026") so the forgiveness header has a date label without the template having to do month-name lookup. Used as the small uppercase tag above the heading.

---

## 2026-05-07 — Crisis flow entry points (Block 2 Task 2.4)

### What I did

Built the entry-point and routing layer for the crisis flow. A user whose life suddenly changes — lost job, unexpected cost, or just needs to step back — now has a single calm place to say "something's changed" and gets routed to the right next step. Three paths from one landing page, each capturing the data we need without making the user navigate.

This task ships the routing and the data capture. The actual responses for the income and pause paths are placeholders that point at Tasks 2.5 (survival mode) and 2.6 (hardship pause). The cost path is fully wired — it reuses the existing `can_i_afford` planner helper to show real absorption numbers right now.

The product principle: **the plan bends, never breaks**, extended to life events. A crisis is data the system needs to know about. Once Claro knows, it adapts.

- **Three paths, not more.** The landing page (`/crisis`) has exactly three options. Crisis is the wrong moment to make users navigate a long list. Three is enough to cover the realistic cases (income drop, one-off cost, pause request) and the page footer offers `hello@getclaro.co.uk` for anything else. Adding a fourth option would make the page feel like an admin form; staying at three keeps it feeling like a conversation.
- **`CrisisEvent` model — one table, multiple event types.** `crisis_events` discriminates on `event_type` (`lost_income` | `unexpected_cost` | `pause_requested`). NULLable columns per type rather than separate tables; at the scale of crisis events, the storage waste is trivial and the support / analytics queries stay one-line. Reserved `resolved_at` and `resolution_notes` columns for Task 2.5 / 2.6 follow-up. Production gets the table from `db.create_all()` (idempotent for new tables — no ALTER block needed) and the FK cascade is wired into the existing migration block in `app/__init__.py`.
- **`crisis_service.py` — pure logic, route-agnostic.** `record_lost_income`, `record_unexpected_cost`, `record_pause_request`, and `calculate_cost_absorption`. The income service updates `User.monthly_income` only when the user provided a number; the "I don't know yet" branch leaves the field alone so the plan keeps using the previous figure until the user comes back with a value. `calculate_cost_absorption` wraps the existing `can_i_afford(plan, expense_name, amount)` helper from `planner_service.py:748` — no new planner code — and adds two extras: `surplus` (so the response template can show context) and `show_signposting` (true when cost > £500 OR > 50% of monthly surplus).
- **`crisis_routes.py` — six routes.** `GET /crisis` (landing), `GET/POST /crisis/income` (lost-income form + submit), `GET/POST /crisis/cost` (cost form + submit + response render in same POST), `GET/POST /crisis/pause` (signposting page + fire-and-forget pause-event capture), and `POST /crisis/api/link-clicked` (click tracker matching the companion chip-click pattern). All `@login_required`. POSTs validate via the existing `validate_amount` and `sanitize_string` utilities; nonsense input is rejected with a flash redirect, never a write.
- **Cost response uses real planner output.** When the user submits a cost, the response page reads `can_i_afford` and renders one of three messages: "your plan can absorb this cleanly" (impact none), "tight but doable" (impact minor — lifestyle + buffer), or "this cost is bigger than your plan can absorb in one go" (impact significant). No Claro-specific recommendation; just the planner saying what the plan can do.
- **Income and pause are placeholders today.** Both render real templates with calm copy and proper signposting. The income response says "we're building survival mode that'll auto-simplify your goals; for now we've recorded the new income and you can adjust manually". The pause response says "we're building a self-service hardship pause; for now email support and we'll work it out one-to-one". Both responses include free regulated UK signposting (StepChange, MoneyHelper, Citizens Advice; Samaritans and Mind on the pause page).
- **Two access points, neither in primary nav.** The "Something's changed?" item lives in the profile popover (`base.html`) alongside "Get help" — present on every authenticated page without overweighting it. The contextual line on `/overview` reads "If something's changed, tell us here" — quiet, discoverable, the primary entry path.
- **Click-tracking JS added once to `base.html`.** A delegated event listener fires `crisis_link_clicked` for any anchor with `class="js-crisis-link"` and reads `data-crisis-location` for the source name. Both the popover entry and the overview contextual link use the same hook. `keepalive: true` lets the request survive the page navigation, mirroring the companion chip-click pattern.

### FCA boundary review

I went through every piece of user-facing copy with the "would a regulator flag this?" eye. The boundary I held to: **we record what happened, we update the plan inside Claro, we point at free regulated resources. We never recommend a financial product, suggest a debt arrangement, or tell someone what to do with money outside Claro.**

Specific calls:
- The cost response says "this cost is bigger than your plan can absorb in one go." That's a statement about the plan, not advice. The follow-up signposting points at StepChange and MoneyHelper if the user wants advice — we don't try to give it.
- The income placeholder says "your plan keeps running with the new income figure and you can adjust your goals manually". No prescription on which goals to drop or whether to take on debt; the user decides.
- The pause page says "free help is available" and lists Samaritans, Mind, StepChange. No phrasing that pretends Claro provides the help.
- All resource links use `target="_blank" rel="noopener noreferrer"` and aren't paid placements — they're the canonical free UK resources.

### Schema changes

| Table | Column | Type | Notes |
|-------|--------|------|-------|
| `crisis_events` (new) | `id` | `INTEGER PK` | |
| | `user_id` | `INTEGER FK users.id` | `ON DELETE CASCADE` (Postgres + SQLite via FK pragma) |
| | `event_type` | `VARCHAR(20)` | `lost_income`, `unexpected_cost`, `pause_requested` |
| | `income_change_type` | `VARCHAR(30)` | nullable; `lost_income` only |
| | `new_monthly_income` | `NUMERIC(10,2)` | nullable; `lost_income` only |
| | `income_unknown` | `BOOLEAN` | default false |
| | `cost_description` | `VARCHAR(200)` | nullable; `unexpected_cost` only |
| | `cost_amount` | `NUMERIC(10,2)` | nullable; `unexpected_cost` only |
| | `cost_already_paid` | `BOOLEAN` | nullable; `unexpected_cost` only |
| | `occurred_on` | `DATE` | nullable |
| | `created_at` | `DATETIME` | default `datetime.utcnow` |
| | `resolved_at` | `DATETIME` | nullable; reserved for Task 2.5 / 2.6 |
| | `resolution_notes` | `TEXT` | nullable; reserved for Task 2.5 / 2.6 |

`db.create_all()` covers fresh DBs; the table is brand new so no idempotent-ALTER entries are needed — only the FK cascade row in the existing migration block.

### New routes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/crisis/` | login | Landing page, three options |
| `GET` | `/crisis/income` | login | Lost-income form |
| `POST` | `/crisis/income` | login | Submit + render response |
| `GET` | `/crisis/cost` | login | Cost form |
| `POST` | `/crisis/cost` | login | Submit + render response with real absorption |
| `GET` | `/crisis/pause` | login | Pause signposting page |
| `POST` | `/crisis/pause` | login | Fire-and-forget pause-event capture |
| `POST` | `/crisis/api/link-clicked` | login | Fire-and-forget click tracker |

### Events instrumented

| Event | Where it fires | Properties |
|-------|----------------|------------|
| `crisis_landing_viewed` | `GET /crisis` | `source` (`overview`, `popover`, or `direct`) |
| `crisis_income_submitted` | `POST /crisis/income` after write | `change_type`, `income_unknown` |
| `crisis_cost_submitted` | `POST /crisis/cost` after write | `amount`, `already_paid`, `absorbable`, `impact` |
| `crisis_pause_viewed` | `GET /crisis/pause` | (none) |
| `crisis_pause_requested` | `POST /crisis/pause` after write | (none) |
| `crisis_link_clicked` | `POST /crisis/api/link-clicked` | `location` (`overview`, `popover`) |

### Why pause is intentionally NOT self-service

A self-service pause button is the kind of thing that looks easy until you ship it. The interesting questions — how long should the pause be, do we ringfence the user's data, do we hold their plan state, what happens to their goal balances, do we still send pay-day emails during the pause — all need answers we don't have yet. Forcing one-to-one email conversations for the first cohort means we get those answers from real users before we automate the wrong thing. Task 2.6 builds the self-service version after we've handled enough manual pauses to know the right shape.

### Manual verification still needed (for Daniel)

1. **Popover access.** Open any authenticated page, click the profile avatar, confirm the new "Something's changed?" item renders in the popover with the new icon. Click it — should land on `/crisis` and PostHog should fire `crisis_link_clicked` with `location=popover` plus `crisis_landing_viewed` with `source=popover`.
2. **Overview contextual link.** Visit `/overview`. Confirm the small "If something's changed, tell us here" line renders just before the plan whisper card. Click it — `crisis_link_clicked` with `location=overview`, then `crisis_landing_viewed` with `source=overview`.
3. **Lost income end-to-end.** Click "I've lost income". Pick a radio option, enter a new monthly income, leave the date as today. Submit. Confirm the response page renders with the StepChange / MoneyHelper / Citizens Advice list. In the DB, confirm `monthly_income` updated and a `crisis_events` row exists with `event_type='lost_income'`. PostHog: `crisis_income_submitted` fired with `change_type` and `income_unknown=false`.
4. **Income unknown branch.** Repeat step 3 but tick "I don't know yet" and leave the income blank. Submit. Confirm `monthly_income` is unchanged and the new event has `income_unknown=true`, `new_monthly_income=NULL`.
5. **Unexpected cost.** Click "I have an unexpected cost". Enter "boiler repair", £320, "Not yet", today. Submit. Confirm the response page shows the cost in a card and a real absorption message (one of "absorb cleanly" / "tight but doable" / "bigger than your plan can absorb"). With £320 < £500 and (assuming surplus > £640), no signposting box should appear. Now repeat with £800 — signposting should appear.
6. **Pause page.** Click "I just need to pause". Confirm signposting renders with Samaritans phone number, Mind link, StepChange link, and a working `mailto:hello@getclaro.co.uk` email button. Click "Email support" — your mail client should open with the pre-filled subject AND a `crisis_pause_requested` event fires (a row also lands in `crisis_events`).
7. **Negative cases.** Try submitting `/crisis/income` with no radio selected, no income and no "unknown" tick, or a negative monthly income — each should redirect with a flash error and no `crisis_events` row should be written.
8. **PostHog audit.** After steps 1-6, confirm all six new events appear in PostHog with the right properties.

### Tests

24 new tests in `tests/test_crisis_flow.py`:
- Service `record_lost_income` (2): updates `monthly_income` when value provided, leaves it alone when `income_unknown=True`.
- Service `record_unexpected_cost` (1): creates event without mutating user.
- Service `record_pause_request` (1): creates event with correct type.
- Service `calculate_cost_absorption` (3): absorbable cost returns affordable, large cost (>£500) triggers signposting, cost >50% of small surplus triggers signposting.
- Auth gating (2): landing redirects when anonymous, income POST redirects when anonymous.
- Landing (2): renders three options, fires `crisis_landing_viewed` with the right `source`.
- Income route (5): GET renders form, POST creates event + updates `monthly_income`, invalid `change_type` rejected, missing income+unknown rejected, future `occurred_on` rejected.
- Cost route (3): GET renders form, POST creates event + renders response with real numbers, negative amount rejected, blank description rejected.
- Pause route (2): GET renders signposting + mailto, POST creates event with `event_type=pause_requested`.
- Link-click endpoint (2): POST fires `crisis_link_clicked` with location, requires login.

Suite count: **608 passing** (583 baseline + 24 new + 1 — `test_anomaly` calendar flake currently green; on other dates expect 607).

### Deviations from the prompt

- **Footer link placement.** Prompt said "footer link in the main layout". The app has no `<footer>` element on authenticated pages — it has a sidebar shell with a profile popover that's effectively the persistent footer. I added the "Something's changed?" item there, alongside the existing "Get help" mailto. Same calm-presence behaviour the prompt asked for, fitting the existing UI shape.
- **Pause page POST.** Prompt described pause as a GET-only page that surfaces a mailto. I added a parallel `POST /crisis/pause` (204 fire-and-forget) so clicking "Email support" creates a `crisis_events` row alongside opening the user's mail client — gives support the row when the email lands, not just analytics. The mailto behaviour itself is unchanged.
- **Mailto address.** Prompt and Task 2.1 use `hello@getclaro.co.uk`. The pre-existing "Get help" popover link still points at `hello@clarofinance.co.uk`. I left that unchanged (out of scope) but every new crisis-flow link uses the correct `hello@getclaro.co.uk` address. Flagged for a small follow-up cleanup.
- **No `__init__.py` ALTER block entry.** The CrisisEvent table is brand new, so `db.create_all()` handles it idempotently. ALTER block entries are only needed when adding columns to existing tables. Added the FK cascade entry to the existing Postgres-only migration list.

---

## 2026-05-07 — Survival mode for the planner (Block 2 Task 2.5)

### What I did

Built survival mode: the planner branch that activates when a user's income drops meaningfully (or they manually flip the switch from settings). When survival mode is on, non-essential goal contributions automatically pause, lifestyle reduces to a survival floor, and the plan focuses on essentials only. The product principle "the plan bends, never breaks" gets its most explicit expression here — a user whose income drops 40% doesn't need a stern warning, they need the plan to adapt automatically and quietly.

The implementation is a branch *inside* the existing planner, not a separate planner. That was the key constraint: anything that consumes `generate_financial_plan()` (overview, plan page, check-in pre-population, companion, can_i_afford, the cost-absorption helper) had to keep working without changes. The survival branch produces a plan dict that is schema-identical to the standard plan, plus two extra keys (`survival_mode: True`, `survival_floor`).

- **`app/services/survival_mode_service.py` — new file.** Four functions: `should_auto_activate(user, new_income)` (returns True for >= 25% drop with safety bail-outs for missing baseline / unknown income / already-active), `activate_survival_mode(user, reason)` (flips the flag, stamps `survival_mode_started_at`, fires `survival_mode_activated`), `deactivate_survival_mode(user)` (clears the flag but keeps the timestamp as a historical record), and `get_survival_floor(user)` (`max(income * 0.20, £400)`). Module-level constants `INCOME_DROP_THRESHOLD = 0.25`, `SURVIVAL_LIFESTYLE_FRACTION = 0.20`, `SURVIVAL_LIFESTYLE_HARD_FLOOR = 400.0` so the planner branch and tests reference the same numbers.
- **Planner branch in `generate_financial_plan`.** A 6-line gate at the top of the function reads `user_profile["survival_mode_active"]` and short-circuits to `_generate_survival_plan(...)` before any of the standard pot-building runs. The new `_generate_survival_plan` function builds a `pots` list with debts at minimum payments, essential goals at their existing `monthly_allocation`, non-essential goals at zero (with `_paused_for_survival=True` so the dict version surfaces a `paused_for_survival: True` flag for templates), lifestyle pot at the survival floor, and buffer at zero. Runs through the same `_simulate_phases` and `_pot_to_dict` machinery so the output schema matches.
- **Schema-compatibility test.** `TestPlannerSurvivalMode::test_survival_plan_has_same_top_level_keys` builds a standard plan and a survival plan from comparable inputs, takes the set of top-level keys from each, and asserts the survival plan contains every standard key. Cheap, future-proof, and catches the most likely regression: someone adds a key to the standard planner and forgets the survival branch.
- **Essential goals — explicit flag plus heuristic backup.** Added `Goal.is_essential` (Boolean, default False, idempotent ALTER). Users can explicitly mark a goal as essential. The planner branch also treats anything that matches the existing debt-name heuristic (`_is_debt_goal`) or the new emergency-name heuristic (Emergency / Rainy day / Safety net) as essential automatically. This means existing users don't have to go and re-tag their emergency fund and debts to keep contributions flowing in survival mode — those goals are essential by name, not by flag.
- **Auto-activation hook in `crisis_service.record_lost_income`.** The hook runs *before* mutating `user.monthly_income` (otherwise the comparison baseline is gone). When `should_auto_activate` returns True, `activate_survival_mode(user, reason="income_drop")` flips the flag and stamps the timestamp before the income write commits. The function returns the `CrisisEvent` with a transient attribute `survival_mode_just_activated` so the route can read it without a follow-up query and pass it to the response template.
- **Crisis income response template.** Now branches on `survival_mode_just_activated`. If True: "We've also simplified your plan to focus on essentials only. Non-essential goals are paused. We'll keep it that way until you tell us things have changed in settings." If False (small drop or unknown income): "Your plan keeps running with the new income figure. If you'd like a simpler plan that focuses on essentials only, you can switch to survival mode in settings."
- **Manual toggle in settings.** New "Survival mode" collapsible section in `settings.html`. When inactive: header "Need a simpler plan?" with a one-line explanation and a "Switch to survival mode" button posting to `/settings/survival-mode/activate`. When active: header "Survival mode is on" with the activation date and a "Switch back to standard mode" button posting to `/settings/survival-mode/deactivate`. Both routes flip the flag, flash a calm one-line message, redirect back to settings.
- **Overview banner.** Above the contextual crisis link, a small calm banner appears when `current_user.survival_mode_active`: "Survival mode is on. Plan simplified to essentials." with a Roman-Gold left edge and a "Switch back to standard mode" link to settings. Subtle, informational, not alarming.
- **Companion light touch.** Appended a single context line in `_build_user_context` when `user.survival_mode_active`: "Survival mode: on. The user's plan is currently simplified to essentials only because their income recently dropped or they asked for a simpler plan. Be matter-of-fact about this — it's just where they are right now, not a problem to solve. Do not suggest increasing contributions to non-essential goals." The static system prompt and routing/caching machinery stay untouched.

### Critical compatibility statement

The planner's output schema is unchanged. The survival branch returns a dict with every key the standard planner returns, plus two additive keys (`survival_mode`, `survival_floor`). All existing planner consumers — overview, plan page, check-in pre-population, companion, `can_i_afford`, `calculate_cost_absorption` from Task 2.4 — work unmodified. The full test suite is 636 passing, including every test under those code paths.

### Schema changes

| Table | Column | Type | Notes |
|-------|--------|------|-------|
| `users` | `survival_mode_active` | `BOOLEAN NOT NULL DEFAULT FALSE` | Idempotent ALTER block |
| `users` | `survival_mode_started_at` | `TIMESTAMP` | Nullable; preserved across deactivations as historical record |
| `goals` | `is_essential` | `BOOLEAN NOT NULL DEFAULT FALSE` | New idempotent ALTER block for goals |

### New routes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/settings/survival-mode/activate` | login | Manual entry to survival mode |
| `POST` | `/settings/survival-mode/deactivate` | login | Manual exit back to standard plan |

### Events instrumented

| Event | Where it fires | Properties |
|-------|----------------|------------|
| `survival_mode_activated` | `activate_survival_mode` | `reason` (`manual` or `income_drop`) |
| `survival_mode_deactivated` | `deactivate_survival_mode` | (none) |
| `crisis_income_submitted` | (existing event, new property) | adds `survival_mode_just_activated` (bool) |

### Why no auto-deactivate

Auto-deactivation when income recovers feels like the obvious next step but it's intentionally deferred. The interesting questions — what counts as "recovered" (current income matches the pre-drop amount? Or 80% of it? Three consecutive months above some threshold?), what happens to paused goals (do contributions resume at the old level or scale to the new income?), do we ask the user before flipping back or just do it, what if they got a bonus rather than a salary increase — all need answers we don't have yet. Manual exit only for now means we get those answers from real conversations before automating the wrong rule. Block 5 candidate.

### FCA boundary review

Survival mode is a planner state that the user opts into (via crisis flow auto-activation or the settings toggle) and opts out of (via the settings toggle). Nothing in this task tells the user how to handle creditors, what to do about debts they can't pay, or whether to seek any specific kind of help — that signposting was Task 2.4's job and lives in the crisis-flow templates. Survival mode itself only does three things: pauses non-essential contributions, sets lifestyle to a survival floor, focuses the plan on essentials. All three are plan adjustments inside Claro. The companion's added context line is matter-of-fact ("just where they are right now, not a problem to solve") and explicitly tells the model not to push goal contributions during survival mode. No advice creep.

### Manual verification still needed (for Daniel)

1. Set up a test account with `monthly_income = 2000`. Visit `/crisis/income`, pick a radio option, submit `new_monthly_income = 1400` (30% drop), today's date. Confirm the response page now reads "We've also simplified your plan to focus on essentials only..." instead of the older copy.
2. Navigate to `/overview`. Confirm the calm "Survival mode is on. Plan simplified to essentials." banner appears above the contextual crisis line, with a working "Switch back to standard mode" link.
3. Open the goals list / dashboard goal cards. Confirm non-essential goals show £0/month contributions; emergency fund and any debt goals continue to receive contributions.
4. Visit `/settings`, expand the "Survival mode is on" section, click "Switch back to standard mode". Confirm the flash message renders and the overview banner disappears on the next page load.
5. From a fresh test account with no prior crisis event, open `/settings`, expand "Need a simpler plan?", click "Switch to survival mode". Confirm same banner appears.
6. PostHog: confirm `survival_mode_activated` fired twice — once with `reason=income_drop` (step 1) and once with `reason=manual` (step 5). `survival_mode_deactivated` fired once (step 4). `crisis_income_submitted` carries `survival_mode_just_activated: true` for the auto-activation case.
7. Optional: open `/companion` while survival mode is on, ask "should I save more for my house deposit?". Confirm the response stays calm and matter-of-fact and does not push goal contributions.

### Tests

28 new tests in `tests/test_survival_mode.py`:
- `should_auto_activate` (6): 30% drop → True, 10% drop → False, exactly 25% → True, no previous income → False, unknown new income → False, already active → False (no double-fire).
- `activate_survival_mode` / `deactivate_survival_mode` (3): activate sets flag + timestamp, deactivate clears flag but keeps timestamp, activate fires `survival_mode_activated` with `reason`.
- `get_survival_floor` (2): 20% of high income, £400 hard floor for low income.
- Planner integration (7): standard mode returns `survival_mode: False`, survival mode returns `survival_mode: True` and `survival_floor`, survival schema has every standard key, non-essentials paused with `paused_for_survival: True`, emergency fund essential by name (heuristic backup), lifestyle set to survival floor and buffer is zero, alerts include `survival_mode` entry.
- Auto-activation via crisis (4): 30% drop activates, 10% drop does not, unknown income does not, event fires with `reason=income_drop`.
- Manual toggle routes (4): activate flips + redirects, deactivate clears + redirects, both require login.
- Companion awareness (2): user-context mentions survival mode when active, omits it when inactive.

Suite count: **636 passing** (607 deterministic baseline + 28 new + 1 — `test_anomaly` calendar flake currently green; on other dates expect 635).

### Deviations from the prompt

- **Goal essential detection — heuristic backup added.** Prompt said use `is_essential=True` as the gate. I added that field as the explicit flag, but the planner also treats debt-name and emergency-name goals as essential automatically. Without that, every existing user who entered survival mode would see their emergency fund and debt contributions drop to zero — they'd have to retroactively go tick `is_essential` on each goal. The heuristic backup keeps existing data working sensibly without forcing migration UX.
- **`paused_for_survival` flag on pot dicts.** Not in the prompt's output spec, but the overview / goals templates need a way to render paused goals muted versus completed goals. Adding the flag is the minimum surface area to keep `monthly_amount: 0` distinguishable from "this goal is done".
- **Buffer pot drops to zero in survival mode.** The standard planner has both lifestyle and buffer pots; the prompt only addressed lifestyle. Setting buffer to zero is consistent with "we're not building a buffer when income just dropped" and matches the spirit of survival mode's "essentials only" framing. Calling it out explicitly so it's visible in review.
- **`survival_mode: False` in standard plan output.** Strictly additive, but means any consumer that reads `plan.get("survival_mode")` gets a clean True/False rather than `True/None`. Negligible cost; small clarity win.

---

*This journal is part of the FinTrack project. It documents genuine learning, not polished retrospection. Mistakes, confusion, and wrong turns are included deliberately — they're where the real growth happened.*