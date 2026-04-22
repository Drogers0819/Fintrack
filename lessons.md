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

## 2026-04-22 — Breadcrumb reflects IA, not navigation history
**Mistake**: goal_detail.html conditionally showed "Overview" or "Goals" as breadcrumb parent based on a `from_page` URL param (tracking where the user came from). Check-in showed "Overview › Monthly check-in" even though Check-in is a top-level nav item. Plan showed "Overview › Your plan" for the same reason.
**Fix**: Breadcrumbs always reflect Information Architecture — where the page lives in the nav hierarchy. Top-level nav pages (Overview, Check-in, Goals, Companion, Plan) show only their own name in the header. Sub-pages always show the matching sidebar section as parent (e.g. "Goals › goal name", "Check-in › Life check-in", "Plan › Need cash"). No `from_page` conditionals.
**Rule**: Breadcrumbs show IA position, not navigation history. The parent in the breadcrumb is always the sidebar section that owns this page — never the page the user came from. Sidebar active state and breadcrumb parent must always match.

## 2026-04-22 — Duplicate CSS definition causes confusion and cascade bugs
**Mistake**: `.gold-card` was defined twice in main.css — an older definition at line ~549 with hardcoded `rgba(197,163,93,0.05)` background and `rgba(197,163,93,0.2)` border, and the canonical definition at ~1948 with the correct token-aware values. The cascade meant the second definition won, but the first created confusion and overrode inherited values unexpectedly on some selectors.
**Fix**: Removed the earlier duplicate block entirely. Kept only the canonical definition. Changed its border from hardcoded `rgba(197,163,93,0.15)` to `var(--roman-gold-glow)` so it adapts across all 9 themes.
**Rule**: Before adding any new CSS rule, grep for existing definitions of the same selector. Duplicates always create cascade confusion. One canonical definition per component.

## 2026-04-22 — Fixed input zone on companion needs sidebar-aware left offset
**Mistake**: Companion's full-bleed fixed input zone needed to account for the 260px sidebar on desktop. Setting `left: 0` would put it behind the sidebar. Using `position: static` kept it inside the 560px column and not full-bleed.
**Fix**: `.companion-input-zone { position: fixed; bottom: 0; left: 260px; right: 0; }` on desktop. `@media (max-width: 768px) { left: 0; bottom: 60px; }` to clear the mobile bottom nav. Inner div has `max-width: 560px` to align text with the column above.
**Rule**: Full-bleed fixed zones on pages with a sidebar must use `left: [sidebar-width]px` to avoid overlapping the sidebar. The inner content container constrains the max-width. Mobile override resets left to 0 and adjusts bottom to clear the nav bar.

## 2026-04-22 — Glass chip style vs btn-secondary for quick-select inputs
**Mistake**: Quick-amount preset buttons on withdraw.html used `btn-secondary btn-sm` — the gold-bordered secondary button — to fill in an amount field. These are not action buttons; they're quick-fill shortcuts. Using a gold-bordered button for this misrepresents the action and overloads the gold semantic.
**Fix**: Inline glass chip style: `border: 0.5px solid var(--glass-border); background: var(--glass-bg); color: var(--text-tertiary); border-radius: 50px`. These are neutral selection indicators, not actions.
**Rule**: Quick-fill preset chips that populate a field are NOT buttons — they're selection shortcuts. Use glass chip styling (neutral border, no gold). Only the form's actual submit button is the action and earns btn-primary.

## 2026-04-18 — Mixed tappable/non-tappable rows in the same list (affordance failure)
**Mistake**: Overview pots section showed goal rows (tappable, with chevron) and allocation rows (Lifestyle & family, Buffer — not tappable) in the same visual list. Tried visual differentiation (text-primary+chevron vs text-secondary+no chevron) as a middle ground — this was wrong. On mobile with no hover states, users default to "nothing navigates" and miss the tappable rows entirely regardless of styling.
**Fix**: Removed Lifestyle & Buffer from the overview pots section entirely. They're allocation categories, not goals — they have no detail pages. The Plan page shows full allocation breakdown. Now every row in "Your pots" is a goal row and every row has a chevron and navigates.
**Rule**: Lists must be homogenous — all rows navigate, or none do. The fix is structural (remove non-navigable items), not cosmetic (style them differently). Never mix tappable and non-tappable rows in the same visual list on mobile.

