# 채널톡 제출 질문지

## Q1

채널톡 고객사의 CX 운영자·상담 관리자가 출처가 표시되지 않은 AI 답변을 공식 문서로 추가 확인할 때, 주장 분리·원문 탐색·정확 인용 기록을 반복해야 해 감사 가능한 답변을 만들기 어려운 문제를 해결합니다.

## Q2

채널톡 공식 글은 AI 어시스턴트가 FAQ·아티클 기반으로 답변한다고 설명하면서도, 출처가 표시되지 않은 경우 공식 문서나 가이드로 한 번 더 확인하라고 직접 권고합니다. 따라서 실제 병목은 답변 생성 자체보다 초안의 각 주장을 공식 원문과 연결해 검수 가능한 기록으로 만드는 과정입니다. 알림 진단은 채널톡의 기존 설정 가이드와 중복되어 탈락시켰고, 공개 리뷰 한 건을 전체 장애·원인·복구로 일반화하는 제안도 근거 범위를 넘으므로 거절했습니다. 답변 초안과 공식 URL만 받아 claim·quote·위치·판정을 만드는 workflow가 공개 근거, Codex 사용 현실성, 기존 기능 차별성에서 가장 적합했습니다.

출처 URL: https://channel.io/kr/blog/articles/ai-assistant-alf-1ba879b9

## Q3

사용자는 답변 초안과 공식 source URL만 제공합니다. Codex가 URL을 열어 retrieved_at과 source_text를 기록하면 스크립트가 문장별 claim_id를 만들고, 원문에서 직접 일치 또는 의미상 관련 문장을 찾아 evidence_id, 정확 quote, 문자 위치, content_sha256이 담긴 evidence packet을 구성합니다. quote가 지정 위치의 source_text와 다르면 입력을 거절합니다. claim이 검증된 quote에 직접 포함되면 SUPPORTED, 관련 의역이면 HUMAN_REVIEW, 근거가 없거나 무관하거나 고위험 결론의 직접 인용이 없으면 NEEDS_EVIDENCE입니다. READY만 발송 후보를 만들며 HUMAN_REVIEW는 담당자 확인, NEEDS_EVIDENCE는 직접 인용 추가나 결론 삭제를 요구합니다. 사설·loopback·link-local·reserved IP URL도 거부합니다.

## Q4

AI는 기존 플러그인을 유지한 채 테스트를 먼저 추가해, 무관 evidence가 SUPPORTED 되던 약점과 비공개 IP URL 허용을 재현했습니다. 이후 raw draft 자동 분리, quote 위치 검증, 세 단계 판정, URL 방어를 구현했습니다. 사람의 판단은 의역의 의미 일치와 최종 발송 승인에 남겼습니다. 알림 진단 후보는 공식 설정 기능과 중복되어 거절했고, 앱 리뷰 한 건에서 서비스 전체 장애·인증 서버 원인·복구 완료를 단정하는 제안은 리뷰가 그 결론을 직접 입증하지 않아 차단했습니다. 첫 설계처럼 위험 단어가 근거 어딘가에 존재한다는 이유만으로 통과시키지 않고, 전체 결론이 정확 인용에 직접 나타날 때만 자동 지지하도록 수정했습니다.

## Q5

기존 4개 회귀 테스트에 raw draft→2개 claim·2개 evidence packet, 무관 evidence 차단, 의역 HUMAN_REVIEW, 고위험 단어 분산 차단, quote 위치 불일치 거절, 사설·loopback·link-local·multicast·reserved IP 거절을 추가했습니다. 정상 직접 일치는 READY/SUPPORTED, 의역은 HUMAN_REVIEW, 개별 앱 리뷰로 전체 장애·원인·복구를 주장한 입력은 NEEDS_EVIDENCE, 잘못된 입력은 INVALID_INPUT·종료 코드 2가 됩니다. fresh-session에서는 raw-draft fixture를 실제 처리해 claim/evidence/판정 JSON을 확인합니다. 남은 한계는 원문 확보의 완전성과 최신성을 사람이 확인해야 하고 직접 일치 중심이라 올바른 의역도 수동 검토가 필요하다는 점입니다.
