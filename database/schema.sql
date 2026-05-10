DROP SCHEMA IF EXISTS mart CASCADE;
DROP SCHEMA IF EXISTS raw CASCADE;

CREATE SCHEMA raw;
CREATE SCHEMA mart;

CREATE TABLE raw.companies (
    company_id TEXT PRIMARY KEY,
    registration_date DATE NOT NULL,
    industry TEXT NOT NULL,
    region TEXT NOT NULL,
    company_size TEXT NOT NULL,
    legal_form TEXT NOT NULL,
    ownership_type TEXT NOT NULL,
    latent_profile TEXT NOT NULL,
    years_in_business NUMERIC,
    employees_count INTEGER,
    exporter_flag INTEGER,
    state_related_flag INTEGER,
    related_party_flag INTEGER
);

CREATE TABLE raw.financial_statements (
    company_id TEXT NOT NULL,
    report_date DATE NOT NULL,
    revenue NUMERIC,
    revenue_prev_year NUMERIC,
    ebitda NUMERIC,
    net_income NUMERIC,
    total_assets NUMERIC,
    current_assets NUMERIC,
    cash NUMERIC,
    inventory NUMERIC,
    accounts_receivable NUMERIC,
    total_liabilities NUMERIC,
    current_liabilities NUMERIC,
    short_term_debt NUMERIC,
    long_term_debt NUMERIC,
    equity NUMERIC,
    interest_expense NUMERIC,
    operating_cash_flow NUMERIC,
    capex NUMERIC
);

CREATE TABLE raw.loan_facilities (
    facility_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    origination_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    product_type TEXT NOT NULL,
    limit_amount NUMERIC,
    outstanding_amount NUMERIC,
    undrawn_amount NUMERIC,
    interest_rate NUMERIC,
    term_months INTEGER,
    revolving_flag INTEGER,
    seniority TEXT,
    currency TEXT,
    repayment_type TEXT
);

CREATE TABLE raw.collateral (
    collateral_id TEXT PRIMARY KEY,
    facility_id TEXT NOT NULL,
    collateral_type TEXT,
    collateral_value NUMERIC,
    haircut NUMERIC,
    valuation_date DATE
);

CREATE TABLE raw.payments (
    payment_id TEXT PRIMARY KEY,
    facility_id TEXT NOT NULL,
    payment_date DATE NOT NULL,
    scheduled_amount NUMERIC,
    paid_amount NUMERIC,
    days_past_due INTEGER,
    outstanding_balance NUMERIC
);

CREATE TABLE raw.defaults (
    facility_id TEXT PRIMARY KEY,
    default_date DATE NOT NULL,
    default_type TEXT,
    dpd_at_default INTEGER,
    ead_at_default NUMERIC,
    writeoff_flag INTEGER
);

CREATE TABLE raw.recoveries (
    recovery_id TEXT PRIMARY KEY,
    facility_id TEXT NOT NULL,
    recovery_date DATE NOT NULL,
    recovery_amount NUMERIC,
    recovery_type TEXT,
    collection_cost NUMERIC
);

CREATE TABLE raw.rating_history (
    company_id TEXT NOT NULL,
    rating_date DATE NOT NULL,
    rating_grade TEXT,
    pd_estimate NUMERIC,
    watchlist_flag INTEGER,
    restructuring_flag INTEGER
);

CREATE TABLE raw.macro_scenarios (
    month DATE NOT NULL,
    scenario TEXT NOT NULL,
    scenario_weight NUMERIC,
    gdp_growth NUMERIC,
    inflation NUMERIC,
    base_rate NUMERIC,
    unemployment NUMERIC,
    fx_rate NUMERIC,
    industry_stress_index NUMERIC
);
