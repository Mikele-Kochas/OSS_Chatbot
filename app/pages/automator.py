import streamlit as st
import requests
import json
import pandas as pd
import time

st.set_page_config(page_title="Automator Testów", page_icon="⚙️", layout="wide")

OLLAMA_HOST = "http://ollama:11434"
MODELS_TO_TEST = ["gpt-oss:120b", "gpt-oss:20b"]

st.title("⚙️ Automator Testów (Batch Evaluator)")
st.markdown("Automatyczne porównanie skuteczności modeli (120B vs 20B) na podstawie zbioru testowego.")

# --- CONFIGURATION ---
with st.expander("Konfiguracja Testu", expanded=True):
    default_profile = "Instytut Łukasiewicz-AI specjalizuje się w badaniach nad sztuczną inteligencją, uczeniem maszynowym, cyberbezpieczeństwem oraz cyfryzacją procesów przemysłowych. Główne obszary to: algorytmy NLP, computer vision, systemy autonomiczne oraz bezpieczeństwo infrastruktury IT. Instytut nie zajmuje się rolnictwem, biotechnologią żywności ani energetyką konwencjonalną."
    institute_profile = st.text_area("Profil Instytutu (użyty dla wszystkich fiszek):", value=default_profile, height=100)
    
    uploaded_file = st.file_uploader("Wgraj plik JSON z fiszkami", type=["json"])
    
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
            doc_id = item.get("id_pliku", "N/A")
            goal = item.get("cel_projektu", "")
            innovations = "\n".join(item.get("glowne_funkcjonalnosci", [])) if isinstance(item.get("glowne_funkcjonalnosci"), list) else item.get("glowne_funkcjonalnosci", "")
            results_field = "\n".join(item.get("rezultaty", [])) if isinstance(item.get("rezultaty"), list) else item.get("rezultaty", "")
            
            # Normalize ground truth
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
            
            # Construct Prompt - MARKER-BASED FORMAT
            prompt = f"""Jesteś surowym i precyzyjnym ekspertem oceniającym wnioski grantowe.

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

WYMAGANY FORMAT ODPOWIEDZI:

### 1. Analiza Zgodności z Profilem
(Twoja analiza...)

### 2. Analiza Potencjału Komercjalizacyjnego
(Twoja analiza...)

### UZASADNIENIE
(Krótkie uzasadnienie decyzji...)

NA SAMYM KOŃCU ODPOWIEDZI MUSISZ UMIEŚCIĆ DOKŁADNIE JEDEN Z PONIŻSZYCH ZNACZNIKÓW (skopiuj go dokładnie):
<<<WERDYKT: GO>>>
lub
<<<WERDYKT: NO-GO>>>

WAŻNE: Znacznik musi być ostatnią linią odpowiedzi, dokładnie w tym formacie z trzema nawiasami ostrymi.
"""
            
            for model in MODELS_TO_TEST:
                status_text.text(f"Analiza: {doc_id} na modelu {model}...")
                
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                }
                
                try:
                    start_ts = time.time()
                    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
                    end_ts = time.time()
                    
                    if resp.status_code == 200:
                        full_text = resp.json().get('response', '')
                        
                        # Extract verdict from marker - check NO-GO first (more specific)
                        if "<<<WERDYKT: NO-GO>>>" in full_text:
                            verdict = "NO-GO"
                        elif "<<<WERDYKT: GO>>>" in full_text:
                            verdict = "GO"
                        else:
                            verdict = "BRAK_ZNACZNIKA"
                        
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
        st.dataframe(df)
        
        with st.expander("Pobierz wyniki CSV"):
            st.download_button("Pobierz CSV", df.to_csv().encode('utf-8'), "wyniki_testu.csv")

    except Exception as e:
        st.error(f"Błąd przetwarzania pliku: {e}")
