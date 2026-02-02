import streamlit as st
import requests
import json
import pandas as pd
import time
import plotly.express as px

st.set_page_config(page_title="Benchmark - Tytan Chatbot", page_icon="📊", layout="wide")

OLLAMA_HOST = "http://ollama:11434"

st.title("📊 Model Performance Benchmark")
st.markdown("Compare the speed and latency of your models on the current hardware (A100).")

# Fetch available models
try:
    response = requests.get(f"{OLLAMA_HOST}/api/tags")
    if response.status_code == 200:
        models = [m['name'] for m in response.json().get('models', [])]
    else:
        st.error("Could not fetch models.")
        models = []
except:
    st.error("Could not connect to Ollama.")
    models = []

if not models:
    st.stop()

# Benchmark Settings
with st.expander("Benchmark Settings", expanded=True):
    selected_models = st.multiselect("Select Models to Test", models, default=[m for m in models if 'gpt-oss' in m])
    prompt_text = st.text_area("Test Prompt", "Write a concise summary of the history of artificial intelligence (approx 200 words).", help="A longer prompt/response helps measure sustained throughput.")
    runs = st.number_input("Number of runs per model", min_value=1, max_value=5, value=1)

if st.button("Start Benchmark"):
    if not selected_models:
        st.error("Please select at least one model.")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_steps = len(selected_models) * runs
        current_step = 0
        
        for model in selected_models:
            for i in range(runs):
                status_text.text(f"Testing {model} (Run {i+1}/{runs})...")
                
                payload = {
                    "model": model,
                    "prompt": prompt_text,
                    "stream": False,  # We want the full JSON stats at the end
                    "options": {
                        "num_predict": 512, # Limit output to ensure fair comparison
                        "temperature": 0.0 # Deterministic
                    }
                }
                
                try:
                    start_time = time.time()
                    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
                    end_time = time.time()
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        
                        # Ollama returns times in nanoseconds
                        total_ns = data.get('total_duration', 0)
                        load_ns = data.get('load_duration', 0)
                        eval_count = data.get('eval_count', 0)
                        eval_ns = data.get('eval_duration', 0)
                        prompt_eval_count = data.get('prompt_eval_count', 0)
                        prompt_eval_ns = data.get('prompt_eval_duration', 0)
                        
                        # Calculate Metrics
                        tps = (eval_count / eval_ns * 1e9) if eval_ns > 0 else 0
                        latency = (load_ns + prompt_eval_ns) / 1e6 # ms
                        
                        results.append({
                            "Model": model,
                            "Run": i + 1,
                            "Tokens/Sec (Speed)": round(tps, 2),
                            "Total Tokens": eval_count,
                            "First Token Latency (ms)": round(latency, 2),
                            "Total Time (s)": round(total_ns / 1e9, 2),
                            "Model Load Time (ms)": round(load_ns / 1e6, 2)
                        })
                    else:
                        st.error(f"Error testing {model}: {resp.text}")
                except Exception as e:
                    st.error(f"Exception: {e}")
                
                current_step += 1
                progress_bar.progress(current_step / total_steps)

        progress_bar.empty()
        status_text.text("Benchmark Complete!")
        
        if results:
            df = pd.DataFrame(results)
            
            # Display Summary Table
            st.subheader("Results Summary")
            summary = df.groupby("Model").agg({
                "Tokens/Sec (Speed)": "mean",
                "First Token Latency (ms)": "mean",
                "Model Load Time (ms)": "mean"
            }).reset_index()
            st.dataframe(summary.style.format("{:.2f}", subset=["Tokens/Sec (Speed)", "First Token Latency (ms)", "Model Load Time (ms)"]), use_container_width=True)
            
            # Visualizations
            c1, c2 = st.columns(2)
            with c1:
                fig_speed = px.bar(summary, x="Model", y="Tokens/Sec (Speed)", color="Model", title="Generation Speed (Higher is Better)", text_auto='.2f')
                st.plotly_chart(fig_speed, use_container_width=True)
            with c2:
                fig_latency = px.bar(summary, x="Model", y="First Token Latency (ms)", color="Model", title="Latency (Lower is Better)", text_auto='.0f')
                st.plotly_chart(fig_latency, use_container_width=True)
            
            with st.expander("Detailed Logs"):
                st.dataframe(df)
