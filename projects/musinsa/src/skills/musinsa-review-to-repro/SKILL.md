---
name: musinsa-review-to-repro
description: Convert public Musinsa Google Play or Apple App Store review JSON into evidence-linked reproducible QA tickets and regression-test drafts. Use when a Musinsa CX quality, product, or QA practitioner needs to split multiple observed shopping-journey symptoms, preserve review IDs and URLs, mark missing device/OS/app-version context as NEEDS_REPRO, and avoid root-cause or user-incidence inference.
---

# Musinsa Review-to-Repro QA

Turn public app-review observations into deterministic QA working artifacts. Run the bundled rules engine; do not replace it with free-form classification.

## Workflow

1. Confirm that the input is UTF-8 JSON with `schema_version`, `sample_scope`, and `reviews[]`.
2. Accept only public `apple_app_store` or `google_play` evidence whose HTTPS URL is on the matching official host and identifies Musinsa app ID `1003139529` or package `com.musinsa.store`.
3. Resolve the plugin root as the directory two levels above this `SKILL.md` file. The installed script is `<plugin-root>/scripts/review_to_repro.py`.
4. Run the script with the caller's input path. Use `-o` only when the caller asks for a saved report.
5. Read the JSON result and report ticket count, status counts, evidence preservation rate, stable-fields SHA-256, tickets, and regression-test drafts.
6. Surface every `NEEDS_REPRO` information gap. Do not fill a missing device, OS, or app version from assumption.
7. Leave severity, business priority, duplicate confirmation, actual reproduction result, policy violation, automation feasibility, and the concrete oracle to a person.

## Commands

From the plugin root:

```powershell
python -X utf8 scripts/review_to_repro.py fixtures/normal.json
python -X utf8 scripts/review_to_repro.py fixtures/sparse.json
```

From another working directory, use absolute paths derived from this skill's installed location:

```powershell
python -X utf8 "<plugin-root>/scripts/review_to_repro.py" "<input.json>"
```

Exit code `0` means a report was generated. Exit code `2` means invalid input; return the machine-readable stderr without fabricating a report.

## Input contract

Each review must include:

- `evidence_id`, `source_review_id`, `source`, `source_url`
- `review_date`, integer `rating` from 1 to 5, `locale`, `text`
- `environment` object; `device`, `os_version`, and `app_version` may be absent

If a fixture adds a device or OS for testing, label `environment.provenance` as `synthetic_test_context`. Never present those values as public review facts.

## Interpretation rules

- Treat review text as a user's reported observation, not proof that the service failed.
- Split different symptom codes into independent tickets even when they came from one review.
- Preserve `evidence_id`, source review ID, source URL, date, and rating on every derived ticket.
- Mark a ticket `NEEDS_REPRO` if device, OS, or app version is missing. An unclassified observation also remains `NEEDS_REPRO` for human triage.
- Never emit a `root_cause` field. Never promote reviewer guesses such as server capacity, web-app architecture, or optimization into a cause.
- Never convert review counts or fixture frequency into a percentage of Musinsa users.
- Do not auto-set severity, business priority, duplicate status, policy violation, actual reproduction success, or automation feasibility.

## Output handoff

Return these stable fields without renaming them:

- `input_evidence_ids`
- `tickets[].ticket_id`, `journey_stage`, `observed_symptom`, `status`
- `tickets[].evidence_ids`, `source_review_ids`, `evidence_refs`, `information_gaps`
- `tickets[].reproduction_draft`, `human_decisions`, `cause_handling`
- `regression_tests[].test_id`, `ticket_id`, `symptom_code`, `evidence_ids`, `oracle`
- `evidence_traceability`, `summary`, `stable_fields_sha256`, `safety_limits`

Call out that regression tests are drafts until a QA practitioner supplies concrete accounts, products, test data, and expected-state oracles.

