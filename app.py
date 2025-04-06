# app.py - React Website Builder (CDN Preview) with Sidebar Chat, Tabs, and New Window Link
import streamlit as st
import streamlit as st # Ensure streamlit is imported before use
import google.generativeai as genai
import os
from pathlib import Path
import json
import time
from dotenv import load_dotenv # Re-added dotenv import
import re # For regex used in CSS injection
import urllib.parse # <<< ADDED IMPORT for URL encoding

# --- Configuration ---
st.set_page_config(layout="wide", page_title="AI Tvorca Webstránok (React CDN)")
load_dotenv() # Re-added load_dotenv() call

# --- Constants ---
WORKSPACE_DIR = Path("workspace") # Directory for generated web files
WORKSPACE_DIR.mkdir(exist_ok=True)
CSS_FILENAME = "style.css" # Conventional CSS filename for injection

# --- Gemini API Configuration ---
try:
    # Use os.getenv for API key from .env file
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔴 Google API kľúč nenájdený. Prosím, uistite sa, že GOOGLE_API_KEY je nastavený vo vašom .env súbore.")
        st.stop()
    genai.configure(api_key=api_key)

    # Use os.getenv for model name from .env file, otherwise default
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25") # Default fallback

    st.sidebar.caption(f"Používaný model: `{model_name}`")
    model = genai.GenerativeModel(model_name)
except Exception as e:
    st.error(f"🔴 Nepodarilo sa nakonfigurovať Gemini alebo načítať model '{model_name}' pomocou .env: {e}")
    st.stop()

# --- Session State Initialization ---
if "messages" not in st.session_state: st.session_state.messages = []
if "selected_file" not in st.session_state: st.session_state.selected_file = None
if "file_content" not in st.session_state: st.session_state.file_content = ""
if "rendered_html" not in st.session_state: st.session_state.rendered_html = ""
# rendered_for_{filename} marker is added/removed dynamically

# --- Helper Functions --- (Keep as before) ---
def get_workspace_files():
    try: return sorted([f.name for f in WORKSPACE_DIR.iterdir() if f.is_file()])
    except Exception as e: st.error(f"Chyba pri vypisovaní súborov v pracovnom priestore: {e}"); return []

def read_file_content(filename):
    if not filename: return None
    if ".." in filename or filename.startswith(("/", "\\")): return None
    filepath = WORKSPACE_DIR / filename
    try:
        with open(filepath, "r", encoding="utf-8") as f: return f.read()
    except FileNotFoundError: return None
    except Exception as e: st.error(f"Chyba pri čítaní súboru '{filename}': {e}"); return None

def save_file_content(filename, content):
    if not filename: return False
    if ".." in filename or filename.startswith(("/", "\\")): return False
    filepath = WORKSPACE_DIR / filename
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f: f.write(content); return True
    except Exception as e: st.error(f"Chyba pri ukladaní súboru '{filename}': {e}"); return False

def delete_file(filename):
    if not filename: return False
    if ".." in filename or filename.startswith(("/", "\\")): return False
    filepath = WORKSPACE_DIR / filename
    try:
        os.remove(filepath)
        if st.session_state.selected_file == filename: # Clear state if selected file is deleted
            st.session_state.selected_file = None
            st.session_state.file_content = ""
            st.session_state.rendered_html = ""
            st.session_state.pop(f"rendered_for_{filename}", None)
        return True
    except FileNotFoundError: st.warning(f"Súbor '{filename}' nenájdený na vymazanie."); return False
    except Exception as e: st.error(f"Chyba pri mazaní súboru '{filename}': {e}"); return False