## 2026-04-18 — Decorative icon above page headers adds noise
**Mistake**: trial_gate.html had a 40×40px circular check icon above "Your plan is ready." — the h1 already communicated the success state. Two elements saying the same thing = visual noise that delays the user reading the actual headline.
**Fix**: Removed the icon entirely. The h1 stands alone using `.page-header`. Strong typography is sufficient.
**Rule**: Never add a decorative icon above a page h1 unless the icon provides information not already in the heading. "Success checkmark + 'Your plan is ready'" is redundant. The heading wins; remove the icon.

## 2026-04-18 — Never introduce new button variants — use existing classes
**Mistake**: Created `.withdraw-preset` with `border-radius: 50px` (pill shape) for quick-amount chips on withdraw.html. This introduced a fourth button shape that doesn't exist in the design vocabulary, making buttons inconsistent across the app.
**Fix**: Replaced with `btn-secondary btn-sm`. Deleted the custom `.withdraw-preset` CSS block.
**Rule**: The button vocabulary is exactly: `btn-primary`, `btn-secondary`, `btn-danger`, each with optional `btn-sm` and `btn-full` modifiers. Never create a new button class in a page `<style>` block. Exception: `.goal-chip`, `.sub-chip`, `.suggestion-chip` are intentional SELECTION chips (multi-select inputs) — pill shape is correct for them. The violation is pill shape on an ACTION trigger (a button that does something when clicked), not on a selection input.

## 2026-04-18 — Using btn-secondary when btn-primary is correct for a sole CTA
**Mistake**: goal_detail.html unreachable state used `btn-secondary btn-sm` for "Edit this goal". In that state, editing is the ONLY possible action — it's the primary CTA. Secondary button implies it's secondary to something else.
**Fix**: Changed to `btn-primary btn-sm`. Also added a heading ("No contribution set") above the message to follow the title + subtitle + button empty-state pattern.
**Rule**: `btn-secondary` is only correct when it sits alongside a `btn-primary` as a secondary option (e.g., Cancel + Save). A lone action button is always `btn-primary`. If there's nothing to be secondary to, it shouldn't be styled as secondary.

## 2026-04-18 — No-centering rule violated on trial_gate and withdraw pages
**Mistake**: `trial_gate.html` had `max-width: 520px; margin: 0 auto` wrapper + `text-align: center` on header, value framing, CTA card title, and trust signals. `withdraw.html` had the same `max-width: margin: 0 auto` island pattern. Both pages were centered layout islands while every other page in the app is left-aligned — confirmed by reading 10+ templates.
**Fix**: Removed outer centering wrappers from both pages. Removed all `text-align: center` from non-table, non-table-cell elements. Trust signals changed to `justify-content: flex-start`. CTA card title left-aligned.
**Rule**: `max-width + margin: 0 auto` on a page wrapper is always a centering island violation. Grep for it across all templates whenever a new page is built. Table cells (`th`, `td`) may use `text-align: center` — all other block elements must not.

## 2026-04-18 — Hardcoded `rgba(197,163,93,...)` instead of CSS variables
**Mistake**: Multiple templates used hardcoded `rgba(197,163,93,0.04)`, `rgba(197,163,93,0.15)`, `rgba(197,163,93,0.12)` etc. instead of `var(--roman-gold-dim)`, `var(--gold-whisper-bg)`, `var(--glass-border)` etc. This breaks theme-switching (ivory uses a different gold value, cobalt uses blue) and creates inconsistency when variable values are updated.
**Fix**: Audited all templates, replaced hardcoded gold rgba with CSS variables. Added `--gold-whisper-bg` and `--gold-whisper-border` to `:root` in `main.css` so all themes inherit them, with ivory and cobalt theme-specific overrides in `themes.css`.
**Rule**: Never hardcode `rgba(197,163,93,...)` in any template or CSS file. Only `var(--roman-gold)`, `var(--roman-gold-dim)`, `var(--roman-gold-glow)`, `var(--gold-whisper-bg)`, `var(--gold-whisper-border)` are valid. New gold variables must be added to `:root` in `main.css` first, then theme overrides for ivory/cobalt.

