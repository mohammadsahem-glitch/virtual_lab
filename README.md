# Virtual Lab

A Python/Flask application for structured AI-assisted research collaboration with a modern HTML/CSS/JS frontend.

## Overview

Virtual Lab helps you conduct structured research through an AI-guided workflow:

1. **Discovery** - Chat with AI to understand and refine your research task
2. **Task** - Generate an executive summary of your task
3. **People** - AI identifies 5 interdisciplinary team members
4. **Research** - Find 10 relevant precedents and examples from around the world
5. **Meetings** - Simulate interactive expert discussions on each research topic
6. **Report** - Generate a comprehensive final report
7. **Export** - Download your report in various formats

## Architecture

- **Backend**: Flask REST API (`backend.py`)
- **Frontend**: HTML/CSS/JS single-page application (`templates/`, `static/`)
- **AI**: OpenAI GPT-4o integration

## Installation

### Prerequisites
- Python 3.8 or higher
- An OpenAI API key

### Local Setup

1. Clone or download this repository

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python backend.py
   ```

5. Open your browser to `http://localhost:5000`



7. Enter your OpenAI API key in the Settings page

## Railway Deployment

### Deploy to Railway

1. Push your code to a GitHub repository

2. Go to [Railway](https://railway.app) and create a new project

3. Select "Deploy from GitHub repo" and choose your repository

4. Add environment variables in Railway dashboard:
   - `SECRET_KEY`: A secure random string for session management
   - `OPENAI_API_KEY`: Your OpenAI API key (optional, can be set in app)

5. Railway will automatically detect the `Procfile` and deploy

6. Your app will be available at the Railway-provided URL

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask session secret key | Yes (in production) |
| `OPENAI_API_KEY` | OpenAI API key | No (can be set in app) |
| `PORT` | Server port (set by Railway) | Auto |

## Usage

### Getting Started

1. **Login**: Use your credentials to sign in
2. **Configure API Key**: Go to Settings and enter your OpenAI API key
3. **Start Discovery**: Begin chatting with the AI to describe your research task
4. **Generate Summary**: Click "Generate Summary" to create an executive brief
5. **Build Your Team**: The AI will identify 5 expert personas for your task
6. **Conduct Research**: AI finds 10 relevant precedents and examples
7. **Run Meetings**: Interact with experts in step-by-step discussions
8. **Generate Report**: Create a comprehensive final report
9. **Export**: Download your report and data

### Interactive Meetings

The meetings feature allows you to:
- Get responses one at a time from team members
- Ask specific questions to the group
- Select a specific expert to respond
- Auto-run multiple responses
- End and summarize the discussion
- Reset a meeting to start over

### Session Management

- Create multiple sessions for different research projects
- Sessions are automatically saved to `~/.virtual_lab/`
- Switch between sessions using the dropdown in the sidebar

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | User authentication |
| `/api/auth/logout` | POST | End session |
| `/api/sessions` | GET/POST | List/create sessions |
| `/api/sessions/<id>` | GET/PUT/DELETE | Manage session |
| `/api/ai/chat` | POST | Chat with AI |
| `/api/ai/generate-summary` | POST | Generate task summary |
| `/api/ai/generate-people` | POST | Generate team members |
| `/api/ai/generate-research` | POST | Generate research findings |
| `/api/ai/meeting-response` | POST | Get meeting response |
| `/api/ai/meeting-summary` | POST | Summarize meeting |
| `/api/ai/generate-report` | POST | Generate final report |
| `/api/settings/api-key` | GET/POST | Manage API key |
| `/api/prompts` | GET/POST | Manage prompts |

## Data Storage

All data is stored locally in `~/.virtual_lab/`:
- `config.json` - API key and settings
- `prompts.json` - Customized prompts
- `sessions/` - Session data files

## Files Structure

```
virtual_lab/
├── backend.py          # Flask REST API
├── app.py              # Legacy Streamlit app
├── templates/
│   └── index.html      # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css   # Stylesheet
│   └── js/
│       └── app.js      # Frontend JavaScript
├── requirements.txt    # Python dependencies
├── Procfile            # Railway/Heroku deployment
├── railway.json        # Railway configuration
└── README.md           # This file
```

## Requirements

- Python 3.8+
- flask >= 3.0.0
- flask-cors >= 4.0.0
- openai >= 1.0.0
- gunicorn >= 21.0.0 (for production)

## License

This project is provided as-is for personal and educational use.
