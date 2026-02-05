import streamlit as st
import requests
import json
import pandas as pd
import re
import time

st.set_page_config(page_title="Automator Testów", page_icon="⚙️", layout="wide")

OLLAMA_HOST = "http://ollama:11434"
MODELS_TO_TEST = ["gpt-oss:120b", "gpt-oss:20b"]

st.title("⚙️ Automator Testów (Batch Evaluator)")
st.markdown("Automatyczne porównanie skuteczności modeli (120B vs 20B) na podstawie zbioru testowego.")

# --- CONFIGURATION ---
with st.expander("Konfiguracja Testu", expanded=True):
    # Institute Profile (Global for this batch)
    default_profile = "Instytut Łukasiewicz-AI specjalizuje się w badaniach nad sztuczną inteligencją, uczeniem maszynowym, cyberbezpieczeństwem oraz cyfryzacją procesów przemysłowych. Główne obszary to: algorytmy NLP, computer vision, systemy autonomiczne oraz bezpieczeństwo infrastruktury IT. Instytut nie zajmuje się rolnictwem, biotechnologią żywności ani energetyką konwencjonalną."
    institute_profile = st.text_area("Profil Instytutu (użyty dla wszystkich fiszek):", value=default_profile, height=100)
    
    # File Uploader
    uploaded_file = st.file_uploader("Wgraj plik JSON z fiszkami", type=["json"])
    
    # Run Button
    start_btn = st.button("Uruchom Test Porównawczy", type="primary", disabled=not uploaded_file)

# --- LOGIC ---
if start_btn and uploaded_file:
    try:
        data = json.load(uploaded_file)
        if not isinstance(data, list):
            st.error("Plik JSON musi zawierać listę obiektów.")
            st.stop()
            
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_steps = len(data) * len(MODELS_TO_TEST)
        current_step = 0
        
        for item in data:
            # Extract fields from JSON
            doc_id = item.get("id_pliku", "N/A")
            goal = item.get("cel_projektu", "")
            innovations = "\n".join(item.get("glowne_funkcjonalnosci", [])) if isinstance(item.get("glowne_funkcjonalnosci"), list) else item.get("glowne_funkcjonalnosci", "")
            results_field = "\n".join(item.get("rezultaty", [])) if isinstance(item.get("rezultaty"), list) else item.get("rezultaty", "")
            # Normalize ground truth: "go" -> "GO", "no-go" -> "NO-GO"
            raw_gt = item.get("werdykt", "").upper().replace(" ", "-")
            if "NO" in raw_gt:
                ground_truth = "NO-GO"
            else:
                ground_truth = "GO"
            
            row = {
                "ID": doc_id,
                "Tytuł": item.get("tytul_projektu", ""),
                "Ground Truth": ground_truth
            }
            
            # Construct Prompt - JSON OUTPUT FORMAT
            prompt = f"""Jesteś surowym i precyzyjnym ekspertem oceniającym wnioski grantowe. Twoim zadaniem jest ocena projektu na podstawie dostarczonych danych pod kątem dwóch kryteriów krytycznych.

DANE WEJŚCIOWE:
1. PROFIL INSTYTUTU:
{institute_profile}

2. CEL PROJEKTU:
{goal}

3. INNOWACJE:
{innovations}

4. REZULTATY:
{results_field}

KRYTERIA OCENY:
1. DOPASOWANIE DO PROFILU: Czy projekt mieści się w obszarze badawczym i kompetencyjnym instytutu?
2. KOMERCJALIZACJA: Czy wyniki prowadzą do rynkowej komercjalizacji (sprzedaż, licencja), a nie tylko "wdrożenia własnego"?

ODPOWIEDZ W FORMACIE JSON (i TYLKO JSON, bez żadnego innego tekstu):
{{
  "analiza_profilu": "Twoja analiza zgodności z profilem instytutu...",
  "analiza_komercjalizacji": "Twoja analiza potencjału komercjalizacyjnego...",
  "werdykt": "GO",
  "uzasadnienie": "Krótkie uzasadnienie decyzji..."
}}

WAŻNE:
- Pole "werdykt" MUSI zawierać DOKŁADNIE jedno z dwóch słów: "GO" lub "NO-GO" (wielkimi literami, bez innych znaków).
- Odpowiedz TYLKO poprawnym JSON-em, bez żadnych dodatkowych komentarzy przed ani po.
"""
            
            for model in MODELS_TO_TEST:
                status_text.text(f"Analiza: {doc_id} na modelu {model}...")
                
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",  # Ollama hint for JSON output
                    "options": {"temperature": 0.0}
                }
                
                try:
                    start_ts = time.time()
                    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
                    end_ts = time.time()
                    
                    if resp.status_code == 200:
                        full_text = resp.json().get('response', '')
                        
                        # Parse JSON response
                        try:
                            result_json = json.loads(full_text)
                            verdict = result_json.get("werdykt", "").strip().upper()
                        except json.JSONDecodeError:
                            verdict = "JSON_ERROR"
                        
                        row[f"{model} Verdict"] = verdict
                        row[f"{model} Time"] = round(end_ts - start_ts, 2)
                        
                        # Check Match - EXACT comparison
                        is_correct = (verdict == ground_truth)
                        row[f"{model} Correct"] = is_correct
                        
                    else:
                        row[f"{model} Verdict"] = "ERROR"
                        row[f"{model} Correct"] = False
                        
                except Exception as e:
                    row[f"{model} Verdict"] = f"EXC: {e}"
                    row[f"{model} Correct"] = False
                
                current_step += 1
                progress_bar.progress(current_step / total_steps)
            
            results.append(row)
            
        progress_bar.empty()
        status_text.text("Test zakończony!")
        
        # --- RESULTS PRESENTATION ---
        df = pd.DataFrame(results)
        
        # Calculate Accuracy
        acc_120 = df[f"{MODELS_TO_TEST[0]} Correct"].mean() * 100
        acc_20 = df[f"{MODELS_TO_TEST[1]} Correct"].mean() * 100
        
        # Display Metrics
        c1, c2 = st.columns(2)
        c1.metric(f"Dokładność {MODELS_TO_TEST[0]}", f"{acc_120:.1f}%")
        c2.metric(f"Dokładność {MODELS_TO_TEST[1]}", f"{acc_20:.1f}%")
        
        # Detailed Table
        st.subheader("Szczegółowe Wyniki")
        
        # Stylizacja tabeli (highlight errors)
        def highlight_diff(row):
            styles = [''] * len(row)
            # 120B Index
            idx_120 = df.columns.get_loc(f"{MODELS_TO_TEST[0]} Verdict")
            idx_120_corr = df.columns.get_loc(f"{MODELS_TO_TEST[0]} Correct")
            
            # 20B Index
            idx_20 = df.columns.get_loc(f"{MODELS_TO_TEST[1]} Verdict")
            idx_20_corr = df.columns.get_loc(f"{MODELS_TO_TEST[1]} Correct")
            
            if not row[idx_120_corr]:
                styles[idx_120] = 'background-color: #ffcccc; color: black'
            else:
                styles[idx_120] = 'background-color: #ccffcc; color: black'
                
            if not row[idx_20_corr]:
                styles[idx_20] = 'background-color: #ffcccc; color: black'
            else:
                styles[idx_20] = 'background-color: #ccffcc; color: black'
                
            return styles

        st.dataframe(df)
        
        with st.expander("Pobierz wyniki CSV"):
            st.download_button("Pobierz CSV", df.to_csv().encode('utf-8'), "wyniki_testu.csv")

    except Exception as e:
        st.error(f"Błąd przetwarzania pliku: {e}")
