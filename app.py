"""
Virtual Lab - Research Collaboration Tool
A Python/Streamlit rebuild of the Virtual Lab Swift application

This app helps conduct structured research through:
1. Discovery - Chat with AI to understand a task
2. Task/Summary - Generate an executive summary
3. People - AI identifies interdisciplinary team members
4. Research - Find relevant precedents/examples
5. Meetings - Simulate expert discussions
6. Report - Generate a comprehensive final report
7. Export - Save the report
"""

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
import uuid
import anthropic

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class Message:
    role: str
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Person:
    title: str
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class ResearchFinding:
    topic: str
    description: str
    citation: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class MeetingMessage:
    participant_name: str
    content: str
    participant_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Meeting:
    topic: str
    description: str
    messages: list = field(default_factory=list)
    is_complete: bool = False
    turn_count: int = 0
    summary_report: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Session:
    name: str
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_modified_date: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

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

# ============================================================
# FILE PATHS AND STORAGE
# ============================================================

def get_data_dir() -> Path:
    """Get the data directory for storing sessions and config."""
    data_dir = Path.home() / ".virtual_lab"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_sessions_dir() -> Path:
    """Get the sessions directory."""
    sessions_dir = get_data_dir() / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    return sessions_dir

def get_config_path() -> Path:
    """Get the config file path."""
    return get_data_dir() / "config.json"

def get_prompts_path() -> Path:
    """Get the prompts file path."""
    return get_data_dir() / "prompts.json"

# ============================================================
# CONFIGURATION MANAGEMENT
# ============================================================

