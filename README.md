# 2026 북중미 월드컵 경기결과 대시보드

GitHub Pages로 배포해 웹에서 보고, GitHub Actions로 경기 스코어·순위를 자동 갱신하는 단일 페이지 대시보드입니다. 자동 갱신은 무료 축구 데이터 API([football-data.org](https://www.football-data.org))를 사용하며, **무료 토큰 1회 발급**이 필요합니다.

> ⚠️ 결과가 갱신되지 않는다면 대부분 **3·4단계(토큰 등록)** 가 빠진 경우입니다. 토큰이 없으면 Actions가 실패(빨간색)로 표시됩니다.

## 구성 파일

```
worldcup2026/
├─ index.html                          # 대시보드 (data.js 로드 → 웹서버면 data.json으로 갱신)
├─ data.js                             # 로컬 더블클릭용 데이터 (window.WC_DATA, 자동 갱신 대상)
├─ data.json                           # 경기·순위·선수기록 데이터 (자동 갱신 대상)
├─ scripts/
│   ├─ update_data_footballdata.py     # football-data.org 기반 갱신 (★ 기본/권장)
│   └─ update_data.py                  # 대체: FIFA api.fifa.com 기반 (키 불필요하나 CI에서 차단될 수 있음)
├─ .github/workflows/
│   └─ update-data.yml                 # 주기적 자동 갱신 워크플로 (기본=football-data.org)
└─ README.md
```

대시보드 탭: **날짜별 경기결과** / **경기별 선수기록(득점·도움 순위 + 경기별 상세)** / **조별리그 순위(12개 조 승점표)**.

---

## 1단계 · GitHub에 올리기

새 저장소(예: `worldcup2026`)를 만들고 이 폴더의 모든 파일을 올린다. (`.github/workflows/update-data.yml` 같은 점(.) 폴더도 그대로)

```bash
git init
git add .
git commit -m "init: world cup dashboard"
git branch -M main
git remote add origin https://github.com/<사용자명>/worldcup2026.git
git push -u origin main
```

## 2단계 · GitHub Pages 켜기 (웹에서 보기)

1. 저장소 → **Settings → Pages**
2. **Source** = `Deploy from a branch`, Branch = `main` / `/(root)` 저장
3. 1~2분 뒤 `https://<사용자명>.github.io/worldcup2026/` 접속

## 3단계 · 무료 API 토큰 발급 (자동 갱신에 필수)

1. https://www.football-data.org/client/register 에서 무료 가입
2. 메일로 받은 **API Token**(긴 문자열) 복사
   - 무료 플랜에 FIFA 월드컵(`WC`)이 포함되어 있습니다.

## 4단계 · 토큰을 저장소에 등록 (필수)

1. 저장소 → **Settings → Secrets and variables → Actions → New repository secret**
2. **Name** 칸에 정확히 `FOOTBALL_DATA_TOKEN` 입력 (오타 주의)
3. **Secret** 칸에 복사한 토큰을 붙여넣고 저장

이제 끝입니다. `update-data.yml` 이 **6시간마다** 실행되어 경기 스코어·조별 순위를 갱신하고, 변경분이 있으면 `data.json` · `data.js` 를 자동 커밋합니다. Pages 사이트는 새로고침하면 최신 데이터가 보입니다.

- **즉시 한 번 실행해 확인**: 저장소 **Actions** 탭 → `Update World Cup data` → **Run workflow**
- 로그에 `[ok] football-data 갱신 — 경기 N, 순위 M조` 가 보이면 성공.
- `[ERROR] FOOTBALL_DATA_TOKEN …` 이 보이면 4단계(토큰 등록)를 다시 확인.
- 주기 변경: `update-data.yml` 의 `cron` 수정 (예: 매시간 `0 * * * *`, 하루 1회 `0 0 * * *`)

---

## 자동 갱신 범위

- **자동 갱신**: 경기 최종 스코어, 경기 상태(예정/종료), 조별리그 순위(경기수·승·무·패·득·실·승점).
- **자동 갱신 안 됨**: 선발 라인업·교체·득점자·도움·카드 등 선수 단위 상세. 무료 API 범위 밖이라 `data.json` 의 교차검증 시드값을 보존합니다. 직접 보강하려면 해당 경기의 `goals`/`assists`/`cards`/`lineups` 를 편집하면 되고, 자동 갱신 시 덮어쓰이지 않습니다.

## (선택) FIFA API로 바꾸고 싶다면

`scripts/update_data.py` 는 FIFA 내부 API(api.fifa.com)를 키 없이 호출하는 대체본입니다. 다만 FIFA는 공식 개발자 API가 아니어서 GitHub 러너 IP가 차단되면 갱신이 안 될 수 있습니다(그래서 기본값은 football-data.org). 사용하려면 `update-data.yml` 의 실행 단계를 아래로 바꾸면 됩니다(토큰 불필요):

```yaml
      - name: Run updater (FIFA)
        run: python scripts/update_data.py
```

## 로컬에서 미리 보기

- `index.html`·`data.js`·`data.json` 을 **같은 폴더**에 두면 `index.html` 더블클릭만으로 표시됩니다. (단, 로컬 더블클릭은 자동 갱신본을 못 읽어 `data.js` 시드값을 보여줍니다. 최신값은 GitHub Pages에서 확인)
- 웹서버로 보려면: `python -m http.server 8000` 후 `http://localhost:8000`

## 직접 갱신 테스트 (선택)

```bash
export FOOTBALL_DATA_TOKEN=발급받은토큰
python scripts/update_data_footballdata.py
```

---

데이터 출처: football-data.org(자동 스코어·순위) · 선수 상세 시드는 ESPN·FIFA·FOX·AP 등 교차검증.
팀명 표기가 어긋나면 `scripts/update_data_footballdata.py` 의 `NAME_MAP` 에 매핑을 추가하세요.
