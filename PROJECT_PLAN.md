# FinTrack — Project Plan

---

## 1. Problem Statement

Approximately 63% of UK adults report low confidence in managing their finances. Many of these individuals are intelligent and responsible, yet they make daily financial decisions without understanding their long-term consequences over 2, 5, or 10 years.

Current solutions fall into two categories:

**1. Banking apps and budgeting tools**
- Track historical spending
- Retrospective and passive
- Provide data without meaningful insight

**2. Financial advisors**
- Provide forward-looking financial planning
- Typically only accessible to high-net-worth individuals due to fees and minimum asset requirements

### Market Gap

Young professionals aged 22–35 earning approximately £25,000–£60,000 per year are underserved.

Typical characteristics:
- Renting accommodation
- Paying into pension schemes they do not fully understand
- Attempting to save for a home
- Regularly spending on convenience services without recognising long-term impact

**Example:** Spending £340/month on food delivery may feel harmless in the present but represents tens of thousands of pounds over a decade when accounting for opportunity cost and investment growth.

FinTrack aims to make these hidden costs visible.

---

## 2. Core Insight

People rarely change financial behaviour because they lack information. They change behaviour when they **viscerally understand the consequences** of their choices.

FinTrack's mission is to:
- Make financial trade-offs visible
- Present spending consequences clearly
- Deliver insights that are personal and emotionally meaningful

Existing tools tend to be:
- Tedious (manual spreadsheets)
- Bloated with unused features
- Locked behind premium paywalls

FinTrack focuses on delivering simple, intelligent insights without unnecessary complexity.

### Regulatory Position

FinTrack operates entirely within the **unregulated financial guidance space**. It presents data-driven projections and educational information only. It never makes personal recommendations on specific financial products. Product mentions (e.g. LISA) are framed as generic educational information with explicit signposting to regulated advice. No FCA authorisation is required at launch.

The boundary: the system never says "you should put your money into X product." It says "based on your data, here is what your future looks like." That is guidance, not advice.

---

## 3. MVP (v1.0)

### Objective

Launch a functional prototype quickly to validate the core concept.

### Features

- User registration and login (email + password)
- User-scoped data — every transaction belongs to a specific user
- Manual transaction entry via web form
- View transactions in a list
- Delete transactions
- Persistent storage using SQLite
- Display total spending on dashboard
- Deployed and accessible via public URL

### What is NOT in v1.0

- No goals system (v2)
- No categories table / normalisation (v2)
- No ML or auto-categorisation (v3)
- No simulator or projections (v3)
- No charts or data visualisation (v4)
- No budgets or anomaly detection (v4)
- No payments or subscription tiers (v5)
- No chatbot (v5)

### Design Principle

Even at MVP stage, features should support the core insight: helping users understand how daily spending affects their long-term finances. The dashboard total is the first step — seeing the raw number of how much you've spent is the simplest version of awareness.

### MVP Success Metrics

- Number of users registering accounts
- Frequency of transaction logging
- Qualitative feedback indicating improved awareness of spending behaviour

---

## 4. Version Roadmap

Each version is a git tag. Each builds on the previous. Never skip ahead.

### v1.0 — Foundation + Auth (Weeks 1–2)

- User registration, login, logout
- Transaction CRUD (create, read, delete)
- User-scoped data (user_id FK on every transaction)
- Basic dashboard with totals
- SQLite database
- Deployed to Render

### v2.0 — Analytics + Goals (Week 3)

- Service layer extracted (routes thin, services thick)
- Categories table with normalised foreign keys
- Goals system (target amount, deadline, priority ranking)
- Fact-find questionnaire at onboarding
- Analytics: spending by category, monthly summary
- Filtering and sorting on transaction list

### v3.0 — Simulator + ML Intelligence (Weeks 4–5)

- Financial consequence simulator (5/10/20-year projections)
- Scenario modelling ("what if I saved £200 more?")
- ML auto-categorisation (TF-IDF + Naive Bayes)
- Data pipeline layer (validation, cleaning, feature engineering)
- Spending prediction model (Linear Regression)
- Recurring transaction detection algorithm
- Logging system

