"""Memory hook — automatic detection and persistence of important information.

Three-tier design:
1. MemorySaveTool — explicit user-triggered save ("记住", "记一下", "record this")
2. MemoryHook — automatic detection after tool calls (new patterns, user corrections)
3. MemoryIndex — maintain DEEPSEEK.md index so system prompt stays aware
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


# ── Memory file mapping ──

_MEMORY_MAP = {
    "coding": {
        "file": "memory/feedback.md",
        "triggers": ["编码", "代码", "coding", "bug", "报错", "坑", "习惯", "prefer"],
        "description": "编码偏好、踩坑记录、用户习惯",
    },
    "investment": {
        "file": "memory/project_investment_philosophy.md",
        "triggers": ["投资", "排除", "选股", "判断", "框架", "investment", "exclude", "philosophy"],
        "description": "投资排除原则、判断框架",
    },
    "valuation": {
        "file": "memory/project_valuation_framework.md",
        "triggers": ["估值", "PEG", "阈值", "低洼", "valuation", "threshold"],
        "description": "估值逻辑、PEG阈值、低洼标准",
    },
    "workflow": {
        "file": "memory/workflow.md",
        "triggers": ["流程", "工具", "workflow", "pipeline", "步骤", "step"],
        "description": "分析流程、工具能力边界",
    },
    "accuracy": {
        "file": "docs/accuracy_log.md",
        "triggers": ["判断", "预测", "验证", "accuracy", "prediction", "验证"],
        "description": "可验证的投资判断记录",
    },
    "lessons": {
        "file": "docs/analysis_lessons.md",
        "triggers": ["教训", "方法论", "lesson", "methodology", "经验"],
        "description": "分析方法论教训",
    },
    "tasks": {
        "file": "memory/project_tasks.md",
        "triggers": ["任务", "待办", "todo", "task", "继续"],
        "description": "跨会话任务清单",
    },
    "general": {
        "file": "memory/feedback.md",
        "triggers": [],  # fallback
        "description": "通用记忆（fallback）",
    },
}


def classify_memory(content: str) -> str:
    """Classify content into a memory category based on keywords."""
    lower = content.lower()
    for key, info in _MEMORY_MAP.items():
        if key == "general":
            continue
        for trigger in info["triggers"]:
            if trigger.lower() in lower:
                return key
    return "general"


def get_memory_file(category: str, project_dir: str) -> Path:
    """Get the full path to a memory file by category."""
    info = _MEMORY_MAP.get(category, _MEMORY_MAP["general"])
    return Path(project_dir) / info["file"]


def append_to_memory(
    project_dir: str,
    category: str,
    content: str,
    source: str = "auto",
) -> dict:
    """Append a memory entry to the appropriate file.

    Args:
        project_dir: Project root directory
        category: Memory category key
        content: The content to remember
        source: "auto" (detected) or "manual" (user-triggered)

    Returns:
        dict with status, file_path, category
    """
    file_path = get_memory_file(category, project_dir)
    info = _MEMORY_MAP.get(category, _MEMORY_MAP["general"])

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Format the entry
    date_str = datetime.now().strftime("%Y-%m-%d")
    entry = (
        f"\n---\n"
        f"### {date_str} ({source})\n\n"
        f"{content.strip()}\n"
    )

    # Append to file
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(entry)
        return {
            "status": "ok",
            "file_path": str(file_path),
            "category": category,
            "description": info["description"],
        }
    except OSError as e:
        return {
            "status": "error",
            "error": str(e),
            "file_path": str(file_path),
        }


# ── Auto-detection logic ──

_PATTERN_NEW_KNOWLEDGE = re.compile(
    r"(发现|发现了一个|学到了|踩坑|注意|记住|规律|规则|原则|"
    r"found|learned|noticed|remember|rule|principle|pattern|坑|教训)",
    re.IGNORECASE,
)

_PATTERN_USER_CORRECTION = re.compile(
    r"(不对|不是|错了|纠正|更正|应该说|应该是|"
    r"wrong|incorrect|correction|actually|should be|not correct)",
    re.IGNORECASE,
)

_PATTERN_WORKFLOW_CHANGE = re.compile(
    r"(流程变了|改用|以后用|不再用|换成|"
    r"change workflow|use instead|replace|switch to|不再)",
    re.IGNORECASE,
)


def detect_memory_candidates(
    user_input: str,
    assistant_response: str,
    tool_results: list[str],
) -> list[dict]:
    """Detect if the conversation contains information worth remembering.

    Returns list of dicts with:
        - category: str
        - content: str
        - confidence: float (0-1)
        - reason: str
    """
    candidates = []

    # 1. Check user input for correction patterns
    if _PATTERN_USER_CORRECTION.search(user_input):
        # User corrected the AI — this is high-value memory
        candidates.append({
            "category": classify_memory(user_input),
            "content": f"User correction: {user_input.strip()[:500]}",
            "confidence": 0.9,
            "reason": "user_correction",
        })

    # 2. Check assistant response for new knowledge discovery
    if _PATTERN_NEW_KNOWLEDGE.search(assistant_response):
        # Extract the relevant paragraph
        paragraphs = assistant_response.split("\n\n")
        for p in paragraphs:
            if _PATTERN_NEW_KNOWLEDGE.search(p) and len(p) > 30:
                candidates.append({
                    "category": classify_memory(p),
                    "content": p.strip()[:500],
                    "confidence": 0.7,
                    "reason": "new_knowledge",
                })

    # 3. Check for workflow/tool changes
    if _PATTERN_WORKFLOW_CHANGE.search(user_input) or _PATTERN_WORKFLOW_CHANGE.search(assistant_response):
        candidates.append({
            "category": "workflow",
            "content": f"Workflow change detected:\nUser: {user_input[:300]}\nAI: {assistant_response[:300]}",
            "confidence": 0.8,
            "reason": "workflow_change",
        })

    # 4. Check tool results for error patterns worth remembering
    for result in tool_results:
        if "error" in result.lower() or "fail" in result.lower() or "not found" in result.lower():
            if len(result) > 20 and len(result) < 500:
                candidates.append({
                    "category": "coding",
                    "content": f"Tool error pattern: {result.strip()[:300]}",
                    "confidence": 0.5,
                    "reason": "tool_error_pattern",
                })

    return candidates


def should_auto_save(candidates: list[dict], min_confidence: float = 0.7) -> list[dict]:
    """Filter memory candidates by confidence threshold for auto-save."""
    return [c for c in candidates if c["confidence"] >= min_confidence]


# ── Memory index maintenance ──

def update_memory_index(project_dir: str) -> dict:
    """Update DEEPSEEK.md with current memory file index.

    Scans memory/ directory and rebuilds the index section.
    Returns dict with status and file count.
    """
    deepseek_md = Path(project_dir) / "DEEPSEEK.md"
    memory_dir = Path(project_dir) / "memory"

    if not memory_dir.is_dir():
        return {"status": "error", "error": "memory/ directory not found"}

    # Collect all .md files in memory/ (recursive)
    memory_files = []
    for md_file in sorted(memory_dir.rglob("*.md")):
        rel_path = md_file.relative_to(project_dir)
        memory_files.append(str(rel_path).replace("\\", "/"))

    # Build index content
    index_lines = ["\n## Memory Index\n"]
    for mf in memory_files:
        index_lines.append(f"- [{mf}]({mf})")

    index_content = "\n".join(index_lines)

    # Read existing DEEPSEEK.md
    if deepseek_md.exists():
        existing = deepseek_md.read_text(encoding="utf-8")
        # Replace existing index section or append
        if "## Memory Index" in existing:
            before = existing.split("## Memory Index")[0]
            new_content = before.strip() + "\n" + index_content
        else:
            new_content = existing.rstrip() + "\n" + index_content
    else:
        new_content = f"# Project Memory\n\n{index_content}"

    try:
        deepseek_md.write_text(new_content, encoding="utf-8")
        return {
            "status": "ok",
            "file_count": len(memory_files),
            "index_path": str(deepseek_md),
        }
    except OSError as e:
        return {"status": "error", "error": str(e)}
