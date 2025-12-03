"""
Virtual Lab - Backend API
Flask-based REST API for the Virtual Lab application
"""

import os
import json
import hashlib
import uuid
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from openai import OpenAI

# ============================================================
# FLASK APP CONFIGURATION
# ============================================================

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'virtual-lab-secret-key-change-in-production')
CORS(app)

# ============================================================
# AUTHENTICATION
# ============================================================

USERS = {
    "TestUserAD": {
        "password_hash": hashlib.sha256("ADPM1987@AD".encode()).hexdigest(),
        "name": "Test User",
        "role": "admin"
    }
}

def check_password(username: str, password: str) -> bool:
    if username in USERS:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return USERS[username]["password_hash"] == password_hash
    return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# FILE PATHS AND STORAGE
# ============================================================

def get_data_dir() -> Path:
    data_dir = Path.home() / ".virtual_lab"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_sessions_dir() -> Path:
    sessions_dir = get_data_dir() / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    return sessions_dir

def get_config_path() -> Path:
    return get_data_dir() / "config.json"

def get_prompts_path() -> Path:
    return get_data_dir() / "prompts.json"

# ============================================================
# CONFIGURATION MANAGEMENT
# ============================================================

def load_config() -> dict:
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {"api_key": os.environ.get('OPENAI_API_KEY', '')}

def save_config(config: dict):
    with open(get_config_path(), 'w') as f:
        json.dump(config, f, indent=2)

# ============================================================
# PROMPTS CONFIGURATION
# ============================================================

DEFAULT_PROMPTS = {
    "discovery-message": """I work in Abu Dhabi. You are going to ask me a series of small concise questions to get to understand a task that I will ask a think tank to tackle. This is the phase where you ask me questions to understand the task and not to find the solution. Ask me questions to see what I care about. Be smart about it, start with broad questions then narrow down to the details. Ask simple one line questions. Be friendly.""",
    "discovery-summarize": """Write a concise summary of the task the user wants to achieve. It should be two paragraphs long. Make it look like a McKinsey Executive task summary. Don't use hashtags for headings, just bold it.""",
    "people-system-prompt": """You are a helpful assistant that analyzes tasks and identifies appropriate people who could perform them. Return your results as a JSON array of objects with 'title' and 'description' fields.""",
    "people-user-prompt": """I'd like to assemble a team of five people from interdisciplinary backgrounds to tackle the following task. I'd like the five interdisciplinary members from different backgrounds to be able to bring to the table unique perspectives from leading former projects in this space to understanding human behavior to create strong incentives to attract people.

{EXECUTIVE_SUMMARY}

Describe five people you would choose for this role. Make it diverse in the skillset. Be creative.

Return your response as a JSON array with exactly 5 objects, each having "title" and "description" fields. Example format:
[{"title": "Title Here", "description": "Description here"}, ...]""",
    "research-user-prompt": """You are working as a consultant for Abu Dhabi government. Your role is to conduct research and identify relevant precedents and examples that can inform policy and implementation strategies.

You have been provided with an executive summary of a task that the user is working to accomplish:

{EXECUTIVE_SUMMARY}

Your assignment is to research and find ten previous examples of similar work done by other nations, companies, organizations, or institutions that are relevant to accomplishing the task described in the executive summary.

Return your response as a JSON array with exactly 10 objects, each having "topic", "description", and "citation" fields. Example format:
[{"topic": "Topic Name", "description": "Detailed description", "citation": "Source URL or publication"}, ...]""",
    "research-system-prompt": """You will be working on researching information for a task. You are a consultant who uses web search to find current, accurate information from reliable sources. The user will provide an executive summary of the task at hand. Output each search result with a clear topic name, detailed description with specific facts, and proper source citation.""",
    "meeting-sub-report-prompt": """You are creating a summary report for a meeting. The meeting was about:

Topic: {MEETING_TOPIC}
Description: {MEETING_DESCRIPTION}

Here is the full conversation transcript:
{TRANSCRIPT}

Please create a concise summary report that captures:
1. The main insights and perspectives shared by team members
2. Key decisions or recommendations that emerged
3. Important concerns or considerations raised
4. Next steps or action items if any were discussed

Write this as a professional summary report in 2-3 paragraphs.""",
    "meeting-expert-instructions": """This is who you are: {PERSON_DESCRIPTION}

Meeting context: {SUMMARY}

Current Focus: {MEETING_DESCRIPTION}

Respond to your colleagues in one simple paragraph. Be focused on the task and always raise your unique perspective and speak out and collaborate with your brilliant team to build great ideas.""",
    "report-system-prompt": """You are a seasoned executive brief writer who's worked for senior government decision-makers. You are tasked with creating a comprehensive final report from sub reports of various meetings. Create cohesive report that tells a story. Highlight creative ideas. Give suggestions on implementation ideas. Identify common themes and patterns across all meetings. Organize the ideas and insights in a logical structure. Use paragraphs and use formal English. Use markdown formatting for headers and emphasis.""",
    "report-user-prompt": """You are a seasoned executive brief writer who's worked for senior government decision-makers. You are tasked with creating a comprehensive final report from sub reports of various meetings. This is the task at hand:

{DISCOVERY_SUMMARY}

And here are the summaries from the meetings:
{COMBINED_SUB_REPORTS}"""
}