def load_config() -> dict:
    """Load configuration including API key."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {"api_key": ""}

def save_config(config: dict):
    """Save configuration."""
    with open(get_config_path(), 'w') as f:
        json.dump(config, f, indent=2)

def load_prompts() -> dict:
    """Load prompts from file or return defaults."""
    prompts_path = get_prompts_path()
    if prompts_path.exists():
        with open(prompts_path, 'r') as f:
            data = json.load(f)
            return {p['id']: p['content'] for p in data.get('prompts', [])}
    # Save defaults if file doesn't exist
    save_prompts(DEFAULT_PROMPTS)
    return DEFAULT_PROMPTS

def save_prompts(prompts: dict):
    """Save prompts to file."""
    data = {
        "prompts": [{"id": k, "content": v, "name": k.replace("-", " ").title()} for k, v in prompts.items()],
        "version": "1.0"
    }
    with open(get_prompts_path(), 'w') as f:
        json.dump(data, f, indent=2)

def get_prompt(prompt_id: str) -> str:
    """Get a prompt by ID."""
    prompts = load_prompts()
    return prompts.get(prompt_id, DEFAULT_PROMPTS.get(prompt_id, ""))

# ============================================================
# SESSION MANAGEMENT
# ============================================================

def load_sessions_metadata() -> list:
    """Load list of all sessions."""
    metadata_path = get_sessions_dir() / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            return json.load(f)
    return []

def save_sessions_metadata(sessions: list):
    """Save sessions metadata."""
    with open(get_sessions_dir() / "metadata.json", 'w') as f:
        json.dump(sessions, f, indent=2)

def create_session(name: str) -> Session:
    """Create a new session."""
    session = Session(name=name)
    sessions = load_sessions_metadata()
    sessions.append(asdict(session))
    save_sessions_metadata(sessions)
    return session

def delete_session(session_id: str):
    """Delete a session."""
    sessions = load_sessions_metadata()
    sessions = [s for s in sessions if s['id'] != session_id]
    save_sessions_metadata(sessions)
    # Delete session data file
    session_file = get_sessions_dir() / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()

def load_session_data(session_id: str) -> dict:
    """Load data for a specific session."""
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
    """Save data for a specific session."""
    with open(get_sessions_dir() / f"{session_id}.json", 'w') as f:
        json.dump(data, f, indent=2)

# ============================================================
# ANTHROPIC API SERVICE
# ============================================================

class AnthropicService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.model = "claude-sonnet-4-5-20250929"

    def send_message(self, messages: list, system_prompt: str = None) -> str:
        """Send a message and get a response."""
        if not self.client:
            return "Error: API key not configured. Please set your API key in Settings."

        try:
            api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

            kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": api_messages
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            return f"Error: {str(e)}"

# ============================================================
# INITIALIZE SESSION STATE
# ============================================================

def init_session_state():
    """Initialize Streamlit session state."""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True

        # Load config
        config = load_config()
        st.session_state.api_key = config.get('api_key', '')

        # Load or create session
        sessions = load_sessions_metadata()
        if not sessions:
            session = create_session("Session 1")
            st.session_state.current_session_id = session.id
        else:
            st.session_state.current_session_id = sessions[0]['id']

        # Load session data
        load_current_session_data()

        # Navigation state
        st.session_state.current_stage = "discovery"

        # Loading states
        st.session_state.is_loading = False
        st.session_state.is_generating_summary = False
        st.session_state.is_analyzing_people = False
        st.session_state.is_searching = False
        st.session_state.is_running_meetings = False
        st.session_state.is_generating_report = False

def load_current_session_data():
    """Load data for the current session into session state."""
    data = load_session_data(st.session_state.current_session_id)
    st.session_state.messages = data.get('messages', [])
    st.session_state.summary = data.get('summary', '')
    st.session_state.people = data.get('people', [])
    st.session_state.research_findings = data.get('research_findings', [])
    st.session_state.meetings = data.get('meetings', [])
    st.session_state.final_report = data.get('final_report', '')
    st.session_state.report_chat_messages = data.get('report_chat_messages', [])

def save_current_session_data():
    """Save current session data."""
    data = {
        "messages": st.session_state.messages,
        "summary": st.session_state.summary,
        "people": st.session_state.people,
        "research_findings": st.session_state.research_findings,
        "meetings": st.session_state.meetings,
        "final_report": st.session_state.final_report,
        "report_chat_messages": st.session_state.report_chat_messages
    }
    save_session_data(st.session_state.current_session_id, data)

def get_api_service() -> AnthropicService:
    """Get the Anthropic API service."""
    return AnthropicService(st.session_state.api_key)

# ============================================================
# STAGE VIEWS
# ============================================================

def discovery_view():
    """Discovery chat view."""
    st.header("💡 Discovery")
    st.caption("Chat with AI to understand your task")

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    if prompt := st.chat_input("Type your message...", disabled=st.session_state.is_loading):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get AI response
        st.session_state.is_loading = True
        service = get_api_service()

        # Add discovery prompt to conversation
        discovery_messages = st.session_state.messages.copy()
        discovery_messages.append({"role": "user", "content": get_prompt("discovery-message")})

        response = service.send_message(discovery_messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.is_loading = False
        save_current_session_data()
        st.rerun()

    # Next button
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Generate Summary →", type="primary", disabled=len(st.session_state.messages) < 2):
            generate_summary()

def generate_summary():
    """Generate executive summary from discovery chat."""
    st.session_state.is_generating_summary = True
    service = get_api_service()

    summary_messages = st.session_state.messages.copy()
    summary_messages.append({"role": "user", "content": get_prompt("discovery-summarize")})

    response = service.send_message(summary_messages)
    st.session_state.summary = response
    st.session_state.is_generating_summary = False
    st.session_state.current_stage = "task"
    save_current_session_data()
    st.rerun()

def task_view():
    """Task/Summary view."""
    st.header("📄 Task Summary")
    st.caption("Executive summary of your task")

    if st.session_state.summary:
        st.markdown(st.session_state.summary)

        # Edit summary
        with st.expander("Edit Summary"):
            new_summary = st.text_area("Summary", st.session_state.summary, height=200)
            if st.button("Save Changes"):
                st.session_state.summary = new_summary
                save_current_session_data()
                st.success("Summary saved!")
                st.rerun()
    else:
        st.info("No summary generated yet. Go to Discovery to chat and generate a summary.")

    # Next button
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Identify Team →", type="primary", disabled=not st.session_state.summary):
            generate_people()

def generate_people():
    """Generate team members based on task."""
    st.session_state.is_analyzing_people = True
    service = get_api_service()

    user_prompt = get_prompt("people-user-prompt").replace("{EXECUTIVE_SUMMARY}", st.session_state.summary)
    system_prompt = get_prompt("people-system-prompt")

    messages = [{"role": "user", "content": user_prompt}]
    response = service.send_message(messages, system_prompt)

    # Parse JSON response
    try:
        # Find JSON array in response
        import re
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            people_data = json.loads(json_match.group())
            st.session_state.people = [
                {"id": str(uuid.uuid4()), "title": p["title"], "description": p["description"]}
                for p in people_data[:5]
            ]
    except Exception as e:
        st.error(f"Error parsing people: {e}")

    st.session_state.is_analyzing_people = False
    st.session_state.current_stage = "people"
    save_current_session_data()
    st.rerun()

def people_view():
    """People/Team view."""
    st.header("👥 Team Members")
    st.caption("Interdisciplinary experts for your task")

    if st.session_state.people:
        for i, person in enumerate(st.session_state.people):
            with st.expander(f"**{person['title']}**", expanded=True):
                st.write(person['description'])

                # Edit person
                new_title = st.text_input(f"Title###{i}", person['title'], key=f"title_{i}")
                new_desc = st.text_area(f"Description###{i}", person['description'], key=f"desc_{i}")
                if st.button(f"Save###{i}", key=f"save_{i}"):
                    st.session_state.people[i]['title'] = new_title
                    st.session_state.people[i]['description'] = new_desc
                    save_current_session_data()
                    st.success("Saved!")
                    st.rerun()
    else:
        st.info("No team members identified yet. Generate a summary first, then identify the team.")

    # Regenerate button
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if st.button("🔄 Regenerate", disabled=not st.session_state.summary):
            generate_people()

    # Next button
    with col3:
        if st.button("Research →", type="primary", disabled=not st.session_state.people):
            generate_research()

def generate_research():
    """Generate research findings."""
    st.session_state.is_searching = True
    service = get_api_service()

    user_prompt = get_prompt("research-user-prompt").replace("{EXECUTIVE_SUMMARY}", st.session_state.summary)
    system_prompt = get_prompt("research-system-prompt")

    messages = [{"role": "user", "content": user_prompt}]
    response = service.send_message(messages, system_prompt)

    # Parse JSON response
    try:
        import re
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            findings_data = json.loads(json_match.group())
            st.session_state.research_findings = [
                {
                    "id": str(uuid.uuid4()),
                    "topic": f["topic"],
                    "description": f["description"],
                    "citation": f["citation"]
                }
                for f in findings_data[:10]
            ]
    except Exception as e:
        st.error(f"Error parsing research: {e}")

    st.session_state.is_searching = False
    st.session_state.current_stage = "research"
    save_current_session_data()
    st.rerun()

def research_view():
    """Research findings view."""
    st.header("🌍 Research")
    st.caption("Precedents and examples from around the world")

    if st.session_state.research_findings:
        for i, finding in enumerate(st.session_state.research_findings):
            with st.expander(f"**{finding['topic']}**", expanded=False):
                st.write(finding['description'])
                st.caption(f"📎 Source: {finding['citation']}")
    else:
        st.info("No research findings yet. Identify team members first, then conduct research.")

    # Regenerate button
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if st.button("🔄 Regenerate", disabled=not st.session_state.summary):
            generate_research()

    # Next button
    with col3:
        if st.button("Meetings →", type="primary", disabled=not st.session_state.research_findings):
            initialize_meetings()

def initialize_meetings():
    """Initialize meetings from research findings."""
    if not st.session_state.meetings:
        meetings = []
        for finding in st.session_state.research_findings:
            meeting = {
                "id": str(uuid.uuid4()),
                "topic": finding['topic'],
                "description": finding['description'],
                "messages": [{
                    "id": str(uuid.uuid4()),
                    "participant_name": f"Meeting Topic: {finding['topic']}",
                    "content": finding['description'],
                    "participant_id": None
                }],
                "is_complete": False,
                "turn_count": 0,
                "summary_report": None
            }
            meetings.append(meeting)
        st.session_state.meetings = meetings
        save_current_session_data()

    st.session_state.current_stage = "meetings"
    st.rerun()

def meetings_view():
    """Meetings simulation view."""
    st.header("💬 Meetings")
    st.caption("Simulated discussions between experts")

    if not st.session_state.meetings:
        st.info("No meetings initialized. Complete research first.")
        return

    # Meeting selector
    meeting_options = [f"{m['topic']}" for m in st.session_state.meetings]
    selected_idx = st.selectbox(
        "Select Meeting",
        range(len(meeting_options)),
        format_func=lambda x: f"{'✅' if st.session_state.meetings[x]['is_complete'] else '🔄'} {meeting_options[x]}"
    )

    meeting = st.session_state.meetings[selected_idx]

    # Display meeting messages
    st.subheader(meeting['topic'])
    st.caption(meeting['description'])
    st.divider()

    for msg in meeting['messages']:
        if msg['participant_name'].startswith("Meeting Topic:"):
            continue
        with st.chat_message("assistant" if msg['participant_id'] else "user"):
            st.markdown(f"**{msg['participant_name']}**")
            st.write(msg['content'])

    # Meeting controls
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ Run This Meeting", disabled=meeting['is_complete'] or st.session_state.is_running_meetings):
            run_single_meeting(selected_idx)

    with col2:
        if st.button("▶️ Run All Meetings", disabled=st.session_state.is_running_meetings):
            run_all_meetings()

    with col3:
        if st.button("🔄 Reset Meeting"):
            st.session_state.meetings[selected_idx]['messages'] = [{
                "id": str(uuid.uuid4()),
                "participant_name": f"Meeting Topic: {meeting['topic']}",
                "content": meeting['description'],
                "participant_id": None
            }]
            st.session_state.meetings[selected_idx]['is_complete'] = False
            st.session_state.meetings[selected_idx]['turn_count'] = 0
            st.session_state.meetings[selected_idx]['summary_report'] = None
            save_current_session_data()
            st.rerun()

    # Show summary if complete
    if meeting['summary_report']:
        st.divider()
        st.subheader("Meeting Summary")
        st.markdown(meeting['summary_report'])

    # Next button
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col2:
        completed_meetings = sum(1 for m in st.session_state.meetings if m['is_complete'])
        if st.button(f"Generate Report →", type="primary", disabled=completed_meetings == 0):
            st.session_state.current_stage = "report"
            st.rerun()

def run_single_meeting(meeting_idx: int, max_turns: int = 10):
    """Run a single meeting simulation."""
    st.session_state.is_running_meetings = True
    service = get_api_service()
    meeting = st.session_state.meetings[meeting_idx]

    with st.spinner(f"Running meeting: {meeting['topic']}..."):
        while meeting['turn_count'] < max_turns:
            # Select next participant (round-robin through people)
            person_idx = meeting['turn_count'] % len(st.session_state.people)
            person = st.session_state.people[person_idx]

            # Build conversation history
            history = build_meeting_history(person, meeting)

            # Get response
            response = service.send_message(history)

            # Add message to meeting
            meeting['messages'].append({
                "id": str(uuid.uuid4()),
                "participant_name": person['title'],
                "content": response,
                "participant_id": person['id']
            })

            meeting['turn_count'] += 1
            save_current_session_data()

        # Generate meeting summary
        meeting['is_complete'] = True
        generate_meeting_summary(meeting_idx)

    st.session_state.is_running_meetings = False
    st.rerun()

def run_all_meetings():
    """Run all incomplete meetings."""
    for idx, meeting in enumerate(st.session_state.meetings):
        if not meeting['is_complete']:
            run_single_meeting(idx)

def build_meeting_history(person: dict, meeting: dict) -> list:
    """Build conversation history for a meeting participant."""
    prompt = get_prompt("meeting-expert-instructions")
    prompt = prompt.replace("{PERSON_DESCRIPTION}", person['description'])
    prompt = prompt.replace("{SUMMARY}", st.session_state.summary)
    prompt = prompt.replace("{MEETING_DESCRIPTION}", meeting['description'])

    history = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": "Understood. I'm ready to participate in the meeting."}
    ]

    # Add meeting messages
    for msg in meeting['messages'][1:]:  # Skip topic message
        if msg['participant_id'] or msg['participant_name'] == "You":
            history.append({
                "role": "user",
                "content": f"{msg['participant_name']} said: {msg['content']}\n\nPlease respond as the {person['title']}."
            })

    if len(meeting['messages']) == 1:
        history.append({
            "role": "user",
            "content": "Please share your initial thoughts on this feature."
        })

    return history

def generate_meeting_summary(meeting_idx: int):
    """Generate a summary for a meeting."""
    service = get_api_service()
    meeting = st.session_state.meetings[meeting_idx]

    # Build transcript
    transcript = ""
    for msg in meeting['messages'][1:]:  # Skip topic
        if msg['participant_id'] or msg['participant_name'] == "You":
            transcript += f"\n\n[{msg['participant_name']}]:\n{msg['content']}"

    prompt = get_prompt("meeting-sub-report-prompt")
    prompt = prompt.replace("{MEETING_TOPIC}", meeting['topic'])
    prompt = prompt.replace("{MEETING_DESCRIPTION}", meeting['description'])
    prompt = prompt.replace("{TRANSCRIPT}", transcript)

    messages = [{"role": "user", "content": prompt}]
    response = service.send_message(messages)

    st.session_state.meetings[meeting_idx]['summary_report'] = response
    save_current_session_data()

def report_view():
    """Final report view."""
    st.header("📊 Final Report")
    st.caption("Comprehensive report from all meetings")

    if st.session_state.final_report:
        st.markdown(st.session_state.final_report)

        # Report chat
        st.divider()
        st.subheader("💬 Ask Questions About the Report")

        for msg in st.session_state.report_chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("Ask a question about the report..."):
            st.session_state.report_chat_messages.append({"role": "user", "content": prompt})

            # Build context
            full_context = build_full_meeting_context()
            context_message = f"""EXECUTIVE SUMMARY:
{st.session_state.summary}

