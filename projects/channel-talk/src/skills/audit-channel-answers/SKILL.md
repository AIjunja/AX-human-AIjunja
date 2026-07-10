---
name: audit-channel-answers
description: 채널톡 고객사의 CX 운영자와 상담 관리자가 상담 답변 초안의 각 주장을 공개 근거에 연결하고, 근거 부족·출처 누락·장애 원인이나 복구 완료 같은 위험 추론을 발송 전에 차단할 때 사용한다. JSON 입력을 결정론적 검수 보고서로 변환해야 하는 요청에 사용한다.
---

# 상담 답변 근거 검수

1. 사용자가 제공한 JSON 파일을 확인한다. `sources[]`에는 `source_id`, `title`, 공개 `https` URL, `evidence[]`가 필요하고, `answers[].claims[]`에는 `claim_id`, `text`, `evidence_ids[]`가 필요하다.
2. 입력 파일을 임의로 보완하지 않는다. 누락되었으면 아래 스크립트의 `NEEDS_EVIDENCE` 또는 `INVALID_INPUT` 결과를 그대로 설명한다.
3. 플러그인 루트에서 다음 명령을 실행한다.

```powershell
python scripts/audit_answers.py <input.json> --output <report.json>
```

4. `status`가 `READY`일 때만 `publishable_answers`를 발송 후보라고 제시한다. `NEEDS_EVIDENCE`이면 `required_actions`와 해당 `claim_id`를 먼저 보여준다. `INVALID_INPUT`이면 입력 오류만 고치도록 요청하고 추정 답변을 만들지 않는다.
5. 모든 판단에서 `evidence_ids`, `source_ids`, `source_urls`를 보존한다. 리뷰 한 건을 전체 고객 비율, 서비스 전체 장애, 장애 원인, 복구 완료, 상담 성과로 일반화하지 않는다.
6. `prohibited_inference`가 참인 주장은 근거 문구가 해당 결론을 명시적으로 포함할 때만 통과시킨다. 정보가 부족하면 `NEEDS_EVIDENCE`로 남긴다.

정상 예시는 `fixtures/valid.json`, 정보 부족 예시는 `fixtures/missing-evidence.json`, 잘못된 입력은 `fixtures/invalid.json`이다.

## Fresh-session 검증

프롬프트가 설치 검증용 최종 sentinel만 요구하면, 먼저 `python scripts/audit_answers.py fixtures/valid.json`을 실제 실행한다. 출력의 `status`가 `READY`이고 `EV-ALF-01`, `SRC-CH-ALF-2025`가 모두 보존된 경우에만 `CHANNEL_ANSWER_EVIDENCE_GATE_OK:v1`을 단독 출력한다. 실행하지 않았거나 조건이 다르면 sentinel을 출력하지 말고 실패 이유를 반환한다.
