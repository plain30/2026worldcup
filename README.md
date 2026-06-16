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

### 업데이트가 안 되는 것처럼 보일 때 점검
- **CDN/브라우저 캐시**: 이 대시보드는 캐시 우회 처리가 되어 있으나, 그래도 안 보이면 강력 새로고침(Ctrl+F5).
- **배포 지연**: Actions 커밋 후 GitHub Pages 반영에 ~1분 걸린다.
- **Actions 로그**: 저장소 Actions 탭에서 `[ok] FIFA 데이터로 갱신 …` 이 보이면 수집 성공. `[warn] … 기존 data.json 유지` 가 계속 보이면 FIFA 응답이 막힌 것 → 아래 대체 방법 사용.

---

## 자동 갱신 범위

- **자동 갱신**: 경기 최종 스코어, 경기 상태(예정/종료), 조별리그 순위.
- **자동 갱신 안 됨**: 선발 라인업·교체·득점자·도움·카드 등 선수 단위 상세. FIFA 공개 API 범위 밖이라 `data.json` 시드값을 보존하며, 자동 갱신 시 덮어쓰이지 않는다. 직접 보강하려면 해당 경기의 `goals`/`assists`/`cards`/`lineups` 를 편집하면 된다.

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
