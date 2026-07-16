"""Fix extract_sql_code in all notebooks to handle SQLQuery: + code-fence format."""
import json, re, pathlib

NOTEBOOK_DIR = pathlib.Path(r"c:\Users\User\Documents\vibe\delo\ask_bi_agent\notebook")

# Also fix notebook 02 directly (pattern-based replace didn't catch it)
NB02 = NOTEBOOK_DIR / "02_sql_agent_langgraph.ipynb"

NEW_FUNC = '''\
def extract_sql_code(text: str):
    """Extract SQL query from LLM text output (handles SQLQuery: prefix and code fences)."""
    if not text:
        return None
    # 1) SQLQuery: ```sql ... ```
    m = re.search(r"SQLQuery:\\s*```sql\\s*([\\s\\S]+?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 2) ```sql ... ```
    m = re.search(r"```sql\\s*([\\s\\S]+?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 3) ``` ... ``` containing SELECT
    m = re.search(r"```[\\w]*\\s*(SELECT[\\s\\S]+?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 4) SQLQuery: SELECT ... (no fence)
    m = re.search(r"SQLQuery:\\s*(SELECT[\\s\\S]+?)(?:\\n\\n|$)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 5) Bare SELECT ...
    m = re.search(r"(SELECT[\\s\\S]+?)(?:;|\\n\\n|$)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip(";")
    return None
'''

OLD_PATTERN = re.compile(
    r'def extract_sql_code\(text.*?return None\n',
    re.DOTALL
)

for nb_path in NOTEBOOK_DIR.glob("*.ipynb"):
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    changed = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell["source"])
        if "def extract_sql_code" in src:
            new_src = OLD_PATTERN.sub(lambda m: NEW_FUNC, src)
            if new_src != src:
                cell["source"] = new_src.splitlines(keepends=True)
                changed = True
                print(f"  Updated extract_sql_code in {nb_path.name}")
    if changed:
        nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"Saved {nb_path.name}")
    else:
        print(f"No change needed in {nb_path.name}")
