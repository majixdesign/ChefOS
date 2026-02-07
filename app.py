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
# We place the toggle in the top corner first so we can load CSS based on it.
c_ph, c_toggle = st.columns([6, 1])
with c_toggle:
    vibe_mode = st.toggle("✨ Vibe Mode")

# --- 2. DYNAMIC DESIGN SYSTEM ---
# Common Imports
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@300;400;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&display=swap');
    </style>
""", unsafe_allow_html=True)

if not vibe_mode:
    # === SYSTEM MODE (The Architect) ===
    st.markdown("""
        <style>
            html, body, [class*="css"] { font-family: 'Archivo', sans-serif; color: #1a1a1a; }
            
            /* Typography */
            h1 { font-family: 'Archivo', sans-serif !important; font-weight: 700; letter-spacing: -0.02em; color: #000; }
            
            /* Buttons (Systemic) */
            div[data-testid="stForm"] button {
                background-color: #000 !important; color: #fff !important; border-radius: 8px;
                text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; border: none;
            }
            
            /* Dark Mode Overrides for System */
            @media (prefers-color-scheme: dark) {
                h1 { color: #e0e0e0 !important; }
                div[data-testid="stForm"] button { background-color: #fff !important; color: #000 !important; }
            }
        </style>
    """, unsafe_allow_html=True)

else:
    # === VIBE MODE (The Cosmic) ===
    st.markdown("""
        <style>
            /* Global Gradient Background */
            .stApp {
                background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
                background-attachment: fixed;
            }
            
            html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; color: #e0e0e0; }
            
            /* Typography (Neon Glow) */
            h1 { 
                font-family: 'Space Grotesk', sans-serif !important; 
                font-weight: 700; 
                background: linear-gradient(to right, #b993d6, #8ca6db);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 0 20px rgba(138, 43, 226, 0.3);
            }
            
            h2, h3 { color: #fff !important; }
            
            /* Glassmorphism Containers */
            div[data-testid="stVerticalBlock"] > div {
                /* Subtle glass effect on containers if possible, mainly affects text readability */
            }
            
            /* Buttons (Pill Shape + Gradient) */
            div[data-testid="stForm"] button {
                background: linear-gradient(90deg, #8E2DE2, #4A00E0) !important;
                color: #fff !important;
                border-radius: 50px !important; /* The Pill */
                font-family: 'Space Grotesk';
                font-weight: 600;
                border: 1px solid rgba(255,255,255,0.2);
                box-shadow: 0 4px 15px rgba(74, 0, 224, 0.4);
            }
            div[data-testid="stForm"] button:hover {
                transform: scale(1.02);
                box-shadow: 0 6px 20px rgba(74, 0, 224, 0.6);
            }
            
            /* Inputs (Glass) */
            input {
                background: rgba(255, 255, 255, 0.05) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                color: #fff !important;
                border-radius: 12px !important;
            }
        </style>
    """, unsafe_allow_html=True)

# --- 3. CONFIGURATION & LOGIC (Unchanged) ---
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
    # Dynamic styling for the component
    if is_vibe:
        btn_style = "background: linear-gradient(90deg, #8E2DE2, #4A00E0); color: white; border-radius: 50px; border: none; font-family: 'Space Grotesk';"
    else:
        btn_style = "background-color: #f0f0f0; color: #333; border-radius: 8px; border: 1px solid #ccc; font-family: 'Archivo';"
        
    components.html(
        f"""
        <style>@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600&family=Space+Grotesk:wght@600&display=swap');</style>
        <script>
        function copyToClipboard() {{
            const str = "{escaped_text}";
            const el = document.createElement('textarea');
            el.value = str; document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el);
            const btn = document.getElementById("copyBtn"); btn.innerText = "✨ Copied!"; setTimeout(() => {{ btn.innerText = "📄 Copy Recipe"; }}, 2000);
        }}
        </script>
        <button id="copyBtn" onclick="copyToClipboard()" style="{btn_style} padding: 10px 20px; font-size: 14px; cursor: pointer; width: 100%; font-weight: 600;">📄 Copy Recipe</button>
        """, height=50
    )

def speak_text_button(text, is_vibe):
    escaped_text = text.replace("\n", " ").replace("\"", "'")
    if is_vibe:
        btn_play = "background: linear-gradient(90deg, #00c6ff, #0072ff); color: white; border-radius: 50px; border: none; font-family: 'Space Grotesk';"
        btn_stop = "background: rgba(255,255,255,0.1); color: white; border-radius: 50px; border: 1px solid rgba(255,255,255,0.2); font-family: 'Space Grotesk';"
    else:
        btn_play = "background-color: #ffffff; color: #000; border-radius: 8px; border: 1px solid #000; font-family: 'Archivo';"
        btn_stop = "background-color: #f0f0f0; color: #333; border-radius: 8px; border: 1px solid #ccc; font-family: 'Archivo';"

    components.html(
        f"""
        <style>@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600&family=Space+Grotesk:wght@600&display=swap');</style>
        <script>
        var synth = window.speechSynthesis; var utterance = new SpeechSynthesisUtterance("{escaped_text}"); utterance.rate = 0.9;
        function play() {{ synth.cancel(); synth.speak(utterance); }}
        function stop() {{ synth.cancel(); }}
        </script>
        <div style="display: flex; gap: 10px; margin-top: 15px;">
            <button onclick="play()" style="{btn_play} flex: 1; padding: 8px 15px; font-size: 13px; cursor: pointer; font-weight: 600;">▶️ Read</button>
            <button onclick="stop()" style="{btn_stop} flex: 0 0 auto; padding: 8px 15px; font-size: 13px; cursor: pointer; font-weight: 600;">⏹️ Stop</button>
        </div>
        """, height=60
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
        st.title("Sous 🪐")
        st.caption("The cosmic kitchen co-pilot.")
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
        dish_input = st.text_input("What are you craving?", value=val, placeholder="e.g. Carbonara...")
    with col2:
        servings = st.slider("Servings", 1, 8, 2)
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
        
        with st.spinner(f"👨‍🍳 Organizing the kitchen for {final_dish}..."):
            prompt = f"Dish: {final_dish} for {servings}. Break into 'core' (Non-negotiable) and 'character' (Negotiable). JSON only."
            data = robust_api_call(prompt)
            if isinstance(data, dict): st.session_state.ingredients = data
            else: st.error("Sous couldn't read the recipe book.")

# DASHBOARD
if st.session_state.ingredients:
    if not st.session_state.toast_shown:
        st.toast("Mise en place ready!", icon="🧑‍🍳")
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
        h_core = "🧱 The Core (Non-Negotiables)"
        h_char = "✨ The Vibe (Substitutes)"
    else:
        h_core = "🧱 The Core (Non-Negotiables)"
        h_char = "✨ Flavor & Substitutes"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{h_core}**")
        core_checks = [st.checkbox(str(i), True, key=f"c_{x}") for x, i in enumerate(list_core)]
    with c2:
        st.markdown(f"**{h_char}**")
        st.caption("*(Uncheck to get an alternative)*")
        character_avail = [i for x, i in enumerate(list_character) if st.checkbox(str(i), True, key=f"ch_{x}")]
        character_missing = [i for i in list_character if i not in character_avail]

    st.write("")
    
    if all(core_checks) and list_core:
        if st.button("Generate Chef's Recipe", type="primary", use_container_width=True):
            all_missing = character_missing
            confirmed = list_core + character_avail
            with st.spinner("👨‍🍳 Drafting the plan..."):
                final_prompt = f"""
                Act as 'Sous'. Dish: {st.session_state.dish_name} ({servings} servings).
                Confirmed: {confirmed}. Missing: {all_missing}.
                JSON Output: {{ "meta": {{ "prep_time": "15m", "cook_time": "30m", "difficulty": "Easy" }}, "pivot_strategy": "Strategy...", "ingredients_list": ["list..."], "steps": ["step 1...", "step 2..."], "chef_tip": "Tip..." }}
                """
                r_data = robust_api_call(final_prompt)
                if isinstance(r_data, dict): st.session_state.recipe_data = r_data
                else: st.error("Chef is overwhelmed.")

    elif not list_core: st.error("⚠️ AI Error: No ingredients found.")
    else: st.error("🛑 You are missing Core Ingredients.")

# RECIPE CARD
if st.session_state.recipe_data:
    r = st.session_state.recipe_data
    st.divider()
    st.markdown(f"## 🥘 {st.session_state.dish_name}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Prep", r['meta'].get('prep_time', '--'))
    m2.metric("Cook", r['meta'].get('cook_time', '--'))
    m3.metric("Level", r['meta'].get('difficulty', '--'))
    
    pivot_msg = r.get('pivot_strategy', '')
    show_strategy = True
    if not pivot_msg or "full pantry" in pivot_msg.lower() or "no missing" in pivot_msg.lower(): show_strategy = False

    if show_strategy:
        with st.container(border=True):
            st.markdown(f"**💡 Strategy**")
            st.info(pivot_msg)
    
    c_ing, c_step = st.columns([1, 2])
    with c_ing:
        with st.container(border=True):
            st.markdown("**🛒 Mise en Place**")
            for item in r.get('ingredients_list', []): st.markdown(f"- {item}")
                
    with c_step:
        with st.container(border=True):
            st.markdown("**🔥 Instructions**")
            for idx, step in enumerate(r.get('steps', [])):
                clean_step = re.sub(r'^[\d\.\s\*\-]+', '', step)
                st.markdown(f"**{idx+1}.** {clean_step}")
            st.markdown("---")
            st.caption(f"✨ **Chef's Secret:** {r.get('chef_tip', '')}")
            
            # AUDIO
            speech_text = f"Recipe for {st.session_state.dish_name}. "
            if show_strategy: speech_text += f"Strategy: {pivot_msg}. "
            speech_text += "Instructions: "
            for s in r.get('steps', []):
                clean = re.sub(r'^[\d\.\s\*\-]+', '', s)
                speech_text += f"{clean}. "
            speak_text_button(speech_text, vibe_mode)

    st.write("")
    
    share_text = f"🥘 {st.session_state.dish_name}\n\n"
    if show_strategy: share_text += f"💡 STRATEGY: {pivot_msg}\n\n"
    share_text += "🛒 INGREDIENTS:\n"
    for i in r.get('ingredients_list', []): share_text += f"- {i}\n"
    share_text += "\n🔥 INSTRUCTIONS:\n"
    for i, s in enumerate(r.get('steps', [])): 
        clean_step = re.sub(r'^[\d\.\s\*\-]+', '', s)
        share_text += f"{i+1}. {clean_step}\n"
    share_text += f"\n✨ Chef's Secret: {r.get('chef_tip', '')}"
    
    a1, a2 = st.columns(2)
    with a1:
        encoded_wa = urllib.parse.quote(share_text)
        # Dynamic WA Button
        if vibe_mode:
            st.markdown(f"""<a href="https://wa.me/?text={encoded_wa}" target="_blank" style="text-decoration: none;"><button style="width: 100%; background: linear-gradient(90deg, #25D366, #128C7E); color: white; padding: 10px; border-radius: 50px; border: none; font-weight: 600; cursor: pointer;">💬 Share on WhatsApp</button></a>""", unsafe_allow_html=True)
        else:
            st.link_button("💬 Share Recipe on WhatsApp", f"https://wa.me/?text={encoded_wa}", use_container_width=True)
        
    with a2:
        if st.button("🔄 Start New Dish", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
    st.write("")
    st.markdown("### Save Recipe")
    copy_to_clipboard_button(share_text, vibe_mode)

# --- FOOTER ---
st.markdown('<div class="footer">Powered by Gemini</div>', unsafe_allow_html=True)