## 2026-04-18 — Non-standard split £ input on withdraw page
**Mistake**: withdraw.html used a `<span>£</span>` + `<input>` with shared border (right border on span removed, left border on input removed) to create a "£ | amount" input. This is visually different from the standard `<input class="form-input">` used on every other page with `(£)` in the label.
**Fix**: Replaced with standard `<input class="form-input" id="amount-input">` and updated label to "How much do you need? (£)".
**Rule**: The app has one input pattern: `class="form-input"`. Currency prefix goes in the label as `(£)`, never as a separate HTML element joined to the input. Any split-input with conjoined borders is a violation.

## 2026-04-18 — `empty-page-center` class used incorrectly for non-empty-page states
**Mistake**: `checkin.html` and `my_goals.html` used `<div class="empty-page-center">` with `max-width: 280px` constraints on empty-state copy. These states appear when the user hasn't set up a profile yet — they're a guided empty state pointing to the next action, not a "nothing here" dead end. The narrow max-width pushed text into short awkward lines.
**Fix**: Replaced `class="empty-page-center"` with `<div style="padding-top: 8px;">`. Removed all `max-width: 280px` constraints from text.
**Rule**: `empty-page-center` is only valid when there is literally nothing else on the page. Guided empty states (empty + a CTA to an action) use `padding-top: 8px` left-aligned divs, not centred containers.

## 2026-04-18 — Spacing inconsistency from mixing margin-bottom and margin-top across sections
**Mistake**: Plan page tool sections used `margin-bottom` on some sections and `margin-top` on others. These compound: a `margin-bottom: 32px` on section A + `margin-top: 8px` on section B = 40px gap. Other section pairs had only 8px. Result: wildly inconsistent spacing between identical structural elements.
**Fix**: Standardized all tool sections to `margin-top: 20px; padding-top: 20px; border-top:...`. No `margin-bottom` on any section. One value controls every gap.
**Rule**: For divider-separated sections, use margin-top ONLY on the section div — never margin-bottom on content inside a section. Then every gap = exactly one value, consistent everywhere. Check consistency across all pages when changing spacing on one page.


## 2026-04-18 — Section CTAs styled as text links blend into page labels
**Mistake**: "My goals >" section CTA used `color: var(--text-secondary)` and text-only styling, making it indistinguishable from surrounding body text. No obvious tap affordance.
**Fix**: Changed to a bordered pill chip — `border: 0.5px solid rgba(255,255,255,0.12); border-radius: 50px; padding: 3px 10px`. Distinct from text without being a heavy button.
**Rule**: Section-level CTAs (e.g. "My goals >", "See all >") must use a pill chip style, not raw text links. They need a visible border to distinguish them from labels. Apply this pattern consistently wherever a section has a "view all" or navigation CTA.

## 2026-04-18 — Redundant "GOAL" eyebrow on goal detail page
**Mistake**: goal_detail.html had a "GOAL" eyebrow label above the goal name. The user is already on the goal page, navigated from Goals — the eyebrow adds no information and creates two competing identifiers (nav back-link + eyebrow both say "goal").
**Fix**: Removed the eyebrow entirely. Back-link provides sufficient context.
**Rule**: Eyebrow labels on detail pages are only justified if they disambiguate the object type when it's genuinely ambiguous (e.g. multiple object types share the same detail page). Never add eyebrows that just restate the nav context the user already has.

## 2026-04-18 — Interactive elements not obviously discoverable (chevrons faint, rows unseparated)
**Mistake**: Tappable pot rows in overview used `stroke="var(--text-tertiary)"` for chevrons (nearly invisible) and had no separators between rows, so users couldn't tell individual rows were independent tappable items. The "My goals >" section CTA looked like a label, not a link.
**Fix**: Chevrons on tappable rows raised to `var(--text-secondary)` and `stroke-width="2.5"`. Row separators (`border-bottom: 0.5px solid var(--glass-border)`) added between items. "My goals" CTA given slightly heavier chevron weight.
**Rule**: On mobile there are no hover states. Any interactive element must be visually self-evident at rest: chevron at `--text-secondary` or brighter, row separators to define item boundaries, sufficient padding for tap targets. If a user can't see the affordance, the feature doesn't exist for them.

