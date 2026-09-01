# Design direction — Parallax observatory

Guidance: Anthropic `frontend-design` skill, read and installed 2026-08-31. Reference: https://github.com/anthropics/skills/tree/main/skills/frontend-design

## Brief

A Chinese-first research initiative for AI/science researchers and curious cross-disciplinary readers. Its job is to make the project's way of asking questions memorable, without implying scientific results.

## Critique of the previous direction

Warm paper, serif display, terracotta accents, numbered eyebrows and equal feature cards made the project interchangeable with other research landing pages. Merely replacing warm beige with dark neon would repeat another default. The redesign instead uses the subject's own mechanism: changing projection while keeping the underlying object fixed.

## Tokens

- Polar white `#f7faff`: reading surface.
- Ice blue `#e6edf7`: observatory background.
- Cobalt ink `#153cb4`: brand, selected controls, projection.
- Deep navy `#142544`: text.
- Optical cyan `#00a1b7`: projection depth / secondary scientific mark only.
- Blue grey `#536780`: supporting text.

Space Grotesk for English display and identity; system Chinese sans for primary reading; IBM Plex Mono for coordinate labels. Font files are packaged locally. No serif, simulated paper, glass cards or ambient glow.

## Layout and signature

The hero is a small observation instrument set against an oversized wordmark. A mathematically defined torus is rendered under three projections. Controls change the projection, not the underlying sample set. The caption explicitly marks it as a concept demonstration, not evidence or an experimental result.

```text
identity                          small anchor navigation
Scientific             [projection label]
Parallax.              [large interactive torus projection]
Chinese thesis         [front / side / oblique controls]
short project position                  [concept disclaimer]

quiet manifesto, followed by four wide typographic focus rows
one evidence loop, one compact honest-results section
open invitation integrated into footer
```

The broad display type and circular optical field supply the single strong aesthetic gesture. Other sections use quiet text, generous whitespace and simple grouping. Numbering appears only in the actual evidence process; no fake metrics or decorative issue numbers. Focus areas are not a sequence and therefore remain unnumbered.

## Interaction / accessibility

Reuse installed Tabs primitives. Keyboard arrows change projection tabs; panel descriptions are associated with their controls. Reduced motion disables view-change animation. SVG contains a plain-language title/description. All Chinese body text stays readable on narrow screens. No scroll hijacking, hidden cursor, autoplay animation, or pointer-only action.

No browser visual testing was requested; validation is type/build checks and non-browser route/metadata checks. Browser opening is a preview handoff, not a claim of screenshot-based verification.
