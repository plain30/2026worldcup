#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026 월드컵 대시보드 데이터 자동 갱신 (FIFA 공식 데이터 기준)

- fifa.com/match-centre 가 호출하는 FIFA 데이터 API(api.fifa.com)를 직접 사용한다.
- API 키가 필요 없다.
- 경기 스코어/상태/조 + 조별 순위(완료 경기로 계산)를 갱신한다.
- 선수 상세(라인업/득점자/도움/카드)는 FIFA 공개 API 범위 밖이라 기존 시드값을 보존한다.
- FIFA가 응답하지 않거나(차단 등) 오류가 나면 기존 data.json을 그대로 유지하고 종료한다(안전).

수동 실행:  python scripts/update_data.py
GitHub Actions: .github/workflows/update-data.yml 이 주기적으로 실행 (키 불필요)
"""
import os, sys, json, datetime, urllib.request, urllib.error

API = "https://api.fifa.com/api/v3"
ID_COMPETITION = "17"          # FIFA World Cup
SEASON_NAME_HINT = "2026"      # 시즌 이름에 이 문자열이 들어간 것을 2026 대회로 인식
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en",
}

# FIFA 영문 팀명 -> 대시보드 표준 키. 매칭 안 되면 원문 통과.
NAME_MAP = {
    "Mexico":"Mexico","South Africa":"South Africa","Korea Republic":"South Korea",
    "Republic of Korea":"South Korea","South Korea":"South Korea",
    "Czechia":"Czechia","Czech Republic":"Czechia","Canada":"Canada",
    "Bosnia and Herzegovina":"Bosnia and Herzegovina","Qatar":"Qatar","Switzerland":"Switzerland",
    "Brazil":"Brazil","Morocco":"Morocco","Haiti":"Haiti","Scotland":"Scotland",
    "USA":"United States","United States":"United States","Australia":"Australia",
    "Türkiye":"Turkey","Turkiye":"Turkey","Turkey":"Turkey","Paraguay":"Paraguay",
    "Germany":"Germany","Curaçao":"Curaçao","Curacao":"Curaçao",
    "Côte d'Ivoire":"Ivory Coast","Cote d'Ivoire":"Ivory Coast","Ivory Coast":"Ivory Coast",
    "Ecuador":"Ecuador","Netherlands":"Netherlands","Japan":"Japan","Sweden":"Sweden",
    "Tunisia":"Tunisia","Belgium":"Belgium","Egypt":"Egypt","IR Iran":"Iran","Iran":"Iran",
    "New Zealand":"New Zealand","Spain":"Spain","Cabo Verde":"Cape Verde","Cape Verde":"Cape Verde",
    "Saudi Arabia":"Saudi Arabia","Uruguay":"Uruguay","France":"France","Senegal":"Senegal",
    "Norway":"Norway","Iraq":"Iraq","Argentina":"Argentina","Austria":"Austria",
    "Algeria":"Algeria","Jordan":"Jordan","Portugal":"Portugal","Colombia":"Colombia",
    "Congo DR":"DR Congo","DR Congo":"DR Congo","Uzbekistan":"Uzbekistan",
    "England":"England","Croatia":"Croatia","Ghana":"Ghana","Panama":"Panama",
}

def norm(name):
    return NAME_MAP.get((name or "").strip(), (name or "").strip())

def http_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def desc(field):
    """FIFA 다국어 필드 [{Description: ...}] 또는 문자열에서 텍스트 추출."""
    if isinstance(field, list):
        return field[0].get("Description") if field and isinstance(field[0], dict) else None
    if isinstance(field, dict):
        return field.get("Description")
    return field

def group_letter(name):
    if not name:
        return None
    s = str(name).replace("Group", "").replace("그룹", "").replace("조", "").strip()
    return s[:1].upper() if s else None

def find_season_id():
    """2026 시즌 IdSeason을 동적으로 찾는다."""
    for url in (f"{API}/competitions/{ID_COMPETITION}/seasons?language=en",
                f"{API}/seasons?idCompetition={ID_COMPETITION}&count=100&language=en"):
        try:
            data = http_get(url)
        except Exception:
            continue
        rows = data.get("Results") or data.get("results") or data if isinstance(data, list) else data.get("Results", [])
        if isinstance(data, dict) and "Results" in data:
            rows = data["Results"]
        for s in (rows or []):
            nm = desc(s.get("Name")) or ""
            sid = s.get("IdSeason") or s.get("id")
            if SEASON_NAME_HINT in str(nm) and sid:
                return str(sid)
    return None

def load_existing():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)

def main():
    existing = load_existing()

    season = find_season_id()
    if not season:
        print("[warn] 2026 시즌 ID를 찾지 못함(FIFA API 미응답 가능). 기존 data.json 유지.")
        return 0

    try:
        mdata = http_get(f"{API}/calendar/matches?idCompetition={ID_COMPETITION}"
                         f"&idSeason={season}&count=500&language=en")
    except Exception as e:
        print(f"[warn] 경기 데이터 요청 실패: {e}. 기존 data.json 유지.")
        return 0

    matches_raw = mdata.get("Results") or []
    if not matches_raw:
        print("[warn] 경기 결과가 비어있음. 기존 data.json 유지.")
        return 0

    # 기존 선수 상세 / 한글 경기장명 보존용 인덱스 (팀쌍 기준)
    prev_idx = {frozenset([m["t1"], m["t2"]]): m for m in existing.get("matches", [])}
    # 기존 순위표의 조별 팀 명단(48개팀) 보존용
    roster = {g["g"]: [t["t"] for t in g["teams"]] for g in existing.get("standings", [])}

    new_matches, tally = [], {}
    for mm in matches_raw:
        stage = (desc(mm.get("StageName")) or "").lower()
        gname = desc(mm.get("GroupName"))
        grp = group_letter(gname)
        # 조별리그만 (녹아웃 단계는 제외; 필요 시 조건 완화)
        if not grp and "group" not in stage:
            continue
        home = mm.get("Home") or {}
        away = mm.get("Away") or {}
        t1 = norm(desc(home.get("TeamName")) or home.get("ShortClubName"))
        t2 = norm(desc(away.get("TeamName")) or away.get("ShortClubName"))
        if not t1 or not t2 or t1 == "0" or t2 == "0":
            continue
        date = (mm.get("LocalDate") or mm.get("Date") or "")[:10]
        status = mm.get("MatchStatus")
        s1, s2 = home.get("Score"), away.get("Score")
        finished = (status == 0) and (s1 is not None) and (s2 is not None)

        prev = prev_idx.get(frozenset([t1, t2]), {})
        rec = {
            "date": date or prev.get("date"),
            "group": grp or prev.get("group"),
            "t1": t1, "t2": t2,
            "venue": prev.get("venue") or desc(mm.get("Stadium", {}).get("Name")) or "",
            "city": prev.get("city") or desc(mm.get("Stadium", {}).get("CityName")) or "",
            "goals": prev.get("goals", []),
            "assists": prev.get("assists", []),
            "cards": prev.get("cards", []),
            "lineups": prev.get("lineups"),
        }
        if finished:
            rec["s1"], rec["s2"] = int(s1), int(s2)
            g = rec["group"]
            if g:
                tally.setdefault(g, {})
                for tm in (t1, t2):
                    tally[g].setdefault(tm, {"pld":0,"w":0,"d":0,"l":0,"gf":0,"ga":0,"pts":0})
                tally[g][t1]["gf"] += int(s1); tally[g][t1]["ga"] += int(s2)
                tally[g][t2]["gf"] += int(s2); tally[g][t2]["ga"] += int(s1)
                tally[g][t1]["pld"] += 1; tally[g][t2]["pld"] += 1
                if s1 > s2:
                    tally[g][t1]["w"] += 1; tally[g][t1]["pts"] += 3; tally[g][t2]["l"] += 1
                elif s2 > s1:
                    tally[g][t2]["w"] += 1; tally[g][t2]["pts"] += 3; tally[g][t1]["l"] += 1
                else:
                    tally[g][t1]["d"] += 1; tally[g][t2]["d"] += 1
                    tally[g][t1]["pts"] += 1; tally[g][t2]["pts"] += 1
        else:
            rec["s1"], rec["s2"] = None, None
            rec["pending"] = True
        new_matches.append(rec)

    new_matches.sort(key=lambda r: (r["date"] or "9999", r.get("group") or "Z"))

    # 순위표: 기존 조별 팀명단을 유지하고, 완료경기 집계를 덮어쓴다.
    new_standings = []
    for g in sorted(roster.keys()):
        teams = []
        for tm in roster[g]:
            s = tally.get(g, {}).get(tm)
            if s:
                teams.append({"t":tm,"pld":s["pld"],"w":s["w"],"d":s["d"],"l":s["l"],
                              "gf":s["gf"],"ga":s["ga"],"pts":s["pts"]})
            else:
                teams.append({"t":tm,"pld":0,"w":0,"d":0,"l":0,"gf":0,"ga":0,"pts":0})
        new_standings.append({"g":g,"teams":teams})

    out = dict(existing)
    if new_matches:
        out["matches"] = new_matches
    if new_standings:
        out["standings"] = new_standings
    out["updated"] = datetime.date.today().isoformat()
    out["source_note"] = f"FIFA api.fifa.com (idCompetition={ID_COMPETITION}, idSeason={season})"

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    # 로컬 더블클릭에서도 보이도록 data.js(window.WC_DATA)도 함께 갱신
    with open(os.path.join(ROOT, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.WC_DATA = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n")
    print(f"[ok] FIFA 데이터로 갱신 — 경기 {len(new_matches)}건, 순위 {len(new_standings)}조, 기준일 {out['updated']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
