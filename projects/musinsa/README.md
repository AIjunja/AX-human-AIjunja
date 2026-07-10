# 무신사 Review-to-Repro QA

무신사 공개 앱 리뷰를 원본 evidence ID·정확한 일치 구절과 연결하고, 재현 준비도와 정보 공백이 표시된 QA 티켓 및 증상별 회귀 테스트 초안으로 바꾸는 Codex 플러그인입니다. 리뷰는 관찰 신호일 뿐 장애 원인이나 전체 고객의 발생률을 입증하지 않으므로, `root_cause`와 사용자 비율을 생성하지 않습니다.

## 공개 문제와 실제 사용자

**문제 정의:** 무신사 `Senior CX Quality Specialist`가 공개 앱 리뷰에서 반복·구조적 VOC 개선 과제를 찾는 상황에서, 한 리뷰에 여러 여정의 증상이 섞이고 기기·OS·앱 버전과 그 출처가 빠져 있어 원본 근거와 재현 준비도가 표시된 QA 티켓·테스트 초안을 만들기 어려운 문제입니다.

무신사 공식 채용 공고는 이 역할이 VOC에서 반복·구조적 문제를 도출하고, 서비스기획·물류·상품 등과 개선 과제를 수행하며, AI/자동화 기반 QA를 검토한다고 설명합니다. 무신사 기술 블로그도 앱 리뷰 수집·이슈 분류·테스트 케이스 설계와 단위 자동화 테스트를 QA 업무로 소개합니다. 공개 Apple 리뷰 `14280470370`은 한 문장에 품절 표시, 결제 지연, 목록·상세 전환 지연, 발열을 함께 보고합니다. 이 사례는 문제의 존재를 보여 주는 신호이지 전체 사용자 비율·실제 장애·원인을 입증하지는 않습니다.

## 인터뷰와 별도 근거의 관계

조코딩 공식 인터뷰에서 무신사 전사 테크 리드 김상범은 플랫폼·브랜드 증가에 따른 기술 파편화와 패션 도메인의 복잡도를 말하고(00:40~01:24, 03:14~03:36), 문제를 좁게 정의해 해결책까지 end-to-end로 연결하는 흐름을 평가한다고 설명합니다(02:32~02:53). Codex 사용 증가도 언급합니다(04:11~04:37). 이는 좁고 실행 가능한 QA 산출물과 Codex라는 도구 선택을 뒷받침합니다. 다만 인터뷰는 공개 앱 리뷰 처리, CX 병목, 특정 증상의 실제 원인·빈도·매출 영향을 입증하지 않으므로 그 부분은 공식 채용·기술 글·공개 스토어 리뷰로 별도 확인했습니다. 영상의 본선형 트렌드·브랜드 탐색 문제를 복제하지 않았습니다.

## 후보 비교와 선정

5점 척도이며 공개 근거와 Codex 적합성은 각각 4점 이상이어야 합니다.

| 후보 | 공개 근거 | 실제 사용자 | 반복 가치 | 차별성 | fixture 검증 | 구현성 | Codex 적합성 | 결론 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 앱 리뷰 → 재현 QA 티켓·회귀 테스트 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 선정 |
| 검색~결제 VOC 분류 | 4 | 4 | 4 | 2 | 5 | 5 | 4 | 기존 VOC 대시보드와 중복 |
| 배송·교환·환불 문의 정책 대조 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 문의 원문·주문상태 없이는 오판 위험 |

선정 후보는 단순 분류를 넘어 증상 분리, 증거 추적, 정보 부족 상태, 재현 절차와 회귀 테스트 초안을 결정론적으로 만듭니다.

## 설치와 사용

ZIP의 `src`가 플러그인 루트입니다. Codex local marketplace에 `src`를 등록·설치한 뒤 새 세션을 시작하고 `$musinsa-review-to-repro`를 호출합니다.

직접 실행:

```powershell
python -X utf8 src/scripts/review_to_repro.py src/fixtures/normal.json
python -X utf8 src/scripts/review_to_repro.py src/fixtures/sparse.json
python -X utf8 src/scripts/review_to_repro.py src/fixtures/invalid.json
```

정상·sparse는 exit code 0, invalid는 machine-readable stderr와 exit code 2가 기대값입니다.

## 입력과 작동 절차

입력은 UTF-8 JSON이며 `schema_version`, `sample_scope`, `reviews[]`를 포함합니다. 각 리뷰에는 `evidence_id`, 원본 review ID, 공식 스토어 URL, 날짜, 별점, `environment`가 필요합니다. 원문을 확보했다면 `raw_review_text`와 `raw_text_sha256`을 사용합니다. 정규화 문장만 있다면 `normalized_observation`, `normalization_method`, `source_raw_text_sha256`을 분리해 원문으로 오인되지 않게 합니다.

1. Apple/Google 공식 호스트와 무신사 앱 ID·패키지를 검증합니다.
2. 한 리뷰의 서로 다른 관찰 증상을 검색·목록·상품상세·장바구니·결제 등 독립 티켓으로 분리합니다.
3. 정확히 일치한 구절, 시작·끝 문자 offset, 텍스트 SHA-256, evidence ID와 원본 review ID를 `matched_evidence`에 보존합니다.
4. device·OS·app version과 각 필드의 provenance를 확인합니다. 값과 provenance가 모두 신뢰 출처이면 `READY_FOR_REPRO`, 합성값이 있으면 `TEST_SCENARIO_ONLY`, 누락·미확인 출처가 있으면 `NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION`입니다.
5. 관찰 증상만 기록하고 리뷰어의 원인 추측은 `NOT_GENERATED_FROM_REVIEW`로 분리합니다.
6. 각 티켓에 증상별 재현 절차와 같은 evidence ID의 회귀 테스트 초안을 만듭니다. 수치 임계값과 기대 정책은 만들지 않고 `human_defined_thresholds`에 사람이 입력할 항목을 남깁니다.

## 출력 예시

정상 fixture의 공개 리뷰 한 건은 다음 네 티켓과 네 회귀 테스트 초안으로 분리됩니다. fixture의 device·OS는 합성이므로 네 티켓 모두 `TEST_SCENARIO_ONLY`이며 실제 환경 확인 전에는 재현 준비 완료로 보지 않습니다.

- `detail / sold_out_mislabel`
- `checkout / checkout_latency`
- `listing_detail / navigation_lag`
- `cross_cutting_performance / device_overheating`

각 티켓은 `ticket_id`, `journey_stage`, `observed_symptom`, `status`, `matched_evidence`, `evidence_refs`, `information_gaps`, `reproduction_draft`, `human_decisions`, `cause_handling`을 포함합니다. 회귀 테스트는 증상별 `oracle_type`, `required_observations`, `human_defined_thresholds`를 가집니다. 출력에는 evidence 보존율과 순서 독립적 `stable_fields_sha256`도 포함됩니다.

## 판단 기준과 사람의 역할

도구는 문자열 규칙으로 관찰 증상을 분리하고 증상별 관찰 계약을 만들지만 심각도, 사업 우선순위, 중복 확정, 실제 재현 결과, 정책 위반, 자동화 가능성, 수치 임계값과 기대 정책은 정하지 않습니다. QA/CX 담당자가 실제 계정·상품·테스트 데이터·기대 상태를 제공하고 최종 판단합니다.

## KPI

- 입력 evidence ID 보존율 100%
- 복수 증상 독립 티켓 분리
- 합성 환경의 `READY_FOR_REPRO` 반환 0건
- 누락·출처 미확인 환경의 `NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION` 적용률 100%
- `matched_evidence`의 원문 substring·offset·SHA-256 일치율 100%
- `root_cause` 및 사용자 발생률 추정 필드 0건
- invalid 입력의 결정론적 거부
- 동일 입력의 안정 필드 해시 재현

## 검증 결과

2026-07-10에 다음을 실제 실행했습니다.