### v4.0 — Proactive Intelligence (Week 6)

- Proactive nudge system (anticipatory spending alerts)
- Budget tracking with alert thresholds
- Anomaly detection (Z-Score + Isolation Forest)
- CSV import for bank statements
- Chart.js data visualisations
- Rate limiting on API endpoints

### v5.0 — Subscription + Chatbot + Launch (Weeks 7–9)

- Stripe integration (14-day free trial, Core £7.99/month, Plus £12.99/month)
- Feature gating by subscription tier
- Financial companion chatbot (Plus only, Anthropic API)
- System prompt with compliance guardrails
- Comprehensive test suite (80%+ coverage)
- CI/CD pipeline via GitHub Actions
- PostgreSQL migration for production
- Full documentation suite
- ETHICS_AND_COMPLIANCE.md

### v6.0+ — Growth Features (Post-Launch)

- React frontend rebuild
- Open banking sync (TrueLayer)
- Couples/household finance mode
- Mortgage readiness tool
- Salary progression modelling
- SMS nudge delivery

---

## 5. Tech Stack Decisions

Every choice has a reason. These are documented so they can be explained and defended.

### Backend Framework: Flask

**Chosen over:** Django, FastAPI

**Reasoning:**
- Lightweight and flexible — does not impose structure, allowing architectural decisions to be deliberate
- Large ecosystem with well-documented extensions (Flask-Login, Flask-Bcrypt, Flask-Limiter)
- Industry standard for Python APIs and small-to-medium applications
- Django was rejected because it is too opinionated and heavy for this project's learning goals — its built-in features (admin panel, ORM, auth) would hide the engineering decisions that are the point of building this
- FastAPI was rejected because async adds complexity without solving a real problem at this scale

**Scaling position:** Flask behind gunicorn with a PostgreSQL database is sufficient for the foreseeable scale of this application. Framework migration would be evaluated only if specific performance bottlenecks are identified through real usage data. There is no planned migration to another framework.

### Database: SQLite → PostgreSQL

**Development (v1–v4):** SQLite
- Zero configuration — no server setup required
- File-based — portable, easy to reset during development
- Perfect for rapid iteration and learning

**Production (v5+):** PostgreSQL
- Strong concurrency support for multiple users
- Advanced query capabilities
- Production-grade reliability and scalability
- Required by deployment platforms (Render PostgreSQL addon)

**Migration strategy:** SQLAlchemy abstracts the database connection, so switching from SQLite to PostgreSQL requires changing only the connection string in config.py. Alembic handles schema migrations from v3 onwards.

### ORM: SQLAlchemy

**Chosen over:** Raw SQL

**Reasoning:**
- Pythonic interaction with the database
- Database-agnostic — the same model code works with SQLite and PostgreSQL
- Industry standard with excellent documentation
- Prevents SQL injection by parameterising all queries automatically
- Alembic integration for versioned schema migrations
- Development configuration: `echo=True` to log generated SQL for learning

**Trade-off acknowledged:** ORMs hide the underlying SQL. To mitigate this, echo mode is enabled during development so every generated query is visible in the console.

### Frontend: Jinja2 → React (v6+)

**v1–v5:** Jinja2 server-side templates
- Native integration with Flask
- Rapid development — full-stack in one codebase
- Simpler deployment
- Faster to ship MVP

**v6+:** React (planned, not committed)
- Component-based architecture for complex UI
- Better interactivity for simulator and chatbot
- Separate frontend enables mobile app later

**Architectural decision:** The Flask backend is built as a proper REST API from day one. Jinja2 templates are a temporary skin. The API is permanent. This means React can replace the templates without touching any backend code.

### Data Visualisation: Chart.js

- Interactive browser-based charts
- Responsive and mobile-friendly
- Easy integration with Flask via JSON data
- Workflow: Flask generates data → passes as JSON to template → Chart.js renders in browser

