-- Independent cross-check of results/*.csv using SQLite's own CSV parser.
-- Run from the repo root:  sqlite3 :memory: < scripts/crosscheck.sql
-- Integer totals must match exactly; spend sums as doubles, so compare within 0.01.

.mode csv
.import --csv data/ad_data.csv ad
.headers on

CREATE TEMP VIEW totals AS
SELECT campaign_id,
       SUM(CAST(impressions AS INTEGER)) AS total_impressions,
       SUM(CAST(clicks AS INTEGER))      AS total_clicks,
       SUM(CAST(spend AS REAL))          AS total_spend,
       SUM(CAST(conversions AS INTEGER)) AS total_conversions
FROM ad
GROUP BY campaign_id;

.print -- top10_ctr (highest CTR first, impressions > 0, ties by campaign_id)
SELECT campaign_id, total_impressions, total_clicks,
       printf('%.2f', total_spend) AS total_spend, total_conversions,
       printf('%.4f', 1.0 * total_clicks / total_impressions) AS CTR,
       CASE WHEN total_conversions > 0
            THEN printf('%.2f', total_spend / total_conversions) END AS CPA
FROM totals
WHERE total_impressions > 0
ORDER BY 1.0 * total_clicks / total_impressions DESC, campaign_id ASC
LIMIT 10;

.print -- top10_cpa (lowest CPA first, conversions > 0, ties by campaign_id)
SELECT campaign_id, total_impressions, total_clicks,
       printf('%.2f', total_spend) AS total_spend, total_conversions,
       CASE WHEN total_impressions > 0
            THEN printf('%.4f', 1.0 * total_clicks / total_impressions) END AS CTR,
       printf('%.2f', total_spend / total_conversions) AS CPA
FROM totals
WHERE total_conversions > 0
ORDER BY total_spend / total_conversions ASC, campaign_id ASC
LIMIT 10;

.print -- input rows and distinct campaigns
SELECT count(*) AS rows_read, count(DISTINCT campaign_id) AS campaigns FROM ad;
