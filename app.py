import json
import os

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv


def configure_genai():
    # Load environment variables from .env
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Please update your .env file or environment."
        )

    genai.configure(api_key=api_key)


def parse_json_response(text: str):
    """
    Parse the model's response as JSON.
    Tries to be robust to accidental code fences.
    """
    raw = text.strip()

    # Handle ```json ... ``` or ``` ... ``` wrappers if present
    if raw.startswith("```"):
        # Remove leading ```json or ``` and trailing ```
        raw = raw.strip("`")
        # After stripping backticks, there may still be a language tag on the first line
        lines = raw.splitlines()
        if lines and lines[0].strip().lower().startswith("json"):
            lines = lines[1:]
        raw = "\n".join(lines).strip()

    return json.loads(raw)


def main():
    st.set_page_config(page_title="ChefOS")

    st.title("ChefOS")

    dish = st.text_input("What do you want to cook?", value="Butter Chicken")

    analyze_clicked = st.button("Analyze")

    if analyze_clicked:
        if not dish.strip():
            st.warning("Please enter a dish name before analyzing.")
            return

        try:
            configure_genai()
            model = genai.GenerativeModel("models/gemini-flash-latest")
        except Exception as e:
            st.error(f"Failed to configure AI: {e}")
            return

        prompt = (
            f"I want to cook {dish.strip()}.\n"
            "List the ingredients.\n"
            "Return a JSON object with 3 keys:\n"
            "  'heroes' (list of mandatory meats/veg),\n"
            "  'variables' (list of swappable items like cream/ghee),\n"
            "  'pantry' (list of basics like oil/salt).\n"
            "Return ONLY JSON."
        )

        with st.spinner("ChefOS is thinking..."):
            try:
                response = model.generate_content(prompt)
                ingredients = parse_json_response(response.text)
            except Exception as e:
                st.error(f"Failed to analyze dish: {e}")
                return

        # Persist ingredients and dish name so we can reuse them
        st.session_state["ingredients"] = ingredients
        st.session_state["dish_name"] = dish.strip()

    ingredients = st.session_state.get("ingredients")
    dish_name = st.session_state.get("dish_name", dish.strip())

    if ingredients:
        heroes = ingredients.get("heroes", [])
        variables = ingredients.get("variables", [])
        pantry = ingredients.get("pantry", [])

        missing_heroes = []
        missing_ingredients = []

        # Heroes with hard stop if any are missing
        if heroes:
            st.subheader("Heroes")
            for item in heroes:
                checked = st.checkbox(item, value=True, key=f"hero_{item}")
                if not checked:
                    missing_heroes.append(item)

        # Variables where we allow substitution
        if variables:
            st.subheader("Variables")
            for item in variables:
                checked = st.checkbox(item, value=True, key=f"variable_{item}")
                if not checked:
                    missing_ingredients.append(item)
                    st.info(f"⚠️ Missing {item}? No problem, I'll find a substitute.")

        if pantry:
            with st.expander("Pantry Items (Assumed)"):
                for item in pantry:
                    st.checkbox(item, value=True, key=f"pantry_{item}")

        # If any hero is missing, block recipe generation
        if missing_heroes:
            missing_str = ", ".join(missing_heroes)
            st.error(f"🛑 You need {missing_str} to make this dish. We can't proceed.")
            return

        # Final recipe generation step (only when heroes are all present)
        if st.button("Generate My Recipe"):
            missing_str = ", ".join(missing_ingredients) if missing_ingredients else "none"

            recipe_prompt = (
                f"The user is making {dish_name} but is missing: {missing_str}.\n"
                "Rewrite the recipe steps to compensate.\n"
                "Example: If missing Cream, suggest using Cashew paste or Milk + Butter.\n"
                "Structure the output as:\n"
                "1. 'The Fix': Explain how we are swapping the missing item.\n"
                "2. 'The Recipe': The full step-by-step instructions."
            )

            with st.spinner("ChefOS is writing your recipe..."):
                try:
                    configure_genai()
                    recipe_model = genai.GenerativeModel("models/gemini-flash-latest")
                    recipe_response = recipe_model.generate_content(recipe_prompt)
                    recipe_text = getattr(recipe_response, "text", str(recipe_response))
                except Exception as e:
                    st.error(f"Failed to generate recipe: {e}")
                    return

            st.subheader("Your Customized Recipe")
            st.markdown(recipe_text)


if __name__ == "__main__":
    main()
