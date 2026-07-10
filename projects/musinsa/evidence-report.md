# 무신사 공개 근거 보고서

수집 시각: 2026-07-10 KST. 공개 URL은 Scrapling의 보수적 단건 요청으로 직접 열었고, 제목·발행 주체·날짜·입증 사실·해석·한계를 확인했다. 대회 페이지는 Primer 로그인으로 리디렉션되어 상세 본문을 확인할 수 없었으므로 사용자 제공 제출 요건을 기준으로 삼았다. OpenAI 문서는 `learn.chatgpt.com`의 공식 문서로 리디렉션되어 HTTP 200으로 확인됐다.

## 후보 평가

| 후보 | 공개 근거 | Codex 적합성 | 근거와 판단 |
|---|---:|---:|---|
| 공개 앱 리뷰 → 재현 QA 티켓·회귀 테스트 | 5/5 | 5/5 | 공식 CX 채용의 VOC·AI QA, 공식 QA 글의 리뷰 수집·테스트 설계, 실제 다중 증상 리뷰가 연결됨. 결정론적 fixture 검증 가능. 선정. |
| 검색~결제 VOC 분류 | 4/5 | 4/5 | 공식 VOC 대시보드가 자동 분류를 이미 설명해 신규 차별성이 낮음. 미선정. |
| 배송·교환·환불 문의 정책 대조 | 4/5 | 3/5 | 공식 정책은 강하지만 공개 문의만으로 주문 상태·예외를 안전하게 판정하기 어려움. 미선정. |

## 인터뷰 추출

- 00:24~00:39: 패션·뷰티 플랫폼이며 브랜드 소개와 커머스·리테일을 수행한다.
- 00:40~01:24: 여러 플랫폼·브랜드로 기술이 파편화되고 회원·상품 데이터 통합 복잡도가 생긴다.
- 01:25~01:58: 본선형 문제는 AI로 트렌드와 브랜드를 찾는 무신사의 정체성 문제다. 본 제출은 이를 복제하지 않았다.
- 01:59~02:35: 문제 가설과 구현 메커니즘, 문제와 해결책의 수미상관을 중시한다.
- 02:36~02:53: 문제를 좁게 정의하고 생각의 흐름과 end-to-end 메커니즘을 평가한다.
- 02:54~03:13: 깊은 생각이 결과와 비즈니스 임팩트로 이어지는 인재를 원한다.
- 03:14~03:36: 패션 특화 도메인과 플랫폼·브랜드의 기술 복잡도 때문에 AI를 생존 문제로 본다.
- 04:11~04:37: 내부 Codex 사용이 증가하며 명료함과 결과 도달률을 장점으로 말한다.
- 04:41~04:56: 깊이 생각하고 결과를 만들며 필요한 도구는 무엇이든 쓰는 인재상을 말한다.

영상으로 입증할 수 없는 것: 공개 앱 리뷰 처리 업무의 실제 병목, CX 담당자의 구체 직무, 특정 증상의 원인·빈도·매출 영향, 실제 재현 성공 여부. 이는 공식 채용·기술 글·스토어 리뷰로 교차 검증하거나 한계로 남겼다. 제품·QA·CX 니즈는 좁은 문제 정의, end-to-end 산출물, Codex 활용과 연결되며 상품운영의 구체 워크플로는 영상만으로 입증하지 않았다.

## URL별 기록

| URL | 제목 / 발행 주체 / 날짜 | 입증 사실 | 해석 | 한계 |
|---|---|---|---|---|
| https://hack.primer.kr/rounds/10 | Primer 대회 페이지 / Primer / 확인일 2026-07-10 | 로그인 페이지로 리디렉션 | 사용자 제공 요건으로 진행 | 대회 상세 본문 직접 확인 제한 |
| https://developers.openai.com/codex/plugins | Plugins / OpenAI / 확인일 2026-07-10 | 플러그인이 skill·app을 묶고 설치 후 새 세션 필요 | 패키징·fresh 검증 기준 | 동적 문서이며 변경 가능 |
| https://developers.openai.com/codex/plugins/build | Build plugins / OpenAI / 확인일 2026-07-10 | `.codex-plugin/plugin.json`, skills, local marketplace 흐름 | manifest·설치 검증 기준 | UI/CLI 버전별 차이 가능 |
| https://developers.openai.com/codex/skills | Skills / OpenAI / 확인일 2026-07-10 | SKILL.md와 선택적 script/resource 구조 | workflow 설계 기준 | 자동 선택은 description에 의존 |
| https://www.youtube.com/watch?v=OLAWeIuiD5Y | 무신사의 AI 시대 전략과 인재상 / 조코딩 / 2026-07-03 | 위 타임스탬프의 기업 방향·인재상·Codex 언급 | 기업 방향 참고 | QA/CX 병목의 직접 증거 아님 |
| https://www.musinsacareers.com/ko/o/208642 | Senior CX Quality Specialist / 무신사 / 상시 페이지 | VOC 구조 문제, 유관부서 개선, AI/자동화 QA | 실제 사용자를 CX Quality Specialist로 특정 | 채용 공고이며 현재 운영량·성과 미공개 |
| https://techblog.musinsa.com/qaengineer-roles-and-responsibilities-d1fc088c7a43 | 무신사 QA 엔지니어 업무 / 무신사 기술 블로그 / 2022-05-30 | 앱 리뷰 수집, 이슈 분류, 테스트 케이스·자동화 | 리뷰→QA 산출물 적합성 | 2022년 업무 소개로 현재 프로세스와 다를 수 있음 |
| https://techblog.musinsa.com/voc-dashboard-development-part1-ec40412eb17f | VOC 대시보드 Part 1 / 무신사 기술 블로그 | VOC 자동 분류 맥락 | 단순 분류 후보의 기존 기능 중복 | 내부 최신 구조·정확도 미공개 |
| https://techblog.musinsa.com/voc-dashboard-development-part2-a220e42c34e9 | VOC 대시보드 Part 2 / 무신사 기술 블로그 | 분류 결과의 시각화·활용 맥락 | 재현 QA 산출물로 차별화 필요 | 현재 운영 상태 미확인 |
| https://itunes.apple.com/kr/rss/customerreviews/page=1/id=1003139529/sortby=mostrecent/json | Apple 고객 리뷰 RSS / Apple·작성자 / 동적 | 원본 review ID·날짜·본문 공개 신호 | 다중 증상 분리 fixture 근거 | 표본이며 전체 고객으로 일반화 불가 |
| https://play.google.com/store/apps/details?id=com.musinsa.store&hl=ko&gl=KR | 무신사 앱 / Google Play | 앱 ID와 공개 리뷰 표면 | sparse fixture 출처 호스트 검증 | 노출 리뷰가 전체 모집단 아님 |
| https://apps.apple.com/kr/app/id1003139529 | 온라인 패션 스토어 무신사 / Apple App Store | Apple 앱 ID와 공개 앱 페이지 | URL 검증 | 앱 운영 원인·영향 미공개 |
| https://www.musinsa.com/app/mypage/change_info | 교환·환불 가이드 / 무신사 | 공식 교환·환불 절차 | 정책 대조 후보의 근거 | 개별 주문 예외 판정 불가 |

## 앱 리뷰 사용 원칙

리뷰 ID와 URL은 추적성 확보에만 사용했다. 리뷰 개수·별점·fixture 빈도를 전체 고객 비율, 장애 원인 또는 매출 영향으로 환산하지 않았다. fixture의 정규화 문구와 합성 환경은 공개 원문 사실과 분리해 명시했다.
