# Checkpoint 3 — Making the Choice

## QB Translation: Which College QB Profiles Predict NFL Success?

### Question

Which college quarterback profiles predict NFL success, and does recruiting ranking introduce bias into how QBs are evaluated and drafted? If an NFL GM is evaluating QB prospects, which college archetypes consistently produce successful NFL starters — and are highly-recruited QBs being over- or under-valued?

---

### Type of Analysis

**Python:**
- Build a **composite NFL success score** per QB by normalizing and weighting: on-target %, bad throw % (inverted), pressure % (inverted), pocket time, intended air yards per attempt, completion %, games started, and rushing yards per attempt
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
| Pro Football Reference | NFL draft history 2008–2023 (187 QBs, narrowed to 31-QB cohort) | Done |
| Pro Football Reference | NFL advanced passing + rushing stats 2009–2025 | Done |
| College Football Data API | College stats: passing, rushing, PPA, usage, explosiveness | Done |
| 247Sports | Recruiting composite ratings, star rankings, national rank, position type | Done (28/31 QBs) |

> **Note:** Josh Allen, Desmond Ridder, and Aidan O'Connell are missing recruiting data and will be handled as a special case in the bias indicator.
