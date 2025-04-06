# app.py - Multi-Agent Game Generation System
import streamlit as st
import google.generativeai as genai
import os
from pathlib import Path
import json
import time
from dotenv import load_dotenv
import re
import shutil # For potentially cleaning workspace
from typing import TypedDict, List, Dict, Optional, Sequence
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver # For potential future state saving

# --- Configuration ---
st.set_page_config(layout="wide", page_title="AI Generátor Hier")
load_dotenv()

# --- Constants ---
WORKSPACE_DIR = Path("workspace")
WORKSPACE_DIR.mkdir(exist_ok=True)
MAX_GAMES = 16 # Target number of games

# --- Gemini API Configuration ---
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔴 Google API kľúč nenájdený. Prosím, uistite sa, že GOOGLE_API_KEY je nastavený vo vašom .env súbore.")
        st.stop()
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest") # Using a potentially faster model
    model = genai.GenerativeModel(model_name)
    st.sidebar.caption(f"Používaný model: `{model_name}`")
except Exception as e:
    st.error(f"🔴 Nepodarilo sa nakonfigurovať Gemini alebo načítať model '{model_name}' pomocou .env: {e}")
    st.stop()

# --- LangGraph State Definition ---
class AgentState(TypedDict):
    theme: str
    game_concepts: Optional[List[str]]
    game_plan: Optional[List[Dict[str, str]]] # List of {"concept": "...", "instruction": "..."}
    current_game_index: int
    worker_output: Optional[List[Dict[str, str]]] # Output from the worker agent for the current game
    saved_games: List[Dict[str, str]] # List of {"name": "...", "folder": "..."}
    log_messages: List[str]
    error: Optional[str]

# --- Helper Functions ---
def sanitize_foldername(name: str) -> str:
    """Creates a safe folder name from a game concept."""
    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
    name = re.sub(r'[-\s]+', '_', name)
    return name if name else "untitled_game"

def save_game_files(game_name: str, game_index: int, files_data: List[Dict[str, str]]) -> Optional[str]:
    """Saves generated files to a dedicated game folder."""
    folder_name = f"{sanitize_foldername(game_name)}_{game_index:02d}"
    game_dir = WORKSPACE_DIR / folder_name
    try:
        game_dir.mkdir(parents=True, exist_ok=True)
        for file_info in files_data:
            filename = file_info.get("filename")
            content = file_info.get("content")
            if filename and content is not None:
                # Basic security check
                if ".." in filename or filename.startswith(("/", "\\")):
                    st.warning(f"⚠️ Preskočený nebezpečný názov súboru v hre {game_name}: {filename}")
                    continue
                filepath = game_dir / filename
                filepath.parent.mkdir(parents=True, exist_ok=True) # Ensure subdirs within game folder are created
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                 st.warning(f"⚠️ Chýbajúce 'filename' alebo 'content' v dátach pre hru {game_name}: {file_info}")
        return str(game_dir) # Return the path to the created directory
    except Exception as e:
        st.error(f"🔴 Chyba pri ukladaní súborov pre hru '{game_name}' do '{folder_name}': {e}")
        return None

def call_llm(prompt: str, is_json_output: bool = True) -> str:
    """ Helper function to call the LLM and handle potential errors. """
    try:
        # Simple retry mechanism
        for attempt in range(2):
            try:
                response = model.generate_content(prompt)
                # Basic validation if JSON is expected
                if is_json_output:
                    cleaned_response = response.text.strip()
                    if cleaned_response.startswith("```json"):
                        cleaned_response = cleaned_response[7:-3].strip()
                    elif cleaned_response.startswith("```"):
                         cleaned_response = cleaned_response[3:-3].strip()
                    # Try parsing to catch invalid JSON early
                    json.loads(cleaned_response)
                    return cleaned_response
                else:
                    return response.text
            except Exception as inner_e:
                if "429" in str(inner_e) and attempt == 0:
                    st.warning("⏳ Limit API prekročený, čakám 5 sekúnd pred opakovaním...")
                    time.sleep(5)
                    continue # Retry
                elif is_json_output and isinstance(inner_e, json.JSONDecodeError):
                     st.warning(f"⚠️ LLM vrátilo neplatný JSON, skúšam znova... Chyba: {inner_e}")
                     if attempt == 0: continue # Retry on first JSON error
                     else: raise # Raise error on second JSON failure
                else:
                    raise # Re-raise other errors or errors on second attempt
        # If loop finishes without returning/raising (e.g., due to retries)
        raise Exception("LLM volanie zlyhalo po opakovaniach.")

    except Exception as e:
        st.error(f"🔴 Volanie LLM zlyhalo: {e}")
        # Return an error structure if JSON was expected
        if is_json_output:
            return json.dumps([{"action": "chat", "content": f"Chyba volania LLM: {e}"}])
        else:
            return f"Chyba volania LLM: {e}"

