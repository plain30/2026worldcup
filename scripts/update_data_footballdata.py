#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[대체용] football-data.org 기반 갱신 스크립트.

FIFA API(update_data.py)가 깃허브 러너에서 차단되는 등 동작하지 않을 때 사용하는 백업.
무료 API 토큰이 필요하다(환경변수 FOOTBALL_DATA_TOKEN). 토큰 발급:
  https://www.football-data.org/client/register

사용하려면 .github/workflows/update-data.yml 의 실행 단계를
  run: python scripts/update_data.py
에서
  env:
    FOOTBALL_DATA_TOKEN: ${{ secrets.FOOTBALL_DATA_TOKEN }}
  run: python scripts/update_data_footballdata.py
로 바꾸고, 저장소 Secrets에 FOOTBALL_DATA_TOKEN 을 등록한다.
"""
import os, sys, json, datetime, urllib.request, urllib.error

API = "https://api.football-data.org/v4/competitions/WC"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data.json")

NAME_MAP = {
    "United States":"United States","USA":"United States",
    "Korea Republic":"South Korea","South Korea":"South Korea",
    "Türkiye":"Turkey","Turkiye":"Turkey","Turkey":"Turkey",
    "Czech Republic":"Czechia","Czechia":"Czechia",
    "Côte d'Ivoire":"Ivory Coast","Ivory Coast":"Ivory Coast",
    "Curaçao":"Curaçao","Curacao":"Curaçao",
    "Cabo Verde":"Cape Verde","Cape Verde":"Cape Verde",
    "DR Congo":"DR Congo","Congo DR":"DR Congo",
    "Bosnia-Herzegovina":"Bosnia and Herzegovina","Bosnia and Herzegovina":"Bosnia and Herzegovina",
}

def norm(n): return NAME_MAP.get((n or "").strip(), (n or "").strip())
def gl(g):  return (g or "").replace("GROUP_","").replace("Group","").strip()[:1].upper() or None

def fetch(path, token):
    req = urllib.request.Request(API+path, headers={"X-Auth-Token": token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    token = os.environ.get("FOOTBALL_DATA_TOKEN")
    existing = json.load(open(DATA_PATH, encoding="utf-8"))
    if not token:
        print("[ERROR] FOOTBALL_DATA_TOKEN 시크릿이 설정되지 않았습니다.")
        print("        저장소 Settings > Secrets and variables > Actions 에서")
        print("        Name=FOOTBALL_DATA_TOKEN 으로 무료 토큰을 등록하세요.")
        print("        토큰 발급: https://www.football-data.org/client/register")
        return 1   # Action을 빨간색(실패)으로 표시해 설정 누락을 알림
    try:
        mj = fetch("/matches", token); sj = fetch("/standings", token)
    except urllib.error.HTTPError as e:
        body = ""
        try: body = e.read().decode("utf-8")[:300]
        except Exception: pass
        print(f"[ERROR] API HTTP {e.code}: {body}")
        print("        토큰이 유효한지, 무료 플랜이 월드컵(WC)을 포함하는지 확인하세요.")
        return 1
    except Exception as e:
        print(f"[ERROR] API 요청 실패: {e}"); return 1
    print(f"[info] 받은 경기 {len(mj.get('matches',[]))}건, 순위 그룹 {len(sj.get('standings',[]))}개")

    detail = {frozenset([m["t1"],m["t2"]]): m for m in existing.get("matches",[])}
    new_matches=[]
    for mm in mj.get("matches",[]):
        if mm.get("stage") not in (None,"GROUP_STAGE"): continue
        t1=norm(mm["homeTeam"].get("name")); t2=norm(mm["awayTeam"].get("name"))
        if not t1 or not t2: continue
        date=(mm.get("utcDate") or "")[:10]; grp=gl(mm.get("group"))
        ft=(mm.get("score") or {}).get("fullTime") or {}
        s1,s2=ft.get("home"),ft.get("away")
        fin=mm.get("status")=="FINISHED" and s1 is not None and s2 is not None
        p=detail.get(frozenset([t1,t2]),{})
        rec={"date":date or p.get("date"),"group":grp or p.get("group"),"t1":t1,"t2":t2,
             "venue":p.get("venue",""),"city":p.get("city",""),
             "goals":p.get("goals",[]),"assists":p.get("assists",[]),"cards":p.get("cards",[]),
             "lineups":p.get("lineups")}
        if fin: rec["s1"],rec["s2"]=s1,s2
        else: rec["s1"],rec["s2"]=None,None; rec["pending"]=True
        new_matches.append(rec)
    new_matches.sort(key=lambda r:(r["date"] or "9999", r.get("group") or "Z"))

    new_st=[]
    for st in sj.get("standings",[]):
        if st.get("type") not in (None,"TOTAL"): continue
        g=gl(st.get("group")); teams=[]
        for row in st.get("table",[]):
            teams.append({"t":norm(row["team"].get("name")),"pld":row.get("playedGames",0),
                "w":row.get("won",0),"d":row.get("draw",0),"l":row.get("lost",0),
                "gf":row.get("goalsFor",0),"ga":row.get("goalsAgainst",0),"pts":row.get("points",0)})
        if g and teams: new_st.append({"g":g,"teams":teams})

    out=dict(existing)
    if new_matches: out["matches"]=new_matches
    if new_st: out["standings"]=sorted(new_st,key=lambda x:x["g"])
    out["updated"]=datetime.date.today().isoformat()
    json.dump(out, open(DATA_PATH,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(ROOT,"data.js"),"w",encoding="utf-8") as f:
        f.write("window.WC_DATA = "+json.dumps(out,ensure_ascii=False,indent=2)+";\n")
    print(f"[ok] football-data 갱신 — 경기 {len(new_matches)}, 순위 {len(new_st)}조")
    return 0

if __name__=="__main__":
    sys.exit(main())
