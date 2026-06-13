
<div align="center">

<img src="https://img.shields.io/badge/AI-Expectiminimax-blue?style=for-the-badge&logo=robotframework" alt="AI Algorithm">
<img src="https://img.shields.io/badge/Python-3.x-green?style=for-the-badge&logo=python" alt="Python">
<img src="https://img.shields.io/badge/GUI-Dear%20PyGui-purple?style=for-the-badge" alt="Dear PyGui">
<img src="https://img.shields.io/badge/Genre-Strategy%20Game-red?style=for-the-badge&logo=battle.net" alt="Genre">

<br><br>

#  Grid Fight

### *Where AI Agents Battle for Territory*

A multi-agent stochastic battlefield simulation where three AI agents **Expert**, **Intermediate**, and **Novice**  compete for dominance using adversarial search algorithms in an uncertain, ever-changing environment.

<br>

</div>

---

##  Overview

GridFight is an implementation of **Expectiminimax with Alpha-Beta Pruning**, designed to simulate realistic multi-agent competition under uncertainty. Three agents with asymmetric cognitive capabilities battle on a 2D grid, facing probabilistic combat outcomes, environmental disasters, minefields, and limited resources.

---

##  The Three Agents

| Agent | Label | Depth | Vision | Evaluation | Behavior |
|-------|-------|-------|--------|------------|----------|
|  **Expert** | A | 7 | Full Board | 5 Factors | Strategic genius. Sees everything, plans ahead. |
|  **Intermediate** | B | 5 | 5 cell radius | 3 Factors | Balanced player. Good planning, limited info. |
|  **Novice** | C | 3 | 3 cell radius | Greedy | Short-sighted. Reacts to immediate gains only. |

---

##  Game Features

### Board Elements
- 🟫 **Empty Cells**:  Neutral territory
- 🟨 **Fortresses**:  3x score per round
- ⬛ **Obstacles**:  Impassable
- 🟧 **Minefields**:  Random outcomes

### Combat System
- 9-sided die with uneven probabilities
- Outcomes: Fail, Partial Success, Full Success, Critical Hit
- Defense values must reach zero to capture

### Stochastic Events
- 📦 **Supply Drop** -> Random fortress for 3 rounds
- 🌋 **Earthquake**  -> Cell loses defense
- 🔄 **Reinforcement** -> Extra unit for weakest agent
- 🌫️ **Fog of War** -> Vision halved

### Resources
- ⚡ **Energy**: 20 units, -1 per action
- 🛡️ **Defense**: Cells have 1–3 defense value

---

##  The Algorithm

MAX Node (Agent's Turn)

 Choose best action -> CHANCE Node (Die Roll) -> All 9 outcomes weighted -> MIN Node (Opponent's Turn) -> Choose worst for us -> Continue to depth limit

 
### Key Details

| Feature | Status |
|---------|--------|
| MAX/MIN Pruning | ✅ Alpha-Beta applied |
| Chance Pruning | ❌ All branches evaluated |
| Move Ordering | ✅ Better moves first |
| Node Limit | ✅ 15,000 per move |
| Transposition Table | ✅ For Expert agent |

### Evaluation Function (Expert)
1. **Score Differential**:   Direct winning metric
2. **Territory Control**:  Income potential
3. **Energy Advantage**: Future actions
4. **Positional Advantage**:  Proximity to valuables
5. **Threat Penalty**:  Defensive awareness

---

##  GUI

Built with **Dear PyGui**:
- 🗺️ Live board with color-coded cells
- 📊 Real-time agent stats panel
- 📜 Move log with node statistics
- 🎮 Step/Run controls with speed slider

---

##  Quick Start

```bash
pip install dearpygui
python source.py gui
python source.py console
python source.py stats
```
---

##  Files

```bash
Board.txt
Result.txt
Source.py
```
