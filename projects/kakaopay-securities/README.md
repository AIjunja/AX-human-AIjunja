# 카카오페이증권 공개 장애 인테이크

카카오페이증권 서비스운영·QA 담당자가 공개 앱 제보와 공식 공지를 초동 검토할 때, 출처 ID를 잃지 않고 사실·누락·충돌·사람의 다음 검토를 한 번에 정리하는 Codex 플러그인이다. 입력을 구조화할 뿐, 장애 확정·원인·귀책·손실·보상·투자·주문 판단은 하지 않는다.

## 최종 문제 정의

> **카카오페이증권 서비스운영·QA 담당자가 주문·서비스 장애 관련 공개 제보를 초동 검토하는 상황에서, 제보·공식 장애 공지·공공 기준의 출처 ID와 시간·영향 범위·누락정보가 흩어져 있어 사람 검토용 사실관계 패킷을 신속히 완성하기 어려운 문제**

일반 투자자가 Codex를 쓴다고 가정하지 않았다. 카카오페이증권의 공개 채용문서는 AI Agent가 기획·개발·QA·배포·운영을 아우르고, QA·운영·컴플라이언스와 Human-in-the-loop가 실제 적용 영역임을 밝힌다. 금융소비자보호 직무도 모니터링·점검·민원 제도 업무를 공개한다. 따라서 주 사용자는 서비스운영·QA, 보조 검토자는 금융소비자보호·고객지원으로 한정했다.

## 왜 이 문제인가

2026-07-10에 공개 스토어의 최신 Google Play 리뷰 500건과 Apple App Store 리뷰 500건을 다시 수집해 1~3점이면서 증권 맥락인 263건을 분류했다. 이 중 거래 연속성 관련 표현은 97건이었지만, 환경·흐름·명시 증상을 모두 담은 엄격한 재현 가능 제보는 6건(2.3%)뿐이었다. 이 값은 공개 표본의 분류 결과이지 전체 고객, 실제 장애 건수, 피해자 수가 아니다.

카카오페이증권은 2026-06-30 07:02:57에 일부 서비스가 원활하지 않다는 공지(7314)를, 07:15:55에 정상 이용 가능 공지(7315)를 공개했다. 두 시각의 차이는 **공지 게시 간격**일 뿐 실제 장애 지속시간으로 해석하지 않는다. 주문 장애 안내는 시스템 장애와 외부 기관·통신·기기 문제를 구분하고 스크린샷·동영상·전화·주문 로그 같은 증거를 안내한다. 이는 출처와 누락정보를 먼저 보존하고 원인·귀책·보상은 사람이 판단해야 하는 이유다.

요청된 세 후보를 각 5점 만점으로 평가했다. 금융 위험은 5점일수록 금지 동작과 사람 검토로 위험을 통제하기 쉽다는 뜻이다. 공개 근거와 Codex 적합성이 각각 4점 미만인 후보는 탈락시켰다.

| 후보 | 공개 근거 | 실제 Codex 사용자 | 반복 가치 | 기존 기능과 차별성 | 검증 가능성 | 구현 가능성 | 금융 위험 통제 | 합계 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 주문 장애 제보 → 공식 근거 연결 증거·대응 패킷 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | **35** |
| 공개 VOC → 재현 가능한 QA 티켓 | 4 | 5 | 5 | 4 | 5 | 5 | 5 | 33 |
| 공식 공지·규정 ↔ 고객 안내문 정합성 검수 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 28 |

1위는 회사 공식 주문 장애 안내와 장애·정상화 공지, 공개 제보를 같은 시간축에 놓되 판단 월권을 코드로 막을 수 있어 선택했다. 2위의 재현정보 누락 검사는 1위 출력의 `missing_information`에 흡수했다.

## 기업 인터뷰와 별도 근거의 관계

조코딩 공식 인터뷰에서 카카오페이증권 AI서비스센터장은 초보 투자자의 쉬운 투자 경험을 서비스 특성으로 설명했다(00:18~00:30). 전화·채팅 상담이 활발하고 상담사 숙련과 지원 시스템이 필요해 AI로 정보 검색·문제 발생 파악·상담을 지원했다고 밝혔다(00:34~00:59). 원하는 AX 인재는 문제를 논리적으로 뜯고 AI 해결법을 찾은 뒤 스스로 증명하는 사람이다(02:00~02:18). 본인도 Codex를 다른 하네스·도구와 연결하는 확장성 때문에 사용한다고 말했다(03:11~03:24). 이는 고객지원·서비스운영 담당자의 근거 연결 워크플로가 현실적인 사용자 맥락임을 뒷받침한다.

