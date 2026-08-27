import streamlit as st
from Chatbot_Backend import (
    chatbot,
    generate_title,
    ingest_pdf,
    list_all_threads,
    save_thread_title,
    thread_document_metadata,
)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones


st.markdown("""
<style>
/* ========== GLOBAL — deep navy canvas ========== */
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #0F1B2D;
}

/* ========== Sidebar — slightly lighter navy ========== */
[data-testid="stSidebar"] {
    background-color: #162236;
    border-right: 1px solid #1E2E48;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: #CFD8E8 !important;
}

/* ========== Buttons — coral/orange accent ========== */
.stButton > button {
    background: linear-gradient(135deg, #E8734A 0%, #D4603B 100%);
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 0.5rem 1.2rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(232, 115, 74, 0.25);
}
.stButton > button:hover {
    background: linear-gradient(135deg, #F0845E 0%, #E8734A 100%);
    box-shadow: 0 4px 16px rgba(232, 115, 74, 0.4);
    transform: translateY(-1px);
    color: #FFFFFF;
}
.stButton > button:active {
    transform: translateY(0px);
}

/* ========== Input boxes — dark slate with coral border on focus ========== */
.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div,
[data-testid="stChatInput"] {
    background-color: #1A2942 !important;
    border: 1px solid #2A3F5F !important;
    border-radius: 10px;
}
.stTextInput input:focus,
[data-testid="stChatInput"]:focus-within {
    border-color: #E8734A !important;
    box-shadow: 0 0 0 2px rgba(232, 115, 74, 0.2) !important;
}
.stTextInput input,
.stSelectbox div[data-baseweb="select"] span,
[data-testid="stChatInput"] textarea {
    color: #E0E6F0 !important;
}
.stTextInput input::placeholder,
[data-testid="stChatInput"] textarea::placeholder {
    color: #6B7D9A !important;
}
[data-testid="stChatInput"] button svg {
    fill: #E8734A !important;
}

/* Dropdown popup */
ul[role="listbox"] {
    background-color: #1A2942 !important;
    border: 1px solid #2A3F5F !important;
}
ul[role="listbox"] li {
    color: #E0E6F0 !important;
}
ul[role="listbox"] li:hover {
    background-color: #243555 !important;
}

/* ========== Chat bubbles ========== */
[data-testid="stChatMessage"] {
    background-color: #182A42;
    border: 1px solid #243555;
    border-radius: 14px;
    padding: 0.6rem 0.85rem;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] code {
    color: #DAE0EC !important;
}

/* ========== Main conversation area — framed with coral ========== */
[data-testid="stMainBlockContainer"] {
    background-color: #121E32;
    border: 2px solid #E8734A;
    border-radius: 18px;
    box-shadow: 0 4px 24px rgba(232, 115, 74, 0.08);
    padding: 1.5rem 1.75rem 2rem !important;
    max-width: 900px !important;
    width: 92% !important;
    margin: 1.5rem auto !important;
}

[data-testid="stBottom"] .block-container {
    max-width: 900px !important;
    margin: 0 auto !important;
}
[data-testid="stBottom"] {
    background-color: transparent !important;
}

/* ========== Responsiveness ========== */
@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"] {
        width: 96% !important;
        padding: 1rem 1rem 1.5rem !important;
        border-radius: 14px;
        margin: 0.75rem auto !important;
    }
    [data-testid="stBottom"] .block-container {
        max-width: 96% !important;
    }
}

/* ========== File uploader — styled ========== */
[data-testid="stFileUploader"] {
    background-color: #1A2942;
    border: 2px dashed #E8734A;
    border-radius: 12px;
    padding: 0.75rem;
    transition: all 0.2s ease;
}
[data-testid="stFileUploader"]:hover {
    border-color: #F0845E;
    background-color: #1E3050;
}
[data-testid="stFileUploader"] label {
    color: #CFD8E8 !important;
}
[data-testid="stFileUploader"] small {
    color: #6B7D9A !important;
}
[data-testid="stFileUploader"] button {
    background: linear-gradient(135deg, #E8734A, #D4603B) !important;
    color: #FFF !important;
    border: none !important;
    border-radius: 8px !important;
}

/* ========== Alert boxes in sidebar ========== */
[data-testid="stSidebar"] [data-testid="stAlertContainer"] {
    background-color: #1A2942;
    border-radius: 10px;
    border: 1px solid #2A3F5F;
}

/* Success alert — coral tint */
[data-testid="stSidebar"] .stSuccess {
    background-color: rgba(232, 115, 74, 0.1) !important;
    border: 1px solid rgba(232, 115, 74, 0.3) !important;
    border-radius: 10px;
    color: #F0C4B0 !important;
}

/* Info alert */
[data-testid="stSidebar"] .stInfo {
    background-color: rgba(107, 125, 154, 0.15) !important;
    border: 1px solid rgba(107, 125, 154, 0.3) !important;
    border-radius: 10px;
}

/* ========== Selectbox — force light text ========== */
.stSelectbox div[data-baseweb="select"],
.stSelectbox div[data-baseweb="select"] *,
.stSelectbox div[data-baseweb="select"] input {
    color: #E0E6F0 !important;
    -webkit-text-fill-color: #E0E6F0 !important;
}

/* ========== Dividers & captions ========== */
hr {
    border-color: #243555 !important;
}
.stCaption, [data-testid="stCaptionContainer"] {
    color: #6B7D9A !important;
}

/* ========== Popover ========== */
[data-testid="stPopover"] {
    background-color: #1A2942 !important;
    border: 1px solid #2A3F5F !important;
    border-radius: 12px !important;
}

/* ========== Status widget ========== */
[data-testid="stStatusWidget"] {
    background-color: #1A2942 !important;
    border: 1px solid #E8734A !important;
    border-radius: 10px !important;
}

/* ========== Scrollbar ========== */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-track {
    background: #0F1B2D;
}
::-webkit-scrollbar-thumb {
    background: #2A3F5F;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: #E8734A;
}
</style>
""", unsafe_allow_html=True)