FINAL REPORT:
{st.session_state.final_report}

ALL MEETING TRANSCRIPTS:
{full_context}

USER QUESTION:
{prompt}

Please answer the user's question by searching through all the meeting transcripts and the final report. Include specific quotes from experts when relevant."""

            service = get_api_service()
            system_prompt = """You are an AI assistant helping to answer questions about a policy report and the meetings that led to it.

You have access to:
1. The final report that was generated
2. Full transcripts from all meetings between interdisciplinary experts
3. The original executive summary/task description

When answering questions:
- Search through all meeting transcripts to find relevant insights and nuances
- Quote specific experts when relevant
- Highlight interesting points that may not have made it into the final report
- Be thorough but concise
- If asked about specific topics, search all meetings for related discussions"""

            response = service.send_message([{"role": "user", "content": context_message}], system_prompt)
            st.session_state.report_chat_messages.append({"role": "assistant", "content": response})
            save_current_session_data()
            st.rerun()
    else:
        # Show available summaries
        completed = [m for m in st.session_state.meetings if m['summary_report']]
        st.info(f"{len(completed)}/{len(st.session_state.meetings)} meetings have summaries")

        if completed:
            if st.button("🔄 Generate Final Report", type="primary"):
                generate_final_report()
        else:
            st.warning("Complete at least one meeting to generate a report.")

