# 2026 북중미 월드컵 경기결과 대시보드

GitHub Pages로 배포해서 웹에서 보고, GitHub Actions로 경기 스코어·순위를 자동 갱신하는 단일 페이지 대시보드입니다.

## 구성 파일

```
worldcup2026/
├─ index.html                      # 대시보드 (data.json을 불러와 렌더링)
├─ data.json                       # 경기·순위·선수기록 데이터 (자동 갱신 대상)
├─ scripts/
│   └─ update_data.py              # football-data.org에서 데이터 가져와 data.json 갱신
├─ .github/workflows/
│   └─ update-data.yml             # 주기적 자동 갱신 워크플로
└─ README.md
```

대시보드 탭: **날짜별 경기결과** / **경기별 선수기록(득점·도움 순위 + 경기별 상세)** / **조별리그 순위(12개 조 승점표)**.

---

## 1단계 · GitHub에 올리기

1. GitHub에서 새 저장소(repository)를 만든다. 예: `worldcup2026`
2. 이 폴더의 모든 파일을 저장소에 올린다.
   - 웹에서 올릴 경우 `Add file → Upload files`로 끌어다 놓는다.
   - `.github/workflows/update-data.yml` 처럼 점(.)으로 시작하는 폴더도 그대로 올려야 한다.
   - (명령줄을 쓴다면)
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
2. **Source** 를 `Deploy from a branch` 로 두고, Branch 를 `main` / `/(root)` 선택 후 저장
3. 1~2분 뒤 `https://<사용자명>.github.io/worldcup2026/` 주소로 접속하면 대시보드가 보인다.

> 이 단계까지만 해도 현재 들어있는 데이터로 대시보드가 정상 작동합니다. 자동 갱신이 필요 없으면 3·4단계는 건너뛰어도 됩니다.

## 3단계 · 무료 API 키 발급 (자동 갱신용)

1. https://www.football-data.org/client/register 에서 무료 가입
2. 메일로 받은 **API Token**(긴 문자열)을 복사

## 4단계 · API 키를 저장소에 등록

1. 저장소 → **Settings → Secrets and variables → Actions → New repository secret**
2. **Name** 칸에 정확히 `FOOTBALL_DATA_TOKEN` 입력
3. **Secret** 칸에 복사한 토큰 붙여넣고 저장

이제 끝입니다. `update-data.yml` 이 **6시간마다** 자동 실행되어 경기 스코어와 조별 순위를 갱신하고, 바뀐 내용이 있으면 `data.json` 을 자동 커밋합니다. Pages 사이트는 새로고침하면 최신 데이터가 보입니다.

- 즉시 한 번 돌려보고 싶으면: 저장소 **Actions** 탭 → `Update World Cup data` → **Run workflow** 버튼.
- 갱신 주기를 바꾸려면 `update-data.yml` 의 `cron` 값을 수정. (예: 매시간 `0 * * * *`, 하루 한 번 오전 9시 KST = `0 0 * * *`)

---

## 자동 갱신 범위 (중요)

- **자동으로 갱신되는 것**: 경기 최종 스코어, 경기 상태(예정/종료), 조별리그 순위(경기수·승·무·패·득·실·승점).
- **자동 갱신되지 않는 것**: 선발 라인업, 교체, 득점자·도움·카드 등 **선수 단위 상세**. 무료 API 플랜은 이 데이터를 제공하지 않아, `data.json` 에 들어있는 교차검증 시드 값을 그대로 보존합니다.
- 선수 상세를 더하거나 고치고 싶으면 `data.json` 의 해당 경기 `goals` / `assists` / `cards` / `lineups` 항목을 직접 편집하면 됩니다. (스크립트가 팀 조합을 기준으로 기존 상세를 유지하므로 자동 갱신 시 덮어쓰이지 않습니다.)

## 로컬에서 미리 보기

- `index.html` 에는 기본 데이터가 내장돼 있어, **그냥 더블클릭해도 바로 표시**됩니다.
- 단, 더블클릭(파일 직접 열기) 상태에서는 자동 갱신본(`data.json`)을 못 읽고 내장 데이터를 보여줍니다. **최신 data.json까지 반영해 보려면** 같은 폴더에서 웹서버로 여세요:
  ```bash
  python -m http.server 8000
  # 브라우저에서 http://localhost:8000 접속
  ```
- GitHub Pages(웹서버)로 배포하면 항상 최신 `data.json` 을 우선 사용합니다.

## 직접 갱신 테스트 (선택)

```bash
export FOOTBALL_DATA_TOKEN=발급받은토큰
python scripts/update_data.py
```

---

데이터 출처: football-data.org(자동 스코어·순위) · ESPN, FIFA.com, FOX Sports, AP/Reuters 등(선수 상세 시드, 교차검증).
팀명 표기가 어긋나면 `scripts/update_data.py` 상단 `NAME_MAP` 에 매핑을 추가하세요.