## 2026-04-18 — Dual affordances for one action (Edit header button + Adjust this goal link)
**Mistake**: goal_detail.html had an "Edit" button in the page header (top-right) AND an "Adjust this goal >" text link in the unreachable state — two labels, two placements, for the same action. Worse: "Adjust this goal" incorrectly linked to `my_goals` (the list) instead of `edit_goal` (the form), sending users backwards in the hierarchy.
**Fix**: Removed "Edit" from page header. In unreachable state: replaced text link with `btn-primary btn-sm` labeled "Edit this goal" linking to `edit_goal`. In reachable state: added "Edit goal" button at the very bottom after all content.
**Rule**: One action = one entry point = one label. Never have two clickable elements that do the same thing on one page. When spotting this on any page, check every other page for the same duplication.

## 2026-04-18 — Issue raised on one page not checked app-wide
**Mistake**: When Victoria raised a layout/hierarchy issue on one page (e.g. goal_detail), Claude fixed it in isolation without checking whether the same pattern (dual affordances, wrong link target, inconsistent labeling) appeared on other pages.
**Fix**: Check every template for the same pattern before marking fixed. Use Grep to search for the problematic class/attribute/text across all templates.
**Rule**: When any issue is raised, check every other active page immediately. Never audit or fix in isolation. One instance found = grep the entire codebase for the pattern before concluding the fix is complete.

## 2026-04-18 — Logo height matched to avatar container, not optical size
**Mistake**: Set mobile logo to `height: 36px` to match the avatar circle container (also 36px). The logo mark filled nearly the full 52px header height — only 8px breathing room each side. The avatar "T" inside its 36px circle reads optically much smaller, making the logo appear to burst out of the bar while the avatar looked contained.
**Fix**: Reduced to `height: 24px` — 14px clear space above and below in the 52px bar. Logo mark and avatar letter now have equivalent optical weight and breathing room.
**Rule**: Never use an adjacent element's container as the optical reference for a logo. Match perceived visual density, not container size — a single letter in a circle occupies ~50% of the circle, while a logo mark occupies ~80-95% of its bounds. Give the logo proportionally more clear space.

## 2026-04-18 — SVG `<polyline>` missing right slope on landmark/bank icon (persisted two sessions)
**Mistake**: The bank icon used `<polyline points="12 2 2 7 22 7"/>` for the roof. A polyline draws segments between points in order but does NOT close back to the start — this draws only the LEFT slope (12,2)→(2,7) and the BASE (2,7)→(22,7). The right slope (12,2)→(22,7) was never drawn. A partial fix in a previous session corrected column y-positions but left the polyline intact, so the roof line remained visually broken.
**Fix**: Replaced with `<path d="M12 2l10 5H2l10-5z"/>` — the `z` command closes the path back to (12,2), ensuring all three roof edges are drawn. Added explicit `<line x1="2" y1="7" x2="22" y2="7"/>` for the eave.
**Rule**: Never use `<polyline>` for a closed shape (triangle, rectangle, arrowhead). Use `<path>` with `z` to close. If any edge of a shape is missing at render time, check whether the path closes with `z`.

## 2026-04-18 — Logo PNG internal transparent space causing unequal visual padding
**Mistake**: The mobile header had `justify-content: space-between; padding: 0 16px` — equal CSS padding on both sides. But the logo PNG has significant internal transparent space, so the visible mark appeared further from the left edge than the avatar from the right, creating an illusion of unequal margins.
**Fix**: Set both logo and avatar to identical container dimensions (36×36, `object-fit: contain`). Matching physical footprint makes the flex spacing visually equal without asymmetric padding.
**Rule**: When an image asset has internal transparent space, the visible mark occupies a smaller area than the container. Balance it by matching the container dimensions to the paired element — never compensate with asymmetric padding.

