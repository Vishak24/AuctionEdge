import sys, os
sys.path.insert(0, os.path.dirname(__file__))  # ← ADD THIS LINE

import plotly.graph_objects as go
import plotly.express as px
import json


import streamlit as st
import pandas as pd
from engine.players  import PLAYERS
from engine.team     import Team, BUDGET, MAX_PLAYERS, SQUAD_REQS, MAX_OVERSEAS
from engine.decision import decide
from engine.optimizer import recommend_targets, best_xi

# ── Constants ──────────────────────────────────────────────────────────────────
IPL_TEAMS = {
    "CSK":  {"full":"Chennai Super Kings",       "color":"#F5C518","bg":"#2a2200"},
    "MI":   {"full":"Mumbai Indians",            "color":"#0EA5E9","bg":"#001a2e"},
    "RCB":  {"full":"Royal Challengers Bengaluru","color":"#EF4444","bg":"#2a0002"},
    "KKR":  {"full":"Kolkata Knight Riders",     "color":"#A78BFA","bg":"#1a0030"},
    "DC":   {"full":"Delhi Capitals",            "color":"#60A5FA","bg":"#001a2e"},
    "GT":   {"full":"Gujarat Titans",            "color":"#38BDF8","bg":"#001a2a"},
    "LSG":  {"full":"Lucknow Super Giants",      "color":"#34D399","bg":"#001a10"},
    "PBKS": {"full":"Punjab Kings",              "color":"#FB7185","bg":"#2a0005"},
    "RR":   {"full":"Rajasthan Royals",          "color":"#F472B6","bg":"#2a0018"},
    "SRH":  {"full":"Sunrisers Hyderabad",       "color":"#FB923C","bg":"#2a0e00"},
}
TEAM_NAMES = list(IPL_TEAMS.keys())
ROLE_COLORS = {"BATSMAN":"#60A5FA","BOWLER":"#F472B6","ALL-ROUNDER":"#34D399","WICKETKEEPER":"#FBBF24"}
FLAGS = {"India":"IN","Australia":"AU","England":"EN","South Africa":"SA",
         "West Indies":"WI","New Zealand":"NZ","Afghanistan":"AF","Sri Lanka":"LK"}

