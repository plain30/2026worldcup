#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026 월드컵 대시보드 데이터 자동 갱신 (견고 버전)

수집 우선순위:
  1) FIFA 공식 데이터 api.fifa.com  (API 키 불필요)
  2) 실패하면 football-data.org    (환경변수 FOOTBALL_DATA_TOKEN 있을 때만)

핵심 동작:
  - 어느 한 곳에서든 경기 데이터를 받으면 data.json + data.js 를 갱신한다.
  - 두 곳 모두 실패하면 종료코드 1 로 끝낸다 → GitHub Actions가 '실패(빨간색)'로 표시되어
    "조용히 멈춤"을 바로 알 수 있다. (기존 FIFA 단독 스크립트의 가장 큰 문제 해결)
  - 'updated' 에 날짜+시각(UTC) 을 기록 → 화면에서 갱신 여부를 눈으로 확인 가능.
  - 선수 상세(라인업/득점/도움/카드)는 공개 API 범위 밖이라 기존 시드값을 팀쌍 기준으로 보존.

수동 실행:  python scripts/update_data.py
"""
import os, sys, json, datetime, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data.json")

FIFA = "https://api.fifa.com/api/v3"
FIFA_COMP = "17"            # FIFA World Cup
SEASON_HINT = "2026"
FD = "https://api.football-data.org/v4/competitions/WC"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept": "application/json, text/plain, */*", "Accept-Language": "en"}

NAME_MAP = {
    "Mexico":"Mexico","South Africa":"South Africa","Korea Republic":"South Korea",
    "Republic of Korea":"South Korea","South Korea":"South Korea","Czechia":"Czechia",
    "Czech Republic":"Czechia","Canada":"Canada","Bosnia and Herzegovina":"Bosnia and Herzegovina",
    "Bosnia-Herzegovina":"Bosnia and Herzegovina","Qatar":"Qatar","Switzerland":"Switzerland",
    "Brazil":"Brazil","Morocco":"Morocco","Haiti":"Haiti","Scotland":"Scotland",
    "USA":"United States","United States":"United States","Australia":"Australia",
    "Türkiye":"Turkey","Turkiye":"Turkey","Turkey":"Turkey","Paraguay":"Paraguay",
    "Germany":"Germany","Curaçao":"Curaçao","Curacao":"Curaçao","Côte d'Ivoire":"Ivory Coast",
    "Cote d'Ivoire":"Ivory Coast","Ivory Coast":"Ivory Coast","Ecuador":"Ecuador",
    "Netherlands":"Netherlands","Japan":"Japan","Sweden":"Sweden","Tunisia":"Tunisia",
    "Belgium":"Belgium","Egypt":"Egypt","IR Iran":"Iran","Iran":"Iran","New Zealand":"New Zealand",
    "Spain":"Spain","Cabo Verde":"Cape Verde","Cape Verde":"Cape Verde","Saudi Arabia":"Saudi Arabia",
    "Uruguay":"Uruguay","France":"France","Senegal":"Senegal","Norway":"Norway","Iraq":"Iraq",
    "Argentina":"Argentina","Austria":"Austria","Algeria":"Algeria","Jordan":"Jordan",
    "Portugal":"Portugal","Colombia":"Colombia","Congo DR":"DR Congo","DR Congo":"DR Congo",
    "Uzbekistan":"Uzbekistan","England":"England","Croatia":"Croatia","Ghana":"Ghana","Panama":"Panama",
}
def norm(n): return NAME_MAP.get((n or "").strip(), (n or "").strip())
def gletter(s):
    if not s: return None
    s=str(s).replace("GROUP_","").replace("Group","").replace("그룹","").replace("조","").strip()
    return s[:1].upper() if s else None

def map_stage(stage_text, grp):
    """FIFA StageName(소문자) → GROUP / R32 / R16 / QF / SF / 3RD / FINAL (모르면 None)."""
    s=(stage_text or "").lower()
    if grp or "group" in s: return "GROUP"
    if "round of 32" in s or "1/16" in s: return "R32"
    if "round of 16" in s or "1/8" in s: return "R16"
    if "quarter" in s or "1/4" in s: return "QF"
    if "semi" in s: return "SF"
    if "third" in s or "3rd" in s or "play-off for third" in s: return "3RD"
    if "final" in s: return "FINAL"
    return None

FD_STAGE={"GROUP_STAGE":"GROUP","LAST_32":"R32","ROUND_OF_32":"R32","LAST_16":"R16","ROUND_OF_16":"R16",
          "QUARTER_FINALS":"QF","QUARTER_FINAL":"QF","SEMI_FINALS":"SF","SEMI_FINAL":"SF",
          "THIRD_PLACE":"3RD","3RD_PLACE":"3RD","FINAL":"FINAL"}

def http_get(url, headers=None):
    req=urllib.request.Request(url, headers=headers or HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def desc(f):
    if isinstance(f,list): return f[0].get("Description") if f and isinstance(f[0],dict) else None
    if isinstance(f,dict): return f.get("Description")
    return f

# ---- 출처 1: FIFA ----  반환: [{date,group,t1,t2,s1,s2,finished}] 또는 None
def from_fifa():
    season=None
    for url in (f"{FIFA}/competitions/{FIFA_COMP}/seasons?language=en",
                f"{FIFA}/seasons?idCompetition={FIFA_COMP}&count=100&language=en"):
        try: data=http_get(url)
        except Exception as e:
            print(f"  [fifa] seasons 요청 실패: {e}"); continue
        rows=data.get("Results") if isinstance(data,dict) else (data if isinstance(data,list) else [])
        for s in (rows or []):
            if SEASON_HINT in str(desc(s.get("Name")) or "") and (s.get("IdSeason") or s.get("id")):
                season=str(s.get("IdSeason") or s.get("id")); break
        if season: break
    if not season:
        print("  [fifa] 2026 시즌 ID를 찾지 못함"); return None
    try:
        md=http_get(f"{FIFA}/calendar/matches?idCompetition={FIFA_COMP}&idSeason={season}&count=500&language=en")
    except Exception as e:
        print(f"  [fifa] matches 요청 실패: {e}"); return None
    raw=md.get("Results") or []
    if not raw:
        print("  [fifa] matches 비어있음"); return None
    out=[]
    for mm in raw:
        grp=gletter(desc(mm.get("GroupName")))
        sk=map_stage(desc(mm.get("StageName")), grp)
        if sk is None: continue
        h,a=mm.get("Home") or {}, mm.get("Away") or {}
        t1,t2=norm(desc(h.get("TeamName"))),norm(desc(a.get("TeamName")))
        if sk=="GROUP" and (not t1 or not t2 or t1=="0" or t2=="0"): continue
        if not t1 or t1=="0": t1=None
        if not t2 or t2=="0": t2=None
        s1,s2=h.get("Score"),a.get("Score")
        fin=(mm.get("MatchStatus")==0) and s1 is not None and s2 is not None
        out.append({"date":(mm.get("LocalDate") or mm.get("Date") or "")[:10],"group":grp,"stage":sk,
                    "t1":t1,"t2":t2,"s1":s1,"s2":s2,"finished":fin})
    print(f"  [fifa] 성공: 경기 {len(out)}건 (season {season})")
    return out if out else None

# ---- 출처 2: football-data.org ----
def from_footballdata(token):
    try:
        mj=http_get(FD+"/matches", {"X-Auth-Token":token})
    except urllib.error.HTTPError as e:
        print(f"  [fd] HTTP {e.code}"); return None
    except Exception as e:
        print(f"  [fd] 요청 실패: {e}"); return None
    out=[]
    for mm in mj.get("matches",[]):
        sk=FD_STAGE.get(mm.get("stage") or "GROUP_STAGE")
        if sk is None: continue
        t1,t2=norm(mm["homeTeam"].get("name")),norm(mm["awayTeam"].get("name"))
        if sk=="GROUP" and (not t1 or not t2): continue
        if not t1: t1=None
        if not t2: t2=None
        ft=(mm.get("score") or {}).get("fullTime") or {}
        s1,s2=ft.get("home"),ft.get("away")
        fin=mm.get("status")=="FINISHED" and s1 is not None and s2 is not None
        out.append({"date":(mm.get("utcDate") or "")[:10],"group":gletter(mm.get("group")),"stage":sk,
                    "t1":t1,"t2":t2,"s1":s1,"s2":s2,"finished":fin})
    print(f"  [fd] 성공: 경기 {len(out)}건")
    return out if out else None

# ---- 선수기록(득점/도움 순위): API-Football (api-sports.io) ----
# 무료 키 발급: https://dashboard.api-sports.io/register  (헤더 x-apisports-key)
APISPORTS = "https://v3.football.api-sports.io"
APISPORTS_LEAGUE = "1"      # FIFA World Cup
APISPORTS_SEASON = "2026"
def from_apisports_players(key):
    if not key:
        return None
    hdr = {"x-apisports-key": key, "Accept": "application/json"}
    def grab(path, field):
        try:
            data = http_get(f"{APISPORTS}/{path}?league={APISPORTS_LEAGUE}&season={APISPORTS_SEASON}", hdr)
        except Exception as e:
            print(f"  [apisports] {path} 실패: {e}"); return None
        rows = data.get("response") or []
        out = []
        for r in rows:
            st = (r.get("statistics") or [{}])[0]
            n = ((st.get("goals") or {}).get(field))
            if not n:
                continue
            out.append({"p": (r.get("player") or {}).get("name") or "?",
                        "t": norm((st.get("team") or {}).get("name")), "n": int(n)})
        out.sort(key=lambda x: (-x["n"], x["p"]))
        return out
    scorers = grab("players/topscorers", "total")     # goals.total
    assists = grab("players/topassists", "assists")    # goals.assists
    if scorers is None and assists is None:
        return None
    print(f"  [apisports] 성공: 득점 {len(scorers or [])}명, 도움 {len(assists or [])}명")
    return {"scorers": scorers or [], "assists": assists or []}

def _apisports_fixtures_index(key):
    """API-Football 경기 목록 → 팀쌍 기준 {fixtureId, status} 인덱스 (1회 호출)."""
    try:
        data = http_get(f"{APISPORTS}/fixtures?league={APISPORTS_LEAGUE}&season={APISPORTS_SEASON}",
                        {"x-apisports-key": key, "Accept": "application/json"})
    except Exception as e:
        print(f"  [apisports] fixtures 실패: {e}"); return None
    idx = {}
    for r in data.get("response") or []:
        tt = r.get("teams") or {}
        h = norm((tt.get("home") or {}).get("name")); a = norm((tt.get("away") or {}).get("name"))
        fx = r.get("fixture") or {}
        if h and a:
            idx[frozenset([h, a])] = {"id": fx.get("id"),
                                      "status": ((fx.get("status") or {}).get("short"))}
    return idx

def enrich_events(matches, key, max_calls=25):
    """완료됐는데 득점 기록이 비어 있는 경기를 API-Football 이벤트로 채운다(경기당 1호출, 상한 max_calls)."""
    if not key:
        return 0
    # 채울 경기(완료·득점비어있음·미수집)가 없으면 API 호출 자체를 생략 → 무료 쿼터 절약
    candidates = [m for m in matches if (not m.get("pending")) and (not m.get("eventsFetched")) and (not m.get("goals"))]
    if not candidates:
        print("  [apisports] 채울 경기 없음 — 호출 생략")
        return 0
    idx = _apisports_fixtures_index(key)
    if not idx:
        return 0
    hdr = {"x-apisports-key": key, "Accept": "application/json"}
    FIN = {"FT", "AET", "PEN"}
    calls = filled = 0
    for m in matches:
        if m.get("pending") or m.get("eventsFetched") or m.get("goals"):
            continue   # 예정/이미수집/시드보유 → 건너뜀
        info = idx.get(frozenset([m["t1"], m["t2"]]))
        if not info or not info.get("id") or info.get("status") not in FIN:
            continue
        if calls >= max_calls:
            break
        calls += 1
        try:
            data = http_get(f"{APISPORTS}/fixtures/events?fixture={info['id']}", hdr)
        except Exception as e:
            print(f"  [apisports] events {info['id']} 실패: {e}"); continue
        goals, assists, cards = [], [], []
        for ev in data.get("response") or []:
            typ, det = ev.get("type"), (ev.get("detail") or "")
            tm = norm((ev.get("team") or {}).get("name"))
            pl = (ev.get("player") or {}).get("name") or "?"
            tinfo = ev.get("time") or {}; mn = tinfo.get("elapsed")
            if mn is not None and tinfo.get("extra"):
                mn = f"{mn}+{tinfo.get('extra')}"
            if typ == "Goal":
                if det == "Missed Penalty":
                    continue
                nm = pl + (" (PK)" if det == "Penalty" else " (자책골)" if det == "Own Goal" else "")
                goals.append({"p": nm, "t": tm, "m": mn})
                asy = (ev.get("assist") or {}).get("name")
                if asy:
                    assists.append({"p": asy, "t": tm})
            elif typ == "Card":
                cards.append({"p": pl, "t": tm, "m": mn, "c": "red" if "Red" in det else "yellow"})
        m["goals"], m["assists"], m["cards"] = goals, assists, cards
        m["eventsFetched"] = True
        filled += 1
    if calls:
        print(f"  [apisports] 경기별 이벤트 {filled}건 채움 (호출 {calls})")
    return filled

def build(existing, raw_matches, source):
    prev={frozenset([m["t1"],m["t2"]]):m for m in existing.get("matches",[])}
    roster={g["g"]:[t["t"] for t in g["teams"]] for g in existing.get("standings",[])}
    matches, tally=[], {}
    for r in raw_matches:
        if r.get("stage") and r["stage"]!="GROUP": continue   # 조별 경기만 (녹아웃은 bracket으로)
        t1,t2,grp=r["t1"],r["t2"],r["group"]
        p=prev.get(frozenset([t1,t2]),{})
        grp=grp or p.get("group")
        rec={"date":r["date"] or p.get("date"),"group":grp,"t1":t1,"t2":t2,
             "venue":p.get("venue",""),"city":p.get("city",""),
             "goals":p.get("goals",[]),"assists":p.get("assists",[]),
             "cards":p.get("cards",[]),"lineups":p.get("lineups")}
        if p.get("eventsFetched"): rec["eventsFetched"]=True   # 이벤트 수집완료 표시 보존(0-0 재호출 방지)
        if r["finished"]:
            rec["s1"],rec["s2"]=int(r["s1"]),int(r["s2"])
            if grp:
                tally.setdefault(grp,{})
                for tm in (t1,t2): tally[grp].setdefault(tm,{"pld":0,"w":0,"d":0,"l":0,"gf":0,"ga":0,"pts":0})
                a,b=int(r["s1"]),int(r["s2"])
                tally[grp][t1]["gf"]+=a; tally[grp][t1]["ga"]+=b; tally[grp][t1]["pld"]+=1
                tally[grp][t2]["gf"]+=b; tally[grp][t2]["ga"]+=a; tally[grp][t2]["pld"]+=1
                if a>b: tally[grp][t1]["w"]+=1; tally[grp][t1]["pts"]+=3; tally[grp][t2]["l"]+=1
                elif b>a: tally[grp][t2]["w"]+=1; tally[grp][t2]["pts"]+=3; tally[grp][t1]["l"]+=1
                else:
                    tally[grp][t1]["d"]+=1; tally[grp][t2]["d"]+=1
                    tally[grp][t1]["pts"]+=1; tally[grp][t2]["pts"]+=1
        else:
            rec["s1"],rec["s2"]=None,None; rec["pending"]=True
        matches.append(rec)
    matches.sort(key=lambda r:(r["date"] or "9999", r.get("group") or "Z"))

    standings=[]
    for g in sorted(roster.keys()):
        teams=[]
        for tm in roster[g]:
            s=tally.get(g,{}).get(tm)
            teams.append({"t":tm, **(s if s else {"pld":0,"w":0,"d":0,"l":0,"gf":0,"ga":0,"pts":0})})
        standings.append({"g":g,"teams":teams})

    out=dict(existing)
    out["matches"]=matches
    out["standings"]=standings
    out["updated"]=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    out["source_note"]=source
    return out

def build_bracket(raw):
    KEY={"R32":"r32","R16":"r16","QF":"qf","SF":"sf","3RD":"third","FINAL":"final"}
    b={"r32":[],"r16":[],"qf":[],"sf":[],"third":[],"final":[]}
    for r in raw or []:
        k=KEY.get(r.get("stage"))
        if not k: continue
        b[k].append({"t1":r.get("t1"),"t2":r.get("t2"),
                     "s1":(int(r["s1"]) if r.get("finished") else None),
                     "s2":(int(r["s2"]) if r.get("finished") else None)})
    return b

def compute_ranks(matches):
    """경기별 득점/도움으로 토너먼트 순위 집계 (where=어느 상대전에서 몇 분에)."""
    sc={}; asg={}
    for m in matches:
        if m.get("pending"): continue
        def opp(t): return m["t2"] if t==m["t1"] else m["t1"]
        for g in (m.get("goals") or []):
            nm=g.get("p","")
            if "자책골" in nm: continue
            nm=nm.replace(" (PK)","").strip()
            e=sc.setdefault(nm+"|"+g["t"],{"p":nm,"t":g["t"],"n":0,"w":{}})
            e["n"]+=1; e["w"].setdefault(opp(g["t"]),[]).append(g.get("m"))
        for a in (m.get("assists") or []):
            e=asg.setdefault(a["p"]+"|"+a["t"],{"p":a["p"],"t":a["t"],"n":0,"w":{}})
            e["n"]+=1; e["w"].setdefault(opp(a["t"]),[]).append(None)
    def fin(d):
        out=[]
        for e in d.values():
            where=[{"o":o,"m":[x for x in mins if x is not None]} for o,mins in e["w"].items()]
            out.append({"p":e["p"],"t":e["t"],"n":e["n"],"where":where})
        out.sort(key=lambda x:(-x["n"], x["p"]))
        return out
    return fin(sc), fin(asg)

def main():
    existing=json.load(open(DATA_PATH,encoding="utf-8"))
    token=os.environ.get("FOOTBALL_DATA_TOKEN")

    print("[1/2] FIFA 시도…")
    raw=from_fifa(); source="FIFA api.fifa.com"
    if not raw and token:
        print("[2/2] FIFA 실패 → football-data.org 시도…")
        raw=from_footballdata(token); source="football-data.org"
    elif not raw:
        print("[2/2] FIFA 실패 + FOOTBALL_DATA_TOKEN 없음 → 대체 불가")

    if not raw:
        print("[ERROR] 어느 출처에서도 데이터를 받지 못했습니다. data.json 미변경.")
        print("        해결: (a) 잠시 후 재시도, 또는 (b) FOOTBALL_DATA_TOKEN 시크릿 등록 후 재실행.")
        return 1   # Actions를 빨간색(실패)으로 → 멈춤이 보이게

    out=build(existing, raw, source)

    # 경기별 선수기록(득점자·도움·카드) — APISPORTS_KEY 있을 때 API-Football로 채움
    apikey=os.environ.get("APISPORTS_KEY")
    if apikey:
        print("[+] API-Football 경기별 이벤트(득점·도움·카드) 채우는 중…")
        enrich_events(out["matches"], apikey)

    # 득점/도움 순위(어느 경기인지 포함) — 경기 이벤트로부터 집계
    sc, asg = compute_ranks(out["matches"])
    if not sc and apikey:                 # 이벤트가 아직 없으면 API-Football 순위로 폴백(경기정보 없음)
        pr=from_apisports_players(apikey)
        if pr: sc, asg = pr.get("scorers",[]), pr.get("assists",[])
    out["scorers"] = sc if sc else existing.get("scorers", [])
    out["assists"] = asg if asg else existing.get("assists", [])

    # 녹아웃 대진표(32강~결승) — 미정 경기는 팀 null
    out["bracket"] = build_bracket(raw)

    json.dump(out, open(DATA_PATH,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(ROOT,"data.js"),"w",encoding="utf-8") as f:
        f.write("window.WC_DATA = "+json.dumps(out,ensure_ascii=False,indent=2)+";\n")
    done=sum(1 for m in out["matches"] if not m.get("pending"))
    print(f"[ok] 갱신 완료 — 출처 {source}, 총 {len(out['matches'])}경기 (완료 {done}), 기준 {out['updated']}")
    return 0

if __name__=="__main__":
    sys.exit(main())
