# Checkpoint 3 — Making the Choice

## QB Translation: Which College QB Profiles Predict NFL Success?

### Question

Which college quarterback profiles predict NFL success, and does recruiting ranking introduce bias into how QBs are evaluated and drafted? If an NFL GM is evaluating QB prospects, which college archetypes consistently produce successful NFL starters — and are highly-recruited QBs being over- or under-valued?

---

### Type of Analysis

**Python:**
- Build a **composite NFL success score** per QB by normalizing and weighting: on-target % (2×), bad throw % inverted (2×), completion % (1.5×), ANY/A, passer rating, QBR, TD%, Int% inverted, pressure % inverted, and rushing yards per attempt (all 1×)
- Use **PCA + K-Means clustering** on college stats to identify QB archetypes (e.g., dual-threat, efficient pocket passer, high-volume arm)
- Build a **recruitment bias indicator**: compare each QB's 247Sports composite recruit rating against their NFL composite success score — positive bias = overvalued recruit, negative = undervalued (e.g., Josh Allen was unranked; Brock Purdy was a 3-star; both outperformed)
- Map each archetype to average composite success score to answer: which college QB type wins in the NFL?

**SQL:**
- Load the merged dataset into a relational database
- Write queries to aggregate and filter: success score by draft round, conference, star rating tier, QB archetype, and Power 5 vs. non-Power 5 school

**Tableau:**
- QB radar charts comparing college profile vs. NFL outcome
- Recruitment bias scatter plot: recruit rating vs. composite success score (labeled by name)
- Interactive dashboard filtering by draft year, round, conference, archetype, and star rating

---

### Type of Data

| Source | Data | Status |
|--------|------|--------|
| Pro Football Reference | NFL draft history 2008–2024 (198 QBs, narrowed to 40-QB cohort) | Done |
| Pro Football Reference | NFL advanced passing + rushing stats 2018–2025 | Done |
| College Football Data API (CFBD) | College stats: passing, rushing, PPA, usage, team win % | Done (39/40 QBs) |
| 247Sports (via CFBD) | Recruiting composite ratings, star rankings, national rank | Done (34/40 QBs) |
| Sportradar NCAAFB v7 | College sack data (supplemental) | Done (40/40 QBs) |

> **Note:** Josh Allen, Bailey Zappe, Desmond Ridder, Aidan O'Connell, Mason Rudolph, and Ryan Finley are missing recruiting data — small-school or pre-2015 recruits not tracked by 247Sports. Handled as missing/NaN in bias indicator.
