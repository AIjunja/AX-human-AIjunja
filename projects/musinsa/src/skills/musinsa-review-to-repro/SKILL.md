---
name: musinsa-review-to-repro
description: Convert public Musinsa Google Play or Apple App Store review JSON into evidence-linked QA tickets with reproduction readiness gaps and symptom-specific regression-test drafts. Use when a Musinsa CX quality, product, or QA practitioner needs to split multiple shopping-journey symptoms, preserve exact matched text and review IDs, verify per-field environment provenance, and avoid root-cause or user-incidence inference.
---

# Musinsa Review-to-Repro QA

Turn public app-review observations into deterministic QA working artifacts. Run the bundled rules engine; do not replace it with free-form classification.

## Workflow

1. Confirm that the input is UTF-8 JSON with `schema_version`, `sample_scope`, and `reviews[]`.
2. Accept only public `apple_app_store` or `google_play` evidence whose HTTPS URL is on the matching official host and identifies Musinsa app ID `1003139529` or package `com.musinsa.store`.
3. Resolve the plugin root as the directory two levels above this `SKILL.md` file. The installed script is `<plugin-root>/scripts/review_to_repro.py`.
4. Run the script with the caller's input path. Use `-o` only when the caller asks for a saved report.
5. Read the JSON result and report ticket count, status counts, evidence preservation rate, stable-fields SHA-256, tickets, matched evidence, and symptom-specific regression-test drafts.
6. Surface every environment information gap. `TEST_SCENARIO_ONLY` means one or more populated values are synthetic. `NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION` means values or trusted per-field provenance are missing.
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
- `review_date`, integer `rating` from 1 to 5, and `locale`
- Prefer `raw_review_text` plus its `raw_text_sha256`. If only normalized text is available, use `normalized_observation`, `normalization_method`, and `source_raw_text_sha256`; never label it raw.
- `environment` object; `device`, `os_version`, and `app_version` may be absent

`environment.provenance` must map each populated field to `review_reported`, `store_metadata`, `verified_test_run`, or `synthetic_test_context`. An aggregate provenance string is not enough for `READY_FOR_REPRO`. Synthetic values can only produce `TEST_SCENARIO_ONLY`.

## Interpretation rules

- Treat review text as a user's reported observation, not proof that the service failed.
- Split different symptom codes into independent tickets even when they came from one review.
- Preserve `evidence_id`, source review ID, source URL, date, and rating on every derived ticket.
- Return `READY_FOR_REPRO` only when device, OS, and app version all exist and each has trusted per-field provenance: `review_reported`, `store_metadata`, or `verified_test_run`.
- Add `matched_evidence` with the exact matched substring, start/end offsets, source-text SHA-256, text basis, evidence ID, and source review ID.
- Use symptom-specific reproduction steps and oracle contracts. Keep numeric thresholds and expected policies in `human_defined_thresholds` for a person to supply.
- Never emit a `root_cause` field. Never promote reviewer guesses such as server capacity, web-app architecture, or optimization into a cause.
- Never convert review counts or fixture frequency into a percentage of Musinsa users.
- Do not auto-set severity, business priority, duplicate status, policy violation, actual reproduction success, or automation feasibility.

## Output handoff

Return these stable fields without renaming them:

- `input_evidence_ids`
- `tickets[].ticket_id`, `journey_stage`, `observed_symptom`, `status`
- `tickets[].evidence_ids`, `source_review_ids`, `evidence_refs`, `information_gaps`
- `tickets[].matched_evidence`, `reproduction_draft`, `human_decisions`, `cause_handling`
- `regression_tests[].test_id`, `ticket_id`, `symptom_code`, `evidence_ids`, `oracle_type`, `required_observations`, `human_defined_thresholds`
- `evidence_traceability`, `summary`, `stable_fields_sha256`, `safety_limits`

Call out that regression tests are drafts until a QA practitioner supplies concrete accounts, products, test data, and expected-state oracles.
