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
        with st.spinner("Analizuję wniosek (model 120B)..."):
            # Construct the Prompt
            prompt = f"""
Jesteś surowym i precyzyjnym ekspertem oceniającym wnioski grantowe. Twoim zadaniem jest ocena projektu na podstawie dostarczonych danych pod kątem dwóch kryteriów krytycznych.

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
1. DOPASOWANIE DO PROFILU: Czy projekt mieści się w obszarze badawczym i kompetencyjnym instytutu? Jeśli projekt pasowałby lepiej do innego typu instytutu, należy to wypunktować.
2. KOMERCJALIZACJA: Czy wyniki prowadzą do rynkowej komercjalizacji (sprzedaż, licencja), czy jest to tylko "wdrożenie własne" lub realizacja potrzeb wewnętrznych (co jest błędem)? Projekt musi mieć potencjał rynkowy.

WYMAGANY FORMAT ODPOWIEDZI:
Analizę przedstaw w punktach, a na końcu wydaj jednoznaczną opinię.

### 1. Analiza Zgodności z Profilem
(Twoja analiza...)

### 2. Analiza Potencjału Komercjalizacyjnego
(Twoja analiza - zwróć uwagę czy to nie jest wdrożenie wewnętrzne...)

### WERDYKT KOŃCOWY
**[GO / NO-GO]**

### UZASADNIENIE
(Krótkie, żołnierskie uzasadnienie decyzji. Jeśli NO-GO, napisz dlaczego.)
"""
            
            # Send to Ollama
            payload = {
                "model": selected_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2, # Low temperature for consistent, strict evaluation
                    "num_ctx": 4096
                }
            }
            
            try:
                response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
                if response.status_code == 200:
                    result_text = response.json().get('response', '')
                    
                    # Display Results
                    st.markdown("---")
                    st.subheader("Wynik Analizy AI")
                    st.markdown(result_text)
                    
                    # Visual feedback based on verdict
                    # CRITICAL: Only search for verdict in the WERDYKT section to avoid false positives
                    # from Polish words containing "GO" like "DIALOG", "LOGO", "KATEGORIA"
                    verdict_section = ""
                    werdykt_match = re.search(r'WERDYKT[^\n]*\n([\s\S]{0,100})', result_text, re.IGNORECASE)
                    if werdykt_match:
                        verdict_section = werdykt_match.group(0)
                    else:
                        # Fallback: check last 200 characters
                        verdict_section = result_text[-200:]
                    
                    # Now search for verdict ONLY in the extracted section
                    if re.search(r'NO[- _]?GO', verdict_section, re.IGNORECASE):
                        st.error("WERDYKT: NO-GO 🛑")
                    elif re.search(r'\*\*GO\*\*|\bGO\b', verdict_section, re.IGNORECASE):
                        st.success("WERDYKT: GO ✅")
                    else:
                        st.warning("⚠️ Nie udało się automatycznie wykryć werdyktu (sprawdź tekst analizy).")
                    
                else:
                    st.error(f"Błąd komunikacji z modelem: {response.text}")
            except Exception as e:
                st.error(f"Wystąpił błąd: {e}")
