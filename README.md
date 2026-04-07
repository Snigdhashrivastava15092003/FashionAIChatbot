# Fashion AI

Fashion AI is a Python-first fashion recommendation chatbot built with FastAPI, a static HTML/CSS/JavaScript frontend, dataset-grounded retrieval, and Gemini support through environment variables.

## Highlights

- Python backend only
- Plain HTML, CSS, and JavaScript frontend served by FastAPI
- No frontend framework required
- Gemini integration through `GOOGLE_API_KEY` and `GOOGLE_MODEL`
- Retrieval pipeline built from the CSV dataset using TF-IDF embeddings and an optional FAISS backend
- LangChain prompt orchestration through `langchain-core`
- Optional LSTM module for occasion classification when TensorFlow is installed
- Clean fallback behavior when Gemini or retrieval is unavailable

## Project Structure

- `main.py`: FastAPI entrypoint and static frontend host
- `backend/config.py`: environment-backed settings
- `backend/models.py`: request and response schemas
- `backend/routes/api.py`: REST API routes
- `backend/services/dataset_service.py`: dataset loading, cleaning, normalization, and preference options
- `backend/services/vector_store_service.py`: vectorization, caching, and retrieval
- `backend/services/prompt_manager.py`: system prompt loading and LangChain prompt assembly
- `backend/services/llm_service.py`: Gemini request handling and JSON parsing
- `backend/services/recommendation_service.py`: dataset fallback recommendation shaping
- `backend/services/chat_service.py`: conversation orchestration
- `backend/services/lstm_service.py`: optional LSTM training and status helpers
- `backend/prompts/system_prompt.txt`: premium stylist system prompt
- `backend/utils/parsing.py`: preference extraction and clarification rules
- `frontend/index.html`: static interface
- `frontend/styles.css`: premium responsive styling
- `frontend/app.js`: API wiring and UI behavior
- `trained_models/`: cached retrieval artifacts and optional model outputs

## Environment Variables

Create a `.env` file from `.env.example` and provide your own secrets.

Required variables:

- `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- `GOOGLE_MODEL` or `GENAI_MODEL`
- `DATASET_PATH`
- `ALLOWED_ORIGINS`

Optional variables:

- `VECTOR_CACHE_PATH`
- `LSTM_MODEL_PATH`
- `LSTM_METADATA_PATH`

## Setup

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Create `.env` from `.env.example` and fill in your dataset path and Gemini key.

4. Start the backend and frontend together through FastAPI.

```powershell
python main.py
```

5. Open the app.

- `http://127.0.0.1:8000`

## API Routes

- `GET /api/health`
- `GET /api/preferences`
- `GET /api/model-status`
- `POST /api/chat`
- `POST /api/recommend`
- `POST /api/train-lstm`

## Retrieval and AI Flow

1. User message and structured controls are parsed into preferences.
2. If budget or occasion is missing, the chatbot asks a focused follow-up question.
3. The dataset is cleaned and normalized.
4. A vector retrieval query is built from the request and preferences.
5. Top dataset examples are retrieved through the vector store.
6. LangChain prompt composition combines the system prompt, user request, structured preferences, history, and retrieved examples.
7. Gemini produces the final JSON recommendation when available.
8. If Gemini fails, Fashion AI falls back to a dataset-grounded recommendation.

## LSTM Module

The LSTM module is optional. It is designed for occasion classification and is kept separate so the main recommendation flow stays stable even when TensorFlow is not installed.

- `GET /api/model-status` reports whether the LSTM module is available or trained.
- `POST /api/train-lstm` trains the optional classifier when TensorFlow is installed.

## Notes

- No API keys are hardcoded in the source code.
- Secrets are loaded only from environment variables.
- The frontend is plain static HTML/CSS/JavaScript; Node.js is not required to run the application.
- On platforms where `faiss-cpu` is unavailable, the app falls back to cosine-similarity retrieval while keeping the same API behavior.
