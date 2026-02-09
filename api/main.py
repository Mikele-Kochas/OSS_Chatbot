from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
from starlette.status import HTTP_403_FORBIDDEN

app = FastAPI(
    title="Grant Validator API",
    description="API do automatycznej oceny wniosków grantowych przy użyciu modeli LLM (Ollama).",
    version="1.0.0"
)

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
# API_KEY = os.getenv("API_KEY", "tajnehaslo123") # Disabled for demo

# CORS - Allow all origins for local HTML file access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_MODEL = "gpt-oss:20b"

class GrantProposal(BaseModel):
    institute_profile: str
    project_goal: str
    innovations: str
    results: str
    model: str = DEFAULT_MODEL

class ValidationResult(BaseModel):
    verdict: str
    full_analysis: str
    model_used: str

@app.post("/validate", response_model=ValidationResult)
async def validate_proposal(proposal: GrantProposal):
    try:
        # Construct the Prompt - Same robust marker-based format as in the UI
        prompt = f"""Jesteś surowym i precyzyjnym ekspertem oceniającym wnioski grantowe.

DANE WEJŚCIOWE:
1. PROFIL INSTYTUTU:
{proposal.institute_profile}

2. CEL PROJEKTU:
{proposal.project_goal}

3. INNOWACJE:
{proposal.innovations}

4. REZULTATY:
{proposal.results}

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
        
        payload = {
            "model": proposal.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 4096
            }
        }
        
        # Call Ollama
        response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Ollama Error: {response.text}")
            
        result_text = response.json().get('response', '')
        
        # Parse Verdict using Marker
        verdict = "UNCERTAIN"
        if "<<<WERDYKT: NO-GO>>>" in result_text:
            verdict = "NO-GO"
        elif "<<<WERDYKT: GO>>>" in result_text:
            verdict = "GO"
            
        return ValidationResult(
            verdict=verdict,
            full_analysis=result_text,
            model_used=proposal.model
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok", "ollama_host": OLLAMA_HOST}
