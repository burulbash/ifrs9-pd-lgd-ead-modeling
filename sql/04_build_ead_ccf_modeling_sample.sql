DROP TABLE IF EXISTS mart.ead_ccf_modeling_sample;

CREATE TABLE mart.ead_ccf_modeling_sample AS
WITH base AS (
    SELECT
        frm.facility_id,
        frm.company_id,
        frm.observation_date,
        frm.default_date,

        frm.product_type,
        frm.limit_amount,
        frm.outstanding_amount,
        frm.undrawn_amount,
        frm.outstanding_amount / NULLIF(frm.limit_amount, 0) AS utilization_rate,
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

        frm.revenue,
        frm.ebitda,
        frm.net_income,
        frm.total_assets,
        frm.current_assets,
        frm.cash,
        frm.inventory,
        frm.total_liabilities,
        frm.current_liabilities,
        frm.short_term_debt,
        frm.long_term_debt,
        frm.equity,
        frm.interest_expense,
        frm.operating_cash_flow,
        frm.capex,

        frm.total_debt,
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
        frm.avg_collateral_haircut,
        frm.effective_collateral_value,
        frm.loan_to_value,
        frm.collateral_coverage,
        frm.effective_collateral_coverage,

        frm.origination_rating_grade,
        frm.origination_pd_estimate,
        frm.watchlist_flag,
        frm.restructuring_flag,

        frm.default_type,
        frm.dpd_at_default,
        frm.ead_at_default,
        frm.writeoff_flag,

        ms.gdp_growth,
        ms.inflation,
        ms.base_rate,
        ms.unemployment,
        ms.fx_rate,
        ms.industry_stress_index

    FROM mart.financial_ratios_mart frm
    LEFT JOIN raw.macro_scenarios ms
        ON DATE_TRUNC('month', frm.default_date)::date = ms.month
       AND ms.scenario = 'base'
    WHERE frm.default_date IS NOT NULL
      AND frm.revolving_flag = 1
      AND frm.undrawn_amount > 0
      AND frm.ead_at_default IS NOT NULL
)

SELECT
    *,
    LEAST(
        1.5,
        GREATEST(
            0.0,
            (ead_at_default - outstanding_amount) / NULLIF(undrawn_amount, 0)
        )
    ) AS realized_ccf
FROM base;

CREATE INDEX IF NOT EXISTS idx_ead_ccf_modeling_sample_facility
    ON mart.ead_ccf_modeling_sample (facility_id);

CREATE INDEX IF NOT EXISTS idx_ead_ccf_modeling_sample_default_date
    ON mart.ead_ccf_modeling_sample (default_date);

CREATE INDEX IF NOT EXISTS idx_ead_ccf_modeling_sample_product
    ON mart.ead_ccf_modeling_sample (product_type);
