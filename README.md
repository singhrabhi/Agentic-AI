# 🤖 Agentic Research Agent

A fully interactive **research agent** built with Streamlit, Claude (Anthropic), and Tavily — demonstrating the 6-stage agentic AI workflow from the course.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.35+-red)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ What It Does

Enter any research topic and watch the agent autonomously:

| Stage | Pattern | What Happens |
|-------|---------|--------------|
| 🧭 **Planning** | Task Decomposition | Breaks topic into 4-6 research questions with search queries |
| 🔍 **Searching** | Tool Use | Searches the web via Tavily API (up to 8 parallel queries) |
| 🧪 **Synthesizing** | Analysis | Ranks findings, identifies conflicts, notes gaps |
| ✍️ **Drafting** | Generation | Writes a structured first draft with sections |
| 🪞 **Reflecting** | Reflection Pattern | Editor agent reviews for coherence & gaps |
| 🔧 **Revising** | Multi-Agent | Improves the draft based on editorial feedback |

The result is a **comprehensive markdown report** — far more thorough than a single-prompt output.

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd research_agent

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements_research_agent.txt
```

### 2. Set API Keys

```bash
cp .env.example .env
# Edit .env and add your keys:
#   SARVNAM_API_KEY=sk-ant-...
#   TAVILY_API_KEY=tvly-...
```

Or enter them directly in the sidebar UI.

### 3. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🐳 Docker Deployment

```bash
# Build and run
docker compose up --build

# Or manually
docker build -t research-agent .
docker run -p 8501:8501 --env-file .env research-agent
```

---

## ☁️ Cloud Deployment

### Streamlit Community Cloud (Free)

1. Push the code to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as the main file
4. Add your API keys in **Settings → Secrets**:
   ```toml
   SARVNAM_API_KEY = "sk-ant-..."
   TAVILY_API_KEY = "tvly-..."
   ```
5. Deploy!

### AWS / GCP / Azure

Use the included `Dockerfile`:

```bash
# AWS (ECR + ECS/Fargate)
aws ecr create-repository --repository-name research-agent
docker tag research-agent:latest <account>.dkr.ecr.<region>.amazonaws.com/research-agent
docker push <account>.dkr.ecr.<region>.amazonaws.com/research-agent

# GCP (Cloud Run)
gcloud run deploy research-agent \
  --source . \
  --port 8501 \
  --set-env-vars SARVNAM_API_KEY=...,TAVILY_API_KEY=...

# Azure (Container Apps)
az containerapp up \
  --name research-agent \
  --source . \
  --ingress external \
  --target-port 8501
```

### Railway / Render / Fly.io

All support Dockerfiles natively. Just connect your repo and set the environment variables.

---

## 📁 Project Structure

```
research_agent/
├── app.py                  # Streamlit UI — all frontend code
├── agent.py                # Core pipeline — 6 agentic stages
├── requirements.txt        # Python dependencies
├── .env.example            # Template for API keys
├── .streamlit/
│   └── config.toml         # Streamlit theme & server config
├── Dockerfile              # Container build
├── docker-compose.yml      # Docker Compose config
└── README.md               # This file
```

---

## 🏗️ Architecture

```
┌─────────────┐
│   User      │  enters topic
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│                  Streamlit UI (app.py)                │
│  ┌────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │Sidebar │  │ Pipeline │  │  Stage   │  │ Report │ │
│  │Config  │  │ Tracker  │  │  Logs    │  │ View   │ │
│  └────────┘  └──────────┘  └──────────┘  └────────┘ │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│              Agent Pipeline (agent.py)               │
│                                                      │
│  Planning ──► Searching ──► Synthesizing             │
│                                │                     │
│                                ▼                     │
│             Revising ◄── Reflecting ◄── Drafting     │
│                │                                     │
│                ▼                                     │
│          Final Report                                │
└────────┬────────────────────────┬────────────────────┘
         │                        │
         ▼                        ▼
  ┌──────────────┐        ┌──────────────┐
  │  Sarvnam API  │        │  Tavily API  │
  │  (Sarvnam ) │        │ (Web Search) │
  └──────────────┘        └──────────────┘
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SARVNAM_API_KEY` | Yes | Your Sarvnam API key |
| `TAVILY_API_KEY` | Yes | Your Tavily search API key |

### Customization

- **Model**: Change `model` parameter in `run_pipeline()` (default: `claude-sonnet-4-20250514`)
- **Search depth**: Adjust `max_results` in `_search_web()` (default: 5 per query)
- **Max queries**: Adjust the slice in `stage_searching()` (default: 8 queries)
- **Report length**: Modify the system prompt in `stage_revising()` (default: 1500-3000 words)

---

## 🔑 Getting API Keys

### Anthropic (Claude)
1. Go to [Sarvnam Website ](https://dashboard.sarvam.ai/)
2. Sign up / log in
3. Navigate to **API Keys** → **Create Key**

### Tavily (Web Search)
1. Go to [tavily.com](https://tavily.com)
2. Sign up for a free account
3. Copy your API key from the dashboard

---

## 📝 License

MIT — use freely for learning, projects, and production.
