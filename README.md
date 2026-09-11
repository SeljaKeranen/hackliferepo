# hackliferepo

Team repo for the Stockholm Longevity x AI Hackathon, 11 to 13 September 2026 at Epicenter Stockholm. Team: Selja, Max, Jan.

**Status: track and challenge decided. Nothing is built yet.**

We take Track 3 (Communication, Trust & Policy), challenge 1: [map the politics of longevity](docs/challenge.md) — an AI research agent that produces a cited, time-stamped global map of political engagement with longevity. Full brief and plan in [docs/challenge.md](docs/challenge.md).

## What we know

- Hacking starts Friday 18:30 after team formation. The venue closes at 21:00 on Friday and Saturday, so there is no overnight work.
- Submission deadline is Sunday 12:00, and the upload link to the [hackathon repository](https://github.com/OxbridgeFrontier/Stockholm-AI-x-Longevity-Hack-2026) only opens Sunday 11:00, so the repo must be push-ready before 11:00.
- Judges weight impact 20%, path to real-world adoption 10%, technical execution 20%, novelty 20%, evidence and responsible use 10%, track fit 10%, demo and communication 10% (re-checked against the live playbook 11 September).

See [playbook notes](docs/playbook.md) for the schedule, submission checklist, and links, [track challenges](docs/tracks-challenges.md) for the five tracks and their challenges, and [data resources](docs/data-resources/data-resources.md) for the dataset library.

## Initial goal

1. Lock the data schema for a "finding" first: country/region, classification, claim, source URL, source date, confidence.
2. Build the research agent plus a roughly 30–50 finding human-verified benchmark on Saturday, and report accuracy against it.
3. Keep the map UI simple. Coverage explicitly matters less than accuracy.
4. Data source and licence written down before any modelling starts.

## Team

| Person | Owns | First deliverable |
| --- | --- | --- |
| Selja | to agree | |
| Max | to agree | |
| Jan | to agree | |

The playbook recommends covering domain, technical, and product or communication strengths. Fill this in on Friday.

## Repository layout

Create directories as work starts. Raw and restricted data stay out of git; see `.gitignore`.

```text
docs/
  playbook.md            Event facts, deadlines, judging, links
  challenge.md           Our selected challenge and initial plan
  tracks-challenges.md   The five tracks and their challenges
  data-resources/        Dataset library with access and licence notes
data/                  Local datasets, ignored
```

Shared agent skills live in `.agents/skills/`; see [AGENTS.md](AGENTS.md).
