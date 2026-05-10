CREATE INDEX IF NOT EXISTS idx_financial_statements_company_date
    ON raw.financial_statements (company_id, report_date);

CREATE INDEX IF NOT EXISTS idx_loan_facilities_company_date
    ON raw.loan_facilities (company_id, origination_date);

CREATE INDEX IF NOT EXISTS idx_collateral_facility
    ON raw.collateral (facility_id);

CREATE INDEX IF NOT EXISTS idx_payments_facility_date
    ON raw.payments (facility_id, payment_date);

CREATE INDEX IF NOT EXISTS idx_defaults_facility_date
    ON raw.defaults (facility_id, default_date);

CREATE INDEX IF NOT EXISTS idx_recoveries_facility_date
    ON raw.recoveries (facility_id, recovery_date);

CREATE INDEX IF NOT EXISTS idx_rating_history_company_date
    ON raw.rating_history (company_id, rating_date);

CREATE INDEX IF NOT EXISTS idx_macro_scenarios_month_scenario
    ON raw.macro_scenarios (month, scenario);