# --- Agent Node Functions ---

def games_planner_node(state: AgentState) -> AgentState:
    """Generates a list of game concepts based on the theme."""
    theme = state["theme"]
    log_messages = state.get("log_messages", [])
    log_messages.append(f"🤖 GAMES_PLANNER: Generujem {MAX_GAMES} konceptov hier pre tému '{theme}'...")
    st.session_state.log_messages = log_messages # Update UI immediately

    prompt = f"""
    Si kreatívny plánovač hier. Vytvor zoznam {MAX_GAMES} jednoduchých konceptov webových hier (HTML, CSS, JS) na tému '{theme}'.
    Zameraj sa na jednoduché, dobre známe herné mechaniky.
    Odpovedz IBA platným JSON poľom reťazcov obsahujúcim názvy herných konceptov.

    Príklad pre tému 'vesmír':
    ["Hádaj planétu", "Vesmírny kliker", "Pexeso s kozmickými loďami", "Kvíz o súhvezdiach", ...]
    """
    try:
        response_text = call_llm(prompt, is_json_output=True)
        game_concepts = json.loads(response_text)
        if not isinstance(game_concepts, list) or not all(isinstance(item, str) for item in game_concepts):
            raise ValueError("LLM nevrátilo platný zoznam názvov hier.")
        log_messages.append(f"✅ GAMES_PLANNER: Koncepty hier vygenerované ({len(game_concepts)} hier).")
        return {**state, "game_concepts": game_concepts[:MAX_GAMES], "log_messages": log_messages, "error": None}
    except Exception as e:
        error_msg = f"🔴 GAMES_PLANNER zlyhal: {e}"
        log_messages.append(error_msg)
        return {**state, "log_messages": log_messages, "error": error_msg}

def profesor_planner_node(state: AgentState) -> AgentState:
    """Refines the game concepts with aesthetic instructions."""
    game_concepts = state.get("game_concepts")
    log_messages = state.get("log_messages", [])
    if not game_concepts:
        error_msg = "🔴 PROFESOR_PLANNER: Chýbajú herné koncepty."
        log_messages.append(error_msg)
        return {**state, "log_messages": log_messages, "error": error_msg}

    log_messages.append("🧑‍🏫 PROFESOR_PLANNER: Pridávam inštrukcie pre vizuálnu stránku ku každému konceptu...")
    st.session_state.log_messages = log_messages

    game_plan = []
    for concept in game_concepts:
        instruction = (
            f"Vytvor jednoduchú webovú hru '{concept}'. "
            f"Prioritou je vytvoriť **vizuálne krásne a pútavé používateľské rozhranie (UI)** pomocou moderného CSS. "
            f"Zahrň relevantnú **grafiku** (zváž SVG, CSS art alebo jednoduché obrázky, ak je to vhodné) a pútavé **CSS animácie**. "
            f"Vzhľad a dojem sú dôležitejšie ako zložitá herná logika. Hra by mala byť hrateľná, ale jednoduchá."
        )
        game_plan.append({"concept": concept, "instruction": instruction})

    log_messages.append("✅ PROFESOR_PLANNER: Herný plán s inštrukciami vytvorený.")
    return {**state, "game_plan": game_plan, "log_messages": log_messages, "error": None}

