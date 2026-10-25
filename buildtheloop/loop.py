import argparse
import json
import os
from pathlib import Path
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4
from openai import OpenAI

# 127.0.0.1:11434

BASE_URL = os.getenv("LOOP_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.getenv("LOOP_API_KEY", "lm-studio")
MODEL = os.getenv("LOOP_MODEL", "qwen3.5:35b-a3b")
WORKSPACE = Path.cwd().resolve()

MAX_TURNS = 12
MAX_TOOL_CALLS = 24

PROJECT_CONTEXT_PATH = ".loop/PROJECT.md"
MAX_INIT_FILES = 120
MAX_DOC_PREVIEW_CHARS = 2000
MEMORY_PATH = ".loop/memory.json"
RUN_PATH = ".loop/RUN.md"
MAX_FIELD_CHARS = 500
MAX_RECENT_RESULTS = 12


client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
session_approvals: set[str] = set()

IGNORED_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}

INTERNAL_DIR = WORKSPACE / ".loop"

@dataclass
class Memory:
    id: str
    text: str
    kind: str
    scope: str
    created_at: str

def memory_path(workspace: Path) -> Path:
    return workspace / MEMORY_PATH

def run_path(workspace: Path) -> Path:
    return workspace / RUN_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def shorten(value: object, limit: int = MAX_FIELD_CHARS) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."

def collect_tool_results(messages: list[dict]) -> list[dict]:
    arguments_by_id = {}
    for message in messages:
        for tool_call in message.get("tool_calls") or []:
            try:
                arguments = json.loads(
                    tool_call.get("function", {}).get("arguments") or "{}"
                )
            except json.JSONDecodeError:
                arguments = {}
            arguments_by_id[tool_call.get("id")] = arguments

    results = []
    for message in messages:
        if message.get("role") != "tool":
            continue
        try:
            result = json.loads(message.get("content", "{}"))
        except json.JSONDecodeError:
            continue
        path = arguments_by_id.get(message.get("tool_call_id"), {}).get("path")
        if path:
            result.setdefault("path", path)
        results.append(result)
    return results

def unique(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def compact_history(
    task: str,
    messages: list[dict],
    *,
    stop_reason: str = "unknown",
) -> str:
    results = collect_tool_results(messages)
    recent = results[-MAX_RECENT_RESULTS:]
    files = unique(
        [
            str(result.get("path") or result.get("file") or "")
            for result in results
        ]
    )
    tools = unique([str(result.get("tool") or "tool") for result in results])
    failures = [result for result in results if not result.get("ok", True)]

    lines = [
        "# Run Handoff",
        "",
        f"Updated: `{now_iso()}`",
        f"Stop reason: `{stop_reason}`",
        "",
        "## Goal",
        "",
        task,
        "",
        "## Tools Used",
        "",
    ]
    lines.extend(f"- `{tool}`" for tool in tools or ["None recorded."])

    lines.extend(["", "## Files Mentioned", ""])
    lines.extend(f"- `{path}`" for path in files or ["None recorded."])

    lines.extend(["", "## Recent Tool Results", ""])
    for result in recent:
        tool = result.get("tool", "tool")
        ok = "ok" if result.get("ok", True) else "failed"
        detail = result.get("message") or result.get("result") or ""
        lines.append(f"- `{tool}` {ok}: {shorten(detail)}")

    lines.extend(["", "## Failures To Keep In Mind", ""])
    if failures:
        for result in failures[-5:]:
            tool = result.get("tool", "tool")
            error = result.get("message") or result.get("error_type") or "unknown"
            lines.append(f"- `{tool}` failed: {shorten(error)}")
    else:
        lines.append("- None recorded.")

    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "- Continue from this handoff, but verify current files before editing.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_handoff(
    workspace: Path,
    task: str,
    messages: list[dict],
    *,
    stop_reason: str = "unknown",
) -> Path:
    path = run_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(compact_history(task, messages, stop_reason=stop_reason))
    return path


def build_messages_from_handoff(task: str, workspace: Path) -> list[dict]:
    handoff = run_path(workspace)
    context = ""
    if handoff.exists():
        context = handoff.read_text()

    user_content = task
    if context:
        user_content = f"Run handoff:\n{context}\n\nUser task:\n{task}"

    return [
        {
            "role": "system",
            "content": "You are a careful coding agent. Verify stale context.",
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]

def load_memories(workspace: Path) -> list[Memory]:
    path = memory_path(workspace)
    if not path.exists():
        return []

    raw = json.loads(path.read_text())
    return [Memory(**item) for item in raw]


def save_memories(workspace: Path, memories: list[Memory]) -> None:
    path = memory_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(memory) for memory in memories]
    path.write_text(json.dumps(data, indent=2) + "\n")


