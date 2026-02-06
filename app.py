import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re
import time

# --- HIDE BRANDING ---
st.set_page_config(page_title="Sous", page_icon="🍳", layout="wide")
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            div[data-testid="stCheckbox"] label span {
                font-size: 1.1rem;
            }
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
    try:
        my_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        preferred_order = [
            "models/gemini-1.5-flash",
            "models/gemini-2.0-flash", 
            "models/gemini-1.5-pro"
        ]
        for p in preferred_order:
            if p in my_models: return genai.GenerativeModel(p)
        return genai.GenerativeModel(my_models[0]) if my_models else genai.GenerativeModel("models/gemini-1.5-flash")
    except:
        return genai.GenerativeModel("models/gemini-1.5-flash")

model = get_working_model()

# 2. Header
st.title("Sous 🍳")
st.caption("Your smart kitchen co-pilot. (Powered by Gemini)")

# 3. Input
with st.form("input_form"):
    col1, col2 = st.columns([3, 1])
    with col1:
        dish = st.text_input("What are we cooking?", placeholder="e.g. Mutton Biryani...", label_visibility="collapsed")
    with col2:
        servings = st.slider("Servings", 1, 8, 2)
    submitted = st.form_submit_button("Start Prep", use_container_width=True)

if "ingredients" not in st.session_state: st.session_state.ingredients = None
if "dish_name" not in st.session_state: st.session_state.dish_name = ""
if "generated_recipe" not in st.session_state: st.session_state.generated_recipe = False
if "raw_response" not in st.session_state: st.session_state.raw_response = ""

# 4. Logic
if submitted and dish:
    st.session_state.dish_name = dish
    st.session_state.ingredients = None
    st.session_state.recipe_text = None
    st.session_state.generated_recipe = False
    
    with st.status("👨‍🍳 Sous is organizing the kitchen...", expanded=True) as status:
        
        prompt = f"""
        I want to cook {dish} for {servings} people. 
        If the dish name is generic (like "Biryani"), assume the most popular authentic version but label the protein clearly.
        
        Break down ingredients into a JSON object. Use EXACTLY these 3 keys (lowercase):
        1. "must_haves": The absolute core items (Meat, Rice, Pasta, Main Veg).
        2. "soul": Flavor builders (Fresh Herbs, Whole Spices, Ghee, Saffron, Wine, Cheese).
        3. "foundation": The pantry basics (Onions, Tomatoes, Ginger-Garlic, Oil, Spices like Turmeric/Chili/Cumin, Salt).
        
        Return ONLY valid JSON.
        """
        
        try:
            time.sleep(0.5)
            response = model.generate_content(prompt)
            st.session_state.raw_response = response.text # Save for debugging
            
            # --- BULLETPROOF JSON CLEANER ---
            # 1. Strip Markdown
            text = response.text.replace("```json", "").replace("```", "").strip()
            # 2. Find the JSON object using Regex (ignores extra chatty text)
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                clean_json = match.group(0)
                data = json.loads(clean_json)
                
                # 3. Normalize Keys (Handle Case Sensitivity)
                normalized_data = {}
                for k, v in data.items():
                    normalized_data[k.lower()] = v
                
                st.session_state.ingredients = normalized_data
                status.update(label="Prep List Ready!", state="complete", expanded=False)
            else:
                st.error("Could not find ingredient data. See Debug below.")
                status.update(label="Error", state="error")
            
        except Exception as e:
            status.update(label="Connection Error", state="error")
            st.error(f"Error: {e}")

# 5. Dashboard
if st.session_state.ingredients:
    data = st.session_state.ingredients
    
    # Safe Getters (handle missing keys gracefully)
    list_must = data.get('must_haves') or data.get('must_have') or []
    list_soul = data.get('soul') or data.get('flavor') or []
    list_foundation = data.get('foundation') or data.get('pantry') or []

    st.divider()
    st.subheader(f"Inventory: {st.session_state.dish_name}")
    st.caption("Uncheck anything you are missing. We will adapt.")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.info("🧱 **The Vitals**")
        if not list_must: st.write("*(No items found)*")
        must_haves = [st.checkbox(i, True, key=f"m_{i}") for i in list_must]
        
    with c2:
        st.warning("✨ **The Soul**")
        if not list_soul: st.write("*(No items found)*")
        soul_missing = []
        soul_available = []
        for i in list_soul:
            if st.checkbox(i, True, key=f"s_{i}"):
                soul_available.append(i)
            else:
                soul_missing.append(i)
                
    with c3:
        st.success("🏗️ **The Foundation**")
        if not list_foundation: st.write("*(No items found)*")
        pantry_missing = []
        pantry_available = []
        for i in list_foundation:
            if st.checkbox(i, True, key=f"p_{i}"):
                pantry_available.append(i)
            else:
                pantry_missing.append(i)

    st.write("") 
    if all(must_haves) and list_must:
        gen_btn = st.button("Generate Chef's Recipe", type="primary", use_container_width=True)
        if gen_btn: st.session_state.generated_recipe = True
            
        if st.session_state.get("generated_recipe"):
            if "recipe_text" not in st.session_state or gen_btn:
                with st.spinner("👨‍🍳 Chef is planning the strategy..."):
                    
                    confirmed_inventory = list_must + soul_available + pantry_available
                    all_missing = soul_missing + pantry_missing
                    
                    final_prompt = f"""
                    Act as 'Sous', a warm, expert home chef.
                    Create a recipe for {st.session_state.dish_name} ({servings} servings).
                    
                    CRITICAL INVENTORY CONTEXT:
                    1. User CONFIRMED they have: {confirmed_inventory}. USE THESE EXACTLY.
                    2. User is MISSING: {all_missing}.
                    
                    Structure:
                    1. **The Strategy:** A quick opening note about how we will handle the missing items (if any).
                    2. **The Mise en Place:** List the exact ingredients to use.
                    3. **The Cook:** Step-by-step, descriptive instructions. Focus on sensory cues (smell, color).
                    4. **Chef's Tip:** One pro tip at the end.
                    """
                    try:
                        resp = model.generate_content(final_prompt)
                        st.session_state.recipe_text = resp.text
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.markdown("---")
            if all_missing: st.info(f"💡 **Adapting for:** {', '.join(all_missing)}")
            
            if st.session_state.recipe_text:
                st.markdown(st.session_state.recipe_text)
                st.markdown("---")
                col_copy, col_reset = st.columns(2)
                with c_copy:
                    with st.expander("📋 Copy Recipe"):
                        st.code(st.session_state.recipe_text, language="markdown")
                with c_reset:
                    if st.button("🔄 Start Over", use_container_width=True):
                        st.session_state.clear()
                        st.rerun()
    elif not list_must:
        st.error("⚠️ Data Error: The AI didn't return any ingredients. Please try again.")
    else:
        st.error("🛑 You are missing a Vital Ingredient. We can't cook this dish without it.")

# --- DEBUG SECTION (Only visible if something breaks) ---
with st.expander("🛠️ Debug Data (For Developer)"):
    st.write("Raw Model Response:")
    st.code(st.session_state.raw_response)
    if st.session_state.ingredients:
        st.write("Parsed Data:")
        st.json(st.session_state.ingredients)