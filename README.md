# SQL AI Copilot

An AI-powered Business Intelligence agent, from a basic text-to-SQL chain to a routed LangGraph workflow and a chat-based Streamlit app. Built with **LangChain**, **LangGraph**, and **OpenAI**, querying a local SQLite database of Walmart daily item demand.

## Dataset

`data/walmart_sales.db` (SQLite) — a single table:

| Table | Columns | Rows | Range |
|---|---|---|---|
| `daily_demand` | `item_id` (TEXT), `value` (INTEGER), `date` (TEXT) | ~23,000 | 2011 – 2016 |

## Components

Each component exists as a Python script (repo root) and a matching executed Jupyter notebook (`notebook/`). The scripts build on each other, adding one capability at a time.

| # | Script | Notebook | What it adds |
|---|---|---|---|
| 01 | [01_sql_agent_langgraph.py](01_sql_agent_langgraph.py) | [notebook](notebook/01_sql_agent_langgraph.ipynb) | SQL agent: `create_sql_query_chain` + SQL-extraction utility, wrapped in a LangGraph DAG that returns a Pandas DataFrame |
| 02 | [02_add_routing_langgraph.py](02_add_routing_langgraph.py) | [notebook](notebook/02_add_routing_langgraph.ipynb) | Routing preprocessor + conditional edges: table vs. text summary |
| 03 | [03_streamlit_bi_copilot.py](03_streamlit_bi_copilot.py) | — (Streamlit app) | "Your SQL AI Copilot" — chat UI over the full agent |

## Workflow Diagrams

The LangGraph workflow grows across the scripts:

**01 — SQL agent as a DAG**

![SQL agent DAG](images/01_sql_agent_langgraph_dag.png)

**01 — add DataFrame conversion**

![SQL agent + pandas](images/01_sql_agent_langgraph_dataframe.png)

**02 — add routing with conditional edges (table or summary)**

![Routing workflow](images/02_add_routing_langgraph_graph.png)

## Setup

1. **Activate the virtual environment** (Python 3.11):

   ```powershell
   # PowerShell
   .\venv\Scripts\Activate.ps1
   ```

   ```bash
   # Git Bash
   source venv/Scripts/activate
   ```

   Or create a fresh environment and install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

2. **Add your OpenAI API key** in `credentials.yml` at the repo root (gitignored — never commit it):

   ```yaml
   openai: sk-...
   ```

## Running

**Streamlit copilot (03):**

```powershell
streamlit run 03_streamlit_bi_copilot.py
```

Then open http://localhost:8501, pick a model in the sidebar, and ask questions like:

- What are the top 10 items by total cumulative demand value?
- What is the total demand value by year-month? Order chronologically.
- What is the total demand value by year? Summarize the trend in words.

**Notebooks:** open any notebook in `notebook/` with the `ask_bi_agent_venv` Jupyter kernel, or re-execute from the command line:

```powershell
cd notebook
..\venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace 01_sql_agent_langgraph.ipynb
```

> Notebooks use `../`-relative paths (they run from `notebook/`); the scripts use repo-root-relative paths.

## Project Structure

```
sql_agent/
├── 01_sql_agent_langgraph.py     # Agent scripts (source of truth)
├── 02_add_routing_langgraph.py
├── 03_streamlit_bi_copilot.py    # Streamlit chat app
├── credentials.yml               # OpenAI API key (gitignored, keep private)
├── requirements.txt              # Dependencies (Streamlit Cloud installs from this)
├── data/
│   └── walmart_sales.db          # SQLite: daily_demand table
├── images/                       # Workflow diagrams (exported from notebooks)
└── notebook/                     # Executed notebooks generated from the scripts
```