def load_prompts() -> dict:
    prompts_path = get_prompts_path()
    if prompts_path.exists():
        with open(prompts_path, 'r') as f:
            data = json.load(f)
            return {p['id']: p['content'] for p in data.get('prompts', [])}
    save_prompts(DEFAULT_PROMPTS)
    return DEFAULT_PROMPTS

def save_prompts(prompts: dict):
    data = {
        "prompts": [{"id": k, "content": v, "name": k.replace("-", " ").title()} for k, v in prompts.items()],
        "version": "1.0"
    }
    with open(get_prompts_path(), 'w') as f:
        json.dump(data, f, indent=2)

def get_prompt(prompt_id: str) -> str:
    prompts = load_prompts()
    return prompts.get(prompt_id, DEFAULT_PROMPTS.get(prompt_id, ""))

# ============================================================
# SESSION MANAGEMENT
# ============================================================

def load_sessions_metadata() -> list:
    metadata_path = get_sessions_dir() / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            return json.load(f)
    return []

def save_sessions_metadata(sessions: list):
    with open(get_sessions_dir() / "metadata.json", 'w') as f:
        json.dump(sessions, f, indent=2)

def create_session(name: str) -> dict:
    session_data = {
        "id": str(uuid.uuid4()),
        "name": name,
        "created_date": datetime.now().isoformat(),
        "last_modified_date": datetime.now().isoformat()
    }
    sessions = load_sessions_metadata()
    sessions.append(session_data)
    save_sessions_metadata(sessions)
    return session_data

def delete_session(session_id: str):
    sessions = load_sessions_metadata()
    sessions = [s for s in sessions if s['id'] != session_id]
    save_sessions_metadata(sessions)
    session_file = get_sessions_dir() / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()

def load_session_data(session_id: str) -> dict:
    session_file = get_sessions_dir() / f"{session_id}.json"
    if session_file.exists():
        with open(session_file, 'r') as f:
            return json.load(f)
    return {
        "messages": [],
        "summary": "",
        "people": [],
        "research_findings": [],
        "meetings": [],
        "final_report": "",
        "report_chat_messages": []
    }

def save_session_data(session_id: str, data: dict):
    with open(get_sessions_dir() / f"{session_id}.json", 'w') as f:
        json.dump(data, f, indent=2)

# ============================================================
# OPENAI API SERVICE
# ============================================================

class OpenAIService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = "gpt-4o"

    def send_message(self, messages: list, system_prompt: str = None) -> str:
        if not self.client:
            return "Error: API key not configured. Please set your API key in Settings."
        try:
            api_messages = []
            if system_prompt:
                api_messages.append({"role": "system", "content": system_prompt})
            api_messages.extend([{"role": m["role"], "content": m["content"]} for m in messages])

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                messages=api_messages
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

