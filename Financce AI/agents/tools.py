import json
from datetime import datetime
from typing import List

import yfinance as yf
from langchain.tools import Tool
from langchain_community.tools.tavily_search import TavilySearchResults


class FinancialTools:
    def __init__(self, tavily_api_key: str):
        self.tavily_search = TavilySearchResults(api_key=tavily_api_key)

    def create_budget_planner(self) -> Tool:
        def budget_planner(input_str: str) -> str:
            """Create a personalized budget plan with advanced features"""
            try:
                # Handle empty or invalid input
                if not input_str or input_str.strip() == "":
                    input_str = '{"income": 5000, "expenses": {}}'

                # Try to parse JSON, if it fails, try to extract values from text
                try:
                    data = json.loads(input_str)
                except json.JSONDecodeError:
                    # Fallback: extract income and expenses from text
                    import re

                    income_match = re.search(r"(\$?[\d,]+(?:\.\d{2})?)", input_str)
                    income = (
                        float(income_match.group(1).replace("$", "").replace(",", ""))
                        if income_match
                        else 5000
                    )
                    data = {"income": income, "expenses": {}}

                income = data.get("income", 5000)
                expenses = data.get("expenses", {})
                goals = data.get("savings_goals", {})
                debt = data.get("debt", {})

                # Calculate budget allocations using 50/30/20 rule
                needs = income * 0.5
                wants = income * 0.3
                savings = income * 0.2

                total_expenses = sum(expenses.values())
                remaining = income - total_expenses

                # Debt analysis
                total_debt = sum(debt.values()) if debt else 0
                debt_to_income = (total_debt / income * 100) if income > 0 else 0

                # Emergency fund calculation (3-6 months of expenses)
                emergency_fund_needed = total_expenses * 6
                emergency_fund_goal = goals.get("emergency_fund", 0)

                # Calculate actual savings potential
                debt_payments = debt.get("monthly_payments", 0)
                available_for_savings = remaining - debt_payments

                budget_plan = {
                    "monthly_income": income,
                    "recommended_allocation": {
                        "needs": needs,
                        "wants": wants,
                        "savings": savings,
                    },
                    "current_expenses": expenses,
                    "total_expenses": total_expenses,
                    "remaining_budget": remaining,
                    "savings_rate": (available_for_savings / income * 100)
                    if income > 0
                    else 0,
                    "debt_analysis": {
                        "total_debt": total_debt,
                        "debt_to_income_ratio": debt_to_income,
                        "monthly_payments": debt_payments,
                    },
                    "emergency_fund": {
                        "recommended": emergency_fund_needed,
                        "current": emergency_fund_goal,
                        "progress": (emergency_fund_goal / emergency_fund_needed * 100)
                        if emergency_fund_needed > 0
                        else 0,
                    },
                    "savings_optimization": {
                        "available_monthly": available_for_savings,
                        "annual_savings_potential": available_for_savings * 12,
                    },
                    "recommendations": [],
                }

                # Enhanced recommendations
                if available_for_savings < savings:
                    budget_plan["recommendations"].append(
                        f"Increase savings by ${savings - available_for_savings:.2f}/month to reach 20% goal"
                    )

                if debt_to_income > 36:
                    budget_plan["recommendations"].append(
                        f"High debt-to-income ratio ({debt_to_income:.1f}%). Consider debt consolidation."
                    )

                if emergency_fund_goal < emergency_fund_needed:
                    monthly_needed = (emergency_fund_needed - emergency_fund_goal) / 12
                    budget_plan["recommendations"].append(
                        f"Build emergency fund: save ${monthly_needed:.2f}/month for 12 months"
                    )

                # Expense optimization suggestions
                largest_expense = (
                    max(expenses.items(), key=lambda x: x[1]) if expenses else None
                )
                if largest_expense and largest_expense[1] > income * 0.35:
                    budget_plan["recommendations"].append(
                        f"Your {largest_expense[0]} expense (${largest_expense[1]:.2f}) is high. Consider cost reduction."
                    )

                return json.dumps(budget_plan, indent=2)
            except Exception as e:
                return f"Error creating budget plan: {str(e)}"

        return Tool(
            name="budget_planner",
            description="Create personalized budget plans with income and expense analysis",
            func=budget_planner,
        )

    def create_investment_analyzer(self) -> Tool:
        def investment_analyzer(symbol: str) -> str:
            """Analyze stocks with advanced metrics, sector comparison, and risk assessment"""
            try:
                stock = yf.Ticker(symbol.upper())
                info = stock.info
                hist = stock.history(period="1y")  # Reduced from 2y to 1y for speed

                if hist.empty:
                    return f"No data available for {symbol}"

                # Calculate key metrics
                current_price = info.get("currentPrice", hist["Close"].iloc[-1])
                pe_ratio = info.get("trailingPE", "N/A")
                pb_ratio = info.get("priceToBook", "N/A")
                dividend_yield = (
                    info.get("dividendYield", 0) * 100
                    if info.get("dividendYield")
                    else 0
                )
                market_cap = info.get("marketCap", "N/A")
                beta = info.get("beta", "N/A")
                sector = info.get("sector", "Unknown")
                industry = info.get("industry", "Unknown")

                # Advanced technical indicators
                sma_20 = hist["Close"].rolling(window=20).mean().iloc[-1]
                sma_50 = (
                    hist["Close"].rolling(window=50).mean().iloc[-1]
                    if len(hist) >= 50
                    else None
                )
                sma_200 = (
                    hist["Close"].rolling(window=200).mean().iloc[-1]
                    if len(hist) >= 200
                    else None
                )

                # RSI calculation
                delta = hist["Close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]

                # Simplified MACD calculation
                ema_12 = hist["Close"].ewm(span=12).mean()
                ema_26 = hist["Close"].ewm(span=26).mean()
                macd = ema_12 - ema_26
                macd_signal = macd.ewm(span=9).mean()

                # Simplified Bollinger Bands (only what we need)
                bb_middle = hist["Close"].rolling(window=20).mean()
                bb_std_dev = hist["Close"].rolling(window=20).std()
                bb_upper = bb_middle + (bb_std_dev * 2)
                bb_lower = bb_middle - (bb_std_dev * 2)

                # Simplified volatility analysis
                volatility_30d = (
                    hist["Close"].pct_change().rolling(30).std().iloc[-1] * 100
                )

                # Value at Risk (VaR) - 5% level
                returns = hist["Close"].pct_change().dropna()
                var_5 = returns.quantile(0.05) * 100

                # Performance metrics
                price_1m = hist["Close"].iloc[-22] if len(hist) >= 22 else None
                price_3m = hist["Close"].iloc[-66] if len(hist) >= 66 else None
                price_6m = hist["Close"].iloc[-132] if len(hist) >= 132 else None
                price_1y = hist["Close"].iloc[-252] if len(hist) >= 252 else None

                performance = {}
                if price_1m:
                    performance["1_month"] = (current_price - price_1m) / price_1m * 100
                if price_3m:
                    performance["3_month"] = (current_price - price_3m) / price_3m * 100
                if price_6m:
                    performance["6_month"] = (current_price - price_6m) / price_6m * 100
                if price_1y:
                    performance["1_year"] = (current_price - price_1y) / price_1y * 100

                # Sharpe ratio calculation (using risk-free rate of 4%)
                risk_free_rate = 0.04
                mean_return = returns.mean() * 252
                return_std = returns.std() * (252**0.5)
                sharpe_ratio = (
                    (mean_return - risk_free_rate) / return_std if return_std > 0 else 0
                )

                # Risk assessment
                risk_score = 0
                risk_factors = []

                if volatility_30d > 30:
                    risk_score += 2
                    risk_factors.append("High volatility (>30%)")
                elif volatility_30d > 20:
                    risk_score += 1
                    risk_factors.append("Moderate volatility (20-30%)")

                if isinstance(beta, (int, float)):
                    if beta > 1.5:
                        risk_score += 2
                        risk_factors.append(
                            f"High beta ({beta:.2f}) - market sensitive"
                        )
                    elif beta > 1.2:
                        risk_score += 1
                        risk_factors.append(f"Above-average beta ({beta:.2f})")

                if var_5 < -5:
                    risk_score += 2
                    risk_factors.append(f"High downside risk (VaR: {var_5:.1f}%)")

                # Enhanced recommendation logic
                recommendation = "HOLD"
                confidence = 50
                reasoning = []

                # Technical analysis
                if current_price < bb_lower.iloc[-1]:
                    recommendation = "BUY"
                    confidence += 20
                    reasoning.append(
                        "Price below Bollinger Band lower bound (oversold)"
                    )
                elif current_price > bb_upper.iloc[-1]:
                    recommendation = "SELL"
                    confidence += 15
                    reasoning.append(
                        "Price above Bollinger Band upper bound (overbought)"
                    )

                # RSI analysis
                if rsi < 30:
                    if recommendation != "SELL":
                        recommendation = "BUY"
                    confidence += 15
                    reasoning.append(f"RSI oversold ({rsi:.1f})")
                elif rsi > 70:
                    if recommendation != "BUY":
                        recommendation = "SELL"
                    confidence += 10
                    reasoning.append(f"RSI overbought ({rsi:.1f})")

                # MACD analysis
                if (
                    macd.iloc[-1] > macd_signal.iloc[-1]
                    and macd.iloc[-2] <= macd_signal.iloc[-2]
                ):
                    if recommendation != "SELL":
                        recommendation = "BUY"
                    confidence += 10
                    reasoning.append("MACD bullish crossover")

                # Fundamental analysis
                if isinstance(pe_ratio, (int, float)):
                    if pe_ratio < 15:
                        confidence += 10
                        reasoning.append("Low P/E ratio suggests undervaluation")
                    elif pe_ratio > 30:
                        confidence -= 5
                        reasoning.append("High P/E ratio suggests overvaluation")

                # Risk adjustment
                if risk_score >= 4:
                    if recommendation == "BUY":
                        recommendation = "HOLD"
                    confidence -= 15
                    reasoning.append("High risk profile suggests caution")

                analysis = {
                    "symbol": symbol.upper(),
                    "company_name": info.get("longName", symbol),
                    "sector": sector,
                    "industry": industry,
                    "current_price": f"${current_price:.2f}",
                    "market_cap": f"${market_cap:,.0f}"
                    if isinstance(market_cap, (int, float))
                    else "N/A",
                    "fundamental_metrics": {
                        "pe_ratio": pe_ratio,
                        "pb_ratio": pb_ratio,
                        "dividend_yield": f"{dividend_yield:.2f}%",
                        "beta": beta,
                        "sharpe_ratio": f"{sharpe_ratio:.2f}",
                    },
                    "technical_indicators": {
                        "sma_20": f"${sma_20:.2f}",
                        "sma_50": f"${sma_50:.2f}" if sma_50 else "N/A",
                        "sma_200": f"${sma_200:.2f}" if sma_200 else "N/A",
                        "rsi": f"{rsi:.1f}",
                        "macd": f"{macd.iloc[-1]:.2f}",
                        "bollinger_position": "Lower"
                        if current_price < bb_lower.iloc[-1]
                        else "Upper"
                        if current_price > bb_upper.iloc[-1]
                        else "Middle",
                    },
                    "risk_assessment": {
                        "volatility_30d": f"{volatility_30d:.1f}%",
                        "value_at_risk_5%": f"{var_5:.1f}%",
                        "risk_score": f"{risk_score}/6",
                        "risk_factors": risk_factors,
                        "risk_level": "Low"
                        if risk_score <= 1
                        else "Medium"
                        if risk_score <= 3
                        else "High",
                    },
                    "price_levels": {
                        "52_week_high": f"${info.get('fiftyTwoWeekHigh', 'N/A')}",
                        "52_week_low": f"${info.get('fiftyTwoWeekLow', 'N/A')}",
                    },
                    "performance": {k: f"{v:.1f}%" for k, v in performance.items()},
                    "recommendation": {
                        "action": recommendation,
                        "confidence": f"{min(max(confidence, 20), 95)}%",
                        "reasoning": reasoning,
                        "target_allocation": "5-10%"
                        if recommendation == "BUY"
                        else "0-5%"
                        if recommendation == "SELL"
                        else "3-7%",
                    },
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                return json.dumps(analysis, indent=2)
            except Exception as e:
                return f"Error analyzing {symbol}: {str(e)}"

        return Tool(
            name="investment_analyzer",
            description="Analyze stocks and provide investment recommendations",
            func=investment_analyzer,
        )

    def create_market_trends_analyzer(self) -> Tool:
        def market_trends(query: str) -> str:
            """Get comprehensive real-time market trends, news, and sector analysis"""
            try:
                # Get current year for search queries
                current_year = datetime.now().year

                # Status tracking for API calls
                status_updates = []

                # Optimized single comprehensive search instead of multiple calls
                comprehensive_query = f"stock market {query} trends analysis financial news {current_year} latest"

                # Get primary market information
                status_updates.append(
                    "🔍 Fetching latest market news via Tavily Search API..."
                )
                market_news = self.tavily_search.run(comprehensive_query)
                status_updates.append("✅ Market news retrieved successfully")

                # Quick market indices check (reduced to just S&P 500 and NASDAQ for speed)
                index_data = {}
                market_sentiment = {"overall": "Unknown", "note": "Limited data"}

                try:
                    status_updates.append(
                        "📊 Fetching market indices via Yahoo Finance API..."
                    )
                    # Fetch only key indices for speed
                    key_indices = ["^GSPC", "^IXIC"]  # S&P 500, NASDAQ

                    for index in key_indices:
                        index_names = {"^GSPC": "S&P 500", "^IXIC": "NASDAQ"}
                        status_updates.append(
                            f"📈 Getting {index_names[index]} data..."
                        )

                        ticker = yf.Ticker(index)
                        hist = ticker.history(period="2d")  # Reduced period for speed
                        if not hist.empty:
                            current = hist["Close"].iloc[-1]
                            prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
                            change = ((current - prev) / prev * 100) if prev != 0 else 0

                            index_data[index_names[index]] = {
                                "current": round(current, 2),
                                "change_pct": round(change, 2),
                                "direction": "📈"
                                if change > 0
                                else "📉"
                                if change < 0
                                else "➡️",
                            }

                    status_updates.append(
                        "✅ Market indices data retrieved successfully"
                    )

                    # Simple sentiment based on available indices
                    if index_data:
                        status_updates.append("🧠 Analyzing market sentiment...")
                        positive_count = sum(
                            1 for data in index_data.values() if data["change_pct"] > 0
                        )
                        total_count = len(index_data)

                        if positive_count >= total_count * 0.75:
                            sentiment = "🟢 Bullish"
                        elif positive_count <= total_count * 0.25:
                            sentiment = "🔴 Bearish"
                        else:
                            sentiment = "🟡 Mixed"

                        market_sentiment = {
                            "overall": sentiment,
                            "summary": f"{positive_count}/{total_count} indices positive",
                        }
                        status_updates.append("✅ Market sentiment analysis completed")

                except Exception as index_error:
                    status_updates.append(
                        f"❌ Error fetching market indices: {str(index_error)}"
                    )
                    index_data = {
                        "error": f"Index data unavailable: {str(index_error)}"
                    }

                # Extract key themes from search results
                status_updates.append("🔍 Analyzing key market themes...")
                key_themes = _extract_key_themes(market_news)
                status_updates.append("✅ Theme analysis completed")

                # Format output for better readability
                def format_search_results(results):
                    """Convert search results to readable format"""
                    if isinstance(results, list):
                        # Extract key information from search results
                        formatted = []
                        for item in results[:3]:  # Limit to top 3 results
                            if isinstance(item, dict):
                                title = item.get("title", "No title")
                                content = item.get(
                                    "content", item.get("snippet", "No content")
                                )
                                formatted.append(f"• {title}: {content[:200]}...")
                            else:
                                formatted.append(f"• {str(item)[:200]}...")
                        return "\n".join(formatted)
                    elif isinstance(results, str):
                        return (
                            results[:1000] + "..." if len(results) > 1000 else results
                        )
                    else:
                        return str(results)[:1000]

                status_updates.append("📋 Compiling final analysis report...")

                # Compile streamlined analysis
                analysis = {
                    "query": query,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "api_execution_log": status_updates,
                    "market_summary": format_search_results(market_news),
                    "key_indices": index_data,
                    "market_sentiment": market_sentiment,
                    "key_themes": key_themes,
                    "note": "Real-time API status tracking enabled",
                }

                status_updates.append("✅ Analysis report completed successfully")

                return json.dumps(analysis, indent=2, ensure_ascii=False)

            except Exception as e:
                return f"Error fetching market analysis: {str(e)}"

        def _extract_key_themes(news_text) -> list:
            """Extract key themes from market news"""
            themes = []
            keywords = {
                "earnings": ["earnings", "quarterly results", "revenue", "profit"],
                "fed_policy": [
                    "federal reserve",
                    "interest rates",
                    "fed",
                    "monetary policy",
                ],
                "inflation": ["inflation", "cpi", "price increases", "cost of living"],
                "geopolitical": ["geopolitical", "war", "trade war", "sanctions"],
                "technology": [
                    "ai",
                    "artificial intelligence",
                    "tech stocks",
                    "innovation",
                ],
                "recession": ["recession", "economic downturn", "market crash"],
            }

            # Handle both string and list inputs
            if isinstance(news_text, list):
                # Convert list to string
                news_text = " ".join(str(item) for item in news_text)
            elif not isinstance(news_text, str):
                # Convert other types to string
                news_text = str(news_text)

            news_lower = news_text.lower()
            for theme, terms in keywords.items():
                if any(term in news_lower for term in terms):
                    themes.append(theme.replace("_", " ").title())

            return themes[:5]  # Return top 5 themes

        return Tool(
            name="market_trends",
            description="Get real-time market trends and financial news",
            func=market_trends,
        )

    def create_portfolio_analyzer(self) -> Tool:
        def portfolio_analyzer(input_str: str) -> str:
            """Analyze portfolio performance and diversification"""
            try:
                import re

                # Try to parse as JSON first (from OpenAI extraction)
                total_investment = 0
                holdings_info = []
                
                try:
                    # First try to parse as JSON
                    data = json.loads(input_str)
                    if isinstance(data, dict):
                        holdings_info = data.get("holdings", [])
                        total_investment = data.get("total_investment", 0)
                except:
                    # If JSON parsing fails, extract from natural language
                    pass

                # If no JSON data found, extract from natural language using regex
                if not holdings_info:
                    # Extract investment amount using improved patterns
                    def extract_investment_amount(text):
                        patterns = [
                            r"(?:invested|investment|total|have)\s*(?:of)?\s*(?:\$)?(\d+(?:[,\d]*)?(?:\.\d+)?)\s*([KMB]?)\s*(?:USD|dollars?|\$)?",
                            r"(\d+(?:[,\d]*)?(?:\.\d+)?)\s*([KMB]?)\s*(?:USD|dollars?)",
                            r"\$(\d+(?:[,\d]*)?(?:\.\d+)?)\s*([KMB]?)",
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                amount_str = match.group(1).replace(",", "")
                                suffix = match.group(2).upper() if len(match.groups()) > 1 else ""
                                
                                multiplier = {"K": 1000, "M": 1000000, "B": 1000000000}.get(suffix, 1)
                                return float(amount_str) * multiplier
                        return 0

                    if total_investment == 0:
                        total_investment = extract_investment_amount(input_str)

                    # Extract holdings using regex
                    def extract_holdings(text):
                        holdings = []
                        
                        # First try percentage patterns (with % symbol)
                        percentage_patterns = [
                            r"([A-Z]{2,5})\s*[:\s]*(\d+(?:\.\d+)?)%",
                            r"([A-Z]{2,5}):\s*(\d+(?:\.\d+)?)%",
                            r"([A-Z]{2,5})\s+(\d+(?:\.\d+)?)%",
                        ]
                        
                        for pattern in percentage_patterns:
                            matches = re.findall(pattern, text, re.IGNORECASE)
                            if matches:
                                for symbol, percentage in matches:
                                    holdings.append({
                                        "symbol": symbol.upper(),
                                        "percentage": float(percentage)
                                    })
                                return holdings
                        
                        # If no percentages found, try shares patterns (without % symbol)
                        shares_patterns = [
                            r"([A-Z]{2,5})\s*[:\s]*(\d+(?:\.\d+)?)\s*(?!%)",
                            r"([A-Z]{2,5}):\s*(\d+(?:\.\d+)?)\s*(?!%)",
                            r"([A-Z]{2,5})\s+(\d+(?:\.\d+)?)\s*(?!%)",
                        ]
                        
                        for pattern in shares_patterns:
                            matches = re.findall(pattern, text, re.IGNORECASE)
                            if matches:
                                for symbol, shares in matches:
                                    holdings.append({
                                        "symbol": symbol.upper(),
                                        "shares": float(shares)
                                    })
                                return holdings
                        
                        return holdings

                    holdings_info = extract_holdings(input_str)
                
                # If no valid holdings found, return early to avoid using this tool
                if not holdings_info:
                    # Debug: show what we received
                    return f"Portfolio analyzer debug - received input: {input_str[:200]}... No holdings found. Please provide portfolio details like 'AAPL 40%, MSFT 30%' or JSON format."

                portfolio_data = []
                total_calculated_value = 0

                # Process each holding
                for holding in holdings_info:
                    symbol = holding.get("symbol", "")
                    percentage = holding.get("percentage", 0)
                    shares = holding.get("shares", None)

                    if not symbol:
                        continue

                    try:
                        # Get current stock price
                        stock = yf.Ticker(symbol)
                        hist = stock.history(period="1d")

                        if not hist.empty:
                            current_price = hist["Close"].iloc[-1]

                            if shares is not None:
                                # Shares-based calculation
                                value = current_price * shares
                                allocation_percentage = percentage
                            else:
                                # Percentage-based calculation
                                value = total_investment * (percentage / 100)
                                allocation_percentage = percentage
                                shares = value / current_price if current_price > 0 else 0

                            total_calculated_value += value

                            portfolio_data.append(
                                {
                                    "symbol": symbol,
                                    "shares": round(shares, 2),
                                    "current_price": f"${current_price:.2f}",
                                    "value": value,
                                    "allocation": allocation_percentage,
                                }
                            )
                    except Exception:
                        # Skip if can't get data but add placeholder
                        if percentage > 0:
                            value = total_investment * (percentage / 100)
                            portfolio_data.append(
                                {
                                    "symbol": symbol,
                                    "shares": "N/A",
                                    "current_price": "N/A",
                                    "value": value,
                                    "allocation": percentage,
                                }
                            )

                # For percentage-based portfolios, use the original total investment
                # For share-based portfolios, use calculated value
                final_total_value = (
                    total_investment 
                    if total_investment > 0 and any(h.get("percentage", 0) > 0 for h in holdings_info)
                    else total_calculated_value
                )

                # Analysis and recommendations
                analysis = {
                    "total_portfolio_value": f"${final_total_value:.2f}",
                    "number_of_holdings": len(portfolio_data),
                    "holdings": portfolio_data,
                    "recommendations": [],
                }

                # Diversification recommendations
                if len(portfolio_data) < 5:
                    analysis["recommendations"].append(
                        "Consider diversifying with more holdings"
                    )

                if portfolio_data:
                    max_allocation = max(item["allocation"] for item in portfolio_data)
                    if max_allocation > 40:
                        analysis["recommendations"].append(
                            f"High concentration risk: largest holding is {max_allocation:.1f}%"
                        )
                    elif max_allocation > 30:
                        analysis["recommendations"].append(
                            f"Moderate concentration risk: largest holding is {max_allocation:.1f}%"
                        )

                # Check if allocations add up to 100%
                total_allocation = sum(item["allocation"] for item in portfolio_data)
                if abs(total_allocation - 100) > 5:
                    analysis["recommendations"].append(
                        f"Portfolio allocations total {total_allocation:.1f}% - consider rebalancing to 100%"
                    )

                # Sector diversification recommendation
                if len(portfolio_data) == 3:
                    analysis["recommendations"].append(
                        "Consider adding holdings from different sectors (healthcare, utilities, financials)"
                    )

                return json.dumps(analysis, indent=2)

            except Exception as e:
                return f"Error analyzing portfolio: {str(e)}"

        return Tool(
            name="portfolio_analyzer",
            description="Analyze portfolio performance and diversification. Input should include holdings like: [{'symbol': 'AAPL', 'shares': 100}]",
            func=portfolio_analyzer,
        )

    def get_all_tools(self) -> List[Tool]:
        return [
            self.create_budget_planner(),
            self.create_investment_analyzer(),
            self.create_market_trends_analyzer(),
            self.create_portfolio_analyzer(),
        ]
