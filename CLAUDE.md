# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the bus_ai_audit_v2 project - a production-grade Streamlit application called "IDPETECH · BA Assistant (AI Readiness Audit Engine)". It's a multi-stage AI reasoning pipeline that analyzes companies for AI readiness and generates structured advisory outputs.

## Project Structure

```
bus_ai_audit_v2/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── CLAUDE.md          # Development guidance
```

## Technology Stack

- **Frontend**: Streamlit for web interface
- **AI**: OpenAI GPT-4o for multi-stage reasoning pipeline
- **PDF Generation**: fpdf2 for report exports
- **Text Processing**: markdown, beautifulsoup4 for content handling

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

### BAAssistant Pipeline
The core `BAAssistant` class implements a 5-stage reasoning pipeline:

1. **extract_signals()** - Extract structured JSON from inputs (no interpretation)
2. **diagnose()** - Strategic analysis of what company thinks vs. reality
3. **generate_hook()** - Founder-facing outbound message with tension point
4. **generate_audit()** - Structured markdown audit report with scores
5. **generate_close()** - Consultative reflection with soft CTA

### Key Design Patterns
- **Staged Reasoning**: Each pipeline stage is a separate OpenAI call
- **Caching**: Results cached by input hash for performance
- **Retry Handling**: Built-in retry logic for API failures
- **Modular Design**: Clean separation between pipeline stages

### Environment Variables
Required in Streamlit secrets or environment:
```
OPENAI_API_KEY=your_openai_api_key
```

## Key Principles

- No buzzwords in outputs (leverage, unlock, synergy, transformation)
- Opinionated analysis focusing on failure modes and blind spots
- Mechanisms over descriptions in recommendations
- Virtual environments for Python development
- Defensive security practices for audit systems