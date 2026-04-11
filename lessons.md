# Lessons — Claro (Fintrack)

<!-- Claude: review before beginning any work. Update immediately after any correction. -->

## Format — use this exactly, every time

```
## YYYY-MM-DD — [Short title of what went wrong]
**Mistake**: What Claude did wrong
**Fix**: What the correct approach is
**Rule**: The principle to prevent it recurring (one sentence, actionable)
```

---

<!-- Entries go below this line, newest first -->

## 2026-04-11 — Banner CTA competing with page primary action
**Mistake**: Added a factfind nudge banner with `btn-primary btn-sm` inside it — rendered as a full-width gold button, creating two competing primary CTAs on screen (the banner "Set up" + the page's own primary action like "Set budget" or "Upload statement").
**Fix**: Make the entire banner a slim tappable `<a>` strip — info icon + single line of text + chevron. No separate button. The whole row is the link.
**Rule**: A page can only have one primary CTA (gold/filled button); persistent nudge banners must use a tappable strip pattern, never a button.

## 2026-04-11 — Floating action button between content sections
**Mistake**: Upload statement / Add manually CTA was a standalone floating div between the whisper card and the spending breakdown — unanchored, interrupting data flow, and dominating empty state.
**Fix**: Move upload/add actions into the "All transactions" card header, positioned next to the section label. Actions belong adjacent to the data they create.
**Rule**: Actions should anchor to the section they affect — never float standalone between content sections.

## 2026-04-11 — Settings nav active state leaking to factfind page
**Mistake**: `pages.factfind` was included in the Settings nav active-state condition, so the Settings tab lit up gold when users were on the factfind page — making them think they were on Settings.
**Fix**: Remove `pages.factfind` from the Settings active endpoint list. Factfind is a standalone onboarding flow, not a Settings sub-page.
**Rule**: Nav active states should only highlight the tab that directly owns that route — never highlight a parent tab for an unrelated onboarding flow.

## 2026-04-11 — Factfind banner placed on unreachable page
**Mistake**: Added factfind setup banner to `overview.html`, but the `/overview` route redirects pre-factfind users to `/factfind` — making the banner on Overview unreachable.
**Fix**: Place the banner on the three pages users CAN actually reach before completing factfind: Money, Goals, Budgets.
**Rule**: Before adding UI to a page, verify the route renders that page for the target user state — check Flask routes for conditional redirects.
