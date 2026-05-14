# Claro — Deferred Tasks

Living list of deferred research, pending decisions, and future work.
Update this file when items are completed or new ones are discovered.

---

## Pending decisions (needs sign-off)

- [ ] **Daniel sign-off**: Section order as app-wide standard (not just overview)
  — Plan whisper first, then spending, then goals, then companion prompt, then act
  — Currently applied to overview; needs agreement to extend to other pages

---

## Competitor research

- [ ] **Emma app** — iOS home screen, goals treatment, spending breakdown, tone/copy style
  Search: "Emma finance app iOS home screen goals spending 2024 2025"
  Extract: section order, how goals appear, spending breakdown UI, copy tone

- [ ] **Wealthfront goal card pattern** — date-as-hero on goal_detail page
  Wealthfront shows outcome (date + target amount) as the HERO, not progress bar
  Implication: goal_detail.html should lead with "Ready by Oct 2026 · £5,000 target"

---

## Dedicated audit sessions

- [ ] **Full theme audit** — every page, ALL themes (racing-green, midnight-navy, amethyst, rosso, obsidian, ivory, pearl, paper, sage, soft-modern, cobalt)
  All breakpoints: 375, 768, 1440px
  Every page in the active routes list

- [ ] **Accessibility audit** — text contrast, touch target sizes, focus states
  WCAG AA minimum on all text/background combinations
  Touch targets >= 44px on all interactive elements
  Focus rings visible on all interactive elements

---

## UX enhancements (future sessions)

- [ ] **Context tooltips (info icon)** — subtle info icon on "Monthly surplus", "Net worth", ring chart total
  Wealthfront uses hover tooltips on key numbers to explain what they mean
  High value for first-time users

- [ ] **Delta vs last month on stats strip** — show "up £X vs last month" for surplus + net worth
  Communicates trajectory without the user having to remember last month

- [ ] **Goal completion celebration** — pulse/glow briefly when a goal hits 100%
  Monarch and Plum have milestone moments; Claro currently shows flat "Goal complete" text

- [ ] **Collapsible desktop sidebar** — icon-only rail option
  Linear, Notion, most modern SaaS. 2026 standard. Consider after core UI is stable.

- [ ] **Time period toggle on ring chart** — "This month / Last month / Last 3 months"
  Small addition, high value for users who want to compare

- [ ] **Skeleton loading states** — placeholder shimmer while data loads
  Standard in Monarch, Linear. Currently blank sections show.

---

## Text/copy improvements

- [ ] **Placeholder text audit** — every input in every form should show realistic examples
  "e.g. Tesco weekly shop" not "Enter description"
  "e.g. £250" not "Amount"

- [ ] **Error message audit** — every error must say what happened AND what to do
  "Something went wrong" is not acceptable

---

## Architecture / tech

- [ ] **Pre-commit audit hook** — run grep sweeps (em dashes, hardcoded gold, etc.) before every commit
  AGENTS.md Section A sweeps should run automatically, not manually

- [ ] **Golden state Playwright baseline** — capture screenshots at end of each session
  Compare against at start of next session to detect visual regressions
