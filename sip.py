import pandas as pd

# Helper to format amounts in crore/lakh for summary
def format_cr_lac(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    amt = abs(amount)
    if amt >= 10_000_000:  # 1 crore
        return f"{sign}{amt/10_000_000:.2f} cr"
    if amt >= 100_000:  # 1 lakh
        return f"{sign}{amt/100_000:.2f} lac"
    return f"{sign}{amt:,.2f}"

def sip_calculator(initial_balance, years, annual_interest_rate, monthly_investment, yearly_increment_percent):
    rows = []
    opening_balance = initial_balance
    total_invested = initial_balance
    total_earnings = 0
    monthly_rate = annual_interest_rate / 12 / 100

    # Add Year 0 row only if there's an initial investment
    if initial_balance > 0:
        rows.append({
            "Year": 0,
            "Deposits": round(initial_balance, 2),
            "Earnings": 0.00,
            "Total Deposits": round(initial_balance, 2),
            "Accrued Earnings": 0.00,
            "Balance": round(initial_balance, 2)
        })

    for year in range(1, years + 1):
        # Calculate yearly deposits and earnings
        year_deposits = 0
        year_earnings = 0
        
        for month in range(1, 13):
            # Apply monthly interest on starting balance (deposit earns from next month)
            monthly_interest = opening_balance * monthly_rate
            opening_balance += monthly_interest
            year_earnings += monthly_interest
            
            # Add monthly SIP at end of the month
            opening_balance += monthly_investment
            year_deposits += monthly_investment
        
        total_invested += year_deposits
        total_earnings += year_earnings

        rows.append({
            "Year": year,
            "Deposits": round(year_deposits, 2),
            "Earnings": round(year_earnings, 2),
            "Total Deposits": round(total_invested, 2),
            "Accrued Earnings": round(total_earnings, 2),
            "Balance": round(opening_balance, 2)
        })

        # Increase monthly investment for next year
        monthly_investment += monthly_investment * (yearly_increment_percent / 100)

    df = pd.DataFrame(rows)

    # Summary
    final_corpus = opening_balance
    profit = final_corpus - total_invested
    growth_percent = (profit / total_invested) * 100

    print("\nSIP Calculation Table:\n")
    print(df.to_string(index=False))
    print("\nSummary:")
    print(f"Total Invested: {format_cr_lac(total_invested)}")
    print(f"Total Profit: {format_cr_lac(profit)}")
    print(f"Final Corpus: {format_cr_lac(final_corpus)}")
    print(f"Growth: {growth_percent:.2f}%")

# Example run
if __name__ == "__main__":
    initial_balance = float(input("Enter initial investment (PKR): "))
    years = int(input("Enter number of years: "))
    annual_interest_rate = float(input("Enter annual interest rate (%): "))
    monthly_investment = float(input("Enter monthly investment (PKR): "))
    yearly_increment_percent = float(input("Enter yearly increment in monthly investment (%): "))
    
    sip_calculator(initial_balance, years, annual_interest_rate, monthly_investment, yearly_increment_percent)
