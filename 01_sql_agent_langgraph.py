# # SQL Agent with LangGraph — Walmart Sales
# **Goal:** Build a SQL agent for the Walmart Sales database — from a LangChain SQL query chain to a LangGraph DAG that executes the SQL and returns Pandas DataFrames


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


# ## 1. SQL Database Setup


PATH_DB = "sqlite:///data/walmart_sales.db"

sql_engine = sql.create_engine(PATH_DB)
conn = sql_engine.connect()

# Show all tables
pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)


db = SQLDatabase.from_uri(PATH_DB)

print("Dialect:", db.dialect)
print("Tables:", db.get_usable_table_names())
print("\nSample data:")
print(db.run("SELECT * FROM daily_demand LIMIT 5;"))


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


# ## 3. SQL Agent + DataFrame Conversion


sql_generator = create_sql_query_chain(
    llm=llm,
    db=db,
    k=int(1e7),  # Set high to avoid LIMIT truncation
)

sql_generator


# New: convert the SQL result to a Pandas DataFrame
response = sql_generator.invoke({"question": "Which 10 items have the highest total cumulative demand value?"})

df = pd.read_sql(extract_sql_code(response), conn)
df


# df.to_dict(orient="records") is JSON serializable — safe to store in graph state
df.to_dict(orient="records")


pd.DataFrame(df.to_dict(orient="records"))


# ## 4. Build a LangGraph DAG


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


QUESTION = "What are the top 10 items by total cumulative demand value?"

response = app.invoke({"question": QUESTION})
print("SQL:", response['sql_query'])
db.run(response['sql_query'])


# ## 5. Add a DataFrame Node to the Graph
# Extend the graph state and add a node that executes the SQL and stores the result as a JSON-serializable DataFrame (records).


class GraphState(TypedDict):
    """Represents the state of our graph."""
    question: str
    sql_query: str
    # New: DataFrame stored as records
    data: dict


# New: execute the SQL and store the result as a DataFrame
def convert_dataframe(state):
    print("---CONVERT DATA FRAME---")
    sql_query = state.get("sql_query")
    df = pd.read_sql(sql_query, conn)
    return {"data": df.to_dict(orient="records")}


def state_printer(state):
    """Print the state."""
    print("---STATE PRINTER---")
    print(f"question: {state.get('question')}")
    pprint(f"SQL Query: {state.get('sql_query')}")
    print(f"Data: {pd.DataFrame(state.get('data')).to_string()}")


workflow = StateGraph(GraphState)

workflow.add_node("generate_sql", generate_sql)
workflow.add_node("convert_dataframe", convert_dataframe)
workflow.add_node("state_printer", state_printer)

workflow.set_entry_point("generate_sql")
workflow.add_edge("generate_sql", "convert_dataframe")
workflow.add_edge("convert_dataframe", "state_printer")
workflow.add_edge("state_printer", END)

app = workflow.compile()
app


# ## 6. Testing the Graph


QUESTION = "Which 10 items have the highest total cumulative demand value?"

response = app.invoke({"question": QUESTION})
pd.DataFrame(response.get("data"))


QUESTION = "What are the names of each table in the database?"

response = app.invoke({"question": QUESTION})
pd.DataFrame(response.get("data"))


QUESTION = "Extract the first 20 rows for item FOODS_3_090 from the daily_demand table, ordered by date."

response = app.invoke({"question": QUESTION})
pd.DataFrame(response.get("data"))


QUESTION = "What is the total demand value by year-month? Order chronologically."

response = app.invoke({"question": QUESTION})
pd.DataFrame(response.get("data"))


pprint(response.get("sql_query"))


conn.close()
