# AX Human Projects

AX 인재전쟁 기업별 Codex 플러그인 제출물을 통합 관리합니다.

| 기업명 | 플러그인명 | 문제 정의 | 실제 사용자 | 기존 기능과 차별성 | 핵심 공개 근거 | 인터뷰 | 프로젝트 브랜치 | 검증 상태 | ZIP SHA-256 |
|---|---|---|---|---|---|---|---|---|---|
| 채널톡 | Channel Answer Evidence Gate | AI 상담 답변을 발송 전 검수할 때 출처 없는 주장과 공개 리뷰의 과잉 일반화 때문에 감사 가능한 답변을 만들기 어려운 문제 | 채널톡 고객사의 CX 운영자·상담 관리자 | ALF의 답변 생성·문서 검색과 달리 claim→evidence→source→URL 배치 검수 및 차단 보고서 생성 | [채널톡 AI 어시스턴트 공식 글](https://channel.io/kr/blog/articles/ai-assistant-alf-1ba879b9) | [조코딩 공식 인터뷰](https://www.youtube.com/watch?v=5iRf37Z8Wd4) | [project/channel-talk](https://github.com/AIjunja/AX-human-AIjunja/tree/project/channel-talk) | READY_TO_SUBMIT — validators, 4 tests, 3 fixtures, installed/enabled, fresh-session, unpack 검증 PASS | `cb2694a57f643bc6957524d5d0b36bebad3ced124179930485b92ff7afeb1690` |
| 무신사 | Musinsa Review-to-Repro QA | 공개 앱 리뷰 한 건에 여러 여정 증상이 섞이고 환경 정보가 빠져 원본 근거가 연결된 재현 QA 티켓과 회귀 테스트 초안을 만들기 어려운 문제 | 무신사 Senior CX Quality Specialist | 기존 VOC 분류를 넘어 증상 분리, evidence 추적, NEEDS_REPRO, 재현 절차·회귀 테스트 초안을 결정론적으로 생성 | [무신사 Senior CX Quality Specialist](https://www.musinsacareers.com/ko/o/208642) | [조코딩 공식 인터뷰](https://www.youtube.com/watch?v=OLAWeIuiD5Y) | [project/musinsa](https://github.com/AIjunja/AX-human-AIjunja/tree/project/musinsa) | READY_TO_SUBMIT — validators, 14 tests, 3 fixtures, installed/enabled, fresh-session, unpack·hash 검증 PASS | `0e629e1f3a26d91a54931f9677a24f70c2daf81a57f7a13104a5146e97983117` |