def build_full_meeting_context() -> str:
    """Build context from all meetings."""
    context = ""
    for i, meeting in enumerate(st.session_state.meetings):
        context += f"\n\n=== MEETING {i+1}: {meeting['topic']} ===\n"
        context += f"Description: {meeting['description']}\n"
        context += "Meeting Transcript:\n"

        for msg in meeting['messages']:
            if not msg['participant_name'].startswith("Meeting Topic:"):
                context += f"\n[{msg['participant_name']}]: {msg['content']}"

        if meeting.get('summary_report'):
            context += f"\n\nMeeting Summary: {meeting['summary_report']}"

        context += "\n\n---"

    return context

def generate_final_report():
    """Generate the final comprehensive report."""
    st.session_state.is_generating_report = True
    service = get_api_service()

    # Collect summaries
    summaries = []
    for i, meeting in enumerate(st.session_state.meetings):
        if meeting.get('summary_report'):
            summaries.append(f"=== Meeting {i+1} Summary ===\n\n{meeting['summary_report']}")

    combined_summaries = "\n\n---\n\n".join(summaries)

    system_prompt = get_prompt("report-system-prompt")
    user_prompt = get_prompt("report-user-prompt")
    user_prompt = user_prompt.replace("{DISCOVERY_SUMMARY}", st.session_state.summary)
    user_prompt = user_prompt.replace("{COMBINED_SUB_REPORTS}", combined_summaries)

    messages = [{"role": "user", "content": user_prompt}]
    response = service.send_message(messages, system_prompt)

    st.session_state.final_report = response
    st.session_state.is_generating_report = False
    save_current_session_data()
    st.rerun()