# **************************************** utility functions *************************

def generate_thread_id():
    return uuid.uuid4()

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    return state.values.get('messages', [])

@st.fragment(run_every="1s")
def render_live_time():
    tz_name = st.session_state.get('user_timezone', 'Asia/Kolkata')
    now = datetime.now(ZoneInfo(tz_name))
    st.markdown(f"**Time zone**  \n{tz_name}")
    st.markdown(f"**Date**  \n{now.strftime('%a, %d %b %Y')}")
    st.markdown(f"**Time**  \n{now.strftime('%I:%M:%S %p')}")

# **************************************** Session Setup ******************************
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    persisted = list_all_threads()
    st.session_state['chat_threads'] = [t['thread_id'] for t in persisted]
    st.session_state['chat_titles'] = {t['thread_id']: t['title'] for t in persisted}

if 'chat_titles' not in st.session_state:
    st.session_state['chat_titles'] = {}

if 'user_location' not in st.session_state:
    st.session_state['user_location'] = ''
if 'user_timezone' not in st.session_state:
    st.session_state['user_timezone'] = 'Asia/Kolkata'
if 'settings_expanded' not in st.session_state:
    st.session_state['settings_expanded'] = True

if 'ingested_docs' not in st.session_state:
    st.session_state['ingested_docs'] = {}

add_thread(st.session_state['thread_id'])

if 'editing_thread' not in st.session_state:
    st.session_state['editing_thread'] = None

thread_key = str(st.session_state['thread_id'])
thread_docs = st.session_state['ingested_docs'].setdefault(thread_key, {})

# **************************************** Sidebar UI *********************************
st.sidebar.title('SAM : Ai Chatbot')

if st.sidebar.button('New Chat', icon=':material/add_comment:', use_container_width=True):
    reset_chat()
    st.rerun()

st.sidebar.markdown("---")

# ---- PDF Upload ----
st.sidebar.subheader(':material/upload_file: Document Upload')

