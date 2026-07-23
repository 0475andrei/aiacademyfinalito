import os
import uuid
import time
import glob
import gradio as gr
import logging
from agent import Agent
from llm_client import LLMClient
from conversation_context import ConversationContext
from config import INPUT_TOKEN_PRICE_PER_MILLION, OUTPUT_TOKEN_PRICE_PER_MILLION
from tools.tools import tools

# --- 1. GLOBAL LOGGER & DIRECTORY SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

SAVE_DIR = "saved_sessions"
os.makedirs(SAVE_DIR, exist_ok=True)
logger.info("Application initialized and ready.")

# --- 2. MULTI-SESSION MANAGEMENT & PERSISTENCE ---
active_sessions = {}

def create_new_session():
    """Creates a new unique isolated chat session and saves it locally."""
    session_id = str(uuid.uuid4())[:8]
    context = ConversationContext()
    llm_client = LLMClient()
    agent = Agent(llm_client, context, tools=tools)
    
    active_sessions[session_id] = {
        "title": f"New Chat",
        "agent": agent
    }
    
    # Auto-save initial empty state
    filepath = os.path.join(SAVE_DIR, f"session_{session_id}.json")
    context.export_to_json(filepath)
    
    logger.info(f"Created new isolated session: {session_id}")
    return session_id

def load_saved_sessions():
    """Scans the saved_sessions folder and loads all past conversations on startup."""
    json_files = glob.glob(os.path.join(SAVE_DIR, "*.json"))
    
    for filepath in json_files:
        filename = os.path.basename(filepath)
        session_id = filename.replace("session_", "").replace(".json", "")
        
        context = ConversationContext()
        success = context.import_from_json(filepath)
        
        if success:
            llm_client = LLMClient()
            agent = Agent(llm_client, context, tools=tools)
            
            
            user_msgs = [m for m in context.get_history() if m.get("role") == "user"]
            if user_msgs:
                first_msg = user_msgs[0].get("content", "")
                clean_title = (first_msg[:27] + "...") if len(first_msg) > 30 else first_msg
            else:
                clean_title = "New Chat"
                
            active_sessions[session_id] = {
                "title": clean_title,
                "agent": agent
            }
            logger.info(f"Loaded existing session: {session_id}")

# Initialize by loading existing files, or create a new one if the folder is empty
load_saved_sessions()
if not active_sessions:
    default_session_id = create_new_session()
else:
    # Set the default session to the most recently created/loaded one
    default_session_id = list(active_sessions.keys())[-1]
    
current_active_session = default_session_id

def get_session_choices():
    """Returns formatted session choices for the UI dropdown."""
    return [(data["title"], sid) for sid, data in active_sessions.items()]

def get_current_agent(request: gr.Request = None):
    """Retrieves the active session agent based on UI selection."""
    global current_active_session
    sid = current_active_session
    if sid not in active_sessions:
        sid = create_new_session()
        current_active_session = sid
    return active_sessions[sid]["agent"], sid

# --- 3. EXPORT / IMPORT LOGIC & FORMATTING ---
def _rebuild_gradio_history(history_msgs):
    """Converts internal context history into Gradio 5's expected dictionary format."""
    chat_history = []
    for msg in history_msgs:
        role = msg.get("role")
        content = msg.get("content")
        if content is None:
            content = ""
            
        if role in ["user", "assistant"]:
            chat_history.append({"role": role, "content": content})
    return chat_history

def export_chat(request: gr.Request):
    agent, session_id = get_current_agent(request)
    filepath = os.path.join(SAVE_DIR, f"session_{session_id}.json")
    agent.context.export_to_json(filepath)
    return gr.DownloadButton(value=filepath, interactive=True)

def import_chat(file, request: gr.Request = None):
    if file is None:
        return "Upload failed.", []
    
    agent, session_id = get_current_agent(request)
    filepath = file if isinstance(file, str) else file.name
    success = agent.context.import_from_json(filepath)
    
    if success:
        
        local_save_path = os.path.join(SAVE_DIR, f"session_{session_id}.json")
        agent.context.export_to_json(local_save_path)
        
        chat_history = _rebuild_gradio_history(agent.context.get_history())
        return "✅ Session imported successfully! You can resume your chat.", chat_history
    
    return "❌ Failed to import session.", []

# --- 4. SESSION SELECTOR & CREATOR ACTIONS ---
def switch_session(selected_sid):
    global current_active_session
    if selected_sid in active_sessions:
        current_active_session = selected_sid
        context = active_sessions[selected_sid]["agent"].context
        return _rebuild_gradio_history(context.get_history())
    return []

def handle_new_chat_btn():
    global current_active_session
    new_sid = create_new_session()
    current_active_session = new_sid
    return [], gr.update(choices=get_session_choices(), value=new_sid)