def remember(
    workspace: Path,
    text: str,
    *,
    kind: str = "semantic",
    scope: str = "project",
) -> Memory:
    memories = load_memories(workspace)
    memory = Memory(
        id=uuid4().hex[:8],
        text=text.strip(),
        kind=kind,
        scope=scope,
        created_at=now_iso(),
    )
    memories.append(memory)
    save_memories(workspace, memories)
    return memory


def forget(workspace: Path, memory_id: str) -> bool:
    memories = load_memories(workspace)
    kept = [memory for memory in memories if memory.id != memory_id]
    if len(kept) == len(memories):
        return False
    save_memories(workspace, kept)
    return True


def update_memory(workspace: Path, memory_id: str, text: str) -> bool:
    memories = load_memories(workspace)
    for memory in memories:
        if memory.id == memory_id:
            memory.text = text.strip()
            save_memories(workspace, memories)
            return True
    return False


def search_memories(
    workspace: Path,
    query: str,
    *,
    limit: int = 8,
) -> list[Memory]:
    words = {word.lower() for word in query.split() if len(word) > 2}
    if not words:
        return []

    scored = []
    for memory in load_memories(workspace):
        text = memory.text.lower()
        score = sum(1 for word in words if word in text)
        if score:
            scored.append((score, memory))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [memory for _, memory in scored[:limit]]


def render_memory_context(memories: list[Memory]) -> str:
    if not memories:
        return ""

    lines = ["Relevant saved memories:"]
    for memory in memories:
        lines.append(f"- [{memory.scope}/{memory.kind}] {memory.text}")
    return "\n".join(lines)


def build_context(task: str, workspace: Path) -> str:
    memories = search_memories(workspace, task)
    memory_context = render_memory_context(memories)
    if not memory_context:
        return task
    return f"{memory_context}\n\nUser task:\n{task}"


def build_messages(task: str, workspace: Path) -> list[dict]:
    return [
        {
            "role": "system",
            "content": "You are a careful coding agent.",
        },
        {
            "role": "user",
            "content": build_context(task, workspace),
        },
    ]

def context_path(workspace: Path) -> Path:
    return workspace / PROJECT_CONTEXT_PATH


def should_skip_project_path(workspace: Path, path: Path) -> bool:
    relative = path.relative_to(workspace)
    parts = set(relative.parts)
    if parts & {".git", ".venv", "__pycache__", ".pytest_cache", ".loop"}:
        return True
    return relative.as_posix() == "memory.json"


def collect_project_files(workspace: Path) -> list[Path]:
    files = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or should_skip_project_path(workspace, path):
            continue
        files.append(path)
        if len(files) >= MAX_INIT_FILES:
            break
    return files


def read_preview(path: Path) -> str:
    try:
        content = path.read_text(errors="replace")
    except OSError as error:
        return f"[could not read: {type(error).__name__}: {error}]"

    if len(content) <= MAX_DOC_PREVIEW_CHARS:
        return content.strip()
    return content[:MAX_DOC_PREVIEW_CHARS].strip() + "\n...[truncated]"


def detect_project_kind(files: list[Path]) -> list[str]:
    names = {path.name for path in files}
    kinds = []
    if "pyproject.toml" in names or "requirements.txt" in names:
        kinds.append("Python")
    if any(path.suffix == ".py" for path in files):
        kinds.append("Python")
    if "package.json" in names:
        kinds.append("Node.js")
    if "Cargo.toml" in names:
        kinds.append("Rust")
    if "go.mod" in names:
        kinds.append("Go")
    return sorted(set(kinds)) or ["unknown"]


