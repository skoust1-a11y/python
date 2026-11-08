import random
from datetime import datetime, timedelta

# -----------------------------
# CONFIGURATION
# -----------------------------
NUM_PORTFOLIOS = 20
NUM_HOLDINGS = 120
NUM_RISK_LOGS = 150
NUM_MARKET_INDICATORS = 80
NUM_INVESTMENT_DECISIONS = 100

# -----------------------------
# SAMPLE DATA POOLS
# -----------------------------

portfolio_managers = [
    "Alice Morgan", "David Chen", "Ravi Patel",
    "Sophia Martinez", "Daniel Kim", "Emma Wilson"
]

risk_categories = ["Low", "Moderate", "High"]
benchmark_indexes = ["S&P 500", "NASDAQ 100", "MSCI World", "FTSE 100"]

assets = [
    "Apple Inc", "Tesla", "Microsoft", "Amazon",
    "Google", "Nvidia", "JPMorgan", "Gold ETF",
    "Oil Futures", "US Treasury Bonds"
]

asset_types = ["Equity", "ETF", "Bond", "Commodity"]
sectors = ["Technology", "Finance", "Energy", "Healthcare", "Consumer"]

risk_types = [
    "Market Volatility",
    "Liquidity Risk",
    "Regulatory Risk",
    "Credit Risk",
    "Geopolitical Risk"
]

decision_types = ["BUY", "SELL", "HOLD"]

regions = ["US", "Europe", "Asia", "Global"]

market_indicators = [
    "Inflation Rate",
    "Interest Rate",
    "GDP Growth",
    "Unemployment Rate",
    "Consumer Confidence Index"
]

trend_directions = ["Increasing", "Decreasing", "Stable"]

approval_status = ["Approved", "Pending", "Rejected"]

# -----------------------------
# HELPERS
# -----------------------------

def random_date():
    start = datetime(2024, 1, 1)
    end = datetime(2025, 3, 1)
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def generate_risk_level(score):
    if score < 30:
        return "Low"
    elif score < 70:
        return "Medium"
    return "High"


# -----------------------------
# DATA GENERATORS
# -----------------------------

def generate_portfolios():
    rows = []
    for i in range(1, NUM_PORTFOLIOS + 1):
        portfolio_name = f"Global Growth Portfolio {i}"
        manager = random.choice(portfolio_managers)
        risk_category = random.choice(risk_categories)
        total_value = random.randint(5_000_000, 50_000_000)
        benchmark = random.choice(benchmark_indexes)

        row = f"""INSERT INTO portfolios 
(portfolio_id, portfolio_name, portfolio_manager, risk_category, total_value, benchmark_index)
VALUES ({i}, '{portfolio_name}', '{manager}', '{risk_category}', {total_value}, '{benchmark}');"""

        rows.append(row)
    return rows


def generate_holdings():
    rows = []
    for i in range(1, NUM_HOLDINGS + 1):

        portfolio_id = random.randint(1, NUM_PORTFOLIOS)
        asset = random.choice(assets)
        asset_type = random.choice(asset_types)
        sector = random.choice(sectors)
        allocation = round(random.uniform(1, 25), 2)
        market_value = random.randint(50_000, 5_000_000)
        date = random_date().date()

        row = f"""INSERT INTO portfolio_holdings 
(holding_id, portfolio_id, asset_name, asset_type, sector, allocation_percentage, market_value, last_updated)
VALUES ({i}, {portfolio_id}, '{asset}', '{asset_type}', '{sector}', {allocation}, {market_value}, '{date}');"""

        rows.append(row)

    return rows


def generate_risk_logs():
    rows = []

    for i in range(1, NUM_RISK_LOGS + 1):

        asset = random.choice(assets)
        risk_type = random.choice(risk_types)
        score = random.randint(0, 100)
        risk_level = generate_risk_level(score)
        description = f"{risk_type} identified for {asset} due to market conditions."
        date = random_date().date()
        escalation = "TRUE" if score > 80 else "FALSE"

        row = f"""INSERT INTO asset_risk_logs 
(risk_id, asset_name, risk_type, risk_score, risk_level, risk_description, assessment_date, escalation_flag)
VALUES ({i}, '{asset}', '{risk_type}', {score}, '{risk_level}', '{description}', '{date}', {escalation});"""

        rows.append(row)

    return rows


def generate_market_indicators():
    rows = []

    for i in range(1, NUM_MARKET_INDICATORS + 1):

        indicator = random.choice(market_indicators)
        region = random.choice(regions)
        value = round(random.uniform(1.0, 10.0), 2)
        date = random_date().date()
        trend = random.choice(trend_directions)

        row = f"""INSERT INTO market_indicators
(indicator_id, indicator_name, region, indicator_value, measurement_date, trend_direction)
VALUES ({i}, '{indicator}', '{region}', {value}, '{date}', '{trend}');"""

        rows.append(row)

    return rows


def generate_investment_decisions():
    rows = []

    for i in range(1, NUM_INVESTMENT_DECISIONS + 1):

        portfolio_id = random.randint(1, NUM_PORTFOLIOS)
        asset = random.choice(assets)
        decision = random.choice(decision_types)
        risk_reference = random.randint(1, NUM_RISK_LOGS)
        reason = f"Decision based on market trend and portfolio diversification strategy."
        date = random_date().date()
        approval = random.choice(approval_status)

        row = f"""INSERT INTO investment_decisions
(decision_id, portfolio_id, asset_name, decision_type, decision_reason, risk_assessment_reference, decision_date, approval_status)
VALUES ({i}, {portfolio_id}, '{asset}', '{decision}', '{reason}', {risk_reference}, '{date}', '{approval}');"""

        rows.append(row)

    return rows


# -----------------------------
# MAIN
# -----------------------------

def generate_sql_file():

    sql_statements = []

    sql_statements += generate_portfolios()
    sql_statements += generate_holdings()
    sql_statements += generate_risk_logs()
    sql_statements += generate_market_indicators()
    sql_statements += generate_investment_decisions()

    with open("finance_capstone_data.sql", "w") as f:
        for stmt in sql_statements:
            f.write(stmt + "\n")

    print("SQL data generation completed → finance_capstone_data.sql")


if __name__ == "__main__":
    generate_sql_file()