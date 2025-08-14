from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
import math
import requests
from datetime import datetime

app = FastAPI(
    title="KSE-100 Investment Calculator API",
    description="API for calculating optimal investment allocation in KSE-100 index stocks",
    version="1.0.0"
)

# Configuration
EXCEL_FILE = "kse100.xlsx"
API_URL = "https://psxterminal.com/api/market-data?market=REG"

# Response models
class StockAllocation(BaseModel):
    symbol: str
    weight_percent: float
    adjusted_weight_percent: float
    price: float
    shares: int
    invested_amount: float

class InvestmentResponse(BaseModel):
    success: bool
    message: str
    investment_plan: List[StockAllocation]
    summary: Dict[str, Any]
    selected_companies: List[str]
    timestamp: str

# --- SIP models ---
class SIPRow(BaseModel):
    year: int
    year_deposits: float
    earnings_this_year: float
    total_deposits: float
    accrued_earnings: float
    net_balance: float

class SIPResponse(BaseModel):
    success: bool
    rows: List[SIPRow]
    summary: Dict[str, Any]
    timestamp: str

# Helper: crore/lakh formatter for summary
def format_cr_lac(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    amt = abs(amount)
    if amt >= 10_000_000:  # 1 crore
        return f"{sign}{amt/10_000_000:.2f} cr"
    if amt >= 100_000:  # 1 lakh
        return f"{sign}{amt/100_000:.2f} lac"
    return f"{sign}{amt:,.2f}"


def update_prices_api():
    """Update stock prices from PSX API"""
    try:
        df = pd.read_excel(EXCEL_FILE)
        
        if 'symbol' not in df.columns:
            raise ValueError("Excel file must contain a 'symbol' column")

        response = requests.get(API_URL, timeout=10)
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}")
        
        market_data = response.json()
        stocks = market_data.get("data", {})

        price_lookup = {sym.upper(): stock["price"]
                        for sym, stock in stocks.items()
                        if isinstance(stock, dict) and "price" in stock}

        df['price'] = [
            price_lookup.get(str(sym).upper().strip(), None)
            for sym in df['symbol']
        ]

        df.to_excel(EXCEL_FILE, index=False)
        updated_count = df['price'].notna().sum()
        return True, f"Updated prices for {updated_count}/{len(df)} companies"
        
    except Exception as e:
        return False, f"Error updating prices: {str(e)}"


def calculate_investment_api(coverage_percent: float, investment_amount: float):
    """Calculate investment allocation"""
    try:
        df = pd.read_excel(EXCEL_FILE)

        if not all(col in df.columns for col in ['symbol', 'weight', 'price']):
            raise ValueError("Excel file must contain columns: symbol, weight, price")

        # Select companies until cumulative weight >= coverage_percent
        df['cum_weight'] = df['weight'].cumsum()
        target_coverage_decimal = coverage_percent / 100
        
        coverage_reached_idx = df[df['cum_weight'] >= target_coverage_decimal].index
        
        if len(coverage_reached_idx) > 0:
            first_coverage_idx = coverage_reached_idx[0]
            selected = df.loc[:first_coverage_idx].copy()
        else:
            selected = df.copy()

        # Normalize weights
        total_selected_weight = selected['weight'].sum()
        selected['adjusted_weight'] = selected['weight'] / total_selected_weight

        # Calculate investments
        results = []
        total_invested = 0
        successful_investments = 0

        for _, row in selected.iterrows():
            symbol = row['symbol']
            price = row['price']
            adj_weight = row['adjusted_weight']

            if pd.isna(price) or price <= 0:
                continue

            allocation_amount = adj_weight * investment_amount
            shares = math.floor(allocation_amount / price)
            invested_amount = shares * price
            total_invested += invested_amount

            if shares > 0:
                successful_investments += 1

            results.append(StockAllocation(
                symbol=symbol,
                weight_percent=round(row['weight'] * 100, 2),
                adjusted_weight_percent=round(adj_weight * 100, 2),
                price=float(price),
                shares=int(shares),
                invested_amount=round(invested_amount, 2)
            ))

        remaining_cash = investment_amount - total_invested

        summary = {
            "total_investment_amount": investment_amount,
            "total_invested": round(total_invested, 2),
            "remaining_cash": round(remaining_cash, 2),
            "investment_efficiency_percent": round((total_invested/investment_amount)*100, 2),
            "companies_selected": len(selected),
            "companies_invested": successful_investments,
            "target_coverage_percent": coverage_percent,
            "actual_coverage_percent": round(total_selected_weight * 100, 2)
        }

        selected_companies = selected['symbol'].tolist()
        return True, results, summary, selected_companies, "Investment calculation completed successfully"

    except Exception as e:
        return False, [], {}, [], f"Error calculating investment: {str(e)}"


