"""
research_agent/agent.py
========================
Core agentic pipeline with 6 stages:
  1. Planning        — decompose topic into research questions
  2. Searching       — web search via Tavily for each question
  3. Synthesizing    — rank & organize findings
  4. Drafting        — write structured first draft
  5. Reflecting      — editor agent reviews for coherence & gaps
  6. Revising        — improve draft based on editorial feedback

Each stage is a separate LLM call (or tool call), demonstrating the
agentic workflow design patterns: reflection, tool use, planning,
and multi-agent collaboration.

LLM Provider: Sarvam AI (OpenAI-compatible API)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import openai
from tavily import TavilyClient
import history as _history

SARVAM_BASE_URL = "https://api.sarvam.ai/v1"
SARVAM_DEFAULT_MODEL = "sarvam-m"
SARVAM_CONTEXT_LIMIT = 7192   # max context tokens for sarvam-m
SARVAM_MAX_RESPONSE = 1024    # tokens reserved for response
SARVAM_MAX_PROMPT_CHARS = (SARVAM_CONTEXT_LIMIT - SARVAM_MAX_RESPONSE) * 3  # ~3 chars/token


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    """Output of a single pipeline stage."""
    stage: str
    title: str
    icon: str
    content: str
    elapsed: float = 0.0


@dataclass
class AgentState:
    """Full state carried through the pipeline."""
    topic: str
    plan: str = ""
    raw_research: str = ""
    synthesis: str = ""
    draft: str = ""
    critique: str = ""
    final_report: str = ""
    stages: list[StageResult] = field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _call_llm(
    client: openai.OpenAI,
    system: str,
    user: str,
    model: str = SARVAM_DEFAULT_MODEL,
    max_tokens: int = SARVAM_MAX_RESPONSE,
) -> str:
    """Single Sarvam AI API call (OpenAI-compatible). Returns assistant text."""
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Web search helper
# ---------------------------------------------------------------------------

def _search_web(tavily: TavilyClient, queries: list[str], max_results: int = 2) -> str:
    """Run multiple Tavily searches and merge results."""
    all_results: list[str] = []
    seen_urls: set[str] = set()

    for query in queries:
        try:
            resp = tavily.search(query=query, max_results=max_results, include_raw_content=False)
            for r in resp.get("results", []):
                url = r.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                title = r.get("title", "Untitled")
                snippet = r.get("content", "")
                all_results.append(f"**{title}**\nURL: {url}\n{snippet}")
        except Exception as e:
            all_results.append(f"[Search error for '{query}': {e}]")

    return "\n\n---\n\n".join(all_results) if all_results else "No results found."


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def stage_planning(state: AgentState, client: openai.OpenAI) -> StageResult:
    t0 = time.time()
    state.plan = _call_llm(
        client,
        system=(
            "You are a research planning agent. Given a topic, produce:\n"
            "1. A one-sentence summary of the research goal.\n"
            "2. 4-6 specific, focused research questions that together would cover "
            "the topic comprehensively.\n"
            "3. For each question, suggest 1-2 concise web search queries.\n\n"
            "Format the output clearly with numbered questions and search queries."
        ),
        user=f"Topic: {state.topic}\n\nGenerate a research plan.",
    )
    return StageResult("planning", "Planning", "🧭", state.plan, time.time() - t0)


def stage_searching(
    state: AgentState,
    client: openai.OpenAI,
    tavily: TavilyClient,
) -> StageResult:
    t0 = time.time()

    # Ask LLM to extract search queries from the plan
    queries_raw = _call_llm(
        client,
        system=(
            "Extract all the web search queries from the research plan below. "
            "Return ONLY the queries, one per line, no numbering, no extra text."
        ),
        user=state.plan,
        max_tokens=512,
    )
    queries = [q.strip() for q in queries_raw.strip().splitlines() if q.strip()]
    if not queries:
        queries = [state.topic]

    # Limit to 8 queries to stay within reasonable API usage
    queries = queries[:8]

    state.raw_research = _search_web(tavily, queries)
    summary = f"Ran {len(queries)} searches. Found {state.raw_research.count('---') + 1} unique sources."
    return StageResult("searching", "Researching", "🔍", summary, time.time() - t0)


def stage_synthesizing(state: AgentState, client: openai.OpenAI) -> StageResult:
    t0 = time.time()
    # Truncate raw_research to stay within sarvam-m context window
    system_prompt = (
        "You are a research synthesis agent. Analyze the raw search results below "
        "and produce a structured synthesis:\n"
        "1. **Key Findings** — the most important facts, data points, and insights, "
        "organized by theme.\n"
        "2. **Conflicting Information** — note where sources disagree.\n"
        "3. **Gaps** — identify questions that remain unanswered.\n"
        "4. **Source Quality** — rank sources by reliability.\n\n"
        "Be thorough and specific. Cite source titles when referencing information."
    )
    prefix = f"Topic: {state.topic}\n\nResearch Plan:\n{state.plan}\n\nRaw Search Results:\n"
    budget = SARVAM_MAX_PROMPT_CHARS - len(system_prompt) - len(prefix)
    truncated_research = state.raw_research[:max(budget, 500)]
    state.synthesis = _call_llm(
        client,
        system=system_prompt,
        user=prefix + truncated_research,
    )
    return StageResult("synthesizing", "Synthesizing", "🧪", state.synthesis, time.time() - t0)


def stage_drafting(state: AgentState, client: openai.OpenAI) -> StageResult:
    t0 = time.time()
    state.draft = _call_llm(
        client,
        system=(
            "You are a report-writing agent. Write a comprehensive, well-structured "
            "research report in Markdown. Include:\n"
            "- **Title** (# heading)\n"
            "- **Executive Summary** — 2-3 paragraph overview\n"
            "- **Background** — context and importance\n"
            "- **Key Findings** — organized by theme (## subsections)\n"
            "- **Analysis** — deeper interpretation, implications\n"
            "- **Conclusion** — summary and forward-looking remarks\n"
            "- **Sources** — list of referenced sources\n\n"
            "Write in a professional but accessible tone. Be thorough and cite "
            "specific facts from the research. Aim for depth, not breadth."
        ),
        user=(
            f"Topic: {state.topic}\n\n"
            f"Research Plan:\n{state.plan}\n\n"
            f"Synthesized Findings:\n{state.synthesis}"
        ),
    )
    return StageResult("drafting", "Drafting", "✍️", "First draft complete.", time.time() - t0)


def stage_reflecting(state: AgentState, client: openai.OpenAI) -> StageResult:
    t0 = time.time()
    state.critique = _call_llm(
        client,
        system=(
            "You are an editorial review agent — a senior editor reviewing a research "
            "report. Critically evaluate the draft for:\n"
            "1. **Logical Coherence** — does the argument flow?\n"
            "2. **Factual Support** — are claims backed by evidence?\n"
            "3. **Coverage Gaps** — what important aspects are missing?\n"
            "4. **Structural Issues** — is the organization effective?\n"
            "5. **Depth** — where does the report stay too surface-level?\n"
            "6. **Tone & Clarity** — is the writing clear and professional?\n\n"
            "Provide 5-8 specific, actionable recommendations for improvement. "
            "Be constructive but rigorous."
        ),
        user=f"Review this research report draft:\n\n{state.draft}",
    )
    return StageResult("reflecting", "Reflecting", "🪞", state.critique, time.time() - t0)


def stage_revising(state: AgentState, client: openai.OpenAI) -> StageResult:
    t0 = time.time()
    state.final_report = _call_llm(
        client,
        system=(
            "You are a report revision agent. Take the draft and the editorial "
            "feedback and produce a polished, improved final report.\n\n"
            "Requirements:\n"
            "- Address EVERY point from the editorial feedback.\n"
            "- Maintain Markdown formatting (# title, ## sections, ### subsections, "
            "bullet points, bold for emphasis).\n"
            "- The final report should be comprehensive (1500-3000 words), "
            "well-organized, and insightful.\n"
            "- End with a 'Sources' section listing referenced sources."
        ),
        user=(
            f"Original draft:\n{state.draft}\n\n"
            f"Editorial feedback:\n{state.critique}\n\n"
            f"Produce the improved final report."
        ),
    )
    return StageResult("revising", "Revising", "🔧", "Final report ready.", time.time() - t0)


# ---------------------------------------------------------------------------
# Full pipeline runner
# ---------------------------------------------------------------------------

STAGE_SEQUENCE = [
    ("planning",     "🧭 Planning — Decomposing topic into research questions..."),
    ("searching",    "🔍 Researching — Searching the web for sources..."),
    ("synthesizing", "🧪 Synthesizing — Ranking and organizing findings..."),
    ("drafting",     "✍️ Drafting — Writing the first draft..."),
    ("reflecting",   "🪞 Reflecting — Editor reviewing for coherence & gaps..."),
    ("revising",     "🔧 Revising — Improving based on editorial feedback..."),
]


def run_pipeline(
    topic: str,
    sarvam_key: str,
    tavily_key: str,
    on_stage_start: Optional[Callable[[int, str], None]] = None,
    on_stage_end: Optional[Callable[[int, StageResult], None]] = None,
    model: str = SARVAM_DEFAULT_MODEL,
    use_cache: bool = True,
) -> AgentState:
    """
    Execute the full 6-stage agentic research pipeline.

    Parameters
    ----------
    topic : str
        The research topic.
    sarvam_key : str
        Sarvam AI API key.
    tavily_key : str
        Tavily search API key.
    on_stage_start : callback(stage_index, status_message)
    on_stage_end   : callback(stage_index, StageResult)
    model : str
        Sarvam model to use (default: sarvam-m).
    use_cache : bool
        If True, return cached result when topic was researched before.

    Returns
    -------
    AgentState with all fields populated (including .final_report).
    """
    # ---- Cache lookup -------------------------------------------------------
    if use_cache:
        cached = _history.get(topic)
        if cached and cached.get("final_report"):
            state = AgentState(
                topic=cached["topic"],
                plan=cached.get("plan", ""),
                raw_research=cached.get("raw_research", ""),
                synthesis=cached.get("synthesis", ""),
                draft=cached.get("draft", ""),
                critique=cached.get("critique", ""),
                final_report=cached["final_report"],
            )
            # Replay on_end callbacks so UI renders stage cards from cache
            cached_stages = cached.get("stages", [])
            for i, (stage_id, status_msg) in enumerate(STAGE_SEQUENCE):
                if on_stage_start:
                    on_stage_start(i, status_msg)
                if i < len(cached_stages):
                    s = cached_stages[i]
                    result = StageResult(
                        stage=s["stage"], title=s["title"],
                        icon=s["icon"], content=s["content"],
                        elapsed=s.get("elapsed", 0.0),
                    )
                else:
                    result = StageResult(stage_id, stage_id.title(), "✓", "(from cache)")
                state.stages.append(result)
                if on_stage_end:
                    on_stage_end(i, result)
            return state
    # ---- Fresh pipeline run -------------------------------------------------
    client = openai.OpenAI(api_key=sarvam_key, base_url=SARVAM_BASE_URL)
    tavily = TavilyClient(api_key=tavily_key)
    state = AgentState(topic=topic)

    stage_funcs = [
        lambda s: stage_planning(s, client),
        lambda s: stage_searching(s, client, tavily),
        lambda s: stage_synthesizing(s, client),
        lambda s: stage_drafting(s, client),
        lambda s: stage_reflecting(s, client),
        lambda s: stage_revising(s, client),
    ]

    for i, (stage_id, status_msg) in enumerate(STAGE_SEQUENCE):
        if on_stage_start:
            on_stage_start(i, status_msg)
        try:
            result = stage_funcs[i](state)
            state.stages.append(result)
            if on_stage_end:
                on_stage_end(i, result)
        except Exception as e:
            state.error = f"Stage '{stage_id}' failed: {e}"
            if on_stage_end:
                on_stage_end(i, StageResult(stage_id, stage_id.title(), "❌", str(e)))
            break

    # ---- Persist to history if successful -----------------------------------
    if not state.error:
        _history.save(topic, {
            "topic": state.topic,
            "plan": state.plan,
            "raw_research": state.raw_research,
            "synthesis": state.synthesis,
            "draft": state.draft,
            "critique": state.critique,
            "final_report": state.final_report,
            "stages": [
                {"stage": r.stage, "title": r.title,
                 "icon": r.icon, "content": r.content, "elapsed": r.elapsed}
                for r in state.stages
            ],
        })

    return state
