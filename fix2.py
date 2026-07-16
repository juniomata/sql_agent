import json, re, pathlib

NOTEBOOK_DIR = pathlib.Path(r"c:\Users\User\Documents\vibe\delo\ask_bi_agent\notebook")

# Build regex patterns programmatically to avoid special char issues
BT = chr(96)*3  # backticks

def new_extract_func():
    lines = []
    lines.append('def extract_sql_code(text: str):\n')
    lines.append('    if not text:\n')
    lines.append('        return None\n')
    # Pattern 1: SQLQuery: ```sql ... ```
    p1 = 'r"SQLQuery:\\s*' + BT + 'sql\\s*([\\s\\S]+?)' + BT + '"'
    lines.append('    m = re.search(' + p1 + ', text, re.IGNORECASE)\n')
    lines.append('    if m: return m.group(1).strip()\n')
    # Pattern 2: ```sql ... ```
    p2 = 'r"' + BT + 'sql\\s*([\\s\\S]+?)' + BT + '"'
    lines.append('    m = re.search(' + p2 + ', text, re.IGNORECASE)\n')
    lines.append('    if m: return m.group(1).strip()\n')
    # Pattern 3: ```[any]... SELECT ... ```
    p3 = 'r"' + BT + '[\\w]*\\s*(SELECT[\\s\\S]+?)' + BT + '"'
    lines.append('    m = re.search(' + p3 + ', text, re.IGNORECASE)\n')
    lines.append('    if m: return m.group(1).strip()\n')
    # Pattern 4: SQLQuery: SELECT (no fence)
    p4 = 'r"SQLQuery:\\s*(SELECT[\\s\\S]+?)(?:\\n\\n|$)"'
    lines.append('    m = re.search(' + p4 + ', text, re.IGNORECASE)\n')
    lines.append('    if m: return m.group(1).strip()\n')
    # Pattern 5: Bare SELECT
    p5 = 'r"(SELECT[\\s\\S]+?)(?:;|\\n\\n|$)"'
    lines.append('    m = re.search(' + p5 + ', text, re.IGNORECASE)\n')
    lines.append("    if m: return m.group(1).strip().rstrip(';')\n")
    lines.append('    return None\n')
    return lines

OLD_PATTERN = re.compile(r'def extract_sql_code\(text.*?return None\n', re.DOTALL)
new_lines = new_extract_func()

for nb_path in NOTEBOOK_DIR.glob("*.ipynb"):
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    changed = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell["source"])
        if "def extract_sql_code" not in src:
            continue
        new_src = OLD_PATTERN.sub(lambda m: "".join(new_lines), src)
        if new_src == src and src.strip().startswith("def extract_sql_code"):
            new_src = "".join(new_lines)
        if new_src != src:
            cell["source"] = list(new_src.splitlines(keepends=True))
            changed = True
            print("  Fixed " + nb_path.name)
    if changed:
        nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        print("  Saved " + nb_path.name)
    else:
        print("  No change: " + nb_path.name)
