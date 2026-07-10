# Channel Answer Evidence Gate

채널톡 고객사의 CX 운영자·상담 관리자가 AI 또는 사람이 작성한 상담 답변을 발송하기 전에, 각 주장을 공개 근거와 연결하고 근거 없는 고위험 결론을 차단하는 Codex 플러그인입니다.

## 공개 문제와 사용자

문제 정의: **CX 운영자·상담 관리자가 AI 초안과 도움말을 함께 검수하는 상황에서, 출처 없는 답변은 추가 확인이 필요하고 공개 리뷰 한 건을 전체 장애·원인·복구로 일반화할 위험 때문에 감사 가능한 상담 답변을 만들기 어려운 문제**입니다.

채널톡 공식 글은 AI 어시스턴트가 FAQ·아티클 기반으로 답변한다고 설명하면서도, 출처가 표시되지 않으면 공식 문서로 추가 확인하라고 권고합니다. 공식 인터뷰는 고객 커뮤니케이션 문제를 회사의 본질로 정의하고(00:18~00:58), 전 직원이 AI를 자기 업무에 쓰게 하는 것이 어렵다고 말하며(01:01~01:24), 도구 수보다 문제 접근과 판단 이유를 본다고 강조합니다(01:46~02:28). 인터뷰의 이커머스 상담·AI 에이전트 과제를 복제하지 않고, 별도 공식 도움말과 공개 앱 리뷰에서 확인되는 검증 병목에 집중했습니다.

## 기존 기능과 차별성

ALF/AI 어시스턴트는 고객 질문 답변, FAQ·아티클 검색, 메시지 요약을 수행합니다. 이 플러그인은 답변을 새로 생성하는 기능이 아니라 **여러 답변 초안을 발송 전 배치 검수**하고 `claim_id → evidence_id → source_id → URL` 추적표와 차단 사유를 JSON으로 남깁니다. 따라서 기존 생성·검색 기능을 대체하지 않고 품질보증과 감사 단계를 보완합니다.

## 설치

`src`가 플러그인 루트입니다. 로컬 마켓플레이스에 `src`를 등록한 뒤 `channel-answer-evidence-gate`를 설치하고 새 Codex 세션을 시작합니다. 공식 구조는 `.codex-plugin/plugin.json`과 `skills/audit-channel-answers/SKILL.md`를 사용합니다.

## 사용

```powershell
python src/scripts/audit_answers.py src/fixtures/valid.json --output report.json
```

Codex에서는 “`audit-channel-answers`로 이 JSON의 상담 답변을 검수해 줘”라고 요청합니다.

## 절차·입출력·판단 기준

## Operation

입력은 `sources[]`와 `answers[]`입니다. 각 공개 출처에는 고유 `source_id`, 제목, 공개 HTTPS URL, 원문 근거(`evidence_id`, `text`)가 필요합니다. 각 답변은 주장별 `claim_id`, 문장, `evidence_ids[]`를 제공합니다.

도구는 스키마와 ID 중복을 검사하고, 연결된 근거·출처 URL을 보존하며, 서비스 전체 장애·장애 원인·복구 완료·성과 향상 표현이 근거 문구에 명시되어 있는지 확인합니다. 모두 통과하면 `READY`와 인용이 붙은 `publishable_answers`를 만듭니다. 정보가 부족하면 `NEEDS_EVIDENCE`와 수정 행동을 반환하고 발송 후보를 만들지 않습니다. 잘못된 입력은 `INVALID_INPUT`, 종료 코드 2이며 traceback을 노출하지 않습니다.

## 후보 비교와 선택

5점 척도(공개 근거/실제 Codex 사용자 적합성/기존 기능 차별성/반복 가치/검증 가능성/구현 가능성)입니다.

| 후보 | 근거 | Codex | 차별성 | 반복 | 검증 | 구현 | 결과 |
|---|---:|---:|---:|---:|---:|---:|---|
| 응대 연속성·알림·계정 운영 진단 | 5 | 4 | 2 | 4 | 4 | 5 | 기존 설정 안내와 중복, 탈락 |
| 공개 VOC→재현·지원 티켓 | 4 | 5 | 4 | 4 | 4 | 5 | 강하지만 리뷰가 재현 조건을 충분히 주지 않는 경우가 많음 |
| 공식 도움말↔상담 답변 근거 검수 | 5 | 5 | 5 | 5 | 5 | 5 | 선정 |

## 공개 출처

- 채널톡, 「우리 채널 맞춤 비서, AI 어시스턴트를 고용해 보세요」, 2025-03-10: https://channel.io/kr/blog/articles/ai-assistant-alf-1ba879b9
- 채널톡, 「상담 알림, 또 놓치실 건가요?」: https://channel.io/kr/blog/articles/notifications-56c7413f
- 채널톡 도움말, 「팔로업 알림」: https://docs.channel.io/help/ko/articles/1ab15b6a
- Apple App Store, Channel Talk 공개 앱 페이지·리뷰: https://apps.apple.com/kr/app/id1088828788
- Google Play, Channel Talk 공개 앱 페이지·리뷰: https://play.google.com/store/apps/details?id=com.zoyi.channel.desk.android
- 조코딩 공식 인터뷰, 「채널톡이 바라보는 AI 시대 인재」, 2026-07-04: https://www.youtube.com/watch?v=5iRf37Z8Wd4
- OpenAI, Plugins/Build plugins/Build skills: https://developers.openai.com/codex/plugins , https://developers.openai.com/codex/plugins/build , https://developers.openai.com/codex/skills

## KPI

- 검수한 주장 중 공개 근거 ID가 유효하게 연결된 비율
- 발송 전 차단된 무근거 고위험 주장 수
- 수정 후 `NEEDS_EVIDENCE`에서 `READY`로 전환된 답변 비율
- 출처 URL·ID가 보존된 검수 보고서 비율

KPI 목표치는 운영 데이터 없이 임의로 제시하지 않습니다.

## 검증 결과

정상 fixture는 `READY`, 정보 부족 fixture는 세 종류의 고위험 추론을 차단해 `NEEDS_EVIDENCE`, 잘못된 입력은 `INVALID_INPUT`/종료 코드 2가 되어야 합니다. 공식 플러그인 validator, SKILL validator, 문법 검사, 단위 테스트, 고유 로컬 마켓플레이스 설치, 새 Codex 프로세스의 실제 skill 호출, ZIP 재검증 결과는 GitHub의 `validation/`에 보관합니다.

## 한계

이 도구는 제공된 근거 문구와 연결을 검사할 뿐 URL의 최신성·진위를 자동 보증하거나 실제 서비스 상태를 관측하지 않습니다. 정규식 기반 고위험 표현 검사는 모든 한국어 변형을 포괄하지 않습니다. 앱 리뷰는 개별 사용자의 보고이며 고객 전체 비율이나 장애 원인을 입증하지 않습니다. 최종 발송 판단은 CX 담당자가 합니다.