def render_project_context(workspace: Path, files: list[Path]) -> str:
    rel_files = [path.relative_to(workspace).as_posix() for path in files]
    docs = [
        path
        for path in files
        if path.name.lower().startswith("readme")
        or path.name in {"AGENTS.md", "CONTEXT.md", "requirements.txt", "pyproject.toml"}
        or "/docs/adr/" in path.as_posix()
    ]
    source_files = [
        rel for rel in rel_files if rel.endswith((".py", ".js", ".ts", ".tsx", ".jsx"))
    ]
    test_files = [
        rel for rel in rel_files if "/test_" in f"/{rel}" or rel.startswith("test_")
    ]

    lines = [
        "# Project Context",
        "",
        "Generated by `loop /init`.",
        "",
        "## Root",
        "",
        f"`{workspace}`",
        "",
        "## Detected Shape",
        "",
        "- " + ", ".join(detect_project_kind(files)),
        "",
        "## Important Files",
        "",
    ]
    lines.extend(f"- `{rel}`" for rel in rel_files[:MAX_INIT_FILES])

    lines.extend(["", "## Source Files", ""])
    lines.extend(f"- `{rel}`" for rel in source_files[:50] or ["None detected."])

    lines.extend(["", "## Test Files", ""])
    lines.extend(f"- `{rel}`" for rel in test_files[:50] or ["None detected."])

    lines.extend(["", "## Document Previews", ""])
    for doc in docs[:10]:
        rel = doc.relative_to(workspace).as_posix()
        lines.extend([f"### `{rel}`", "", "```text", read_preview(doc), "```", ""])

    lines.extend(
        [
            "## Notes For The Agent",
            "",
            "- Use this file as orientation, not as ground truth when code has changed.",
            "- Re-run `/init` after meaningful structure changes.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def initialize_project_context(workspace: Path) -> Path:
    files = collect_project_files(workspace)
    content = render_project_context(workspace, files)
    output = context_path(workspace)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content)
    return output

class ToolError(Exception):
    def __init__(self, error_type: str, message: str, retryable: bool):
        self.error_type = error_type
        self.message = message
        self.retryable = retryable


def safe_path(path: str) -> Path:
    resolved = (WORKSPACE / path).resolve()
    if not resolved.is_relative_to(WORKSPACE):
        raise ToolError(
            "permission",
            "Path escapes the workspace.",
            retryable=False,
        )
    return resolved


def list_dir(path: str) -> list[str]:
    target = safe_path(path)
    return sorted(
        p.name
        for p in target.iterdir()
        if p.name not in IGNORED_NAMES
    )


def read_file(path: str) -> str:
    target = safe_path(path)
    return target.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {path}"


TOOL_FUNCTIONS = {
    "list_dir": list_dir,
    "read_file": read_file,
    "write_file": write_file,
}

REQUIRED_ARGUMENTS = {
    "list_dir": ["path"],
    "read_file": ["path"],
    "write_file": ["path", "content"],
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": (
                "List visible files and folders inside the workspace. "
                "Use this to inspect project structure. "
                "Path must be relative to the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to the workspace.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a UTF-8 text file from the workspace. "
                "Use this when you need exact file contents. "
                "Path must be relative to the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the workspace.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write a UTF-8 text file inside the workspace. "
                "Use this only when the task requires changing or creating a file. "
                "Path must be relative to the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to the workspace.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete text content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
]


def parse_arguments(raw_arguments: str) -> dict:
    try:
        parsed = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError as error:
        raise ToolError(
            "invalid_tool_arguments",
            f"Arguments were not valid JSON: {error}",
            retryable=True,
        )
    if not isinstance(parsed, dict):
        raise ToolError(
            "invalid_tool_arguments",
            "Arguments must be a JSON object.",
            retryable=True,
        )
    return parsed


def require(arguments: dict, *names: str) -> None:
    missing = [name for name in names if name not in arguments]
    if missing:
        raise ToolError(
            "missing_arguments",
            f"Missing required arguments: {', '.join(missing)}",
            retryable=True,
        )


def validate_tool_call(name: str, arguments: dict) -> None:
    if name not in REQUIRED_ARGUMENTS:
        raise ToolError("unknown_tool", f"Unknown tool: {name}", False)
    require(arguments, *REQUIRED_ARGUMENTS[name])


SENSITIVE_PATHS = (
    ".env",
    "secrets/",
)

INTERNAL_PATHS = (
    ".loop/",
)

SOURCE_PATHS = (
    "src/",
    "tests/",
)

def allow() -> dict:
    return {"decision": "allow"}


def deny(message: str) -> dict:
    return {
        "decision": "deny",
        "message": message,
        "retryable": False,
    }


def ask(message: str, risk: str, rule_hint: str) -> dict:
    return {
        "decision": "ask",
        "message": message,
        "risk": risk,
        "rule_hint": rule_hint,
        "approval_scopes": ["once", "session", "always"],
        "retryable": False,
    }
def path_starts_with(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def check_policy(name: str, arguments: dict) -> dict:
    path = arguments.get("path", "")

    if name == "read_file" and path_starts_with(path, SENSITIVE_PATHS):
        return deny("The agent may not read sensitive files.")

    if name == "write_file" and path_starts_with(path, INTERNAL_PATHS):
        return deny("The agent may not write internal loop state.")

    if name == "write_file" and path_starts_with(path, SENSITIVE_PATHS):
        return deny("The agent may not write secrets.")

    if name == "write_file" and path_starts_with(path, SOURCE_PATHS):
        return ask(
            message=f"The agent wants to modify source code: {path}",
            risk="changes code that may affect behavior",
            rule_hint=f"write_file:{path}",
        )

    return allow()

def prompt_for_approval(policy: dict) -> bool:
    rule_hint = policy.get("rule_hint")
    if rule_hint in session_approvals:
        return True

    print("\nApproval needed")
    print(policy["message"])
    print(f"Risk: {policy.get('risk', 'unknown')}")
    print("\nAllow?")
    print("  y  yes, once")
    print("  s  yes, for this session")
    print("  n  no")

    choice = input("> ").strip().lower()
    if choice == "s" and rule_hint:
        session_approvals.add(rule_hint)
        return True
    return choice == "y"

def policy_to_tool_result(name: str, policy: dict) -> dict:
    return {
        "ok": False,
        "tool": name,
        "error_type": "permission",
        "message": policy["message"],
        "retryable": policy.get("retryable", False),
        "needs_approval": policy["decision"] == "ask",
        "risk": policy.get("risk"),
        "rule_hint": policy.get("rule_hint"),
        "approval_scopes": policy.get("approval_scopes", []),
    }


def normalize_result(name: str, result) -> dict:
    return {"ok": True, "tool": name, "result": result}


def error_result(name: str, error: ToolError) -> dict:
    return {
        "ok": False,
        "tool": name,
        "error_type": error.error_type,
        "message": error.message,
        "retryable": error.retryable,
    }


def execute_tool(name: str, arguments: dict):
    kwargs = {key: arguments[key] for key in REQUIRED_ARGUMENTS[name]}
    return TOOL_FUNCTIONS[name](**kwargs)


def handle_tool_call(tool_call) -> dict:
    name = tool_call.function.name
    try:
        arguments = parse_arguments(tool_call.function.arguments)
        validate_tool_call(name, arguments)
        policy = check_policy(name, arguments)

        if policy["decision"] == "deny":
            return policy_to_tool_result(name, policy)

        if policy["decision"] == "ask" and not prompt_for_approval(policy):
            return policy_to_tool_result(name, policy)

        result = execute_tool(name, arguments)
        return normalize_result(name, result)
    except ToolError as error:
        return error_result(name, error)


def log_event(event: dict) -> None:
    print(json.dumps(event))


def call_model(messages: list[dict]):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    return response.choices[0].message


def run_agent(task: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a tiny coding agent. Use tools when you need to inspect "
                "or change the workspace. Paths must stay inside the workspace. "
                "When you have enough information, answer clearly."
            ),
        },
        {"role": "user", "content": task},
    ]    
    tool_call_count = 0
    stop_reason = "max_turns"

    for turn in range(MAX_TURNS):
        log_event({"type": "model_call", "turn": turn})
        message = call_model(messages)
        messages.append(message.model_dump(exclude_none=True))

        if message.content:
            print("\nassistant:")
            print(message.content)

        if not message.tool_calls:
            stop_reason = "final_answer"
            break

        for tool_call in message.tool_calls:
            tool_call_count += 1
            if tool_call_count > MAX_TOOL_CALLS:
                stop_reason = "tool_budget_exceeded"
                break

            result = handle_tool_call(tool_call)
            log_event(
                {
                    "type": "tool_result",
                    "turn": turn,
                    "tool": result.get("tool"),
                    "ok": result["ok"],
                    "error_type": result.get("error_type"),
                }
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

        if stop_reason != "max_turns":
            break

    return {
        "messages": messages,
        "stop_reason": stop_reason,
        "tool_call_count": tool_call_count,
    }



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the tiny coding agent loop.")
    parser.add_argument("task", help="The task for the agent to perform.")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory the agent can inspect and edit.",
    )
    return parser.parse_args()


def main() -> int:
    global WORKSPACE

    args = parse_args()
    WORKSPACE = Path(args.workspace).expanduser().resolve()
    if not WORKSPACE.exists() or not WORKSPACE.is_dir():
        print(f"Workspace does not exist: {WORKSPACE}", file=sys.stderr)
        return 3

    print(f"Workspace: {WORKSPACE}")
    result = run_agent(args.task)
    print(f"\nStopped because: {result['stop_reason']}")

    if result["stop_reason"] == "final_answer":
        return 0
    if result["stop_reason"] in {"max_turns", "tool_budget_exceeded"}:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())