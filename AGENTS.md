# Delivery focus

## Shared skills

Repository skills live in `.agents/skills/` and are also available through `.claude/skills/`.

- [avoid-ai-writing](.agents/skills/avoid-ai-writing/SKILL.md): audit or edit writing while preserving meaning, evidence, and technical uncertainty.

Use it on anything a judge or mentor will read: README, docs, pitch notes, the Demo Day summary. It does not replace the submission requirements below and does not authorise publishing.

## Judging alignment

The delivery target is the Sunday 12:00 submission and the Demo Day pitch. Before implementing work and in every PR or change summary, state:

- Which Demo Day component or judging criterion it advances. See [playbook notes](docs/playbook.md).
- What now works, with verification evidence. Identify fixtures, simulations, and unverified claims.
- What remains incomplete.

The demo centerpiece is the index map under `map/` (run command, both layer formulas and vendored-asset provenance in `map/README.md`). Its visible funding-gap layer reads `ratio/output/`; the original politics layer reads `eval/findings/` and `eval/verdicts/` and is retained but hidden from the header. Both read only built JSON and stay decoupled from the eval loop, which works standalone.

Evidence over theatre. Every material finding, classification, or claim links to a dated source. Findings follow `schema/finding.schema.json` and are human-verified with the eval loop in `eval/README.md` (`python3 eval/server.py`). State uncertainty and failure modes. Where the track brief asks for a falsification criterion or a held-out evaluation, build for generalisation rather than the visible data.

Document each dataset's source and licence before using it. Do not commit raw datasets, restricted data, credentials, or anything identifiable. Restricted, paid, private, or identifiable data needs explicit permission and safeguards. Be explicit about what the prototype can and cannot do, especially for anything health related. No clinical claims.

Prefer the smallest prototype judges can see or test, plus a recorded fallback. Defer work without a clear contribution to the submission.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
