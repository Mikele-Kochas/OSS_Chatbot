import streamlit as st
import requests
import json
import re

st.set_page_config(page_title="Walidator Wniosków", page_icon="📋", layout="wide")

OLLAMA_HOST = "http://ollama:11434"
DEFAULT_MODEL = "gpt-oss:120b"
ALTERNATIVE_MODEL = "gpt-oss:20b"

st.title("📋 Walidator Wniosków Grantowych")
st.markdown("Narzędzie do wstępnej oceny zgodności projektu z profilem instytutu oraz potencjałem komercjalizacyjnym.")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        if response.status_code == 200:
            models = [m['name'] for m in response.json().get('models', [])]
            
            # Ensure our target models are in the list
            if DEFAULT_MODEL not in models:
                 models.append(DEFAULT_MODEL)
            if ALTERNATIVE_MODEL not in models:
                 models.append(ALTERNATIVE_MODEL)
            
            # Sort to keep our preferred models at the top
            models.sort(key=lambda x: (x != DEFAULT_MODEL, x != ALTERNATIVE_MODEL))
            
            selected_model = st.selectbox("Select Model", models)
        else:
            st.error("Could not fetch models from Ollama.")
            selected_model = DEFAULT_MODEL
    except Exception as e:
        st.error(f"Connection error: {e}")
        selected_model = DEFAULT_MODEL
    
    st.markdown("---")
    st.markdown(f"- Active Model: `{selected_model}`")

# --- INPUT FORM ---
with st.container():
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("1. Profil Instytutu")
        institute_profile = st.text_area(
            "Opisz profil działalności badawczej i kompetencje instytutu:",
            height=300,
            placeholder="Np. Instytut specjalizuje się w badaniach nad sztuczną inteligencją, uczeniem maszynowym oraz ich zastosowaniem w medycynie..."
        )

    with c2:
        st.subheader("2. Dane Projektu")
        project_goal = st.text_area("Cel projektu (krótki opis):", height=100)
        innovations = st.text_area("Główne funkcjonalności / Cechy innowacyjne:", height=100, help="Elementy innowacyjne lub znacząco ulepszone w stosunku do rynku.")
        results = st.text_area("Rezultaty:", height=100, help="Mierzalne efekty, w tym komercjalizacja.")

# --- VALIDATION LOGIC ---
if st.button("Sprawdź Wniosek (GO / NO-GO)", type="primary"):
    if not all([institute_profile, project_goal, innovations, results]):
        st.error("Proszę wypełnić wszystkie pola formularza.")
    else:
        with st.spinner(f"Analizuję wniosek ({selected_model})..."):
            # Construct the Prompt - JSON OUTPUT FORMAT
            prompt = f"""Jesteś surowym i precyzyjnym ekspertem oceniającym wnioski grantowe. Twoim zadaniem jest ocena projektu na podstawie dostarczonych danych pod kątem dwóch kryteriów krytycznych.

DANE WEJŚCIOWE:
1. PROFIL INSTYTUTU:
{institute_profile}

2. CEL PROJEKTU:
{project_goal}

3. INNOWACJE:
{innovations}

4. REZULTATY:
{results}

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

Przykład poprawnej odpowiedzi dla projektu który NIE pasuje:
{{
  "analiza_profilu": "Projekt dotyczy rolnictwa, co nie jest w profilu instytutu IT.",
  "analiza_komercjalizacji": "Brak planu sprzedaży, tylko wdrożenie wewnętrzne.",
  "werdykt": "NO-GO",
  "uzasadnienie": "Projekt nie pasuje do profilu i nie ma potencjału komercyjnego."
}}
"""
            
            # Send to Ollama with JSON format hint
            payload = {
                "model": selected_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",  # Ollama hint for JSON output
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 4096
                }
            }
            
            try:
                response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
                if response.status_code == 200:
                    result_text = response.json().get('response', '')
                    
                    # Try to parse JSON response
                    try:
                        result_json = json.loads(result_text)
                        
                        # Display Results
                        st.markdown("---")
                        st.subheader("Wynik Analizy AI")
                        
                        st.markdown("### 1. Analiza Zgodności z Profilem")
                        st.markdown(result_json.get("analiza_profilu", "Brak danych"))
                        
                        st.markdown("### 2. Analiza Potencjału Komercjalizacyjnego")
                        st.markdown(result_json.get("analiza_komercjalizacji", "Brak danych"))
                        
                        st.markdown("### WERDYKT KOŃCOWY")
                        verdict = result_json.get("werdykt", "").strip().upper()
                        
                        st.markdown("### UZASADNIENIE")
                        st.markdown(result_json.get("uzasadnienie", "Brak uzasadnienia"))
                        
                        # Visual feedback based on EXACT verdict value
                        if verdict == "NO-GO":
                            st.error("WERDYKT: NO-GO 🛑")
                        elif verdict == "GO":
                            st.success("WERDYKT: GO ✅")
                        else:
                            st.warning(f"⚠️ Nieoczekiwany werdykt: '{verdict}' (oczekiwano 'GO' lub 'NO-GO')")
                            
                    except json.JSONDecodeError:
                        # Fallback: display raw text if JSON parsing fails
                        st.warning("⚠️ Model nie zwrócił poprawnego JSON. Wyświetlam surową odpowiedź:")
                        st.markdown(result_text)
                        st.error("Nie udało się automatycznie wykryć werdyktu.")
                    
                else:
                    st.error(f"Błąd komunikacji z modelem: {response.text}")
            except Exception as e:
                st.error(f"Wystąpił błąd: {e}")

