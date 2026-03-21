# HPCM — Hybrid Plagiarism Content Matching System

A full-stack plagiarism detection platform that uses a multi-layered ML pipeline combining lexical, semantic, and stylometric analysis to detect plagiarism across uploaded PDF documents.

---

## Architecture

```
┌─────────────┐       ┌─────────────────┐       ┌──────────────────────┐
│   React      │       │  Node/Express    │       │  FastAPI (Python)     │
│   Frontend   │──────▶│  Backend         │──────▶│  ML Engine            │
│   Port 3000  │       │  Port 5011       │       │  Port 8000            │
└─────────────┘       └────────┬─────────┘       └──────────────────────┘
                               │
                        ┌──────▼──────┐
                        │  MongoDB     │
                        │  Atlas       │
                        └─────────────┘
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Vite | Dashboard, PDF upload, report visualization |
| Backend API | Node.js + Express | PDF processing, MongoDB CRUD, orchestration |
| ML Engine | FastAPI + Python | HPCM pipeline — all ML computation |
| Database | MongoDB + GridFS | Document storage, report persistence |

---

## HPCM Pipeline — ML Modules

The core detection engine is a 9-module pipeline:

```
Raw PDF Text
     │
     ▼
┌─── M1: Preprocessing ────────────────────────────┐
│    Tokenize, lemmatize, stopword removal (NLTK)   │
└────┬──────────────┬──────────────┬────────────────┘
     │              │              │
     ▼              ▼              ▼
   M2: Lexical   M3: Semantic   M4: Stylometric
   TF-IDF +      Sentence-BERT  POS distribution +
   Cosine Sim    Embeddings      TTR + Avg Sent Len
     │              │              │
     ▼              ▼              ▼
   S_lex          S_sem          S_sty
     │              │              │
     └──────────────┼──────────────┘
                    ▼
            M5: Fusion
            C_final = 0.25·S_lex + 0.50·S_sem + 0.25·S_sty
                    │
                    ▼
            M6: Dynamic Similarity Calibration (DSC)
            T_cal = 0.65 + F_len + F_vocab + F_topic
                    │
                    ▼
            M7: Risk Classification
            HIGH (≥0.80) / MEDIUM (≥T_cal) / LOW (<T_cal)
                    │
                    ▼
            M9: Snippet Extraction
            Matching sentence pairs with similarity scores
                    │
                    ▼
            M8: Pipeline Orchestrator
            Chains all modules, returns full report
```

### Module Details

| Module | File | Input | Output | Method |
|--------|------|-------|--------|--------|
| M1 | `preprocessing.py` | Raw text | Tokens, sentences, clean text | NLTK tokenizer, WordNet lemmatizer, spaCy POS |
| M2 | `lexical.py` | Clean text (both docs) | S_lex [0–1] | TF-IDF vectorization + cosine similarity |
| M3 | `semantic.py` | Sentences (both docs) | S_sem [0–1] | Sentence-BERT (all-MiniLM-L6-v2) embeddings |
| M4 | `stylometric.py` | Tokens, sentences, POS tags | S_sty [0–1] | POS distribution similarity, TTR, avg sentence length |
| M5 | `fusion.py` | S_lex, S_sem, S_sty | C_final [0–1] | Weighted sum (0.25, 0.50, 0.25) |
| M6 | `dsc.py` | Token counts, TTR, S_sem | T_cal [0.50–0.80] | Adaptive threshold with calibration factors |
| M7 | `risk.py` | C_final, T_cal | HIGH/MEDIUM/LOW | Rule-based classification |
| M9 | `snippets.py` | Sentences (both docs) | Matching pairs | SBERT cross-similarity matrix, threshold ≥ 0.75 |
| M8 | `pipeline.py` | Source + suspect texts | Full report dict | Orchestrates M1–M9 with embedding caching |

### Fusion Weights

```
C_final = 0.25 × S_lex + 0.50 × S_sem + 0.25 × S_sty
```

Semantic similarity receives double weight because it catches paraphrasing — the hardest form of plagiarism to detect using word overlap alone.

### Dynamic Threshold Calibration

Instead of a fixed cutoff, the threshold adapts to document characteristics:

```
T_cal = 0.65 (base) + F_len + F_vocab + F_topic
```

Each factor ranges from -0.05 to +0.05:
- **F_len**: Similar document lengths → stricter threshold
- **F_vocab**: Similar vocabulary richness → stricter threshold
- **F_topic**: Same topic (high S_sem) → stricter threshold

### Performance Optimization

The pipeline caches source document data across comparisons:
- Source preprocessing runs once (not N times)
- Source SBERT embeddings computed once and reused
- Source POS tags computed once and reused
- Snippet extraction reuses cached embeddings

---

## API Endpoints

### FastAPI — ML Engine (Port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/compare` | Run HPCM pipeline on document pairs |

**POST /compare** request body:
```json
{
  "project_id": "abc123",
  "project_text": "full text of the uploaded document...",
  "compare_against": [
    { "id": "doc1", "title": "Paper A", "text": "..." },
    { "id": "doc2", "title": "Paper B", "text": "..." }
  ],
  "use_layer4": true
}
```

