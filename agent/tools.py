"""Your agent's abilities live here.

To add a tool:
  1. Write a plain Python function.
  2. Add an entry to TOOLS below (name, description, input schema).
That's it — the agent loop picks it up automatically.

Included: file tools (list/read/search).
Files come from two places:
  - knowledge/   -> committed to the repo, ships with every deploy
  - data/files/  -> runtime uploads (set FILES_DIR to a volume in the cloud)
"""

import os

# Where the agent looks for files. Both are optional.
KNOWLEDGE_DIR = os.environ.get("KNOWLEDGE_DIR", "knowledge")
FILES_DIR = os.environ.get("FILES_DIR", os.path.join("data", "files"))
_ROOTS = {"knowledge": KNOWLEDGE_DIR, "files": FILES_DIR}

MAX_READ_CHARS = 20_000   # cap what a single read puts into context
MAX_LIST = 200
MAX_SEARCH_RESULTS = 20

# --------------------------------------------------------- file tools


def _iter_files():
    """Yield (label, relative_path, full_path) across all roots."""
    for label, root in _ROOTS.items():
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for fn in sorted(filenames):
                if fn.startswith("."):
                    continue
                full = os.path.join(dirpath, fn)
                yield label, os.path.relpath(full, root), full


def _resolve(path: str) -> str:
    """Turn 'knowledge/notes.md' into a real path, refusing escapes."""
    label, _, rel = path.replace("\\", "/").strip("/").partition("/")
    root = _ROOTS.get(label)
    if not root or not rel:
        raise ValueError(
            "Path must start with 'knowledge/' or 'files/' — call list_files to see what exists."
        )
    full = os.path.realpath(os.path.join(root, rel))
    root_real = os.path.realpath(root)
    if full != root_real and not full.startswith(root_real + os.sep):
        raise ValueError("Path escapes the allowed directories.")
    return full


def list_files() -> str:
    """All files the agent can see, with sizes."""
    lines = []
    for label, rel, full in _iter_files():
        try:
            size = os.path.getsize(full)
        except OSError:
            continue
        lines.append(f"{label}/{rel} ({size:,} bytes)")
        if len(lines) >= MAX_LIST:
            lines.append("... (list truncated)")
            break
    if not lines:
        return (
            "No files available. Add files to the repo's knowledge/ folder "
            "and redeploy, or place them in the uploads directory."
        )
    return "\n".join(lines)


def read_file(path: str) -> str:
    """Read a text file's contents (truncated if very long)."""
    full = _resolve(path)
    if not os.path.isfile(full):
        raise ValueError(
            f"No such file: {path} — call list_files to see what exists.")
    with open(full, "rb") as f:
        raw = f.read(MAX_READ_CHARS * 4)
    if b"\x00" in raw[:8000]:
        return (
            f"'{path}' looks like a binary file (PDF, image, ...). "
            "Only plain-text files (txt, md, csv, code, ...) are readable for now."
        )
    text = raw.decode("utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + (
            f"\n\n[truncated at {MAX_READ_CHARS:,} characters — the file continues]"
        )
    return text


def search_files(query: str) -> str:
    """Find files whose name or text content contains the query."""
    q = query.lower().strip()
    if not q:
        raise ValueError("Give me a non-empty search query.")
    hits = []
    for label, rel, full in _iter_files():
        if len(hits) >= MAX_SEARCH_RESULTS:
            hits.append("... (more matches not shown)")
            break
        snippet = None
        try:
            with open(full, "rb") as f:
                raw = f.read(1_000_000)
            if b"\x00" not in raw[:8000]:
                text = raw.decode("utf-8", errors="replace")
                idx = text.lower().find(q)
                if idx != -1:
                    start = max(0, idx - 60)
                    snippet = " ".join(text[start: idx + 120].split())
        except OSError:
            continue
        if q in rel.lower():
            hits.append(f"{label}/{rel} (filename match)")
        elif snippet:
            hits.append(f"{label}/{rel} — ...{snippet}...")
    return "\n".join(hits) if hits else f"No files matching '{query}'."


# ------------------------------------------------------------- registry

TOOLS = {
    "list_files": {
        "function": list_files,
        "definition": {
            "name": "list_files",
            "description": (
                "List all files the agent has access to (the repo's knowledge/ "
                "folder and uploaded files). Use before reading or when the user "
                "mentions their files, notes, or documents."
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
    },
    "read_file": {
        "function": read_file,
        "definition": {
            "name": "read_file",
            "description": (
                "Read the contents of one text file. Use paths exactly as shown "
                "by list_files, e.g. 'knowledge/notes.md'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path from list_files, e.g. 'knowledge/notes.md'.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    "search_files": {
        "function": search_files,
        "definition": {
            "name": "search_files",
            "description": (
                "Search all available files by filename and text content. "
                "Returns matching paths with a short snippet."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Case-insensitive text to look for.",
                    }
                },
                "required": ["query"],
            },
        },
    },
}

if os.environ.get("PARALLEL_SEARCH_ENABLED", "").lower() == "true":
    from agent.parallel_search import TOOLS as WEB_TOOLS

    TOOLS.update(WEB_TOOLS)

DEFINITIONS = [t["definition"] for t in TOOLS.values()]


def run(name: str, tool_input: dict, *, session_id=None, model_name=None) -> str:
    """Execute a tool by name. Errors are returned as text so the model
    can recover instead of the whole agent crashing."""
    if name not in TOOLS:
        return f"Tool error: unknown tool '{name}'"
    try:
        arguments = dict(tool_input or {})
        if name in ("web_search", "web_fetch"):
            # Runtime metadata comes from the caller, never model-generated arguments.
            arguments.pop("session_id", None)
            arguments.pop("model_name", None)
            if session_id:
                arguments["session_id"] = session_id
            if model_name:
                arguments["model_name"] = model_name
        return str(TOOLS[name]["function"](**arguments))
    except Exception as exc:  # noqa: BLE001 — surface anything to the model
        return f"Tool error: {exc}"
