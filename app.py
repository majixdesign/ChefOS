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
from PIL import Image

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
    
    @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    @keyframes glitch { 0% { text-shadow: 4px 4px 0px #FF00FF; } 50% { text-shadow: -4px -4px 0px #00FFFF; } 100% { text-shadow: 4px 4px 0px #FF00FF; } }
    </style>
""", unsafe_allow_html=True)

if not vibe_mode:
    # === SYSTEM MODE ===
    st.markdown("""
        <style>
            html, body, [class*="css"] { font-family: 'Archivo', sans-serif; }
            h1 { font-family: 'Archivo', sans-serif !important; font-weight: 700; letter-spacing: -0.02em; }
            div.stButton > button { background-color: #000 !important; color: #fff !important; border-radius: 8px; font-weight: 600; border: none; }
        </style>
    """, unsafe_allow_html=True)
else:
    # === VIBE MODE ===
    st.markdown("""
        <style>
            .stApp { background-color: #000; background-image: radial-gradient(#222 1px, transparent 0); background-size: 30px 30px; }
            html, body, [class*="css"], p, label, div, span { font-family: 'Space Mono', monospace !important; color: #ffffff !important; }
            h1 { font-family: 'Space Mono', monospace !important; font-weight: 700 !important; text-transform: uppercase; font-size: 4rem !important; color: #fff !important; animation: glitch 0.5s infinite steps(1); }
            
            /* BUTTONS: Neon Green */
            div.stButton > button {
                background-color: #000 !important; color: #00FF00 !important; border: 3px solid #00FF00 !important;
                border-radius: 0px !important; font-family: 'Space Mono', monospace !important; font-weight: 700;
                box-shadow: 6px 6px 0px #00FF00 !important; transition: all 0.1s; text-transform: uppercase;
            }
            div.stButton > button:hover { transform: translate(2px, 2px); box-shadow: 2px 2px 0px #FF00FF !important; border-color: #FF00FF !important; color: #FF00FF !important; }

            input { background: #000 !important; border: 2px solid #fff !important; border-bottom: 5px solid #fff !important; color: #00FF00 !important; border-radius: 0px !important; font-family: 'Space Mono', monospace !important; }
            
            /* EXPANDER & UPLOAD FIX - FORCED HIGH CONTRAST */
            div[data-testid="stExpander"] {
                background-color: #000000 !important; border: 2px solid #00FF00 !important; border-radius: 0px !important; color: #00FF00 !important;
            }
            div[data-testid="stExpander"] details summary {
                color: #00FF00 !important; font-family: 'Space Mono', monospace !important;
            }
            div[data-testid="stExpander"] details summary svg {
                fill: #00FF00 !important; /* The Arrow */
            }
            div[data-testid="stFileUploader"] {
                color: #00FF00 !important;
            }
            div[data-testid="stFileUploader"] section {
                background-color: #111 !important; border: 1px dashed #00FF00 !important;
            }
            div[data-testid="stFileUploader"] button {
                 border: 1px solid #00FF00 !important; color: #00FF00 !important;
            }

            div[data-testid="stToast"] { background-color: #000 !important; border: 2px solid #00FF00 !important; color: #fff !important; opacity: 1 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background: #3300FF; overflow: hidden; white-space: nowrap; border-bottom: 3px solid #000; margin-top: -30px; margin-bottom: 20px;">
            <div style="display: inline-block; animation: marquee 10s linear infinite; font-family: 'Space Mono', monospace; font-weight: 700; font-size: 1.2rem; color: #FFFFFF !important; padding: 10px;">
                NO CAP /// JUST COOKING /// IT'S GIVING MICHELIN /// MAIN CHARACTER ENERGY /// NO CAP /// JUST COOKING /// IT'S GIVING MICHELIN
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 3. CONFIGURATION & LOGIC ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    try: api_key = st.secrets["GOOGLE_API_KEY"]
    except: st.error("🔑 Google API Key missing."); st.stop()

genai.configure(api_key=api_key)

def get_model():
    try: return genai.GenerativeModel("gemini-1.5-flash") # Using Flash for Vision + Speed
    except: return genai.GenerativeModel("models/gemini-1.5-flash")
model = get_model()

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

def robust_api_call(prompt, image=None):
    try:
        config = {"response_mime_type": "application/json"}
        if image: response = model.generate_content([prompt, image], generation_config=config)
        else: response = model.generate_content(prompt, generation_config=config)
        return json.loads(response.text)
    except:
        try:
            # Fallback if strict JSON fails
            if image: response = model.generate_content([prompt, image])
            else: response = model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match: return json.loads(match.group(0))
        except Exception as e: return f"ERROR: {str(e)}"

# --- STATE MANAGEMENT ---
if "ingredients" not in st.session_state: st.session_state.ingredients = None
if "dish_name" not in st.session_state: st.session_state.dish_name = ""
if "recipe_data" not in st.session_state: st.session_state.recipe_data = None
if "trigger_search" not in st.session_state: st.session_state.trigger_search = False
if "toast_shown" not in st.session_state: st.session_state.toast_shown = False
if "suggested_dishes" not in st.session_state: st.session_state.suggested_dishes = []
if "scan_done" not in st.session_state: st.session_state.scan_done = False

# --- UI LAYOUT ---
c_title, c_surprise = st.columns([4, 1])
with c_title:
    if vibe_mode: st.title("SOUS"); st.caption("BRUH. STOP ORDERING TAKEOUT.") 
    else: st.title("Sous"); st.caption("The adaptive kitchen co-pilot.")

with c_surprise:
    st.write(""); st.write("") 
    if st.button("🎲 Surprise Me", use_container_width=True):
        st.session_state.dish_name = random.choice(["Shakshuka", "Pad Thai", "Tacos", "Ramen", "Bibimbap"])
        st.session_state.trigger_search = True
        st.session_state.suggested_dishes = []

# --- 1. VISION INPUT ---
with st.container():
    label = "📸 SCAN FRIDGE / PANTRY (AI VISION)" if vibe_mode else "📸 Scan Ingredients"
    
    with st.expander(label, expanded=not st.session_state.scan_done):
        uploaded_file = st.file_uploader("Upload photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        
        if uploaded_file:
            st.image(uploaded_file, width=200)
            if st.button("👀 Analyze & Suggest Dishes"):
                with st.spinner("Scanning pantry..."):
                    img = Image.open(uploaded_file)
                    prompt = """
                    Analyze this image. Identify available ingredients.
                    Based on them, SUGGEST 3 distinct dish names I could cook.
                    
                    OUTPUT STRICT JSON ONLY: 
                    { "ingredients_detected": ["item1", "item2"], "suggestions": ["Dish A", "Dish B", "Dish C"] }
                    """
                    data = robust_api_call(prompt, img)
                    
                    if isinstance(data, dict):
                        # 1. Populate Text Input
                        detected = ", ".join(data.get("ingredients_detected", []))
                        st.session_state.dish_name = detected 
                        # 2. Save Suggestions
                        st.session_state.suggested_dishes = data.get("suggestions", [])
                        st.session_state.scan_done = True
                        st.rerun()

# --- 2. SUGGESTION CHIPS (PERSISTENT) ---
if st.session_state.suggested_dishes:
    if vibe_mode: st.markdown("### 💡 FOUND THESE. CLICK TO COOK:")
    else: st.markdown("### 💡 Suggestions based on scan:")
    
    cols = st.columns(3)
    for i, dish in enumerate(st.session_state.suggested_dishes):
        with cols[i]:
            # Each button triggers a rerun with the new dish name
            if st.button(f"🥘 {dish}", use_container_width=True, key=f"sug_{i}"):
                st.session_state.dish_name = dish
                st.session_state.trigger_search = True
                st.session_state.suggested_dishes = [] # Clear suggestions to declutter
                st.rerun()

# --- 3. TEXT INPUT ---
with st.form("input_form"):
    c1, c2 = st.columns([4, 1])
    with c1:
        val = st.session_state.dish_name
        ph = "What's living rent-free in your head?" if vibe_mode else "What are you craving?"
        dish_input = st.text_input(ph, value=val, placeholder="e.g. Carbonara...")
    with c2:
        servings = st.slider("Servings", 1, 8, 2)
    
    label = "🔥 BET / LET'S COOK" if vibe_mode else "Let's Cook"
    submitted = st.form_submit_button(label, use_container_width=True)

# --- 4. CORE LOGIC ---
if submitted or st.session_state.trigger_search:
    final_dish = dish_input if submitted else st.session_state.dish_name
    if final_dish:
        st.session_state.dish_name = final_dish
        st.session_state.trigger_search = False
        st.session_state.ingredients = None
        st.session_state.recipe_data = None
        st.session_state.toast_shown = False
        
        with st.spinner(f"Loading Assets for: {final_dish}..."):
            # Step 1: Breakdown Ingredients
            prompt = f"""
            Dish/Ingredients: "{final_dish}" for {servings} people.
            Task: If input is ingredients, pick a dish name. Break into Core/Character.
            JSON: {{ "dish_name": "Name", "core": ["Ing1"], "character": ["Ing2"] }}
            """
            data = robust_api_call(prompt)
            if isinstance(data, dict): 
                st.session_state.ingredients = data
                if "dish_name" in data: st.session_state.dish_name = data["dish_name"]
            else: st.error("System Failure.")

# --- 5. DASHBOARD ---
if st.session_state.ingredients:
    if not st.session_state.toast_shown:
        msg = "WE ARE LOCKED IN. 🔒" if vibe_mode else "Mise en place ready."
        st.toast(msg, icon="🎒"); st.session_state.toast_shown = True

    data = st.session_state.ingredients
    list_core = clean_list(data.get('core', []))
    list_character = clean_list(data.get('character', []))

    st.divider()
    h_core = "> THE GOATS (NO CAP)" if vibe_mode else "🧱 Core Ingredients"
    h_char = "> THE RIZZ (FLAVOR)" if vibe_mode else "✨ Flavor & Substitutes"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{h_core}**")
        core_checks = [st.checkbox(str(i), True, key=f"c_{x}") for x, i in enumerate(list_core)]
    with c2:
        st.markdown(f"**{h_char}**")
        character_avail = [i for x, i in enumerate(list_character) if st.checkbox(str(i), True, key=f"ch_{x}")]

    st.write("")
    
    if all(core_checks) and list_core:
        btn_gen = "🚀 FULL SEND (GENERATE RECIPE)" if vibe_mode else "Generate Chef's Recipe"
        if st.button(btn_gen, type="primary", use_container_width=True):
            with st.spinner("Cooking..."):
                # --- RECIPE GENERATION ---
                confirmed = list_core + character_avail
                persona = "Chef Z (Gen Z slang)" if vibe_mode else "Michelin Chef"
                
                final_prompt = f"""
                Act as {persona}. Dish: {st.session_state.dish_name} ({servings} servings).
                Ingredients: {confirmed}.
                
                OUTPUT JSON:
                {{
                    "meta": {{ "prep": "15m", "cook": "30m", "level": "Medium" }},
                    "vibe_check": "A short, fun intro.",
                    "ingredients": ["Item 1", "Item 2"],
                    "tldr_steps": ["Step 1 (Short)", "Step 2 (Short)", "Step 3 (Short)"],
                    "full_steps": ["Detailed Step 1...", "Detailed Step 2..."],
                    "tip": "Pro tip."
                }}
                """
                r_data = robust_api_call(final_prompt)
                if isinstance(r_data, dict): st.session_state.recipe_data = r_data

# --- 6. RECIPE CARD ---
if st.session_state.recipe_data:
    r = st.session_state.recipe_data
    st.divider()
    st.markdown(f"## {st.session_state.dish_name.upper()}")
    
    # META
    c1, c2, c3, c4 = st.columns([1,1,1,2])
    c1.metric("PREP", r['meta'].get('prep', '--'))
    c2.metric("COOK", r['meta'].get('cook', '--'))
    c3.metric("LEVEL", r['meta'].get('level', '--'))
    
    # TL;DR TOGGLE
    with c4:
        st.write("") # Spacer
        is_tldr = st.toggle("⚡ SPEED RUN (TL;DR)", value=True if vibe_mode else False)

    # VIBE CHECK
    if r.get('vibe_check'):
        st.info(r['vibe_check'])

    # INGREDIENTS & STEPS
    c_ing, c_step = st.columns([1, 2])
    with c_ing:
        st.markdown("**INVENTORY**")
        for item in r.get('ingredients', []): st.markdown(f"- {item}")
            
    with c_step:
        st.markdown("**THE TUTORIAL**")
        
        # LOGIC: Show TLDR or Full
        steps_to_show = r.get('tldr_steps', []) if is_tldr else r.get('full_steps', [])
        
        for idx, step in enumerate(steps_to_show):
            clean_step = re.sub(r'^[\d\.\s\*\-]+', '', step)
            st.markdown(f"**{idx+1}.** {clean_step}")
        
        st.markdown("---")
        st.caption(f"**SECRET:** {r.get('tip', '')}")

    st.markdown('<div style="text-align: center; color: #666; font-size: 12px; margin-top: 50px;">Powered by Gemini 1.5</div>', unsafe_allow_html=True)