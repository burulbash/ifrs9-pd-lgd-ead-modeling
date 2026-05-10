DROP TABLE IF EXISTS mart.financial_ratios_mart;

CREATE TABLE mart.financial_ratios_mart AS
WITH facility_base AS (
    SELECT
        lf.facility_id,
        lf.company_id,
        lf.origination_date AS observation_date,
        lf.maturity_date,
        lf.product_type,
        lf.limit_amount,
        lf.outstanding_amount,
        lf.undrawn_amount,
        lf.interest_rate,
        lf.term_months,
        lf.revolving_flag,
        lf.seniority,
        lf.currency,
        lf.repayment_type,

        c.registration_date,
        c.industry,
        c.region,
        c.company_size,
        c.legal_form,
        c.ownership_type,
        c.latent_profile,
        c.years_in_business,
        c.employees_count,
        c.exporter_flag,
        c.state_related_flag,
        c.related_party_flag
    FROM raw.loan_facilities lf
    LEFT JOIN raw.companies c
        ON lf.company_id = c.company_id
),

latest_financials AS (
    SELECT
        fb.facility_id,
        fs.report_date,
        fs.revenue,
        fs.revenue_prev_year,
        fs.ebitda,
        fs.net_income,
        fs.total_assets,
        fs.current_assets,
        fs.cash,
        fs.inventory,
        fs.accounts_receivable,
        fs.total_liabilities,
        fs.current_liabilities,
        fs.short_term_debt,
        fs.long_term_debt,
        fs.equity,
        fs.interest_expense,
        fs.operating_cash_flow,
        fs.capex
    FROM facility_base fb
    LEFT JOIN LATERAL (
        SELECT fs_inner.*
        FROM raw.financial_statements fs_inner
        WHERE fs_inner.company_id = fb.company_id
          AND fs_inner.report_date <= fb.observation_date
        ORDER BY fs_inner.report_date DESC
        LIMIT 1
    ) fs ON TRUE
),

latest_rating AS (
    SELECT
        fb.facility_id,
        rh.rating_date,
        rh.rating_grade AS origination_rating_grade,
        rh.pd_estimate AS origination_pd_estimate,
        rh.watchlist_flag,
        rh.restructuring_flag
    FROM facility_base fb
    LEFT JOIN LATERAL (
        SELECT rh_inner.*
        FROM raw.rating_history rh_inner
        WHERE rh_inner.company_id = fb.company_id
          AND rh_inner.rating_date <= fb.observation_date
        ORDER BY rh_inner.rating_date DESC
        LIMIT 1
    ) rh ON TRUE
),

collateral_agg AS (
    SELECT
        facility_id,
        MAX(collateral_type) AS collateral_type,
        SUM(collateral_value) AS collateral_value,
        AVG(haircut) AS avg_collateral_haircut,
        SUM(collateral_value * (1 - haircut)) AS effective_collateral_value
    FROM raw.collateral
    GROUP BY facility_id
),

payment_agg AS (
    SELECT
        fb.facility_id,
        MAX(p.days_past_due) AS max_dpd_observed,
        MAX(
            CASE
                WHEN p.payment_date <= fb.observation_date + INTERVAL '12 months'
                THEN p.days_past_due
                ELSE NULL
            END
        ) AS max_dpd_12m,
        COUNT(*) AS payment_months_observed,
        SUM(p.scheduled_amount) AS total_scheduled_amount,
        SUM(p.paid_amount) AS total_paid_amount
    FROM facility_base fb
    LEFT JOIN raw.payments p
        ON fb.facility_id = p.facility_id
    GROUP BY fb.facility_id
),

default_flags AS (
    SELECT
        fb.facility_id,
        d.default_date,
        d.default_type,
        d.dpd_at_default,
        d.ead_at_default,
        d.writeoff_flag,
        CASE
            WHEN d.default_date IS NOT NULL
             AND d.default_date <= fb.observation_date + INTERVAL '12 months'
            THEN 1
            ELSE 0
        END AS target_default_12m
    FROM facility_base fb
    LEFT JOIN raw.defaults d
        ON fb.facility_id = d.facility_id
),

recovery_agg AS (
    SELECT
        facility_id,
        SUM(recovery_amount) AS total_recovery_amount,
        SUM(collection_cost) AS total_collection_cost,
        COUNT(*) AS recovery_events_count
    FROM raw.recoveries
    GROUP BY facility_id
)

