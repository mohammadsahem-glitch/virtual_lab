/**
 * Virtual Lab - Frontend JavaScript
 * Handles all UI interactions and API communication
 */

// ============================================================
// STATE MANAGEMENT
// ============================================================

const state = {
    user: null,
    sessions: [],
    currentSessionId: null,
    sessionData: {
        messages: [],
        summary: '',
        people: [],
        research_findings: [],
        meetings: [],
        final_report: '',
        report_chat_messages: []
    },
    currentMeetingIndex: 0,
    meetingTurnIndex: 0
};

// ============================================================
// API HELPER FUNCTIONS
// ============================================================

async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include'
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(endpoint, options);

    if (response.status === 401) {
        showLoginPage();
        throw new Error('Unauthorized');
    }

    return response.json();
}

function showLoading(text = 'Loading...') {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// ============================================================
// AUTHENTICATION
// ============================================================

function showLoginPage() {
    document.getElementById('login-page').classList.remove('hidden');
    document.getElementById('app-page').classList.add('hidden');
}

function showAppPage() {
    document.getElementById('login-page').classList.add('hidden');
    document.getElementById('app-page').classList.remove('hidden');
}

async function checkAuth() {
    try {
        const result = await apiCall('/api/auth/check');
        if (result.authenticated) {
            state.user = result.user;
            updateUserInfo();
            showAppPage();
            await loadSessions();
        } else {
            showLoginPage();
        }
    } catch (error) {
        showLoginPage();
    }
}

async function login(username, password) {
    try {
        showLoading('Signing in...');
        const result = await apiCall('/api/auth/login', 'POST', { username, password });

        if (result.success) {
            state.user = result.user;
            updateUserInfo();
            showAppPage();
            await loadSessions();
        } else {
            document.getElementById('login-error').textContent = result.error || 'Invalid credentials';
            document.getElementById('login-error').classList.remove('hidden');
        }
    } catch (error) {
        document.getElementById('login-error').textContent = 'Login failed. Please try again.';
        document.getElementById('login-error').classList.remove('hidden');
    } finally {
        hideLoading();
    }
}

async function logout() {
    try {
        await apiCall('/api/auth/logout', 'POST');
    } catch (error) {
        console.error('Logout error:', error);
    }
    state.user = null;
    showLoginPage();
}

function updateUserInfo() {
    if (state.user) {
        document.getElementById('user-name').textContent = state.user.name;
        document.getElementById('user-role').textContent = state.user.role;
    }
}

// ============================================================
// SESSION MANAGEMENT
// ============================================================

async function loadSessions() {
    try {
        state.sessions = await apiCall('/api/sessions');
        updateSessionSelect();

        if (state.sessions.length > 0) {
            await selectSession(state.sessions[0].id);
        }
    } catch (error) {
        console.error('Failed to load sessions:', error);
    }
}

function updateSessionSelect() {
    const select = document.getElementById('session-select');
    select.innerHTML = state.sessions.map(s =>
        `<option value="${s.id}">${s.name}</option>`
    ).join('');

    if (state.currentSessionId) {
        select.value = state.currentSessionId;
    }
}

async function selectSession(sessionId) {
    try {
        showLoading('Loading session...');
        state.currentSessionId = sessionId;
        state.sessionData = await apiCall(`/api/sessions/${sessionId}`);

        // Update UI with session data
        renderDiscoveryMessages();
        renderTaskSummary();
        renderPeople();
        renderResearch();
        renderMeetings();
        renderReport();

        document.getElementById('session-select').value = sessionId;
    } catch (error) {
        console.error('Failed to load session:', error);
    } finally {
        hideLoading();
    }
}

async function createNewSession() {
    const name = prompt('Enter session name:', `Session ${state.sessions.length + 1}`);
    if (!name) return;

    try {
        showLoading('Creating session...');
        const newSession = await apiCall('/api/sessions', 'POST', { name });
        state.sessions.push(newSession);
        updateSessionSelect();
        await selectSession(newSession.id);
    } catch (error) {
        console.error('Failed to create session:', error);
        alert('Failed to create session');
    } finally {
        hideLoading();
    }
}

async function deleteCurrentSession() {
    if (!state.currentSessionId) return;
    if (!confirm('Are you sure you want to delete this session?')) return;

    try {
        showLoading('Deleting session...');
        await apiCall(`/api/sessions/${state.currentSessionId}`, 'DELETE');
        state.sessions = state.sessions.filter(s => s.id !== state.currentSessionId);
        updateSessionSelect();

        if (state.sessions.length > 0) {
            await selectSession(state.sessions[0].id);
        } else {
            state.currentSessionId = null;
            state.sessionData = {
                messages: [],
                summary: '',
                people: [],
                research_findings: [],
                meetings: [],
                final_report: '',
                report_chat_messages: []
            };
        }
    } catch (error) {
        console.error('Failed to delete session:', error);
        alert('Failed to delete session');
    } finally {
        hideLoading();
    }
}

async function saveSessionData() {
    if (!state.currentSessionId) return;

    try {
        await apiCall(`/api/sessions/${state.currentSessionId}`, 'PUT', state.sessionData);
    } catch (error) {
        console.error('Failed to save session:', error);
    }
}

// ============================================================
// NAVIGATION
// ============================================================

function switchStage(stageName) {
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.stage === stageName) {
            item.classList.add('active');
        }
    });

    // Update stages
    document.querySelectorAll('.stage').forEach(stage => {
        stage.classList.add('hidden');
    });
    document.getElementById(`stage-${stageName}`).classList.remove('hidden');
}

