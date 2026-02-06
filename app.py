import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re
import time
import random
import urllib.parse

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sous", page_icon="🍳", layout="wide")

# --- 1. DESIGN SYSTEM (Clean, Modern, Card-Based) ---
st.markdown("""
    <style>
        /* Import Inter Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Playfair+Display:wght@700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1a1a1a;
        }

        /* Title */
        h1 {
            font-family: 'Playfair Display', serif !important;
            font-weight: 700 !important;
            font-size: 3rem !important;
            color: #000000 !important;
        }
        
        /* Card Styling (Containers) */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
            # background-color: #f9f9f9;
            # border-radius: 12px;
            # padding: 1rem;
        }

        /* Buttons */
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
            background-color: #000000 !important;
            color: #ffffff !important;
            border: none;
            padding: 0.6rem 1.2rem;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            border-radius: 8px;
        }

        /* Metrics (Prep Time etc) */
        div[data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
            font-family: 'Inter', sans-serif;
        }

        /* Footer */
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
    submitted = st.form_submit_button("Start Prep", use_container_width=True)

# ANALYSIS LOGIC
if submitted or st.session_state.trigger_search:
    final_dish = dish_input if submitted else st.session_state.dish_name
    if final_dish:
        st.session_state.dish_name = final_dish
        st.session_state.trigger_search = False
        st.session_state.ingredients = None
        st.session_state.recipe_data = None
        
        with st.status(f"👨‍🍳 Analyzing {final_dish}...", expanded=True) as status:
            # PROMPT UPDATE: Force Physics Essentials into Must Haves
            prompt = f"""
            Dish: {final_dish} for {servings} people.
            
            Task: Break down ingredients into 3 categories.
            1. "must_haves": 
               - Main Proteins/Carbs/Veg.
               - THE PHYSICS ESSENTIALS: You MUST include Cooking Oil/Fat, Salt, and Water here if the dish needs them.
            2. "soul": Fresh Herbs, Aromatics, Cheese, Acids (Lemon/Vinegar).
            3. "pantry": Dried Spices, Sauces, Shelf-stable items.
            
            Output: JSON only. No "None" values.
            """
            try:
                time.sleep(0.5)
                response = model.generate_content(prompt)
                text = response.text.replace("```json", "").replace("```", "").strip()
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    st.session_state.ingredients = json.loads(match.group(0))
                    status.update(label="Mise en place ready.", state="complete", expanded=False)
                else:
                    st.error("Could not parse ingredients.")
                    status.update(label="Error", state="error")
            except Exception as e:
                status.update(label="Connection Error", state="error")

# --- DASHBOARD ---
if st.session_state.ingredients:
    data = st.session_state.ingredients
    # Normalize keys
    data = {k.lower(): v for k, v in data.items()}
    
    list_must = extract_items(data.get('must_haves') or data.get('must_have'))
    list_soul = extract_items(data.get('soul') or data.get('flavor'))
    list_pantry = extract_items(data.get('pantry') or data.get('foundation'))

    st.divider()
    st.subheader(f"Inventory: {st.session_state.dish_name}")
    st.caption("Uncheck what is missing. We will adapt the recipe.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**🔴 Non-Negotiables**")
        must_haves = [st.checkbox(i, True, key=f"m_{x}") for x, i in enumerate(list_must)]
    with c2:
        st.markdown("**🟡 Soul & Fresh**")
        soul_avail = [i for x, i in enumerate(list_soul) if st.checkbox(i, True, key=f"s_{x}")]
        soul_missing = [i for i in list_soul if i not in soul_avail]
    with c3:
        st.markdown("**🟢 Pantry & Spices**")
        pantry_avail = [i for x, i in enumerate(list_pantry) if st.checkbox(i, True, key=f"p_{x}")]
        pantry_missing = [i for i in list_pantry if i not in pantry_avail]

    st.write("")
    
    # COOK BUTTON
    if all(must_haves) and list_must:
        if st.button("Generate Adaptive Recipe", type="primary", use_container_width=True):
            
            all_missing = soul_missing + pantry_missing
            confirmed = list_must + soul_avail + pantry_avail
            
            with st.spinner("👨‍🍳 Chef is pivoting the strategy..."):
                final_prompt = f"""
                Act as 'Sous', a Michelin-star home chef.
                Dish: {st.session_state.dish_name} ({servings} servings).
                
                CONTEXT:
                - CONFIRMED INGREDIENTS: {confirmed} (Use these EXACTLY)
                - MISSING INGREDIENTS: {all_missing}
                
                TASK: Create a structured recipe that SPECIFICALLY adapts to the missing items.
                
                OUTPUT FORMAT (JSON):
                {{
                    "meta": {{ "prep_time": "15 mins", "cook_time": "30 mins", "difficulty": "Medium" }},
                    "pivot_strategy": "A 1-2 sentence explanation of how we are adapting (e.g. 'Since we are missing tomatoes, we will use extra caramelized onions...'). If nothing missing, say 'We have everything needed.'",
                    "ingredients_list": ["Item 1", "Item 2"],
                    "steps": ["Step 1...", "Step 2..."],
                    "chef_tip": "A pro tip."
                }}
                """
                try:
                    resp = model.generate_content(final_prompt)
                    clean_resp = resp.text.replace("```json", "").replace("```", "").strip()
                    # JSON regex to be safe
                    match = re.search(r'\{.*\}', clean_resp, re.DOTALL)
                    if match:
                        st.session_state.recipe_data = json.loads(match.group(0))
                except Exception as e:
                    st.error("Chef is overwhelmed. Please try again.")

    elif not list_must:
        st.error("⚠️ AI Error: No ingredients found.")
    else:
        st.error("🛑 You are missing Non-Negotiables (Physics Essentials). Cannot cook safely.")

# --- RECIPE CARD DISPLAY ---
if st.session_state.recipe_data:
    r = st.session_state.recipe_data
    
    st.divider()
    
    # 1. HEADER & META
    st.markdown(f"## 🥘 {st.session_state.dish_name}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Prep Time", r['meta'].get('prep_time', '--'))
    m2.metric("Cook Time", r['meta'].get('cook_time', '--'))
    m3.metric("Difficulty", r['meta'].get('difficulty', '--'))
    
    # 2. THE PIVOT (The Core Value)
    pivot_msg = r.get('pivot_strategy', '')
    if pivot_msg and "everything needed" not in pivot_msg.lower():
        with st.container(border=True):
            st.markdown(f"**💡 Chef's Pivot Strategy**")
            st.info(pivot_msg)
    
    # 3. INGREDIENTS & STEPS
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

    # 4. ACTION BAR (Copy & Share)
    st.write("")
    a1, a2 = st.columns(2)
    with a1:
        # WhatsApp
        recipe_str = f"Cooking {st.session_state.dish_name}!\n\nStrategy: {pivot_msg}"
        encoded = urllib.parse.quote(recipe_str)
        st.link_button("💬 Share Pivot on WhatsApp", f"https://wa.me/?text={encoded}", use_container_width=True)
    with a2:
        if st.button("🔄 Start New Dish", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
    # 5. COPY SECTION (The functional copy)
    with st.expander("📋 Copy Full Recipe Text"):
        # Construct plain text for copying
        copy_text = f"{st.session_state.dish_name}\n\nSTRATEGY: {pivot_msg}\n\nINGREDIENTS:\n"
        for i in r.get('ingredients_list', []): copy_text += f"- {i}\n"
        copy_text += "\nINSTRUCTIONS:\n"
        for i, s in enumerate(r.get('steps', [])): copy_text += f"{i+1}. {s}\n"
        
        st.code(copy_text, language=None)


# --- FOOTER ---
st.markdown('<div class="footer">Powered by Gemini</div>', unsafe_allow_html=True)