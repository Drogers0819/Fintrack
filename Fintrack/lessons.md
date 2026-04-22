# Claro — Session Lessons

Staging area. Rules here are new enough that they need another session's worth of validation before graduating to AGENTS.md or DESIGN-SYSTEM.md. Once a rule has been applied consistently (or is blindingly obvious), graduate it and delete from here.

---


## CSS custom property inheritance — always re-declare `--ai-whisper` in fully-custom dark themes

When a theme defines its own `--roman-gold` override (e.g. cobalt uses `#63B3ED`), it must also explicitly re-declare `--ai-whisper: var(--roman-gold)` inside that theme block. Without it, `--ai-whisper` resolves against `:root`'s `--roman-gold` value at cascade time, not the theme's override — producing the wrong colour. This silently worked for all themes that inherit `:root` gold, but broke for cobalt. Fix: add `--ai-whisper: var(--roman-gold);` anywhere `--roman-gold` is redefined to a non-gold value.

**Applied**: `.theme-cobalt` in `themes.css` — added `--ai-whisper: var(--roman-gold)` after the cobalt `--roman-gold: #63B3ED` declaration. Verified whisper text now shows electric blue on cobalt.

---

## Slider readout — always a feedback indicator, never a hero metric

Live interactive readouts (slider values, calculator inputs) should be styled at ~1rem, not `metric-value sm` (1.3rem). 1.3rem creates false hierarchy against the primary metric on the same card.

**Applied**: goal_detail.html slider amount — inline `font-size: 1.05rem; font-variant-numeric: tabular-nums`. Needs to hold through future goal detail changes.

---

## Feature check icons in paywalls = green, not gold

Feature validation lists (checkmark Full financial plan, checkmark AI companion) use `stroke="var(--success)"`. Gold (`--roman-gold`) is reserved for: filled primary CTAs, AI card pulse headers, goal savings progress bars, projections on track. Confirming a feature is delivery/completion = green. Not achievement/brand = not gold.

**Applied**: companion.html paywall — 4 check icons changed from `var(--roman-gold)` to `var(--success)`.

---

## Gold card bg — perceptual contrast, not absolute opacity

Gold card bg opacity must be calibrated against the actual page background hue, not matched numerically across themes. A 15% gold tint on a near-black page reads very differently to 15% on a warm-brown page (Oxford Saddle) — the latter looks muddy.

Calibrated values as of April 2026 (all in `themes.css` as explicit `.gold-card` overrides):
- Racing Green: 10% bg, 25% border (was 15% — too heavy)
- Oxford Saddle: 9% bg, 22% border (warm page needs lower)
- Midnight Navy: 12% bg, 28% border (cold page, needs explicit override)
- Obsidian: 10% bg, 25% border (pure-black page, fallback was 5% — too subtle)
- Rosso: 13% bg, 30% border
- Cobalt: 10% bg, 22% border
- Amethyst: 13% bg, 30% border
- Light themes: 10-11% bg, 30-32% border (explicit class overrides per theme)

Rule: never rely on `--roman-gold-dim` token alone for gold card bg on themes where that token is set for other purposes. Always use explicit `.theme-X .gold-card` override.

---

## Empty progress bars — do not suppress in goal rows

An empty progress track (0% fill, e.g. birthday at £0.00 of £200.00) on a goal row is a valid, intentional state. It tells the user the goal exists and how much is left to save. Do NOT suppress the track or replace with "Not started" text. The empty grey track + amount labels below is the correct design.

**Ruled out**: Adding `{% if pot.current > 0 %}` guard or replacing with "Not started" text. Victoria objected and reverted both. The track renders even at zero. This was corrected twice in one session — do not attempt again.

---

## Double border — button + following subordinate copy

When a button is followed by a whisper/note/hint, the note must NOT have its own `border-top`. The button's wrapper already has the section separator above it. Two borders box the button in visually and make the note look like a separate section.

**Applied**: overview.html action_whisper wrapper — removed border-top + padding-top, kept margin-top: 10px only. Watch for this pattern recurring on other cards.

---

## Optical spacing vs numerical spacing — same value reads differently by context

Equal pixel values do not create equal optical spacing. A 22px gap after Cormorant Garamond italic at large size reads optically larger than a 22px gap after body-weight Inter, because the serif has more descending visual weight. Rule: reduce gap after heavy/display type by ~25-30% to achieve the same optical breathing room as body copy. Trust the eye, not the ruler.

**Applied**: overview.html whisper card — AI italic text to OVERALL PROGRESS section gap: 22px to 16px (optical balance fix).

---

## Icon alignment in two-line list items — flex-start, not center

When a list item has an icon + two-line text block (title + description), use `align-items: flex-start` on the flex container. `align-items: center` floats the icon between the two lines, which reads as unmoored. `flex-start` anchors the icon to the title (the primary action), which is the correct semantic and visual hierarchy.

**Applied**: life_checkin.html — all 8 choice-card items changed from `align-items: center` to `align-items: flex-start`.

---
