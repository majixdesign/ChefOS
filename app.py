import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re
import time
import random
import urllib.parse
import streamlit.components.v1 as components

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sous", page_icon="🍳", layout="wide")

# --- 1. VIBE CONTROLLER ---
c_ph, c_toggle = st.columns([6, 1])
with c_toggle:
    vibe_mode = st.toggle("✨ Vibe Mode")

# --- 2. DYNAMIC DESIGN SYSTEM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@300;400;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');
    
    /* ANIMATIONS */
    @keyframes marquee {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    
    @keyframes glitch {
        0% { text-shadow: 4px 4px 0px #FF00FF; }
        50% { text-shadow: -4px -4px 0px #00FFFF; }
        100% { text-shadow: 4px 4px 0px #FF00FF; }
    }
    </style>
""", unsafe_allow_html=True)

if not vibe_mode:
    # === SYSTEM MODE (The Architect - Default) ===
    st.markdown("""
        <style>
            html, body, [class*="css"] { font-family: 'Archivo', sans-serif; }
            h1 { font-family: 'Archivo', sans-serif !important; font-weight: 700; letter-spacing: -0.02em; }
            
            div.stButton > button, div[data-testid="stForm"] button {
                background-color: #000 !important; color: #fff !important; border-radius: 8px;
                text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; border: none;
                height: auto; padding: 0.6rem 1.2rem;
            }
            @media (prefers-color-scheme: dark) {
                h1 { color: #e0e0e0 !important; }
                div.stButton > button, div[data-testid="stForm"] button { background-color: #fff !important; color: #000 !important; }
            }
        </style>
    """, unsafe_allow_html=True)

else:
    # === VIBE MODE (Gen Z / Neo-Brutal) ===
    st.markdown("""
        <style>
            .stApp {
                background-color: #000;
                background-image: radial-gradient(#222 1px, transparent 0);
                background-size: 30px 30px;
            }
            html, body, [class*="css"], p, label, div, span {
                font-family: 'Space Mono', monospace !important;
                color: #ffffff !important;
            }
            h1 { 
                font-family: 'Space Mono', monospace !important; 
                font-weight: 700 !important;
                text-transform: uppercase;
                font-size: 4rem !important;
                color: #fff !important;
                animation: glitch 0.5s infinite steps(1);
            }
            
            div.stButton > button, div[data-testid="stForm"] button {
                background-color: #000 !important;
                color: #00FF00 !important;
                border: 3px solid #00FF00 !important;
                border-radius: 0px !important;
                font-family: 'Space Mono', monospace !important;
                font-weight: 700;
                box-shadow: 8px 8px 0px #00FF00 !important;
                transition: all 0.1s;
                text-transform: uppercase;
            }
            div.stButton > button:hover, div[data-testid="stForm"] button:hover {
                transform: translate(4px, 4px);
                box-shadow: 4px 4px 0px #FF00FF !important;
                border-color: #FF00FF !important;
                color: #FF00FF !important;
            }

            input {
                background: #000 !important;
                border: 2px solid #fff !important;
                border-bottom: 5px solid #fff !important;
                color: #00FF00 !important;
                border-radius: 0px !important;
                font-family: 'Space Mono', monospace !important;
            }
            div[data-testid="stVerticalBlock"] { gap: 1.5rem; }
            div[data-testid="stExpander"], div[data-testid="stForm"] {
                border: 2px solid #333 !important; border-radius: 0px !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background: #00FF00; overflow: hidden; white-space: nowrap; border-bottom: 3px solid #000; margin-top: -30px; margin-bottom: 20px;">
            <div style="display: inline-block; animation: marquee 10s linear infinite; font-family: 'Space Mono'; font-weight: bold; font-size: 1.2rem; color: #000; padding: 10px;">
                NO CAP /// JUST COOKING /// IT'S GIVING MICHELIN /// MAIN CHARACTER ENERGY /// NO CAP /// JUST COOKING /// IT'S GIVING MICHELIN
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 3. CONFIGURATION & LOGIC ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        st.error("🔑 Google API Key missing.")
        st.stop()

genai.configure(api_key=api_key)

def get_working_model():
    try:
        all_models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m.name for m in all_models if 'flash' in m.name.lower()]
        if flash_models: return genai.GenerativeModel(flash_models[0])
        pro_models = [m.name for m in all_models if 'pro' in m.name.lower()]
        if pro_models: return genai.GenerativeModel(pro_models[0])
        if all_models: return genai.GenerativeModel(all_models[0].name)
        return genai.GenerativeModel("models/gemini-pro")
    except:
        return genai.GenerativeModel("models/gemini-1.5-flash")

model = get_working_model()

# --- HELPER FUNCTIONS ---
def clean_list(raw_list):
    clean_items = []
    IGNORE_LIST = ["none", "null", "n/a", "undefined", "", "missing", "optional", "core", "character", "must_haves", "soul"]
    if isinstance(raw_list, list):
        for item in raw_list:
            if isinstance(item, list): clean_items.extend(clean_list(item))
            elif isinstance(item, str):
                s = item.strip().replace("- ", "").replace("* ", "")
                if len(s) > 2 and s.lower() not in IGNORE_LIST: clean_items.append(s)
            elif isinstance(item, dict): clean_items.extend(clean_list(list(item.values())))
    return clean_items

def robust_api_call(prompt):
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except:
        try:
            response = model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match: return json.loads(match.group(0))
        except Exception as e:
            return f"ERROR: {str(e)}"

def copy_to_clipboard_button(text, is_vibe):
    escaped_text = text.replace("\n", "\\n").replace("\"", "\\\"")
    if is_vibe:
        btn_style = "background-color: #000; color: #00FF00; border: 2px solid #00FF00; box-shadow: 4px 4px 0px #00FF00; font-family: 'Space Mono', monospace; border-radius: 0px;"
        btn_text = "SAVE THIS DRIP"
    else:
        btn_style = "background-color: #f0f0f0; color: #333; border-radius: 8px; border: 1px solid #ccc; font-family: 'Archivo';"
        btn_text = "Copy Recipe"
        
    components.html(
        f"""
        <style>@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600&family=Space+Mono:wght@700&display=swap');</style>
        <script>
        function copyToClipboard() {{
            const str = "{escaped_text}";
            const el = document.createElement('textarea');
            el.value = str; document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el);
            const btn = document.getElementById("copyBtn"); btn.innerText = "COPIED!"; setTimeout(() => {{ btn.innerText = "{btn_text}"; }}, 2000);
        }}
        </script>
        <button id="copyBtn" onclick="copyToClipboard()" style="{btn_style} padding: 10px 20px; font-size: 14px; cursor: pointer; width: 100%; font-weight: 700; text-transform: uppercase;">{btn_text}</button>
        """, height=60
    )

def speak_text_button(text, is_vibe):
    escaped_text = text.replace("\n", " ").replace("\"", "'")
    if is_vibe:
        btn_play = "background-color: #000; color: #00FF00; border: 2px solid #00FF00; box-shadow: 4px 4px 0px #00FF00; font-family: 'Space Mono', monospace; border-radius: 0px;"
        btn_stop = "background-color: #000; color: #FF00FF; border: 2px solid #FF00FF; box-shadow: 4px 4px 0px #FF00FF; font-family: 'Space Mono', monospace; border-radius: 0px;"
        txt_play = "▶ SPILL THE TEA"
        txt_stop = "⏹ MUTE"
    else:
        btn_play = "background-color: #ffffff; color: #000; border-radius: 8px; border: 1px solid #000; font-family: 'Archivo';"
        btn_stop = "background-color: #f0f0f0; color: #333; border-radius: 8px; border: 1px solid #ccc; font-family: 'Archivo';"
        txt_play = "▶ Read"
        txt_stop = "⏹ Stop"

    components.html(
        f"""
        <style>@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600&family=Space+Mono:wght@700&display=swap');</style>
        <script>
        var synth = window.speechSynthesis; var utterance = new SpeechSynthesisUtterance("{escaped_text}"); utterance.rate = 0.9;
        function play() {{ synth.cancel(); synth.speak(utterance); }}
        function stop() {{ synth.cancel(); }}
        </script>
        <div style="display: flex; gap: 15px; margin-top: 15px;">
            <button onclick="play()" style="{btn_play} flex: 1; padding: 10px 15px; font-size: 13px; cursor: pointer; font-weight: 700; text-transform: uppercase;">{txt_play}</button>
            <button onclick="stop()" style="{btn_stop} flex: 0 0 auto; padding: 10px 15px; font-size: 13px; cursor: pointer; font-weight: 700; text-transform: uppercase;">{txt_stop}</button>
        </div>
        """, height=70
    )

GLOBAL_DISHES = ["Shakshuka", "Pad Thai", "Chicken Tikka Masala", "Beef Wellington", "Bibimbap", "Moussaka", "Paella", "Ramen", "Tacos"]

# --- STATE ---
if "ingredients" not in st.session_state: st.session_state.ingredients = None
if "dish_name" not in st.session_state: st.session_state.dish_name = ""
if "recipe_data" not in st.session_state: st.session_state.recipe_data = None
if "trigger_search" not in st.session_state: st.session_state.trigger_search = False
if "toast_shown" not in st.session_state: st.session_state.toast_shown = False

# --- UI LAYOUT ---
c_title, c_surprise = st.columns([4, 1])
with c_title:
    if vibe_mode:
        st.title("SOUS") 
        st.caption("BRUH. STOP ORDERING TAKEOUT.") # <--- THE "BRUH" UPDATE
    else:
        st.title("Sous")
        st.caption("The adaptive kitchen co-pilot.")

with c_surprise:
    st.write("") 
    st.write("") 
    if st.button("🎲 Surprise Me", use_container_width=True):
        st.session_state.dish_name = random.choice(GLOBAL_DISHES)
        st.session_state.trigger_search = True

# INPUT
with st.form("input_form"):
    col1, col2 = st.columns([4, 1])
    with col1:
        val = st.session_state.dish_name if st.session_state.trigger_search else ""
        if vibe_mode:
            dish_input = st.text_input("What's living rent-free in your head?", value=val, placeholder="e.g. Carbonara (It slaps)...")
        else:
            dish_input = st.text_input("What are you craving?", value=val, placeholder="e.g. Carbonara...")
    with col2:
        servings = st.slider("Servings", 1, 8, 2)
    
    if vibe_mode:
        submitted = st.form_submit_button("🔥 BET / LET'S COOK", use_container_width=True)
    else:
        submitted = st.form_submit_button("Let's Cook", use_container_width=True)

# LOGIC
if submitted or st.session_state.trigger_search:
    final_dish = dish_input if submitted else st.session_state.dish_name
    if final_dish:
        st.session_state.dish_name = final_dish
        st.session_state.trigger_search = False
        st.session_state.ingredients = None
        st.session_state.recipe_data = None
        st.session_state.toast_shown = False
        
        with st.spinner(f"Loading Assets for: {final_dish}..."):
            prompt = f"""
            Dish: {final_dish} for {servings} people.
            Task: Break down ingredients into exactly 2 categories.
            OUTPUT JSON STRUCTURE ONLY:
            {{ "core": ["Ing 1", "Ing 2"], "character": ["Ing 3", "Ing 4"] }}
            RULES: 1. Core = Non-negotiables. 2. Character = Spices/Herbs. 3. No Nulls.
            """
            data = robust_api_call(prompt)
            if isinstance(data, dict): st.session_state.ingredients = data
            else: st.error(f"System Failure. Details: {data}")

# DASHBOARD
if st.session_state.ingredients:
    if not st.session_state.toast_shown:
        if vibe_mode:
            st.toast("W. WE ARE SO BACK.", icon="🟩")
        else:
            st.toast("Mise en place ready.", icon="🧑‍🍳")
        st.session_state.toast_shown = True

    data = st.session_state.ingredients
    data_lower = {k.lower(): v for k, v in data.items()}
    raw_core = data_lower.get('core') or data_lower.get('must_haves') or []
    raw_char = data_lower.get('character') or data_lower.get('soul') or []
    if not raw_core and not raw_char:
        all_lists = [v for v in data.values() if isinstance(v, list)]
        if len(all_lists) > 0: raw_core = all_lists[0]
        if len(all_lists) > 1: raw_char = all_lists[1]
    
    list_core = clean_list(raw_core)
    list_character = clean_list(raw_char)

    st.divider()
    
    # Dynamic Headers
    if vibe_mode:
        h_core = "> THE GOATS (NO CAP / REQUIRED)"
        h_char = "> THE RIZZ (FLAVOR DRIP)"
    else:
        h_core = "🧱 The Core (Non-Negotiables)"
        h_char = "✨ Flavor & Substitutes"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{h_core}**")
        core_checks = [st.checkbox(str(i), True, key=f"c_{x}") for x, i in enumerate(list_core)]
    with c2:
        st.markdown(f"**{h_char}**")
        st.caption("*(Uncheck if you are delulu)*")
        character_avail = [i for x, i in enumerate(list_character) if st.checkbox(str(i), True, key=f"ch_{x}")]
        character_missing = [i for i in list_character if i not in character_avail]

    st.write("")
    
    if all(core_checks) and list_core:
        if vibe_mode:
            btn_gen = "🚀 FULL SEND (GENERATE RECIPE)"
        else:
            btn_gen = "Generate Chef's Recipe"
            
        if st.button(btn_gen, type="primary", use_container_width=True):
            all_missing = character_missing
            confirmed = list_core + character_avail
            with st.spinner("Cooking..."):
                
                # --- DYNAMIC PROMPTING (THE BRAIN) ---
                if vibe_mode:
                    # GEN Z PERSONA
                    final_prompt = f"""
                    Act as 'Chef Z', a chaotic Gen Z food influencer.
                    Dish: {st.session_state.dish_name} ({servings} servings).
                    Context: Confirmed: {confirmed}. Missing: {all_missing}.
                    
                    MANDATORY SLANG TO USE:
                    - Rizz (Flavor/Charisma)
                    - No Cap (Truth)
                    - Bussin (Tastes good)
                    - Bet (Yes/Okay)
                    - Glow-up (Cooking process)
                    - Era (e.g., In my spicy era)
                    - Serving (Plating)
                    - Slaps (Good)
                    - Sus (If missing ingredients)
                    - Delulu (If user thinks they can cook without basics)
                    - Ghosting (If flavor is missing)
                    
                    OUTPUT JSON:
                    {{
                        "meta": {{ "prep_time": "15m", "cook_time": "30m", "difficulty": "Valid" }},
                        "pivot_strategy": "Explain strategy using slang (e.g. 'We are entering our savory era').",
                        "ingredients_list": ["Item 1", "Item 2"],
                        "steps": ["Step 1...", "Step 2..."],
                        "chef_tip": "A savage pro tip (e.g. 'Don't be a simp for salt')."
                    }}
                    """
                else:
                    # MICHELIN PERSONA (DEFAULT)
                    final_prompt = f"""
                    Act as 'Sous', a Michelin-star home chef.
                    Dish: {st.session_state.dish_name} ({servings} servings).
                    Context: Confirmed: {confirmed}. Missing: {all_missing}.
                    
                    TONE: Professional, structured, encouraging.
                    
                    OUTPUT JSON:
                    {{
                        "meta": {{ "prep_time": "15 mins", "cook_time": "30 mins", "difficulty": "Medium" }},
                        "pivot_strategy": "Explain pivot strategy clearly.",
                        "ingredients_list": ["Item 1", "Item 2"],
                        "steps": ["Step 1...", "Step 2..."],
                        "chef_tip": "A professional tip."
                    }}
                    """

                r_data = robust_api_call(final_prompt)
                if isinstance(r_data, dict): st.session_state.recipe_data = r_data
                else: st.error("System Overload.")

    elif not list_core: 
        if vibe_mode:
             st.error("⚠️ BRUH. IT'S GIVING EMPTY. GO TOUCH GRASS & BUY FOOD.")
        else:
             st.error("ERROR: No ingredients found.")
    else: 
        if vibe_mode:
            st.error("💀 NAH. YOU NEED THE OGs. STOP BEING DELULU.")
        else:
            st.error("CRITICAL: Missing Core Ingredients.")

# RECIPE CARD
if st.session_state.recipe_data:
    r = st.session_state.recipe_data
    st.divider()
    st.markdown(f"## {st.session_state.dish_name.upper()}")
    m1, m2, m3 = st.columns(3)
    m1.metric("PREP", r['meta'].get('prep_time', '--'))
    m2.metric("COOK", r['meta'].get('cook_time', '--'))
    m3.metric("LEVEL", r['meta'].get('difficulty', '--'))
    
    pivot_msg = r.get('pivot_strategy', '')
    show_strategy = True
    if not pivot_msg or "full pantry" in pivot_msg.lower() or "no missing" in pivot_msg.lower(): show_strategy = False

    if show_strategy:
        with st.container(border=True):
            if vibe_mode: st.markdown(f"**VIBE CHECK**")
            else: st.markdown(f"**STRATEGY**")
            st.info(pivot_msg)
    
    c_ing, c_step = st.columns([1, 2])
    with c_ing:
        with st.container(border=True):
            if vibe_mode: st.markdown("**THE LOOT DROP**")
            else: st.markdown("**INVENTORY**")
            for item in r.get('ingredients_list', []): st.markdown(f"- {item}")
                
    with c_step:
        with st.container(border=True):
            if vibe_mode: st.markdown("**THE TUTORIAL**")
            else: st.markdown("**EXECUTION**")
            for idx, step in enumerate(r.get('steps', [])):
                clean_step = re.sub(r'^[\d\.\s\*\-]+', '', step)
                st.markdown(f"**{idx+1}.** {clean_step}")
            st.markdown("---")
            if vibe_mode: st.caption(f"**CHEAT CODE:** {r.get('chef_tip', '')}")
            else: st.caption(f"**SECRET:** {r.get('chef_tip', '')}")
            
            # AUDIO
            speech_text = f"Recipe for {st.session_state.dish_name}. "
            if show_strategy: speech_text += f"Strategy: {pivot_msg}. "
            speech_text += "Instructions: "
            for s in r.get('steps', []):
                clean = re.sub(r'^[\d\.\s\*\-]+', '', s)
                speech_text += f"{clean}. "
            speak_text_button(speech_text, vibe_mode)

    st.write("")
    
    share_text = f"DISH: {st.session_state.dish_name}\n\n"
    if show_strategy: share_text += f"STRATEGY: {pivot_msg}\n\n"
    share_text += "INGREDIENTS:\n"
    for i in r.get('ingredients_list', []): share_text += f"- {i}\n"
    share_text += "\nINSTRUCTIONS:\n"
    for i, s in enumerate(r.get('steps', [])): 
        clean_step = re.sub(r'^[\d\.\s\*\-]+', '', s)
        share_text += f"{i+1}. {clean_step}\n"
    share_text += f"\nSECRET: {r.get('chef_tip', '')}"
    
    a1, a2 = st.columns(2)
    with a1:
        encoded_wa = urllib.parse.quote(share_text)
        # Dynamic WA Button
        if vibe_mode:
            st.markdown(f"""<a href="https://wa.me/?text={encoded_wa}" target="_blank" style="text-decoration: none;"><button style="width: 100%; background-color: #000; color: #00FF00; border: 2px solid #00FF00; box-shadow: 4px 4px 0px #00FF00; font-family: 'Space Mono'; padding: 10px; font-weight: 700; cursor: pointer; text-transform: uppercase;">💬 SPILL THE TEA (WA)</button></a>""", unsafe_allow_html=True)
        else:
            st.link_button("💬 Share Recipe on WhatsApp", f"https://wa.me/?text={encoded_wa}", use_container_width=True)
        
    with a2:
        if st.button("🔄 Start New Dish", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
    st.write("")
    st.markdown("### SAVE DATA")
    copy_to_clipboard_button(share_text, vibe_mode)

# --- FOOTER ---
st.markdown('<div class="footer">Powered by Gemini</div>', unsafe_allow_html=True)