def worker_node(state: AgentState) -> AgentState:
    """Generates the files for the current game based on the plan."""
    game_plan = state.get("game_plan")
    current_index = state.get("current_game_index", 0)
    log_messages = state.get("log_messages", [])

    if not game_plan or current_index >= len(game_plan):
        error_msg = f"🔴 WORKER: Neplatný herný plán alebo index ({current_index})."
        log_messages.append(error_msg)
        return {**state, "log_messages": log_messages, "error": error_msg}

    current_game = game_plan[current_index]
    concept = current_game["concept"]
    instruction = current_game["instruction"]
    theme = state["theme"]

    log_messages.append(f"👷 WORKER: Začínam generovať hru {current_index + 1}/{len(game_plan)}: '{concept}'...")
    st.session_state.log_messages = log_messages

    prompt = f"""
    Si expert na vývoj webových hier (HTML, CSS, JavaScript). Tvojou úlohou je vytvoriť súbory pre jednoduchú webovú hru.

    Téma: '{theme}'
    Koncept hry: '{concept}'
    Špecifické inštrukcie: '{instruction}'

    Požiadavky na výstup:
    1. Vygeneruj potrebné súbory (typicky index.html, style.css, script.js).
    2. Zameraj sa na vizuálnu stránku podľa inštrukcií (krásne UI, grafika, animácie).
    3. Udržuj kód jednoduchý a funkčný pre daný koncept.
    4. Všetky súbory musia byť samostatné (žiadne externé závislosti okrem bežných prehliadačových API).
    5. Odpovedz IBA platným JSON poľom objektov, kde každý objekt reprezentuje jeden súbor.
       Formát objektu súboru: {{"filename": "nazov_suboru.ext", "content": "obsah súboru ako reťazec..."}}
    6. Dôsledne dodržuj JSON formátovanie: dvojité úvodzovky pre kľúče a reťazce, správne escapovanie špeciálnych znakov (\\n, \\", atď.) v obsahu súboru.

    Príklad JSON výstupu:
    [
      {{"filename": "index.html", "content": "<!DOCTYPE html>..."}},
      {{"filename": "style.css", "content": "body {{ ... }}"}},
      {{"filename": "script.js", "content": "console.log('Hello');"}}
    ]
    """

    try:
        response_text = call_llm(prompt, is_json_output=True)
        files_data = json.loads(response_text)
        if not isinstance(files_data, list) or not all(isinstance(item, dict) and "filename" in item and "content" in item for item in files_data):
             raise ValueError("LLM nevrátilo platný zoznam súborov v JSON formáte.")

        log_messages.append(f"✅ WORKER: Súbory pre '{concept}' vygenerované.")
        return {**state, "worker_output": files_data, "log_messages": log_messages, "error": None}
    except Exception as e:
        error_msg = f"🔴 WORKER zlyhal pri generovaní '{concept}': {e}"
        log_messages.append(error_msg)
        # Still proceed to next game, but log the error
        return {**state, "worker_output": None, "log_messages": log_messages, "error": error_msg} # Allow graph to continue

def save_and_log_node(state: AgentState) -> AgentState:
    """Saves the generated files and updates the list of saved games."""
    worker_output = state.get("worker_output")
    game_plan = state.get("game_plan")
    current_index = state.get("current_game_index", 0)
    saved_games = state.get("saved_games", [])
    log_messages = state.get("log_messages", [])

    if worker_output and game_plan and current_index < len(game_plan):
        concept = game_plan[current_index]["concept"]
        log_messages.append(f"💾 Ukladám súbory pre hru '{concept}'...")
        st.session_state.log_messages = log_messages

        game_dir = save_game_files(concept, current_index + 1, worker_output)

        if game_dir:
            saved_games.append({"name": concept, "folder": game_dir})
            log_messages.append(f"✅ Hra '{concept}' uložená do '{Path(game_dir).name}'.")
        else:
            # Error logged in save_game_files
            log_messages.append(f"❌ Nepodarilo sa uložiť súbory pre '{concept}'.")

    elif not worker_output and state.get("error"):
         # Error already logged by worker
         pass # Just move to the next game
    else:
        log_messages.append(f"🤔 Preskakujem ukladanie pre hru index {current_index} (žiadny výstup alebo neplatný stav).")


    # Increment index for the next iteration
    next_index = current_index + 1
    return {**state, "saved_games": saved_games, "current_game_index": next_index, "log_messages": log_messages, "worker_output": None} # Clear worker output

# --- Conditional Edge ---
def should_continue(state: AgentState) -> str:
    """Determines whether to continue the loop or end."""
    current_index = state.get("current_game_index", 0)
    game_plan = state.get("game_plan", [])
    error = state.get("error")

    # Stop if major error occurred before worker loop
    if not game_plan and error:
        return "end_process"

    if current_index >= len(game_plan) or current_index >= MAX_GAMES:
        return "end_process"
    else:
        return "continue_worker"

# --- Build the Graph ---
graph_builder = StateGraph(AgentState)

graph_builder.add_node("games_planner", games_planner_node)
graph_builder.add_node("profesor_planner", profesor_planner_node)
graph_builder.add_node("worker", worker_node)
graph_builder.add_node("save_and_log", save_and_log_node)

graph_builder.set_entry_point("games_planner")
graph_builder.add_edge("games_planner", "profesor_planner")

# Conditional loop for worker
graph_builder.add_conditional_edges(
    "profesor_planner",
    should_continue,
    {
        "continue_worker": "worker", # Start worker loop if plan exists
        "end_process": END
    }
)
graph_builder.add_conditional_edges(
    "save_and_log", # After saving/logging, check if loop should continue
    should_continue,
    {
        "continue_worker": "worker", # Go back to worker for next game
        "end_process": END
    }
)
graph_builder.add_edge("worker", "save_and_log")

# Compile the graph
# memory = MemorySaver() # Optional: For resuming runs later
app_graph = graph_builder.compile() # checkpointer=memory

# --- Streamlit UI ---
st.title("🤖 AI Generátor Hier (Multi-Agent)")
st.markdown("Zadajte tému a AI agenti vygenerujú sériu jednoduchých webových hier.")

