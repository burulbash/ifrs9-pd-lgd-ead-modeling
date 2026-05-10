from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SIZE_CONFIG = {
    "tiny": 500,
    "small": 3_000,
    "medium": 10_000,
}

START_DATE = pd.Timestamp("2021-01-01")
END_DATE = pd.Timestamp("2025-12-31")


INDUSTRIES = [
    "trade",
    "construction",
    "manufacturing",
    "agriculture",
    "transport",
    "services",
    "real_estate",
    "energy",
]

REGIONS = [
    "Almaty",
    "Astana",
    "Shymkent",
    "Karaganda",
    "Aktobe",
    "Atyrau",
    "Kostanay",
    "Other",
]

COMPANY_SIZES = ["micro", "small", "medium", "large"]

LEGAL_FORMS = ["LLP", "JSC", "IE"]

OWNERSHIP_TYPES = ["private", "state_related", "foreign_owned"]

LATENT_PROFILES = [
    "stable_exporter",
    "high_growth_sme",
    "construction_sensitive",
    "agri_seasonal",
    "high_leverage",
    "weak_cashflow",
    "collateralized_borrower",
    "distressed_company",
]


def random_dates(
    rng: np.random.Generator,
    start: pd.Timestamp,
    end: pd.Timestamp,
    size: int,
) -> pd.Series:
    start_day = start.toordinal()
    end_day = end.toordinal()

    days = rng.integers(start_day, end_day + 1, size=size)
    dates = [pd.Timestamp.fromordinal(int(day)) for day in days]

    return pd.Series(pd.to_datetime(dates))


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def generate_companies(n_companies: int, rng: np.random.Generator) -> pd.DataFrame:
    company_ids = [f"C{idx:06d}" for idx in range(1, n_companies + 1)]

    profile_probs = np.array([0.14, 0.14, 0.13, 0.11, 0.15, 0.14, 0.12, 0.07])
    size_probs = np.array([0.28, 0.42, 0.23, 0.07])

    registration_dates = random_dates(
        rng,
        pd.Timestamp("2000-01-01"),
        pd.Timestamp("2023-12-31"),
        n_companies,
    )

    companies = pd.DataFrame(
        {
            "company_id": company_ids,
            "registration_date": registration_dates,
            "industry": rng.choice(INDUSTRIES, size=n_companies),
            "region": rng.choice(REGIONS, size=n_companies),
            "company_size": rng.choice(COMPANY_SIZES, size=n_companies, p=size_probs),
            "legal_form": rng.choice(LEGAL_FORMS, size=n_companies, p=[0.75, 0.08, 0.17]),
            "ownership_type": rng.choice(
                OWNERSHIP_TYPES,
                size=n_companies,
                p=[0.82, 0.08, 0.10],
            ),
            "latent_profile": rng.choice(
                LATENT_PROFILES,
                size=n_companies,
                p=profile_probs,
            ),
        }
    )

    companies["years_in_business"] = (
        (END_DATE - companies["registration_date"]).dt.days / 365.25
    ).clip(lower=0.5).round(1)

    employees_base = companies["company_size"].map(
        {
            "micro": 8,
            "small": 35,
            "medium": 140,
            "large": 600,
        }
    )

    employees_count = (
        employees_base.to_numpy()
        * rng.lognormal(mean=0.0, sigma=0.35, size=n_companies)
    ).round().astype(int)

    companies["employees_count"] = np.clip(employees_count, 1, None)

    companies["exporter_flag"] = (
        (companies["latent_profile"].eq("stable_exporter"))
        | ((companies["industry"].isin(["manufacturing", "agriculture", "energy"])) & (rng.random(n_companies) < 0.25))
    ).astype(int)

    companies["state_related_flag"] = companies["ownership_type"].eq("state_related").astype(int)
    companies["related_party_flag"] = (rng.random(n_companies) < 0.04).astype(int)

    return companies


def profile_risk_adjustment(profile: pd.Series) -> pd.Series:
    mapping = {
        "stable_exporter": -0.9,
        "high_growth_sme": -0.2,
        "construction_sensitive": 0.45,
        "agri_seasonal": 0.25,
        "high_leverage": 0.85,
        "weak_cashflow": 0.95,
        "collateralized_borrower": -0.25,
        "distressed_company": 1.65,
    }

    return profile.map(mapping).astype(float)


