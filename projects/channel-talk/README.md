# Channel Answer Evidence Gate

채널톡 고객사의 CX 운영자·상담 관리자가 답변 초안과 공식 source URL만 제공하면, 주장을 자동 분리하고 정확 인용 기반 evidence packet과 발송 전 검수 보고서를 만드는 Codex 플러그인입니다.

## 공개 문제와 사용자

문제 정의: **CX 운영자·상담 관리자가 AI 답변 초안을 검수할 때, 출처가 표시되지 않은 답변은 공식 문서로 다시 확인해야 하므로 주장 분리·원문 탐색·인용 기록을 반복해야 하고 감사 가능한 답변을 만들기 어려운 문제**입니다.

채널톡 공식 글은 AI 어시스턴트가 FAQ·아티클 기반으로 답변한다고 설명하면서도, 출처가 표시되지 않으면 공식 문서나 가이드로 추가 확인하라고 직접 권고합니다. 이 플러그인은 그 확인 병목을 `draft + 공식 URL → claims → exact quotes → evidence packet → audit report`로 구조화합니다. 앱 리뷰는 문제의 중심 근거가 아니라, 개별 보고를 전체 장애·원인·복구로 확대하면 안 된다는 예외 fixture에만 사용합니다.

## 기존 기능과 차별성

ALF/AI 어시스턴트는 고객 질문 답변, FAQ·아티클 검색, 메시지 요약을 수행합니다. 이 플러그인은 답변을 생성하지 않고, 초안을 발송하기 전에 원문 위치와 인용을 검증해 `SUPPORTED`, `HUMAN_REVIEW`, `NEEDS_EVIDENCE`로 분리하고 감사 가능한 JSON을 남깁니다. 알림 진단 후보는 채널톡의 기존 설정 가이드와 중복되어 선택하지 않았습니다.

## 설치

`src`가 플러그인 루트입니다. 로컬 마켓플레이스에서 설치한 뒤 새 Codex 세션을 시작합니다.

## 사용과 입력 UX

사용자는 claim/evidence ID를 만들 필요가 없습니다. 답변 초안과 공식 URL을 주면 Codex가 URL 원문을 확인해 다음 raw 입력을 구성합니다.

```json
{
  "draft_id": "DRAFT-1",
  "draft": "검수할 답변 초안입니다. 두 번째 주장입니다.",
  "sources": [{
    "source_id": "SRC-1",
    "title": "공식 문서",
    "url": "https://official.example/guide",
    "retrieved_at": "2026-07-10T13:00:00Z",
    "source_text": "직접 확인한 공식 원문"
  }]
}
```

```powershell
python src/scripts/audit_answers.py src/fixtures/raw-draft.json --output workflow-report.json
```

## Operation

스크립트는 초안을 문장 단위 claim으로 분리하고 `CLM-*`를 부여합니다. 각 source_text에서 직접 일치 문장 또는 의미상 관련 후보를 찾고 `EV-*`, 정확한 quote, UTF-8 문자 기준 start/end 위치, 원문 SHA-256을 포함한 evidence packet을 구성한 뒤 즉시 검수합니다.

- `SUPPORTED`: quote 위치가 source_text와 일치하고 claim 문장이 quote에 직접 포함됨
- `HUMAN_REVIEW`: 관련 인용이지만 의역이라 자동 확정 불가
- `NEEDS_EVIDENCE`: 근거 없음·무관한 evidence·미등록 ID·고위험 결론의 직접 인용 부재

서비스 전체 장애·원인·복구 완료는 위험 단어가 원문 어딘가에 흩어져 있는 것으로 통과하지 않습니다. 전체 결론을 직접 진술한 정확한 인용이 있어야 합니다. HTTPS URL의 loopback, 사설, link-local, multicast, reserved, unspecified IP도 거부합니다.

## 공개 출처

- 채널톡, 「우리 채널 맞춤 비서, AI 어시스턴트를 고용해 보세요」: https://channel.io/kr/blog/articles/ai-assistant-alf-1ba879b9
- 조코딩 공식 인터뷰: https://www.youtube.com/watch?v=5iRf37Z8Wd4
- 예외 fixture용 공개 앱 페이지: https://apps.apple.com/kr/app/id1088828788

## 검증과 KPI

자동 테스트는 기존 4개 회귀 항목과 raw workflow, 무관 evidence, 의역, 고위험 단어 분산, quote 위치, 비공개 IP를 검사합니다. KPI는 직접 인용 연결률, HUMAN_REVIEW 해소율, 무근거 고위험 주장 차단 수이며 운영 데이터 없는 목표값은 만들지 않습니다.

## 로그 최종화

현재 실행 중인 세션 prefix를 전체 로그라고 주장하지 않습니다. 스레드가 완전히 종료된 뒤 `src/scripts/finalize-channel-talk.ps1 -TranscriptPath <종료된-jsonl> -HarnessRoot <plugin-harness> -OutputZip <zip>`을 실행합니다. 스크립트는 transcript를 독점 열 수 있을 때만 byte-for-byte 복사하고 SHA-256 일치, 비밀 패턴, ZIP 구조와 해시를 검증합니다.

## 한계

Codex가 URL에서 확보한 source_text의 완전성과 최신성은 담당자가 확인해야 합니다. 직접 문자열 일치만 자동 지지하므로 올바른 의역도 HUMAN_REVIEW가 될 수 있습니다. 정규식은 모든 한국어 고위험 표현을 포괄하지 않으며 실제 서비스 상태를 관측하지 않습니다.
