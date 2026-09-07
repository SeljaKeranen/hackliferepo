# hackliferepo

Team repo for the Stockholm Longevity x AI Hackathon, 11 to 13 September 2026 at Epicenter Stockholm. Team: Selja, Max, Jan.

**Status: nothing is built yet. Track and challenge are undecided.**

## What we know

- Hacking starts Friday 18:30 after team formation. The venue closes at 21:00 on Friday and Saturday, so there is no overnight work.
- Submission deadline is Sunday 12:00. Finalist pitches start 13:00, awards 15:00.
- On Sunday one team member asks the organisers for access to upload our repo to the [hackathon repository](https://github.com/OxbridgeFrontier/Stockholm-AI-x-Longevity-Hack-2026).
- Judges weight impact 30%, technical execution 20%, novelty 20%, evidence and responsible use 10%, track fit 10%, demo and communication 10%.

See [playbook notes](docs/playbook.md) for the schedule, tracks, submission checklist, and links, and [data resources](docs/data-resources.md) for the dataset library.

## Decide first

1. Track and challenge. Tracks 1 (longevity biology) and 3 (communication, trust, policy) have written briefs with required outputs. Track 2 (Nebius infrastructure) is announced before the event. Tracks 4 (clinical translation) and 5 (wildcard) are open.
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
  playbook.md          Event facts, deadlines, judging, links
  data-resources.md    Dataset library with access and licence notes
data/                  Local datasets, ignored
```

Shared agent skills live in `.agents/skills/`; see [AGENTS.md](AGENTS.md).