### Machine Learning: scikit-learn + pandas

**Chosen over:** TensorFlow, PyTorch

**Reasoning:**
- Lightweight and well-tested
- Ideal for structured financial data
- Sufficient for the ML tasks in this product: classification (categorisation), regression (spending prediction), anomaly detection
- Deep learning frameworks would be overkill — the dataset is tabular, not images or natural language requiring neural networks
- Easier to interpret and explain model decisions

### Authentication: Flask-Login + Flask-Bcrypt

- Flask-Login handles session management and the @login_required decorator
- Flask-Bcrypt handles password hashing (never store plaintext passwords)
- Simple, well-documented, sufficient for the application's needs

### Payments: Stripe

- Industry standard for subscription billing
- No monthly fee — charges per transaction only (1.4% + 20p for UK cards)
- Excellent Python SDK and documentation
- Handles all card data — FinTrack never touches payment details directly
- Webhook system for event-driven subscription management

### Chatbot: Anthropic API (Claude)

- Strong safety guardrails — critical for a financial product where regulatory compliance matters
- Context injection model works well for personalised financial dialogue
- The system prompt defines hard compliance boundaries that prevent regulated advice

### Testing: pytest

- Industry standard for Python testing
- Clean syntax with fixtures and parametrisation
- pytest-cov for coverage measurement
- Integrates with GitHub Actions for CI/CD

### CI/CD: GitHub Actions

- Free for public and private repositories
- 2,000 free minutes per month
- Runs test suite on every push
- Badge on README shows test status at a glance

### Deployment: Render

- Free tier for initial development
- Git auto-deploy from main branch
- PostgreSQL addon for production database
- Simple configuration — no DevOps expertise required

---

## 6. API Design

### v1.0 Endpoints

All transaction endpoints require authentication.

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| POST | /api/auth/register | Create account | No |
| POST | /api/auth/login | Log in | No |
| POST | /api/auth/logout | Log out | Yes |
| POST | /api/transactions | Create transaction | Yes |
| GET | /api/transactions | List user's transactions | Yes |
| GET | /api/transactions/{id} | Get single transaction | Yes |
| DELETE | /api/transactions/{id} | Delete transaction | Yes |

**Deferred to v2:** PUT /api/transactions/{id} (update). In v1, users delete and re-add to correct mistakes. This is a deliberate MVP scope decision — update functionality adds complexity without changing core value.

### v2.0 Endpoints (Added)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| PUT | /api/transactions/{id} | Update transaction |
| POST | /api/goals | Create financial goal |
| GET | /api/goals | List goals with progress |
| PUT | /api/goals/{id} | Update goal |
| DELETE | /api/goals/{id} | Delete goal |
| POST | /api/onboarding/fact-find | Submit questionnaire |
| GET | /api/analytics/spending-by-category | Category breakdown |
| GET | /api/analytics/monthly-summary | Monthly totals |

### v3.0 Endpoints (Added)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/simulator/projection | 5/10/20-year projection |
| POST | /api/simulator/scenario | Run what-if scenario |
| GET | /api/analytics/recurring | Detected subscriptions |
| GET | /api/analytics/predictions | Spending forecast |

### v4.0 Endpoints (Added)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /api/transactions/import | CSV upload |
| POST | /api/budgets | Set category budget |
| GET | /api/budgets/status | Budget vs actual |
| GET | /api/analytics/anomalies | Flagged transactions |

### v5.0 Endpoints (Added)

| Method | Endpoint | Purpose | Tier |
|--------|----------|---------|------|
| POST | /api/chatbot/message | Send message to companion | Plus only |
| GET | /api/chatbot/history | Get conversation history | Plus only |
| POST | /api/billing/create-checkout | Start Stripe checkout | All |
| POST | /api/billing/webhook | Stripe event handler | System |
| GET | /api/billing/status | Check subscription | All |
| POST | /api/billing/cancel | Cancel subscription | All |

---

## 7. Database Schema

