from engine.team import SQUAD_REQS, MAX_OVERSEAS

def estimate_sale_price(player_name, player_data, my_team, rival_teams):
    base    = player_data["base"]
    pts     = player_data["pts"]
    role    = player_data["role"]
    country = player_data["country"]
    need_count      = sum(1 for t in rival_teams if role in t.mandatory_roles_needed())
    rich_rivals     = sum(1 for t in rival_teams if t.budget > 800)
    overseas_rivals = sum(1 for t in rival_teams if country != "India" and t.overseas_count() < MAX_OVERSEAS - 1)
    demand      = min(1.0, need_count * 0.3 + rich_rivals * 0.1 + overseas_rivals * 0.05)
    pts_premium = 1.0 + (pts - 38) * 0.12
    estimated   = max(base, int(base * pts_premium * (1 + demand * 0.5)))
    return estimated, round(demand, 2)

def compute_max_bid(player_name, player_data, my_team, rival_teams):
    pts     = player_data["pts"]
    role    = player_data["role"]
    country = player_data["country"]
    base    = player_data["base"]
    slots   = my_team.slots_remaining()

    if slots == 0 or (country != "India" and my_team.overseas_count() >= MAX_OVERSEAS):
        return 0

    needed = my_team.mandatory_roles_needed()

    # Step 1 — Reserve budget for mandatory roles still unfilled (excluding current)
    other_needed = {r: v for r, v in needed.items() if r != role}
    mandatory_reserve = sum(other_needed.values()) * 150  # min 150L per mandatory slot

    # Step 2 — Reserve budget for remaining free slots at floor price
    mandatory_slots = sum(other_needed.values())
    free_slots      = max(slots - 1 - mandatory_slots, 0)
    floor_reserve   = free_slots * 100  # 100L minimum per leftover slot

    total_reserve   = mandatory_reserve + floor_reserve
    free_budget     = max(my_team.budget - total_reserve, 0)

    # Step 3 — Urgency & quality premium
    urgency    = 1.5 if role in needed else 1.0
    pts_factor = pts / 42.0

    # Step 4 — Budget-based ceiling (max 50% of free budget on one player)
    budget_max = int(free_budget * 0.50 * urgency * pts_factor)

    # Step 5 — Get estimated sale price to cap sensibly
    est_price, _ = estimate_sale_price(player_name, player_data, my_team, rival_teams)

    # Step 6 — Never recommend paying more than 1.5× estimated sale price
    market_cap = int(est_price * 1.5)

    # Step 7 — Check richest rival — no point overbidding if no one can chase
    max_rival_budget = max((t.budget for t in rival_teams), default=0)
    rival_cap = int(max_rival_budget * 0.6)  # rivals can't bid beyond 60% of their budget

    max_bid = min(budget_max, market_cap, rival_cap)
    max_bid = max(max_bid, base)  # never below base price

    return max_bid