반면 인터뷰만으로 주문 장애 빈도·원인·손실·귀책, 상담 AI의 정확한 개선 수치, 내부 반복량은 입증할 수 없다. 01:03~01:21의 초보 투자자 매수·매도 도움은 영상에서 언급된 인재전쟁 문제이며 이번 예선 문제로 주장하거나 복제하지 않았다. 플러그인의 구체 병목은 카카오페이증권 공식 주문 장애 안내·장애 공지와 공개 앱 리뷰로 별도 교차 검증했다.

## Installation

제출물의 전체 플러그인 루트는 `src/`다. 독립 로컬 marketplace에는 다음 구조로 등록한다.

```text
marketplace/
├── .codex-plugin/marketplace.json
└── plugins/kps-public-incident-intake/   # 제출물 src/의 byte copy
```

Codex CLI 명령은 다음과 같다.

```powershell
codex plugin marketplace add <marketplace-root> --json
codex plugin add kps-public-incident-intake@axwar-kps-final --json
codex plugin list --json
```

최종 검증은 독립 `axwar-kps-final` marketplace에서 완료했다. Codex CLI `0.142.2`의 `plugin list --json`에서 `kps-public-incident-intake@axwar-kps-final`가 `installed: true`, `enabled: true`, version `1.0.0`임을 확인한 뒤 새 세션에서 실제 fixture를 처리했다. 설치 확인용 문자열만 출력하는 별도 smoke 스킬은 없다. 실제 스킬이 실제 fixture를 처리해야만 proof line이 나온다.

## Usage

새 Codex 세션에서 다음처럼 요청한다.

```text
Use $build-public-incident-intake to process fixtures/normal.json.
Run the real workflow, verify evidence preservation and all prohibited conclusions,
then summarize the human-review packet.
```

직접 실행도 가능하다.

```powershell
cd src
python -B -X utf8 scripts/build_incident_intake.py fixtures/normal.json --compact
python -B -X utf8 scripts/build_incident_intake.py fixtures/normal.json --proof-only
```

사용자 입력은 `schemas/public-incident-intake.schema.json`을 따른다. 최소 입력 예시는 다음과 같다.

```json
{
  "schema_version": "1.0.0",
  "case_id": "KPS-PUBLIC-2026-06-30-A",
  "observed_window": {
    "start": "2026-06-30T07:00:00+09:00",
    "end": "2026-06-30T07:30:00+09:00"
  },
  "public_reports": [
    {
      "evidence_id": "GP-9B529133",
      "source_record_id": "9b529133-249a-483a-bb72-88613275c692",
      "source_url": "https://play.google.com/store/apps/details?id=com.kakaopay.app&hl=ko&gl=KR&reviewId=9b529133-249a-483a-bb72-88613275c692",
      "source_type": "google_play_review",
      "published_at": "2026-06-30",
      "captured_at": "2026-07-10T21:30:00+09:00",
      "text": "공개 리뷰 원문",
      "rating": 1
    }
  ],
  "official_sources": []
}
```

계좌번호·주문번호·이름·전화번호·이메일·주민등록번호는 입력하지 않는다.

## How it works

1. 표준 라이브러리만으로 최상위 필드, 스키마 버전, 시간대, HTTPS URL, 출처 유형, 중복 ID, 민감 필드와 고신뢰 개인정보 패턴을 검증한다.
2. 모든 입력 레코드를 `evidence_registry`로 옮기고 `evidence_id`, `source_record_id`, URL, 게시·수집 시각, 원문 SHA-256을 보존한다. 결과에는 원문을 반복하지 않는다.
3. 공개 제보 문구에서 `SECURITIES_SURFACE`, `ORDER_CONTROL`, `UNAVAILABLE` 같은 **관찰 코드**만 추출한다. 코드는 진단이 아니다. 증권 표면과 중단 증상이 함께 없는 제보는 READY 기준에서 제외한다.
4. 제보의 정확 시각 또는 게시 시각이 관찰창 안인지 구분한다. 게시일만 있는 같은 날 리뷰는 `UNRESOLVED_DATE_ONLY_SAME_DAY`로 남기며, 다른 날짜 제보는 제외한다. 공식 출처는 시간대가 있는 게시 시각이 관찰창 안일 때만 연결한다.
5. 재현에 필요한 환경·정확 시각·절차·기대·실제 결과의 누락을 제보별로 기록한다.
6. 공개 제보와 공식 문구의 범위가 다르면 양쪽 ID를 보존하고 `HUMAN_REVIEW_REQUIRED`로 남긴다.
7. 증권 중단 신호가 있고 정확 시간창 안이거나 같은 날이지만 시간 연계가 미확정인 서로 다른 공개 제보 2건 이상, 그리고 정확 관찰창 내 공식 출처 1건 이상이면 `READY_FOR_HUMAN_TRIAGE`를 반환한다. 아니면 `NEEDS_MORE_PUBLIC_INFORMATION`이다. 전자는 사실 확정이 아니라 사람이 검토할 최소 묶음이 갖춰졌다는 뜻이다.
8. 투자 추천, 주문 실행, 손실액, 보상 적격성, 회사 귀책, 원인은 항상 `NOT_ASSESSED`다.

