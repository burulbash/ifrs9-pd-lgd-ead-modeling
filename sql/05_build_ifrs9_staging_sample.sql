DROP TABLE IF EXISTS mart.ifrs9_staging_sample;

CREATE TABLE mart.ifrs9_staging_sample AS
WITH current_rating AS (
    SELECT DISTINCT ON (company_id)
        company_id,
        rating_date AS current_rating_date,
        rating_grade AS current_rating_grade,
        pd_estimate AS current_pd_estimate,
        watchlist_flag AS current_watchlist_flag,
        restructuring_flag AS current_restructuring_flag
    FROM raw.rating_history
    WHERE rating_date <= DATE '2025-12-31'
    ORDER BY company_id, rating_date DESC
),

latest_payment AS (
    SELECT DISTINCT ON (facility_id)
        facility_id,
        payment_date AS latest_payment_date,
        days_past_due AS current_dpd,
        outstanding_balance AS current_outstanding_balance
    FROM raw.payments
    WHERE payment_date <= DATE '2025-12-31'
    ORDER BY facility_id, payment_date DESC
),

rating_orders AS (
    SELECT *
    FROM (
        VALUES
            ('A', 1),
            ('B', 2),
            ('C', 3),
            ('D', 4),
            ('E', 5),
            ('F', 6),
            ('Default', 7)
    ) AS t(rating_grade, rating_order)
)

SELECT
    frm.facility_id,
    frm.company_id,
    DATE '2025-12-31' AS reporting_date,
    frm.observation_date,
    frm.maturity_date,

    frm.product_type,
    frm.limit_amount,
    frm.outstanding_amount,
    frm.undrawn_amount,
    frm.interest_rate,
    frm.term_months,
    frm.revolving_flag,
    frm.seniority,
    frm.currency,
    frm.repayment_type,

    frm.industry,
    frm.region,
    frm.company_size,
    frm.legal_form,
    frm.ownership_type,
    frm.years_in_business,
    frm.employees_count,
    frm.exporter_flag,
    frm.state_related_flag,
    frm.related_party_flag,

    frm.current_ratio,
    frm.quick_ratio,
    frm.debt_to_equity,
    frm.debt_to_assets,
    frm.debt_to_ebitda,
    frm.interest_coverage,
    frm.ebitda_margin,
    frm.net_profit_margin,
    frm.operating_cf_to_debt,
    frm.cash_to_short_term_debt,
    frm.equity_to_assets,
    frm.revenue_growth_yoy,

    frm.collateral_type,
    frm.collateral_value,
    frm.effective_collateral_value,
    frm.collateral_coverage,
    frm.effective_collateral_coverage,

    frm.origination_rating_grade,
    ro.rating_order AS origination_rating_order,
    frm.origination_pd_estimate,

    cr.current_rating_date,
    cr.current_rating_grade,
    rc.rating_order AS current_rating_order,
    cr.current_pd_estimate,

    lp.latest_payment_date,
    COALESCE(lp.current_dpd, 0) AS current_dpd,
    COALESCE(lp.current_outstanding_balance, frm.outstanding_amount) AS current_outstanding_balance,

    COALESCE(cr.current_watchlist_flag, frm.watchlist_flag, 0) AS watchlist_flag,
    COALESCE(cr.current_restructuring_flag, frm.restructuring_flag, 0) AS restructuring_flag,

    frm.max_dpd_observed,
    frm.max_dpd_12m,
    frm.default_date,
    frm.default_type,
    frm.dpd_at_default,
    frm.writeoff_flag,

    CASE
        WHEN frm.default_date IS NOT NULL
          OR COALESCE(frm.writeoff_flag, 0) = 1
          OR COALESCE(frm.dpd_at_default, 0) >= 90
          OR COALESCE(lp.current_dpd, 0) >= 90
        THEN 1
        ELSE 0
    END AS default_flag,

    CASE
        WHEN frm.origination_pd_estimate > 0 AND cr.current_pd_estimate IS NOT NULL
        THEN cr.current_pd_estimate / frm.origination_pd_estimate
        ELSE NULL
    END AS pd_ratio_current_to_origination,

    CASE
        WHEN ro.rating_order IS NOT NULL AND rc.rating_order IS NOT NULL
        THEN rc.rating_order - ro.rating_order
        ELSE NULL
    END AS rating_downgrade_notches,

    frm.target_default_12m

FROM mart.financial_ratios_mart frm
LEFT JOIN current_rating cr
    ON frm.company_id = cr.company_id
LEFT JOIN latest_payment lp
    ON frm.facility_id = lp.facility_id
LEFT JOIN rating_orders ro
    ON frm.origination_rating_grade = ro.rating_grade
LEFT JOIN rating_orders rc
    ON cr.current_rating_grade = rc.rating_grade;

CREATE INDEX IF NOT EXISTS idx_ifrs9_staging_sample_facility
    ON mart.ifrs9_staging_sample (facility_id);

CREATE INDEX IF NOT EXISTS idx_ifrs9_staging_sample_company
    ON mart.ifrs9_staging_sample (company_id);

CREATE INDEX IF NOT EXISTS idx_ifrs9_staging_sample_reporting_date
    ON mart.ifrs9_staging_sample (reporting_date);