// ============================================================
// DISCOVERY STAGE
// ============================================================

function renderDiscoveryMessages() {
    const container = document.getElementById('discovery-messages');
    container.innerHTML = state.sessionData.messages.map(msg => `
        <div class="chat-message ${msg.role}">
            ${escapeHtml(msg.content)}
        </div>
    `).join('');
    container.scrollTop = container.scrollHeight;
}

async function sendDiscoveryMessage() {
    const input = document.getElementById('discovery-input');
    const message = input.value.trim();
    if (!message) return;

    // Add user message
    state.sessionData.messages.push({ role: 'user', content: message });
    renderDiscoveryMessages();
    input.value = '';

    try {
        showLoading('AI is thinking...');

        // Get system prompt for discovery
        const systemPrompt = "I work in Abu Dhabi. You are going to ask me a series of small concise questions to get to understand a task that I will ask a think tank to tackle. This is the phase where you ask me questions to understand the task and not to find the solution. Ask me questions to see what I care about. Be smart about it, start with broad questions then narrow down to the details. Ask simple one line questions. Be friendly.";

        const result = await apiCall('/api/ai/chat', 'POST', {
            messages: state.sessionData.messages,
            system_prompt: systemPrompt
        });

        state.sessionData.messages.push({ role: 'assistant', content: result.response });
        renderDiscoveryMessages();
        await saveSessionData();
    } catch (error) {
        console.error('Chat error:', error);
        state.sessionData.messages.push({
            role: 'assistant',
            content: 'Error: Failed to get response. Please check your API key.'
        });
        renderDiscoveryMessages();
    } finally {
        hideLoading();
    }
}

async function generateSummary() {
    if (state.sessionData.messages.length === 0) {
        alert('Please have a conversation first before generating a summary.');
        return;
    }

    try {
        showLoading('Generating summary...');
        const result = await apiCall('/api/ai/generate-summary', 'POST', {
            messages: state.sessionData.messages
        });

        state.sessionData.summary = result.summary;
        renderTaskSummary();
        await saveSessionData();
        switchStage('task');
    } catch (error) {
        console.error('Summary error:', error);
        alert('Failed to generate summary');
    } finally {
        hideLoading();
    }
}

// ============================================================
// TASK STAGE
// ============================================================

function renderTaskSummary() {
    const displayContainer = document.getElementById('task-summary-display');
    const editBtn = document.getElementById('edit-summary-btn');

    if (state.sessionData.summary) {
        displayContainer.innerHTML = `<div class="markdown-content">${formatMarkdown(state.sessionData.summary)}</div>`;
        editBtn.classList.remove('hidden');
    } else {
        displayContainer.innerHTML = '<p class="placeholder">Complete the Discovery phase to generate a task summary.</p>';
        editBtn.classList.add('hidden');
    }
}

