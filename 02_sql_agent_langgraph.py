# BUSINESS SCIENCE UNIVERSITY
# PYTHON FOR GENERATIVE AI COURSE
# ML + AI BUSINESS INTELLIGENCE (FLOW CONTROL)
# ***

# Goal: Introduction to LangGraph
# - DAGs: Directed Acyclic Graphs

# Requirements:
# pip install langgraph==0.2.59 


# LIBRARIES

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain

# * New: LangGraph
from langgraph.graph import END, StateGraph
from typing import TypedDict

import pandas as pd
import sqlalchemy as sql
import os
import yaml
from pprint import pprint

# * New: Import extract_sql_code (modular approach)
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

# * New: SQL Agent

db = SQLDatabase.from_uri(PATH_DB)

sql_generator = create_sql_query_chain(
    llm = llm,
    db = db,
    k = 1e7, # * NEW: Set to 1e7 to avoid truncation
)

sql_generator

response = sql_generator.invoke({"question": "which 10 customers have the highest p1 probability of purchase?"})

pprint(extract_sql_code(response))

pd.read_sql(extract_sql_code(response), conn)


response = sql_generator.invoke({"question": "what tables are in the database?"})

pprint(extract_sql_code(response))

pd.read_sql(extract_sql_code(response), conn)


# * LANGGRAPH
class GraphState(TypedDict):
    """
    Represents the state of our graph.
    """
    question: str
    sql_query : str


def generate_sql(state):
    print("---GENERATE SQL---")
    question = state.get("question")
    
    # Generate SQL
    sql_query = sql_generator.invoke({"question": question})
    
    # Extract SQL code
    sql_query = extract_sql_code(sql_query)
    
    return {"sql_query": sql_query}

def state_printer(state):
    """print the state"""
    print("---STATE PRINTER---")
    print(f"question: {state.get('question')}")
    pprint(f"SQL Query:\n{state.get('sql_query')}")

# * WORKFLOW DAG

workflow = StateGraph(GraphState)

workflow.add_node("generate_sql", generate_sql)
workflow.add_node("state_printer", state_printer)

workflow.set_entry_point("generate_sql")
workflow.add_edge("generate_sql", "state_printer")
workflow.add_edge("state_printer", END)

app = workflow.compile()
app


# * TESTING

QUESTION = """
Which 10 customers have the highest p1 probability of purchase?
"""

response = app.invoke({"question": QUESTION})

response.keys()

response['question']
response['sql_query']

db.run(response['sql_query'])


QUESTION = """
Extract the transactions table. Return all rows.
"""


response = app.invoke({"question": QUESTION})
response

response.get("sql_query")

db.run(response.get("sql_query"))

    
QUESTION = """
What are the total sales by month-year?
"""
response = app.invoke({"question": QUESTION})
response

response.get("sql_query")

db.run(response.get("sql_query"))