## 2026-04-18 — Centered h1 left as-is on "reveal" page
**Mistake**: plan_reveal.html had `text-align: center` on the page-header and h1 ("Here's your plan."). The assumption was that a dramatic reveal moment warranted centering — treating it as a theatrical exception to the left-align rule.
**Fix**: Removed `text-align: center` and the inline `font-size: 1.6rem` override. Left-aligned header, standard size.
**Rule**: Page headers (`h1`, `.page-header`) are always left-aligned. There are no exceptions — not for reveals, not for emotional moments. Consistency IS the quality signal.

## 2026-04-18 — Sign-out separator (border-top) created awkward visual gap on mobile
**Mistake**: The mobile sign-out button on settings.html had `border-top: 0.5px solid var(--glass-border)` to visually separate it from the account section above. This created a cramped physical line that looked disconnected — the margin above felt too tight between the line and the content, while the margin below felt excessive.
**Fix**: Removed `border-top` and `padding-top: 20px`. Increased `margin-top` from `32px` to `48px`. Changed color from `var(--text-tertiary)` to `var(--danger)` at `opacity: 0.65`.
**Rule**: Don't use `border-top` to create semantic separation for a sign-out/destructive action. Use generous `margin-top` + danger color. Colour creates semantic hierarchy; borders create visual clutter when misapplied.

## 2026-04-18 — glass-card on plan overview summary and methodology text in plan_review
**Mistake**: plan_review.html had a `glass-card` around the "Plan overview" numbers (income/essentials/surplus) and a box-styled div around the methodology explanation text. Both are informational content, not discrete financial objects the user acts on.
**Fix**: Plan overview section: removed `glass-card` class, replaced with bare div + `border-bottom` separator. Methodology text: removed box styling, changed to plain `<p>` in `var(--text-tertiary)`.
**Rule**: If the content explains HOW the plan works or summarises numbers from elsewhere, it is not a glass-card candidate. Reserve cards for the things users interact with (goal cards, budget rows, transaction lists).

## 2026-04-18 — Emoji icon strings in whisper_service.py rendered as raw text in production
**Mistake**: whisper_service.py returned emoji strings (🏦 ✅ 🎯 📋 etc.) as the `icon` field. These were rendered directly in the overview template as text, not as icon glyphs, depending on font stack and OS.
**Fix**: Replaced all emoji strings with semantic Lucide icon names (e.g. "bank", "check-circle", "target", "clipboard-list"). Overview template maps these names to inline SVG paths via a Jinja2 if/elif block. When adding new icon names to the service, always update the template mapping at the same time.
**Rule**: Service files must never contain emoji. Icon references should be semantic string names that a template mapping can resolve to an inline SVG.

## 2026-04-17 — Competing progress systems treated as a surface issue
**Mistake**: Welcome page had a 2-step checklist ("Complete profile → Choose goals") while a separate 4-step onboarding wizard (factfind → surplus_reveal → goal_chips → plan_reveal) already covered the same ground. This was initially described as "architecturally fine but confusing" — which was settling for a known UX failure.
**Fix**: Removed the welcome page from the new-user flow entirely. Register → factfind directly. The wizard handles full onboarding. Welcome page still exists but is no longer in the path.
**Rule**: Two competing progress trackers for the same user journey is always a structural problem, not a surface one. One flow, one tracker. When you spot this pattern, the fix is to eliminate the redundant system — not add copy clarifying which one to follow.

## 2026-04-17 — AI whisper (gold-card) placed on reveal/hero page instead of review page
**Mistake**: plan_reveal.html had an AI commentary block (gold-card with Claro label) at the top of the page, immediately before the plan numbers. Reveal moments are the "wow" — a block of AI text before the numbers interrupts the payoff and dilutes it.
**Fix**: Removed the gold-card from plan_reveal entirely. Moved it to plan_review (the detail/confirmation step) where users are actively reading and comparing — contextually appropriate for commentary.
**Rule**: AI whisper blocks belong on review/detail pages only. Never on reveal or hero moments. Reveal pages should be clean — numbers first, no preamble.

