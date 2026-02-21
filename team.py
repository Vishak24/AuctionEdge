BUDGET       = 7000
MAX_PLAYERS  = 18
MIN_PLAYERS  = 16
MAX_OVERSEAS = 7
SQUAD_REQS   = {"WICKETKEEPER": 2, "BATSMAN": 3, "ALL-ROUNDER": 3, "BOWLER": 4}

class Team:
    def __init__(self, name, budget=BUDGET):
        self.name   = name
        self.budget = budget
        self.squad  = []
        self.spent  = 0

    def add_player(self, player_name, player_data, price):
        p = player_data.copy()
        p["name"]       = player_name
        p["price_paid"] = price
        self.squad.append(p)
        self.budget -= price
        self.spent  += price

    def remove_last(self):
        if self.squad:
            p = self.squad.pop()
            self.budget += p["price_paid"]
            self.spent  -= p["price_paid"]

    def overseas_count(self):
        return sum(1 for p in self.squad if p["country"] != "India")

    def role_count(self):
        rc = {"WICKETKEEPER": 0, "BATSMAN": 0, "ALL-ROUNDER": 0, "BOWLER": 0}
        for p in self.squad:
            rc[p["role"]] = rc.get(p["role"], 0) + 1
        return rc

    def top16_pts(self):
        pts = sorted([p["pts"] for p in self.squad], reverse=True)
        return sum(pts[:16])

    def slots_remaining(self):
        return MAX_PLAYERS - len(self.squad)

    def mandatory_roles_needed(self):
        rc = self.role_count()
        return {role: req - rc.get(role, 0)
                for role, req in SQUAD_REQS.items()
                if req - rc.get(role, 0) > 0}

    def to_dict(self):
        return {"name": self.name, "budget": self.budget,
                "spent": self.spent, "squad": self.squad}