### Node/Express — Backend API (Port 5011)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/projects/upload` | Upload PDF, extract text, save to MongoDB + GridFS |
| GET | `/api/projects` | List all projects |
| POST | `/api/projects/:id/compare` | Trigger plagiarism check against all other documents |
| GET | `/api/projects/:id/report` | Retrieve plagiarism report |

---

## Project Structure

```
E:\LY REVIEW\Project\
│
├── Plagiarism_Engine/              # Python — FastAPI + ML Pipeline
│   ├── app.py                      # FastAPI server (port 8000)
│   └── modules/
│       ├── __init__.py
│       ├── preprocessing.py        # M1 — tokenize, lemmatize, stopwords
│       ├── lexical.py              # M2 — TF-IDF + cosine similarity
│       ├── semantic.py             # M3 — Sentence-BERT embeddings
│       ├── stylometric.py          # M4 — POS + TTR + avg sentence length
│       ├── fusion.py               # M5 — weighted score combination
│       ├── dsc.py                  # M6 — dynamic threshold calibration
│       ├── risk.py                 # M7 — risk classification
│       ├── snippets.py             # M9 — matching sentence extraction
│       └── pipeline.py             # M8 — orchestrator
│
├── server/                         # Node.js — Express Backend
│   ├── .env                        # Environment variables
│   ├── package.json
│   ├── server.js                   # Express server (port 5011)
│   ├── config/
│   │   └── db.js                   # MongoDB connection
│   ├── models/
│   │   ├── Project.js              # Project schema (text + GridFS ref)
│   │   └── Report.js               # Report schema (scores + snippets)
│   └── routes/
│       └── projects.js             # Upload, list, compare, report routes
│
├── client/                         # React — Frontend Dashboard
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx                # Entry point
│       ├── App.jsx                 # Router + navbar
│       ├── App.css                 # All styles
│       ├── api.js                  # Axios instance
│       └── pages/
│           ├── Dashboard.jsx       # Project list + compare trigger
│           ├── Upload.jsx          # PDF drag-and-drop upload
│           └── Report.jsx          # Scores, risk, snippets display
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+ (conda recommended)
- Node.js 18+
- MongoDB Atlas account (or local MongoDB)
- Git

### 1. Python ML Engine

```bash
cd Plagiarism_Engine

# Create conda environment
conda create -n tf311 python=3.11 -y
conda activate tf311

# Install dependencies
pip install nltk scikit-learn sentence-transformers spacy fastapi uvicorn pydantic python-multipart
python -m spacy download en_core_web_sm

# Start FastAPI server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Node.js Backend

```bash
cd server

# Install dependencies
npm install

# Configure environment (.env file)
# MONGO_URI=mongodb+srv://...
# FASTAPI_URL=http://localhost:8000
# PORT=5011

# Start server
npx nodemon server.js
```

### 3. React Frontend

```bash
cd client

# Install dependencies
npm install

# Start dev server
npm run dev
```

### Verify All Services

| Service | URL | Expected |
|---------|-----|----------|
| FastAPI | http://localhost:8000/health | `{"status":"ok"}` |
| Node.js | http://localhost:5011/health | `{"status":"ok"}` |
| React | http://localhost:5173 | Dashboard UI |

---

## Usage Flow

1. **Upload** — Go to Upload page, drop a PDF. Text is extracted and saved to MongoDB.
2. **Build Dataset** — Upload multiple PDFs. Each becomes part of the reference dataset.
3. **Check Plagiarism** — Click "Check Plagiarism" on any project from the Dashboard.
4. **View Report** — See overall risk level, individual scores (lexical, semantic, stylometric), calibrated threshold, and side-by-side matching snippets.

---

## Report Output

Each comparison produces:

- **S_lex** — Lexical similarity (word overlap via TF-IDF)
- **S_sem** — Semantic similarity (meaning via Sentence-BERT)
- **S_sty** — Stylometric similarity (writing style fingerprint)
- **C_final** — Composite score (weighted fusion)
- **T_cal** — Calibrated threshold (adaptive to document pair)
- **Risk Level** — HIGH (≥0.80) / MEDIUM (≥T_cal) / LOW (<T_cal)
- **Snippets** — Side-by-side matching sentence pairs with similarity percentages
- **Pipeline Time** — Processing time per comparison and total

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| ML Framework | scikit-learn, Sentence-Transformers, spaCy, NLTK |
| SBERT Model | all-MiniLM-L6-v2 |
| API Framework | FastAPI (Python), Express (Node.js) |
| Frontend | React 18, Vite, React Router, Axios |
| Database | MongoDB Atlas, GridFS |
| PDF Parsing | pdf-parse (Node.js) |

---

## Key Design Decisions

1. **Separate ML engine from backend** — FastAPI handles only computation, Node handles business logic and database. This allows independent scaling and testing.

2. **Three-layer similarity** — Lexical catches copy-paste, semantic catches paraphrasing, stylometric catches writing style similarity. No single method catches all plagiarism types.

3. **Dynamic threshold** — Fixed thresholds produce false positives on same-topic documents and false negatives on different-length documents. DSC adapts automatically.

4. **Embedding caching** — Source document is encoded once and reused across all comparisons, reducing pipeline time significantly as the dataset grows.

5. **Snippet extraction** — Raw similarity scores aren't actionable. Side-by-side matching passages let users verify and understand the detection results.

---

## License

This project is developed for academic/educational purposes.
