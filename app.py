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

# --- 1. DESIGN SYSTEM ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1a1a1a;
        }

        h1 {
            font-family: 'Playfair Display', serif !important;
            font-weight: 700 !important;
            font-size: 3rem !important;
            color: #000000 !important;
        }
        
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
            background-color: #000000 !important;
            color: #ffffff !important;
            border: none;
            padding: 0.8rem 1.5rem;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            border-radius: 8px;
            font-size: 1rem;
        }

        .footer {
            position: fixed;
            bottom: 15px;
            right: 15px;
            font-size: 0.8rem;
            color: #aaa;
            font-family: 'Inter', sans-serif;
            text-align: right;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURATION ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        st.error("🔑 Google API Key missing. Please check Secrets.")
        st.stop()

genai.configure(api_key=api_key)

def get_working_model():
    try:
        my_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        preferred_order = ["models/gemini-1.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-pro"]
        for p in preferred_order:
            if p in my_models: return genai.GenerativeModel(p)
        return genai.GenerativeModel(my_models[0]) if my_models else genai.GenerativeModel("models/gemini-1.5-flash")
    except:
        return genai.GenerativeModel("models/gemini-1.5-flash")

model = get_working_model()

# --- 3. HELPER FUNCTIONS ---

def extract_items(data):
    """Bouncer: Removes junk data."""
    items = []
    IGNORE_LIST = ["none", "null", "n/a", "undefined", "", "missing", "optional"]
    
    if isinstance(data, dict):
        for v in data.values(): items.extend(extract_items(v))
    elif isinstance(data, list):
        for item in data: items.extend(extract_items(item))
    elif isinstance(data, str) or isinstance(data, int) or isinstance(data, float):
        clean_text = str(data).strip()
        if len(clean_text) > 2 and clean_text.lower() not in IGNORE_LIST:
            items.append(clean_text)
            
    return items

def generate_with_retry(prompt, retries=1):
    """Retries the AI call if JSON parsing fails."""
    for attempt in range(retries + 1):
        try:
            response = model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group(0))
        except Exception:
            time.sleep(1)
            continue
    return None

def copy_to_clipboard_button(text):
    escaped_text = text.replace("\n", "\\n").replace("\"", "\\\"")
    components.html(
        f"""
        <script>
        function copyToClipboard() {{
            const str = "{escaped_text}";
            const el = document.createElement('textarea');
            el.value = str;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            const btn = document.getElementById("copyBtn");
            btn.innerText = "✅ Copied!";
            setTimeout(() => {{ btn.innerText = "📄 Copy to Clipboard"; }}, 2000);
        }}
        </script>
        <button id="copyBtn" onclick="copyToClipboard()" style="
            background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 8px; 
            padding: 10px 20px; font-family: sans-serif; font-size: 14px; 
            cursor: pointer; width: 100%; font-weight: 600; color: #333;">
            📄 Copy to Clipboard
        </button>
        """,
        height=50
    )

GLOBAL_DISHES = [
    "Shakshuka", "Pad Thai", "Chicken Tikka Masala", "Beef Wellington", "Bibimbap",
    "Moussaka", "Paella", "Ramen", "Tacos al Pastor", "Coq au Vin",
    "Gnocchi Sorrentina", "Butter Chicken", "Pho", "Falafel Wrap", "Risotto"
]

# --- STATE ---
if "ingredients" not in st.session_state: st.session_state.ingredients = None
if "dish_name" not in st.session_state: st.session_state.dish_name = ""
if "recipe_data" not in st.session_state: st.session_state.recipe_data = None
if "trigger_search" not in st.session_state: st.session_state.trigger_search = False
if "toast_shown" not in st.session_state: st.session_state.toast_shown = False

# --- 4. UI LAYOUT ---

c_title, c_surprise = st.columns([4, 1])
with c_title:
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
        dish_input = st.text_input("What are you craving?", value=val, placeholder="e.g. Carbonara, Pancakes...")
    with col2:
        servings = st.slider("Servings", 1, 8, 2)
    submitted = st.form_submit_button("Let's Cook", use_container_width=True)

# ANALYSIS LOGIC
if submitted or st.session_state.trigger_search:
    final_dish = dish_input if submitted else st.session_state.dish_name
    if final_dish:
        st.session_state.dish_name = final_dish
        st.session_state.trigger_search = False
        st.session_state.ingredients = None
        st.session_state.recipe_data = None
        st.session_state.toast_shown = False
        
        with st.spinner(f"👨‍🍳 Organizing the kitchen for {final_dish}..."):
            
            prompt = f"""
            Dish: {final_dish} for {servings} people.
            
            Task: Break down ingredients into exactly 2 categories.
            
            1. "core": THE PHYSICS & STRUCTURE (Non-Negotiable)
               - The Main Ingredients (Meat, Rice, Pasta, Eggs for Omelet).
               - The Physics Essentials (Cooking Oil/Fat, Salt, Water).
               - The Flavor Base (Onions/Garlic for Curry, Canned Tomato for Pasta).
               - WITHOUT THESE, THE DISH FAILS.
               
            2. "character": THE FLAVOR & SOUL (Negotiable/Swappable)
               - Fresh Herbs (Parsley, Cilantro).
               - Dried Spices (Cumin, Paprika).
               - Acids & Garnishes (Lemon, Cheese toppings).
            
            Output: JSON only. No "None" values.
            """
            data = generate_with_retry(prompt)
            
            if data:
                st.session_state.ingredients = data
            else:
                st.error("Sous couldn't read the recipe book. Please try again.")