def get_api_service() -> OpenAIService:
    config = load_config()
    api_key = config.get('api_key', os.environ.get('OPENAI_API_KEY', ''))
    return OpenAIService(api_key)

# ============================================================
# API ROUTES - Authentication
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    if check_password(username, password):
        session['user'] = {
            'username': username,
            'name': USERS[username]['name'],
            'role': USERS[username]['role']
        }
        return jsonify({
            "success": True,
            "user": session['user']
        })
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"success": True})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    if 'user' in session:
        return jsonify({"authenticated": True, "user": session['user']})
    return jsonify({"authenticated": False})

# ============================================================
# API ROUTES - Sessions
# ============================================================

@app.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    sessions = load_sessions_metadata()
    return jsonify(sessions)

@app.route('/api/sessions', methods=['POST'])
@login_required
def create_new_session():
    data = request.json
    name = data.get('name', f"Session {len(load_sessions_metadata()) + 1}")
    new_session = create_session(name)
    return jsonify(new_session)

@app.route('/api/sessions/<session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    data = load_session_data(session_id)
    return jsonify(data)

@app.route('/api/sessions/<session_id>', methods=['PUT'])
@login_required
def update_session(session_id):
    data = request.json
    save_session_data(session_id, data)
    return jsonify({"success": True})

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
@login_required
def remove_session(session_id):
    delete_session(session_id)
    return jsonify({"success": True})

# ============================================================
# API ROUTES - AI Operations
# ============================================================

@app.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    data = request.json
    messages = data.get('messages', [])
    system_prompt = data.get('system_prompt')

    service = get_api_service()
    response = service.send_message(messages, system_prompt)
    return jsonify({"response": response})

@app.route('/api/ai/generate-summary', methods=['POST'])
@login_required
def generate_summary():
    data = request.json
    messages = data.get('messages', [])

    service = get_api_service()
    summary_messages = messages.copy()
    summary_messages.append({"role": "user", "content": get_prompt("discovery-summarize")})

    response = service.send_message(summary_messages)
    return jsonify({"summary": response})

@app.route('/api/ai/generate-people', methods=['POST'])
@login_required
def generate_people():
    data = request.json
    summary = data.get('summary', '')

    service = get_api_service()
    user_prompt = get_prompt("people-user-prompt").replace("{EXECUTIVE_SUMMARY}", summary)
    system_prompt = get_prompt("people-system-prompt")

    messages = [{"role": "user", "content": user_prompt}]
    response = service.send_message(messages, system_prompt)

    # Parse JSON response
    import re
    try:
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            people_data = json.loads(json_match.group())
            people = [
                {"id": str(uuid.uuid4()), "title": p["title"], "description": p["description"]}
                for p in people_data[:5]
            ]
            return jsonify({"people": people})
    except Exception as e:
        return jsonify({"error": str(e), "raw_response": response}), 500

    return jsonify({"error": "Failed to parse response", "raw_response": response}), 500

@app.route('/api/ai/generate-research', methods=['POST'])
@login_required
def generate_research():
    data = request.json
    summary = data.get('summary', '')

    service = get_api_service()
    user_prompt = get_prompt("research-user-prompt").replace("{EXECUTIVE_SUMMARY}", summary)
    system_prompt = get_prompt("research-system-prompt")

    messages = [{"role": "user", "content": user_prompt}]
    response = service.send_message(messages, system_prompt)

    # Parse JSON response
    import re
    try:
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            findings_data = json.loads(json_match.group())
            findings = [
                {
                    "id": str(uuid.uuid4()),
                    "topic": f["topic"],
                    "description": f["description"],
                    "citation": f["citation"]
                }
                for f in findings_data[:10]
            ]
            return jsonify({"findings": findings})
    except Exception as e:
        return jsonify({"error": str(e), "raw_response": response}), 500

    return jsonify({"error": "Failed to parse response", "raw_response": response}), 500

@app.route('/api/ai/meeting-response', methods=['POST'])
@login_required
def get_meeting_response():
    data = request.json
    person = data.get('person', {})
    meeting = data.get('meeting', {})
    summary = data.get('summary', '')
    user_question = data.get('user_question')

    service = get_api_service()

    prompt = get_prompt("meeting-expert-instructions")
    prompt = prompt.replace("{PERSON_DESCRIPTION}", person.get('description', ''))
    prompt = prompt.replace("{SUMMARY}", summary)
    prompt = prompt.replace("{MEETING_DESCRIPTION}", meeting.get('description', ''))

    history = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": "Understood. I'm ready to participate in the meeting."}
    ]

    # Add meeting messages
    for msg in meeting.get('messages', [])[1:]:
        if msg.get('participant_id') or msg.get('participant_name') == "You":
            history.append({
                "role": "user",
                "content": f"{msg['participant_name']} said: {msg['content']}\n\nPlease respond as the {person['title']}."
            })

    if len(meeting.get('messages', [])) == 1:
        history.append({
            "role": "user",
            "content": "Please share your initial thoughts on this topic."
        })
    elif user_question:
        history.append({
            "role": "user",
            "content": f"The facilitator asks you directly: {user_question}\n\nPlease respond as the {person['title']}."
        })

    response = service.send_message(history)
    return jsonify({"response": response})