def generate_financial_statements(
    companies: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    years = [2021, 2022, 2023, 2024, 2025]
    rows = []

    size_revenue = {
        "micro": 80_000,
        "small": 450_000,
        "medium": 2_500_000,
        "large": 12_000_000,
    }

    profile_growth = {
        "stable_exporter": 0.09,
        "high_growth_sme": 0.22,
        "construction_sensitive": 0.04,
        "agri_seasonal": 0.03,
        "high_leverage": 0.02,
        "weak_cashflow": -0.02,
        "collateralized_borrower": 0.05,
        "distressed_company": -0.08,
    }

    profile_margin = {
        "stable_exporter": 0.18,
        "high_growth_sme": 0.15,
        "construction_sensitive": 0.10,
        "agri_seasonal": 0.12,
        "high_leverage": 0.09,
        "weak_cashflow": 0.06,
        "collateralized_borrower": 0.13,
        "distressed_company": 0.02,
    }

    for _, company in companies.iterrows():
        base_revenue = size_revenue[company["company_size"]] * rng.lognormal(0, 0.55)
        growth = profile_growth[company["latent_profile"]]

        revenue_prev = None

        for year in years:
            year_noise = rng.normal(0, 0.08)
            revenue = base_revenue * ((1 + growth + year_noise) ** (year - years[0]))
            revenue = max(revenue, 10_000)

            ebitda_margin = profile_margin[company["latent_profile"]] + rng.normal(0, 0.035)
            ebitda_margin = float(np.clip(ebitda_margin, -0.10, 0.35))
            ebitda = revenue * ebitda_margin

            net_income = ebitda - abs(revenue * rng.normal(0.05, 0.02))

            total_assets = revenue * rng.uniform(0.7, 1.8)
            current_assets = total_assets * rng.uniform(0.25, 0.65)
            cash = current_assets * rng.uniform(0.04, 0.25)
            inventory = current_assets * rng.uniform(0.05, 0.35)
            accounts_receivable = current_assets * rng.uniform(0.10, 0.45)

            leverage = {
                "stable_exporter": 0.35,
                "high_growth_sme": 0.45,
                "construction_sensitive": 0.60,
                "agri_seasonal": 0.48,
                "high_leverage": 0.78,
                "weak_cashflow": 0.70,
                "collateralized_borrower": 0.58,
                "distressed_company": 0.88,
            }[company["latent_profile"]]

            total_liabilities = total_assets * np.clip(rng.normal(leverage, 0.08), 0.05, 0.95)
            equity = total_assets - total_liabilities

            current_liabilities = total_liabilities * rng.uniform(0.25, 0.65)
            short_term_debt = current_liabilities * rng.uniform(0.20, 0.75)
            long_term_debt = (total_liabilities - current_liabilities) * rng.uniform(0.30, 0.90)

            total_debt = short_term_debt + long_term_debt
            interest_expense = total_debt * rng.uniform(0.05, 0.16)
            operating_cash_flow = ebitda * rng.uniform(0.35, 1.10)
            capex = revenue * rng.uniform(0.01, 0.08)

            rows.append(
                {
                    "company_id": company["company_id"],
                    "report_date": pd.Timestamp(f"{year}-12-31"),
                    "revenue": round(revenue, 2),
                    "revenue_prev_year": round(revenue_prev, 2) if revenue_prev is not None else np.nan,
                    "ebitda": round(ebitda, 2),
                    "net_income": round(net_income, 2),
                    "total_assets": round(total_assets, 2),
                    "current_assets": round(current_assets, 2),
                    "cash": round(cash, 2),
                    "inventory": round(inventory, 2),
                    "accounts_receivable": round(accounts_receivable, 2),
                    "total_liabilities": round(total_liabilities, 2),
                    "current_liabilities": round(current_liabilities, 2),
                    "short_term_debt": round(short_term_debt, 2),
                    "long_term_debt": round(long_term_debt, 2),
                    "equity": round(equity, 2),
                    "interest_expense": round(interest_expense, 2),
                    "operating_cash_flow": round(operating_cash_flow, 2),
                    "capex": round(capex, 2),
                }
            )

            revenue_prev = revenue

    return pd.DataFrame(rows)


def generate_loan_facilities(
    companies: pd.DataFrame,
    financials: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    latest_financials = (
        financials.sort_values("report_date")
        .groupby("company_id", as_index=False)
        .tail(1)[["company_id", "revenue"]]
    )

    company_base = companies.merge(latest_financials, on="company_id", how="left")

    rows = []
    facility_id = 1

    for _, company in company_base.iterrows():
        n_facilities = int(np.clip(rng.poisson(1.3), 1, 4))

        for _ in range(n_facilities):
            product_type = rng.choice(
                ["term_loan", "credit_line", "overdraft", "working_capital", "leasing", "trade_finance"],
                p=[0.34, 0.22, 0.12, 0.16, 0.10, 0.06],
            )

            revolving_flag = int(product_type in ["credit_line", "overdraft", "trade_finance"])

            origination_date = random_dates(
                rng,
                pd.Timestamp("2022-01-01"),
                pd.Timestamp("2025-06-30"),
                1,
            ).iloc[0]

            term_months = int(rng.choice([12, 18, 24, 36, 48, 60], p=[0.18, 0.12, 0.24, 0.25, 0.13, 0.08]))
            maturity_date = origination_date + pd.DateOffset(months=term_months)

            annual_revenue = max(company["revenue"], 50_000)
            limit_amount = annual_revenue * rng.uniform(0.05, 0.35)

            if product_type == "overdraft":
                limit_amount *= 0.45
            elif product_type == "leasing":
                limit_amount *= 0.80

            utilization = rng.uniform(0.35, 0.95) if revolving_flag else rng.uniform(0.80, 1.00)
            outstanding_amount = limit_amount * utilization
            undrawn_amount = max(limit_amount - outstanding_amount, 0)

            risk_adj = profile_risk_adjustment(pd.Series([company["latent_profile"]])).iloc[0]
            interest_rate = np.clip(0.12 + risk_adj * 0.015 + rng.normal(0, 0.015), 0.08, 0.28)

            rows.append(
                {
                    "facility_id": f"F{facility_id:07d}",
                    "company_id": company["company_id"],
                    "origination_date": origination_date,
                    "maturity_date": maturity_date,
                    "product_type": product_type,
                    "limit_amount": round(limit_amount, 2),
                    "outstanding_amount": round(outstanding_amount, 2),
                    "undrawn_amount": round(undrawn_amount, 2),
                    "interest_rate": round(float(interest_rate), 4),
                    "term_months": term_months,
                    "revolving_flag": revolving_flag,
                    "seniority": rng.choice(["senior_secured", "senior_unsecured", "subordinated"], p=[0.62, 0.32, 0.06]),
                    "currency": rng.choice(["KZT", "USD", "EUR"], p=[0.78, 0.18, 0.04]),
                    "repayment_type": rng.choice(["annuity", "bullet", "amortizing"], p=[0.35, 0.25, 0.40]),
                }
            )

            facility_id += 1

    return pd.DataFrame(rows)


def generate_collateral(
    facilities: pd.DataFrame,
    companies: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    company_profiles = companies[["company_id", "latent_profile"]]
    data = facilities.merge(company_profiles, on="company_id", how="left")

    rows = []

    for idx, facility in data.iterrows():
        profile = facility["latent_profile"]

        has_collateral_prob = {
            "stable_exporter": 0.70,
            "high_growth_sme": 0.55,
            "construction_sensitive": 0.72,
            "agri_seasonal": 0.62,
            "high_leverage": 0.60,
            "weak_cashflow": 0.50,
            "collateralized_borrower": 0.92,
            "distressed_company": 0.42,
        }[profile]

        has_collateral = rng.random() < has_collateral_prob

        if not has_collateral:
            collateral_type = "none"
            collateral_value = 0.0
            haircut = 1.0
        else:
            collateral_type = rng.choice(
                ["real_estate", "equipment", "inventory", "receivables", "guarantee"],
                p=[0.38, 0.22, 0.15, 0.15, 0.10],
            )

            coverage = rng.uniform(0.6, 2.4)

            if profile == "collateralized_borrower":
                coverage *= 1.35
            if profile == "distressed_company":
                coverage *= 0.65

            collateral_value = facility["outstanding_amount"] * coverage

            haircut = {
                "real_estate": 0.25,
                "equipment": 0.40,
                "inventory": 0.55,
                "receivables": 0.45,
                "guarantee": 0.30,
            }[collateral_type]

        rows.append(
            {
                "collateral_id": f"CL{idx + 1:07d}",
                "facility_id": facility["facility_id"],
                "collateral_type": collateral_type,
                "collateral_value": round(float(collateral_value), 2),
                "haircut": round(float(haircut), 3),
                "valuation_date": facility["origination_date"],
            }
        )

    return pd.DataFrame(rows)


def assign_rating_from_pd(pd_value: float) -> str:
    if pd_value < 0.005:
        return "A"
    if pd_value < 0.015:
        return "B"
    if pd_value < 0.035:
        return "C"
    if pd_value < 0.075:
        return "D"
    if pd_value < 0.15:
        return "E"
    return "F"


def generate_rating_history(
    companies: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    rows = []

    for _, company in companies.iterrows():
        risk_adj = profile_risk_adjustment(pd.Series([company["latent_profile"]])).iloc[0]
        base_pd = float(np.clip(sigmoid(np.array([-4.7 + risk_adj]))[0], 0.002, 0.35))

        for year in [2022, 2023, 2024, 2025]:
            pd_estimate = float(np.clip(base_pd * rng.lognormal(0, 0.25), 0.001, 0.45))
            rating_grade = assign_rating_from_pd(pd_estimate)

            watchlist_prob = np.clip(pd_estimate * 2.5, 0.01, 0.45)
            restructuring_prob = np.clip(pd_estimate * 0.8, 0.005, 0.20)

            rows.append(
                {
                    "company_id": company["company_id"],
                    "rating_date": pd.Timestamp(f"{year}-01-01"),
                    "rating_grade": rating_grade,
                    "pd_estimate": round(pd_estimate, 6),
                    "watchlist_flag": int(rng.random() < watchlist_prob),
                    "restructuring_flag": int(rng.random() < restructuring_prob),
                }
            )

    return pd.DataFrame(rows)


def generate_defaults(
    facilities: pd.DataFrame,
    companies: pd.DataFrame,
    collateral: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    data = (
        facilities.merge(companies[["company_id", "latent_profile", "industry"]], on="company_id", how="left")
        .merge(collateral[["facility_id", "collateral_value"]], on="facility_id", how="left")
    )

    rows = []

    industry_adj = {
        "trade": 0.05,
        "construction": 0.45,
        "manufacturing": 0.10,
        "agriculture": 0.20,
        "transport": 0.15,
        "services": 0.00,
        "real_estate": 0.35,
        "energy": -0.05,
    }

    for _, facility in data.iterrows():
        profile_adj = profile_risk_adjustment(pd.Series([facility["latent_profile"]])).iloc[0]
        industry_risk = industry_adj[facility["industry"]]
        utilization = facility["outstanding_amount"] / max(facility["limit_amount"], 1)

        collateral_coverage = facility["collateral_value"] / max(facility["outstanding_amount"], 1)

        logit_pd = -4.2 + profile_adj + industry_risk + 1.1 * utilization - 0.35 * min(collateral_coverage, 2.5)
        default_prob = float(np.clip(sigmoid(np.array([logit_pd]))[0], 0.002, 0.55))

        default_flag = rng.random() < default_prob

        if not default_flag:
            continue

        min_default_date = facility["origination_date"] + pd.DateOffset(months=3)
        max_default_date = min(facility["maturity_date"], END_DATE)

        if min_default_date >= max_default_date:
            default_date = max_default_date
        else:
            default_date = random_dates(rng, min_default_date, max_default_date, 1).iloc[0]

        if facility["revolving_flag"] == 1:
            drawdown = facility["undrawn_amount"] * rng.uniform(0.20, 0.85)
        else:
            drawdown = 0

        ead_at_default = facility["outstanding_amount"] + drawdown

        rows.append(
            {
                "facility_id": facility["facility_id"],
                "default_date": default_date,
                "default_type": rng.choice(["90dpd", "bankruptcy", "restructuring", "writeoff"], p=[0.70, 0.08, 0.17, 0.05]),
                "dpd_at_default": int(rng.choice([90, 120, 150, 180, 360], p=[0.45, 0.22, 0.14, 0.12, 0.07])),
                "ead_at_default": round(float(ead_at_default), 2),
                "writeoff_flag": int(rng.random() < 0.18),
            }
        )

    return pd.DataFrame(rows)


def generate_recoveries(
    defaults: pd.DataFrame,
    collateral: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    if defaults.empty:
        return pd.DataFrame(
            columns=[
                "recovery_id",
                "facility_id",
                "recovery_date",
                "recovery_amount",
                "recovery_type",
                "collection_cost",
            ]
        )

    data = defaults.merge(
        collateral[["facility_id", "collateral_type", "collateral_value", "haircut"]],
        on="facility_id",
        how="left",
    )

    rows = []
    recovery_id = 1

    for _, default in data.iterrows():
        n_recoveries = int(rng.choice([1, 2, 3, 4], p=[0.40, 0.35, 0.18, 0.07]))

        effective_collateral = default["collateral_value"] * (1 - default["haircut"])
        collateral_recovery_rate = effective_collateral / max(default["ead_at_default"], 1)

        total_recovery_rate = float(np.clip(0.10 + 0.55 * collateral_recovery_rate + rng.normal(0, 0.12), 0.02, 0.95))
        total_recovery = default["ead_at_default"] * total_recovery_rate

        parts = rng.dirichlet(np.ones(n_recoveries))

        for part in parts:
            recovery_date = default["default_date"] + pd.DateOffset(months=int(rng.integers(1, 25)))
            recovery_amount = total_recovery * part
            collection_cost = recovery_amount * rng.uniform(0.02, 0.12)

            rows.append(
                {
                    "recovery_id": f"R{recovery_id:07d}",
                    "facility_id": default["facility_id"],
                    "recovery_date": recovery_date,
                    "recovery_amount": round(float(recovery_amount), 2),
                    "recovery_type": rng.choice(["cash", "collateral_sale", "guarantee_payment", "restructuring_payment"], p=[0.45, 0.32, 0.12, 0.11]),
                    "collection_cost": round(float(collection_cost), 2),
                }
            )

            recovery_id += 1

    return pd.DataFrame(rows)


def generate_payments(
    facilities: pd.DataFrame,
    defaults: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    default_dates = defaults.set_index("facility_id")["default_date"].to_dict()

    rows = []
    payment_id = 1

    for _, facility in facilities.iterrows():
        start_month = pd.Timestamp(facility["origination_date"]).to_period("M").to_timestamp()
        end_month = min(pd.Timestamp(facility["maturity_date"]), END_DATE).to_period("M").to_timestamp()

        months = pd.date_range(start_month, end_month, freq="MS")

        if len(months) == 0:
            continue

        scheduled_amount = facility["outstanding_amount"] / max(len(months), 1)

        facility_default_date = default_dates.get(facility["facility_id"])

        outstanding = facility["outstanding_amount"]

        for month in months:
            if facility_default_date is not None and month >= facility_default_date:
                dpd = int(rng.choice([90, 120, 150, 180, 360], p=[0.45, 0.22, 0.14, 0.12, 0.07]))
                paid_amount = scheduled_amount * rng.uniform(0.0, 0.25)
            else:
                dpd = int(rng.choice([0, 0, 0, 5, 15, 30, 60], p=[0.72, 0.05, 0.05, 0.06, 0.05, 0.05, 0.02]))
                paid_amount = scheduled_amount * rng.uniform(0.85, 1.05) if dpd < 30 else scheduled_amount * rng.uniform(0.30, 0.80)

            outstanding = max(outstanding - paid_amount, 0)

            rows.append(
                {
                    "payment_id": f"P{payment_id:09d}",
                    "facility_id": facility["facility_id"],
                    "payment_date": month,
                    "scheduled_amount": round(float(scheduled_amount), 2),
                    "paid_amount": round(float(paid_amount), 2),
                    "days_past_due": dpd,
                    "outstanding_balance": round(float(outstanding), 2),
                }
            )

            payment_id += 1

    return pd.DataFrame(rows)


def generate_macro_scenarios() -> pd.DataFrame:
    months = pd.date_range("2021-01-01", "2026-12-01", freq="MS")
    scenarios = [
        ("base", 0.60, 0.030, 0.075, 0.145, 0.048, 470, 1.0),
        ("downside", 0.25, -0.010, 0.110, 0.175, 0.065, 540, 1.35),
        ("upside", 0.15, 0.050, 0.055, 0.115, 0.040, 440, 0.85),
        ("severe_downturn", 0.00, -0.040, 0.140, 0.210, 0.090, 620, 1.85),
    ]

    rows = []

    for month in months:
        season = np.sin(2 * np.pi * month.month / 12)

        for scenario, weight, gdp, inflation, base_rate, unemployment, fx_rate, stress in scenarios:
            rows.append(
                {
                    "month": month,
                    "scenario": scenario,
                    "scenario_weight": weight,
                    "gdp_growth": round(gdp + 0.005 * season, 4),
                    "inflation": round(inflation + 0.004 * season, 4),
                    "base_rate": round(base_rate, 4),
                    "unemployment": round(unemployment + 0.002 * season, 4),
                    "fx_rate": round(fx_rate * (1 + 0.015 * season), 2),
                    "industry_stress_index": round(stress + 0.04 * season, 4),
                }
            )

    return pd.DataFrame(rows)


def write_csv(df: pd.DataFrame, output_dir: Path, filename: str) -> None:
    path = output_dir / filename
    df.to_csv(path, index=False)
    print(f"{filename}: {len(df):,} rows")


def generate_all(
    size: str,
    seed: int,
    output_dir: Path,
) -> None:
    rng = np.random.default_rng(seed)
    n_companies = SIZE_CONFIG[size]

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating IFRS9 synthetic corporate portfolio: size={size}, companies={n_companies:,}, seed={seed}")
    print(f"Output directory: {output_dir.resolve()}")
    print()

    companies = generate_companies(n_companies, rng)
    financials = generate_financial_statements(companies, rng)
    facilities = generate_loan_facilities(companies, financials, rng)
    collateral = generate_collateral(facilities, companies, rng)
    rating_history = generate_rating_history(companies, rng)
    defaults = generate_defaults(facilities, companies, collateral, rng)
    recoveries = generate_recoveries(defaults, collateral, rng)
    payments = generate_payments(facilities, defaults, rng)
    macro_scenarios = generate_macro_scenarios()

    write_csv(companies, output_dir, "companies.csv")
    write_csv(financials, output_dir, "financial_statements.csv")
    write_csv(facilities, output_dir, "loan_facilities.csv")
    write_csv(collateral, output_dir, "collateral.csv")
    write_csv(payments, output_dir, "payments.csv")
    write_csv(defaults, output_dir, "defaults.csv")
    write_csv(recoveries, output_dir, "recoveries.csv")
    write_csv(rating_history, output_dir, "rating_history.csv")
    write_csv(macro_scenarios, output_dir, "macro_scenarios.csv")

    summary = pd.DataFrame(
        {
            "metric": [
                "companies",
                "financial_statements",
                "loan_facilities",
                "collateral",
                "payments",
                "defaults",
                "recoveries",
                "rating_history",
                "macro_scenarios",
                "defaulted_facility_share",
            ],
            "value": [
                len(companies),
                len(financials),
                len(facilities),
                len(collateral),
                len(payments),
                len(defaults),
                len(recoveries),
                len(rating_history),
                len(macro_scenarios),
                len(defaults) / max(len(facilities), 1),
            ],
        }
    )

    write_csv(summary, output_dir, "generation_summary.csv")
    print()
    print(summary.to_string(index=False))
    print()
    print("Generation completed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic IFRS9 corporate credit risk data.")
    parser.add_argument("--size", choices=SIZE_CONFIG.keys(), default="tiny")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="data/raw/ifrs9_synthetic")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    generate_all(
        size=args.size,
        seed=args.seed,
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
