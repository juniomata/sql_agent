# BI Copilot — Walmart Sales (Streamlit App)
# Goal: Chat-based Business Intelligence agent that answers questions about the
# Walmart Sales database with SQL-backed data tables and text summaries.
#
# Run with: streamlit run 05_streamlit_bi_copilot.py

# LIBRARIES

import streamlit as st

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_community.utilities import SQLDatabase
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_classic.chains import create_sql_query_chain

from langgraph.graph import END, StateGraph
from typing import TypedDict

import pandas as pd
import sqlalchemy as sql
import os
import re
import yaml

# AI SETUP

os.environ["OPENAI_API_KEY"] = yaml.safe_load(open('credentials.yml'))['openai']

MODEL_LIST = ['gpt-4o-mini', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-4.1', 'gpt-4o']

# SQL DATABASE SETUP

PATH_DB = "sqlite:///data/walmart_sales.db"


# UTILITIES

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


# BI AGENT (LangGraph): route -> generate SQL -> dataframe -> optional summary

def make_business_intelligence_agent(path: str, model: str):

    llm = ChatOpenAI(model=model)

    sql_engine = sql.create_engine(path)
    conn = sql_engine.connect()

    db = SQLDatabase.from_uri(path)

    sql_generator = create_sql_query_chain(llm=llm, db=db, k=int(1e7))

    routing_preprocessor_prompt = PromptTemplate(
        template="""
        You are an expert in routing decisions for a SQL database agent. Your job is to:

        1. Determine what the correct format for a User's Question should be for use with a SQL translator agent.
        2. Determine whether the results should be returned as a data table or as a short text summary, based on the user's question.

        From the incoming user question, remove any details about the format of the final response (table or summary) and return only the part of the question that is relevant for the SQL generator agent. This will be the 'formatted_user_question_sql_only'. If 'None' is found, return the original user question.

        Next, determine if the user would like a data 'table' or a natural-language 'summary' returned with the results of the SQL query. Select 'summary' whenever the user asks to summarize, describe, interpret, or explain the results in words, sentences, or prose. If unknown, not specified or 'None' is found, then select 'table'. This will be the 'routing_preprocessor_decision'.

        Return JSON with 'formatted_user_question_sql_only' and 'routing_preprocessor_decision'.

        INITIAL_USER_QUESTION: {initial_question}
        """,
        input_variables=["initial_question"]
    )

    routing_preprocessor = routing_preprocessor_prompt | llm | JsonOutputParser()

    summarizer_prompt = PromptTemplate(
        template="""
        You are a business analyst. Using the SQL query results below, answer the user's question in a few concise sentences. Report concrete numbers where relevant.

        USER_QUESTION: {question}

        DATA (records): {data}
        """,
        input_variables=["question", "data"]
    )

    summarizer = summarizer_prompt | llm | StrOutputParser()

    class GraphState(TypedDict):
        user_question: str
        formatted_user_question_sql_only: str
        routing_preprocessor_decision: str
        sql_query: str
        data: dict
        summary: str

    def preprocess_routing(state):
        response = routing_preprocessor.invoke({"initial_question": state.get("user_question")})
        return {
            "formatted_user_question_sql_only": response.get('formatted_user_question_sql_only'),
            "routing_preprocessor_decision": response.get('routing_preprocessor_decision'),
        }

    def generate_sql(state):
        question = state.get("formatted_user_question_sql_only") or state.get("user_question")
        sql_query = sql_generator.invoke({"question": question})
        return {"sql_query": extract_sql_code(sql_query)}

    def convert_dataframe(state):
        df = pd.read_sql(state.get("sql_query"), conn)
        return {"data": df.to_dict(orient="records")}

    def decide_table_or_summary(state):
        return "summary" if state.get('routing_preprocessor_decision') == "summary" else "table"

    def generate_summary(state):
        summary = summarizer.invoke({
            "question": state.get("user_question"),
            "data": state.get("data"),
        })
        return {"summary": summary}

    workflow = StateGraph(GraphState)

    workflow.add_node("preprocess_routing", preprocess_routing)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("convert_dataframe", convert_dataframe)
    workflow.add_node("generate_summary", generate_summary)

    workflow.set_entry_point("preprocess_routing")
    workflow.add_edge("preprocess_routing", "generate_sql")
    workflow.add_edge("generate_sql", "convert_dataframe")
    workflow.add_conditional_edges(
        "convert_dataframe",
        decide_table_or_summary,
        {
            "summary": "generate_summary",
            "table": END,
        }
    )
    workflow.add_edge("generate_summary", END)

    return workflow.compile()


# STREAMLIT APP SETUP

st.set_page_config(page_title="Your SQL AI Copilot")
st.title("Your SQL AI Copilot")

st.markdown("""
            I'm a handy business intelligence agent connected to the walmart_sales.db SQLite database, which contains daily item demand data (item_id, value, date) ranging from 2011-01-29 to 2016-04-24. Ask me Business Intelligence questions and I'll answer with data tables or text summaries.
            """)

# Sidebar for model selection
model_option = st.sidebar.selectbox(
    "Choose OpenAI model",
    MODEL_LIST,
    index=0
)

# AGENT

app = make_business_intelligence_agent(
    path=PATH_DB,
    model=model_option
)

# STREAMLIT CHAT UI

example_questions = st.expander("Try out example questions")

with example_questions:
    """
    Example Questions:
    1. What tables are in the database?
    2. How many rows are in the daily_demand table?
    3. How many unique items are in the daily_demand table?
    4. What are the top 10 items by total cumulative demand value?
    5. What is the total demand value by year-month? Order chronologically.
    6. Which item had the single highest daily demand value, and on what date?
    7. What is the average daily demand value per item? Return the top 15 items.
    8. What is the total demand value by year? Summarize the trend in words.
    """

# Set up memory
msgs = StreamlitChatMessageHistory(key="langchain_messages")
if len(msgs.messages) == 0:
    msgs.add_ai_message("How can I help you?")

# Initialize dataframe storage in session state
if "dataframes" not in st.session_state:
    st.session_state.dataframes = []

# Function to display chat messages including dataframes
def display_chat_history():
    for msg in msgs.messages:
        with st.chat_message(msg.type):
            if "DATAFRAME_INDEX:" in msg.content:
                df_index = int(msg.content.split("DATAFRAME_INDEX:")[1])
                st.dataframe(st.session_state.dataframes[df_index], key=f"history_dataframe_{df_index}")
            else:
                st.write(msg.content)

# Render current messages from StreamlitChatMessageHistory
display_chat_history()

if question := st.chat_input("Enter your question here:", key="query_input"):
    with st.spinner("Thinking..."):

        st.chat_message("human").write(question)
        msgs.add_user_message(question)

        error_occured = False
        try:
            result = app.invoke({"user_question": question})
        except Exception as e:
            error_occured = True
            import traceback
            traceback.print_exc()
            st.error(f"Error: {e}")

        if not error_occured:

            if result.get('routing_preprocessor_decision') == 'summary' and result.get('summary'):
                # Text summary was requested
                response_text = f"{result['summary']}\n\nSQL Query:\n```sql\n{result['sql_query']}\n```"
                msgs.add_ai_message(response_text)
                st.chat_message("ai").write(response_text)

            else:
                # Table was requested (default)
                response_text = f"Returning the table...\n\nSQL Query:\n```sql\n{result['sql_query']}\n```"

                response_df = pd.DataFrame(result['data'])

                # Store the dataframe and keep its index
                df_index = len(st.session_state.dataframes)
                st.session_state.dataframes.append(response_df)

                # Store the response text and dataframe index in the messages
                msgs.add_ai_message(response_text)
                msgs.add_ai_message(f"DATAFRAME_INDEX:{df_index}")

                st.chat_message("ai").write(response_text)
                st.dataframe(response_df)
        else:
            # SQL error occurred
            response_text = "An error occurred in generating the SQL. I apologize. Please try again or format the question differently and I'll try my best to provide a helpful answer."
            msgs.add_ai_message(response_text)
            st.chat_message("ai").write(response_text)
