import pandas as pd
import math
import requests

# File path to your Excel file
EXCEL_FILE = "kse100.xlsx"

# PSX API endpoint
API_URL = "https://psxterminal.com/api/market-data?market=REG"

def update_prices():
    """
    Update stock prices from PSX API
    """
    print("🔄 Updating stock prices from PSX API...")
    
    try:
        # Step 1: Load Excel
        df = pd.read_excel(EXCEL_FILE)
        print(f"✅ Loaded {len(df)} companies from {EXCEL_FILE}")

        # Ensure 'symbol' column exists
        if 'symbol' not in df.columns:
            raise ValueError("Excel file must contain a 'symbol' column")

        # Step 2: Fetch PSX API data
        response = requests.get(API_URL)
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}")
        
        market_data = response.json()

        # Step 3: Access actual symbols dictionary inside "data"
        stocks = market_data.get("data", {})

        # Step 4: Create price lookup dictionary {symbol_upper: price}
        price_lookup = {sym.upper(): stock["price"]
                        for sym, stock in stocks.items()
                        if isinstance(stock, dict) and "price" in stock}

        # Step 5: Create/Update 'price' column
        df['price'] = [
            price_lookup.get(str(sym).upper().strip(), None)
            for sym in df['symbol']
        ]

        # Step 6: Save updated Excel file
        df.to_excel(EXCEL_FILE, index=False)

        # Count successful price updates
        updated_count = df['price'].notna().sum()
        print(f"✅ Updated prices for {updated_count}/{len(df)} companies")
        
        if updated_count < len(df):
            missing_symbols = df[df['price'].isna()]['symbol'].tolist()
            print(f"⚠️  Could not find prices for: {missing_symbols}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating prices: {e}")
        print("📊 Proceeding with existing prices in Excel file...")
        return False

def invest_in_kse100(coverage_percent, investment_amount):
    """
    Calculate optimal investment allocation for KSE-100 index
    """
    print(f"\n🎯 Calculating investment plan for {coverage_percent}% coverage with {investment_amount:,.0f} PKR")
    print("-" * 60)
    
    # Step 1: Load Excel file
    df = pd.read_excel(EXCEL_FILE)

    # Ensure necessary columns exist
    if not all(col in df.columns for col in ['symbol', 'weight', 'price']):
        raise ValueError("Excel file must contain columns: symbol, weight, price")

    # Step 2: Select companies until cumulative weight >= coverage_percent
    df['cum_weight'] = df['weight'].cumsum()
    target_coverage_decimal = coverage_percent / 100
    
    # Find the first row where cumulative weight >= target coverage
    coverage_reached_idx = df[df['cum_weight'] >= target_coverage_decimal].index
    
    if len(coverage_reached_idx) > 0:
        # Include all companies up to and including the one that reaches target coverage
        first_coverage_idx = coverage_reached_idx[0]
        selected = df.loc[:first_coverage_idx].copy()
    else:
        # If target coverage exceeds total index weight, select all companies
        selected = df.copy()

    # Step 3: Adjust weights relative to selected subset (normalize to 100%)
    total_selected_weight = selected['weight'].sum()
    selected['adjusted_weight'] = selected['weight'] / total_selected_weight

    print(f"📊 Selected {len(selected)} companies representing {total_selected_weight*100:.2f}% of KSE-100")
    print(f"📈 Selected companies: {', '.join(selected['symbol'].tolist())}")

    # Step 4: Calculate investment per company
    results = []
    total_invested = 0
    leftover_cash = 0

    for _, row in selected.iterrows():
        symbol = row['symbol']
        price = row['price']
        adj_weight = row['adjusted_weight']

        # Skip companies with missing or invalid prices
        if pd.isna(price) or price <= 0:
            print(f"⚠️  {symbol}: No valid price (${price}), skipping")
            continue

        # How much money goes into this stock
        allocation_amount = adj_weight * investment_amount

        # How many whole shares
        shares = math.floor(allocation_amount / price)

        # Actual money invested
        invested_amount = shares * price
        total_invested += invested_amount

        # Leftover from fractional shares
        fractional_cash = allocation_amount - invested_amount
        leftover_cash += fractional_cash

        results.append({
            "symbol": symbol,
            "weight(%)": round(row['weight'] * 100, 2),
            "adjusted_weight(%)": round(adj_weight * 100, 2),
            "price": price,
            "shares": shares,
            "invested_amount": round(invested_amount, 2)
        })

    # Step 5: Calculate remaining cash
    remaining_cash = investment_amount - total_invested

    # Step 6: Output results
    results_df = pd.DataFrame(results)
    
    print("\n📈 INVESTMENT ALLOCATION TABLE")
    print("=" * 80)
    print(results_df.to_string(index=False, formatters={
        'price': lambda x: f"{x:.2f}",
        'shares': lambda x: f"{x:,}",
        'invested_amount': lambda x: f"{x:,.2f}"
    }))
    
    print("\n" + "=" * 80)
    print("💼 INVESTMENT SUMMARY")
    print("=" * 80)
    print(f"💰 Total Investment Amount:  {investment_amount:,.2f} PKR")
    print(f"💵 Total Invested:           {total_invested:,.2f} PKR")
    print(f"🏦 Remaining Cash:           {remaining_cash:,.2f} PKR")
    print(f"📊 Investment Efficiency:    {(total_invested/investment_amount)*100:.2f}%")
    
    successful_investments = len([r for r in results if r['shares'] > 0])
    print(f"🎯 Companies Invested In:    {successful_investments}/{len(selected)}")
    
    return results_df, remaining_cash

def main():
    """
    Main function: Update prices then calculate investment
    """
    print("🚀 KSE-100 Index Investment Calculator")
    print("=" * 50)
    
    # Step 1: Update prices from API
    update_prices()
    
    # Step 2: Get user inputs
    print("\n📝 Investment Parameters:")
    coverage = float(input("Enter index coverage percentage (e.g., 20 for 20%): "))
    investment = float(input("Enter total investment amount (PKR): "))
    
    # Step 3: Calculate and display investment plan
    invest_in_kse100(coverage, investment)

if __name__ == "__main__":
    main()