## 2026-04-17 — CTA hidden with `display: none` until condition met
**Mistake**: goal_chips.html hid the "Build my plan" button entirely (`display: none`) until at least one chip was selected. Users had no affordance that a next step existed — the page appeared to have no exit.
**Fix**: Changed to an always-visible disabled button with instructional text ("Select a goal above to continue"). `updateBtn()` enables the button, updates the label, and appends the Lucide arrow-right icon when a selection is made.
**Rule**: Never hide the primary CTA behind a condition. Show it disabled with a short explanation of what the user needs to do. Disabled with hint = clear path forward. Hidden = dead end.

## 2026-04-17 — Chip selected state used white opacity border instead of gold
**Mistake**: `.goal-chip.selected` and `.sub-chip.selected` on goal_chips.html and factfind.html used `border-color: rgba(255,255,255,0.3)`. On a dark glass surface, this border is nearly imperceptible — the selected and unselected states look identical at a glance.
**Fix**: Changed to `border-color: var(--roman-gold)` on all chip selected states across factfind, goal_chips, and surplus_reveal. Gold provides a clear, semantically consistent selection signal.
**Rule**: Selected chip states always use `border-color: var(--roman-gold)`. White opacity borders are invisible on dark backgrounds — they communicate nothing. If it's selected, it must be obviously selected.

## 2026-04-17 — metric-label class misused for AI card pulse headers across 6 templates
**Mistake**: `goal_detail.html`, `insights.html`, `checkin.html`, `recurring.html`, `macros.html`, `scenario.html` all used `.metric-label` class on AI card header labels (e.g. "Projection", "Prediction", "Savings spotted", "Claro") with a gold color override. `.metric-label` is for ≤3-word noun labels above numbers only — never for AI card headers.
**Fix**: Replaced `.metric-label` + gold override with inline `font-size: 0.65rem; color: var(--roman-gold); text-transform: uppercase; letter-spacing: 0.06em;` — matching the pattern already established in overview.html, plan.html, budgets.html AI cards.
**Rule**: AI card pulse-header labels always use inline style, never `.metric-label` or `.section-label` class. The distinction: classes are semantic (≤3-word noun above a number; structural section divider). AI headers are one-off inline styled elements.

## 2026-04-17 — My Budgets page unreachable from within the app
**Mistake**: My Budgets (/my-budgets) was only linked from `waterfall.html`, which is an unrouted template. No active page linked to it — users could only reach it by knowing the URL.
**Fix**: Added My Budgets as a 4th row in the My Money sub-nav (Insights, Recurring, Analytics, Budgets) with a pie-chart icon. Moved the `border-bottom` from the Analytics row (previously last) to the now-separated Analytics row, and removed it from the new last item (Budgets).
**Rule**: Before shipping any new page, trace the full path from a bottom nav tab to that page. If no path exists, the page doesn't exist for users. Always verify navigation coverage in the active templates, not the static route list.

## 2026-04-17 — gold on inline text links persisting across welcome.html, upload.html, goal_detail.html, settings.html, unsubscribe.html
**Mistake**: After fixing gold inline links on my_money, my_goals, my_budgets, the same violation persisted on 5 more templates. Each new template was written independently without checking the established fix.
**Fix**: Changed all to `color: var(--text-secondary); text-decoration: underline; text-underline-offset: 2px;`.
**Rule**: The gold-on-inline-link grep (`grep -r "roman-gold" templates/ | grep "<a "`) must be part of every audit pass — run it as a command, not a visual check.

## 2026-04-17 — "Done" badge on welcome.html used gold instead of green
**Mistake**: Completed step badges in `welcome.html` used `color: var(--roman-gold); background: rgba(197,163,93,0.1)`. The equivalent badge in `plan.html` uses `color: rgba(72,187,120,0.8); background: rgba(72,187,120,0.1)` (green). Same semantic role, different templates, inconsistent color.
**Fix**: Changed to green to match plan.html. Also changed "Done" to "done" (normal case per copy standards).
**Rule**: Check completion/done badges across all templates for consistency. Green = success/done, not gold. Gold is for achievement/CTA, not status.

