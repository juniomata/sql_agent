import json, pathlib

NB_DIR = pathlib.Path(r"c:\Users\User\Documents\vibe\delo\ask_bi_agent\notebook")

def set_cell_src(cell, lines):
    cell["source"] = lines
    cell["outputs"] = []
    cell["execution_count"] = None

# ── NOTEBOOK 01 ──────────────────────────────────────────────────────────────
nb1 = json.loads((NB_DIR / "01_sql_agent.ipynb").read_text(encoding="utf-8"))
cells1 = nb1["cells"]

# Cell 11 – first chain.invoke question
for c in cells1:
    if c["cell_type"] == "code" and "What are the top 5 items" in "".join(c["source"]):
        set_cell_src(c, [
            'response = chain.invoke({\'question\': "What are the top 10 items by total cumulative demand value?"})\n',
            'pprint(response)\n',
            'Markdown(response)',
        ])

# Cell 16 – monthly totals
for c in cells1:
    if c["cell_type"] == "code" and "total sales value by year-month" in "".join(c["source"]):
        set_cell_src(c, [
            '# Total demand value aggregated by year-month\n',
            'q = chain.invoke({\'question\': "What is the total demand value by year-month? Order results chronologically."})\n',
            'sql_q = extract_sql_code(q)\n',
            'pprint(sql_q)\n',
            'pd.read_sql(sql_q, conn)',
        ])

# Cell 17 – average demand question
for c in cells1:
    if c["cell_type"] == "code" and "highest average daily demand" in "".join(c["source"]):
        set_cell_src(c, [
            '# Top items by average daily demand\n',
            'q2 = chain.invoke({\'question\': "Which 10 items have the highest average daily demand value?"})\n',
            'sql_q2 = extract_sql_code(q2)\n',
            'pprint(sql_q2)\n',
            'pd.read_sql(sql_q2, conn)',
        ])

(NB_DIR / "01_sql_agent.ipynb").write_text(json.dumps(nb1, indent=1, ensure_ascii=False), encoding="utf-8")
print("Saved 01")

# ── NOTEBOOK 02 ──────────────────────────────────────────────────────────────
nb2 = json.loads((NB_DIR / "02_sql_agent_langgraph.ipynb").read_text(encoding="utf-8"))
cells2 = nb2["cells"]

# Cell 9 – direct generator test
for c in cells2:
    if c["cell_type"] == "code" and "highest total demand value" in "".join(c["source"]) and "sql_generator" in "".join(c["source"]):
        set_cell_src(c, [
            '# Test the SQL generator directly\n',
            'response = sql_generator.invoke({"question": "What are the top 10 items ranked by total cumulative demand value?"})\n',
            'sql_q = extract_sql_code(response)\n',
            'pprint(sql_q)\n',
            'pd.read_sql(sql_q, conn)',
        ])

# Cell 13 – first app.invoke
for c in cells2:
    if c["cell_type"] == "code" and "QUESTION" in "".join(c["source"]) and "highest total demand" in "".join(c["source"]) and "app.invoke" in "".join(c["source"]):
        set_cell_src(c, [
            'QUESTION = "What are the top 10 items by total cumulative demand value?"\n',
            '\n',
            'response = app.invoke({"question": QUESTION})\n',
            'print("SQL:", response[\'sql_query\'])\n',
            'db.run(response[\'sql_query\'])',
        ])

# Cell 14 – monthly totals
for c in cells2:
    if c["cell_type"] == "code" and "total sales value by year-month" in "".join(c["source"]):
        set_cell_src(c, [
            'QUESTION = "What is the total demand value grouped by year and month? Order chronologically."\n',
            '\n',
            'response = app.invoke({"question": QUESTION})\n',
            'sql_q = response.get("sql_query")\n',
            'pprint(sql_q)\n',
            'pd.read_sql(sql_q, conn)',
        ])

# Cell 15 – top 20 by item_id
for c in cells2:
    if c["cell_type"] == "code" and "top 20 items" in "".join(c["source"]):
        set_cell_src(c, [
            'QUESTION = "What is the average daily demand value per item_id? Return top 15 items ordered by average descending."\n',
            '\n',
            'response = app.invoke({"question": QUESTION})\n',
            'sql_q = response.get("sql_query")\n',
            'pprint(sql_q)\n',
            'pd.read_sql(sql_q, conn)',
        ])

(NB_DIR / "02_sql_agent_langgraph.ipynb").write_text(json.dumps(nb2, indent=1, ensure_ascii=False), encoding="utf-8")
print("Saved 02")

# ── NOTEBOOK 03 ──────────────────────────────────────────────────────────────
nb3 = json.loads((NB_DIR / "03_bi_copilot.ipynb").read_text(encoding="utf-8"))
cells3 = nb3["cells"]

# Cell 12 – tables question
for c in cells3:
    if c["cell_type"] == "code" and "What tables are in the database" in "".join(c["source"]):
        set_cell_src(c, [
            'result = app.invoke({"user_question": "How many rows and unique items are in the daily_demand table?"})\n',
            'print("SQL:", result.get(\'sql_query\'))\n',
            'pd.DataFrame(result.get(\'data\', []))',
        ])

# Cell 13 – top 10 items table
for c in cells3:
    if c["cell_type"] == "code" and "top 10 items by total demand" in "".join(c["source"]) and "chart" not in "".join(c["source"]):
        set_cell_src(c, [
            'result = app.invoke({"user_question": "What are the top 10 items by total cumulative demand value?"})\n',
            'print("SQL:", result.get(\'sql_query\'))\n',
            'pd.DataFrame(result.get(\'data\', []))',
        ])

# Cell 15 – line chart
for c in cells3:
    if c["cell_type"] == "code" and "line chart" in "".join(c["source"]):
        set_cell_src(c, [
            'result = app.invoke({\n',
            '    "user_question": "What is the total demand value by year-month? Make a line chart showing demand trend over time."\n',
            '})\n',
            '\n',
            'print("SQL:", result.get(\'sql_query\'))\n',
            'df_result = pd.DataFrame(result.get(\'data\', []))\n',
            'display(df_result)\n',
            '\n',
            'if result.get(\'chart_figure\'):\n',
            '    fig = pio.from_json(result[\'chart_figure\'])\n',
            '    fig.show()',
        ])

# Cell 16 – bar chart
for c in cells3:
    if c["cell_type"] == "code" and "horizontal bar chart" in "".join(c["source"]):
        set_cell_src(c, [
            'result = app.invoke({\n',
            '    "user_question": "What are the top 15 items by total demand value? Make a horizontal bar chart ordered by demand descending."\n',
            '})\n',
            '\n',
            'print("SQL:", result.get(\'sql_query\'))\n',
            'df_result = pd.DataFrame(result.get(\'data\', []))\n',
            'display(df_result)\n',
            '\n',
            'if result.get(\'chart_figure\'):\n',
            '    fig = pio.from_json(result[\'chart_figure\'])\n',
            '    fig.show()',
        ])

(NB_DIR / "03_bi_copilot.ipynb").write_text(json.dumps(nb3, indent=1, ensure_ascii=False), encoding="utf-8")
print("Saved 03")
