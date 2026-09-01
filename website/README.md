# Scientific Parallax · 科学视差

中英文项目主页，独立于上层研究代码。只介绍长期关注点、方法假说与证据边界，不启动实验。

## Local development

Node 22.13+; `npm ci`, then `npm run dev`. Run `npm test` for copy and projection invariance tests. After a build, run `npm run typecheck` for type checks.

## GitHub Pages

The intended public origin is `https://scientific-parallax.com`; DNS and publishing are separate from preparing the code. See [DEPLOYMENT.md](DEPLOYMENT.md) for the one-time GitHub and GoDaddy setup.

- `npm run build:pages` exports and verifies static HTML, CSS, JavaScript, fonts and the existing social card in `dist/client/`. It needs no Sites or Cloudflare credentials.
- `npm run preview:pages` serves exactly those files at `http://localhost:4173`, with directory redirects and real 404 responses, without an application server.
- `npm run verify:pages` rechecks the built artifact, including both languages, metadata, all page script/style references, local fonts and HTTP responses.
- `.github/workflows/pages.yml` validates website pull requests and publishes successful website updates on `main` once GitHub Pages is enabled. It uploads **only `website/dist/client`**, never the research repository, secrets or `dist/server`.

This artifact is built for a domain root, not the `/ScientificParallax/` project URL prefix. Configure the custom domain in GitHub before enabling the public release. Keep the GoDaddy DNS unchanged until the website artifact is validated and the domain has been verified and added in GitHub.

The installed Vinext version skips the English route when a trailing-slash redirect is encountered during export. The Pages build disables that redirect while rendering, then packages `en.html` as `en/index.html`. Verification is part of `build:pages`, so a framework build that silently omits either language cannot be published.

## Existing Sites compatibility

`npm run dev` and `npm run build` retain the existing Sites/Worker configuration. The `.openai/hosting.json` association is preserved; the GitHub Pages workflow does not call or redeploy Sites. Both build modes use `dist/`, so rebuild with the intended target before previewing or publishing.

For Sites, set `SITE_ORIGIN` to the verified origin in local `.env` or Sites runtime settings. The Pages build explicitly defaults to `https://scientific-parallax.com`, overriding the local-preview `.env` value unless `SITE_ORIGIN` is supplied in the command environment. Social metadata uses only this configured value, never request host headers. If unset in the Sites build, image metadata is omitted rather than inventing an origin.

Website source is maintained within the parent ScientificParallax project; a separately rooted source snapshot is used for Sites publishing. Do not publish the parent research repository to the Sites source remote.

## Content

Chinese lives at `/`; English lives at `/en/`. The header links switch language using real, shareable URLs, so refresh and browser history preserve the selected language. Both versions share the page, typed copy in `lib/copy.ts`, and metadata generation in `lib/metadata.ts`. Each language has its own static root layout, with the document language and metadata fixed at build time. There is no request-header middleware or browser-only language detection. The existing bilingual brand illustration is intentionally reused for social previews.

The positioning brief lives in `../docs/project-brief.md`. Existing experiments and negative findings remain in the parent repository. The page links to its GitHub project and issues; no contact identity or research result is fabricated.

The redesign follows Anthropic's `frontend-design` skill. See `DESIGN.md` for the critique, visual rules and accessibility approach. The hero's three views project a fixed mathematical torus; it is explicitly a conceptual illustration, not experimental data. Existing research findings are unchanged.

The generated social card is `public/og.png`, 1732 × 908. Built-in image generation prompt: a clean scientific observatory sharing card, exact oversized geometric sans title “Scientific Parallax.”, Chinese name “科学视差” and supporting line “换个视角，问题也会改变。”; flat ice blue #e6edf7, polar white #f7faff circular optical field, cobalt #153cb4 and restrained cyan #00a1b7; asymmetric typography left, fine oblique wireframe torus right; generous negative space, no serif, paper texture, glow, fabricated data or extra wording. Previous card remains recoverable in the previous published source version.