def export_view():
    """Export view for downloading the report."""
    st.header("📤 Export")
    st.caption("Download your report")

    if st.session_state.final_report:
        st.subheader("Final Report")
        st.markdown(st.session_state.final_report[:500] + "..." if len(st.session_state.final_report) > 500 else st.session_state.final_report)

        # Download buttons
        col1, col2 = st.columns(2)

        with col1:
            # Markdown download
            st.download_button(
                label="📥 Download as Markdown",
                data=st.session_state.final_report,
                file_name="virtual_lab_report.md",
                mime="text/markdown"
            )

        with col2:
            # Full export (JSON with all data)
            full_export = {
                "summary": st.session_state.summary,
                "people": st.session_state.people,
                "research_findings": st.session_state.research_findings,
                "meetings": st.session_state.meetings,
                "final_report": st.session_state.final_report,
                "exported_at": datetime.now().isoformat()
            }
            st.download_button(
                label="📥 Download Full Data (JSON)",
                data=json.dumps(full_export, indent=2),
                file_name="virtual_lab_full_export.json",
                mime="application/json"
            )
    else:
        st.info("No report to export yet. Generate a final report first.")

def prompts_view():
    """Prompts settings view."""
    st.header("⚙️ Prompts")
    st.caption("Customize AI prompts")

    prompts = load_prompts()

    for prompt_id, content in prompts.items():
        with st.expander(prompt_id.replace("-", " ").title()):
            new_content = st.text_area(
                "Prompt",
                content,
                height=150,
                key=f"prompt_{prompt_id}"
            )
            if st.button(f"Save", key=f"save_prompt_{prompt_id}"):
                prompts[prompt_id] = new_content
                save_prompts(prompts)
                st.success("Saved!")

    if st.button("Reset to Defaults"):
        save_prompts(DEFAULT_PROMPTS)
        st.success("Reset to defaults!")
        st.rerun()

