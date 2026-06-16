# 2026 북중미 월드컵 경기결과 대시보드

GitHub Pages로 배포해 웹에서 보고, GitHub Actions로 **FIFA 공식 데이터**(api.fifa.com — 매치센터와 동일 소스)를 자동 갱신하는 단일 페이지 대시보드입니다. **API 키가 필요 없습니다.**

## 구성 파일

```
worldcup2026/
├─ index.html                          # 대시보드 (data.js 로드 → 웹서버면 data.json으로 갱신)
├─ data.js                             # 로컬 더블클릭용 데이터 (window.WC_DATA, 자동 갱신 대상)
├─ data.json                           # 경기·순위·선수기록 데이터 (자동 갱신 대상)
├─ scripts/
│   ├─ update_data.py                  # FIFA api.fifa.com 기반 갱신 (★ 기본, 키 불필요)
│   └─ update_data_footballdata.py     # 대체: football-data.org 기반 (무료 토큰 필요)
├─ .github/workflows/
│   └─ update-data.yml                 # 자동 갱신 워크플로 (30분마다, 기본=FIFA)
└─ README.md
```

대시보드 탭: **날짜별 경기결과** / **경기별 선수기록(득점·도움 순위 + 경기별 상세)** / **조별리그 순위(12개 조 승점표)**.

---

## 배포 (3단계)

1. **GitHub에 올리기** — 새 저장소를 만들고 이 폴더의 모든 파일을 올린다. (`.github/workflows/…` 점(.) 폴더 포함)
2. **Pages 켜기** — Settings → Pages → Source `Deploy from a branch`, Branch `main` `/(root)` → 저장. 1~2분 뒤 `https://<사용자명>.github.io/<저장소>/` 접속.
3. **자동 갱신** — 추가 설정 없음. `update-data.yml` 이 **30분마다** FIFA에서 스코어·순위를 받아 `data.json`·`data.js` 를 자동 커밋한다. (즉시 실행: Actions 탭 → Update World Cup data → Run workflow)

---

## 화면의 업데이트 버튼

- **🔄 새로고침**: 최신 `data.json` 을 페이지 리로드 없이 즉시 다시 불러온다. **URL에 매번 다른 값을 붙여 GitHub Pages CDN 캐시까지 우회**하므로 항상 최신이 반영된다.
- **자동 60초**: 체크하면 60초마다 자동으로 다시 불러온다.
- **▶ GitHub에서 최신 받기**: GitHub Pages에서 열었을 때만 보인다. 누르면 Actions 실행 페이지가 열리고 **Run workflow** 로 그 자리에서 최신 데이터를 수집한다(약 1분 뒤 🔄 새로고침으로 반영).

> 즉시 최신 결과까지 받으려면: **▶ GitHub에서 최신 받기 → Run workflow → (약 1분) → 🔄 새로고침** 순서. 평소엔 **자동 60초** 만 켜둬도 충분하다.

### ⚠️ 특정 날짜부터 결과가 멈췄을 때 (가장 흔한 원인)

데이터 출처(FIFA)와 스크립트는 정상이어도, **GitHub Action이 실제로 실행되지 않으면** data.json이 그 시점에 멈춥니다. 순서대로 점검하세요.

1. **Actions 활성화 확인** — 저장소 **Actions** 탭을 연다.
   - "Workflows aren't being run on this repository" 또는 활성화 버튼이 보이면 클릭해 **활성화**한다. (파일 업로드로 만든 저장소는 Actions가 꺼져 있는 경우가 많음 — 이게 핵심 원인일 때가 많습니다.)
2. **수동 실행으로 즉시 테스트** — Actions → `Update World Cup data` → **Run workflow**. (대시보드의 **▶ GitHub에서 최신 받기** 버튼도 이 화면으로 이동)
   - 실행 후 `Run updater` 단계 로그에서 `[ok] 갱신 완료 — 출처 FIFA …, 기준 2026-06-16 01:54 UTC` 처럼 나오면 성공. 곧 자동 커밋되고, 사이트에서 🔄 새로고침하면 반영됩니다.
   - 빨간색(실패)으로 `[ERROR] 어느 출처에서도 …` 가 나오면 FIFA가 일시 차단된 것 → 아래 football-data 토큰을 등록하면 자동 대체됩니다.
