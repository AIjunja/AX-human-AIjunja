---
name: build-public-incident-intake
description: Use when a Kakao Pay Securities service-operations or QA reviewer needs to turn public app reports and public official notices into a source-ID-preserving initial incident-intake packet. Also use for the bundled normal or insufficient fixtures and installation proof. Never use for investment advice, trade execution, loss calculation, compensation or fault decisions, root-cause inference, or personal/account data.
---

# Build Public Incident Intake

## Purpose and trigger

Build a deterministic, public-evidence-only intake packet for a human service-operations or QA reviewer. Invoke this skill when the request mentions public outage reports, public VOC triage, an evidence registry, the bundled fixtures, or `KPS_PUBLIC_INCIDENT_INTAKE_OK`.

This workflow structures what public sources state. It does not confirm an internal incident, a customer's individual experience, an outage duration, a cause, fault, compensation, loss, or a trading decision.

## Inputs

Accept one UTF-8 JSON file conforming to `schemas/public-incident-intake.schema.json` at the plugin root. Required top-level fields are:

- `schema_version`: exactly `1.0.0`
- `case_id`: stable uppercase identifier
- `observed_window.start` and `.end`: timezone-aware ISO datetimes
- `public_reports`: at least one public source record
- `official_sources`: zero or more public official records

Every record must carry a unique `evidence_id`, the source's stable `source_record_id`, a public HTTPS `source_url`, `source_type`, `published_at`, `captured_at`, and the source text. Do not accept names, phone numbers, email addresses, resident-registration numbers, account numbers, or order numbers.

## Workflow

1. Locate the plugin root: it is two directories above this `SKILL.md` file.
2. Read `references/public-sources.json` only to understand source roles and limitations. Do not treat it as a substitute for records in the input.
3. Confirm that the requested input is a public-evidence JSON file. Refuse private account, order, or customer identifiers.
4. Preserve the input file. Do not silently edit, normalize, or delete its records.
5. From the plugin root, execute:

   `python -B -X utf8 scripts/build_incident_intake.py <input-json> --compact`

6. If the command exits `2`, report its structured `code` and `path` values and ask for corrected public input. Do not produce a success proof.
7. If it succeeds, inspect `workflow_status`, `source_coverage`, `evidence_registry`, `temporal_association`, `reported_signals`, `official_corroboration`, `source_conflicts`, `missing_information`, `human_review`, `prohibited_conclusions`, and `safety_review`.
8. Verify that every input `evidence_id` and `source_record_id` is present in `evidence_registry`, `safety_review.result` is `PASS`, and all six prohibited conclusions are `NOT_ASSESSED`.
9. Present the packet to the human reviewer. `READY_FOR_HUMAN_TRIAGE` means the minimum public-source combination was met; it never means an incident, cause, fault, loss, or compensation was established. `NEEDS_MORE_PUBLIC_INFORMATION` is a valid non-error result; list only the reported missing fields.
10. Leave the final operational, QA, compliance, and customer-response decisions to authorized people using authorized internal telemetry.

## Source and judgment rules

- Treat an app review as a public report, not as a verified event or verified affected customer.
- Treat a company notice as evidence only of what the company publicly stated. Correlation is limited to the supplied time window.
- A date-only report `published_at` on a day touched by the observed window is an `UNRESOLVED_DATE_ONLY_SAME_DAY` candidate, never an exact in-window observation. A date-only official source cannot corroborate a narrow time window.
- Only `kps_official_notice` records can satisfy company-official window corroboration or the READY gate. Preserve `public_standard` and `public_market_notice` records as context, but never treat them as Kakao Pay Securities confirmation.
- The interval between two notice publication times is not an outage duration.
- A public industry standard supplies context, not evidence that Kakao Pay Securities violated it.
- Signal codes such as `UNAVAILABLE` or `ORDER_CONTROL` are text observations, not diagnoses.
- A source conflict always remains `HUMAN_REVIEW_REQUIRED`.
- Never add evidence, fill a missing reproduction detail, or infer an unreported cause.

## Installation and fixture proof

For an installation verification request, use the real workflow, not a stand-alone echo. From the plugin root:

1. Run `python -B -X utf8 scripts/build_incident_intake.py fixtures/normal.json --compact`.
2. Inspect the full JSON using steps 7 and 8 above.
3. Only after that command succeeds, run `python -B -X utf8 scripts/build_incident_intake.py fixtures/normal.json --proof-only`.
4. Return exactly the emitted proof line if the caller explicitly requests proof-only output.

If an installation smoke request invokes this skill without naming an input path, use the installed
plugin's own `fixtures/normal.json` and its own `scripts/build_incident_intake.py`; do not search for
or use another company's fixture.

The expected bundled-fixture line is:

`KPS_PUBLIC_INCIDENT_INTAKE_OK:v1|case=KPS-PUBLIC-2026-06-30-A|status=READY_FOR_HUMAN_TRIAGE|evidence=4|reports=2|official=2|preserved=100%|forbidden=PASS`

Never return that line when either execution failed, when the full JSON was not inspected, or when its safety checks differ.

## Exceptions

- Missing Python or unreadable file: report the execution blocker; do not simulate output.
- `INPUT_VALIDATION_FAILED`: return the structured errors without echoing sensitive input text.
- Insufficient sources: keep `NEEDS_MORE_PUBLIC_INFORMATION`; do not upgrade it manually.
- Source divergence: preserve both source IDs and require human review.
- Any non-`PASS` safety result, missing evidence ID, or assessed prohibited conclusion: stop and report validation failure.

## Output contract

Return the generated packet without renaming stable fields. When summarizing for a human, include:

- case ID and workflow status
- source counts and evidence IDs
- exact, date-only unresolved, outside-window, and topic-irrelevant association IDs
- observed signal codes with supporting evidence IDs
- official window-correlation status and IDs
- conflicts and missing information
- required human review actions
- the six `NOT_ASSESSED` prohibited conclusions

Do not repeat raw source text unless the human explicitly needs to inspect a short public excerpt; prefer hashes and source URLs.
