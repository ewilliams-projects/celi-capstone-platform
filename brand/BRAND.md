# Mainline Analytics — brand guide (web)

**Mainline Analytics** provides targeted analytics for equitable gas decommissioning. We help local governments and public utility commissions (PUCs) decide which sections of the gas distribution system to retire first, and how to do it fairly.

## Positioning

**One-liner:** Mainline Analytics shows cities and regulators which gas mains to retire first, and makes sure the communities with the least don't end up paying the most.

**Positioning statement:** For local governments and public utility commissions planning the move off gas, Mainline Analytics is the targeted-analytics partner that pinpoints which pipeline segments to decommission, and when. We weigh pipe condition, avoided replacement cost and electrification readiness alongside equity, so the transition is defensible, affordable and fair.

**Tagline:** *Mapping a fair path off gas.*
Alternates: *Retire the right pipes, fairly.* · *Clear data for a fair gas transition.*

**Why "Mainline":** gas *mains* are the distribution pipes we help retire, and a mainline is also the central, dependable route. The name says we know the infrastructure and we're the steady line through a complicated transition.

## Personality

| Trait | What it means | What it isn't |
| --- | --- | --- |
| **Trustworthy** | Transparent methods, cited data, numbers that hold up in a rate case | Bland or bureaucratic |
| **Creative** | Fresh ways to see the system: maps, stories, scenarios | Gimmicky or flashy |
| **Fair-minded** | Equity is built into the model, not added at the end | Preachy or partisan |
| **Grounded** | Speaks the language of pipes, budgets and ratepayers | Abstract or academic |

## Voice

Write the way a sharp, calm analyst briefs a commissioner: plain, specific and sure of the numbers.

- **Do:** lead with the decision ("Retire these 12 miles first"), name the people affected ("households in the Eastside tract"), cite every figure, and use the field's terms correctly (mains, service lines, non-pipeline alternatives, ratepayers, stranded assets).
- **Don't:** use hype ("revolutionary", "game-changing"), doom framing, exclamation marks, or jargon without a gloss for a general audience.
- **Example headline:** "Retiring 3 aging mains could avoid $18M in replacement costs and protect 4,200 low-income households." *(Placeholder figures. Replace them with your real analysis.)*

## Logo

The primary mark is an **M drawn as a gas main** with rounded pipe joints, fed by an **amber pathway** that runs in from the left and flows straight into it. Read together, they make one continuous route: the path into the transition, with Mainline carrying it forward.

- **Primary lockup:** `mainline-lockup.svg` (mark + "Mainline" in Fraunces + "ANALYTICS" spaced out in Inter). Use it on the title slide and the closing slide.
- **Reverse:** `mainline-lockup-reverse.svg` / `mainline-mark-reverse.svg` on `deep` backgrounds.
- **Mark alone:** `mainline-mark.svg` in slide footers, favicons, and avatars.
- **One color:** `mainline-mark-mono.svg` for one-color print and watermarks. A small gap separates the pathway from the M, standing in for the change from amber to teal.
- **Clear space:** keep at least the length of the amber pathway (about 1/4 of the mark's width) clear on every side.
- **Minimum size:** mark 24px tall, lockup 32px tall.
- **Don't:** recolor the pathway, move it away from the M (the one-color gap is the only exception), stretch the mark, put it on busy photos, or set the lockup on `brand` teal (it disappears).

## Color

The palette pairs a dependable deep teal with one warm amber spark.

| Role | Token | Hex (light) | Use |
| --- | --- | --- | --- |
| Primary | `brand` (Mainline Teal) | #1F7A72 | Logo, headings, key data |
| Anchor | `deep` (Slate) | #12343B | Title and section slides |
| Spark | `accent` (Pilot Amber) | #E8A33D | One highlight per slide |
| Soft | `tint` (Sage) | #DCEBE6 | Callouts, table headers |
| Background | `surface` (Paper) | #F7F5F0 | Slide background |
| Text | `ink` / `ink-muted` | #14262B / #5A6B6E | Body / captions |

**Proportion:** roughly 60% `surface`, 25% `deep` + `brand`, 10% `tint`, and no more than 5% `accent`. Amber works because it is rare.

**Maps and charts:** existing gas network in `ink-muted`, recommended decommissioning segments in `brand`, the top-priority segment or community in `accent`, and equity overlays as a `tint` → `deep` sequential ramp. Never use red/green for good/bad. Teal vs. amber stays distinguishable for colorblind viewers.

## Typography

All three families are free on Google Fonts. `brand.css` loads them for you.

- **Fraunces** (display, semibold): slide titles and big numbers. A warm, slightly quirky serif that carries the "creative" side while still feeling established.
- **Inter** (sans): subheads, body, and tables. Neutral and highly legible. This is the "trustworthy" side.
- **IBM Plex Mono** (data): chart labels, map legends, and source lines. Signals rigor.

Use the size variables in `brand.css` (`--ml-text-display` down to `--ml-text-label`).

## Using this kit on the website

**Files in this folder**

| File | Use |
| --- | --- |
| `brand.css` | All colors, fonts, sizes, spacing and base components as CSS variables (`--ml-…`). Load it before the site's own styles. |
| `logos/mainline-lockup.svg` | Header logo on light backgrounds. Text is converted to outlines, so it looks right without the fonts. |
| `logos/mainline-lockup-on-dark.svg` | Logo on Slate (`--ml-deep`) sections and the footer (transparent background). |
| `logos/mainline-lockup-reverse.svg` | Logo with its own Slate background, for social cards and other places where the background isn't yours. |
| `logos/mainline-mark.svg`, `mainline-mark-on-dark.svg` | The M alone, for tight spaces and mobile headers. |
| `logos/mainline-mark-mono.svg` | One-color mark that follows CSS `color` when inlined. |
| `logos/*.png` | PNG copies for places that don't take SVG (email, social). |
| `icons/` | Favicon set: `favicon.svg`, `favicon.ico`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`. |
| `illustrations/map-icon.svg` | The map illustration for the homepage hero. |

**Head tags**

```html
<link rel="stylesheet" href="/brand/brand.css">
<link rel="icon" href="/brand/icons/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/brand/icons/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/brand/icons/apple-touch-icon.png">
<meta name="theme-color" content="#12343B">
```

**Page patterns**

- **Header:** Paper background, `mainline-lockup.svg` at about 40px tall, links in `--ml-ink`, one primary button (`.ml-btn .ml-btn-primary`).
- **Hero:** `.ml-section-dark` (Slate) with the headline in Fraunces (`.ml-display`), the tagline in Inter in `--ml-tint`, and `map-icon.svg` on the right at 320 to 480px. Stack the map under the text on mobile.
- **Content sections:** Paper background, white `.ml-card`s with `--ml-radius-lg`, a Fraunces `h2` that states the takeaway.
- **Stats:** `.ml-stat` numbers in Teal with a short label and a `.ml-source` line under them.
- **Footer:** Slate, `mainline-lockup-on-dark.svg`, muted links.
- **Amber:** at most one amber element per screen (a highlighted number, the priority segment on a map). Never amber text on Paper.

**Rules for code**

- Use the `--ml-…` variables; don't hard-code hex values.
- Keep text contrast at 4.5:1 or better. The token pairs above already meet it.
- Use `<img alt="Mainline Analytics">` for the logo, and give the map icon a short description as its alt text, or `alt=""` if it's only decorative.
