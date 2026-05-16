# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the bus_ai_audit_v2 project - a production-grade Streamlit application called "IDPETECH · BA Assistant (AI Readiness Audit Engine)". It's a multi-stage AI reasoning pipeline that analyzes companies for AI readiness and generates structured advisory outputs.

## Project Structure

```
bus_ai_audit_v2/
├── core/                     # Modular core components
│   ├── __init__.py          # Package initialization
│   ├── models.py            # Data structures (CompanyInputs, PipelineResults, etc.)
│   ├── utils.py             # Utility functions (_is_url, sieve_context)
│   ├── database.py          # SQLite operations (DatabaseManager)
│   ├── scraping.py          # Web scraping (FirecrawlManager, scrape functions)
│   ├── pipeline.py          # AI reasoning pipeline (BAAssistant)
│   ├── export.py            # Document generation (PDF, Word)
│   └── agent.py             # Agent research mode (ResearchAgent, ICPScorer)
├── app.py                   # Main Streamlit application (UI only)
├── requirements.txt         # Python dependencies
├── CLAUDE.md               # Development guidance
└── company_reality_check.db # SQLite database (auto-created)
```

## Technology Stack

- **Frontend**: Streamlit for web interface with dual mode (Manual/Agent)
- **AI**: OpenAI GPT-4o for multi-stage reasoning pipeline + GPT-4o-mini for agent tasks
- **Web Scraping**: Firecrawl API for website content extraction and search
- **Database**: SQLite for company analysis persistence and caching
- **PDF Generation**: fpdf2 for report exports
- **Word Generation**: python-docx for document exports
- **Text Processing**: markdown, beautifulsoup4 for content handling
- **Token Management**: tiktoken for context sieving and TPM management

## Development Setup

### Environment Requirements

**Python Projects:**
```bash
# Always use virtual environments
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Node.js Projects:**
```bash
npm install
# or
yarn install
```

## Common Development Commands

### Running the Application
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py

# Run with specific port
streamlit run app.py --server.port 8501
```

### Development
```bash
# Code formatting
black app.py

# Type checking (if mypy configured)
mypy app.py

# Basic linting
flake8 app.py
```

## Development Workflow

1. **Environment Setup**: Always activate virtual environment for Python projects
2. **Testing**: Run tests locally before deployment
3. **Staging/Production**: Test in staging environment before production deployment
4. **No Hard-coding**: Avoid hard-coded values; use environment variables and configuration files

## Application Architecture

### Dual Mode Operation
The application provides two distinct modes:

**Manual Mode (Original Functionality):**
- Direct URL input for manual company analysis
- Company database browser with clickable load buttons
- Context editing capabilities for reprocessing
- Prompt management interface

**Agent Mode (New Agentic Research):**
- Automated company research based on company name only
- Six-step research process with Firecrawl API integration
- Two-pass ICP (Ideal Customer Profile) scoring system
- Alternative company suggestions for disqualified prospects

### Core Pipeline (BAAssistant)
The `BAAssistant` class in `core/pipeline.py` implements a 5-stage reasoning pipeline:

1. **extract_signals()** - Extract structured JSON from inputs (no interpretation)
2. **diagnose()** - Strategic analysis of what company thinks vs. reality
3. **generate_hook()** - Founder-facing outbound message with tension point
4. **generate_audit()** - Structured markdown audit report with scores
5. **generate_close()** - Consultative reflection with soft CTA

### Agent Research System
The agent mode (`core/agent.py`) implements automated company research:

**ResearchAgent** - Six-step research process:
1. Website discovery via search
2. Funding intelligence gathering
3. Recent news signal hunting
4. Leadership signal detection
5. Job posting analysis
6. Deep website content scraping

**ICPScorer** - Two-pass scoring system:
1. Hard disqualifiers (immediate rejection criteria)
2. Positive scoring (HOT/WARM/COLD assessment)

**State Machine** - Streamlit session state management:
- IDLE → RESEARCHING → ICP_DECISION → RUNNING_PIPELINE → COMPLETE
- Alternative path: ICP_DECISION → DISQUALIFIED

### Database Architecture
SQLite database (`DatabaseManager` in `core/database.py`) with three tables:
- **companies**: Complete analysis storage with extended data
- **interaction_states**: Agent state persistence (planned)
- **cache**: Hash-based result caching

### Key Design Patterns
- **Modular Architecture**: Clean separation of concerns across core modules
- **Staged Reasoning**: Each pipeline stage is a separate OpenAI call
- **State Machine**: Streamlit session state for agent mode transitions
- **Triangulation**: Cross-reference company claims vs. external signals
- **Credit Efficiency**: Firecrawl API usage optimization
- **Token Management**: tiktoken-based context sieving for TPM limits

### Environment Variables
Required in Streamlit secrets or environment:
```
OPENAI_API_KEY=your_openai_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

## Key Principles

- No buzzwords in outputs (leverage, unlock, synergy, transformation)
- Opinionated analysis focusing on failure modes and blind spots
- Mechanisms over descriptions in recommendations
- Virtual environments for Python development
- Defensive security practices for audit systems
# IDPETECH BA Assistant — Claude Code Rules

## Before ANY change
- Read app.py fully before touching anything
- Confirm understanding of existing class structure
- List which classes/methods you will modify before modifying them
- Never rename existing methods or classes
- Never change existing method signatures without flagging it first

## Architecture rules
- Core logic organized in modular core/ package (models, pipeline, database, etc.)
- app.py contains UI logic only (Streamlit interface)
- No new pip dependencies without asking first
- Database schema changes must be backward compatible
- Existing Manual Mode must always remain functional
- Agent mode enhances but doesn't replace manual functionality

## Code style
- All network calls wrapped in try/except with 8 second timeout
- Every new method needs a docstring
- Log all agent decisions to hunt_log or research_log
- Never block the pipeline on a single failure

## Testing
- After any change, confirm existing pipeline still runs
- Smoke test new features before declaring done
- State which smoke test you ran and what it returned

## What not to touch
- Scraping logic unless explicitly asked
- PDF/Word generation
- Streamlit UI layout unless explicitly asked
- SQLite schema for existing tables
## Project context
This is a solo-built sales tool for fractional CTO prospecting.
Stability over cleverness. If unsure, ask before refactoring.
	
## Checkpoint policy
- Create a git commit or checkpoint before 
  every major feature addition
- Checkpoint naming: 
  baseline-clean, pre-agent, pre-prospecting etc
- Never build two major features without 
  a checkpoint between them

## Build sequence for this project
Phase 1 ✅ — Core pipeline (original manual mode)
Phase 2 ✅ — Playwright removal + Firecrawl scraping integration
Phase 3 ✅ — Modular architecture extraction (core/ package)
Phase 4 ✅ — Agent mode (automated single company research)
Phase 5 — Prospecting agent (bulk research and funnel management)

## Current Status: Phase 4 Complete
- ✅ Manual mode fully functional with enhanced UI
- ✅ Agent mode implemented with state machine
- ✅ Dual mode operation with seamless switching
- ✅ Modular codebase ready for future enhancements

## Never combine phases in one prompt
One phase per Claude Code session.
Validate before proceeding.