# --- AI Interaction & File Ops --- (Keep parse_and_execute_commands as before) ---
def parse_and_execute_commands(ai_response_text):
    parsed_commands = []
    try:
        response_text_cleaned = ai_response_text.strip()
        if response_text_cleaned.startswith("```json"): response_text_cleaned = response_text_cleaned[7:-3].strip()
        elif response_text_cleaned.startswith("```"): response_text_cleaned = response_text_cleaned[3:-3].strip()
        commands = json.loads(response_text_cleaned) # Strict parsing
        if not isinstance(commands, list): return [{"action": "chat", "content": f"AI (Non-list JSON): {ai_response_text}"}]
        for command in commands:
            if not isinstance(command, dict): parsed_commands.append({"action": "chat", "content": f"Skipped: {command}"}); continue
            action=command.get("action"); filename=command.get("filename"); content=command.get("content")
            parsed_commands.append(command)
            if action=="create_update":
                if filename and content is not None:
                    if not save_file_content(filename, content): st.warning(f"Nepodarilo sa uložiť '{filename}'.")
                else: st.warning(f"⚠️ Neplatný 'create_update': {command}")
            elif action=="delete":
                if filename: delete_file(filename)
                else: st.warning(f"⚠️ Neplatný 'delete': {command}")
            elif action=="chat": pass
            else: st.warning(f"⚠️ Neznáma akcia '{action}': {command}")
        return parsed_commands
    except json.JSONDecodeError as e:
        st.error(f"🔴 Neplatný JSON: {e}\nText:\n'{ai_response_text[:500]}...'")
        return [{"action": "chat", "content": f"AI(Invalid JSON): {ai_response_text}"}]
    except Exception as e:
        st.error(f"🔴 Chyba pri spracovaní príkazov: {e}")
        return [{"action": "chat", "content": f"Error processing commands: {e}"}]

# --- Keep call_gemini as before (with strict prompt for web/React CDN) ---
def call_gemini(history):
    safe_history = []
    for msg in history:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            safe_history.append({"role": msg["role"], "content": str(msg["content"])})

    instruction = """
    You are an AI assistant that helps users create web pages and simple web applications.
    Your goal is to generate HTML, CSS, JavaScript code, or self-contained React preview files.
    Based on the user's request, you MUST respond ONLY with a valid JSON array containing file operation objects.

    **JSON FORMATTING RULES (VERY IMPORTANT):**
    1.  The entire response MUST be a single JSON array starting with '[' and ending with ']'.
    2.  All keys (like "action", "filename", "content") MUST be enclosed in **double quotes** (").
    3.  All string values (like filenames and the large code content) MUST be enclosed in **double quotes** ("). Single quotes (') or backticks (`) are NOT ALLOWED for keys or string values in the JSON structure.
    4.  Special characters within the "content" string (like newlines, double quotes inside the code) MUST be properly escaped (e.g., use '\\n' for newlines, '\\"' for double quotes).

    **EXAMPLE of Correct JSON action object:**
    {
        "action": "create_update",
        "filename": "example.html",
        "content": "<!DOCTYPE html>\\n<html>\\n<head>\\n  <title>Example</title>\\n</head>\\n<body>\\n  <h1>Hello World!</h1>\\n  <p>This contains a \\"quote\\" example.</p>\\n</body>\\n</html>"
    }

    Possible action objects in the JSON array:
    - {"action": "create_update", "filename": "path/to/file.ext", "content": "file content string here..."}
    - {"action": "delete", "filename": "path/to/file.ext"}
    - {"action": "chat", "content": "Your helpful answer string here..."}

    **VERY IMPORTANT - UPDATING FILES:**
    If the user asks you to modify an existing file (e.g., "add a footer to index.html", "change the button color in style.css"), you MUST provide the **ENTIRE**, complete, updated file content within the 'content' field of the 'create_update' action object, following all JSON formatting rules. Do NOT provide only the changed lines or a diff.

    **REACT PREVIEWS:**
    If the user asks for a simple React component/app to preview, generate a SINGLE self-contained HTML file (e.g., 'react_preview.html') using 'create_update'. This file MUST use CDN links for React/ReactDOM/Babel, have a <div id="root">, include JSX in a <script type="text/babel"> tag, render to the root, and include CSS in <style> tags within the <head>. (Ensure valid JSON).

    **GENERAL:**
    Use standard filenames ('index.html', 'style.css', 'script.js'). The standard CSS file for injection is 'style.css'. If unsure, ask the user. Respond ONLY with the JSON array. Use 'chat' action for questions or explanations.
    """
    current_files = get_workspace_files()
    file_list_prompt = f"Current files in workspace: {', '.join(current_files) if current_files else 'None'}"
    gemini_history = []
    gemini_history.append({"role": "user", "parts": [{"text": f"{instruction}\n{file_list_prompt}"}]})
    gemini_history.append({"role": "model", "parts": [{"text": '[{"action": "chat", "content": "Okay, I understand the strict JSON formatting rules (double quotes, escaping) and the need to provide full file content on updates. I will respond only with the valid JSON array. Ready."}]'}]})
    for msg in safe_history:
        role = "user" if msg["role"] == "user" else "model"; content_text = msg["content"]
        if role == "model" and isinstance(msg["content"], list):
            try: content_text = json.dumps(msg["content"])
            except Exception: content_text = str(msg["content"])
        gemini_history.append({"role": role, "parts": [{"text": content_text}]})
    try:
        response = model.generate_content(gemini_history); return response.text
    except Exception as e:
        if "429" in str(e): st.error("🔴 Prekročená kvóta/limit požiadaviek Gemini API.")
        else: st.error(f"🔴 Volanie Gemini API zlyhalo: {e}")
        error_content = f"Error calling AI: {str(e)}".replace('"',"'"); return json.dumps([{"action": "chat", "content": error_content}])

