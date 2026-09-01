# GitHub Pages · scientific-parallax.com

## Status and scope

The repository contains the static build and an automatic Pages workflow. This does **not** mean the live site or DNS has been switched. Publishing requires an authenticated GitHub account with access to `RyanChromium/ScientificParallax`, Pages settings, and the separate GoDaddy changes below. Do not change repository visibility without the owner's approval; private-repository Pages availability depends on the GitHub plan.

Target URLs:

- Chinese: `https://scientific-parallax.com/`
- English: `https://scientific-parallax.com/en/`
- `www.scientific-parallax.com`: redirect to the apex domain after GitHub and DNS are configured.

Only `website/dist/client/` is uploaded. Research files, `.env`, `.openai/hosting.json`, dependencies, and server bundles are not part of the website artifact. The original Sites association is preserved, but is not involved in Pages publishing.

## 1. Validate locally

From `website/`, with Node 22.13+:

```sh
npm ci
npm test
npm run build:pages
npm run typecheck
npm run preview:pages
```

Open `http://localhost:4173/` and `http://localhost:4173/en/`. `build:pages` includes automated artifact checks and strict HTTP tests. It fails if either language, its metadata, required assets, or real 404 handling is missing. No Cloudflare Worker or Sites token is used for the exported site.

The export uses root-relative URLs. It targets the custom domain, **not** `ryanchromium.github.io/ScientificParallax/`. Do not treat that prefixed URL as a working preview of this particular build.

## 2. Authenticate and prepare GitHub

Sign in to GitHub through a trusted login flow; never paste a password or access token into chat. The CLI can be connected using `gh auth login` if desired.

1. Confirm the account has admin access to the existing repository and check that Pages is available on its current plan/visibility. Preserve its current visibility.
2. In the **account** Settings → Pages, add `scientific-parallax.com` as a verified domain. GitHub supplies a TXT challenge. In GoDaddy add the exact TXT name and value displayed by GitHub, then verify it on GitHub. Keep this TXT record after verification.
3. In the **repository** Settings → Pages, select **GitHub Actions** as the build/deployment source. Set **Custom domain** to `scientific-parallax.com` before pointing the website's DNS to GitHub.
4. Review and commit the intended website files, lockfile, workflow and documentation. Exclude local environment files, generated output, and unrelated research edits.
5. Push the reviewed changes to `main`, or merge a reviewed pull request. The **Website · GitHub Pages** workflow tests, builds, verifies and publishes. Pull requests build only; they do not publish. A manual run is also available on `main`.

If GitHub asks for an initial deployment before accepting the custom-domain setting, finish that deployment first, then add the domain **before changing the website's DNS**. The default project URL may have missing assets until the custom domain is configured; the local static check remains the pre-cutover validation.

No `CNAME` file is needed for the custom GitHub Actions publishing method; GitHub's Pages settings hold the domain association.

## 3. Switch only the website DNS in GoDaddy

Do this after GitHub domain verification, the repository domain setting, and a successful deployment. First save/export the existing DNS configuration and confirm the existing root domain is not serving another site that must remain online.

GoDaddy → Domain Portfolio → `scientific-parallax.com` → DNS → DNS Records:

| Type  | Name  | Value                    |
| ----- | ----- | ------------------------ |
| A     | `@`   | `185.199.108.153`        |
| A     | `@`   | `185.199.109.153`        |
| A     | `@`   | `185.199.110.153`        |
| A     | `@`   | `185.199.111.153`        |
| CNAME | `www` | `ryanchromium.github.io` |

TTL may remain at its default. The CNAME value has no protocol or repository path. Replace the old website A records rather than leaving them alongside the GitHub addresses, and update the existing `www` record rather than adding a conflicting duplicate.

Read-only DNS snapshot on 2026-08-31 (recheck immediately before changing):

- Nameservers: `ns35.domaincontrol.com`, `ns36.domaincontrol.com` — **keep these**.
- Existing apex A: `76.223.105.230`, `13.248.243.5` — replace only during cutover.
- Existing `www` CNAME: `scientific-parallax.com` — change to the value above.
- Existing MX: priority 0 `smtp.secureserver.net`, priority 10 `mailstore1.secureserver.net` — **preserve**.
- Existing SPF TXT: `v=spf1 include:spf.em.secureserver.net ?all` — **preserve**.
- No apex AAAA or CAA answer was observed. Recheck for conflicting or restrictive records before cutover.

Do not clear the DNS zone, change nameservers, remove mail records, add wildcard records, or enable domain forwarding. GoDaddy remains the domain registrar and DNS provider; no GoDaddy website-hosting plan is needed.

## 4. Verify the actual public site

1. Confirm the apex resolves to the four GitHub A records and `www` to `ryanchromium.github.io`.
2. Wait for GitHub's DNS check and HTTPS certificate to complete, then enable **Enforce HTTPS**. DNS propagation and certificate availability can take up to 24 hours.
3. Open both language URLs directly, refresh the English page, switch language and projection tabs, and confirm fonts and the social image load.
4. Check `www` redirects to the apex and an unknown URL returns the 404 page, not the homepage with a success response.
5. Test from the user's normal network. A successful build/deployment alone is not proof of reachability; the old Sites access problem must not be assumed resolved without this check.

## Recovery

Keep the pre-cutover GoDaddy DNS snapshot. To return traffic to the old destination, restore **only** the replaced apex A records and `www` CNAME from the current snapshot. The old destination may not have a working HTTPS certificate; restoring DNS alone does not guarantee a working previous website. For a bad website release, restore the last known-good website source and rerun the Pages workflow, without resetting unrelated research work. Retain the domain-verification TXT record.

## References

- [GitHub: custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub: verifying a custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages)
- [GitHub: custom domain and DNS configuration](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
- [GoDaddy: managing DNS records](https://www.godaddy.com/help/manage-dns-records-680)