## 2026-04-17 — section-label CSS class used roman-gold globally for all structural dividers
**Mistake**: `.section-label` had `color: var(--roman-gold)` in the base CSS, making every section divider on every page appear in gold — a color reserved for CTAs, AI insights, goal highlights, and projections. "MONTHLY BREAKDOWN", "YOUR JOURNEY", "ALLOCATION BREAKDOWN" etc. all shouted in gold when they should recede.
**Fix**: Changed `.section-label` color to `var(--text-tertiary)`. AI card pulse-headers use inline styles, not this class, so they were unaffected. One CSS line corrected 20+ pages simultaneously.
**Rule**: Section dividers are structural elements that should recede — never apply a brand accent color to them. Hero hierarchy comes from size and contrast on the content, not on the label above it.

## 2026-04-17 — Heading/description size inversion on tool sections in plan.html
**Mistake**: "Can I afford this?", "Habit cost", and "What if?" section labels were `0.72rem text-tertiary` (smaller than their descriptions at `0.85rem text-secondary`). The eye read the description first, inverting the intended hierarchy.
**Fix**: Changed tool headings to `0.9rem text-primary font-weight:500`, descriptions to `0.78rem text-tertiary`. Heading always larger AND higher contrast than its supporting body copy.
**Rule**: Before shipping any label+description pair, verify: heading font-size > description font-size AND heading color contrast > description color contrast. Both must hold simultaneously.

## 2026-04-17 — glass-card wrapping teaser/summary sections on overview
**Mistake**: The "This month" spending snapshot on overview.html was wrapped in a `glass-card`. Per card rules, glass-card is only for discrete financial objects the user acts on as a whole. A spending summary with a "My money" link is a teaser to another page — must be bare.
**Fix**: Replaced `<div class="glass-card">` with a bare div using `padding-top: 20px; border-top: 0.5px solid rgba(255,255,255,0.06)` — same visual pattern as the pots section above it.
**Rule**: Before adding glass-card, ask "is this a discrete financial object the user acts on as a whole?" Summaries, teasers, and cross-page CTAs are always bare.

## 2026-04-17 — Gold on inline text links (my_money, my_goals, my_budgets)
**Mistake**: "or add manually" (my_money), "See your projection" (my_goals), and "Recurring payments" (my_budgets) all used `color: var(--roman-gold)`. Gold must only appear on filled primary CTA buttons, AI card pulse headers, goal progress bars, and on-track projections.
**Fix**: Changed all three to `color: var(--text-secondary)` with `text-decoration: underline` for discoverability on inline links.
**Rule**: Gold on an inline text link is always a violation. Inline links that are secondary/supporting actions use text-secondary + underline.

## 2026-04-17 — border-left gold accent on hero metric cards (insights, analytics)
**Mistake**: `border-left: 3px solid var(--roman-gold)` was used on "Predicted total" and "Total spending" cards to signal hierarchy. Gold on a structural/positional accent is misuse — gold is a semantic color, not a layout tool.
**Fix**: Removed the border-left. The `metric-value hero` class already establishes hierarchy via larger font size — no colour accent needed.
**Rule**: Never use `--roman-gold` as a CSS layout tool (borders, backgrounds). Size and weight create hierarchy. Gold is a semantic signal, not a design flourish.

