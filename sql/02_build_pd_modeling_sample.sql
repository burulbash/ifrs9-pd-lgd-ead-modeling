DROP TABLE IF EXISTS mart.pd_modeling_sample;

CREATE TABLE mart.pd_modeling_sample AS
SELECT
    facility_id,
    company_id,
    observation_date,

    target_default_12m,

    product_type,
    limit_amount,
    outstanding_amount,
    undrawn_amount,
    interest_rate,
    term_months,
    revolving_flag,
    seniority,
    currency,
    repayment_type,

    industry,
    region,
    company_size,
    legal_form,
    ownership_type,
    years_in_business,
    employees_count,
    exporter_flag,
    state_related_flag,
    related_party_flag,

    revenue,
    revenue_prev_year,
    ebitda,
    net_income,
    total_assets,
    current_assets,
    cash,
    inventory,
    accounts_receivable,
    total_liabilities,
    current_liabilities,
    short_term_debt,
    long_term_debt,
    equity,
    interest_expense,
    operating_cash_flow,
    capex,

    total_debt,
    current_ratio,
    quick_ratio,
    debt_to_equity,
    debt_to_assets,
    debt_to_ebitda,
    interest_coverage,
    ebitda_margin,
    net_profit_margin,
    operating_cf_to_debt,
    cash_to_short_term_debt,
    equity_to_assets,
    revenue_growth_yoy,

    collateral_type,
    collateral_value,
    avg_collateral_haircut,
    effective_collateral_value,
    loan_to_value,
    collateral_coverage,
    effective_collateral_coverage,

    watchlist_flag,
    restructuring_flag

FROM mart.financial_ratios_mart
WHERE target_default_12m IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pd_modeling_sample_facility
    ON mart.pd_modeling_sample (facility_id);

CREATE INDEX IF NOT EXISTS idx_pd_modeling_sample_observation_date
    ON mart.pd_modeling_sample (observation_date);

CREATE INDEX IF NOT EXISTS idx_pd_modeling_sample_target
    ON mart.pd_modeling_sample (target_default_12m);
