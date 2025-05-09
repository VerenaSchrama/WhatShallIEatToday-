# utils.py
import openai
import streamlit as st

# 👇 Debug print om te controleren of de sleutel geladen wordt
print("🔐 OpenAI key found:", st.secrets.get("OPENAI_API_KEY", "❌ NOT FOUND"))

openai.api_key = st.secrets["OPENAI_API_KEY"]
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

@st.cache_resource
def load_llm_chain():
    llm = ChatOpenAI(model_name="gpt-4", temperature=0.2)

    prompt_template = PromptTemplate(
        input_variables=["phase", "goal", "diet", "question"],
        template="""
You are a personalized cycle nutrition assistant.
The user is currently in the {phase} phase of her menstrual cycle.
Her main focus is {goal}.
She follows these dietary preferences: {diet}.

Given this information, answer her question below in a clear, practical, and warm tone.
Be specific when you recommend foods.
Structure your answer with a list of bullet points when that clarifies.

When it makes sense based on the chat history, end your answer with a suggestion to give a recipe suggestion, a meal plan for for example breakfast, lunch or dinner or with specific questions.

Question: {question}

Answer:
"""
    )

    return LLMChain(llm=llm, prompt=prompt_template)

def reset_session():
    keys_defaults = {
        "phase": None,
        "cycle_length": None,
        "dietary_preferences": [],
        "support_goal": None,
        "last_period": None,
        "second_last_period": None,
        "personalization_completed": False,
        "chat_history": []
    }
    for key, default in keys_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

def add_to_chat_history(role, message):
    if st.session_state.chat_history is None:
        st.session_state.chat_history = []
    st.session_state.chat_history.append((role, message))