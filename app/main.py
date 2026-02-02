import streamlit as st
import requests
import json

# Configuration
OLLAMA_HOST = "http://ollama:11434"
DEFAULT_MODEL = "gpt-oss:120b"

st.set_page_config(page_title="Tytan Chatbot", page_icon="🤖", layout="wide")

st.title("🤖 Tytan Chatbot (GPT-OSS 120B)")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        if response.status_code == 200:
            models = [m['name'] for m in response.json().get('models', [])]
            # Ensure our target model is in the list or set as default option
            if DEFAULT_MODEL not in models:
                 models.append(DEFAULT_MODEL) # Just in case it's not pulled yet, still show it
            
            selected_model = st.selectbox("Select Model", models, index=models.index(DEFAULT_MODEL) if DEFAULT_MODEL in models else 0)
        else:
            st.error("Could not fetch models from Ollama.")
            selected_model = DEFAULT_MODEL
    except Exception as e:
        st.error(f"Connection error: {e}")
        selected_model = DEFAULT_MODEL
    
    st.markdown("---")
    st.markdown("**User Info:**")
    st.markdown("- Model: `gpt-oss:120b`")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What is up?"):
    # Display user message in chat message container
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            payload = {
                "model": selected_model,
                "messages": st.session_state.messages,
                "stream": True
            }
            
            with requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, stream=True) as response:
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            data = json.loads(decoded_line)
                            if 'message' in data and 'content' in data['message']:
                                chunk = data['message']['content']
                                full_response += chunk
                                message_placeholder.markdown(full_response + "▌")
                            if data.get('done', False):
                                break
                    message_placeholder.markdown(full_response)
                else:
                    st.error(f"Error from Ollama: {response.status_code} - {response.text}")
                    full_response = "Error generating response."
        except Exception as e:
            st.error(f"An error occurred: {e}")
            full_response = f"Error: {e}"

    st.session_state.messages.append({"role": "assistant", "content": full_response})