3. **예약(cron) 신뢰성** — GitHub의 예약 실행은 지연·누락이 잦습니다(특히 무료 저장소). 정해진 시각에 정확히 안 돌 수 있으니, 확실히 최신을 원하면 **Run workflow** 또는 대시보드의 **자동 60초 + 🔄 새로고침** 을 쓰세요.
4. **기본 브랜치 확인** — 예약 워크플로는 기본 브랜치(보통 `main`)에 있어야 동작합니다.

### 화면엔 떴는데 옛날 데이터일 때
- 이 대시보드는 CDN 캐시 우회 처리가 되어 있으나, 그래도 안 보이면 강력 새로고침(Ctrl+F5).
- Actions 커밋 후 GitHub Pages 반영에 ~1분 걸립니다.
- 화면 우측 상단 **기준 2026-06-16 01:54 UTC** 표기로 data.json이 언제 갱신됐는지 확인할 수 있습니다.

---

## 자동 갱신 범위

- **자동 갱신(기본)**: 경기 최종 스코어, 경기 상태(예정/종료), 조별리그 순위 — FIFA로 자동.
- **자동 갱신(선택, API-Football 키 등록 시)**: ① 토너먼트 **득점·도움 순위**, ② **새 경기의 경기별 득점자·도움·카드**(업데이트된 경기도 선수기록이 채워짐).
- **자동 갱신 안 됨**: 경기별 **선발 라인업·교체**는 무료 API 범위 밖이라, 시드로 넣은 경기(개막 초반)만 표시됩니다. 직접 보강하려면 `data.json` 의 해당 경기 `lineups` 를 편집.

## (선택) 선수기록 자동 갱신 — API-Football 키 등록

대시보드 **경기별 선수기록** 탭의 **득점·도움 순위**를 자동으로 채우려면 무료 키를 등록합니다. (등록 전에는 시드값으로 표시되고, 등록하면 토너먼트 전체 득점·도움 순위가 자동 갱신됩니다.)

1. https://dashboard.api-sports.io/register 에서 무료 가입 → 발급된 **API Key** 복사 (무료 100요청/일)
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `APISPORTS_KEY` / Secret: 복사한 키
3. Actions → `Update World Cup data` → **Run workflow** 로 한 번 실행하면, 로그에 `[apisports] 성공: 득점 N명, 도움 N명` 이 보이고 순위가 채워집니다.

> 무료 100요청/일 한도가 있어, 호출이 많으면 워크플로의 `cron` 을 1~2시간 주기(`0 */2 * * *`)로 늘리세요. 키가 없거나 한도를 넘으면 선수순위는 기존값을 그대로 유지합니다(오류로 멈추지 않음).

## (대체) football-data.org 사용

FIFA 응답이 막히는 경우, football-data.org(무료 토큰)로 전환할 수 있다.

1. https://www.football-data.org/client/register 가입 → 토큰 복사
2. 저장소 Settings → Secrets and variables → Actions → New repository secret → Name `FOOTBALL_DATA_TOKEN`, Secret 토큰
3. `update-data.yml` 의 실행 단계를 아래로 교체:
   ```yaml
   - name: Run updater (football-data 대체)
     env:
       FOOTBALL_DATA_TOKEN: ${{ secrets.FOOTBALL_DATA_TOKEN }}
     run: python scripts/update_data_footballdata.py
   ```

## 로컬에서 미리 보기

- `index.html`·`data.js`·`data.json` 을 같은 폴더에 두면 `index.html` 더블클릭만으로 표시된다(웹서버 없이도 `data.js` 로 동작). 단 로컬에선 자동 갱신본을 못 읽어 `data.js` 시드값을 보여준다 — 최신값은 GitHub Pages에서 확인.

---

데이터 출처: FIFA(api.fifa.com, 매치센터와 동일 소스) · 선수 상세 시드는 ESPN·FIFA·FOX·AP 등 교차검증.
팀명 표기가 어긋나면 `scripts/update_data.py` 의 `NAME_MAP` 에 매핑을 추가하세요.
