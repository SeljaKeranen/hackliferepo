# Deployment and handover

This advances the live Demo Day demo and its fallback. The static Vercel preview is reachable, including deep links and the encrypted team review page. Persistent account ownership and final human evidence review remain required for the submission.

The current site is a temporary Vercel deployment. Its claim URL and expiry are recorded in ignored `outputs/deployment.json`. The team must claim it in Vercel to keep it beyond the temporary lifetime. The private review link contains a browser-only decryption key in the URL fragment; share it only with reviewers. It is not a research-provider API key.

After generating the deck and recording using the README commands, build and publish only the static output:

```bash
.venv/bin/python -m pipeline.release
node scripts/package-review.mjs
.venv/bin/python scripts/package-delivery.py
npm run build
.venv/bin/python scripts/package-delivery.py --offline
.venv/bin/python -m scripts.security-check
```

For an authenticated account, `npx vercel deploy --prod` uses the root Vite configuration. Audit upload contents first with `npx vercel deploy --dry --json`; never upload `keys`, raw `data/`, review histories or `outputs/reviewer.key`. The implementation's temporary deployment uses an isolated directory containing only `dist/` and a static Vercel configuration. It can be updated using `npx vercel deploy outputs/deploy-preview --temporary --yes` until claimed; inspect the returned status and expiry each time.

Netlify can use `netlify.toml` with `npm run build` and publish directory `dist`. No API keys are needed by either host. The reviewer packet contains only encrypted candidate text; approved findings and derived model summaries are public JSON.

Before final publication, import team reviews, run `python -m pipeline.release --strict`, run the tests and regenerate screenshots, slides and the recording. A pending release can demonstrate the numerical model but cannot claim the evidence benchmark is complete.

A fresh browser should be able to select all three countries, follow a source, reset a scenario, open a shared deep link, read the 90% requirement and print a brief. Also verify the private review page's export. Keep the WebM recording and a local copy of the build for Demo Day. Organiser repository upload access is separate from hosting and must be obtained by a team member.