정상 fixture의 핵심 출력은 아래와 같다.

```json
{
  "case_id": "KPS-PUBLIC-2026-06-30-A",
  "workflow_status": "READY_FOR_HUMAN_TRIAGE",
  "source_coverage": {
    "public_report_count": 2,
    "official_source_count": 2
  },
  "official_corroboration": {
    "status": "OFFICIAL_SOURCE_IN_WINDOW",
    "scope": "WINDOW_ONLY_NOT_CAUSE_FAULT_OR_INDIVIDUAL_REPORT_CONFIRMATION"
  },
  "temporal_association": {
    "candidate_report_count": 2,
    "unresolved_report_ids": ["GP-1DFE18BB", "GP-9B529133"],
    "exact_window_official_source_ids": ["KPS-NOTICE-7314", "KPS-NOTICE-7315"]
  },
  "safety_review": {
    "result": "PASS",
    "evidence_id_preservation_percent": 100
  }
}
```

검증 proof line:

```text
KPS_PUBLIC_INCIDENT_INTAKE_OK:v1|case=KPS-PUBLIC-2026-06-30-A|status=READY_FOR_HUMAN_TRIAGE|evidence=4|reports=2|official=2|preserved=100%|forbidden=PASS
```

정보 부족 fixture는 오류로 실패하지 않고 `NEEDS_MORE_PUBLIC_INFORMATION`, 공식 일치 0건, 누락 필드, 100% 출처 보존을 반환한다. 잘못된 fixture는 종료 코드 2와 함께 `SENSITIVE_FIELD_FORBIDDEN`, `SOURCE_URL_NOT_HTTPS`, `DUPLICATE_EVIDENCE_ID`를 반환한다.

## Tests

Windows에서 UTF-8 모드를 명시한다.

```powershell
# 공식 plugin validator
python -X utf8 $HOME\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py src

# 공식 SKILL.md validator
python -X utf8 $HOME\.codex\skills\.system\skill-creator\scripts\quick_validate.py src\skills\build-public-incident-intake

# Python 문법 및 23개 자동 테스트
python -B -X utf8 -m py_compile src\scripts\build_incident_intake.py
cd src
python -B -X utf8 -m unittest discover -s tests -v
```

자동 테스트는 정상·정보 부족·잘못된 입력, 결정론적 proof, 입력 원문 미반복, 모든 evidence/source ID 보존, 파생 참조 무결성, 공식 도메인·경로·record ID, 공공 기준만으로 회사 공식 상관근거를 만들지 않는 회귀 조건, 중복 원문, 오래된·주제 불일치 제보, 날짜 정밀도, 모든 허용 문자열의 민감정보, 재현 필드 타입, 역전 시간창, 비 UTF-8 오류, 금지 판단 6종 `NOT_ASSESSED`, CLI 종료 코드를 검사한다.

2026-07-10 최종 검증에서 공식 plugin validator, 공식 skill validator, JSON 파싱, Python 문법, 자동 테스트 23건이 통과했다. `PYTHONIOENCODING=utf-8`로 독립 marketplace를 준비하고 설치·enabled 상태를 확인했으며, 새 Codex 세션에서 설치된 `build-public-incident-intake`가 `fixtures/normal.json`을 실제 실행했다. 세션은 모든 evidence/source ID, `temporal_association`, `safety_review.result=PASS`, 6개 `NOT_ASSESSED` 금지 판단을 확인한 뒤 아래 proof line만 반환했다. 첫 harness 보고 시도는 Windows cp949 출력 인코딩으로 JSON 보고가 깨졌지만, 플러그인 실행 자체는 성공했고 UTF-8 환경으로 재실행해 전체 검증을 통과시켰다.

## KPI

