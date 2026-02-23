from engine.team import SQUAD_REQS, MAX_OVERSEAS, MAX_PLAYERS
from engine.estimator import estimate_sale_price, compute_max_bid

def decide(player_name, player_data, current_bid, my_team, rival_teams):
    role    = player_data["role"]
    country = player_data["country"]
    pts     = player_data["pts"]
    if len(my_team.squad) >= MAX_PLAYERS:
        return _o("PASS", 0, "Squad full", 0, 0)
    if country != "India" and my_team.overseas_count() >= MAX_OVERSEAS:
        return _o("PASS", 0, "Overseas cap reached", 0, 0)
    if my_team.budget < current_bid:
        return _o("PASS", 0, "Insufficient budget", 0, 0)
    est_price, demand = estimate_sale_price(player_name, player_data, my_team, rival_teams)
    max_bid           = compute_max_bid(player_name, player_data, my_team, rival_teams)
    needed      = my_team.mandatory_roles_needed()
    role_count  = my_team.role_count().get(role, 0)
    role_excess = role_count >= SQUAD_REQS.get(role, 0) + 2
    reserve          = sum(needed.values()) * 150
    effective_budget = my_team.budget - reserve
    rival_needs = [t for t in rival_teams if role in t.mandatory_roles_needed()]
    shill_ok = (len(rival_needs) >= 2 and role_excess and
                current_bid < est_price * 0.65 and my_team.budget > 1500)
    if shill_ok:
        shill_max = min(int(est_price * 0.72), int(my_team.budget * 0.12))
        return _o("SHILL", shill_max,
                  f"{len(rival_needs)} rivals need {role} — drain them, drop at ₹{shill_max}L",
                  est_price, demand)
    is_needed   = role in needed
    is_valuable = pts >= 44
    if current_bid <= max_bid and effective_budget >= current_bid:
        if is_needed or is_valuable or (not role_excess and demand < 0.6):
            return _o("BID", max_bid,
                      f"pts={pts} | max=₹{max_bid}L | est=₹{est_price}L | demand={demand}",
                      est_price, demand)
    return _o("PASS", 0,
              f"Overpriced or not urgent | est=₹{est_price}L | max=₹{max_bid}L",
              est_price, demand)

def _o(action, max_pay, reason, est_price, demand):
    return {"action": action, "max_pay": max_pay, "reason": reason,
            "est_price": est_price, "demand": demand}
