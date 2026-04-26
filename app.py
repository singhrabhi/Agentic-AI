"""
research_agent/app.py
=====================
Streamlit UI for the Agentic Research Agent.

Run with:
    streamlit run app.py
"""

import os
import time

import streamlit as st
from dotenv import load_dotenv

from agent import run_pipeline, STAGE_SEQUENCE, AgentState
import history as _history


# ---------------------------------------------------------------------------
# Markdown → HTML helper  (used for report rendering)
# ---------------------------------------------------------------------------

def _md_to_html(md: str) -> str:
    """Lightweight Markdown to HTML conversion."""
    try:
        import markdown as md_lib
        return md_lib.markdown(md, extensions=["tables", "fenced_code"])
    except ImportError:
        import html as html_lib
        text = html_lib.escape(md)
        text = text.replace("\n\n", "</p><p>")
        text = text.replace("\n", "<br/>")
        return f"<p>{text}</p>"


# ---------------------------------------------------------------------------
# Config & theme
# ---------------------------------------------------------------------------

load_dotenv()

st.set_page_config(
    page_title="Research Agent — Agentic AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* ---------- Global ---------- */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap');

    .stApp {
        font-family: 'DM Sans', sans-serif;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1628 0%, #111827 100%);
    }
    section[data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] .stTextInput input {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: #f1f5f9 !important;
        border-radius: 10px !important;
    }
    section[data-testid="stSidebar"] .stTextInput input::placeholder {
        color: #64748b !important;
    }

    /* ---------- Stage cards ---------- */
    .stage-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.9rem;
        backdrop-filter: blur(10px);
    }
    .stage-card.active {
        border-color: #06b6d4;
        box-shadow: 0 0 20px rgba(6,182,212,0.08);
    }
    .stage-card.done {
        border-color: rgba(16,185,129,0.3);
    }

    /* ---------- Pipeline tracker ---------- */
    .pipeline-step {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        min-width: 80px;
    }
    .pipeline-dot {
        width: 38px; height: 38px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem;
        border: 2px solid rgba(255,255,255,0.1);
        background: rgba(255,255,255,0.03);
        transition: all 0.3s;
    }
    .pipeline-dot.active {
        border-color: #06b6d4;
        background: rgba(6,182,212,0.15);
        animation: pulse 2s ease-in-out infinite;
    }
    .pipeline-dot.done {
        border-color: #10b981;
        background: rgba(16,185,129,0.12);
    }
    .pipeline-label {
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
        color: #475569;
    }
    .pipeline-label.active { color: #06b6d4; }
    .pipeline-label.done { color: #10b981; }

    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(6,182,212,0.25); }
        50% { box-shadow: 0 0 0 10px rgba(6,182,212,0); }
    }

    /* ---------- Report container ---------- */
    .report-container {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 18px;
        padding: 2rem 2.5rem;
        line-height: 1.8;
        color: #cbd5e1;
    }
    .report-container h1 { color: #f1f5f9; font-family: 'Instrument Serif', Georgia, serif; font-size: 1.8rem; margin-top: 1.5rem; }
    .report-container h2 { color: #e2e8f0; font-family: 'Instrument Serif', Georgia, serif; font-size: 1.4rem; margin-top: 1.4rem; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 0.4rem; }
    .report-container h3 { color: #cbd5e1; font-size: 1.15rem; margin-top: 1.2rem; }
    .report-container strong { color: #e2e8f0; }
    .report-container a { color: #67e8f9; }

    /* ---------- Misc ---------- */
    .hero-badge {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 5px 14px;
        background: rgba(6,182,212,0.08);
        border: 1px solid rgba(6,182,212,0.15);
        border-radius: 99px;
        font-size: 0.75rem; color: #67e8f9;
        letter-spacing: 0.05em; text-transform: uppercase; font-weight: 600;
    }
    .metric-box {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .metric-val {
        font-size: 1.6rem; font-weight: 700; color: #06b6d4;
        font-family: 'JetBrains Mono', monospace;
    }
    .metric-label {
        font-size: 0.7rem; color: #64748b; text-transform: uppercase;
        letter-spacing: 0.06em; margin-top: 4px;
    }

    /* Hide default Streamlit footer & menu */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

DEFAULTS = {
    "agent_state": None,
    "current_stage": -1,
    "running": False,
    "stage_logs": [],
    "from_cache": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------------------------------------------------------------------------
# Sidebar — config & controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<div class="hero-badge">🤖 Agentic Research Agent</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("#### 🔑 API Keys")
    sarvam_key = st.text_input(
        "Sarvam AI API Key",
        value=os.getenv("SARVAM_API_KEY", ""),
        type="password",
        help="Get yours at https://dashboard.sarvam.ai",
    )
    tavily_key = st.text_input(
        "Tavily API Key",
        value=os.getenv("TAVILY_API_KEY", ""),
        type="password",
        help="Get yours at https://tavily.com",
    )

    st.markdown("---")
    st.markdown("#### 🧭 Research Topic")
    topic = st.text_area(
        "What should we research?",
        placeholder="e.g. How is AI transforming drug discovery in 2025?",
        height=100,
        label_visibility="collapsed",
    )

    st.markdown("")
    use_cache = st.toggle("⚡ Use cached results if available", value=True)
    run_btn = st.button(
        "🚀  Start Research",
        use_container_width=True,
        disabled=st.session_state.running,
        type="primary",
    )

    # ---- Research History panel ------------------------------------------
    st.markdown("---")
    st.markdown("#### 📚 Research History")
    history_entries = _history.all_entries()
    if not history_entries:
        st.markdown('<p style="font-size:0.78rem;color:#475569;">No history yet.</p>', unsafe_allow_html=True)
    else:
        for entry in history_entries:
            col_a, col_b = st.columns([5, 1])
            with col_a:
                if st.button(
                    f"📄 {entry['original_topic'][:40]}",
                    key=f"hist_{entry['original_topic']}",
                    use_container_width=True,
                ):
                    st.session_state.agent_state = AgentState(
                        topic=entry["topic"],
                        plan=entry.get("plan", ""),
                        raw_research=entry.get("raw_research", ""),
                        synthesis=entry.get("synthesis", ""),
                        draft=entry.get("draft", ""),
                        critique=entry.get("critique", ""),
                        final_report=entry["final_report"],
                        stages=[
                            __import__('agent').StageResult(
                                stage=s["stage"], title=s["title"],
                                icon=s["icon"], content=s["content"],
                                elapsed=s.get("elapsed", 0.0),
                            ) for s in entry.get("stages", [])
                        ],
                    )
                    st.session_state.stage_logs = st.session_state.agent_state.stages
                    st.session_state.from_cache = True
                    st.rerun()
            with col_b:
                if st.button("🗑️", key=f"del_{entry['original_topic']}", help="Delete"):
                    _history.delete(entry["original_topic"])
                    st.rerun()
            st.markdown(
                f'<p style="font-size:0.68rem;color:#475569;margin-top:-8px;">{entry.get("cached_at","")}</p>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("#### ℹ️ How It Works")
    st.markdown(
        "This agent uses a **6-stage agentic pipeline** — each stage is a "
        "separate LLM call demonstrating the design patterns from the "
        "Agentic AI course:\n\n"
        "1. **Planning** — Task decomposition\n"
        "2. **Searching** — Tool use (Tavily)\n"
        "3. **Synthesizing** — Analysis\n"
        "4. **Drafting** — Generation\n"
        "5. **Reflecting** — Reflection pattern\n"
        "6. **Revising** — Multi-agent collaboration"
    )

    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;font-size:0.7rem;color:#475569;">'
        'Built with Streamlit + Sarvam AI + Tavily</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

# Header
st.markdown(
    '<h1 style="font-family:\'Instrument Serif\',Georgia,serif;font-size:2.4rem;'
    'font-weight:400;margin-bottom:0;color:#f1f5f9;">'
    'Deep Research, <em style="color:#06b6d4;">Autonomously</em></h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#94a3b8;margin-top:0.3rem;margin-bottom:1.5rem;">'
    'Enter a topic in the sidebar and watch the agent plan, search, draft, '
    'reflect, and revise — a full agentic workflow.</p>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Pipeline tracker (always visible once started)
# ---------------------------------------------------------------------------

def render_pipeline_tracker(current: int):
    """Render the horizontal pipeline progress bar."""
    icons = ["🧭", "🔍", "🧪", "✍️", "🪞", "🔧"]
    labels = ["Plan", "Search", "Synthesize", "Draft", "Reflect", "Revise"]
    cols = st.columns(len(icons))
    for i, col in enumerate(cols):
        if i < current:
            cls_dot, cls_lbl = "done", "done"
            icon = "✓"
        elif i == current:
            cls_dot, cls_lbl = "active", "active"
            icon = icons[i]
        else:
            cls_dot, cls_lbl = "", ""
            icon = icons[i]
        col.markdown(
            f'<div class="pipeline-step">'
            f'  <div class="pipeline-dot {cls_dot}">{icon}</div>'
            f'  <div class="pipeline-label {cls_lbl}">{labels[i]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Run the pipeline
# ---------------------------------------------------------------------------

if run_btn:
    # Validate inputs
    if not sarvam_key:
        st.error("Please enter your Sarvam AI API key in the sidebar.")
        st.stop()
    if not tavily_key:
        st.error("Please enter your Tavily API key in the sidebar.")
        st.stop()
    if not topic.strip():
        st.error("Please enter a research topic.")
        st.stop()

    st.session_state.running = True
    st.session_state.stage_logs = []
    st.session_state.current_stage = 0
    st.session_state.agent_state = None

    # Pipeline tracker
    tracker_placeholder = st.empty()
    status_placeholder = st.empty()
    log_container = st.container()

    # Stage output expanders (created upfront)
    stage_placeholders: list[st.delta_generator.DeltaGenerator] = []
    with log_container:
        for i, (sid, msg) in enumerate(STAGE_SEQUENCE):
            stage_placeholders.append(st.empty())

    total_start = time.time()

    def on_start(idx: int, msg: str):
        st.session_state.current_stage = idx
        with tracker_placeholder:
            render_pipeline_tracker(idx)
        status_placeholder.info(msg)

    def on_end(idx: int, result):
        st.session_state.stage_logs.append(result)
        icon = result.icon
        title = result.title
        elapsed = f"{result.elapsed:.1f}s"

        with stage_placeholders[idx]:
            with st.expander(f"{icon}  {title}  —  {elapsed}", expanded=(idx == len(STAGE_SEQUENCE) - 1)):
                st.markdown(result.content)

    # Execute
    state = run_pipeline(
        topic=topic.strip(),
        sarvam_key=sarvam_key,
        tavily_key=tavily_key,
        on_stage_start=on_start,
        on_stage_end=on_end,
        use_cache=use_cache,
    )
    st.session_state.from_cache = use_cache and bool(_history.get(topic.strip()))

    total_elapsed = time.time() - total_start
    st.session_state.agent_state = state
    st.session_state.running = False

    # Final tracker state
    with tracker_placeholder:
        render_pipeline_tracker(len(STAGE_SEQUENCE))
    status_placeholder.empty()

    if state.error:
        st.error(f"Pipeline stopped: {state.error}")
    else:
        if st.session_state.from_cache:
            st.info("⚡ Result loaded from cache — no LLM or web search calls were made.")
        # Metrics
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                f'<div class="metric-box"><div class="metric-val">6</div>'
                f'<div class="metric-label">Agent Stages</div></div>',
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f'<div class="metric-box"><div class="metric-val">{total_elapsed:.0f}s</div>'
                f'<div class="metric-label">Total Time</div></div>',
                unsafe_allow_html=True,
            )
        with m3:
            word_count = len(state.final_report.split())
            st.markdown(
                f'<div class="metric-box"><div class="metric-val">{word_count:,}</div>'
                f'<div class="metric-label">Words</div></div>',
                unsafe_allow_html=True,
            )
        with m4:
            source_count = state.raw_research.count("---") + 1
            st.markdown(
                f'<div class="metric-box"><div class="metric-val">{source_count}</div>'
                f'<div class="metric-label">Sources</div></div>',
                unsafe_allow_html=True,
            )

        # Final report
        st.markdown("---")
        st.markdown(
            '<h2 style="font-family:\'Instrument Serif\',Georgia,serif;'
            'color:#f1f5f9;">📄 Final Research Report</h2>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="report-container">{_md_to_html(state.final_report)}</div>',
            unsafe_allow_html=True,
        )

        # Download button
        st.download_button(
            label="📥  Download Report (.md)",
            data=state.final_report,
            file_name="research_report.md",
            mime="text/markdown",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# If we have a previous result, show it (for reruns)
# ---------------------------------------------------------------------------

elif st.session_state.agent_state and st.session_state.agent_state.final_report:
    state = st.session_state.agent_state
    render_pipeline_tracker(len(STAGE_SEQUENCE))

    # Show stage logs
    for result in st.session_state.stage_logs:
        with st.expander(f"{result.icon}  {result.title}  —  {result.elapsed:.1f}s"):
            st.markdown(result.content)

    st.markdown("---")
    st.markdown(
        '<h2 style="font-family:\'Instrument Serif\',Georgia,serif;'
        'color:#f1f5f9;">📄 Final Research Report</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="report-container">{_md_to_html(state.final_report)}</div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        label="📥  Download Report (.md)",
        data=state.final_report,
        file_name="research_report.md",
        mime="text/markdown",
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

else:
    st.markdown("")

    # Feature cards
    cols = st.columns(3)
    features = [
        ("🧭", "Plan & Decompose", "Breaks your topic into focused research questions with targeted search queries."),
        ("🔍", "Search & Gather", "Uses Tavily to search the web in parallel, gathering real sources and data."),
        ("🧪", "Synthesize & Rank", "Analyzes findings, identifies conflicts, and ranks sources by reliability."),
        ("✍️", "Draft & Structure", "Writes a comprehensive first draft with executive summary and key findings."),
        ("🪞", "Reflect & Critique", "An editor agent reviews the draft for coherence, gaps, and weak arguments."),
        ("🔧", "Revise & Polish", "Addresses all editorial feedback to produce the polished final report."),
    ]
    for i, col in enumerate(cols):
        f = features[i]
        col.markdown(
            f'<div class="stage-card">'
            f'<div style="font-size:1.5rem;margin-bottom:8px;">{f[0]}</div>'
            f'<div style="font-size:0.85rem;font-weight:600;color:#e2e8f0;margin-bottom:4px;">{f[1]}</div>'
            f'<div style="font-size:0.78rem;color:#64748b;line-height:1.5;">{f[2]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    for i in range(3, 6):
        f = features[i]
        cols[i - 3].markdown(
            f'<div class="stage-card">'
            f'<div style="font-size:1.5rem;margin-bottom:8px;">{f[0]}</div>'
            f'<div style="font-size:0.85rem;font-weight:600;color:#e2e8f0;margin-bottom:4px;">{f[1]}</div>'
            f'<div style="font-size:0.78rem;color:#64748b;line-height:1.5;">{f[2]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<p style="text-align:center;color:#475569;font-style:italic;'
        'font-size:0.85rem;margin-top:1.5rem;">'
        'Each stage is a separate LLM call — demonstrating the agentic '
        'workflow design patterns from the course.</p>',
        unsafe_allow_html=True,
    )