# --- Input Area ---
theme_input = st.text_input("Zadajte tému pre hry:", placeholder="napr. zvieratá, vesmír, matematika")

if 'log_messages' not in st.session_state:
    st.session_state.log_messages = ["Vitajte! Zadajte tému a stlačte 'Generovať Hry'."]
if 'running' not in st.session_state:
    st.session_state.running = False
if 'saved_games_list' not in st.session_state:
     st.session_state.saved_games_list = []

# --- Control Button ---
if st.button("🚀 Generovať 16 Hier", disabled=st.session_state.running or not theme_input):
    # Clear previous run logs and saved games list for UI
    st.session_state.log_messages = [f"🏁 Štartujem generovanie pre tému: '{theme_input}'"]
    st.session_state.saved_games_list = []
    st.session_state.running = True

    # Clean workspace before starting? Optional.
    # try:
    #     for item in WORKSPACE_DIR.iterdir():
    #         if item.is_dir():
    #             shutil.rmtree(item)
    #         else:
    #             item.unlink()
    #     st.session_state.log_messages.append("🧹 Pracovný priestor vyčistený.")
    # except Exception as e:
    #     st.session_state.log_messages.append(f"⚠️ Nepodarilo sa vyčistiť pracovný priestor: {e}")

    # Initial state for the graph
    initial_state = AgentState(
        theme=theme_input,
        game_concepts=None,
        game_plan=None,
        current_game_index=0,
        worker_output=None,
        saved_games=[],
        log_messages=st.session_state.log_messages,
        error=None
    )

    # Use st.status for better progress indication
    with st.status("⚙️ Spúšťam agentov...", expanded=True) as status:
        try:
            # Stream the graph execution
            # config = {"configurable": {"thread_id": "game-gen-thread"}} # For memory saver
            final_state = None
            for output in app_graph.stream(initial_state): # Removed config for simplicity
                # output is a dictionary where keys are node names
                # and values are the AgentState after that node ran
                node_name = list(output.keys())[0]
                current_state = list(output.values())[0]

                # Update logs in session state for UI refresh
                st.session_state.log_messages = current_state.get("log_messages", [])
                st.session_state.saved_games_list = current_state.get("saved_games", [])

                # Update status message (optional)
                last_log = st.session_state.log_messages[-1] if st.session_state.log_messages else "Pracujem..."
                status.update(label=f"⚙️ {last_log}", state="running")

                # Store the very last state
                final_state = current_state

            # Update status upon completion
            if final_state and final_state.get("error"):
                 status.update(label=f"⚠️ Proces dokončený s chybami.", state="error")
            else:
                 status.update(label="✅ Proces generovania hier dokončený!", state="complete")

        except Exception as e:
            st.error(f"🔴 Neočakávaná chyba počas behu grafu: {e}")
            status.update(label=f"💥 Kritická chyba!", state="error")
            st.session_state.log_messages.append(f"💥 Kritická chyba: {e}")
        finally:
            st.session_state.running = False # Allow starting again
            # Rerun to potentially update the showcase if it's on the same page
            # Or rely on user navigating to the showcase page
            st.rerun()


# --- Log Display ---
st.subheader("📜 Priebeh Generovania (Log)")
log_container = st.container(height=300)
with log_container:
    log_text = "\n".join(st.session_state.log_messages)
    st.text(log_text)

# --- Showcase Area (Simple List for now) ---
st.subheader("🎮 Vygenerované Hry")
if st.session_state.saved_games_list:
    for game_info in st.session_state.saved_games_list:
        game_name = game_info.get("name", "Neznáma hra")
        game_folder = game_info.get("folder", "")
        if game_folder:
            folder_path = Path(game_folder)
            st.markdown(f"- **{game_name}** (v priečinku: `{folder_path.name}`)")
            # Add a link - Note: This link only works reliably if running locally
            # and potentially requires the local server to be running if JS needs it.
            index_file = folder_path / "index.html"
            if index_file.exists():
                 # Simple relative link - might not work well in all scenarios
                 # A better approach might involve the local server if kept
                 st.link_button(f"Otvoriť {game_name}", f"./{folder_path.relative_to(Path.cwd())}/index.html", help=f"Pokúsi sa otvoriť {index_file.name}")

else:
    st.info("Zatiaľ neboli vygenerované žiadne hry.")


# --- Footer / Warnings ---
st.sidebar.markdown("---")
st.sidebar.warning("""
    **Obmedzenia prototypu a varovania:**
    - **Generovanie:** Môže trvať dlho a spotrebovať veľa API volaní.
    - **Kvalita Hier:** Vizuálna stránka a funkčnosť závisí od schopností LLM.
    - **Bezpečnosť:** AI generuje kód. Spúšťajte lokálne a opatrne.
    - **Stav:** Stratí sa pri obnovení prehliadača.
""", icon="⚠️")
