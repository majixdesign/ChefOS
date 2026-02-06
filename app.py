# Force Update: Dynamic Model Selector
import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import time

# --- HIDE STREAMLIT BRANDING ---
st.set_page_config(page_title="Sous", page_icon="🍳", layout="centered")
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# 1. Configuration
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
    """
    Asks Google what models are actually enabled for this API Key 
    and picks the best available one.
    """
    try:
        # Get the real list from your account
        my_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priority: We prefer Flash because it's fast/cheap
        # But we will take WHATEVER is in the list.
        preferred_order = [
            "models/gemini-1.5-flash",
            "models/gemini-2.0-flash",       # <--- Your account has this!
            "models/gemini-2.0-flash-lite",
            "models/gemini-1.5-pro",
            "models/gemini-pro"
        ]
        
        # 1. Look for a match
        for p in preferred_order:
            if p in my_models:
                return genai.GenerativeModel(p), p
        
        # 2. If no match, take the first valid one
        if my_models:
            return genai.GenerativeModel(my_models[0]), my_models[0]
            
        # 3. Hail Mary
        return genai.GenerativeModel("models/gemini-2.0-flash"), "models/gemini-2.0-flash"

    except Exception as e:
        # Fallback if listing fails
        return genai.GenerativeModel("models/gemini-2.0-flash"), "Default (2.0)"

model, model_name = get_working_model()

# 2. Header
st.title("Sous 🍳")
st.caption(f"Your smart kitchen co-pilot. (Engine: {model_name.replace('models/', '')})")

# 3. Input
with st.form("input_form"):
    col1, col2 = st.columns([3, 1])
    with col1:
        dish = st.text_input("What are we cooking?", placeholder="e.g. Mutton Biryani...", label_visibility="collapsed")
    with col2:
        servings = st.slider("Servings", 1, 8, 2)
    submitted = st.form_submit_button("Let's Cook", use_container_width=True)

if "ingredients" not in st.session_state: st.session_state.ingredients = None
if "dish_name" not in st.session_state: st.session_state.dish_name = ""
if "generated_recipe" not in st.session_state: st.session_state.generated_recipe = False

# 4. Logic
if submitted and dish:
    st.session_state.dish_name = dish
    st.session_state.ingredients = None
    st.session_state.recipe_text = None
    st.session_state.generated_recipe = False
    
    with st.status("👨‍🍳 Sous is analyzing...", expanded=True) as status:
        
        prompt = f"""
        I want to cook {dish} for {servings} people. 
        Break down the ingredients into a JSON object with these 3 keys:
        
        1. 'heroes': List 3-4 CORE ingredients (e.g. Meat, Main Veg, Special Rice).
        2. 'variables': List 5-6 SECONDARY flavor ingredients (Herbs, Spices, Dairy). DO NOT list alternative meats here.
        3. 'pantry': List basic items (Oil, Salt, Water, Onions, Ginger-Garlic Paste, Chili Powder, Turmeric).
        
        Return ONLY valid JSON.
        """
        
        try:
            # Sleep slightly to be polite
            time.sleep(0.5)
            response = model.generate_content(prompt)
            cleaned = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            st.session_state.ingredients = data
            status.update(label="Ingredients Found!", state="complete", expanded=False)
            
        except Exception as e:
            status.update(label="Connection Error", state="error")
            st.error(f"Error: {e}")

# 5. Output
if st.session_state.ingredients:
    data = st.session_state.ingredients
    st.divider()
    st.subheader(f"Inventory: {st.session_state.dish_name}")
    
    col_heroes, col_vars = st.columns(2)
    with col_heroes:
        st.info("🛡️ **Heroes** (The Core)")
        heroes = [st.checkbox(i, True, key=f"h_{i}") for i in data.get('heroes', [])]
    with col_vars:
        st.warning("🎨 **Flavor Builders** (Check what you have)")
        missing = []
        available_vars = []
        for i in data.get('variables', []):
            if st.checkbox(i, value=True, key=f"v_{i}"):
                available_vars.append(i)
            else:
                missing.append(i)

    st.write("") 
    if all(heroes):
        gen_btn = st.button("Generate Chef's Recipe", type="primary", use_container_width=True)
        if gen_btn: st.session_state.generated_recipe = True
            
        if st.session_state.get("generated_recipe"):
            if "recipe_text" not in st.session_state or gen_btn:
                with st.spinner("👨‍🍳 Chef is cooking up the plan..."):
                    
                    confirmed_list = data.get('heroes', []) + data.get('pantry', []) + available_vars
                    
                    final_prompt = f"""
                    Act as 'Sous', a warm, encouraging, Michelin-star home chef.
                    Create a recipe for {st.session_state.dish_name} ({servings} servings).
                    
                    CRITICAL INVENTORY:
                    1. User HAS: {confirmed_list}. USE THESE EXACTLY.
                    2. User is MISSING: {missing}.
                    
                    Structure:
                    1. **The Fix:** Reassure the user about the missing items.
                    2. **The Recipe:** Step-by-step, descriptive, mouth-watering instructions. Bold the ingredients.
                    """
                    try:
                        resp = model.generate_content(final_prompt)
                        st.session_state.recipe_text = resp.text
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.markdown("---")
            if missing: st.success(f"💡 **Adaptations:** {', '.join(missing)}")
            if st.session_state.recipe_text:
                st.markdown(st.session_state.recipe_text)
                st.markdown("---")
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("📋 Copy"):
                        st.code(st.session_state.recipe_text, language="markdown")
                with c2:
                    if st.button("🔄 Reset", use_container_width=True):
                        st.session_state.clear()
                        st.rerun()
    else:
        st.error("🛑 Need Heroes!")