if thread_docs:
    latest_doc = list(thread_docs.values())[-1]
    st.sidebar.success(
        f":material/check_circle: **{latest_doc.get('filename')}** indexed "
        f"({latest_doc.get('chunks')} chunks, {latest_doc.get('documents')} pages)"
    )
else:
    st.sidebar.info(":material/info: No PDF indexed for this chat.")

uploaded_pdf = st.sidebar.file_uploader(
    "Upload a PDF for RAG",
    type=["pdf"],
    label_visibility="collapsed",
)
if uploaded_pdf:
    if uploaded_pdf.name in thread_docs:
        st.sidebar.info(f"`{uploaded_pdf.name}` already processed for this chat.")
    else:
        with st.sidebar.status("Indexing PDF...", expanded=True) as status_box:
            try:
                summary = ingest_pdf(
                    uploaded_pdf.getvalue(),
                    thread_id=thread_key,
                    filename=uploaded_pdf.name,
                )
                thread_docs[uploaded_pdf.name] = summary
                status_box.update(label="PDF indexed successfully", state="complete", expanded=False)
            except Exception as e:
                status_box.update(label="PDF indexing failed", state="error", expanded=False)
                st.sidebar.error(f":material/error: {e}")

st.sidebar.markdown("---")

# ---- Conversations list ----
st.sidebar.subheader(':material/forum: My Conversations')

for thread_id in st.session_state['chat_threads'][::-1]:
    title = st.session_state['chat_titles'].get(thread_id, 'New Chat')

    if st.session_state['editing_thread'] == thread_id:
        new_title = st.sidebar.text_input(
            'Rename chat',
            value=title,
            key=f'edit_input_{thread_id}',
            label_visibility='collapsed',
        )
        save_col, cancel_col = st.sidebar.columns(2)
        if save_col.button(':material/save: Save', key=f'save_{thread_id}'):
            final_title = new_title.strip() or title
            st.session_state['chat_titles'][thread_id] = final_title
            save_thread_title(str(thread_id), final_title)
            st.session_state['editing_thread'] = None
            st.rerun()
        if cancel_col.button(':material/close: Cancel', key=f'cancel_{thread_id}'):
            st.session_state['editing_thread'] = None
            st.rerun()

    else:
        open_col, edit_col = st.sidebar.columns([4, 1.2])
        if open_col.button(f':material/chat_bubble_outline: {title}', key=str(thread_id), use_container_width=True):
            st.session_state['thread_id'] = thread_id
            messages = load_conversation(thread_id)
            temp_messages = []
            for msg in messages:
                role = 'user' if isinstance(msg, HumanMessage) else 'assistant'
                temp_messages.append({'role': role, 'content': msg.content})
            st.session_state['message_history'] = temp_messages
            st.session_state['ingested_docs'].setdefault(str(thread_id), {})
            st.rerun()
        if edit_col.button(':material/edit:', key=f'edit_{thread_id}', help='Rename'):
            st.session_state['editing_thread'] = thread_id
            st.rerun()

st.sidebar.markdown("---")

# ---- Location & Time Zone (collapsible) ----
tz_options = sorted(available_timezones())

if st.session_state['settings_expanded']:
    st.sidebar.subheader(':material/settings: Location & Time Zone')

    loc = st.sidebar.text_input(
        'Your location (city, country)',
        value=st.session_state['user_location'],
        placeholder='e.g., Noida, India',
        key='loc_input',
    )
    tz = st.sidebar.selectbox(
        'Your time zone',
        options=tz_options,
        index=tz_options.index(st.session_state['user_timezone']),
        key='tz_input',
    )

    if st.sidebar.button(':material/save: Save Settings', key='save_settings', use_container_width=True):
        st.session_state['user_location'] = loc.strip()
        st.session_state['user_timezone'] = tz
        st.session_state['settings_expanded'] = False
        st.rerun()