@app.route('/api/ai/meeting-summary', methods=['POST'])
@login_required
def generate_meeting_summary():
    data = request.json
    meeting = data.get('meeting', {})

    service = get_api_service()

    transcript = ""
    for msg in meeting.get('messages', [])[1:]:
        if msg.get('participant_id') or msg.get('participant_name') == "You":
            transcript += f"\n\n[{msg['participant_name']}]:\n{msg['content']}"

    prompt = get_prompt("meeting-sub-report-prompt")
    prompt = prompt.replace("{MEETING_TOPIC}", meeting.get('topic', ''))
    prompt = prompt.replace("{MEETING_DESCRIPTION}", meeting.get('description', ''))
    prompt = prompt.replace("{TRANSCRIPT}", transcript)

    messages = [{"role": "user", "content": prompt}]
    response = service.send_message(messages)

    return jsonify({"summary": response})

@app.route('/api/ai/generate-report', methods=['POST'])
@login_required
def generate_final_report():
    data = request.json
    summary = data.get('summary', '')
    meetings = data.get('meetings', [])

    service = get_api_service()

    summaries = []
    for i, meeting in enumerate(meetings):
        if meeting.get('summary_report'):
            summaries.append(f"=== Meeting {i+1} Summary ===\n\n{meeting['summary_report']}")

    combined_summaries = "\n\n---\n\n".join(summaries)

    system_prompt = get_prompt("report-system-prompt")
    user_prompt = get_prompt("report-user-prompt")
    user_prompt = user_prompt.replace("{DISCOVERY_SUMMARY}", summary)
    user_prompt = user_prompt.replace("{COMBINED_SUB_REPORTS}", combined_summaries)

    messages = [{"role": "user", "content": user_prompt}]
    response = service.send_message(messages, system_prompt)

    return jsonify({"report": response})

# ============================================================
# API ROUTES - Settings
# ============================================================

@app.route('/api/settings/api-key', methods=['GET'])
@login_required
def get_api_key_status():
    config = load_config()
    has_key = bool(config.get('api_key') or os.environ.get('OPENAI_API_KEY'))
    return jsonify({"configured": has_key})

@app.route('/api/settings/api-key', methods=['POST'])
@login_required
def set_api_key():
    data = request.json
    api_key = data.get('api_key', '')
    config = load_config()
    config['api_key'] = api_key
    save_config(config)
    return jsonify({"success": True})

@app.route('/api/prompts', methods=['GET'])
@login_required
def get_prompts():
    prompts = load_prompts()
    return jsonify(prompts)

@app.route('/api/prompts', methods=['POST'])
@login_required
def update_prompts():
    data = request.json
    save_prompts(data)
    return jsonify({"success": True})

@app.route('/api/prompts/reset', methods=['POST'])
@login_required
def reset_prompts():
    save_prompts(DEFAULT_PROMPTS)
    return jsonify({"success": True})

# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