def settings_view():
    """Settings view for API key."""
    st.header("🔑 Settings")
    st.caption("Configure your API key")

    # API Key input
    api_key = st.text_input(
        "Anthropic API Key",
        value=st.session_state.api_key,
        type="password",
        help="Enter your Anthropic API key to use the AI features"
    )

    if st.button("Save API Key"):
        st.session_state.api_key = api_key
        save_config({"api_key": api_key})
        st.success("API key saved!")

    # API key status
    if st.session_state.api_key:
        st.success("✅ API key is configured")
    else:
        st.warning("⚠️ No API key configured")
        st.markdown("""
        To get an API key:
        1. Go to [console.anthropic.com](https://console.anthropic.com)
        2. Sign up or log in
        3. Navigate to API Keys
        4. Create a new API key
        5. Paste it above
        """)

# ============================================================
# SIDEBAR
# ============================================================

def render_sidebar():
    """Render the sidebar navigation."""
    with st.sidebar:
        st.title("🧪 Virtual Lab")

        # Session selector
        sessions = load_sessions_metadata()
        current_session = next((s for s in sessions if s['id'] == st.session_state.current_session_id), None)

        st.subheader("Current Session")
        session_names = [s['name'] for s in sessions]
        selected_idx = session_names.index(current_session['name']) if current_session else 0

        new_session_idx = st.selectbox(
            "Session",
            range(len(session_names)),
            format_func=lambda x: session_names[x],
            index=selected_idx,
            label_visibility="collapsed"
        )

        if sessions[new_session_idx]['id'] != st.session_state.current_session_id:
            save_current_session_data()
            st.session_state.current_session_id = sessions[new_session_idx]['id']
            load_current_session_data()
            st.rerun()

        # Session management
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ New", use_container_width=True):
                new_session = create_session(f"Session {len(sessions) + 1}")
                st.session_state.current_session_id = new_session.id
                load_current_session_data()
                st.rerun()

        with col2:
            if st.button("🗑️ Delete", use_container_width=True, disabled=len(sessions) <= 1):
                delete_session(st.session_state.current_session_id)
                sessions = load_sessions_metadata()
                st.session_state.current_session_id = sessions[0]['id']
                load_current_session_data()
                st.rerun()

        st.divider()

        # Navigation
        stages = [
            ("discovery", "💡", "Discovery"),
            ("task", "📄", "Task"),
            ("people", "👥", "People"),
            ("research", "🌍", "Research"),
            ("meetings", "💬", "Meetings"),
            ("report", "📊", "Report"),
        ]

        for stage_id, icon, label in stages:
            if st.button(f"{icon} {label}", use_container_width=True,
                        type="primary" if st.session_state.current_stage == stage_id else "secondary"):
                st.session_state.current_stage = stage_id
                st.rerun()

        st.divider()

        # Settings
        settings_stages = [
            ("prompts", "⚙️", "Prompts"),
            ("settings", "🔑", "API Key"),
            ("export", "📤", "Export"),
        ]

        for stage_id, icon, label in settings_stages:
            if st.button(f"{icon} {label}", use_container_width=True,
                        type="primary" if st.session_state.current_stage == stage_id else "secondary"):
                st.session_state.current_stage = stage_id
                st.rerun()

# ============================================================
# MAIN APP
# ============================================================

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Virtual Lab",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    init_session_state()

    # Render sidebar
    render_sidebar()

    # Main content area
    stage = st.session_state.current_stage

    if stage == "discovery":
        discovery_view()
    elif stage == "task":
        task_view()
    elif stage == "people":
        people_view()
    elif stage == "research":
        research_view()
    elif stage == "meetings":
        meetings_view()
    elif stage == "report":
        report_view()
    elif stage == "export":
        export_view()
    elif stage == "prompts":
        prompts_view()
    elif stage == "settings":
        settings_view()

if __name__ == "__main__":
    main()
