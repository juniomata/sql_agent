# LIBRARIES

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain

from langgraph.graph import END, StateGraph
from typing import TypedDict

import os
import yaml
from pprint import pprint

# * New: Execute SQL Code with pd.read_sql
import pandas as pd
import sqlalchemy as sql

from business_intelligence_agent.utils import extract_sql_code

# AI SETUP

os.environ["OPENAI_API_KEY"] = yaml.safe_load(open('../credentials.yml'))['openai']

OPENAI_LLM = ChatOpenAI(
    model = "gpt-4o-mini"
)

llm = OPENAI_LLM

# SQL DATABASE SETUP

PATH_DB = "sqlite:///database/leads_scored.db"

sql_engine = sql.create_engine(PATH_DB)

conn = sql_engine.connect()


# * AGENTS

# * SQL Agent

db = SQLDatabase.from_uri(PATH_DB)

sql_generator = create_sql_query_chain(
    llm = llm,
    db = db,
    k = int(1e7)
)

sql_generator

# * NEW: Dataframe Conversion

response = sql_generator.invoke({"question": "which 10 customers have the highest p1 probability of purchase?"})

df = pd.read_sql(extract_sql_code(response), conn)

df

df.to_dict(orient="records")

pd.DataFrame(df.to_dict(orient="records"))

# * LANGGRAPH
class GraphState(TypedDict):
    """
    Represents the state of our graph.
    """
    question: str
    sql_query : str
    # * New: Data Frame
    data: dict 


def generate_sql(state):
    print("---GENERATE SQL---")
    question = state.get("question")
    
    # Generate SQL
    sql_query = sql_generator.invoke({"question": question})
    
    # Extract SQL code
    sql_query = extract_sql_code(sql_query)
    
    return {"sql_query": sql_query}

# * New: Create Data Frame
def convert_dataframe(state):
    print("---CONVERT DATA FRAME---")

    sql_query = state.get("sql_query")
    
    df = pd.read_sql(sql_query, conn)
    
    return {"data": df.to_dict(orient="records")} # df.to_dict(orient="records") is JSON serializable
  
    
def state_printer(state):
    """print the state"""
    print("---STATE PRINTER---")
    print(f"question: {state.get('question')}")
    pprint(f"SQL Query: {state.get('sql_query')}")
    print(f"Data: {pd.DataFrame(state.get('data')).to_string()}")

# * WORKFLOW DAG

workflow = StateGraph(GraphState)

workflow.add_node("generate_sql", generate_sql)
workflow.add_node("convert_dataframe", convert_dataframe)
workflow.add_node("state_printer", state_printer)

workflow.set_entry_point("generate_sql")

# * New: Add Edge
workflow.add_edge("generate_sql", "convert_dataframe")
workflow.add_edge("convert_dataframe", "state_printer")

workflow.add_edge("state_printer", END)

app = workflow.compile()

app

# * TESTING

QUESTION = """
Which 10 customers have the highest p1 probability of purchase?
"""

response = app.invoke({"question": QUESTION})

response.keys()

pd.DataFrame(response.get("data"))

# expect error due to pandas conversion only allowed on 1 table at a time
QUESTION = """
What are the first five rows of each table?
"""

response = app.invoke({"question": QUESTION})

response.keys()

pd.DataFrame(response.get("data"))
    
    
QUESTION = """
What are the names of each table?
"""

response = app.invoke({"question": QUESTION})

response.keys()

pd.DataFrame(response.get("data"))
    
    
QUESTION = """
Extract the transactions table. Return all rows.
"""

response = app.invoke({"question": QUESTION})

response.keys()

pd.DataFrame(response.get("data"))
    

# Note - May need to use gpt-4o or gpt-4.1

QUESTION = """
What are the total sales by month-year - multiply quantity by price?
"""

response = app.invoke({"question": QUESTION})

response.keys()

pd.DataFrame(response.get("data"))

pprint(response.get("sql_query"))
