# AGENTS.md

See `CLAUDE.md` for full project overview, architecture, and development commands.

## Cursor Cloud specific instructions

### Services

| Service | Command | Port | Notes |
|---|---|---|---|
| Streamlit dev server | `source .venv/bin/activate && streamlit run app.py --server.port 8501 --server.headless true` | 8501 | Single service; no DB or other backing services needed |

### Environment

- Python 3.12 with virtualenv at `.venv/`.
- `python3.12-venv` system package is required (pre-installed via update script).
- Dependencies: `pip install -r requirements.txt` (already run by update script).
- Dev tools `flake8` and `black` are installed in the venv for linting/formatting.

### Secrets

- `OPENAI_API_KEY` is required for the AI pipeline to function. Without it, the UI loads but audits cannot be generated. Provide it either via the Streamlit sidebar input or in `.streamlit/secrets.toml`.

### Gotchas

- The app initializes an `openai.OpenAI(api_key="temp")` client on first load to read default prompts, which logs a warning but does not crash. This is expected.
- Streamlit must be started with `--server.headless true` in headless/CI environments to avoid the browser-open prompt.
- Lint checks (`flake8 app.py --max-line-length 120`) report pre-existing style issues in `app.py`; these are in the original codebase and not regressions.
