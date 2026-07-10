---
name: audit-channel-answers
description: 채널톡 고객사의 CX 운영자와 상담 관리자가 답변 초안과 공식 source URL을 제공하면 주장을 자동 분리하고 정확 인용·위치가 담긴 evidence packet을 구성한 뒤 SUPPORTED, HUMAN_REVIEW, NEEDS_EVIDENCE로 발송 전 검수할 때 사용한다.
---

# 상담 답변 근거 검수

1. 사용자가 답변 초안과 공식 URL을 주면 URL을 열어 원문을 확인하고 `retrieved_at`, `source_text`를 포함한 raw workflow JSON을 만든다. 사용자가 `claim_id`나 `evidence_id`를 직접 작성하게 하지 않는다.
2. 플러그인 루트에서 다음 명령을 실행한다.

```powershell
python scripts/audit_answers.py <raw-draft.json> --output <workflow-report.json>
```

3. 결과의 `evidence_packet`에서 자동 분리된 주장, 정확한 `quote`, 문자 기준 `location`, `source_id`, `content_sha256`을 확인한다.
4. `report.claim_results`를 다음처럼 해석한다.
   - `SUPPORTED`: 검증된 source_text의 정확한 인용에 주장 문장이 직접 포함된다.
   - `HUMAN_REVIEW`: 관련 인용 후보는 있지만 의역이라 결정론적으로 같은 뜻인지 확정할 수 없다.
   - `NEEDS_EVIDENCE`: 근거가 없거나 무관하거나, 전체 장애·원인·복구 완료 같은 고위험 결론을 직접 진술한 정확한 인용이 없다.
5. `READY`일 때만 `publishable_answers`를 발송 후보로 제시한다. `HUMAN_REVIEW`는 담당자 확인 전 발송하지 않는다. `NEEDS_EVIDENCE`는 직접 인용을 추가하거나 결론을 삭제한다.
6. 리뷰 한 건을 전체 고객 비율, 서비스 전체 장애, 장애 원인, 복구 완료, 상담 성과로 일반화하지 않는다.

사용자가 이미 evidence packet을 제공하면 동일 스크립트로 직접 검수한다. `source_text`가 있으면 모든 quote가 지정 위치에 실제로 존재해야 한다. source_text 없이 `content_sha256`만 있으면 자동 `SUPPORTED`로 판정하지 않는다.

## Fresh-session 검증

설치 검증 요청에서는 `python scripts/audit_answers.py fixtures/raw-draft.json`을 실제 실행한다. 출력에서 자동 생성 claim 2개, evidence 2개, 두 결정이 모두 `SUPPORTED`, 최종 상태가 `READY`인지 확인한 뒤 다음 결과 요약만 출력한다.

```text
claim_count=2;evidence_count=2;decisions=SUPPORTED,SUPPORTED;status=READY
```

조건이 다르면 성공 요약을 출력하지 말고 실제 실패 결과를 반환한다.
