---
description: Capture a new entry in INCIDENTS.md from the latest workspace run. Human-gated curation step of the Anamnesis Pattern's Curate beat. Drafts a candidate entry; the user confirms before append.
argument-hint: "<one-line description of the failure>"
---

# /log-incident

The user just observed a failure in the most recent run and wants to add a permanent rule to `INCIDENTS.md` so it cannot recur. This command implements the **Curate** beat of the Anamnesis Pattern (see `references/anamnesis_pattern.md`).

## What you should do

1. **Read the user's `$ARGUMENTS`** — a short description of what went wrong.
2. **Pick the latest workspace run** — the most recently modified directory under `workspace/{Company}_{Date}/`. If none exists, ask the user to point you at the run dir.
3. **Run the collector** to gather a structured digest of that run:

   ```bash
   python3 tools/io/log_incident.py --collect --workspace workspace/<latest_run>/ --description "$ARGUMENTS"
   ```

   This prints a JSON digest of the run's validator outputs, structure-conformance, red-team outputs (if present), and the resolved P0 gate values. It does **not** write to `INCIDENTS.md`.
4. **Read `INCIDENTS.md`** to see the existing entry format and the next available `I-NNN` id.
5. **Draft a candidate entry** matching the existing format (Phase, What happened, Root cause, Rule (load-bearing), Detection, Related contract). Use concrete paths and values from the digest, not generic prose.
6. **Show the candidate entry to the user** as a proposed `INCIDENTS.md` append — do not write it yet.
7. **Wait for explicit user confirmation.** Acceptable confirmations: `yes`, `confirm`, `append`, `ok 写入`, `OK`. Anything else (including silence) means do not append.
8. **On confirmation, append** the entry to `INCIDENTS.md` (do not rewrite or reorder existing entries; append-only). Print the path and the appended id back to the user.

## Hard rules

- **Append only.** Never delete, reorder, or rewrite existing `INCIDENTS.md` entries. If a past entry is now incorrect, supersede it with a *new* entry that links back via `Related contract:`.
- **Human gate is non-negotiable.** Do not append without an explicit user confirmation. Auto-mode does not override this.
- **No PII.** If the digest contains the user's email (e.g. surfaced from a `User-Agent` string in `data_source` fields), strip it before quoting in the entry.
- **Specific, not generic.** Cite the actual run dir path, the actual workspace JSON paths, the actual values that were wrong. Generic entries don't earn a permanent slot in the system prompt.
- **One rule per entry.** If the user describes two distinct failures, draft two entries and confirm separately.

## What "load-bearing rule" means

The `Rule (load-bearing):` field of an `INCIDENTS.md` entry must be:

- **Enforceable** — written as something a future run can be checked against (a path, a whitelist, a test). Not advice ("be careful"), not aspirations ("do better").
- **Specific** — naming the file, phase, or field that must hold a particular property. "Never invent profile names; profiles must come from `workflow_meta.json -> packaging_profiles`" is enforceable. "Be more careful with profiles" is not.
- **Detectable** — paired with a `Detection:` field naming the file or test that signals violation. If you can't name the detector, the rule is a wish.

If you cannot draft an entry that meets all three, tell the user — don't append a wish-grade entry just to discharge the slash command.