## 2026-04-17 — Gold fill on month progress bar (insights)
**Mistake**: The "Month progress" bar in insights.html used `background: var(--roman-gold)`. A time-based progress indicator is a neutral UI element — it shows time passing, not achievement. Gold implies achievement or "on track."
**Fix**: Changed to `background: rgba(255,255,255,0.18)` — a muted neutral fill.
**Rule**: Gold progress bar fills are ONLY for goal savings progress bars (the user's savings vs. their target). All other progress bars (time, month, budget consumption) use a neutral color.

## 2026-04-17 — "Surplus" label confusing in plan breakdown total row
**Mistake**: The total row at the bottom of the monthly breakdown was labeled "Surplus" in text-tertiary. Users couldn't understand why a "surplus" appeared at the bottom of a list of allocated pots — it sounded like leftover money rather than the total being allocated.
**Fix**: Renamed to "Total allocated" with text-secondary font-weight:500 on label and text-primary font-weight:600 on amount — clearly reads as a ledger total row.
**Rule**: Label financial summary rows to communicate what's happening, not the technical backend field name. "Surplus" is a calculation concept; "Total allocated" is what the user cares about.

## 2026-04-17 — New template pages not covered by ui-audit scope definition
**Mistake**: The ui-audit skill listed active routes but didn't include new routes added in the recent pull (companion, checkin, plan_reveal, plan_review, surplus_reveal, goal_chips). These were missed in the initial audit pass.
**Fix**: At the start of every audit, run `flask routes` (or equivalent) to list all active routes and compare against the audit scope list. Any route not in the list must be added.
**Rule**: Before running /ui-audit, always enumerate all app routes programmatically — never trust a static list in the skill file.

## 2026-04-17 — Emojis in new onboarding templates (goal_chips, plan_review)
**Mistake**: goal_chips.html used emojis both in chip labels (🏠 ✈️ 👶) and in goal-detail section headers ("🏠 House deposit — roughly how much?"). plan_review.html used pot-type icons (🛡️ 💳 🎉 🔄 🎯) in allocation cards.
**Fix**: Removed all emojis. Chip labels became plain text. Detail headers use plain copy with a colon instead of em dash ("House deposit: roughly how much?"). Plan review allocation cards use only the pot name.
**Rule**: Zero emojis everywhere — including onboarding flows and chip UI. Labels, detail headers, and allocation cards must be text-only.

## 2026-04-17 — Subagent Edit permission was blocked in session
**Mistake**: Two background agents (em dash fixer, template UI fixer) were dispatched but both had the Edit tool blocked — all their fixes were no-ops. The task appeared completed but no changes were made.
**Fix**: After any agent completes, always verify by reading the output file AND checking the actual files for the expected change. If agent was blocked, make the edits directly.
**Rule**: Never assume background agent edits succeeded — always read the output file and spot-check a key file before moving on.

## 2026-04-17 — Em dashes in goal detail section headers used em dash AND emoji together
**Mistake**: goal_chips.html detail headers had both an emoji and an em dash: "🏠 House deposit — roughly how much?" — two violations in one string.
**Fix**: "House deposit: roughly how much?" — no emoji, colon replaces em dash.
**Rule**: When fixing em dashes in templates, also scan for adjacent emojis in the same element — they often co-occur.

## 2026-04-17 — inline `text-transform: uppercase; letter-spacing` on section dividers in new templates
**Mistake**: plan_reveal.html, plan_review.html, checkin.html, plan.html all had inline `style="font-size: 0.65rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.06em;"` instead of `class="section-label"`. Each new template introduced the violation independently.
**Fix**: Replace all inline uppercase+letter-spacing combos with `class="section-label"` and a single remaining style attribute (e.g. margin-bottom only).
**Rule**: Any time a new template is written, the first thing to audit is whether section dividers use `class="section-label"` — never inline uppercase style.

## 2026-04-17 — Gold on neutral sub-total displays in factfind
**Mistake**: factfind.html used `color: var(--roman-gold)` on the "Subscriptions total" and "Other payments total" running totals — these are neutral calculated values, not projections on track, not AI insights, not primary CTAs.
**Fix**: Changed to `color: var(--text-primary)` on both span elements. Confirmed JS updates only .textContent so the color fix persists dynamically.
**Rule**: Running totals, subtotals, and calculated field displays are neutral informational values — always text-primary, never gold.

## 2026-04-17 — Settings forms lacked Cancel buttons
**Mistake**: The "Change email" and "Change password" forms inside Settings accordions had only a primary submit button. The edit rule requires: "Edit pages always have Save changes (primary) AND Cancel (secondary) — never primary alone."
**Fix**: Added Cancel buttons that call `toggleSettings(key)` to collapse the accordion without submitting. Wrapped both buttons in a flex row.
**Rule**: Any form inside an accordion or expandable panel needs a Cancel button that reverses the open action (closes the panel), not just a page navigation link.

<!-- Graduated 2026-04-12: all entries from the 2026-04-12 session moved to:
     - Universal design principles → ~/.claude/design-standards.md
     - Claro-specific dev rules → Fintrack/AGENTS.md
     - UX/product rules → memory/feedback_ui_quality_bar.md
-->