# --- DASHBOARD ---
if st.session_state.ingredients:
    if not st.session_state.toast_shown:
        st.toast("Mise en place ready!", icon="🧑‍🍳")
        st.session_state.toast_shown = True

    data = st.session_state.ingredients
    data = {k.lower(): v for k, v in data.items()}
    
    list_core = extract_items(data.get('core') or data.get('must_haves'))
    list_character = extract_items(data.get('character') or data.get('soul'))

    st.divider()
    st.subheader(f"Inventory: {st.session_state.dish_name}")
    st.caption("Uncheck what is missing. We will adapt.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("🧱 **The Core (Non-Negotiables)**")
        core_checks = [st.checkbox(str(i), True, key=f"c_{x}") for x, i in enumerate(list_core)]
    with c2:
        st.markdown("✨ **The Character (Negotiable)**")
        character_avail = [i for x, i in enumerate(list_character) if st.checkbox(str(i), True, key=f"ch_{x}")]
        character_missing = [i for i in list_character if i not in character_avail]

    st.write("")
    
    if all(core_checks) and list_core:
        if st.button("Generate Chef's Recipe", type="primary", use_container_width=True):
            
            all_missing = character_missing
            confirmed = list_core + character_avail
            
            with st.spinner("👨‍🍳 Drafting the plan..."):
                final_prompt = f"""
                Act as 'Sous', a Michelin-star home chef.
                Dish: {st.session_state.dish_name} ({servings} servings).
                
                CONTEXT:
                - CONFIRMED INGREDIENTS: {confirmed}
                - MISSING INGREDIENTS: {all_missing}
                
                TASK: Create a structured recipe.
                
                OUTPUT FORMAT (JSON):
                {{
                    "meta": {{ "prep_time": "15 mins", "cook_time": "30 mins", "difficulty": "Medium" }},
                    "pivot_strategy": "Explain how we adapt to missing items. If nothing missing, say 'Full Pantry'",
                    "ingredients_list": ["Item 1", "Item 2"],
                    "steps": ["Step 1...", "Step 2..."],
                    "chef_tip": "A pro tip."
                }}
                """
                r_data = generate_with_retry(final_prompt)
                
                if r_data:
                    st.session_state.recipe_data = r_data
                else:
                    st.error("Chef is overwhelmed. Please try again.")

    elif not list_core:
        st.error("⚠️ AI Error: No ingredients found. Please try again.")
    else:
        st.error("🛑 You are missing Core Ingredients. This dish will not work physically without them.")

# --- RECIPE CARD DISPLAY ---
if st.session_state.recipe_data:
    r = st.session_state.recipe_data
    
    st.divider()
    
    # 1. HEADER
    st.markdown(f"## 🥘 {st.session_state.dish_name}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Prep Time", r['meta'].get('prep_time', '--'))
    m2.metric("Cook Time", r['meta'].get('cook_time', '--'))
    m3.metric("Difficulty", r['meta'].get('difficulty', '--'))
    
    # 2. PIVOT (Conditional Logic)
    pivot_msg = r.get('pivot_strategy', '')
    show_strategy = True
    
    # Logic to HIDE strategy if pantry is full
    if not pivot_msg or "full pantry" in pivot_msg.lower() or "everything needed" in pivot_msg.lower() or "no missing" in pivot_msg.lower():
        show_strategy = False

    if show_strategy:
        with st.container(border=True):
            st.markdown(f"**💡 Chef's Strategy**")
            st.info(pivot_msg)
    
    # 3. CONTENT
    c_ing, c_step = st.columns([1, 2])
    
    with c_ing:
        with st.container(border=True):
            st.markdown("**🛒 Mise en Place**")
            for item in r.get('ingredients_list', []):
                st.markdown(f"- {item}")
                
    with c_step:
        with st.container(border=True):
            st.markdown("**🔥 Instructions**")
            for idx, step in enumerate(r.get('steps', [])):
                st.markdown(f"**{idx+1}.** {step}")
            
            st.markdown("---")
            st.caption(f"✨ **Chef's Secret:** {r.get('chef_tip', '')}")

    # 4. ACTION BAR
    st.write("")
    
    # --- CONSTRUCT TEXT FOR SHARING ---
    # Smart logic: If strategy is hidden, don't include it in text
    share_text = f"🥘 {st.session_state.dish_name}\n\n"
    if show_strategy:
        share_text += f"💡 STRATEGY: {pivot_msg}\n\n"
    
    share_text += "🛒 INGREDIENTS:\n"
    for i in r.get('ingredients_list', []): share_text += f"- {i}\n"
    
    share_text += "\n🔥 INSTRUCTIONS:\n"
    for i, s in enumerate(r.get('steps', [])): share_text += f"{i+1}. {s}\n"
    
    share_text += f"\n✨ Chef's Secret: {r.get('chef_tip', '')}"
    
    # --- BUTTONS ---
    a1, a2 = st.columns(2)
    with a1:
        # Full Recipe for WhatsApp
        encoded_wa = urllib.parse.quote(share_text)
        st.link_button("💬 Share Recipe on WhatsApp", f"https://wa.me/?text={encoded_wa}", use_container_width=True)
        
    with a2:
        if st.button("🔄 Start New Dish", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
    # 5. COPY
    st.write("")
    st.markdown("### Save Recipe")
    copy_to_clipboard_button(share_text)

# --- FOOTER ---
st.markdown('<div class="footer">Powered by Gemini</div>', unsafe_allow_html=True)