st.set_page_config(page_title="IPL Auction AI", page_icon="🏏", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#080810;color:#e2e8f0;}
.main .block-container{padding:1rem 1.4rem;max-width:100%;}
section[data-testid="stSidebar"]{background:#0a0a1a;border-right:1px solid #1e1e3a;}
.stTabs [data-baseweb="tab-list"]{background:#0d0d1f;border-radius:12px;padding:4px;gap:4px;}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px;color:#64748b;font-weight:600;padding:8px 18px;font-size:14px;}
.stTabs [aria-selected="true"]{background:#1e1e3a!important;color:#e2e8f0!important;}
.gc{background:linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01));
    border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:18px;margin-bottom:12px;}
.mc{background:#0d0d1f;border:1px solid #1e1e3a;border-radius:12px;padding:16px;text-align:center;}
.mv{font-size:26px;font-weight:800;line-height:1.1;}
.ml{font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.1em;margin-top:3px;}
.dBID{background:linear-gradient(135deg,#052e16,#14532d);border:2px solid #22c55e;border-radius:16px;padding:22px;box-shadow:0 0 30px rgba(34,197,94,.2);}
.dSHILL{background:linear-gradient(135deg,#1c1007,#451a03);border:2px solid #f59e0b;border-radius:16px;padding:22px;box-shadow:0 0 30px rgba(245,158,11,.2);}
.dPASS{background:linear-gradient(135deg,#1c0707,#450a0a);border:2px solid #ef4444;border-radius:16px;padding:22px;box-shadow:0 0 30px rgba(239,68,68,.2);}
.dt{font-size:30px;font-weight:900;margin:0;letter-spacing:-.5px;}
.ds{font-size:18px;font-weight:700;margin:4px 0 0;}
.rc{background:#0d0d1f;border-radius:12px;padding:13px 15px;border-left:4px solid;margin-bottom:7px;}
.rp{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;background:#1e1e3a;color:#94a3b8;margin:2px;}
.wp{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;background:#450a0a;color:#fca5a5;margin:2px;}
.sh{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.1em;margin:14px 0 7px;border-bottom:1px solid #1e1e3a;padding-bottom:5px;}
.le{background:#0d0d1f;border:1px solid #1e1e3a;border-radius:7px;padding:7px 11px;font-size:13px;margin-bottom:4px;color:#94a3b8;}
.lm{border-color:#22c55e!important;color:#bbf7d0!important;}
.stButton>button{background:#1e1e3a;border:1px solid #2e2e5a;color:#e2e8f0;border-radius:8px;font-weight:600;}
.stButton>button:hover{background:#2e2e5a;}
.stSelectbox>div>div,.stNumberInput>div>div>input{background:#0d0d1f!important;border:1px solid #1e1e3a!important;color:#e2e8f0!important;border-radius:8px!important;}
#MainMenu,footer,header{visibility:hidden;}
</style>""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
if "my_franchise" not in st.session_state:
    st.session_state.my_franchise = None
    st.session_state.my_team      = None
    st.session_state.rivals       = {}
    st.session_state.log          = []

def color_balance(b):
    p = b/BUDGET
    return "#22c55e" if p>.55 else "#f59e0b" if p>.30 else "#ef4444"

def all_bought():
    t = ([st.session_state.my_team] if st.session_state.my_team else [])
    t += list(st.session_state.rivals.values())
    return {p["name"] for team in t for p in team.squad}

def avail_players():
    return sorted([n for n in PLAYERS if n not in all_bought()])

def smart_max_bid(pname, my_team, rivals):
    pdata = PLAYERS[pname]
    pts,role,base = pdata["pts"],pdata["role"],pdata["base"]
    slots  = my_team.slots_remaining()
    budget = my_team.budget
    if slots == 0: return base, budget-base, True, "Squad full"
    needed = my_team.mandatory_roles_needed()
    all_t  = [my_team]+rivals
    bought = {p["name"] for t in all_t for p in t.squad} | {pname}
    avail  = {n:d for n,d in PLAYERS.items() if n not in bought}
    mand_cost = 0
    for req_role, cnt in needed.items():
        adj = max(0, cnt-(1 if req_role==role else 0))
        cands = sorted(d["base"] for n,d in avail.items() if d["role"]==req_role)
        mand_cost += sum(cands[:adj])
    free_slots = slots-1-sum(max(0,v-(1 if k==role else 0)) for k,v in needed.items())
    free_budget = budget - mand_cost
    per_slot    = free_budget/max(free_slots,1) if free_slots>0 else free_budget
    urgency     = 2.2 if role in needed else 1.0
    max_b = int(per_slot*(pts/42.0)*urgency*0.85)
    max_b = min(max_b, int(budget*0.60))
    max_b = max(max_b, base)
    after = budget - max_b
    ok    = after >= mand_cost
    msg = (f"✅ After ₹{max_b}L — ₹{after}L left, enough to fill remaining slots."
           if ok else
           f"⚡ If you spend ₹{max_b}L, recover by targeting base-price players only for "
           f"remaining {slots-1} slots (min mandatory cost: ₹{mand_cost}L).")
    return max_b, after, ok, msg

# ── SETUP SCREEN ──────────────────────────────────────────────────────────────
if st.session_state.my_franchise is None:
    st.markdown("""<div style='text-align:center;padding:40px 0 20px'>
    <div style='font-size:54px'>🏏</div>
    <h1 style='font-size:34px;font-weight:900;margin:6px 0 4px'>IPL Auction AI</h1>
    <p style='color:#64748b;font-size:15px'>Real-time bidding advisor · IPL Auction Battle 6.0</p>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    _, mid, _ = st.columns([1,2,1])
    with mid:
        st.markdown("<div class='sh'>SELECT YOUR FRANCHISE</div>", unsafe_allow_html=True)
        items = list(IPL_TEAMS.items())
        for row in range(5):
            c1,c2 = st.columns(2)
            for ci,col in enumerate([c1,c2]):
                idx = row*2+ci
                if idx < len(items):
                    abbr,info = items[idx]
                    with col:
                        if st.button(f"{abbr} — {info['full']}", key=f"pick_{abbr}", use_container_width=True):
                            st.session_state.my_franchise = abbr
                            st.session_state.my_team = Team(abbr)
                            for t in TEAM_NAMES:
                                if t!=abbr: st.session_state.rivals[t] = Team(t)
                            st.rerun()
    st.stop()

# ── MAIN APP ──────────────────────────────────────────────────────────────────
my_team  = st.session_state.my_team
rivals   = list(st.session_state.rivals.values())
my_abbr  = st.session_state.my_franchise
my_info  = IPL_TEAMS[my_abbr]

# SIDEBAR
with st.sidebar:
    pct = my_team.spent/BUDGET
    st.markdown(f"""<div style='background:{my_info["bg"]};border:1px solid {my_info["color"]}44;
    border-radius:12px;padding:12px 16px;margin-bottom:12px;'>
    <div style='font-size:10px;color:{my_info["color"]}88;font-weight:700;text-transform:uppercase;letter-spacing:.1em'>MY TEAM</div>
    <div style='font-size:24px;font-weight:900;color:{my_info["color"]}'>{my_abbr}</div>
    <div style='font-size:12px;color:#64748b'>{my_info["full"]}</div>
    <div style='margin-top:8px;font-size:20px;font-weight:800;color:{color_balance(my_team.budget)}'>₹{my_team.budget}L</div>
    <div style='background:#1e1e3a;border-radius:6px;height:8px;margin-top:6px;overflow:hidden'>
    <div style='background:linear-gradient(90deg,#22c55e,#f59e0b {min(pct*200,100):.0f}%,#ef4444);
    width:{pct*100:.1f}%;height:100%;'></div></div>
    <div style='display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-top:3px'>
    <span>₹{my_team.spent}L spent</span><span>{int(pct*100)}%</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='sh'>RECORD PURCHASE</div>", unsafe_allow_html=True)
    ap = avail_players()
    if ap:
        all_names  = [my_abbr]+[r.name for r in rivals]
        buyer_s    = st.selectbox("Team", all_names, key="sb_b")
        # Auto-sync with Player on the Block
        default_idx = ap.index(st.session_state.get("_last_block_player", ap[0])) \
                  if st.session_state.get("_last_block_player") in ap else 0
        player_s   = st.selectbox("Player", ap, index=default_idx, key="sb_p")

        pd_info    = PLAYERS[player_s]
        st.markdown(f"""<div style='background:#0d0d1f;border:1px solid #1e1e3a;border-radius:8px;
        padding:9px 12px;margin:6px 0;font-size:13px'>
        <b style='color:#e2e8f0'>{player_s}</b><br>
        <span style='color:{ROLE_COLORS.get(pd_info["role"],"#94a3b8")}'>{pd_info["role"]}</span>
        <span style='color:#64748b'> · {pd_info["country"]} · ⭐{pd_info["pts"]}pts · Base ₹{pd_info["base"]}L</span>
        </div>""", unsafe_allow_html=True)
        price_s = st.number_input("Price (₹L)", min_value=pd_info["base"],
                           max_value=7000, step=10, value=pd_info["base"], key="sb_pr")

        ovp = int((price_s/pd_info["base"]-1)*100)
        if ovp > 80:
            st.markdown(f"""<div style='background:#2a1500;border:1px solid #f59e0b;border-radius:7px;
            padding:7px 11px;font-size:12px;color:#fbbf24;margin:3px 0'>⚠️ +{ovp}% above base price</div>""",
            unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm", use_container_width=True, key="btn_c"):
                buyer_t = (my_team if buyer_s==my_abbr else st.session_state.rivals[buyer_s])
                buyer_t.add_player(player_s, PLAYERS[player_s], price_s)
                is_mine = buyer_s==my_abbr
                st.session_state.log.append({"text":f"{'🏆 '+my_abbr if is_mine else '👁 '+buyer_s}: {player_s} → ₹{price_s}L","mine":is_mine})
                st.rerun()
        with c2:
            if st.button("↩️ Undo", use_container_width=True, key="btn_u"):
                bt = my_team if buyer_s==my_abbr else st.session_state.rivals.get(buyer_s)
                if bt and bt.squad:
                    bt.remove_last()
                    if st.session_state.log: st.session_state.log.pop()
                    st.rerun()
    else:
        st.info("All players purchased!")

    st.markdown("<div class='sh'>UPDATE RIVAL BALANCE</div>", unsafe_allow_html=True)
    rsel = st.selectbox("Rival", [r.name for r in rivals], key="rbal_s")
    nbal = st.number_input("Balance (₹L)", 0, 7000, step=50, key="rbal_v")
    if st.button("Set Balance", use_container_width=True, key="rbal_b"):
        st.session_state.rivals[rsel].budget = nbal; st.rerun()

    st.markdown("<div class='sh'>OPTIONS</div>", unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 Export", use_container_width=True):
            d = {"my_franchise":my_abbr,"my_team":my_team.to_dict(),
                 "rivals":{k:v.to_dict() for k,v in st.session_state.rivals.items()}}
            st.download_button("⬇️ JSON", json.dumps(d,indent=2),"auction.json","application/json")
    with c2:
        if st.button("🔄 Reset", use_container_width=True):
            [st.session_state.pop(k) for k in list(st.session_state.keys())]; st.rerun()

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4,tab5 = st.tabs(["⚡  Live Advisor","📋  My Squad","🎯  Targets","📊  Dashboard","👥  All Teams"])


# ── TAB 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    ap2 = avail_players()
    if not ap2:
        st.info("All players purchased!"); st.stop()

    colA, colB = st.columns([1.45,1], gap="large")

    with colA:
        st.markdown("<div class='sh'>PLAYER ON THE BLOCK</div>", unsafe_allow_html=True)
        pup   = st.selectbox("", ap2, key="lp", label_visibility="collapsed")
        pd2   = PLAYERS[pup]

        # Auto-reset bid to base price when player changes
        if st.session_state.get("_last_block_player") != pup:
            st.session_state["_last_block_player"] = pup
            st.session_state["_bid_val"] = pd2["base"]

        cbid  = st.number_input("Current bid (₹L)", min_value=pd2["base"],
                         max_value=7000, step=10, value=pd2["base"], key=f"lb_{pup}")




        rc2   = ROLE_COLORS.get(pd2["role"],"#94A3B8")

        # Player card
        ovp2  = int((cbid/pd2["base"]-1)*100)
        st.markdown(f"""<div class='gc' style='border-color:{rc2}33;padding:16px'>
        <div style='display:flex;align-items:center;gap:14px'>
        <div style='background:{rc2}22;border:2px solid {rc2};border-radius:50%;
            width:54px;height:54px;display:flex;align-items:center;justify-content:center;
            font-size:20px;font-weight:900;color:{rc2};flex-shrink:0'>{pd2["pts"]}</div>
        <div style='flex:1'>
          <div style='font-size:21px;font-weight:800'>{pup}</div>
          <div style='margin-top:5px;display:flex;gap:6px;flex-wrap:wrap'>
            <span style='background:{rc2}22;color:{rc2};padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700'>{pd2["role"]}</span>
            <span style='background:#1e1e3a;color:#94a3b8;padding:2px 10px;border-radius:20px;font-size:12px'>{pd2["country"]}</span>
            <span style='background:#1e1e3a;color:#94a3b8;padding:2px 10px;border-radius:20px;font-size:12px'>Base ₹{pd2["base"]}L</span>
          </div>
        </div>
        <div style='text-align:right'>
          <div style='font-size:11px;color:#64748b'>Current Bid</div>
          <div style='font-size:28px;font-weight:900'>₹{cbid}L</div>
          <div style='font-size:12px;color:{"#f59e0b" if ovp2>50 else "#22c55e"}'>{ovp2:+d}% vs base</div>
        </div></div></div>""", unsafe_allow_html=True)

        # Compute
        smart_max, b_after, cope, recover_msg = smart_max_bid(pup, my_team, rivals)
        result = decide(pup, pd2, cbid, my_team, rivals)
        action = result["action"]
        ac = {"BID":"#22c55e","SHILL":"#f59e0b","PASS":"#ef4444"}[action]
        ai = {"BID":"🟢","SHILL":"🟡","PASS":"🔴"}[action]
        al = {"BID":"BID — Go for it!","SHILL":"SHILL — Push rivals, then DROP","PASS":"PASS — Let them overpay"}[action]

        st.markdown(f"""<div class='d{action}'>
            <div class='dt' style='color:{ac}'>{ai} {al}</div>
            </div>""", unsafe_allow_html=True)


        # SPEND ANALYSIS
        st.markdown("<div class='sh'>SPEND ANALYSIS</div>", unsafe_allow_html=True)
        base_p = pd2["base"]
        est_p  = result["est_price"]
        danger = int(est_p*1.45)
        span   = max(danger-base_p, 1)
        safe_w = min((smart_max-base_p)/span*100, 100)
        caut_w = min((est_p-smart_max)/span*100, 40)
        curr_w = min((cbid-base_p)/span*100, 98)
        in_zone = "SAFE" if cbid<=smart_max else ("CAUTION" if cbid<=est_p else "DANGER")
        zone_c  = {"SAFE":"#22c55e","CAUTION":"#f59e0b","DANGER":"#ef4444"}[in_zone]

        st.markdown(f"""<div class='gc'>
        <div style='font-size:14px;font-weight:700;margin-bottom:12px'>How far can you push?
          <span style='float:right;font-size:12px;background:{zone_c}22;color:{zone_c};
          padding:2px 10px;border-radius:20px;font-weight:700'>● {in_zone}</span></div>
        <div style='display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-bottom:5px'>
          <span>Base ₹{base_p}L</span><span style='color:#22c55e'>Safe ≤₹{smart_max}L</span>
          <span style='color:#f59e0b'>Est ₹{est_p}L</span><span style='color:#ef4444'>Max ₹{danger}L</span>
        </div>
        <div style='background:#1e1e3a;border-radius:8px;height:18px;overflow:hidden;display:flex'>
          <div style='background:#22c55e;width:{safe_w:.1f}%;height:100%'></div>
          <div style='background:#f59e0b;width:{caut_w:.1f}%;height:100%'></div>
          <div style='background:#ef4444;flex:1;height:100%;opacity:.55'></div>
        </div>
        <div style='position:relative;height:18px;margin-top:3px'>
          <div style='position:absolute;left:{curr_w:.1f}%;transform:translateX(-50%);
          font-size:12px;color:{zone_c};font-weight:800'>▲ ₹{cbid}L</div>
        </div>
        <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:14px'>
          <div style='background:#052e16;border:1px solid #22c55e44;border-radius:8px;padding:10px;text-align:center'>
            <div style='font-size:11px;color:#22c55e;font-weight:700'>✅ SAFE</div>
            <div style='font-size:15px;font-weight:800'>≤₹{smart_max}L</div>
            <div style='font-size:11px;color:#64748b'>Bid freely</div>
          </div>
          <div style='background:#1c1007;border:1px solid #f59e0b44;border-radius:8px;padding:10px;text-align:center'>
            <div style='font-size:11px;color:#f59e0b;font-weight:700'>⚠️ CAUTION</div>
            <div style='font-size:15px;font-weight:800'>₹{smart_max}–{est_p}L</div>
            <div style='font-size:11px;color:#64748b'>Think hard</div>
          </div>
          <div style='background:#1c0707;border:1px solid #ef444444;border-radius:8px;padding:10px;text-align:center'>
            <div style='font-size:11px;color:#ef4444;font-weight:700'>🚨 DANGER</div>
            <div style='font-size:15px;font-weight:800'>>₹{est_p}L</div>
            <div style='font-size:11px;color:#64748b'>Rival overpaying</div>
          </div>
        </div>
        </div>""", unsafe_allow_html=True)

        bg_r  = "#052e16" if cope else "#450a0a"
        brd_r = "#22c55e" if cope else "#ef4444"
        st.markdown(f"""<div style='background:{bg_r};border:1px solid {brd_r}55;
        border-radius:10px;padding:13px 16px;font-size:13px;color:#94a3b8'>{recover_msg}</div>""",
        unsafe_allow_html=True)

    with colB:
        st.markdown("<div class='sh'>RIVAL WATCH</div>", unsafe_allow_html=True)
        for t in sorted(rivals, key=lambda x: x.budget, reverse=True):
            info  = IPL_TEAMS[t.name]
            rc    = t.role_count()
            needs = t.mandatory_roles_needed()
            bc    = color_balance(t.budget)
            bp    = t.budget/BUDGET
            need_html = "".join(f"<span class='wp'>⚠️{v}×{k[:3]}</span>" for k,v in needs.items())
            st.markdown(f"""<div class='rc' style='border-left-color:{info["color"]}'>
            <div style='display:flex;justify-content:space-between;align-items:center'>
              <div>
                <span style='font-size:15px;font-weight:800;color:{info["color"]}'>{t.name}</span>
                <span style='font-size:11px;color:#64748b;margin-left:7px'>{len(t.squad)} players · 🌍{t.overseas_count()}/7</span>
              </div>
              <div style='font-size:18px;font-weight:800;color:{bc}'>₹{t.budget}L</div>
            </div>
            <div style='background:#1e1e3a;border-radius:4px;height:4px;margin:5px 0'>
              <div style='background:{bc};width:{bp*100:.1f}%;height:100%;border-radius:4px'></div>
            </div>
            <div>
              <span class='rp'>WK:{rc.get("WICKETKEEPER",0)}</span>
              <span class='rp'>BAT:{rc.get("BATSMAN",0)}</span>
              <span class='rp'>AR:{rc.get("ALL-ROUNDER",0)}</span>
              <span class='rp'>BO:{rc.get("BOWLER",0)}</span>
              {need_html}
            </div>
            <div style='font-size:12px;margin-top:4px;color:#94a3b8'>Top-16: <b style='color:#e2e8f0'>{t.top16_pts()}</b></div>
            </div>""", unsafe_allow_html=True)

        if st.session_state.log:
            st.markdown("<div class='sh'>AUCTION LOG</div>", unsafe_allow_html=True)
            for e in reversed(st.session_state.log[-10:]):
                cls = "le lm" if e["mine"] else "le"
                st.markdown(f"<div class='{cls}'>{e['text']}</div>", unsafe_allow_html=True)

# ── TAB 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    rc  = my_team.role_count()
    ndd = my_team.mandatory_roles_needed()
    pct2= my_team.spent/BUDGET

    st.markdown(f"""<div class='gc' style='border-color:{my_info["color"]}44'>
    <div style='display:flex;align-items:center;gap:16px'>
      <div>
        <div style='font-size:10px;color:{my_info["color"]}99;font-weight:700;text-transform:uppercase;letter-spacing:.1em'>MY FRANCHISE</div>
        <div style='font-size:26px;font-weight:900;color:{my_info["color"]}'>{my_abbr}</div>
        <div style='font-size:13px;color:#64748b'>{my_info["full"]}</div>
      </div>
      <div style='flex:1'>
        <div style='background:#1e1e3a;border-radius:6px;height:10px;overflow:hidden'>
          <div style='background:linear-gradient(90deg,#22c55e,#f59e0b {min(pct2*200,100):.0f}%,#ef4444);
          width:{pct2*100:.1f}%;height:100%'></div>
        </div>
        <div style='display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-top:3px'>
          <span>₹{my_team.spent}L spent</span><span>₹{my_team.budget}L left</span>
        </div>
      </div>
      <div style='text-align:right'>
        <div style='font-size:11px;color:#64748b'>Top-16 Points</div>
        <div style='font-size:36px;font-weight:900;color:#22c55e'>{my_team.top16_pts()}</div>
      </div>
    </div>
    </div>""", unsafe_allow_html=True)

    mc = st.columns(6)
    mvs = [("Players",f"{len(my_team.squad)}/{MAX_PLAYERS}","#60A5FA"),
           ("Overseas",f"{my_team.overseas_count()}/7","#F472B6"),
           ("WK",f"{rc.get('WICKETKEEPER',0)}/2","#FBBF24"),
           ("Batsmen",f"{rc.get('BATSMAN',0)}/3","#60A5FA"),
           ("All-Rounders",f"{rc.get('ALL-ROUNDER',0)}/3","#34D399"),
           ("Bowlers",f"{rc.get('BOWLER',0)}/4","#F87171")]
    for col,(lb,v,c) in zip(mc,mvs):
        with col:
            st.markdown(f"<div class='mc'><div class='mv' style='color:{c}'>{v}</div><div class='ml'>{lb}</div></div>",unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if ndd:
        st.markdown(f"""<div style='background:#450a0a;border:1px solid #ef444466;border-radius:10px;
        padding:11px 15px;color:#fca5a5;font-weight:600;margin-bottom:10px'>
        ⚠️ Must still buy: {" · ".join(f"{v}× {k}" for k,v in ndd.items())}</div>""",unsafe_allow_html=True)
    else:
        st.markdown("""<div style='background:#052e16;border:1px solid #22c55e66;border-radius:10px;
        padding:11px 15px;color:#bbf7d0;font-weight:600;margin-bottom:10px'>
        ✅ All mandatory role requirements satisfied!</div>""",unsafe_allow_html=True)

    if my_team.squad:
        df = pd.DataFrame(my_team.squad)[["name","role","country","pts","price_paid"]].rename(
            columns={"name":"Player","role":"Role","country":"Country","pts":"Pts","price_paid":"Paid (₹L)"}
        ).sort_values("Pts",ascending=False).reset_index(drop=True)
        df.index += 1
        st.dataframe(df, use_container_width=True,
                     column_config={"Pts":st.column_config.ProgressColumn("Pts",min_value=0,max_value=50,format="%d"),
                                    "Paid (₹L)":st.column_config.NumberColumn("Paid (₹L)",format="₹%d L")})
    else:
        st.info("No players yet. Record purchases in the sidebar.")

    st.markdown("<div class='sh'>🌟 BEST PLAYING XI — FINALS OPTIMIZER</div>", unsafe_allow_html=True)
    if len(my_team.squad) >= 11:
        xi, xi_pts = best_xi(my_team.squad)
        if xi:
            st.markdown(f"""<div class='gc' style='text-align:center;border-color:#22c55e44'>
            <div style='font-size:12px;color:#64748b'>Optimal Playing XI Score</div>
            <div style='font-size:52px;font-weight:900;color:#22c55e'>{xi_pts}</div>
            <div style='font-size:13px;color:#64748b'>total points</div>
            </div>""", unsafe_allow_html=True)
            xdf = pd.DataFrame(xi)[["name","role","country","pts"]].rename(
                columns={"name":"Player","role":"Role","country":"Country","pts":"Points"}
            ).sort_values("Points",ascending=False)
            st.dataframe(xdf, use_container_width=True, hide_index=True,
                         column_config={"Points":st.column_config.ProgressColumn("Points",min_value=0,max_value=50,format="%d")})
    else:
        st.info(f"Need at least 11 players. You have {len(my_team.squad)}.")

# ── TAB 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("<div class='sh'>RECOMMENDED TARGETS</div>", unsafe_allow_html=True)
    cf1,cf2,cf3 = st.columns(3)
    with cf1: rf = st.multiselect("Role filter",["WICKETKEEPER","BATSMAN","ALL-ROUNDER","BOWLER"],key="tf_r")
    with cf2: mf = st.checkbox("Mandatory only",key="tf_m")
    with cf3: inf= st.checkbox("India only",key="tf_i")
    tgts = recommend_targets(my_team, rivals, PLAYERS, top_n=40)
    if rf:  tgts = [t for t in tgts if t["role"] in rf]
    if mf:  tgts = [t for t in tgts if t["mandatory"]]
    if inf: tgts = [t for t in tgts if t["country"]=="India"]
    for tg in tgts:
        rc3   = ROLE_COLORS.get(tg["role"],"#94A3B8")
        mb    = ("<span style='background:#450a0a;color:#fca5a5;padding:2px 8px;border-radius:20px;"
                 "font-size:11px;font-weight:700;margin-left:6px'>MUST</span>" if tg["mandatory"] else "")
        dw    = tg["demand"]*100
        st.markdown(f"""<div class='gc' style='padding:13px 16px;margin-bottom:7px'>
        <div style='display:flex;align-items:center;gap:12px'>
          <div style='background:{rc3}22;border:2px solid {rc3};border-radius:8px;
               padding:5px 10px;font-size:18px;font-weight:900;color:{rc3};min-width:40px;text-align:center'>{tg["pts"]}</div>
          <div style='flex:1'>
            <div style='display:flex;align-items:center'>
              <span style='font-size:15px;font-weight:700'>{tg["name"]}</span>{mb}
            </div>
            <div style='margin-top:4px;display:flex;gap:5px;flex-wrap:wrap'>
              <span style='background:{rc3}22;color:{rc3};padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600'>{tg["role"]}</span>
              <span style='background:#1e1e3a;color:#94a3b8;padding:2px 8px;border-radius:20px;font-size:11px'>{tg["country"]}</span>
            </div>
          </div>
          <div style='text-align:right;min-width:150px'>
            <div style='font-size:12px;color:#64748b'>Base · Est. Sale</div>
            <div style='font-size:15px;font-weight:700'>₹{tg["base"]}L · ₹{tg["est_price"]}L</div>
            <div style='display:flex;align-items:center;gap:6px;justify-content:flex-end;margin-top:4px'>
              <div style='background:#1e1e3a;border-radius:4px;height:5px;width:70px;overflow:hidden'>
                <div style='background:#f59e0b;width:{dw:.0f}%;height:100%'></div>
              </div>
              <span style='font-size:11px;color:#64748b'>demand {tg["demand"]:.2f}</span>
            </div>
          </div>
        </div>
        </div>""", unsafe_allow_html=True)

# ── TAB 4 ─────────────────────────────────────────────────────────────────────
with tab4:
    all_t  = [my_team]+rivals
    labels = [t.name for t in all_t]
    clrs   = [IPL_TEAMS[t.name]["color"] for t in all_t]

    c1,c2 = st.columns(2)
    with c1:
        fig = go.Figure(go.Bar(x=labels, y=[t.budget for t in all_t],
            marker_color=clrs, text=[f"₹{t.budget}L" for t in all_t], textposition="outside"))
        fig.add_hline(y=BUDGET*0.5,line_dash="dash",line_color="#64748b",
                      annotation_text="50% line",annotation_position="top right")
        fig.update_layout(title="💰 Remaining Budget",paper_bgcolor="#0d0d1f",
            plot_bgcolor="#0d0d1f",font_color="#e2e8f0",height=290,
            yaxis=dict(gridcolor="#1e1e3a"),margin=dict(t=50,b=20,l=20,r=20))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = go.Figure(go.Bar(x=labels, y=[t.top16_pts() for t in all_t],
            marker_color=clrs, text=[str(t.top16_pts()) for t in all_t], textposition="outside"))
        fig2.update_layout(title="⭐ Top-16 Points",paper_bgcolor="#0d0d1f",
            plot_bgcolor="#0d0d1f",font_color="#e2e8f0",height=290,
            yaxis=dict(gridcolor="#1e1e3a"),margin=dict(t=50,b=20,l=20,r=20))
        st.plotly_chart(fig2, use_container_width=True)

    # Budget vs Points scatter
    fig3 = go.Figure()
    for t in all_t:
        fig3.add_trace(go.Scatter(x=[t.budget],y=[t.top16_pts()],mode="markers+text",
            text=[t.name],textposition="top center",
            marker=dict(size=20,color=IPL_TEAMS[t.name]["color"],
                        line=dict(width=2,color="#0d0d1f")),name=t.name))
    fig3.update_layout(title="💡 Budget vs Points (best = top-right)",
        paper_bgcolor="#0d0d1f",plot_bgcolor="#0d0d1f",font_color="#e2e8f0",
        height=320,showlegend=False,
        xaxis=dict(title="Budget (₹L)",gridcolor="#1e1e3a"),
        yaxis=dict(title="Top-16 Pts",gridcolor="#1e1e3a"),
        margin=dict(t=50,b=30))
    st.plotly_chart(fig3, use_container_width=True)

    # Stacked role bar
    ro = ["WICKETKEEPER","BATSMAN","ALL-ROUNDER","BOWLER"]
    rc_map = {"WICKETKEEPER":"#FBBF24","BATSMAN":"#60A5FA","ALL-ROUNDER":"#34D399","BOWLER":"#F472B6"}
    fig4 = go.Figure()
    for role in ro:
        fig4.add_trace(go.Bar(name=role,x=labels,
            y=[t.role_count().get(role,0) for t in all_t],marker_color=rc_map[role]))
    fig4.update_layout(barmode="stack",title="🧱 Squad Composition",
        paper_bgcolor="#0d0d1f",plot_bgcolor="#0d0d1f",font_color="#e2e8f0",height=290,
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        margin=dict(t=50,b=20),yaxis=dict(gridcolor="#1e1e3a"))
    st.plotly_chart(fig4, use_container_width=True)

# ── TAB 5 — ALL TEAMS ─────────────────────────────────────────────────────────
with tab5:
    ROLE_COLORS_LOCAL = {"BATSMAN":"#60A5FA","BOWLER":"#F472B6","ALL-ROUNDER":"#34D399","WICKETKEEPER":"#FBBF24"}
    all_display = [my_team] + sorted(rivals, key=lambda x: x.top16_pts(), reverse=True)

    for t in all_display:
        is_mine = t.name == my_abbr
        info    = IPL_TEAMS[t.name]
        rc_t    = t.role_count()
        needs   = t.mandatory_roles_needed()
        bc      = color_balance(t.budget)
        bp      = t.budget / BUDGET

        need_html = "".join(
            f"<span style='background:#450a0a;color:#fca5a5;padding:2px 7px;"
            f"border-radius:20px;font-size:11px;font-weight:700;margin:2px'>⚠️{v}×{k[:3]}</span>"
            for k, v in needs.items()
        )
        mine_badge = (f"<span style='background:{info['color']}22;color:{info['color']};"
                      f"padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;"
                      f"margin-left:8px'>MY TEAM</span>" if is_mine else "")

        if t.squad:
            roster_rows = ""
            for p in sorted(t.squad, key=lambda x: -x["pts"]):
                rc_col = ROLE_COLORS_LOCAL.get(p["role"], "#94a3b8")
                flag = "🇮🇳" if p["country"] == "India" else "🌍"
                roster_rows += f"""
                <tr style='border-bottom:1px solid #1e1e3a33'>
                  <td style='padding:7px 10px;color:#e2e8f0;font-weight:600;font-size:13px'>{p["name"]}</td>
                  <td style='padding:7px 10px'>
                    <span style='background:{rc_col}22;color:{rc_col};padding:2px 8px;
                    border-radius:20px;font-size:11px;font-weight:600'>{p["role"][:3]}</span>
                  </td>
                  <td style='padding:7px 10px;text-align:center;font-size:12px;color:#64748b'>{flag} {p["country"]}</td>
                  <td style='padding:7px 10px;text-align:center'>
                    <span style='background:#1e1e3a;color:{rc_col};padding:2px 10px;
                    border-radius:20px;font-size:14px;font-weight:900'>{p["pts"]}</span>
                  </td>
                  <td style='padding:7px 10px;text-align:right;color:#64748b;font-size:12px'>₹{p["price_paid"]}L</td>
                </tr>"""
            roster_html = f"""
            <table style='width:100%;border-collapse:collapse'>
              <thead><tr style='border-bottom:1px solid #1e1e3a'>
                <th style='padding:5px 10px;text-align:left;font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em'>Player</th>
                <th style='padding:5px 10px;text-align:left;font-size:10px;color:#64748b;text-transform:uppercase'>Role</th>
                <th style='padding:5px 10px;text-align:center;font-size:10px;color:#64748b;text-transform:uppercase'>Country</th>
                <th style='padding:5px 10px;text-align:center;font-size:10px;color:#64748b;text-transform:uppercase'>Pts</th>
                <th style='padding:5px 10px;text-align:right;font-size:10px;color:#64748b;text-transform:uppercase'>Paid</th>
              </tr></thead>
              <tbody>{roster_rows}</tbody>
            </table>"""
        else:
            roster_html = "<div style='color:#64748b;font-size:13px;padding:16px;text-align:center'>No players yet</div>"

        border = f"2px solid {info['color']}88" if is_mine else f"1px solid {info['color']}33"
        st.markdown(f"""
        <div style='background:#0d0d1f;border:{border};border-left:5px solid {info["color"]};
             border-radius:14px;padding:16px 20px;margin-bottom:14px'>
          <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px'>
            <div>
              <div style='display:flex;align-items:center;gap:8px'>
                <span style='font-size:20px;font-weight:900;color:{info["color"]}'>{t.name}</span>{mine_badge}
              </div>
              <div style='font-size:12px;color:#64748b;margin-top:2px'>{info["full"]}</div>
            </div>
            <div style='text-align:right'>
              <div style='font-size:24px;font-weight:900;color:{bc}'>₹{t.budget}L</div>
              <div style='font-size:11px;color:#64748b'>left · ₹{t.spent}L spent</div>
            </div>
          </div>
          <div style='background:#1e1e3a;border-radius:6px;height:6px;margin-bottom:10px'>
            <div style='background:{bc};width:{bp*100:.1f}%;height:100%;border-radius:6px'></div>
          </div>
          <div style='display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:12px'>
            <span style='background:#1e1e3a;color:#94a3b8;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600'>👥 {len(t.squad)}/18</span>
            <span style='background:#1e1e3a;color:#94a3b8;padding:3px 10px;border-radius:20px;font-size:12px'>🌍 {t.overseas_count()}/7</span>
            <span style='background:#FBBF2422;color:#FBBF24;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600'>WK {rc_t.get("WICKETKEEPER",0)}</span>
            <span style='background:#60A5FA22;color:#60A5FA;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600'>BAT {rc_t.get("BATSMAN",0)}</span>
            <span style='background:#34D39922;color:#34D399;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600'>AR {rc_t.get("ALL-ROUNDER",0)}</span>
            <span style='background:#F472B622;color:#F472B6;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600'>BO {rc_t.get("BOWLER",0)}</span>
            <span style='background:#22c55e22;color:#22c55e;padding:3px 10px;border-radius:20px;font-size:13px;font-weight:800'>⭐ {t.top16_pts()} pts</span>
            {need_html}
          </div>
          <div style='background:#080810;border-radius:10px;overflow:hidden'>{roster_html}</div>
        </div>
        """, unsafe_allow_html=True)
