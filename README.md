# PromptCanary 🐦

**A system for testing and improving AI prompts with safe deployments**

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-green.svg)](https://fastapi.tiangolo.com)

## Overview

PromptCanary solves a common problem in AI development: how do you know if your prompts are actually good? Instead of guessing or testing manually, this system provides scientific evaluation and safe deployment of prompt improvements.

**Key Features:**
- 🧪 **AI-Powered Evaluation** - Test prompts with real AI models and ML metrics
- 🚀 **Canary Deployments** - Safely test improvements with traffic splitting
- 📊 **Performance Analytics** - Track improvements over time with real data
- 🔄 **A/B Testing** - Compare prompt versions objectively
- 🛡️ **Production Ready** - Error handling, logging, and monitoring

## Quick Start

### Prerequisites
- Python 3.13+
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/asnoori915/PromptCanary.git
cd PromptCanary

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run the Server

```bash
# Start the development server
python -m uvicorn app.main:app --reload

# Open Swagger UI
open http://127.0.0.1:8000/swagger
```

## How It Works

### 1. Test a Prompt
```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a short story about a robot learning to paint"}'
```

### 2. Get Optimization Suggestions
```bash
curl "http://127.0.0.1:8000/optimize?prompt_id=1"
```

### 3. Deploy with Canary Testing
```bash
curl -X POST "http://127.0.0.1:8000/prompts/1/release" \
  -H "Content-Type: application/json" \
  -d '{"suggestion_id": 1, "canary_percent": 20}'
```

### 4. Monitor Performance
```bash
curl "http://127.0.0.1:8000/prompts/1/status"
```

## Core Concepts

### Canary Deployments
The system uses canary releases to safely test prompt improvements. Instead of replacing your current prompt immediately, you can:
- Deploy a new version to a small percentage of traffic (e.g., 20%)
- Compare performance between old and new versions
- Promote the new version if it performs better, or rollback if it doesn't

### Evaluation Pipeline
Prompts are evaluated using multiple approaches:
- **Heuristic Scoring** - Basic rules about length, clarity, and structure
- **AI Evaluation** - GPT-4 provides detailed feedback and suggestions
- **ML Metrics** - BLEU, ROUGE, and semantic similarity scores
- **Human Feedback** - User ratings and comments for continuous improvement

### Smart Optimization
The system analyzes your prompt's performance history to suggest specific improvements based on what has worked well in the past.

## API Endpoints

### Core Evaluation
- `POST /analyze` - Test and evaluate prompts
- `GET /optimize` - Generate improved prompt versions
- `POST /feedback` - Submit human feedback and ratings

### Canary Management
- `POST /prompts/{id}/release` - Create canary deployment
- `GET /prompts/{id}/status` - Check canary performance
- `POST /prompts/{id}/promote` - Promote canary to active
- `POST /prompts/{id}/rollback` - Rollback canary deployment

### ML Evaluation
- `GET /eval/{id}/analysis` - Analyze prompt patterns and performance
- `GET /eval/{id}/performance` - Get historical performance data
- `POST /eval/{id}/test-metrics` - Test ML metrics on prompts

### System
- `GET /health` - Health check endpoint
- `GET /metrics` - System metrics and statistics
- `GET /report` - Comprehensive analytics report

## Example Workflow

Here's a complete example of testing and improving a prompt:

```bash
# 1. Test your original prompt
curl -X POST "http://127.0.0.1:8000/analyze" \
  -d '{"prompt": "Write a professional email"}'

# 2. Get optimization suggestions
curl "http://127.0.0.1:8000/optimize?prompt_id=1"

# 3. Deploy the improvement with 20% traffic
curl -X POST "http://127.0.0.1:8000/prompts/1/release" \
  -d '{"suggestion_id": 1, "canary_percent": 20}'

# 4. Test multiple times to see traffic splitting
for i in {1..10}; do
  curl -X POST "http://127.0.0.1:8000/analyze" \
    -d '{"prompt_id": 1, "response": "Sample response"}'
done

# 5. Check the results
curl "http://127.0.0.1:8000/prompts/1/status"
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Swagger UI    │───▶│   FastAPI App    │───▶│   PostgreSQL    │
│   (Frontend)    │    │   (API Layer)    │    │   (Database)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   OpenAI API     │
                       │   (AI Models)    │
                       └──────────────────┘
```

### Tech Stack
- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **AI/ML:** OpenAI API, sentence-transformers, rouge-score, nltk
- **Database:** PostgreSQL (production) / SQLite (development)
- **Infrastructure:** Alembic migrations, Redis caching, Docker support

## Production Deployment

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost/promptcanary
OPENAI_API_KEY=sk-proj-...
WEBHOOK_URL=https://your-webhook-url.com
CANARY_MIN_SAMPLES=30
CANARY_THRESHOLD=0.55
```

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Database Migrations
```bash
# Run Alembic migrations
alembic upgrade head
```

## Use Cases

### For AI Engineers
- Systematic prompt optimization and A/B testing
- Performance monitoring and analytics
- Safe deployment of prompt improvements
- Data-driven decision making

### For Product Teams
- Improve AI-powered features with confidence
- Reduce risk in AI system updates
- Measure and track AI performance improvements
- User experience optimization

### For Businesses
- Enhance customer service AI interactions
- Optimize content generation systems
- Reduce AI-related errors and inconsistencies
- Increase user satisfaction with AI features

## Development

### Project Structure
```
app/
├── main.py              # FastAPI application setup
├── models.py            # Database models
├── schemas.py           # Pydantic validation schemas
├── config.py            # Configuration management
├── db.py                # Database connection
├── utils.py             # Shared utilities
├── routes/              # API endpoint handlers
│   ├── analyze.py       # Core evaluation endpoints
│   ├── optimize.py      # Optimization endpoints
│   ├── feedback.py      # Human feedback endpoints
│   ├── releases.py      # Canary deployment endpoints
│   ├── evaluation.py    # ML evaluation endpoints
│   └── ...
└── services/            # Business logic
    ├── prompt_service.py    # Core prompt operations
    ├── canary.py           # Canary deployment logic
    ├── router.py           # Traffic splitting
    ├── ml_metrics.py       # ML evaluation metrics
    ├── analytics.py        # Performance analysis
    └── ...
```

### Key Design Patterns
- **Service Layer** - Business logic separated from API routes
- **Repository Pattern** - Database operations abstracted
- **Decorator Pattern** - Consistent error handling and logging
- **Dependency Injection** - Clean, testable code structure

## Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Areas for Contribution
- New evaluation metrics and algorithms
- Performance optimizations
- Additional AI model integrations
- Frontend dashboard development
- Documentation improvements
- Bug fixes and testing

## Contact

**Amir Paneer** - [GitHub](https://github.com/asnoori915)

Project Link: [https://github.com/asnoori915/PromptCanary](https://github.com/asnoori915/PromptCanary)

---

*Built to make AI prompt engineering more systematic and data-driven*