# --- Streamlit UI Layout ---

# --- Sidebar: Chat Interface --- (Keep as before) ---
with st.sidebar:
    st.header("💬 Chat s AI")
    st.markdown("Požiadajte AI o vytvorenie alebo úpravu webových súborov (HTML, CSS, JS, React CDN náhľady).")
    st.caption(f"Používaný model: `{model_name}`") # Display model name
    chat_container = st.container(height=500)
    with chat_container:
        if st.session_state.messages:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    if isinstance(message.get("content"), list) and message.get("role") == "assistant":
                        display_text = ""; chat_messages = []
                        for command in message["content"]:
                            if not isinstance(command, dict): continue
                            action = command.get("action"); filename = command.get("filename")
                            if action == "create_update": display_text += f"📝 Vytvoriť/Aktualizovať: `{filename}`\n"
                            elif action == "delete": display_text += f"🗑️ Vymazať: `{filename}`\n"
                            elif action == "chat": chat_messages.append(command.get('content', '...'))
                            else: display_text += f"⚠️ {command.get('content', f'Neznáma akcia: {action}')}\n"
                        final_display = (display_text + "\n".join(chat_messages)).strip()
                        if not final_display: final_display = "(Žiadna akcia)"
                        st.markdown(final_display)
                    else: st.write(str(message.get("content", "")))
        else: st.info("História chatu je prázdna.")
    if prompt := st.chat_input("napr., Vytvor index.html s nadpisom"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("🧠 AI premýšľa..."):
            ai_response_text = call_gemini(st.session_state.messages)
            executed_commands = parse_and_execute_commands(ai_response_text)
            st.session_state.messages.append({"role": "assistant", "content": executed_commands})
            st.rerun()

# --- Main Area: Tabs ---
st.title("🤖 AI Tvorca Webstránok (React CDN Náhľad)")
tab1, tab2 = st.tabs([" 📂 Pracovný priestor ", " 👀 Náhľad "])

with tab1: # --- Workspace Tab (Keep as before) ---
    st.header("Pracovný priestor & Editor")
    st.markdown("---")
    st.subheader("Súbory")
    available_files = get_workspace_files()
    if not available_files: st.info(f"Pracovný priestor '{WORKSPACE_DIR.name}' je prázdny.")
    current_selection_index = 0; options = [None] + available_files
    if st.session_state.selected_file in options:
        try: current_selection_index = options.index(st.session_state.selected_file)
        except ValueError: st.session_state.selected_file = None
    selected_file_option = st.selectbox("Vyberte súbor:", options=options, format_func=lambda x: "--- Vyberte ---" if x is None else x, key="ws_file_select", index=current_selection_index)
    st.subheader("Upraviť kód")
    editor_key = f"editor_{st.session_state.selected_file or 'none'}"
    if selected_file_option != st.session_state.selected_file:
        st.session_state.selected_file = selected_file_option
        st.session_state.file_content = read_file_content(st.session_state.selected_file) or "" if st.session_state.selected_file else ""
        st.session_state.rendered_html = ""; st.session_state.pop(f"rendered_for_{st.session_state.selected_file}", None)
        st.rerun()
    if st.session_state.selected_file:
        st.caption(f"Upravuje sa: `{st.session_state.selected_file}`")
        file_ext = Path(st.session_state.selected_file).suffix.lower()
        lang_map = {".html": "html", ".css": "css", ".js": "javascript", ".py":"python", ".md": "markdown", ".json": "json", ".jsx":"javascript", ".vue":"vue", ".svelte":"svelte", ".txt":"text"}
        language = lang_map.get(file_ext)
        edited_content = st.text_area("Editor kódu", value=st.session_state.file_content, height=400, key=editor_key, label_visibility="collapsed", args=(language,))
        if edited_content != st.session_state.file_content:
             if st.button("💾 Uložiť manuálne zmeny"):
                if save_file_content(st.session_state.selected_file, edited_content):
                    st.session_state.file_content = edited_content; st.success(f"Uložené: `{st.session_state.selected_file}`")
                    st.session_state.rendered_html = ""; st.session_state.pop(f"rendered_for_{st.session_state.selected_file}", None)
                    time.sleep(0.5); st.rerun()
                else: st.error("Nepodarilo sa uložiť.")
    else:
        st.info("Vyberte súbor na úpravu.")
        st.text_area("Editor kódu", value="Vyberte súbor...", height=400, key="editor_placeholder", disabled=True, label_visibility="collapsed")

with tab2: # --- Preview Tab (Add New Window Link) ---
    st.header("👀 Živý náhľad")
    st.markdown("---")
    css_applied_info = "" # Initialize to prevent NameError

    if st.session_state.selected_file:
        if st.session_state.selected_file.lower().endswith(('.html', '.htm')):
            current_file_content_for_preview = read_file_content(st.session_state.selected_file)
            rendered_marker_key = f"rendered_for_{st.session_state.selected_file}"
            needs_render_update = False
            if current_file_content_for_preview is not None:
                 needs_render_update = (not st.session_state.rendered_html or st.session_state.get(rendered_marker_key) != current_file_content_for_preview)
            else:
                 st.session_state.rendered_html = ""; st.session_state.pop(rendered_marker_key, None)

            # --- Generate Rendered HTML (if needed) ---
            if needs_render_update:
                if current_file_content_for_preview is not None:
                    final_html = current_file_content_for_preview
                    is_react_cdn_preview = "<script src=\"https://unpkg.com/@babel/standalone" in final_html
                    css_applied_info = "" # Reset for this render pass
                    if not is_react_cdn_preview: # Try CSS injection only if not React CDN preview
                        css_content = read_file_content(CSS_FILENAME)
                        if css_content:
                            style_tag = f"\n<style>\n{css_content}\n</style>\n"
                            head_match = re.search(r"</head>", final_html, re.IGNORECASE)
                            if head_match:
                                injection_point = head_match.start()
                                final_html = final_html[:injection_point] + style_tag + final_html[injection_point:]
                                css_applied_info = f"🎨 Vložené `{CSS_FILENAME}`." # Set only if successful
                    st.session_state.rendered_html = final_html
                    st.session_state[rendered_marker_key] = current_file_content_for_preview
                    # Info message moved below display logic
                else:
                    st.warning(f"Nepodarilo sa načítať `{st.session_state.selected_file}` pre náhľad.")
                    st.session_state.rendered_html = "Chyba pri čítaní súboru pre náhľad."
                    st.session_state.pop(rendered_marker_key, None)

            # --- Display Preview & New Window Link ---
            if st.session_state.rendered_html and "Chyba pri čítaní súboru" not in st.session_state.rendered_html:
                st.info(f"Náhľad súboru: `{st.session_state.selected_file}`")
                st.markdown("---")

                # --- NEW: Button/Link to Open in New Window ---
                try:
                    # URL encode the HTML content
                    encoded_html = urllib.parse.quote(st.session_state.rendered_html)
                    data_uri = f"data:text/html;charset=utf-8,{encoded_html}"
                    # Display as a link (browsers usually handle data URIs opening in new tabs)
                    st.markdown(f'<a href="{data_uri}" target="_blank" rel="noopener noreferrer"><button>🚀 Otvoriť náhľad v novom okne</button></a>', unsafe_allow_html=True)
                    st.caption("_(Používa Data URI - najlepšie pre samostatné HTML/CSS/JS)_")
                except Exception as e:
                    st.warning(f"Nepodarilo sa vytvoriť odkaz 'Otvoriť v novom okne': {e}")
                # --- End New Window Link ---


                st.components.v1.html(st.session_state.rendered_html, height=600, scrolling=True)
                st.markdown("---")
                # --- Caption Logic ---
                preview_note = "Poznámka: Základný HTML náhľad."
                if "<script src=\"https://unpkg.com/@babel/standalone" in st.session_state.rendered_html:
                     preview_note = "Poznámka: Náhľad používa CDN odkazy a transpiláciu v prehliadači pre jednoduché React ukážky."
                # Re-check css_applied_info based on rendered content for caption consistency
                # This assumes css_applied_info was correctly set during the relevant render pass
                # A more robust way might be to store the injection status in session state too.
                # Simple check: if style tag is present (might be inaccurate if original HTML had one)
                if not is_react_cdn_preview and f"Vložené `{CSS_FILENAME}`" in css_applied_info: # Check the flag set during render
                     preview_note += f" {css_applied_info}"
                st.caption(preview_note)

            elif "Chyba pri čítaní súboru" in str(st.session_state.rendered_html):
                 st.error("Náhľad zlyhal: Nepodarilo sa načítať HTML súbor.")

        else: # File selected, but not HTML
            st.info(f"Náhľad je dostupný iba pre HTML súbory. Vybraný: `{st.session_state.selected_file}`")
            st.session_state.rendered_html = ""
            st.session_state.pop(f"rendered_for_{st.session_state.selected_file}", None)
    else: # No file selected
        st.info("Vyberte HTML súbor z karty 'Pracovný priestor' pre zobrazenie náhľadu.")
        st.session_state.rendered_html = ""

# --- Footer / Warnings (Sidebar) --- (Keep as before) ---
st.sidebar.markdown("---")
st.sidebar.warning("""
    **Obmedzenia prototypu a varovania:**
    - **Bezpečnosť:** AI môže priamo upravovať súbory! Používajte lokálne a opatrne. **Nezverejňujte verejne.**
    - **Operácie so súbormi:** Základné vytvorenie/aktualizácia/vymazanie. Možné chyby.
    - **Náhľad:** Základné vykresľovanie HTML. Pokúša sa vložiť `style.css`. Dokáže vykresliť jednoduché príklady React CDN. **Žiadny build proces, prepojené JS/CSS (pokiaľ nie sú vložené), atď.** "Otvoriť v novom okne" používa Data URI a má obmedzenia (dĺžka URL, žiadne relatívne cesty pre obrázky).
    - **Spoľahlivosť AI:** AI môže nepochopiť, generovať neplatný JSON/kód alebo zlyhať pri aktualizáciách. Ladenie promptov pomáha. Chyby sú zachytené, ale operácie so súbormi môžu zlyhať.
    - **Stav:** Stratí sa pri obnovení prehliadača.
""", icon="⚠️")
