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

## Double border — button + following subordinate copy

When a button is followed by a whisper/note/hint, the note must NOT have its own `border-top`. The button's wrapper already has the section separator above it. Two borders box the button in visually and make the note look like a separate section.

**Applied**: overview.html action_whisper wrapper — removed border-top + padding-top, kept margin-top: 10px only. Watch for this pattern recurring on other cards.

---
