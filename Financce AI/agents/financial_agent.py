import json
import operator
import re
from typing import Annotated, List, Tuple, TypedDict, Union

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.tools import Tool
from langchain_openai import ChatOpenAI


class AgentState(TypedDict):
    messages: Annotated[List[Union[HumanMessage, AIMessage]], operator.add]
    context: dict


class FinancialAdvisorAgent:
    def __init__(self, tools: List[Tool], openai_api_key: str):
        self.tools = tools
        self.llm = ChatOpenAI(
            api_key=openai_api_key, model="gpt-4.1-mini-2025-04-14", temperature=0.7
        )
        self.tools_by_name = {tool.name: tool for tool in tools}

        # Create agent with tools
        self.system_prompt = """You are a professional financial advisor AI assistant with access to specialized tools.

Available tools:
- budget_planner: Use when users ask about budgeting, income allocation, or expense planning. Input should be JSON with 'income' and 'expenses' keys.
- investment_analyzer: Use when users ask about specific stocks or investments. Input should be a stock symbol (e.g., AAPL).
- market_trends: Use when users ask about market trends or financial news. Input should be a search query.
- portfolio_analyzer: Use when users want to analyze their portfolio. Input should be JSON with 'holdings' array.

IMPORTANT: You MUST use these tools when answering financial questions. Do not provide generic advice without using the appropriate tool first.

When a user asks a question:
1. Identify which tool is most appropriate
2. Extract or request the necessary information
3. Use the tool to get specific data
4. Provide advice based on the tool's output"""

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                MessagesPlaceholder(variable_name="messages"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            return_intermediate_steps=True,
        )

    def _extract_tool_usage(self, intermediate_steps):
        """Extract tool usage from intermediate steps"""
        tools_used = []
        tool_results = []

        for action, result in intermediate_steps:
            if hasattr(action, "tool"):
                tools_used.append(action.tool)
                tool_results.append(result)

        # Return the last tool used and its result for backward compatibility
        # But also return all tools and results for multi-tool scenarios
        if tools_used:
            return tools_used[-1], tool_results[-1], tools_used, tool_results
        return None, None, [], []

    def _prepare_tool_input(self, message: str, tool_name: str) -> str:
        """Prepare input for specific tools based on the message"""
        if tool_name == "investment_analyzer":
            # Use OpenAI to extract stock symbol from natural language
            extraction_prompt = f"""Extract the stock symbol from this message: "{message}"

If the user mentions a company name, return the corresponding stock ticker symbol.
If they mention a ticker symbol directly, return that symbol.
If no stock or company is mentioned, return "UNKNOWN".

Examples:
- "Tell me about NVIDIA" -> "NVDA"
- "Analyze AAPL stock" -> "AAPL" 
- "How is Tesla doing?" -> "TSLA"
- "What about Microsoft stock?" -> "MSFT"

Return only the stock symbol, nothing else."""

            try:
                response = self.llm.invoke([
                    SystemMessage(content="You are a stock symbol extraction assistant. Return only the ticker symbol."),
                    HumanMessage(content=extraction_prompt)
                ])
                
                extracted_symbol = response.content.strip().upper()
                if extracted_symbol and extracted_symbol != "UNKNOWN":
                    return extracted_symbol
                
            except Exception:
                pass
            
            # Fallback to regex if LLM fails
            symbols = re.findall(r"\b[A-Z]{2,5}\b", message)
            return symbols[0] if symbols else ""

        elif tool_name == "budget_planner":
            # Use OpenAI to extract budget information from natural language
            extraction_prompt = f"""Extract budget information from this message: "{message}"

Extract:
1. Monthly income (if mentioned)
2. Expenses by category (rent, food, utilities, transportation, etc.)

Return as JSON format:
{{"income": 5000, "expenses": {{"rent": 1500, "food": 500, "utilities": 200}}}}

If income is not mentioned, use 5000 as default.
If no expenses are mentioned, return empty expenses object.

Examples:
- "I make $6000 monthly, rent is $1800, food $600" -> {{"income": 6000, "expenses": {{"rent": 1800, "food": 600}}}}
- "Help with budget, income 4500, utilities 150" -> {{"income": 4500, "expenses": {{"utilities": 150}}}}

Return only valid JSON, nothing else."""

            try:
                response = self.llm.invoke([
                    SystemMessage(content="You are a budget data extraction assistant. Return only valid JSON."),
                    HumanMessage(content=extraction_prompt)
                ])
                
                # Try to parse the JSON response
                extracted_data = response.content.strip()
                # Remove any markdown formatting
                if extracted_data.startswith("```"):
                    extracted_data = extracted_data.split("\n")[1:-1]
                    extracted_data = "\n".join(extracted_data)
                
                # Validate JSON
                json.loads(extracted_data)
                return extracted_data
                
            except Exception:
                pass
            
            # Fallback to regex extraction
            income_match = re.search(r"\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:monthly\s*)?income", message, re.I)
            income = float(income_match.group(1).replace(",", "")) if income_match else 5000
            
            expenses = {}
            expense_patterns = [
                (r"rent:?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", "rent"),
                (r"food:?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", "food"),
                (r"utilities:?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", "utilities"),
                (r"transportation:?\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", "transportation"),
            ]
            
            for pattern, category in expense_patterns:
                match = re.search(pattern, message, re.I)
                if match:
                    expenses[category] = float(match.group(1).replace(",", ""))
            
            return json.dumps({"income": income, "expenses": expenses})

        elif tool_name == "portfolio_analyzer":
            # Use OpenAI to extract portfolio information from natural language
            extraction_prompt = f"""Extract portfolio holdings and total investment from this message: "{message}"

Convert the portfolio information to JSON format with holdings array and total investment amount.
Each holding should have symbol and either shares or percentage.

Return format:
{{"holdings": [{{"symbol": "AAPL", "shares": 100}}, {{"symbol": "GOOGL", "percentage": 30}}], "total_investment": 100000}}

Examples:
- "My portfolio: AAPL 100 shares, GOOGL 50 shares" -> {{"holdings": [{{"symbol": "AAPL", "shares": 100}}, {{"symbol": "GOOGL", "shares": 50}}], "total_investment": 0}}
- "I have 40% AAPL, 30% MSFT, 30% TSLA. I have invested total of 100K USD" -> {{"holdings": [{{"symbol": "AAPL", "percentage": 40}}, {{"symbol": "MSFT", "percentage": 30}}, {{"symbol": "TSLA", "percentage": 30}}], "total_investment": 100000}}
- "Portfolio with Apple 200 shares and Microsoft 25%, total investment $50,000" -> {{"holdings": [{{"symbol": "AAPL", "shares": 200}}, {{"symbol": "MSFT", "percentage": 25}}], "total_investment": 50000}}

Important:
- Extract total investment amount if mentioned (convert K=1000, M=1000000)
- If total investment not mentioned, set to 0
- Convert company names to stock symbols (Apple->AAPL, Microsoft->MSFT, Tesla->TSLA, etc.)

If no clear portfolio data is found, return: {{"holdings": [], "total_investment": 0}}

Return only valid JSON, nothing else."""

            try:
                response = self.llm.invoke([
                    SystemMessage(content="You are a portfolio data extraction assistant. Return only valid JSON with holdings array and total_investment field."),
                    HumanMessage(content=extraction_prompt)
                ])
                
                # Try to parse the JSON response
                extracted_data = response.content.strip()
                # Remove any markdown formatting
                if extracted_data.startswith("```"):
                    lines = extracted_data.split("\n")
                    # Find the start and end of JSON content
                    start_idx = 1 if lines[0].startswith("```") else 0
                    end_idx = -1 if lines[-1].startswith("```") or lines[-1] == "```" else len(lines)
                    extracted_data = "\n".join(lines[start_idx:end_idx])
                
                # Validate JSON
                parsed_json = json.loads(extracted_data)
                # Ensure it has the required structure
                if isinstance(parsed_json, dict) and "holdings" in parsed_json:
                    return extracted_data
                else:
                    # If structure is wrong, fall back to regex
                    pass
                
            except Exception:
                pass
            
            # Fallback to returning the original message
            return message

        elif tool_name == "market_trends":
            # Use OpenAI to extract and refine market research query
            extraction_prompt = f"""Convert this user message into an optimized market research query: "{message}"

Create a focused search query that will get the best market trends and financial news results.

Examples:
- "What's happening in tech stocks?" -> "technology stocks market trends latest news 2025"
- "Tell me about the market today" -> "stock market trends today financial news latest"
- "How is the crypto market?" -> "cryptocurrency market trends bitcoin ethereum latest news"
- "What about NVIDIA trends?" -> "NVIDIA NVDA stock market trends analysis latest news"

Return only the optimized search query, nothing else."""

            try:
                response = self.llm.invoke([
                    SystemMessage(content="You are a search query optimization assistant. Return only the optimized search query."),
                    HumanMessage(content=extraction_prompt)
                ])
                
                optimized_query = response.content.strip()
                return optimized_query if optimized_query else message
                
            except Exception:
                pass
            
            # Fallback to returning the original message
            return message

        return message

    def process_message_with_details(
        self, message: str, history: List[dict] = None
    ) -> Tuple[str, str, str, List[str], List[str]]:
        """Process a message and return response, tool used, tool result, and all tools/results"""
        if history is None:
            history = []

        # Check if this is a multi-tool query (contains keywords for multiple tools)
        message_lower = message.lower()
        tool_keywords = {
            "budget_planner": ["budget", "income", "expense", "spending", "allocat", "track", "categoriz"],
            "investment_analyzer": ["stock", "invest", "buy", "sell", "analyze"],
            "portfolio_analyzer": ["portfolio", "holdings", "allocation", "diversif"],
            "market_trends": ["market", "trend", "news", "sector", "economic"]
        }
        
        detected_tools = []
        for tool_name, keywords in tool_keywords.items():
            if any(word in message_lower for word in keywords):
                # Special check for investment analyzer - needs stock symbols
                if tool_name == "investment_analyzer":
                    if re.search(r"\b[A-Z]{2,5}\b", message) or any(word in message_lower for word in ["stock", "invest", "recommend"]):
                        detected_tools.append(tool_name)
                else:
                    detected_tools.append(tool_name)
        
        # If multiple tools detected or complex query, use agent executor
        if len(detected_tools) > 1 or len(message.split()) > 15:
            try:
                result = self.agent_executor.invoke({"input": message, "messages": []})

                tool_used, tool_result, all_tools, all_results = self._extract_tool_usage(
                    result.get("intermediate_steps", [])
                )
                return result["output"], tool_used, tool_result, all_tools, all_results

            except Exception as e:
                return (
                    f"I encountered an error processing your request: {str(e)}",
                    None,
                    None,
                    [],
                    []
                )
        
        # Single tool execution for simple queries
        elif len(detected_tools) == 1:
            selected_tool = detected_tools[0]
            try:
                tool = self.tools_by_name[selected_tool]
                tool_input = self._prepare_tool_input(message, selected_tool)
                
                # Execute the tool
                tool_result = tool.func(tool_input)

                # Generate response based on tool result - optimized for speed
                response_prompt = f"""Based on this {selected_tool.replace('_', ' ')} analysis, provide a concise financial summary for: {message}

Data: {tool_result}

Keep response under 200 words with key insights and 2-3 actionable recommendations."""

                response = self.llm.invoke(
                    [
                        SystemMessage(content="Financial advisor. Be concise and actionable."),
                        HumanMessage(content=response_prompt),
                    ]
                )

                return response.content, selected_tool, tool_result, [selected_tool], [tool_result]

            except Exception as e:
                return f"Error using {selected_tool}: {str(e)}", selected_tool, None, [], []

        # Fallback to agent executor for unclear queries
        else:
            try:
                result = self.agent_executor.invoke({"input": message, "messages": []})

                tool_used, tool_result, all_tools, all_results = self._extract_tool_usage(
                    result.get("intermediate_steps", [])
                )
                return result["output"], tool_used, tool_result, all_tools, all_results

            except Exception as e:
                return (
                    f"I encountered an error processing your request: {str(e)}",
                    None,
                    None,
                    [],
                    []
                )

    def process_message(self, message: str, history: List[dict] = None):
        """Process a user message and return response"""
        response, _, _, _, _ = self.process_message_with_details(message, history)
        return response
    
    def stream_response(self, message: str, tool_result: str, selected_tool: str, response_type: str = "short"):
        """Stream the LLM response in real-time"""
        
        if response_type == "detailed":
            response_prompt = f"""Based on the following comprehensive analysis from the {selected_tool.replace('_', ' ').title()}:

{tool_result}

Provide detailed financial advice to the user addressing their question: {message}

Guidelines:
- Be thorough and comprehensive
- Reference specific data points from the analysis
- Provide clear, actionable recommendations with explanations
- Include multiple scenarios or considerations where relevant
- Use a professional but friendly tone
- Structure your response with clear sections
- Provide context for your recommendations"""

            system_message = "You are a professional financial advisor. Provide comprehensive, detailed advice based on the analysis results. Be thorough and educational."
        else:
            response_prompt = f"""Based on this {selected_tool.replace('_', ' ')} analysis, provide a concise financial summary for: {message}

Data: {tool_result}

Keep response under 200 words with key insights and 2-3 actionable recommendations."""

            system_message = "Financial advisor. Be concise and actionable."

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=response_prompt),
        ]
        
        # Stream the response token by token
        for chunk in self.llm.stream(messages):
            if chunk.content:
                yield chunk.content
