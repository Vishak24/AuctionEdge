# 🏏 AuctionEdge

> Real-time AI co-pilot for IPL auctions — track 10 franchises live, get instant BID / SHILL / PASS decisions, and always know exactly how much to spend.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?style=flat-square&logo=streamlit)
![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75?style=flat-square&logo=plotly)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ✨ Features

- ⚡ **Live Advisor** — Select the player on the block, type the current bid, and get an instant AI decision: BID, SHILL, or PASS with a reason
- 💰 **Smart Max Bid Engine** — Computes exactly how far you can push based on your remaining budget, squad gaps, mandatory roles, and rival spending patterns
- 📊 **Spend Zone Analysis** — 3-zone bar (SAFE / CAUTION / DANGER) anchored to estimated market value, not raw budget math
- 👥 **Rival Watch** — Live cards for all 9 rival franchises showing balance, role counts, overseas slots, and automatic ⚠️ warnings for unfilled mandatory roles
- 🎯 **AI Target Recommender** — Ranked list of all remaining players by priority, urgency, and estimated sale price
- 📋 **My Squad Tracker** — Role composition, overseas count, budget progress, and a Best XI optimizer for Finals
- 📈 **Dashboard** — Budget comparison, points leaderboard, budget vs points scatter, and squad composition charts across all 10 teams
- 👥 **All Teams Tab** — Full roster breakdown for every franchise with player names, roles, points, and price paid

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
# Clone the repo
git clone https://github.com/Vishak24/AuctionEdge.git
cd AuctionEdge

# Create a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Open your browser at `http://localhost:8501`

---

## 📁 Project Structure

```
AuctionEdge/
├── app.py # Main Streamlit app
├── requirements.txt
└── engine/
├── __init__.py
├── players.py # Full player database (name, role, country, base, pts)
├── team.py # Team class, budget constants, squad logic
├── estimator.py # Market price estimator + smart max bid engine
├── decision.py # BID / SHILL / PASS decision engine
└── optimizer.py # Target recommender + Best XI optimizer
```

---

## 🧠 How the AI Works

### BID Decision
Triggers when the player is valuable, the role is needed, and the current bid is within the computed max bid — factoring in mandatory role reserves and rival pressure.

### SHILL Decision
Triggers when 2+ rivals desperately need the same role, you already have enough of that role, and the current bid is well below estimated sale price. You push the price up, then drop — draining rival budgets.

### PASS Decision
Triggers when the player is overpriced relative to your max bid, you've hit the overseas cap, or your budget reserves are too thin to risk it.

### Smart Max Bid Formula
```
free_budget = my_budget − mandatory_reserve − floor_reserve
budget_max = free_budget × 0.50 × urgency × (pts / 42)
max_bid = min(budget_max, 1.5 × est_price, 0.6 × richest_rival_budget)
```

---

## 🎮 How to Use During an Auction

```
1. Pick your franchise at startup
2. Auctioneer calls a player → select them in "Player on the Block"
3. Type the current bid as it rises → read the BIG decision banner
4. Whoever wins → Sidebar → Record Purchase (team + player + price)
5. Repeat. Check "Targets" tab between rounds for your next picks.
```

---

## 📦 Requirements

```
streamlit
pandas
plotly
```

---

## 🛠️ Built With

- [Streamlit](https://streamlit.io) — UI framework
- [Plotly](https://plotly.com) — Interactive charts
- [Pandas](https://pandas.pydata.org) — Data handling
- Custom AI decision engine — Pure Python

---

## 👨‍💻 Author

**Vishal Ganesan**
Electronics & Communication Engineering, SRM Institute of Science and Technology
[GitHub](https://github.com/Vishak24) · [LinkedIn](https://linkedin.com/in/vishalg24)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

> *Built in 48 hours for a live IPL mock auction. AuctionEdge was the only team with a real-time AI co-pilot.* 🏏🔥

