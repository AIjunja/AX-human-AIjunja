# 무신사 제출 질문지

## Q1

무신사 Senior CX Quality Specialist가 공개 앱 리뷰에서 반복·구조적 개선 과제를 찾을 때, 한 리뷰에 여러 쇼핑 여정 증상이 섞이고 환경과 출처 정보가 빠진 병목 때문에 원본 근거와 재현 준비도·정보 공백이 표시된 QA 티켓 및 테스트 초안을 만들기 어려운 문제를 해결하는 Codex 플러그인입니다.

## Q2

무신사 공식 CX 채용 공고는 VOC에서 반복·구조적 문제를 도출하고 유관 부서와 개선 과제를 수행하며 AI/자동화 기반 QA를 검토한다고 밝힙니다. 공식 QA 글도 앱 리뷰 수집, 이슈 분류, 테스트 케이스 설계와 자동화를 설명합니다. Apple 공개 리뷰 14280470370은 품절 표시·결제 지연·화면 전환 지연·발열을 한 문장에 함께 보고해, 단순 분류보다 원문 근거와 환경 공백이 연결된 QA 티켓·테스트 초안이 필요함을 보여 줍니다. 기존 VOC 분류와 겹치는 단순 분류, 주문 상태 없이는 오판할 수 있는 정책 대조보다 공개 근거·실제 사용자·반복 가치·차별성·fixture 검증성이 강해 선택했습니다. 리뷰는 문제 신호로만 쓰며 전체 고객 비율, 장애 원인, 매출 영향으로 일반화하지 않습니다.

출처 URL: https://www.musinsacareers.com/ko/o/208642

## Q3

입력은 evidence_id, 원본 review ID, 공식 스토어 URL, 날짜, 별점, environment와 raw_review_text·원문 SHA-256 또는 정규화 문장·정규화 방법·원본 해시를 가진 UTF-8 JSON입니다. 공식 호스트와 무신사 앱 ID를 검증한 뒤 한 리뷰의 증상을 독립 티켓으로 분리하고, 각 티켓에 정확한 일치 구절·문자 offset·텍스트 해시·evidence ID를 보존합니다. device·OS·app version과 각 필드 provenance를 함께 확인해 모두 review_reported·store_metadata·verified_test_run이면 READY_FOR_REPRO, 합성값이면 TEST_SCENARIO_ONLY, 누락·출처 미확인이면 NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION으로 표시합니다. 증상별 재현 절차와 oracle_type·required_observations·human_defined_thresholds를 만들되 수치 임계값과 기대 정책은 사람이 입력합니다. root_cause, 심각도, 우선순위, 실제 재현 성공, 사용자 발생률은 생성하지 않습니다.

## Q4

AI는 기존 아이템을 유지한 채 상태 모델, 원문 매칭, 증상별 재현 절차·oracle 계약을 구현하고 테스트·validator·설치·fresh-session·ZIP 검증을 수행했습니다. 사람이 맡을 판단은 환경 출처 확인, 수치 임계값과 기대 정책, 심각도, 사업 우선순위, 중복, 실제 재현, 자동화 가능성입니다. 핵심 수정 판단은 TEST-* 값이 채워졌다는 이유만으로 READY_FOR_REPRO를 반환하면 안 된다는 것이며 synthetic은 TEST_SCENARIO_ONLY, 필드별 신뢰 provenance가 없으면 환경 확인 필요 상태로 바꿨습니다. fresh-session 1차 모델 비호환은 유지 기록하고 지원 모델로 재검증했습니다. 리뷰의 원인 추측과 fixture 빈도를 원인·사용자 비율로 바꾸는 제안은 계속 제외했습니다.

## Q5

공개 Apple 원문 evidence 14280470370을 입력하자 품절 오표시·결제 지연·화면 전환 지연·발열이 4개 독립 QA 티켓과 4개 증상별 회귀 테스트 초안으로 분리됐고, evidence 보존율 1.0을 확인했습니다. 원문 일치 구절·문자 offset·SHA-256이 모두 입력과 일치했으며 각 증상에 서로 다른 재현 절차와 oracle_type이 생성됐습니다. 합성 device·OS는 의도대로 4건 모두 TEST_SCENARIO_ONLY, 환경이 빈 Google Play 입력 3건은 NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION, evidence_id가 없는 입력은 exit code 2로 처리됐습니다. 기존 14개와 신규 6개, 총 20개 자동 테스트와 설치된 플러그인의 fresh Codex workflow에서 같은 결과를 재검증했습니다. 구현 중 합성 환경의 READY 오판 가능성과 generic oracle을 의심해 필드별 provenance 상태 모델과 증상별 관찰 계약으로 수정했습니다. 검증 범위는 공개 리뷰를 재현 준비도 QA 산출물로 변환하는 로직이며, 실제 앱 재현 결과와 사업 우선순위는 담당자가 이어서 확정합니다.