### 7.1 Users Table

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, Auto-increment | Unique identifier |
| email | String(255) | UNIQUE, NOT NULL | Login credential and contact |
| password_hash | String(255) | NOT NULL | Bcrypt hashed password — NEVER store plaintext |
| name | String(100) | NOT NULL | Display name |
| income | Decimal(10,2) | NULLABLE | Monthly income (from fact-find, added in v2) |
| subscription_tier | String(10) | Default: 'trial' | trial / core / plus / expired |
| trial_start | DateTime | NULLABLE | When 14-day trial began |
| stripe_customer_id | String(255) | NULLABLE | Stripe customer reference |
| notification_prefs | JSON | Default: {} | Email/push/SMS preferences |
| created_at | DateTime | Default: now() | Registration date |

**Notes:**
- password_hash stores the bcrypt output, never the plaintext password
- subscription_tier defaults to 'trial' at registration — trial logic checks trial_start + 14 days
- income, stripe_customer_id, and notification_prefs are NULLABLE because they are not needed at registration but are populated by later features
- The users table is the foundation — every other table references it via user_id

### 7.2 Transactions Table

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, Auto-increment | Unique identifier |
| user_id | Integer | FK → users.id, NOT NULL | **Links transaction to its owner — critical for data isolation** |
| amount | Decimal(10,2) | NOT NULL | Transaction value — NEVER use Float |
| description | String(255) | NOT NULL | What was purchased — ML uses this for categorisation |
| category | String(50) | NOT NULL | Plain text in v1 — becomes category_id FK in v2 |
| type | String(10) | NOT NULL | 'income' or 'expense' |
| date | Date | NOT NULL, INDEXED | When the transaction occurred |
| merchant | String(255) | NULLABLE | Who was paid — used for recurring detection |
| is_recurring | Boolean | Default: False | Flagged by recurring detection algorithm (v3) |
| created_at | DateTime | Default: now() | When added to system |
| updated_at | DateTime | Auto-update | Last modification |

**Critical design decisions:**
- **user_id** is NOT NULL and has a foreign key constraint. Every query against this table MUST filter by user_id to ensure users only see their own data. Forgetting this would be a security vulnerability.
- **amount** uses Decimal(10,2), never Float. Floating point arithmetic has rounding errors (0.1 + 0.2 = 0.30000000000000004). Financial calculations require precision.
- **category** is plain text in v1 for simplicity. In v2 it becomes category_id (Integer, FK → categories.id) when the categories table is introduced. This is a deliberate choice: ship v1 fast with the simpler approach, normalise in v2.
- **date** is indexed because analytics queries (monthly summary, category breakdown) filter by date range frequently.

