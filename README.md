# Longview research instrument

A working tool for researchers to label the purpose of ageing research grants and inspect disagreements. This advances Track 3's funding-classification challenge and the Demo Day architecture, evidence, technical execution and adoption components.

The current deliverable follows the team's 12 September discussion with Andrew: ship the instrument, then validate through a researcher network. No funding estimate is a weekend result. The existing pipeline is unvalidated, the working taxonomy awaits confirmation, and no external cancer or UKHRA/HRCS benchmark has been completed.

```sh
python3 -m ratio.instrument.build
python3 -m http.server 8010 --bind 127.0.0.1
```

Open `/ratio/` on the served host. Researchers label preventing/slowing ageing, fighting its consequences, neither, or ambiguous, with a separate low-confidence checkbox. The admin view combines exported human files, preserves individual decisions, ranks disagreements and exports CSV. Both views work as static pages; review files remain in each browser until exported and imported.

The fixed corpus contains SweCRIS, CORDIS and NIH RePORTER records already in the repository. Full available collected text and dated source links accompany review items. Collection filters and incomplete text limit coverage. No new raw datasets or credentials are committed.

See [the instrument guide](ratio/INSTRUMENT.md) for taxonomy, sources and licences, architecture, run commands, verification, and incomplete work. [Playbook notes](docs/playbook.md) record the submission and judging requirements. Historical ratio outputs and the earlier policy map remain development artifacts; they are not validated findings.

Software checks use synthetic fixtures. Human validation, a frozen final evaluation, and the 90% human-agreement target remain incomplete. No clinical claims.
