# Repository Guidelines

## Project Structure & Module Organization
The FastAPI backend resides in `api/app/`, with configuration and database helpers in `core/`, SQLAlchemy models under `models/`, route definitions in `routes/`, and service logic in `services/`. `init_db.py` seeds the SQLite database stored in `data/`. The React client lives in `web/src/`, where shared UI lives in `components/`, routed screens in `pages/`, shared types in `types/`, and utilities in `utils/`. Root scripts (`START.sh`, `STOP.sh`, `docker-compose.yml`) orchestrate end-to-end setups, while `test_api.py` provides a quick external API check.

## Build, Test, and Development Commands
- `docker-compose up --build` – build both images, initialize the database, and start the stack.
- `docker-compose down --volumes` – tear down containers and reset local state.
- `cd api && source venv/bin/activate && pip install -r requirements.txt` – refresh backend dependencies inside the provided virtualenv.
- `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` – run the API with hot reload.
- `cd web && npm install` followed by `npm run dev` – install frontend deps and launch Vite locally; `npm run build` performs the type-checking production build.

## Coding Style & Naming Conventions
Backend code follows PEP 8 with 4-space indentation, `snake_case` modules/functions, and type hints for request/response schemas. Place new routers in `api/app/routes` and register them in `main.py` in logical groups. Frontend files use 2-space indentation, `PascalCase` React components under `components/` and `pages/`, and `camelCase` hooks and utilities. Keep Tailwind utility classes readable by grouping related concerns per line, and colocate API clients in `web/src/utils`. Avoid committing generated `.venv`, `node_modules`, or `.env` files.

## Testing Guidelines
Backend tests should live in `api/tests/` and use `pytest`; activate the virtualenv and run `pytest api/tests -q`. Mirror route structures with `test_<module>.py` naming, and exercise both success and error paths for WebSocket handlers using FastAPI’s test client. For quick manual checks of the external candidate feed, run `python test_api.py`. Frontend changes should at minimum pass `npm run build`; add component tests with Vitest and React Testing Library when introducing new interactive behaviour.

## Commit & Pull Request Guidelines
Existing history uses short, imperative summaries (for example, “finish app”). Follow that style, and keep messages scoped to a single concern. Each pull request should describe the user impact, list key technical changes, and note any configuration updates (`.env`, data migrations). Link related GitHub issues when available, attach before/after screenshots for UI work, and confirm that required commands (`pytest`, `npm run build`, Docker builds) have been executed. Flag security-sensitive changes (auth, tokens, CORS) explicitly in the PR body.