실운영 도입 전후 같은 표본으로 측정한다. 이 README는 미측정 개선치를 성과처럼 주장하지 않는다.

- 입력 `evidence_id` 및 `source_record_id` 보존율: 목표 100%
- 초동 검토 시작부터 첫 패킷 생성까지의 중앙값
- 사람이 다시 찾아 붙여야 하는 출처 링크 수
- 환경·흐름·증상 누락이 명시된 제보 비율
- 검토자가 수정 없이 수용한 관찰 코드 비율
- 금지 판단 또는 개인정보 출력 건수: 목표 0

## Sources

플러그인 내부의 기계 판독형 장부는 `src/references/public-sources.json`이다. 핵심 원문은 다음과 같다.

- 카카오페이증권: [회사 소개](https://kakaopaysec.com/company/about/dynamicPage.do), [AI Agent 엔지니어](https://career.kakaopaysec.com/job_posting/Rtv75CLr), [AI Agent 기획자](https://career.kakaopaysec.com/job_posting/h6XYO0i5), [금융소비자보호 직무](https://career.kakaopaysec.com/job_posting/nNZ7CkIK)
- 카카오페이증권: [주문 장애 안내](https://kakaopaysec.com/portal/cstmnotice-obstc/dynamicPage.do), [장애 공지 7314](https://www.kakaopaysec.com/customer/notice/dynamicBoardPageDetail.do?id=7314), [정상화 공지 7315](https://www.kakaopaysec.com/customer/notice/dynamicBoardPageDetail.do?id=7315), [민원 처리 절차](https://www.kakaopaysec.com/portal/minwonjubsu/dynamicPage.do)
- 금융투자협회: [표준내부통제기준](https://law.kofia.or.kr/service/law/lawFullScreenContent.do?historySeq=443&seq=150)
- 공개 리뷰 표면: [Google Play 카카오페이](https://play.google.com/store/apps/details?id=com.kakaopay.app&hl=ko&gl=KR), [Apple App Store 카카오페이](https://apps.apple.com/kr/app/%EC%B9%B4%EC%B9%B4%EC%98%A4%ED%8E%98%EC%9D%B4/id1464496236)
- 기업 인터뷰: [조코딩 AX 인재전쟁 6화 카카오페이증권](https://www.youtube.com/watch?v=aBuoojGjyf4)
- OpenAI 공식 문서: [Plugins overview](https://learn.chatgpt.com/docs/plugins?surface=app), [Build plugins](https://learn.chatgpt.com/docs/build-plugins), [Build skills](https://learn.chatgpt.com/docs/build-skills)

## Limitations

- 공개 리뷰는 자기보고이며 실제 장애·영향 사용자·원인·손실을 확정하지 않는다.
- 공식 공지는 그 문구와 게시 시각만 증명한다. 게시 간격을 장애 지속시간으로 바꾸지 않는다.
- 개인정보 패턴 검사는 고신뢰 패턴 중심이다. 자유문에서 모든 개인정보를 완벽히 탐지하지 못하므로 입력 전에 사람이 공개성·비식별성을 확인해야 한다.
- 키워드 관찰 코드는 한국어·영어 규칙 기반이며 은어, 오탈자, 맥락을 놓치거나 과탐할 수 있다.
- `READY_FOR_HUMAN_TRIAGE`는 사람 검토 준비 상태다. 내부 장애 확정, 고객 답변, 컴플라이언스 판단을 자동 승인하지 않는다.
- 카카오페이 앱은 결제·송금·증권이 함께 있어 증권 맥락 필터가 필요하다.
- 앱 리뷰와 공식 페이지는 수정·삭제될 수 있다. `captured_at`, stable ID, URL, 원문 해시를 함께 보존해야 한다.
- 이 플러그인은 네트워크 수집기가 아니다. 검증된 공개 입력을 결정론적으로 처리한다.

## 제출물 구조

```text
submission.zip
├── src/
│   ├── .codex-plugin/plugin.json
│   ├── skills/build-public-incident-intake/SKILL.md
│   ├── scripts/build_incident_intake.py
│   ├── schemas/public-incident-intake.schema.json
│   ├── fixtures/{normal,insufficient,invalid}.json
│   ├── tests/test_public_incident_intake.py
│   └── references/public-sources.json
├── README.md
└── logs/
```

`logs/`에는 이 회사 Goal의 원본 Codex JSONL과 fresh-session 원본 JSONL, byte-for-byte SHA-256 장부만 넣는다. 질문지는 ZIP 밖의 지정 경로에 둔다.