else:
    if st.sidebar.button(':material/edit_location:', key='expand_settings', help='Set location & time zone'):
        st.session_state['settings_expanded'] = True
        st.rerun()


# **************************************** Main UI ************************************
_, loc_col, time_col = st.columns([8, 1, 1])

with loc_col:
    with st.popover("", icon=":material/location_on:"):
        loc = st.session_state.get('user_location', '').strip() or '—'
        st.markdown(f"**Location**  \n{loc}")

with time_col:
    with st.popover("", icon=":material/schedule:"):
        render_live_time()


if not st.session_state['message_history']:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1A2942 0%, #162236 100%);
        border: 1px solid #2A3F5F;
        border-radius: 16px;
        padding: 1.8rem 2rem;
        margin: 1.5rem auto;
        max-width: 680px;
    ">
        <div style="text-align: center; margin-bottom: 1.2rem;">
            <span style="font-size: 1.6rem; font-weight: 700; color: #E8734A;">Hey, I'm SAM</span>
            <p style="color: #8A9BB8; font-size: 0.92rem; margin: 0.3rem 0 0;">Your multi-utility AI assistant. Here's what I can do:</p>
        </div>
        <div style="display: flex; flex-direction: column; gap: 0.7rem;">
            <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 0.9rem; background: #0F1B2D; border-radius: 10px;">
                <span style="font-size: 1.3rem;">📄</span>
                <div>
                    <span style="color: #E0E6F0; font-weight: 600; font-size: 0.95rem;">PDF Q&A</span>
                    <p style="color: #6B7D9A; font-size: 0.82rem; margin: 0.1rem 0 0;">Upload a PDF and ask questions about it</p>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 0.9rem; background: #0F1B2D; border-radius: 10px;">
                <span style="font-size: 1.3rem;">🔍</span>
                <div>
                    <span style="color: #E0E6F0; font-weight: 600; font-size: 0.95rem;">Web Search</span>
                    <p style="color: #6B7D9A; font-size: 0.82rem; margin: 0.1rem 0 0;">Look up real-time info, news & facts</p>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 0.9rem; background: #0F1B2D; border-radius: 10px;">
                <span style="font-size: 1.3rem;">💻</span>
                <div>
                    <span style="color: #E0E6F0; font-weight: 600; font-size: 0.95rem;">Code Interpreter</span>
                    <p style="color: #6B7D9A; font-size: 0.82rem; margin: 0.1rem 0 0;">Write, debug & explain Python code</p>
                </div>
            </div>
        </div>
        <p style="text-align: center; color: #4A5E7A; font-size: 0.8rem; margin: 1rem 0 0;">Type a message below to get started</p>
    </div>
    """, unsafe_allow_html=True)

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

user_input = st.chat_input('Ask about your document, search the web, or run code')

if user_input:
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    tz_name = st.session_state.get('user_timezone', 'Asia/Kolkata')
    CONFIG = {
        'configurable': {
            'thread_id': thread_key,
            'user_location': st.session_state.get('user_location', ''),
            'user_timezone': tz_name,
            'local_time': datetime.now(ZoneInfo(tz_name)).strftime('%A, %d %B %Y, %I:%M %p'),
        }
    }

    with st.chat_message("assistant"):
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f":material/build: Using {tool_name}...", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f":material/build: Using {tool_name}...",
                            state="running",
                            expanded=True,
                        )

                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        if status_holder["box"] is not None:
            status_holder["box"].update(
                label=":material/check_circle: Tool finished", state="complete", expanded=False
            )

    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})

    doc_meta = thread_document_metadata(thread_key)
    if doc_meta:
        st.caption(
            f":material/description: Document indexed: {doc_meta.get('filename')} "
            f"(chunks: {doc_meta.get('chunks')}, pages: {doc_meta.get('documents')})"
        )

    current_thread = st.session_state['thread_id']
    if current_thread not in st.session_state['chat_titles']:
        title = generate_title(user_input, ai_message)
        st.session_state['chat_titles'][current_thread] = title
        save_thread_title(str(current_thread), title)
        st.rerun()
