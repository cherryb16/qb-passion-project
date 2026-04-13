-- =============================================================================
-- 10_build_sql.sql
-- QB Translation: Which college QB traits predict early NFL success?
-- STRAT 412 Passion Project
--
-- SQLite analytical queries.
-- Tables are created by the Python loader (10_build_sql.py).
--
-- To run queries interactively:
--   sqlite3 data/qb_analysis.db
--   sqlite> .read scripts/10_build_sql.sql
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Average composite NFL score by draft round
-- ---------------------------------------------------------------------------
SELECT
    draft_round,
    COUNT(*)                              AS n_qbs,
    ROUND(AVG(composite_nfl_score), 1)   AS avg_nfl_score,
    ROUND(MIN(composite_nfl_score), 1)   AS min_score,
    ROUND(MAX(composite_nfl_score), 1)   AS max_score
FROM composite_scores
GROUP BY draft_round
ORDER BY draft_round;

-- ---------------------------------------------------------------------------
-- 2. Top 10 QBs by composite NFL success score
-- ---------------------------------------------------------------------------
SELECT
    qb_name,
    draft_year,
    draft_round,
    ROUND(composite_nfl_score, 1)         AS nfl_score,
    ROUND(recruit_rating_scaled, 1)        AS recruit_rating,
    ROUND(recruit_bias, 1)                 AS recruit_bias
FROM composite_scores
ORDER BY composite_nfl_score DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- 3. Most overvalued QBs (high recruit rating, low NFL output)
-- ---------------------------------------------------------------------------
SELECT
    qb_name,
    draft_year,
    draft_round,
    ROUND(recruit_rating_scaled, 1)        AS recruit_rating,
    ROUND(composite_nfl_score, 1)          AS nfl_score,
    ROUND(recruit_bias, 1)                 AS recruit_bias
FROM composite_scores
WHERE recruit_bias IS NOT NULL
ORDER BY recruit_bias DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- 4. Most undervalued QBs (low recruit rating, high NFL output)
-- ---------------------------------------------------------------------------
SELECT
    qb_name,
    draft_year,
    draft_round,
    ROUND(recruit_rating_scaled, 1)        AS recruit_rating,
    ROUND(composite_nfl_score, 1)          AS nfl_score,
    ROUND(recruit_bias, 1)                 AS recruit_bias
FROM composite_scores
WHERE recruit_bias IS NOT NULL
ORDER BY recruit_bias ASC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- 5. Cluster summary: avg NFL score, completion %, PPA, rushing by archetype
-- ---------------------------------------------------------------------------
SELECT
    cluster_label,
    COUNT(*)                               AS n_qbs,
    ROUND(AVG(composite_nfl_score), 1)    AS avg_nfl_score,
    ROUND(AVG(col_cmp_pct), 1)            AS avg_col_cmp_pct,
    ROUND(AVG(col_ppa_pass), 3)           AS avg_col_ppa_pass,
    ROUND(AVG(col_rush_yds_per_att), 2)   AS avg_rush_yds_per_att,
    ROUND(AVG(recruit_rating_scaled), 1)  AS avg_recruit_rating
FROM qb_clusters
GROUP BY cluster_label
ORDER BY avg_nfl_score DESC;

-- ---------------------------------------------------------------------------
-- 6. College completion % vs NFL score (decile buckets)
-- ---------------------------------------------------------------------------
SELECT
    CASE
        WHEN col_cmp_pct < 58  THEN '< 58%'
        WHEN col_cmp_pct < 62  THEN '58-62%'
        WHEN col_cmp_pct < 65  THEN '62-65%'
        WHEN col_cmp_pct < 68  THEN '65-68%'
        ELSE '68%+'
    END                                    AS col_cmp_bucket,
    COUNT(*)                               AS n_qbs,
    ROUND(AVG(cs.composite_nfl_score), 1) AS avg_nfl_score
FROM model_table m
JOIN composite_scores cs ON m.qb_name = cs.qb_name
WHERE col_cmp_pct IS NOT NULL
GROUP BY col_cmp_bucket
ORDER BY col_cmp_bucket;

-- ---------------------------------------------------------------------------
-- 7. Average NFL score by conference (min 3 QBs)
-- ---------------------------------------------------------------------------
SELECT
    m.col_conference,
    COUNT(*)                               AS n_qbs,
    ROUND(AVG(cs.composite_nfl_score), 1) AS avg_nfl_score
FROM model_table m
JOIN composite_scores cs ON m.qb_name = cs.qb_name
WHERE m.col_conference IS NOT NULL
GROUP BY m.col_conference
HAVING COUNT(*) >= 3
ORDER BY avg_nfl_score DESC;

-- ---------------------------------------------------------------------------
-- 8. Round 1 busts: first-round picks scoring below 45
-- ---------------------------------------------------------------------------
SELECT
    qb_name,
    draft_year,
    draft_round,
    draft_pick,
    ROUND(composite_nfl_score, 1)          AS nfl_score,
    ROUND(recruit_rating_scaled, 1)        AS recruit_rating
FROM composite_scores
WHERE draft_round = 1
  AND composite_nfl_score < 45
ORDER BY composite_nfl_score ASC;

-- ---------------------------------------------------------------------------
-- 9. Late-round overachievers: rounds 3-7 scoring above cohort mean (58)
-- ---------------------------------------------------------------------------
SELECT
    qb_name,
    draft_year,
    draft_round,
    draft_pick,
    ROUND(composite_nfl_score, 1)          AS nfl_score,
    ROUND(recruit_rating_scaled, 1)        AS recruit_rating
FROM composite_scores
WHERE draft_round >= 3
  AND composite_nfl_score > 58
ORDER BY composite_nfl_score DESC;

-- ---------------------------------------------------------------------------
-- 10. College PPA vs NFL score (PPA quartile buckets)
-- ---------------------------------------------------------------------------
SELECT
    CASE
        WHEN col_ppa_overall < 0.2   THEN 'Q1: < 0.20'
        WHEN col_ppa_overall < 0.35  THEN 'Q2: 0.20-0.35'
        WHEN col_ppa_overall < 0.50  THEN 'Q3: 0.35-0.50'
        ELSE 'Q4: 0.50+'
    END                                    AS ppa_bucket,
    COUNT(*)                               AS n_qbs,
    ROUND(AVG(cs.composite_nfl_score), 1) AS avg_nfl_score
FROM model_table m
JOIN composite_scores cs ON m.qb_name = cs.qb_name
WHERE col_ppa_overall IS NOT NULL
GROUP BY ppa_bucket
ORDER BY ppa_bucket;