function toggleSummaryEdit(showEdit) {
    const displayContainer = document.getElementById('task-summary-display');
    const editContainer = document.getElementById('task-summary-edit');
    const editBtn = document.getElementById('edit-summary-btn');
    const textarea = document.getElementById('task-summary-textarea');

    if (showEdit) {
        textarea.value = state.sessionData.summary;
        displayContainer.classList.add('hidden');
        editContainer.classList.remove('hidden');
        editBtn.classList.add('hidden');
    } else {
        displayContainer.classList.remove('hidden');
        editContainer.classList.add('hidden');
        editBtn.classList.remove('hidden');
    }
}

async function saveSummaryEdit() {
    const textarea = document.getElementById('task-summary-textarea');
    state.sessionData.summary = textarea.value;
    await saveSessionData();
    renderTaskSummary();
    toggleSummaryEdit(false);
}

// ============================================================
// PEOPLE STAGE
// ============================================================

function renderPeople() {
    const container = document.getElementById('people-list');
    container.innerHTML = state.sessionData.people.map((person, index) => `
        <div class="card card-editable" data-person-index="${index}">
            <button class="btn btn-secondary btn-xs card-edit-btn" onclick="togglePersonEdit(${index})">Edit</button>
            <div class="person-display" id="person-display-${index}">
                <h3>${escapeHtml(person.title)}</h3>
                <p>${escapeHtml(person.description)}</p>
            </div>
            <div class="card-edit-form hidden" id="person-edit-${index}">
                <div class="form-group">
                    <label>Title</label>
                    <input type="text" id="person-title-${index}" value="${escapeHtml(person.title)}">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="person-desc-${index}">${escapeHtml(person.description)}</textarea>
                </div>
                <div class="card-actions">
                    <button class="btn btn-success btn-xs" onclick="savePersonEdit(${index})">Save</button>
                    <button class="btn btn-secondary btn-xs" onclick="cancelPersonEdit(${index})">Cancel</button>
                </div>
            </div>
        </div>
    `).join('');

    // Update expert select in meetings
    updateExpertSelect();
}

function togglePersonEdit(index) {
    const display = document.getElementById(`person-display-${index}`);
    const edit = document.getElementById(`person-edit-${index}`);
    const editBtn = display.parentElement.querySelector('.card-edit-btn');

    display.classList.add('hidden');
    edit.classList.remove('hidden');
    editBtn.classList.add('hidden');
}

function cancelPersonEdit(index) {
    const display = document.getElementById(`person-display-${index}`);
    const edit = document.getElementById(`person-edit-${index}`);
    const editBtn = display.parentElement.querySelector('.card-edit-btn');

    // Reset values
    document.getElementById(`person-title-${index}`).value = state.sessionData.people[index].title;
    document.getElementById(`person-desc-${index}`).value = state.sessionData.people[index].description;

    display.classList.remove('hidden');
    edit.classList.add('hidden');
    editBtn.classList.remove('hidden');
}

async function savePersonEdit(index) {
    const title = document.getElementById(`person-title-${index}`).value;
    const description = document.getElementById(`person-desc-${index}`).value;

    state.sessionData.people[index].title = title;
    state.sessionData.people[index].description = description;

    await saveSessionData();
    renderPeople();
}