# --- SIP core logic ---
def compute_sip_api(
    initial_balance: float,
    years: int,
    annual_interest_rate: float,
    monthly_investment: float,
    yearly_increment_percent: float
):
    rows: List[SIPRow] = []
    balance = float(initial_balance)
    total_deposits = float(initial_balance)
    total_earnings = 0.0
    monthly_rate = (annual_interest_rate / 100.0) / 12.0

    # Optional Year 0 row only if initial balance > 0
    if initial_balance > 0:
        rows.append(SIPRow(
            year=0,
            year_deposits=round(initial_balance, 2),
            earnings_this_year=0.0,
            total_deposits=round(total_deposits, 2),
            accrued_earnings=round(total_earnings, 2),
            net_balance=round(balance, 2)
        ))

    for year in range(1, years + 1):
        year_deposits = 0.0
        year_earnings = 0.0

        for _ in range(12):
            # Apply interest on starting balance (deposit earns from next month)
            monthly_interest = balance * monthly_rate
            balance += monthly_interest
            year_earnings += monthly_interest

            # Add this month's deposit at end of month
            balance += monthly_investment
            year_deposits += monthly_investment

        total_deposits += year_deposits
        total_earnings += year_earnings

        rows.append(SIPRow(
            year=year,
            year_deposits=round(year_deposits, 2),
            earnings_this_year=round(year_earnings, 2),
            total_deposits=round(total_deposits, 2),
            accrued_earnings=round(total_earnings, 2),
            net_balance=round(balance, 2)
        ))

        # Increase monthly SIP for next year
        monthly_investment += monthly_investment * (yearly_increment_percent / 100.0)

    final_corpus = balance
    profit = final_corpus - total_deposits
    growth_percent = (profit / total_deposits * 100.0) if total_deposits > 0 else 0.0

    summary = {
        "final_corpus": round(final_corpus, 2),
        "total_deposits": round(total_deposits, 2),
        "total_earnings": round(total_earnings, 2),
        "profit": round(profit, 2),
        "growth_percent": round(growth_percent, 2),
        # formatted values
        "final_corpus_formatted": format_cr_lac(final_corpus),
        "total_deposits_formatted": format_cr_lac(total_deposits),
        "total_earnings_formatted": format_cr_lac(total_earnings),
        "profit_formatted": format_cr_lac(profit)
    }

    return rows, summary


@app.get("/calculate-investment", response_model=InvestmentResponse)
async def calculate_investment(
    coverage_percent: float = Query(..., ge=0.1, le=100, description="Index coverage percentage (0.1-100)"),
    investment_amount: float = Query(..., ge=1000, description="Investment amount in PKR (minimum 1000)")
):
    """
    Calculate optimal investment allocation for KSE-100 index
    
    Parameters:
    - coverage_percent: Percentage of KSE-100 index to cover (0.1-100)
    - investment_amount: Total amount to invest in PKR (minimum 1000)
    """
    try:
        # Update prices first
        price_update_success, price_message = update_prices_api()
        
        # Calculate investment allocation
        success, results, summary, selected_companies, message = calculate_investment_api(
            coverage_percent, investment_amount
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        response_message = message
        if price_update_success:
            response_message += f" | {price_message}"
        else:
            response_message += f" | Price update warning: {price_message}"

        return InvestmentResponse(
            success=True,
            message=response_message,
            investment_plan=results,
            summary=summary,
            selected_companies=selected_companies,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# --- SIP endpoint ---
@app.get("/sip", response_model=SIPResponse)
async def sip(
    initial_balance: float = Query(0, ge=0, description="Initial lump-sum investment at Year 0"),
    years: int = Query(..., ge=1, le=60, description="Number of years to invest"),
    annual_interest_rate: float = Query(..., gt=0, description="Annual return rate in percent (e.g., 16 for 16%)"),
    monthly_investment: float = Query(..., ge=0, description="Monthly SIP amount for Year 1"),
    yearly_increment_percent: float = Query(0, ge=0, description="Annual percentage increase in monthly SIP")
):
    """
    SIP calculator with monthly compounding, yearly SIP increment, and optional Year 0 initial investment.

    Returns rows with: year, year_deposits, earnings_this_year, total_deposits, accrued_earnings, net_balance.
    """
    try:
        rows, summary = compute_sip_api(
            initial_balance=initial_balance,
            years=years,
            annual_interest_rate=annual_interest_rate,
            monthly_investment=monthly_investment,
            yearly_increment_percent=yearly_increment_percent
        )
        return SIPResponse(
            success=True,
            rows=rows,
            summary=summary,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error computing SIP: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
