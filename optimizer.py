from engine.team import MAX_OVERSEAS, SQUAD_REQS
from engine.estimator import estimate_sale_price
from itertools import combinations

def get_available(all_teams, player_db):
    bought = {p["name"] for t in all_teams for p in t.squad}
    return {n: d for n, d in player_db.items() if n not in bought}

def recommend_targets(my_team, rival_teams, player_db, top_n=30):
    all_teams     = [my_team] + rival_teams
    available     = get_available(all_teams, player_db)
    needed        = my_team.mandatory_roles_needed()
    slots         = my_team.slots_remaining()
    overseas_left = MAX_OVERSEAS - my_team.overseas_count()
    targets = []
    for name, p in available.items():
        if p["country"] != "India" and overseas_left <= 0:
            continue
        est_price, demand = estimate_sale_price(name, p, my_team, rival_teams)
        role     = p["role"]
        priority = float(p["pts"])
        if role in needed: priority += 10
        if slots > 0 and est_price > my_team.budget / max(slots, 1) * 1.8: priority -= 5
        priority += p["pts"] / max(est_price / max(p["base"], 1), 1) * 0.5
        targets.append({"name": name, "role": p["role"], "country": p["country"],
                        "pts": p["pts"], "base": p["base"], "est_price": est_price,
                        "demand": demand, "priority": round(priority, 2),
                        "mandatory": role in needed})
    targets.sort(key=lambda x: (-int(x["mandatory"]), -x["priority"]))
    return targets[:top_n]

def best_xi(squad):
    reqs    = {"BOWLER": 3, "ALL-ROUNDER": 2, "WICKETKEEPER": 1, "BATSMAN": 3}
    players = sorted(squad, key=lambda x: -x["pts"])
    best, best_pts = None, 0
    for combo in combinations(players, 11):
        rc      = {}
        overseas = 0
        for p in combo:
            rc[p["role"]] = rc.get(p["role"], 0) + 1
            if p["country"] != "India": overseas += 1
        if overseas > 5: continue
        if all(rc.get(r, 0) >= req for r, req in reqs.items()):
            total = sum(p["pts"] for p in combo)
            if total > best_pts:
                best_pts = total
                best     = list(combo)
    return best, best_pts