async function generatePeople() {
    if (!state.sessionData.summary) {
        alert('Please generate a task summary first.');
        return;
    }

    try {
        showLoading('Identifying team members...');
        const result = await apiCall('/api/ai/generate-people', 'POST', {
            summary: state.sessionData.summary
        });

        if (result.people) {
            state.sessionData.people = result.people;
            renderPeople();
            await saveSessionData();
        } else {
            alert('Failed to generate team members: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('People error:', error);
        alert('Failed to generate team members');
    } finally {
        hideLoading();
    }
}

// ============================================================
// RESEARCH STAGE
// ============================================================

function renderResearch() {
    const container = document.getElementById('research-list');
    container.innerHTML = state.sessionData.research_findings.map(finding => `
        <div class="card">
            <h3>${escapeHtml(finding.topic)}</h3>
            <p>${escapeHtml(finding.description)}</p>
            <div class="citation">${escapeHtml(finding.citation)}</div>
        </div>
    `).join('');

    // Update meeting select
    updateMeetingSelect();
}

async function generateResearch() {
    if (!state.sessionData.summary) {
        alert('Please generate a task summary first.');
        return;
    }

    try {
        showLoading('Researching findings...');
        const result = await apiCall('/api/ai/generate-research', 'POST', {
            summary: state.sessionData.summary
        });

        if (result.findings) {
            state.sessionData.research_findings = result.findings;

            // Initialize meetings based on research findings
            state.sessionData.meetings = result.findings.map(finding => ({
                id: finding.id,
                topic: finding.topic,
                description: finding.description,
                messages: [{
                    id: crypto.randomUUID(),
                    participant_name: 'System',
                    content: `Meeting Topic: ${finding.topic}\n\n${finding.description}`,
                    timestamp: new Date().toISOString()
                }],
                summary_report: ''
            }));

            renderResearch();
            await saveSessionData();
        } else {
            alert('Failed to generate research: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Research error:', error);
        alert('Failed to generate research findings');
    } finally {
        hideLoading();
    }
}

// ============================================================
// MEETINGS STAGE
// ============================================================

function updateMeetingSelect() {
    const select = document.getElementById('meeting-select');
    select.innerHTML = state.sessionData.meetings.map((meeting, i) =>
        `<option value="${i}">${meeting.topic}</option>`
    ).join('');

    if (state.sessionData.meetings.length > 0) {
        state.currentMeetingIndex = 0;
        renderCurrentMeeting();
    }
}

function updateExpertSelect() {
    const select = document.getElementById('expert-select');
    select.innerHTML = '<option value="">Next in rotation</option>' +
        state.sessionData.people.map((person, i) =>
            `<option value="${i}">${person.title}</option>`
        ).join('');
}

function renderCurrentMeeting() {
    const meeting = state.sessionData.meetings[state.currentMeetingIndex];
    if (!meeting) return;

    const container = document.getElementById('meeting-messages');
    container.innerHTML = meeting.messages.map(msg => {
        let className = 'meeting-message';
        if (msg.participant_name === 'You') className += ' user-message';
        if (msg.participant_name === 'Summary') className += ' summary-message';

        return `
            <div class="${className}">
                <div class="participant-name">${escapeHtml(msg.participant_name)}</div>
                <div>${escapeHtml(msg.content)}</div>
            </div>
        `;
    }).join('');
    container.scrollTop = container.scrollHeight;
}

function renderMeetings() {
    updateMeetingSelect();
    updateExpertSelect();
    if (state.sessionData.meetings.length > 0) {
        renderCurrentMeeting();
    }
}

async function getNextMeetingResponse(userQuestion = null, specificExpertIndex = null) {
    const meeting = state.sessionData.meetings[state.currentMeetingIndex];
    if (!meeting) return;

    if (state.sessionData.people.length === 0) {
        alert('Please generate team members first.');
        return;
    }

    // Determine which expert speaks
    let expertIndex;
    if (specificExpertIndex !== null && specificExpertIndex >= 0) {
        expertIndex = specificExpertIndex;
    } else {
        expertIndex = state.meetingTurnIndex % state.sessionData.people.length;
        state.meetingTurnIndex++;
    }

    const person = state.sessionData.people[expertIndex];

    try {
        showLoading(`${person.title} is thinking...`);

        const result = await apiCall('/api/ai/meeting-response', 'POST', {
            person: person,
            meeting: meeting,
            summary: state.sessionData.summary,
            user_question: userQuestion
        });

        meeting.messages.push({
            id: crypto.randomUUID(),
            participant_id: person.id,
            participant_name: person.title,
            content: result.response,
            timestamp: new Date().toISOString()
        });

        renderCurrentMeeting();
        await saveSessionData();
    } catch (error) {
        console.error('Meeting response error:', error);
        alert('Failed to get meeting response');
    } finally {
        hideLoading();
    }
}

async function askExpertQuestion() {
    const input = document.getElementById('meeting-user-input');
    const question = input.value.trim();
    if (!question) return;

    const meeting = state.sessionData.meetings[state.currentMeetingIndex];
    if (!meeting) return;

    // Add user question to meeting
    meeting.messages.push({
        id: crypto.randomUUID(),
        participant_name: 'You',
        content: question,
        timestamp: new Date().toISOString()
    });
    renderCurrentMeeting();
    input.value = '';

    // Get selected expert
    const expertSelect = document.getElementById('expert-select');
    const specificExpertIndex = expertSelect.value ? parseInt(expertSelect.value) : null;

    await getNextMeetingResponse(question, specificExpertIndex);
}

async function autoRunMeeting(count = 5) {
    for (let i = 0; i < count; i++) {
        await getNextMeetingResponse();
        await new Promise(resolve => setTimeout(resolve, 500));
    }
}

async function endAndSummarizeMeeting() {
    const meeting = state.sessionData.meetings[state.currentMeetingIndex];
    if (!meeting) return;

    if (meeting.messages.length <= 1) {
        alert('The meeting needs more discussion before summarizing.');
        return;
    }

    try {
        showLoading('Generating meeting summary...');

        const result = await apiCall('/api/ai/meeting-summary', 'POST', {
            meeting: meeting
        });

        meeting.summary_report = result.summary;

        meeting.messages.push({
            id: crypto.randomUUID(),
            participant_name: 'Summary',
            content: result.summary,
            timestamp: new Date().toISOString()
        });

        renderCurrentMeeting();
        await saveSessionData();
    } catch (error) {
        console.error('Meeting summary error:', error);
        alert('Failed to generate meeting summary');
    } finally {
        hideLoading();
    }
}

function resetCurrentMeeting() {
    const meeting = state.sessionData.meetings[state.currentMeetingIndex];
    if (!meeting) return;

    if (!confirm('Are you sure you want to reset this meeting? All discussion will be lost.')) return;

    meeting.messages = [{
        id: crypto.randomUUID(),
        participant_name: 'System',
        content: `Meeting Topic: ${meeting.topic}\n\n${meeting.description}`,
        timestamp: new Date().toISOString()
    }];
    meeting.summary_report = '';
    state.meetingTurnIndex = 0;

    renderCurrentMeeting();
    saveSessionData();
}

// ============================================================
// REPORT STAGE
// ============================================================

function renderReport() {
    const container = document.getElementById('final-report');
    if (state.sessionData.final_report) {
        container.innerHTML = formatMarkdown(state.sessionData.final_report);
    } else {
        container.innerHTML = '<p class="placeholder">Complete meetings and click "Generate Final Report" to create your report.</p>';
    }

    // Render report chat
    const chatContainer = document.getElementById('report-chat-messages');
    chatContainer.innerHTML = state.sessionData.report_chat_messages.map(msg => `
        <div class="chat-message ${msg.role}">
            ${escapeHtml(msg.content)}
        </div>
    `).join('');
}

async function generateFinalReport() {
    const meetingsWithSummaries = state.sessionData.meetings.filter(m => m.summary_report);

    if (meetingsWithSummaries.length === 0) {
        alert('Please complete at least one meeting with a summary before generating the final report.');
        return;
    }

    try {
        showLoading('Generating final report...');

        const result = await apiCall('/api/ai/generate-report', 'POST', {
            summary: state.sessionData.summary,
            meetings: state.sessionData.meetings
        });

        state.sessionData.final_report = result.report;
        renderReport();
        await saveSessionData();
    } catch (error) {
        console.error('Report error:', error);
        alert('Failed to generate final report');
    } finally {
        hideLoading();
    }
}

async function sendReportChat() {
    const input = document.getElementById('report-chat-input');
    const message = input.value.trim();
    if (!message) return;

    if (!state.sessionData.final_report) {
        alert('Please generate a final report first.');
        return;
    }

    state.sessionData.report_chat_messages.push({ role: 'user', content: message });
    renderReport();
    input.value = '';

    try {
        showLoading('AI is thinking...');

        const chatMessages = [
            { role: 'user', content: `Here is a report:\n\n${state.sessionData.final_report}` },
            { role: 'assistant', content: 'I have read the report. How can I help you?' },
            ...state.sessionData.report_chat_messages
        ];

        const result = await apiCall('/api/ai/chat', 'POST', {
            messages: chatMessages,
            system_prompt: 'You are a helpful assistant that answers questions about the provided report. Be concise and accurate.'
        });

        state.sessionData.report_chat_messages.push({ role: 'assistant', content: result.response });
        renderReport();
        await saveSessionData();
    } catch (error) {
        console.error('Report chat error:', error);
        state.sessionData.report_chat_messages.push({
            role: 'assistant',
            content: 'Error: Failed to get response.'
        });
        renderReport();
    } finally {
        hideLoading();
    }
}

// ============================================================
// EXPORT
// ============================================================

function exportMarkdown() {
    if (!state.sessionData.final_report) {
        alert('Please generate a final report first.');
        return;
    }

    const blob = new Blob([state.sessionData.final_report], { type: 'text/markdown' });
    downloadBlob(blob, 'virtual-lab-report.md');
}

function exportJSON() {
    const data = {
        summary: state.sessionData.summary,
        people: state.sessionData.people,
        research_findings: state.sessionData.research_findings,
        meetings: state.sessionData.meetings,
        final_report: state.sessionData.final_report,
        exported_at: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    downloadBlob(blob, 'virtual-lab-session.json');
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================================
// SETTINGS
// ============================================================

async function checkApiKeyStatus() {
    try {
        const result = await apiCall('/api/settings/api-key');
        const statusEl = document.getElementById('api-key-status');
        if (result.configured) {
            statusEl.className = 'status-message success-message';
            statusEl.textContent = 'API key is configured';
        } else {
            statusEl.className = 'status-message error-message';
            statusEl.textContent = 'API key is not configured';
        }
    } catch (error) {
        console.error('API key check error:', error);
    }
}

async function saveApiKey() {
    const input = document.getElementById('api-key-input');
    const apiKey = input.value.trim();

    if (!apiKey) {
        alert('Please enter an API key');
        return;
    }

    try {
        showLoading('Saving API key...');
        await apiCall('/api/settings/api-key', 'POST', { api_key: apiKey });
        input.value = '';
        await checkApiKeyStatus();
        alert('API key saved successfully');
    } catch (error) {
        console.error('Save API key error:', error);
        alert('Failed to save API key');
    } finally {
        hideLoading();
    }
}

// ============================================================
// PROMPTS
// ============================================================

async function loadPrompts() {
    try {
        const prompts = await apiCall('/api/prompts');
        const container = document.getElementById('prompts-list');

        container.innerHTML = Object.entries(prompts).map(([id, content]) => `
            <div class="prompt-item">
                <label for="prompt-${id}">${id.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</label>
                <textarea id="prompt-${id}" data-prompt-id="${id}">${escapeHtml(content)}</textarea>
            </div>
        `).join('');
    } catch (error) {
        console.error('Load prompts error:', error);
    }
}

async function savePrompts() {
    const prompts = {};
    document.querySelectorAll('#prompts-list textarea').forEach(textarea => {
        prompts[textarea.dataset.promptId] = textarea.value;
    });

    try {
        showLoading('Saving prompts...');
        await apiCall('/api/prompts', 'POST', prompts);
        alert('Prompts saved successfully');
    } catch (error) {
        console.error('Save prompts error:', error);
        alert('Failed to save prompts');
    } finally {
        hideLoading();
    }
}

async function resetPrompts() {
    if (!confirm('Are you sure you want to reset all prompts to defaults?')) return;

    try {
        showLoading('Resetting prompts...');
        await apiCall('/api/prompts/reset', 'POST');
        await loadPrompts();
        alert('Prompts reset to defaults');
    } catch (error) {
        console.error('Reset prompts error:', error);
        alert('Failed to reset prompts');
    } finally {
        hideLoading();
    }
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMarkdown(text) {
    // Simple markdown formatting
    return text
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/^/gim, '<p>')
        .replace(/$/gim, '</p>')
        .replace(/<p><\/p>/g, '')
        .replace(/<p>(<h[1-3]>)/g, '$1')
        .replace(/(<\/h[1-3]>)<\/p>/g, '$1');
}

// ============================================================
// EVENT LISTENERS
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // Check authentication on load
    checkAuth();

    // Login form
    document.getElementById('login-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        login(username, password);
    });

    // Logout button
    document.getElementById('logout-btn').addEventListener('click', logout);

    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const stage = item.dataset.stage;
            if (stage) {
                switchStage(stage);

                // Load prompts when switching to prompts stage
                if (stage === 'prompts') {
                    loadPrompts();
                }
                // Check API key status when switching to settings
                if (stage === 'settings') {
                    checkApiKeyStatus();
                }
            }
        });
    });

    // Session management
    document.getElementById('session-select').addEventListener('change', (e) => {
        selectSession(e.target.value);
    });
    document.getElementById('new-session-btn').addEventListener('click', createNewSession);
    document.getElementById('delete-session-btn').addEventListener('click', deleteCurrentSession);

    // Discovery stage
    document.getElementById('discovery-send-btn').addEventListener('click', sendDiscoveryMessage);
    document.getElementById('discovery-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendDiscoveryMessage();
        }
    });
    document.getElementById('generate-summary-btn').addEventListener('click', generateSummary);

    // Task stage - edit functionality and navigation
    document.getElementById('edit-summary-btn').addEventListener('click', () => toggleSummaryEdit(true));
    document.getElementById('save-summary-btn').addEventListener('click', saveSummaryEdit);
    document.getElementById('cancel-summary-btn').addEventListener('click', () => toggleSummaryEdit(false));
    document.getElementById('task-next-btn').addEventListener('click', () => switchStage('people'));

    // People stage
    document.getElementById('generate-people-btn').addEventListener('click', generatePeople);
    document.getElementById('people-next-btn').addEventListener('click', () => switchStage('research'));

    // Research stage
    document.getElementById('generate-research-btn').addEventListener('click', generateResearch);
    document.getElementById('research-next-btn').addEventListener('click', () => switchStage('meetings'));

    // Meetings stage
    document.getElementById('meeting-select').addEventListener('change', (e) => {
        state.currentMeetingIndex = parseInt(e.target.value);
        state.meetingTurnIndex = 0;
        renderCurrentMeeting();
    });
    document.getElementById('meeting-next-btn').addEventListener('click', () => {
        const userInput = document.getElementById('meeting-user-input').value.trim();
        const expertSelect = document.getElementById('expert-select');
        const specificExpertIndex = expertSelect.value ? parseInt(expertSelect.value) : null;

        if (userInput) {
            askExpertQuestion();
        } else {
            getNextMeetingResponse(null, specificExpertIndex);
        }
    });
    document.getElementById('meeting-auto-btn').addEventListener('click', () => autoRunMeeting(5));
    document.getElementById('meeting-end-btn').addEventListener('click', endAndSummarizeMeeting);
    document.getElementById('meeting-reset-btn').addEventListener('click', resetCurrentMeeting);
    document.getElementById('meeting-user-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            askExpertQuestion();
        }
    });

    // Report stage
    document.getElementById('generate-report-btn').addEventListener('click', generateFinalReport);
    document.getElementById('report-chat-send-btn').addEventListener('click', sendReportChat);
    document.getElementById('report-chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendReportChat();
        }
    });

    // Export
    document.getElementById('export-markdown-btn').addEventListener('click', exportMarkdown);
    document.getElementById('export-json-btn').addEventListener('click', exportJSON);

    // Settings
    document.getElementById('save-api-key-btn').addEventListener('click', saveApiKey);

    // Prompts
    document.getElementById('save-prompts-btn').addEventListener('click', savePrompts);
    document.getElementById('reset-prompts-btn').addEventListener('click', resetPrompts);
});
