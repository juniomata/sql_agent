# BUSINESS SCIENCE UNIVERSITY
# PYTHON FOR GENERATIVE AI COURSE
# ML + AI BUSINESS INTELLIGENCE (FLOW CONTROL)
# ***

# Goal: Create a basic SQL agent to interact with the database

# LIBRARIES

# Most Important: AI
from langchain_openai import ChatOpenAI
from langchain_classic.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase

# Next Most: Data Science 
import pandas as pd
import sqlalchemy as sql

# Utilities
import os
import yaml
import re
from pprint import pprint
from IPython.display import Markdown

# AI SETUP

os.environ["OPENAI_API_KEY"] = yaml.safe_load(open('credentials.yml'))['openai']

OPENAI_LLM = "gpt-4o-mini" # gpt-4.1-mini, gpt-4.1-nano, gpt-4.1

# DATABASE SETUP

PATH_DB = "sqlite:///data/walmart_sales.db"

sql_engine = sql.create_engine(PATH_DB)

conn = sql_engine.connect()

# select all table names
pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)

# * 1.0 CREATE A SIMPLE SQL DATABASE AI AGENT

# * Connecting Langchain to a database

db = SQLDatabase.from_uri(PATH_DB)

db.dialect

db.get_usable_table_names()

db.run("SELECT * FROM daily_demand LIMIT 10;")

# * Generating SQL with LLMs

model = ChatOpenAI(
    model = OPENAI_LLM,
    temperature = 0.7,
)

response = model.invoke("what's the recipe for mayonnaise?")
Markdown(response.content)

# * Combine LLM and SQL Database to create a SQL Query Chain (Agent)
chain = create_sql_query_chain(model, db)

chain

response = chain.invoke({'question': "What are the top 10 items by total cumulative demand value?"})

pprint(response)

Markdown(response)

# Error: Malformed SQL
pprint(db.run(response))

# * Parsing SQL Utility Function

def extract_sql_code(text: str) -> str | None:
    """
    Extracts the SQL query from a block of text. Handles:
      1) SQLQuery: ```sql ...``` fences
      2) ```sql ...``` fences
      3) ``` … ``` fences containing a SELECT
      4) SQLQuery: … (no fences)
      5) Bare SELECT …; up to semicolon
    Returns the SQL (trimmed), or None if no query found.
    """
    patterns = [
        # 1) SQLQuery: ```sql ...```
        r"SQLQuery:\s*```sql\s*(?P<sql>[\s\S]+?)```",
        # 2) ```sql ...```
        r"```sql\s*(?P<sql>[\s\S]+?)```",
        # 3) ``` … ``` containing SELECT
        r"```(?:[\s\S]*?)\s*(?P<sql>SELECT[\s\S]+?)```",
        # 4) SQLQuery: … (grab until a blank line or end)
        r"SQLQuery:\s*(?P<sql>[\s\S]+?)(?=\n\s*\n|$)",
        # 5) Bare SELECT …; up to semicolon
        r"(?P<sql>SELECT[\s\S]+?;)(?=\s|$)",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            sql = m.group("sql").strip()
            # strip any wrapping quotes
            if (sql.startswith(("'", '"')) and sql.endswith(("'", '"'))):
                sql = sql[1:-1].strip()
            return sql

    return None

pprint(extract_sql_code(response))

Markdown(f"```sql\n{extract_sql_code(response)}\n```")

# No Error now
pprint(db.run(extract_sql_code(response)))

# * 2.0 ADDITIONAL QUERIES — WALMART SALES

# Total demand value by year-month

response = chain.invoke({'question': "What is the total demand value by year-month? Order results chronologically."})


Markdown(f"```sql\n{extract_sql_code(response)}\n```")


pd.read_sql(extract_sql_code(response), conn)


# Top 10 items by average daily demand

response = chain.invoke({'question': "Which 10 items have the highest average daily demand value?"})


Markdown(f"```sql\n{extract_sql_code(response)}\n```")


pd.read_sql(extract_sql_code(response), conn)

# Close connection
conn.close()