SELECT
    fb.facility_id,
    fb.company_id,
    fb.observation_date,
    fb.maturity_date,
    fb.product_type,
    fb.limit_amount,
    fb.outstanding_amount,
    fb.undrawn_amount,
    fb.interest_rate,
    fb.term_months,
    fb.revolving_flag,
    fb.seniority,
    fb.currency,
    fb.repayment_type,

    fb.registration_date,
    fb.industry,
    fb.region,
    fb.company_size,
    fb.legal_form,
    fb.ownership_type,
    fb.latent_profile,
    fb.years_in_business,
    fb.employees_count,
    fb.exporter_flag,
    fb.state_related_flag,
    fb.related_party_flag,

    lf.report_date,
    lf.revenue,
    lf.revenue_prev_year,
    lf.ebitda,
    lf.net_income,
    lf.total_assets,
    lf.current_assets,
    lf.cash,
    lf.inventory,
    lf.accounts_receivable,
    lf.total_liabilities,
    lf.current_liabilities,
    lf.short_term_debt,
    lf.long_term_debt,
    lf.equity,
    lf.interest_expense,
    lf.operating_cash_flow,
    lf.capex,

    COALESCE(lf.short_term_debt, 0) + COALESCE(lf.long_term_debt, 0) AS total_debt,

    lf.current_assets / NULLIF(lf.current_liabilities, 0) AS current_ratio,
    (lf.current_assets - COALESCE(lf.inventory, 0)) / NULLIF(lf.current_liabilities, 0) AS quick_ratio,
    (COALESCE(lf.short_term_debt, 0) + COALESCE(lf.long_term_debt, 0)) / NULLIF(lf.equity, 0) AS debt_to_equity,
    (COALESCE(lf.short_term_debt, 0) + COALESCE(lf.long_term_debt, 0)) / NULLIF(lf.total_assets, 0) AS debt_to_assets,
    (COALESCE(lf.short_term_debt, 0) + COALESCE(lf.long_term_debt, 0)) / NULLIF(lf.ebitda, 0) AS debt_to_ebitda,
    lf.ebitda / NULLIF(lf.interest_expense, 0) AS interest_coverage,
    lf.ebitda / NULLIF(lf.revenue, 0) AS ebitda_margin,
    lf.net_income / NULLIF(lf.revenue, 0) AS net_profit_margin,
    lf.operating_cash_flow / NULLIF((COALESCE(lf.short_term_debt, 0) + COALESCE(lf.long_term_debt, 0)), 0) AS operating_cf_to_debt,
    lf.cash / NULLIF(lf.short_term_debt, 0) AS cash_to_short_term_debt,
    lf.equity / NULLIF(lf.total_assets, 0) AS equity_to_assets,
    (lf.revenue - lf.revenue_prev_year) / NULLIF(lf.revenue_prev_year, 0) AS revenue_growth_yoy,

    ca.collateral_type,
    ca.collateral_value,
    ca.avg_collateral_haircut,
    ca.effective_collateral_value,
    fb.outstanding_amount / NULLIF(ca.collateral_value, 0) AS loan_to_value,
    ca.collateral_value / NULLIF(fb.outstanding_amount, 0) AS collateral_coverage,
    ca.effective_collateral_value / NULLIF(fb.outstanding_amount, 0) AS effective_collateral_coverage,

    lr.rating_date,
    lr.origination_rating_grade,
    lr.origination_pd_estimate,
    lr.watchlist_flag,
    lr.restructuring_flag,

    pa.max_dpd_observed,
    pa.max_dpd_12m,
    pa.payment_months_observed,
    pa.total_scheduled_amount,
    pa.total_paid_amount,
    pa.total_paid_amount / NULLIF(pa.total_scheduled_amount, 0) AS payment_completion_rate,

    df.default_date,
    df.default_type,
    df.dpd_at_default,
    df.ead_at_default,
    df.writeoff_flag,
    COALESCE(df.target_default_12m, 0) AS target_default_12m,

    ra.total_recovery_amount,
    ra.total_collection_cost,
    ra.recovery_events_count,

    CASE
        WHEN df.ead_at_default > 0
        THEN 1 - COALESCE(ra.total_recovery_amount, 0) / df.ead_at_default
        ELSE NULL
    END AS realized_lgd,

    CASE
        WHEN fb.revolving_flag = 1 AND fb.undrawn_amount > 0 AND df.ead_at_default IS NOT NULL
        THEN (df.ead_at_default - fb.outstanding_amount) / NULLIF(fb.undrawn_amount, 0)
        ELSE NULL
    END AS realized_ccf

FROM facility_base fb
LEFT JOIN latest_financials lf
    ON fb.facility_id = lf.facility_id
LEFT JOIN latest_rating lr
    ON fb.facility_id = lr.facility_id
LEFT JOIN collateral_agg ca
    ON fb.facility_id = ca.facility_id
LEFT JOIN payment_agg pa
    ON fb.facility_id = pa.facility_id
LEFT JOIN default_flags df
    ON fb.facility_id = df.facility_id
LEFT JOIN recovery_agg ra
    ON fb.facility_id = ra.facility_id;

CREATE INDEX IF NOT EXISTS idx_financial_ratios_mart_facility
    ON mart.financial_ratios_mart (facility_id);

CREATE INDEX IF NOT EXISTS idx_financial_ratios_mart_company
    ON mart.financial_ratios_mart (company_id);

CREATE INDEX IF NOT EXISTS idx_financial_ratios_mart_observation_date
    ON mart.financial_ratios_mart (observation_date);
