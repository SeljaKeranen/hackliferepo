# Hosting and handover

This advances the live Demo Day demo and recorded/offline fallback. The app builds as static files for Vercel or Netlify. It needs no provider credentials at runtime. Human evidence review and account-owned persistent hosting remain separate from deployment.

The latest preview URL, claim link and expiry live in ignored `outputs/deployment.json`. Anonymous Vercel temporary deployments expire unless claimed in a real account. A team member can claim the concrete preview using that link. Do not describe a temporary URL as permanent, and do not assume a redeploy extends its lifetime.

Build the funding report and matching delivery artifacts using the root README. After human approval, set `PUBLIC_SITE_URL` to the intended HTTPS hosting origin before running `funding.release`; approved schema-compatible findings cite the dated report permalink and its complete source ledger. A pending release needs no public origin to build.

```bash
.venv/bin/python -m funding.release
node scripts/package-funding-review.mjs
node scripts/check-funding-browser.mjs
.venv/bin/python -m funding.deck
node scripts/record-funding-demo.mjs
.venv/bin/python -m funding.delivery
npm run build
.venv/bin/python -m funding.delivery --offline
.venv/bin/python -m scripts.security-check
```

With an authenticated Vercel account, the root `vercel.json` builds Vite and publishes `dist`. Netlify uses `netlify.toml`. Audit upload contents before using a root deployment: `.vercelignore` excludes raw data, keys and local outputs. The temporary workflow instead copies only the tested `dist` contents and static routing configuration into a fresh isolated directory under `outputs/`, then deploys that directory. Its `.vercel` state stays ignored.

For a known host URL, `python -m funding.host --origin https://YOUR-HOST --output outputs/YOUR-STAGING-DIRECTORY` prepares isolated static files with absolute social-image and report URLs. Offline paths remain relative.

Verify `/`, `/country/sweden`, `/country/united-states`, `/sources`, `/method`, both reviewer pages, the immutable `/reports/<release>/<country>/` URLs and all four delivery downloads. The route exclusions must preserve actual static funding, report, review, asset and download files.

The funding reviewer key is in ignored `outputs/funding-reviewer.key`; the earlier policy key is in `outputs/reviewer.key`. Use a `#key=...` fragment. The browser decrypts locally, clears the fragment and stores verdicts on that browser. Export real human JSON for the team's version-checked import. No provider API key is exposed by this workflow.

Temporary link renewal, account ownership and the organiser repository upload are separate tasks. The Sunday submission window opens at 11:00 and closes at 12:00 according to the checked playbook notes; a team member needs organiser upload access. This implementation does not submit the project on the team's behalf.
