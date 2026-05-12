DROP TABLE IF EXISTS mart.data_quality_summary;

CREATE TABLE mart.data_quality_summary AS
WITH quality_checks AS (

    -- Row counts: raw tables
    SELECT 'row_count' AS check_group, 'raw companies rows' AS check_name, 'raw.companies' AS table_name,
           'rows' AS metric_name, COUNT(*)::numeric AS metric_value, 1::numeric AS threshold_value,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END AS status,
           'Raw borrower table should not be empty.' AS details
    FROM raw.companies

    UNION ALL
    SELECT 'row_count', 'raw financial statements rows', 'raw.financial_statements',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
           'Raw financial statements table should not be empty.'
    FROM raw.financial_statements

    UNION ALL
    SELECT 'row_count', 'raw loan facilities rows', 'raw.loan_facilities',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
           'Raw loan facilities table should not be empty.'
    FROM raw.loan_facilities

    UNION ALL
    SELECT 'row_count', 'raw payments rows', 'raw.payments',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
           'Raw payments table should not be empty.'
    FROM raw.payments

    UNION ALL
    SELECT 'row_count', 'raw defaults rows', 'raw.defaults',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'WARN' END,
           'Defaults can be sparse, but the synthetic medium portfolio should contain default events.'
    FROM raw.defaults

    UNION ALL
    SELECT 'row_count', 'raw recoveries rows', 'raw.recoveries',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'WARN' END,
           'Recoveries should exist for part of the defaulted portfolio.'
    FROM raw.recoveries

    UNION ALL
    SELECT 'row_count', 'raw rating history rows', 'raw.rating_history',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
           'Rating history table should not be empty.'
    FROM raw.rating_history

    UNION ALL
    SELECT 'row_count', 'raw macro scenarios rows', 'raw.macro_scenarios',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
           'Macro scenarios table should not be empty.'
    FROM raw.macro_scenarios

    -- Row counts: marts
    UNION ALL
    SELECT 'row_count', 'financial ratios mart rows', 'mart.financial_ratios_mart',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
           'Financial ratios mart should not be empty.'
    FROM mart.financial_ratios_mart

    UNION ALL
    SELECT 'row_count', 'pd modeling sample rows', 'mart.pd_modeling_sample',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
           'PD modeling sample should not be empty.'
    FROM mart.pd_modeling_sample

    UNION ALL
    SELECT 'row_count', 'lgd modeling sample rows', 'mart.lgd_modeling_sample',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'WARN' END,
           'LGD sample contains defaulted facilities only.'
    FROM mart.lgd_modeling_sample

    UNION ALL
    SELECT 'row_count', 'ead ccf modeling sample rows', 'mart.ead_ccf_modeling_sample',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'WARN' END,
           'EAD/CCF sample contains revolving defaulted facilities only.'
    FROM mart.ead_ccf_modeling_sample

    UNION ALL
    SELECT 'row_count', 'ifrs9 staging sample rows', 'mart.ifrs9_staging_sample',
           'rows', COUNT(*)::numeric, 1::numeric,
           CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
           'IFRS 9 staging sample should not be empty.'
    FROM mart.ifrs9_staging_sample

    -- Null key checks
    UNION ALL
    SELECT 'null_check', 'company_id nulls', 'raw.companies',
           'null_count', SUM(CASE WHEN company_id IS NULL THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN company_id IS NULL THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'company_id is the primary borrower key.'
    FROM raw.companies

    UNION ALL
    SELECT 'null_check', 'facility_id nulls', 'raw.loan_facilities',
           'null_count', SUM(CASE WHEN facility_id IS NULL THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN facility_id IS NULL THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'facility_id is the primary facility key.'
    FROM raw.loan_facilities

    UNION ALL
    SELECT 'null_check', 'payment_id nulls', 'raw.payments',
           'null_count', SUM(CASE WHEN payment_id IS NULL THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN payment_id IS NULL THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'payment_id is the primary payment key.'
    FROM raw.payments

    -- Duplicate key checks
    UNION ALL
    SELECT 'duplicate_check', 'duplicate company_id', 'raw.companies',
           'duplicate_count', (COUNT(*) - COUNT(DISTINCT company_id))::numeric, 0::numeric,
           CASE WHEN COUNT(*) - COUNT(DISTINCT company_id) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'company_id should be unique.'
    FROM raw.companies

    UNION ALL
    SELECT 'duplicate_check', 'duplicate facility_id', 'raw.loan_facilities',
           'duplicate_count', (COUNT(*) - COUNT(DISTINCT facility_id))::numeric, 0::numeric,
           CASE WHEN COUNT(*) - COUNT(DISTINCT facility_id) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'facility_id should be unique.'
    FROM raw.loan_facilities

    UNION ALL
    SELECT 'duplicate_check', 'duplicate payment_id', 'raw.payments',
           'duplicate_count', (COUNT(*) - COUNT(DISTINCT payment_id))::numeric, 0::numeric,
           CASE WHEN COUNT(*) - COUNT(DISTINCT payment_id) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'payment_id should be unique.'
    FROM raw.payments

    UNION ALL
    SELECT 'duplicate_check', 'duplicate company report date', 'raw.financial_statements',
           'duplicate_count', (COUNT(*) - COUNT(DISTINCT (company_id, report_date)))::numeric, 0::numeric,
           CASE WHEN COUNT(*) - COUNT(DISTINCT (company_id, report_date)) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'There should be one financial statement per company and report date.'
    FROM raw.financial_statements

    -- Negative amount checks
    UNION ALL
    SELECT 'amount_check', 'negative revenue', 'raw.financial_statements',
           'invalid_count', SUM(CASE WHEN revenue < 0 THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN revenue < 0 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Revenue should not be negative in this synthetic dataset.'
    FROM raw.financial_statements

    UNION ALL
    SELECT 'amount_check', 'negative total assets', 'raw.financial_statements',
           'invalid_count', SUM(CASE WHEN total_assets < 0 THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN total_assets < 0 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Total assets should not be negative.'
    FROM raw.financial_statements

    UNION ALL
    SELECT 'amount_check', 'negative facility amounts', 'raw.loan_facilities',
           'invalid_count',
           SUM(CASE WHEN limit_amount < 0 OR outstanding_amount < 0 OR undrawn_amount < 0 THEN 1 ELSE 0 END)::numeric,
           0::numeric,
           CASE WHEN SUM(CASE WHEN limit_amount < 0 OR outstanding_amount < 0 OR undrawn_amount < 0 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Limit, outstanding and undrawn amounts should not be negative.'
    FROM raw.loan_facilities

    UNION ALL
    SELECT 'amount_check', 'negative collateral value', 'raw.collateral',
           'invalid_count', SUM(CASE WHEN collateral_value < 0 THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN collateral_value < 0 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Collateral value should not be negative.'
    FROM raw.collateral

    UNION ALL
    SELECT 'amount_check', 'negative payment amounts', 'raw.payments',
           'invalid_count',
           SUM(CASE WHEN scheduled_amount < 0 OR paid_amount < 0 OR outstanding_balance < 0 THEN 1 ELSE 0 END)::numeric,
           0::numeric,
           CASE WHEN SUM(CASE WHEN scheduled_amount < 0 OR paid_amount < 0 OR outstanding_balance < 0 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Payment and outstanding amounts should not be negative.'
    FROM raw.payments

    UNION ALL
    SELECT 'amount_check', 'negative recovery amounts', 'raw.recoveries',
           'invalid_count',
           SUM(CASE WHEN recovery_amount < 0 OR collection_cost < 0 THEN 1 ELSE 0 END)::numeric,
           0::numeric,
           CASE WHEN SUM(CASE WHEN recovery_amount < 0 OR collection_cost < 0 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Recovery amount and collection cost should not be negative.'
    FROM raw.recoveries

    -- Date checks
    UNION ALL
    SELECT 'date_check', 'maturity before origination', 'raw.loan_facilities',
           'invalid_count', SUM(CASE WHEN maturity_date < origination_date THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN maturity_date < origination_date THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Facility maturity date should not be earlier than origination date.'
    FROM raw.loan_facilities

    UNION ALL
    SELECT 'date_check', 'payment more than 31 days before origination', 'raw.payments',
           'invalid_count', COUNT(*)::numeric, 0::numeric,
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Payment date should not be materially earlier than facility origination date. A 31-day tolerance allows monthly synthetic payment snapshots.'
    FROM raw.payments p
    JOIN raw.loan_facilities lf
        ON p.facility_id = lf.facility_id
    WHERE p.payment_date < lf.origination_date - INTERVAL '31 days'

    UNION ALL
    SELECT 'date_check', 'payment within 31 days before origination', 'raw.payments',
           'warning_count', COUNT(*)::numeric, 0::numeric,
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'WARN' END,
           'Some monthly synthetic payment snapshots can fall shortly before origination when a facility starts mid-month.'
    FROM raw.payments p
    JOIN raw.loan_facilities lf
        ON p.facility_id = lf.facility_id
    WHERE p.payment_date < lf.origination_date
      AND p.payment_date >= lf.origination_date - INTERVAL '31 days'

    UNION ALL
    SELECT 'date_check', 'default before origination', 'raw.defaults',
           'invalid_count', COUNT(*)::numeric, 0::numeric,
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Default date should not be earlier than facility origination date.'
    FROM raw.defaults d
    JOIN raw.loan_facilities lf
        ON d.facility_id = lf.facility_id
    WHERE d.default_date < lf.origination_date

    UNION ALL
    SELECT 'date_check', 'recovery before default', 'raw.recoveries',
           'invalid_count', COUNT(*)::numeric, 0::numeric,
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Recovery date should not be earlier than default date.'
    FROM raw.recoveries r
    JOIN raw.defaults d
        ON r.facility_id = d.facility_id
    WHERE r.recovery_date < d.default_date

    -- PD sample checks
    UNION ALL
    SELECT 'modeling_sample_check', 'pd default rate', 'mart.pd_modeling_sample',
           'default_rate', AVG(target_default_12m)::numeric, NULL::numeric,
           CASE WHEN AVG(target_default_12m) BETWEEN 0.001 AND 0.300 THEN 'PASS' ELSE 'WARN' END,
           'PD target default rate should be non-zero and plausible for the synthetic portfolio.'
    FROM mart.pd_modeling_sample

    UNION ALL
    SELECT 'modeling_sample_check', 'pd target nulls', 'mart.pd_modeling_sample',
           'null_count', SUM(CASE WHEN target_default_12m IS NULL THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN target_default_12m IS NULL THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'PD target should not be null.'
    FROM mart.pd_modeling_sample

    -- LGD checks
    UNION ALL
    SELECT 'modeling_sample_check', 'lgd bounds', 'mart.lgd_modeling_sample',
           'invalid_count', SUM(CASE WHEN realized_lgd < 0 OR realized_lgd > 1 THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN realized_lgd < 0 OR realized_lgd > 1 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Realized LGD should be between 0 and 1 after clipping.'
    FROM mart.lgd_modeling_sample

    UNION ALL
    SELECT 'modeling_sample_check', 'lgd average', 'mart.lgd_modeling_sample',
           'avg_lgd', AVG(realized_lgd)::numeric, NULL::numeric,
           CASE WHEN AVG(realized_lgd) BETWEEN 0 AND 1 THEN 'PASS' ELSE 'FAIL' END,
           'Average realized LGD should be within valid probability bounds.'
    FROM mart.lgd_modeling_sample

    -- EAD / CCF checks
    UNION ALL
    SELECT 'modeling_sample_check', 'ccf bounds', 'mart.ead_ccf_modeling_sample',
           'invalid_count', SUM(CASE WHEN realized_ccf < 0 OR realized_ccf > 1.5 THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN realized_ccf < 0 OR realized_ccf > 1.5 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Realized CCF should be between 0 and 1.5 after clipping.'
    FROM mart.ead_ccf_modeling_sample

    UNION ALL
    SELECT 'modeling_sample_check', 'ccf average', 'mart.ead_ccf_modeling_sample',
           'avg_ccf', AVG(realized_ccf)::numeric, NULL::numeric,
           CASE WHEN AVG(realized_ccf) BETWEEN 0 AND 1.5 THEN 'PASS' ELSE 'FAIL' END,
           'Average realized CCF should be within expected bounds.'
    FROM mart.ead_ccf_modeling_sample

    -- IFRS 9 staging input checks
    UNION ALL
    SELECT 'ifrs9_check', 'ifrs9 default flag rate', 'mart.ifrs9_staging_sample',
           'default_flag_rate', AVG(default_flag)::numeric, NULL::numeric,
           CASE WHEN AVG(default_flag) BETWEEN 0.001 AND 0.300 THEN 'PASS' ELSE 'WARN' END,
           'Default flag rate should be plausible for the synthetic portfolio.'
    FROM mart.ifrs9_staging_sample

    UNION ALL
    SELECT 'ifrs9_check', 'current dpd negative values', 'mart.ifrs9_staging_sample',
           'invalid_count', SUM(CASE WHEN current_dpd < 0 THEN 1 ELSE 0 END)::numeric, 0::numeric,
           CASE WHEN SUM(CASE WHEN current_dpd < 0 THEN 1 ELSE 0 END) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'Current DPD should not be negative.'
    FROM mart.ifrs9_staging_sample

    -- IFRS 9 stage proxy distribution from staging rules
    UNION ALL
    SELECT 'ifrs9_stage_distribution', 'stage 1 facilities', 'mart.ifrs9_staging_sample',
           'facilities', COUNT(*)::numeric, NULL::numeric, 'INFO',
           'Stage proxy calculated from the same staging rules used in Python.'
    FROM mart.ifrs9_staging_sample
    WHERE NOT (
        default_flag = 1
        OR COALESCE(writeoff_flag, 0) = 1
        OR COALESCE(current_dpd, 0) >= 90
        OR COALESCE(dpd_at_default, 0) >= 90
        OR COALESCE(rating_downgrade_notches, 0) >= 2
        OR COALESCE(pd_ratio_current_to_origination, 0) >= 2
        OR COALESCE(current_dpd, 0) >= 30
        OR COALESCE(watchlist_flag, 0) = 1
        OR COALESCE(restructuring_flag, 0) = 1
    )

    UNION ALL
    SELECT 'ifrs9_stage_distribution', 'stage 2 facilities', 'mart.ifrs9_staging_sample',
           'facilities', COUNT(*)::numeric, NULL::numeric, 'INFO',
           'Stage proxy calculated from the same staging rules used in Python.'
    FROM mart.ifrs9_staging_sample
    WHERE NOT (
        default_flag = 1
        OR COALESCE(writeoff_flag, 0) = 1
        OR COALESCE(current_dpd, 0) >= 90
        OR COALESCE(dpd_at_default, 0) >= 90
    )
    AND (
        COALESCE(rating_downgrade_notches, 0) >= 2
        OR COALESCE(pd_ratio_current_to_origination, 0) >= 2
        OR COALESCE(current_dpd, 0) >= 30
        OR COALESCE(watchlist_flag, 0) = 1
        OR COALESCE(restructuring_flag, 0) = 1
    )

    UNION ALL
    SELECT 'ifrs9_stage_distribution', 'stage 3 facilities', 'mart.ifrs9_staging_sample',
           'facilities', COUNT(*)::numeric, NULL::numeric, 'INFO',
           'Stage proxy calculated from the same staging rules used in Python.'
    FROM mart.ifrs9_staging_sample
    WHERE (
        default_flag = 1
        OR COALESCE(writeoff_flag, 0) = 1
        OR COALESCE(current_dpd, 0) >= 90
        OR COALESCE(dpd_at_default, 0) >= 90
    )
)

SELECT
    check_group,
    check_name,
    table_name,
    metric_name,
    metric_value,
    threshold_value,
    status,
    details,
    CURRENT_TIMESTAMP AS checked_at
FROM quality_checks
ORDER BY
    CASE status
        WHEN 'FAIL' THEN 1
        WHEN 'WARN' THEN 2
        WHEN 'PASS' THEN 3
        ELSE 4
    END,
    check_group,
    check_name;
