# Design Baseline

Status: Approved baseline v0.1
Approved by: Product owner (`ksazid`)
Approved at: 2026-08-31T00:46:15+02:00

## Brand

- Product name: **Ziras**
- Tagline: **“what’s nearby.”**
- Brand character: modern, local, intelligent, fast, trustworthy, consumer-first.
- Ziras is not presented as a coupon marketplace; it is a local discovery radar.

## Launch sequence

### Stage 1 — Animated logo

The app opens with a dedicated Ziras logo animation. The motion should communicate **discovery/radar/location** without feeling like a navigation app.

Preferred motion language:
- subtle pulse/radar ring;
- brief location/discovery signal;
- restrained scale/fade;
- no long cinematic delay.

Target duration: approximately 700–1000 ms, adjustable after real-device testing.

### Stage 2 — Tagline transition

After the logo animation, show:

> **what’s nearby.**

The tagline should appear as a short transition state before onboarding/home. It should feel intentional rather than like a loading screen.

Target duration: approximately 500–800 ms. Respect reduced-motion accessibility settings.

### Stage 3 — Destination

- First launch → onboarding.
- Returning user → `For You` home.

## Onboarding

Onboarding has only **two required screens**.

### Screen 1 — Location

Primary message: Ziras needs an area to determine what is nearby.

Actions:
- Use current location.
- Choose location manually.

Requirements:
- Clear explanation before OS permission request.
- Manual fallback if permission is denied.
- Do not block the user permanently because location permission is unavailable.

### Screen 2 — Interests

Prompt should be short and conversational, e.g. **“What are you into?”**

Use visual multi-select chips/cards for broad interests such as:
- Indian food
- Asian food
- Burgers
- Coffee
- Fashion
- Tech
- Events
- Family
- Fitness

Do not ask cuisine hierarchies, favourite brands, discount thresholds or long preference questionnaires during initial onboarding.

The product learns detailed interests later from behaviour.

## Primary navigation

MVP information architecture:

1. **For You** — ranked personal discovery feed.
2. **Nearby** — local list/map exploration.
3. **Watch** — brands/places/categories/conditions the user wants monitored.
4. **Saved** — retained discoveries.

Keep primary mobile navigation compact and reachable with one hand.

## Discovery card baseline

Each card should make the following understandable at a glance:
- what happened / why it matters;
- place or brand;
- distance/location;
- value signal (discount, opening, event timing, price drop, etc.);
- freshness/confidence state;
- source/provider;
- primary action.

Actions:
- Save
- Share
- Not interested
- Open source

Do not overload cards with crawler/source metadata.

## Freshness language

Use understandable trust states:

- **Verified** — recently confirmed by a reliable source.
- **Likely active** — recent evidence but no authoritative active/expiry confirmation.
- **Check availability** — useful signal that cannot currently be verified strongly.
- Expired discoveries do not appear as active feed recommendations.

## Visual direction

Use the approved Ziras splash direction as inspiration, but implementation should stay product-UI appropriate:
- dark-first premium palette is acceptable;
- radar/location cues should be subtle;
- avoid excessive neon/glow in everyday feed screens;
- use strong hierarchy and large touch targets;
- cards should feel editorial and shareable rather than like dense marketplace tiles.

The logo itself must remain simple enough to work at app-icon and small navigation sizes.

## Motion

Use Emil-style motion principles only where motion clarifies state:
- splash logo reveal;
- tagline transition;
- card save/share feedback;
- map/list transition if added;
- lightweight discovery refresh feedback.

Do not add decorative motion that delays content access.

## Accessibility

- Respect reduced-motion settings.
- Minimum accessible touch targets.
- Do not encode freshness/confidence by colour alone.
- Support Dynamic Type/text scaling where practical.
- Maintain readable contrast in dark and light environments.
- Location permission denial must have a clear manual alternative.

## Loading / empty / error states

### Loading
Prefer useful skeleton/content placeholders after the initial launch sequence. Do not replay the full brand splash for ordinary refreshes.

### Empty feed
Explain that Ziras is still learning and offer nearby exploration / interest adjustment.

### No nearby discoveries
Allow radius/location adjustment rather than presenting a dead end.

### Source unavailable
Keep the app stable, mark data stale/unavailable and avoid presenting unverifiable content as live.

## Approved references

The conversation-approved sequence is authoritative for v0.1:

**Animated Ziras logo → “what’s nearby.” → onboarding/home.**

Generated visual mockups are directional references only; production logo geometry, typography, tokens and animation must be implemented as native/vector UI and reviewed on-device before freezing.
