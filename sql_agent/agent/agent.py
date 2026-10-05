import os
import sys

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain.agents import create_agent

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.sql_tool import run_sql as _run_sql, get_schema
from agent.router import route, warmup

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    sys.exit("ERROR: set GROQ_API_KEY in .env (free key at console.groq.com)")


@tool
def run_sql(query: str) -> str:
    """Execute a read-only SQL SELECT query against the air-quality database and
    return the results as text. Only SELECT queries are allowed. On an error you
    get a message starting with 'ERROR:' - read it, fix the SQL, and try again."""
    return _run_sql(query)


SYSTEM_PROMPT = f"""You are a data analyst for an India air-quality database.
Answer the user's question by writing SQLite SQL and calling the run_sql tool.

Database schema:
{get_schema()}

Notes:
- 'pm25' and 'pm10' are the parameter values in the sensors table; join
  measurements -> sensors -> locations to get city-level data.
- Some locations have a blank city ('') where it couldn't be determined.
- Always base your final answer on the actual query result. If a query returns
  'ERROR:', fix the SQL and retry. Give a concise, direct answer with the number
  or name the user asked for.
"""

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
agent = create_agent(llm, tools=[run_sql], system_prompt=SYSTEM_PROMPT)

warmup()


def ask(question: str) -> str:
    match = route(question)
    hint = (
        f"A similar known question is: {match['question']}\n"
        f"Suggested approach: {match['hint']}\n\n"
        f"Question: {question}"
    )
    result = agent.invoke({"messages": [{"role": "user", "content": hint}]})
    return result["messages"][-1].content


if __name__ == "__main__":
    q = "Which city has the highest average PM2.5?"
    print("Q:", q)
    print("A:", ask(q))
