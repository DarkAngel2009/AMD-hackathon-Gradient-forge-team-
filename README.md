# 🏗️ Architectural Multiverse Engine

> **AMD Slingshot Hackathon 2026** — Team Gradient Forge

An AI-powered platform that generates, evaluates, and compares multiple system architectures based on your project requirements. Powered by **Groq LLM (Llama 3.3 70B)** for intelligent, unbiased architectural analysis.

---

## 🎯 What It Does

Describe your system and constraints → get **4 production-grade architecture proposals** (Monolith, Microservices, Event-Driven, Serverless) with:

- **LLM-Driven Architecture Generation** — tailored components, database strategies, communication models, and failure analysis
- **Unbiased Multi-Factor Scoring** — 8 evaluation dimensions including WebSocket concurrency, cost modeling, compliance enforcement
- **Transparent Rankings** — scoring breakdown explains *why* each architecture scored the way it did
- **AI Strategic Analysis** — executive summary, risk analysis, and strategic advice
- **Mermaid.js Diagrams** — auto-generated architecture diagrams
- **SRS Document Generation** — complete Software Requirements Specification
- **Starter Scaffold** — production-ready project structure with Dockerfiles, configs, and boilerplate

---

## 🖥️ Screenshots

The UI features a premium dark theme inspired by [lightweight.info](https://lightweight.info/en) — editorial, minimal, powerful.

---

## 🧪 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Vanilla HTML/CSS/JS, Chart.js, Mermaid.js, Marked.js |
| **Backend** | Python, FastAPI, Pydantic, Uvicorn |
| **LLM** | Groq API — Llama 3.3 70B Versatile |
| **Design** | Dark premium theme, Inter font, glassmorphism |

---

## 📁 Project Structure

```
├── backend/
│   ├── main.py                          # FastAPI entry point
│   ├── .env                             # GROQ_API_KEY goes here
│   ├── requirements.txt                 # Python dependencies
│   ├── models/
│   │   ├── input_models.py              # Pydantic input schemas
│   │   └── architecture_models.py       # Output schemas
│   ├── routers/
│   │   └── api.py                       # REST API endpoints
│   └── services/
│       ├── architecture_generator.py    # LLM architecture generation
│       ├── simulation_engine.py         # Unbiased multi-factor scoring
│       ├── comparison_service.py        # Ranking & comparison logic
│       ├── llm_reasoning_service.py     # Strategic AI analysis
│       ├── scaffold_generator.py        # Project scaffold generation
│       ├── compliance_service.py        # Regulatory compliance checks
│       ├── srs_generator.py             # SRS document generation
│       ├── diagram_generator.py         # Mermaid diagram generation
│       └── model_registry.py            # LLM model routing & registry
├── frontend/
│   ├── index.html                       # Main UI
│   ├── style.css                        # Premium dark theme
│   └── app.js                           # Frontend logic & rendering
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- A Groq API key ([get one free at console.groq.com](https://console.groq.com))

### 1. Clone the repo
```bash
git clone https://github.com/DarkAngel2009/AMD-hackathon-Gradient-forge-team-.git
cd AMD-hackathon-Gradient-forge-team-
```

### 2. Set up the backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 3. Configure your API key
Edit `backend/.env`:
```
GROQ_API_KEY=your_actual_groq_api_key_here
```

### 4. Run the server
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Open the app
Navigate to **http://127.0.0.1:8000** in your browser.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate` | Generate 4 architecture strategies with scores |
| `POST` | `/api/compare` | Rank and compare architectures |
| `POST` | `/api/scaffold` | Generate starter project scaffold |
| `POST` | `/api/scaffold/download` | Download scaffold as ZIP |
| `POST` | `/api/compliance` | Run compliance analysis |
| `POST` | `/api/srs` | Generate SRS document |
| `POST` | `/api/diagram` | Generate Mermaid.js diagram |
| `GET`  | `/api/models` | Get current LLM model assignments |
| `POST` | `/api/models` | Override LLM models per module |

---

## 🧠 How Scoring Works

Each architecture is evaluated by the LLM across **8 dimensions**:

1. **Horizontal Scalability** — scaling ceiling for the user count
2. **WebSocket Concurrency** — max connections per node/service
3. **Sustained Throughput** — efficiency at 100k+ concurrency
4. **Cold-Start Latency Risk** — impact on real-time workloads
5. **Operational Complexity** — deployment, monitoring, CI/CD burden
6. **Cost Modeling** — estimated cost per 1M messages, per 10k connections
7. **Multi-Region Failover** — disaster recovery capability
8. **Compliance Enforcement** — auto-detects GDPR, CCPA, SOC2, HIPAA, PCI-DSS

### Key Design Principles
- ❌ **No hardcoded bias** — all architectures start equal
- ✅ **Monolith CAN win** if constraints favor it
- ✅ **Event-Driven wins** for sustained throughput workloads
- ✅ **Serverless is penalized** for sustained WebSocket workloads
- ✅ **Best Pick** determined purely by computed score

---

## 👥 Team Gradient Forge

Built for the **AMD Slingshot Hackathon 2026**.
