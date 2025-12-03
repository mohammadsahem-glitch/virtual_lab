# Virtual Lab

A Python/Streamlit application for structured AI-assisted research collaboration.

## Overview

Virtual Lab helps you conduct structured research through an AI-guided workflow:

1. **Discovery** - Chat with AI to understand and refine your research task
2. **Task** - Generate an executive summary of your task
3. **People** - AI identifies 5 interdisciplinary team members
4. **Research** - Find 10 relevant precedents and examples from around the world
5. **Meetings** - Simulate expert discussions on each research topic
6. **Report** - Generate a comprehensive final report
7. **Export** - Download your report in various formats

## Installation

### Prerequisites
- Python 3.8 or higher
- An Anthropic API key

### Setup

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
   streamlit run app.py
   ```

5. Open your browser to `http://localhost:8501`

6. Enter your Anthropic API key in the Settings page

## Usage

### Getting Started

1. **Configure API Key**: Go to Settings and enter your Anthropic API key
2. **Start Discovery**: Begin chatting with the AI to describe your research task
3. **Generate Summary**: Click "Generate Summary" to create an executive brief
4. **Build Your Team**: The AI will identify 5 expert personas for your task
5. **Conduct Research**: AI finds 10 relevant precedents and examples
6. **Run Meetings**: Simulate discussions between your expert team
7. **Generate Report**: Create a comprehensive final report
8. **Export**: Download your report and data

### Session Management

- Create multiple sessions for different research projects
- Sessions are automatically saved to `~/.virtual_lab/`
- Switch between sessions using the dropdown in the sidebar

### Customizing Prompts

Visit the Prompts page to customize the AI prompts used throughout the workflow.

## Data Storage

All data is stored locally in `~/.virtual_lab/`:
- `config.json` - API key and settings
- `prompts.json` - Customized prompts
- `sessions/` - Session data files

## Features

- **Multi-session support**: Work on multiple research projects
- **Persistent storage**: All progress is automatically saved
- **Customizable prompts**: Modify AI behavior to suit your needs
- **Expert simulation**: AI-powered personas discuss your research topics
- **Report generation**: Professional executive briefs
- **Export options**: Markdown and JSON export formats
- **Interactive chat**: Ask questions about your final report

## Requirements

- Python 3.8+
- streamlit >= 1.28.0
- anthropic >= 0.18.0

## License

This project is provided as-is for personal and educational use.
