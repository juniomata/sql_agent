
# LIBRARIES

from langchain_openai import ChatOpenAI

# * New: Prompt Engineering and Structured Output
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain

from langgraph.graph import END, StateGraph
from typing import TypedDict

import os
import yaml
from pprint import pprint

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

# * NEW: Routing Preprocessor Agent (AKA The Bouncer)
#  IMPORTANT: Used to format the user's question and provide specifications for how the output is returned

routing_preprocessor_prompt = PromptTemplate(
    template="""
    You are an expert in routing decisions for a SQL database agent, a Charting Visualization Agent, and a Pandas Table Agent. Your job is to:
    
    1. Determine what the correct format for a Users Question should be for use with a SQL translator agent 
    2. Determine whether or not a chart should be generated or a table should be returned based on the users question.
    
    Use the following criteria on how to route the the initial user question:
    
    From the incoming user question, remove any details about the format of the final response as either a Chart or Table and return only the important part of the incoming user question that is relevant for the SQL generator agent. This will be the 'formatted_user_question_sql_only'. If 'None' is found, return the original user question.
    
    Next, determine if the user would like a data visualization ('chart') or a 'table' returned with the results of the SQL query. If unknown, not specified or 'None' is found, then select 'table'.  This will be the 'routing_preprocessor_decision'.
    
    Return JSON with 'formatted_user_question_sql_only' and 'routing_preprocessor_decision'.
    
    INITIAL_USER_QUESTION: {initial_question}
    """,
    input_variables=["initial_question"]
)

routing_preprocessor = routing_preprocessor_prompt | llm | JsonOutputParser()

routing_preprocessor


QUESTION = """
Which 10 customers have the highest p1 probability of purchase?
"""
response = routing_preprocessor.invoke({"initial_question": QUESTION})
response
pprint(response)

response.get('formatted_user_question_sql_only')

response.get('routing_preprocessor_decision')

QUESTION = """
What are the total sales by month-year? Return a chart of sales by month-year. 
"""
response = routing_preprocessor.invoke({"initial_question": QUESTION})
response


QUESTION = """
What are the total sales by month-year? Please return a table. 
"""
response = routing_preprocessor.invoke({"initial_question": QUESTION})
response



# * SQL Agent

db = SQLDatabase.from_uri(PATH_DB)

sql_generator = create_sql_query_chain(
    llm = llm,
    db = db,
    k = int(1e7)
)

sql_generator


# * LANGGRAPH

class GraphState(TypedDict):
    """
    Represents the state of our graph.
    """
    user_question: str
    sql_query : str
    data: dict
    # * New: Formatted User Question for SQL and Routing Decision
    formatted_user_question_sql_only: str
    # * New: Routing Preprocessor Decision
    routing_preprocessor_decision: str

# * NEW: DETERMINES THE PATH + FORMATS THE QUESTION
def preprocess_routing(state):
    print("---ROUTER---")
    question = state.get("user_question")
    
    # Chart Routing and SQL Prep
    response = routing_preprocessor.invoke({"initial_question": question})
    
    formatted_user_question_sql_only = response.get('formatted_user_question_sql_only')
    
    routing_preprocessor_decision = response.get('routing_preprocessor_decision')
    
    return {
        "formatted_user_question_sql_only": formatted_user_question_sql_only,
        "routing_preprocessor_decision": routing_preprocessor_decision,
    }
    

def generate_sql(state):
    print("---GENERATE SQL---")
    question = state.get("formatted_user_question_sql_only")
    
    # Handle case when formatted_user_question_sql_only is None:
    if question is None:
        question = state.get("user_question")
        
    # Generate SQL
    sql_query = sql_generator.invoke({"question": question})
    
    # Extract SQL code
    sql_query = extract_sql_code(sql_query)
    
    return {"sql_query": sql_query}


def convert_dataframe(state):
    print("---CONVERT DATA FRAME---")

    sql_query = state.get("sql_query")
    
    df = pd.read_sql(sql_query, conn)
    
    return {"data": df.to_dict(orient="records")}

# * NEW: Decision Logic
def decide_chart_or_table(state):
    print("---DECIDE CHART OR TABLE---")
    return "chart" if state.get('routing_preprocessor_decision') == "chart" else "table"

def generate_chart(state):
    print("---GENERATE CHART---")
    
    # TODO: Add Charting Logic
    
    return {}
    
    
def state_printer(state):
    """print the state"""
    print("---STATE PRINTER---")
    print(f"User Question: {state['user_question']}")
    print(f"Formatted Question (SQL): {state['formatted_user_question_sql_only']}")
    pprint(f"SQL Query: \n{state['sql_query']}\n")
    print(f"Chart or Table: {state['routing_preprocessor_decision']}")
    print(f"Data: \n{pd.DataFrame(state['data'])}\n")

# * WORKFLOW DAG

workflow = StateGraph(GraphState)

# NODES

workflow.add_node("preprocess_routing", preprocess_routing)
workflow.add_node("generate_sql", generate_sql)
workflow.add_node("convert_dataframe", convert_dataframe)
workflow.add_node("generate_chart", generate_chart)
workflow.add_node("state_printer", state_printer)

# EDGES

workflow.set_entry_point("preprocess_routing")
workflow.add_edge("preprocess_routing", "generate_sql")
workflow.add_edge("generate_sql", "convert_dataframe")

# * NEW: Conditional Edges

workflow.add_conditional_edges(
    "convert_dataframe", 
    decide_chart_or_table,
    {
        # Result : Step Name To Go To
        "chart":"generate_chart", # Path Chart
        "table":"state_printer" # Path State Printer
    }
)

workflow.add_edge("generate_chart", "state_printer")
workflow.add_edge("state_printer", END)

app = workflow.compile()

app

# * TESTING

QUESTION = """
Which 10 customers have the highest p1 probability of purchase?
"""
response = app.invoke({"user_question": QUESTION})
response.keys()

response.get('routing_preprocessor_decision')

pd.DataFrame(response.get('data'))

    
QUESTION = """
What are the names of each table?
"""
response = app.invoke({"user_question": QUESTION})
response
    
    
# Note: May require gpt-4o
QUESTION = """
What are the total sales by month-year? Make a chart of sales over time.
"""
response = app.invoke({"user_question": QUESTION})
response
    
