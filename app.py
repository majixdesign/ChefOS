import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re
import time
import random

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sous", page_icon="🍽️", layout="wide")

# --- 1. DESIGN SYSTEM (CSS INJECTION) ---
# This mimics the "Simple Home Edit" aesthetic: 
# - Archivo for UI text
# - Playfair Display for Headings
# - Minimalist Black/White styling
st.markdown("""
    <style>
        /* Import Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@300;400;600&family=Playfair+Display:wght@700&display=swap');

        /* Global Font Reset */
        html, body, [class*="css"] {
            font-family: 'Archivo', sans-serif;
            color: #1a1a1a;
        }

        /* Title Styling (Serif, Elegant) */
        h1 {
            font-family: 'Playfair Display', serif !important;
            font-weight: 700 !important;
            font-size: 4rem !important;
            color: #000000 !important;
            margin-bottom: 0rem !important;
        }
        
        /* Subheader/Caption Styling */
        .stCaption {
            font-size: 1.1rem !important;
            color: #666 !important;
            font-family: 'Archivo', sans-serif !important;
        }

        /* Input Fields */
        .stTextInput input {
            font-family: 'Archivo', sans-serif;
            border-radius: 8px;
            padding: 12px;
        }

        /* Primary Button (Let's Cook) - Black & Bold */
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
            background-color: #000000 !important;
            color: #ffffff !important;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            font-family: 'Archivo', sans-serif;
            transition: all 0.3s ease;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
            background-color: #333333 !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* Surprise Me Button */
        button[kind="secondary"] {
            border: 1px solid #e0e0e0;
            color: #333;
            border-radius: 8px;
            font-weight: 500;
        }

        /* Footer Styling */
        .footer {
            position: fixed;
            bottom: 10px;
            right: 10px;
            font-size: 0.8rem;
            color: #ccc;
            font-family: 'Archivo', sans-serif;
        }

        /* Checkbox Size */
        div[data-testid="stCheckbox"] label span {
            font-size: 1.1rem;
        }
        
        /* Remove Default Streamlit Chrome */
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

# --- DYNAMIC MODEL SELECTOR ---
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

# --- HELPER: DATA SANITIZER ---
def extract_items(data):
    """Recursively extracts strings from nested JSON."""
    items = []
    if isinstance(data, dict):
        for v in data.values(): items.extend(extract_items(v))
    elif isinstance(data, list):
        for item in data: items.extend(extract_items(item))
    elif isinstance(data, str):
        items.append(data)
    elif data is not None:
        items.append(str(data))
    return items

# --- GLOBAL DISHES (For 'Surprise Me') ---
GLOBAL_DISHES = [
    "Shakshuka", "Pad Thai", "Chicken Tikka Masala", "Beef Wellington", "Bibimbap",
    "Moussaka", "Paella", "Ramen", "Tacos al Pastor", "Coq au Vin",
    "Gnocchi Sorrentina", "Butter Chicken", "Pho", "Falafel Wrap", "Risotto",
    "Jerk Chicken", "Nasi Goreng", "Pierogi", "Ceviche", "Mapo Tofu",
    "Arepas", "Bunny Chow", "Katsudon", "Feijoada", "Osso Buco"
]

# --- STATE MANAGEMENT ---
if "ingredients" not in st.session_state: st.session_state.ingredients = None
if "dish_name" not in st.session_state: st.session_state.dish_name = ""
if "generated_recipe" not in st.session_state: st.session_state.generated_recipe = False
if "trigger_search" not in st.session_state: st.session_state.trigger_search = False

# --- 3. UI LAYOUT ---

# HEADER
c_title, c_surprise = st.columns([4, 1])
with c_title:
    st.title("Sous")
    st.caption("Your smart kitchen co-pilot.")
with c_surprise:
    st.write("") # Spacer
    st.write("") 
    if st.button("🎲 Surprise Me", use_container_width=True):
        st.session_state.dish_name = random.choice(GLOBAL_DISHES)
        st.session_state.trigger_search = True

# INPUT FORM
with st.form("input_form"):
    col1, col2 = st.columns([4, 1])
    with col1:
        # If surprise button was clicked, pre-fill the value
        val = st.session_state.dish_name if st.session_state.trigger_search else ""
        dish_input = st.text_input("What are you craving today?", value=val, placeholder="e.g. Carbonara, Pancakes, Biryani...")
    with col2:
        servings = st.slider("Servings", 1, 8, 2)
    
    # "Let's Cook" button
    submitted = st.form_submit_button("Let's Cook", use_container_width=True)

# LOGIC: Handle Submit OR Surprise Trigger
if submitted or st.session_state.trigger_search:
    # Use input if submitted, or session state if surprise triggered
    final_dish = dish_input if submitted else st.session_state.dish_name
    
    if final_dish:
        st.session_state.dish_name = final_dish
        # Reset trigger so it doesn't loop
        st.session_state.trigger_search = False
        st.session_state.ingredients = None
        st.session_state.recipe_text = None
        st.session_state.generated_recipe = False
        
        with st.status(f"👨‍🍳 Analyzing {final_dish}...", expanded=True) as status:
            prompt = f"""
            I want to cook {final_dish} for {servings} people. 
            Assume the most authentic, world-class version.
            
            Break down ingredients into a JSON object with these 3 keys:
            1. "must_haves": The Non-Negotiables.
               - Heroes (Protein, Carb, Veg)
               - Structural Essentials (Fat/Oil, Water, Salt, Yeast)
               - Critical Bases (Onions for Curry, Flour for Baking)
            2. "soul": Flavor builders (Herbs, Cheese, Wine, Chilies, Cream, Ghee).
            3. "foundation": Shelf-stable seasonings (Spices, Sauces, Vinegars, Sugar).
            
            Return ONLY valid JSON. Simple strings only.
            """
            try:
                time.sleep(0.5)
                response = model.generate_content(prompt)
                
                text = response.text.replace("```json", "").replace("```", "").strip()
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    clean_json = match.group(0)
                    data = json.loads(clean_json)
                    normalized_data = {k.lower(): v for k, v in data.items()}
                    st.session_state.ingredients = normalized_data
                    status.update(label="Mise en place ready.", state="complete", expanded=False)
                else:
                    st.error("Sous couldn't read the recipe book. Try again.")
                    status.update(label="Error", state="error")
            except Exception as e:
                status.update(label="Connection Error", state="error")
                st.error(f"Error: {e}")

# --- 4. OUTPUT DASHBOARD ---
if st.session_state.ingredients:
    data = st.session_state.ingredients
    list_must = extract_items(data.get('must_haves') or data.get('must_have'))
    list_soul = extract_items(data.get('soul') or data.get('flavor'))
    list_foundation = extract_items(data.get('foundation') or data.get('pantry'))

    st.divider()
    st.markdown(f"### Inventory: {st.session_state.dish_name}")
    st.caption("Check what you have. We'll adapt the rest.")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("**🧱 The Non-Negotiables**")
        if not list_must: st.write("*(None)*")
        must_haves = [st.checkbox(str(i), True, key=f"m_{idx}") for idx, i in enumerate(list_must)]
        
    with c2:
        st.markdown("**✨ The Soul**")
        if not list_soul: st.write("*(None)*")
        soul_missing = []
        soul_available = []
        for idx, i in enumerate(list_soul):
            if st.checkbox(str(i), True, key=f"s_{idx}"): soul_available.append(i)
            else: soul_missing.append(i)
                
    with c3:
        st.markdown("**🏗️ The Pantry**")
        if not list_foundation: st.write("*(None)*")
        pantry_missing = []
        pantry_available = []
        for idx, i in enumerate(list_foundation):
            if st.checkbox(str(i), True, key=f"p_{idx}"): pantry_available.append(i)
            else: pantry_missing.append(i)

    st.write("")
    
    if all(must_haves) and list_must:
        all_missing = soul_missing + pantry_missing
        confirmed = list_must + soul_available + pantry_available
        
        # Use a secondary form logic or just a button. 
        # Since we are outside the main form, a button works fine.
        if st.button("Reveal Chef's Recipe", type="primary", use_container_width=True):
            st.session_state.generated_recipe = True
            
        if st.session_state.get("generated_recipe"):
            if "recipe_text" not in st.session_state or st.session_state.generated_recipe:
                with st.spinner("👨‍🍳 Drafting the plan..."):
                    final_prompt = f"""
                    Act as 'Sous', a world-class chef.
                    Dish: {st.session_state.dish_name} ({servings} servings).
                    
                    INVENTORY:
                    - CONFIRMED: {confirmed} (Use EXACTLY)
                    - MISSING: {all_missing} (Do NOT use)
                    
                    Structure:
                    1. **The Vision:** A brief, appetizing description.
                    2. **The Strategy:** How we adapt to missing items.
                    3. **Mise en Place:** The confirmed ingredient list.
                    4. **The Execution:** Step-by-step instructions.
                    5. **Chef's Secret:** A pro tip.
                    """
                    try:
                        resp = model.generate_content(final_prompt)
                        st.session_state.recipe_text = resp.text
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.divider()
            if all_missing: st.info(f"💡 **Adapting recipe for:** {', '.join(all_missing)}")
            
            if st.session_state.recipe_text:
                st.markdown(st.session_state.recipe_text)
                st.divider()
                if st.button("🔄 Start New Dish", use_container_width=True):
                    st.session_state.clear()
                    st.rerun()
    elif not list_must:
        st.error("⚠️ AI Error: No ingredients found.")
    else:
        st.error("🛑 Missing Essentials. Cannot cook safely.")

# --- FOOTER ---
st.markdown('<div class="footer">Powered by Gemini</div>', unsafe_allow_html=True)