# hackliferepo

Team repo for the Stockholm Longevity x AI Hackathon, 11 to 13 September 2026 at Epicenter Stockholm. Team: Selja, Max, Jan.

**Status: nothing is built yet. Track and challenge are undecided.**

## What we know

- Hacking starts Friday 18:30 after team formation. The venue closes at 21:00 on Friday and Saturday, so there is no overnight work.
- Submission deadline is Sunday 12:00. Finalist pitches start 13:00, awards 15:00.
- On Sunday one team member asks the organisers for access to upload our repo to the [hackathon repository](https://github.com/OxbridgeFrontier/Stockholm-AI-x-Longevity-Hack-2026).
- Judges weight impact 30%, technical execution 20%, novelty 20%, evidence and responsible use 10%, track fit 10%, demo and communication 10%.

See [playbook notes](docs/playbook.md) for the schedule, submission checklist, and links, [track challenges](docs/tracks_challenges.md) for the five tracks and their challenges, and [data resources](docs/data-resources/data-resources.md) for the dataset library.

## Decide first

1. Track and challenge. For the five tracks and their challenges, see [tracks-challenges.md](docs/tracks_challenges.md).
2. The one result we can show with evidence by Sunday 12:00. A narrow, checked result beats a broad survey in every track brief.
3. Data source and licence, written down before any modelling starts.

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
  tracks_challenges.md   The five tracks and their challenges
  data-resources/        Dataset library with access and licence notes
data/                  Local datasets, ignored
```

Shared agent skills live in `.agents/skills/`; see [AGENTS.md](AGENTS.md).
