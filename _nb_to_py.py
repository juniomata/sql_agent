import json, pathlib

NB_DIR = pathlib.Path(r"c:\Users\User\Documents\vibe\delo\ask_bi_agent\notebook")
ROOT = pathlib.Path(r"c:\Users\User\Documents\vibe\delo\ask_bi_agent")

def nb_to_py(nb_file, py_file):
    nb = json.loads((NB_DIR / nb_file).read_text(encoding="utf-8"))
    lines = []
    for cell in nb["cells"]:
        src = "".join(cell["source"]).strip()
        if not src:
            continue
        if cell["cell_type"] == "markdown":
            for ln in src.splitlines():
                lines.append("# " + ln.lstrip("#").strip())
            lines.append("")
        elif cell["cell_type"] == "code":
            lines.append(src)
            lines.append("")
    (ROOT / py_file).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {py_file} ({len(lines)} lines)")

nb_to_py("01_sql_agent.ipynb", "01_sql_agent.py")
nb_to_py("03_bi_copilot.ipynb", "03_bi_copilot.py")
