# 의료관광 · 웰니스 이슈 레이더

2026 방한 의료관광 시장조사 및 중장기 사업 전략수립 과업의 일일 뉴스 레이더 · (주)서던포스트

**공개 페이지** : https://baebong3.github.io/medtour-radar/

## 동작
- 매일 07:00(KST) GitHub Actions가 뉴스를 모아 `data/news.db`에 누적하고 `docs/index.html`을 다시 만듦
- 수집원 : 네이버 뉴스 검색 API(키가 있을 때) + Google 뉴스 RSS(키 불필요)
- 두 트랙(의료관광 · 웰니스)을 페이지 상단 토글로 전환 — 자바스크립트 없이 동작

## 구조
```
radar/rules.py     트랙별 질의어 · 범주 · 점수 규칙  ← 질의어 추가 · 수정은 여기서
radar/collect.py   수집 → data/news.db (URL × 트랙 기준 중복 제외, 누적)
radar/build.py     news.db → docs/index.html
radar/style.css    서던포스트 대시보드 공통 서식
data/news.db       전체 수집 이력 (SQLite)
docs/index.html    GitHub Pages 공개 페이지
```

## 로컬 실행
```bash
pip install -r requirements.txt
set NAVER_ID=...  &  set NAVER_SECRET=...     # (선택) Windows
python radar/collect.py --days 3
python radar/build.py --days 7
```
수작업으로 보강한 기사는 JSON으로 만들어 `python radar/collect.py --seed 파일.json`으로 넣음.

## 점수
제도 · 비자 +3 / 리스크 · 분쟁 +4 / 발주처(공사 · 복지부 · 진흥원) +3 / 통계 · 실적 +2 / 중동 · 경쟁국 +2 / 최신성 +1~3 / 과업 핵심어 없으면 -2
웰니스 트랙은 의료관광과의 융복합 · 연계에 +3