# --- 5. CHAT FUNCTION ---
def chat_function(message, history, request: gr.Request = None):
    global current_active_session
    if not message.strip():
        yield history, gr.update()
        return
        
    logger.info(f"User Question: [Session: {current_active_session}] {message}")
    history.append({"role": "user", "content": message})
    yield history, gr.update()
    
    try:
        start_time = time.time()
        agent = active_sessions[current_active_session]["agent"]
        context = agent.context
        
        user_msgs_count = sum(1 for m in context.get_history() if m.get("role") == "user")
        if user_msgs_count == 0:
            clean_title = (message[:27] + "...") if len(message) > 30 else message
            active_sessions[current_active_session]["title"] = clean_title
        
        history.append({"role": "assistant", "content": "🛠️ *System: Checking tools for your request...*"})
        yield history, gr.update()
        
        response_content, tool_used = agent.process_message(message)
        
        logger.info(f"Model Response: {response_content}")
        if tool_used:
            logger.info(f"Tool Call Executed: {tool_used}")
            
        inputs = context.input_tokens
        outputs = context.output_tokens
        cost = (inputs / 1000000 * INPUT_TOKEN_PRICE_PER_MILLION) + (outputs / 1000000 * OUTPUT_TOKEN_PRICE_PER_MILLION)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        final_output = ""
        if tool_used:
            final_output += f"🛠️ *System: Tool '{tool_used}' was used to process your request.*\n\n"
        
        final_output += response_content
        final_output += (f"\n\n---\n"
                        f"⏱️ **Time**: {elapsed_time:.2f}s | "
                        f"📊 **Usage**: {inputs} in / {outputs} out tokens | "
                        f"💰 **Est. Cost**: ${cost:.6f}")
        
        # Update the placeholder message with the final formatted response
        history[-1]["content"] = final_output
        
        # --- AUTO-SAVE AFTER GENERATION ---
        save_path = os.path.join(SAVE_DIR, f"session_{current_active_session}.json")
        context.export_to_json(save_path)
        
        yield history, gr.update(choices=get_session_choices(), value=current_active_session)
        logger.info(f"Cost for this conversation: ${cost:.6f} (Inputs: {inputs} tokens, Outputs: {outputs} tokens)")
        
    except Exception as e:
        logger.error(f"Gradio Chat Fatal Error: {e}", exc_info=True)
        history[-1]["content"] = "⚠️ Sorry, I encountered a critical error. Please refresh the chat."
        yield history, gr.update()

# --- 6. GRADIO UI LAYOUT ---
with gr.Blocks(title="CYB(ri)AN") as demo:
    gr.Markdown("# 🛡️ CYB(ri)AN - AI Cybersecurity Analyst")
    gr.Markdown("Ask CYBriAN about company security policies, incident protocols, or hardware procedures.")
    
    with gr.Row():
        session_dropdown = gr.Dropdown(
            choices=get_session_choices(),
            value=default_session_id,
            label="Active Conversations",
            interactive=True
        )
        new_chat_btn = gr.Button("➕ New Chat Session")

    with gr.Row():
        export_btn = gr.DownloadButton("💾 Export Conversation")
        import_file = gr.File(label="📂 Import Conversation (JSON)", file_types=[".json"], type="filepath")
        import_status = gr.Textbox(label="Status", interactive=False)
        
    # We automatically load the history of the default active session on startup
    initial_history = _rebuild_gradio_history(active_sessions[default_session_id]["agent"].context.get_history()) if default_session_id in active_sessions else []
    chatbot = gr.Chatbot(label="Conversation", value=initial_history)
    
    with gr.Row():
        msg_textbox = gr.Textbox(
            placeholder="Ask a security question...", 
            label="Your Message",
            scale=9
        )
        submit_btn = gr.Button("Send", scale=1)

    gr.Examples(
        examples=[
            "What hardware do I need to run a local server to run movies from home?", 
            "How has AI changed cybersecurity, both for defenders and attackers?", 
            "What are the biggest security mistakes organizations make?", 
            "What's the most overrated cybersecurity practice?"
        ],
        inputs=msg_textbox
    )

    export_btn.click(fn=export_chat, outputs=export_btn)
    
    import_file.upload(
        fn=import_chat, 
        inputs=[import_file], 
        outputs=[import_status, chatbot]
    )

    session_dropdown.change(
        fn=switch_session, 
        inputs=[session_dropdown], 
        outputs=[chatbot]
    )
    
    new_chat_btn.click(
        fn=handle_new_chat_btn, 
        outputs=[chatbot, session_dropdown]
    )
    
    submit_event = msg_textbox.submit(
        fn=chat_function, 
        inputs=[msg_textbox, chatbot], 
        outputs=[chatbot, session_dropdown]
    )
    submit_event.then(fn=lambda: "", outputs=msg_textbox)

    click_event = submit_btn.click(
        fn=chat_function, 
        inputs=[msg_textbox, chatbot], 
        outputs=[chatbot, session_dropdown]
    )
    click_event.then(fn=lambda: "", outputs=msg_textbox)

if __name__ == "__main__":
    demo.launch()