### 7.3 Categories Table (v2)

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK | Category identifier |
| name | String(50) | UNIQUE, NOT NULL | Category name (Food, Transport, etc.) |
| icon | String(10) | NULLABLE | Emoji or icon code for UI |
| colour | String(7) | NULLABLE | Hex colour for charts (#FF5733) |

**Why normalise categories:**
Instead of storing "Food" as text in every transaction, store category_id = 1 which references the categories table. If you later rename "Food" to "Groceries", you change it once in categories, not in thousands of transactions. This is database normalisation — a fundamental data integrity principle.

**Default categories seeded at setup:** Food, Transport, Bills, Entertainment, Shopping, Income, Other.

### 7.4 Goals Table (v2)

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK | Unique identifier |
| user_id | Integer | FK → users.id, NOT NULL | Which user owns this goal |
| type | String(20) | NOT NULL | savings / debt_payoff / spending_limit |
| description | String(255) | NOT NULL | e.g. "House deposit", "Clear credit card" |
| target_amount | Decimal(10,2) | NOT NULL | How much they need to reach |
| current_amount | Decimal(10,2) | Default: 0 | Progress tracked manually or via sync |
| deadline | Date | NULLABLE | Target completion date |
| priority_rank | Integer | Default: 1 | User-ranked importance (1 = highest) |
| created_at | DateTime | Default: now() | When the goal was created |

**Why this table matters:**
The financial consequence simulator (v3) projects against these goals. Without goals, the simulator has nothing to answer — "on track for what?" Goals also drive the proactive nudge system (v4) — "you're £340 from your house deposit milestone" only works if the milestone is defined.

**Design decisions:**
- **type** distinguishes between saving toward something, paying off debt, and limiting spending — each requires different projection logic
- **priority_rank** lets users order their goals by importance, which affects how the simulator allocates reallocation suggestions
- **deadline** is NULLABLE because some goals (e.g. "build emergency fund") don't have a fixed date

### 7.5 Budgets Table (v4)

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK | Unique identifier |
| category_id | Integer | FK → categories.id | Budget category |
| amount | Decimal(10,2) | NOT NULL | Monthly spending limit |
| month | Integer | 1–12 | Budget month |
| year | Integer | NOT NULL | Budget year |

### 7.6 Anomalies Table (v4)

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK | Unique identifier |
| transaction_id | Integer | FK → transactions.id | Flagged transaction |
| reason | String(255) | NOT NULL | Why it was flagged |
| severity | String(10) | NOT NULL | low / medium / high |
| flagged_at | DateTime | Default: now() | When detected |

### 7.7 Additional Tables (v5)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| projections | Cached simulator output | user_id, horizon, data (JSON), generated_at |
| conversations | Chatbot message history | user_id, role, content, created_at |
| subscriptions | Stripe subscription state | user_id, stripe_sub_id, tier, status, current_period_end |
| nudge_log | Sent nudge records | user_id, type, content, sent_at |
| priority_categories | User priority rankings | user_id, category_id, level (essential/flexible/discretionary) |

---

## 8. Schema Evolution Plan

| Version | Tables Added / Changed | Why Now |
|---------|----------------------|---------|
| v1.0 | users, transactions (category as plain text) | Auth + basic storage |
| v2.0 | + categories (normalised), + goals, transactions.category → category_id FK | Analytics need categories; simulator needs goals |
| v3.0 | + projections, + priority_categories | Simulator caches output; fact-find stores priorities |
| v4.0 | + budgets, + anomalies, + nudge_log | Budget tracking, anomaly detection, proactive nudges |
| v5.0 | + subscriptions, + conversations. PostgreSQL migration. | Stripe integration, chatbot history, production readiness |

---

## 9. Security & Privacy Considerations

Since financial data is involved, security is a first-class concern at every stage.

- **Authentication:** Bcrypt password hashing. Flask-Login session management. @login_required on all protected routes.
- **Data isolation:** Every database query scoped by user_id. Users must never see another user's data.
- **SQL injection:** Prevented by SQLAlchemy parameterised queries.
- **XSS:** Prevented by Jinja2 auto-escaping.
- **CSRF:** Protection on all forms.
- **Secrets:** .env file in .gitignore. .env.example committed with placeholder values.
- **HTTPS:** Enforced in production (handled by Render).
- **Payment data:** Stripe handles all card information. FinTrack never touches payment details.
- **Regulatory compliance:** All chatbot responses validated against compliance rules. System prompt enforces FCA guidance boundary. Disclaimers stored in compliance.py as single source of truth.
- **GDPR preparation:** Privacy policy required before launch. Users must be able to request data deletion.

---

## 10. Infrastructure Costs

| Item | Free Tier | Paid Tier | Trigger |
|------|-----------|-----------|---------|
| Hosting (Render) | £0/month | £7/month | First paying user |
| Database (Render PostgreSQL) | 1GB free | £18/month | ~500 users |
| Email (Resend) | 3,000/month free | £15/month | 3,000+ emails |
| Payments (Stripe) | No monthly fee | 1.4% + 20p/transaction | First payment |
| Domain (.co.uk + .com) | — | £25/year | Now |
| LLM API (chatbot) | — | ~£0.002–0.005/message | Plus launch |

**Total cost at launch:** £25/year (domain only).
**Total cost at 500 users:** ~£40–60/month.

The business becomes profitable with the very first paying subscriber covering months of infrastructure costs.