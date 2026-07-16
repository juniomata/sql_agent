# # LangGraph SQL Agent + Routing — Walmart Sales
# **Goal:** Add a routing preprocessor that formats the user question and decides whether to return a table or a text summary (conditional edges)


# ## Libraries


from langchain_openai import ChatOpenAI

# New: Prompt Engineering and Structured Output
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

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


# ## 1.0 SQL Database Setup


PATH_DB = "sqlite:///data/walmart_sales.db"

sql_engine = sql.create_engine(PATH_DB)
conn = sql_engine.connect()

db = SQLDatabase.from_uri(PATH_DB)

print("Tables:", db.get_usable_table_names())


# ## 2.0 SQL Parsing Utility


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


# ## 3.0 Routing Preprocessor Agent (AKA The Bouncer)
# Used to format the user's question for the SQL generator and decide how the output is returned (table or text summary)


routing_preprocessor_prompt = PromptTemplate(
    template="""
    You are an expert in routing decisions for a SQL database agent. Your job is to:

    1. Determine what the correct format for a User's Question should be for use with a SQL translator agent.
    2. Determine whether the results should be returned as a data table or as a short text summary, based on the user's question.

    Use the following criteria to route the initial user question:

    From the incoming user question, remove any details about the format of the final response (table or summary) and return only the part of the question that is relevant for the SQL generator agent. This will be the 'formatted_user_question_sql_only'. If 'None' is found, return the original user question.

    Next, determine if the user would like a data 'table' or a natural-language 'summary' returned with the results of the SQL query. Select 'summary' whenever the user asks to summarize, describe, interpret, or explain the results in words, sentences, or prose. If unknown, not specified or 'None' is found, then select 'table'. This will be the 'routing_preprocessor_decision'.

    Return JSON with 'formatted_user_question_sql_only' and 'routing_preprocessor_decision'.

    INITIAL_USER_QUESTION: {initial_question}
    """,
    input_variables=["initial_question"]
)

routing_preprocessor = routing_preprocessor_prompt | llm | JsonOutputParser()

routing_preprocessor


QUESTION = "What are the top 10 items by total cumulative demand value?"

response = routing_preprocessor.invoke({"initial_question": QUESTION})
pprint(response)


QUESTION = "What is the total demand value by year? Summarize the trend in words."

response = routing_preprocessor.invoke({"initial_question": QUESTION})
pprint(response)


QUESTION = "What is the total demand value by year-month? Please return a table."

response = routing_preprocessor.invoke({"initial_question": QUESTION})
pprint(response)


# ## 4.0 SQL Agent


sql_generator = create_sql_query_chain(
    llm=llm,
    db=db,
    k=int(1e7),  # Set high to avoid LIMIT truncation
)

sql_generator


# ## 5.0 Summarizer Agent
# Used when the router decides the user wants a text summary instead of a table


summarizer_prompt = PromptTemplate(
    template="""
    You are a business analyst. Using the SQL query results below, answer the user's question in a few concise sentences. Report concrete numbers where relevant.

    USER_QUESTION: {question}

    DATA (records): {data}
    """,
    input_variables=["question", "data"]
)

summarizer = summarizer_prompt | llm | StrOutputParser()


# ## 6.0 LangGraph Workflow with Conditional Edges


class GraphState(TypedDict):
    """Represents the state of our graph."""
    user_question: str
    formatted_user_question_sql_only: str
    routing_preprocessor_decision: str
    sql_query: str
    data: dict
    summary: str


# New: determines the path + formats the question
def preprocess_routing(state):
    print("---ROUTER---")
    question = state.get("user_question")
    response = routing_preprocessor.invoke({"initial_question": question})
    return {
        "formatted_user_question_sql_only": response.get('formatted_user_question_sql_only'),
        "routing_preprocessor_decision": response.get('routing_preprocessor_decision'),
    }


def generate_sql(state):
    print("---GENERATE SQL---")
    question = state.get("formatted_user_question_sql_only")
    # Handle case when formatted_user_question_sql_only is None
    if question is None:
        question = state.get("user_question")
    sql_query = sql_generator.invoke({"question": question})
    sql_query = extract_sql_code(sql_query)
    return {"sql_query": sql_query}


def convert_dataframe(state):
    print("---CONVERT DATA FRAME---")
    sql_query = state.get("sql_query")
    df = pd.read_sql(sql_query, conn)
    return {"data": df.to_dict(orient="records")}


# New: decision logic for the conditional edge
def decide_table_or_summary(state):
    print("---DECIDE TABLE OR SUMMARY---")
    return "summary" if state.get('routing_preprocessor_decision') == "summary" else "table"


# New: text summary node
def generate_summary(state):
    print("---GENERATE SUMMARY---")
    summary = summarizer.invoke({
        "question": state.get("user_question"),
        "data": state.get("data"),
    })
    return {"summary": summary}


def state_printer(state):
    """Print the state."""
    print("---STATE PRINTER---")
    print(f"User Question: {state.get('user_question')}")
    print(f"Formatted Question (SQL): {state.get('formatted_user_question_sql_only')}")
    pprint(f"SQL Query: \n{state.get('sql_query')}\n")
    print(f"Table or Summary: {state.get('routing_preprocessor_decision')}")
    if state.get('summary'):
        print(f"Summary: \n{state.get('summary')}\n")
    print(f"Data: \n{pd.DataFrame(state.get('data'))}\n")


workflow = StateGraph(GraphState)

# Nodes
workflow.add_node("preprocess_routing", preprocess_routing)
workflow.add_node("generate_sql", generate_sql)
workflow.add_node("convert_dataframe", convert_dataframe)
workflow.add_node("generate_summary", generate_summary)
workflow.add_node("state_printer", state_printer)

# Edges
workflow.set_entry_point("preprocess_routing")
workflow.add_edge("preprocess_routing", "generate_sql")
workflow.add_edge("generate_sql", "convert_dataframe")

# New: conditional edges
workflow.add_conditional_edges(
    "convert_dataframe",
    decide_table_or_summary,
    {
        # Result : Step Name To Go To
        "summary": "generate_summary",
        "table": "state_printer",
    }
)

workflow.add_edge("generate_summary", "state_printer")
workflow.add_edge("state_printer", END)

app = workflow.compile()
app


# ## 7.0 Testing the Graph


QUESTION = "What are the top 10 items by total cumulative demand value?"

response = app.invoke({"user_question": QUESTION})
print("Decision:", response.get('routing_preprocessor_decision'))
pd.DataFrame(response.get('data'))


QUESTION = "What is the total demand value by year? Summarize the trend in words."

response = app.invoke({"user_question": QUESTION})
print("Decision:", response.get('routing_preprocessor_decision'))
print(response.get('summary'))


QUESTION = "What is the total demand value by year-month? Please return a table."

response = app.invoke({"user_question": QUESTION})
print("Decision:", response.get('routing_preprocessor_decision'))
pd.DataFrame(response.get('data'))


conn.close()