- 기존 14개와 신규 6개, 총 20개 자동 테스트 통과, Python 문법 검사 통과
- 공식 plugin validator와 SKILL.md validator 통과
- 정상 fixture: 4 tickets / 4 regression tests / evidence 보존율 1.0 / 합성 환경으로 4건 `TEST_SCENARIO_ONLY`
- sparse fixture: 3 tickets 모두 `NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION`; device·OS·app version 공백 표기
- invalid fixture: `INVALID_INPUT`, exit code 2
- 고유 local marketplace `axwar-musinsa-final` 설치, installed/enabled 확인
- fresh Codex 세션에서 설치 캐시의 실제 `$musinsa-review-to-repro` workflow로 정상 fixture 처리
- fresh 결과: 4 tickets / 4 regression tests / 4건 `TEST_SCENARIO_ONLY` / matched substring·증상별 oracle 확인 / `root_cause` 없음

## 공개 출처

- [무신사 Senior CX Quality Specialist](https://www.musinsacareers.com/ko/o/208642) — 무신사, 상시채용 페이지, VOC 기반 구조적 문제·AI/자동화 QA 업무
- [무신사 QA 엔지니어 업무](https://techblog.musinsa.com/qaengineer-roles-and-responsibilities-d1fc088c7a43) — 무신사 기술 블로그, 2022-05-30, 앱 리뷰·이슈 분류·테스트 설계와 자동화
- [무신사 VOC 대시보드 Part 1](https://techblog.musinsa.com/voc-dashboard-development-part1-ec40412eb17f) — 무신사 기술 블로그, VOC 자동 분류·대시보드 맥락
- [무신사 VOC 대시보드 Part 2](https://techblog.musinsa.com/voc-dashboard-development-part2-a220e42c34e9) — 무신사 기술 블로그, 분류 결과 활용 맥락
- [Apple 공식 최신 리뷰 RSS](https://itunes.apple.com/kr/rss/customerreviews/page=1/id=1003139529/sortby=mostrecent/json) — 공개 리뷰 원본 ID·날짜·본문 신호
- [Google Play 무신사](https://play.google.com/store/apps/details?id=com.musinsa.store&hl=ko&gl=KR) — 공개 앱·리뷰 페이지
- [Apple App Store 무신사](https://apps.apple.com/kr/app/id1003139529) — 공개 앱 페이지
- [무신사 교환·환불 가이드](https://www.musinsa.com/app/mypage/change_info) — 공식 정책 및 절차
- [조코딩 공식 무신사 인터뷰](https://www.youtube.com/watch?v=OLAWeIuiD5Y) — 2026-07-03, 기업 방향·평가 기준·Codex 활용 참고
- [OpenAI Plugins](https://developers.openai.com/codex/plugins), [Build plugins](https://developers.openai.com/codex/plugins/build), [Skills](https://developers.openai.com/codex/skills) — manifest, 설치 후 새 세션, skill 구조 기준

## 한계

- 리뷰는 작성자의 보고이며 실제 장애·원인·영향을 입증하지 않습니다.
- fixture의 `TEST-*` 환경은 테스트 시나리오용 합성값이며 공개 리뷰 사실이 아닙니다. 값이 채워져도 `TEST_SCENARIO_ONLY`입니다.
- 규칙 밖 표현은 `unknown / NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION`으로 남깁니다.
- 실제 무신사 앱 재현, 내부 티켓 생성, 매출 영향, 전체 고객 발생률은 검증하지 않았습니다.
- 제출 logs의 메인 작업 JSONL은 최종 산출물 확정 cutoff 시점까지의 원본 byte-for-byte snapshot입니다. 정확한 cutoff, 바이트 수, 원본·복사본 SHA-256은 `validation/cutoff-log-verification.json`에 기록합니다. cutoff 이후의 패키징·업로드 확인 대화는 제출 범위에 포함하지 않습니다.
- 공개 페이지는 변경·삭제될 수 있으며 검증 시점 이후 내용이 달라질 수 있습니다.
