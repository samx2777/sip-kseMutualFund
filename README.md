The kse1.py file contains the code to scrap live data of prices of kse100 stocks all 100 stocks are fetched along with live prices in kse100.xlsx file along with weightage based portfolio designer a system that based on weightage selected by user givres companies and exact shares to buy based on user entered investment amount and index weightage percentage to cover.

API GET for custom mutual fund creation => http://localhost:8000/calculate-investment?coverage_percent=20&investment_amount=100000

This api takes user entered weightage cover percentage and investment amount to give details of stocks to buys along with their quantity to buy.

# SIP CALCULATION TABLE Feature.

sip.py contains the implementation code for sip calculator takes initial balance the initial invested amount , years to invest , annuat interest rate the gain percentage , monthly investment amount , per year increase in monthly investment amount percentage.

API GET for SIP calculation => http://localhost:8000/sip?initial_balance=0&years=30&annual_interest_rate=16&monthly_investment=10000&yearly_increment_percent=10