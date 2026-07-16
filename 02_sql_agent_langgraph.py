# # SQL Agent with LangGraph — Walmart Sales
# **Goal:** Introduction to LangGraph DAGs (Directed Acyclic Graphs) for SQL querying on Walmart Sales data


# ## Libraries


from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_classic.chains import create_sql_query_chain

# LangGraph
from langgraph.graph import END, StateGraph
from typing import TypedDict

import pandas as pd
import sqlalchemy as sql
import os
import re
import yaml
from pprint import pprint


# ## AI Setup


os.environ["OPENAI_API_KEY"] = yaml.safe_load(open('credentials.yml'))['openai']

llm = ChatOpenAI(model="gpt-4o-mini")


# ## 1. SQL Agent — Walmart Sales Database


PATH_DB = "sqlite:///data/walmart_sales.db"

sql_engine = sql.create_engine(PATH_DB)
conn = sql_engine.connect()

db = SQLDatabase.from_uri(PATH_DB)

sql_generator = create_sql_query_chain(
    llm=llm,
    db=db,
    k=int(1e7),  # Set high to avoid LIMIT truncation
)

print("Tables:", db.get_usable_table_names())


# ## 2. SQL Parsing Utility


def extract_sql_code(text: str):
    """Extract the SQL query from an LLM response. Returns None if not found."""
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


# Test the SQL generator directly
response = sql_generator.invoke({"question": "What are the top 10 items ranked by total cumulative demand value?"})
sql_q = extract_sql_code(response)
pprint(sql_q)
pd.read_sql(sql_q, conn)


# ## 3. Build a LangGraph DAG


class GraphState(TypedDict):
    """Represents the state of our graph."""
    question: str
    sql_query: str


def generate_sql(state):
    print("---GENERATE SQL---")
    question = state.get("question")
    sql_query = sql_generator.invoke({"question": question})
    sql_query = extract_sql_code(sql_query)
    return {"sql_query": sql_query}


def state_printer(state):
    """Print the state."""
    print("---STATE PRINTER---")
    print(f"question: {state.get('question')}")
    pprint(f"SQL Query:\n{state.get('sql_query')}")


workflow = StateGraph(GraphState)

workflow.add_node("generate_sql", generate_sql)
workflow.add_node("state_printer", state_printer)

workflow.set_entry_point("generate_sql")
workflow.add_edge("generate_sql", "state_printer")
workflow.add_edge("state_printer", END)

app = workflow.compile()
app


# ## 4. Testing the Graph


QUESTION = "What are the top 10 items by total cumulative demand value?"

response = app.invoke({"question": QUESTION})
print("SQL:", response['sql_query'])
db.run(response['sql_query'])


QUESTION = "What is the total demand value grouped by year and month? Order chronologically."

response = app.invoke({"question": QUESTION})
sql_q = response.get("sql_query")
pprint(sql_q)
pd.read_sql(sql_q, conn)


QUESTION = "What is the average daily demand value per item_id? Return top 15 items ordered by average descending."

response = app.invoke({"question": QUESTION})
sql_q = response.get("sql_query")
pprint(sql_q)
pd.read_sql(sql_q, conn)


QUESTION = "Which item had the single highest daily demand value, and on what date?"

response = app.invoke({"question": QUESTION})
sql_q = response.get("sql_query")
pprint(sql_q)
pd.read_sql(sql_q, conn)


QUESTION = "What are the top 5 items by total demand value in 2015?"

response = app.invoke({"question": QUESTION})
sql_q = response.get("sql_query")
pprint(sql_q)
pd.read_sql(sql_q, conn)


conn.close()
