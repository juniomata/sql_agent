# # SQL Agent with Walmart Sales
# **Goal:** Create a basic SQL agent to interact with the Walmart Sales database


# ## Libraries


# Most Important: AI
from langchain_openai import ChatOpenAI
from langchain_classic.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase

# Data Science
import pandas as pd
import sqlalchemy as sql

# Utilities
import os
import yaml
import re
from pprint import pprint
from IPython.display import Markdown


# ## AI Setup


os.environ["OPENAI_API_KEY"] = yaml.safe_load(open('credentials.yml'))['openai']

OPENAI_LLM = "gpt-4o-mini"


# ## 1. Database Setup — Walmart Sales


PATH_DB = "sqlite:///data/walmart_sales.db"

sql_engine = sql.create_engine(PATH_DB)
conn = sql_engine.connect()

# Show all tables
pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)


# ## 2. Connect LangChain to the Database


db = SQLDatabase.from_uri(PATH_DB)

print("Dialect:", db.dialect)
print("Tables:", db.get_usable_table_names())
print("\nSample data:")
print(db.run("SELECT * FROM daily_demand LIMIT 5;"))


# ## 3. Create the SQL Query Chain (Agent)


model = ChatOpenAI(
    model=OPENAI_LLM,
    temperature=0.7,
)

# Create the SQL query chain
chain = create_sql_query_chain(model, db)
chain


response = chain.invoke({'question': "What are the top 10 items by total cumulative demand value?"})
pprint(response)
Markdown(response)


# ## 4. SQL Parsing Utility


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

pprint(extract_sql_code(response))


# Run extracted SQL against DB
pprint(db.run(extract_sql_code(response)))


# ## 5. Additional Questions


# Total demand value aggregated by year-month
q = chain.invoke({'question': "What is the total demand value by year-month? Order results chronologically."})
sql_q = extract_sql_code(q)
pprint(sql_q)
pd.read_sql(sql_q, conn)


# Top items by average daily demand
q2 = chain.invoke({'question': "Which 10 items have the highest average daily demand value?"})
sql_q2 = extract_sql_code(q2)
pprint(sql_q2)
pd.read_sql(sql_q2, conn)


conn.close()
