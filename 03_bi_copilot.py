# BUSINESS SCIENCE UNIVERSITY
# PYTHON FOR GENERATIVE AI COURSE
# ML + AI BUSINESS INTELLIGENCE (FLOW CONTROL)
# ***

# Goal: BI Copilot - LangGraph SQL agent for Walmart Sales data
# (table-only, no charts, no Streamlit)

# LIBRARIES

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_classic.chains import create_sql_query_chain
from langgraph.graph import END, StateGraph
from typing import TypedDict, Optional

import pandas as pd
import sqlalchemy as sql
import re
import os
import yaml
from pprint import pprint
from IPython.display import display

# AI SETUP

os.environ["OPENAI_API_KEY"] = yaml.safe_load(open('credentials.yml'))['openai']

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# DATABASE SETUP

PATH_DB = "sqlite:///data/walmart_sales.db"

sql_engine = sql.create_engine(PATH_DB)
conn = sql_engine.connect()

db = SQLDatabase.from_uri(PATH_DB)
print("Tables:", db.get_usable_table_names())
print("\nSchema:\n", db.get_table_info())

# * UTILITIES

def extract_sql_code(text: str):
    if not text:
        return None
    for pat in [
        r"SQLQuery:\s*```sql\s*([\s\S]+?)```",
        r"```sql\s*([\s\S]+?)```",
        r"```[\w]*\s*(SELECT[\s\S]+?)```",
        r"SQLQuery:\s*(SELECT[\s\S]+?)(?:\n\n|$)",
        r"(SELECT[\s\S]+?)(?:;|\n\n|$)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip().rstrip(";")
    return None

# * LANGGRAPH BI AGENT

sql_chain = create_sql_query_chain(llm=llm, db=db, k=int(1e7))


class BIState(TypedDict):
    user_question: str
    sql_query: Optional[str]
    data: Optional[list]


def generate_sql(state):
    print("---GENERATE SQL---")
    raw = sql_chain.invoke({"question": state["user_question"]})
    return {"sql_query": extract_sql_code(raw)}


def execute_sql(state):
    print("---EXECUTE SQL---")
    df = pd.read_sql(state["sql_query"], conn)
    return {"data": df.to_dict(orient="records")}


workflow = StateGraph(BIState)
workflow.add_node("generate_sql", generate_sql)
workflow.add_node("execute_sql", execute_sql)
workflow.set_entry_point("generate_sql")
workflow.add_edge("generate_sql", "execute_sql")
workflow.add_edge("execute_sql", END)

app = workflow.compile()
app

# * TESTING

# Row count and unique items
result = app.invoke({"user_question": "How many rows and unique items are in the daily_demand table?"})
print("SQL:", result.get('sql_query'))
display(pd.DataFrame(result.get('data', [])))

# Top 10 items by total demand
result = app.invoke({"user_question": "What are the top 10 items by total cumulative demand value?"})
print("SQL:", result.get('sql_query'))
display(pd.DataFrame(result.get('data', [])))

# Monthly demand trend
result = app.invoke({"user_question": "What is the total demand value by year-month? Order chronologically."})
print("SQL:", result.get('sql_query'))
display(pd.DataFrame(result.get('data', [])))

# Top 15 items by average daily demand
result = app.invoke({"user_question": "What is the average daily demand per item? Return top 15 items ordered by average descending."})
print("SQL:", result.get('sql_query'))
display(pd.DataFrame(result.get('data', [])))

conn.close()
