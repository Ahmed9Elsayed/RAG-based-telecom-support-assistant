import os
from fastapi import FastAPI
from pydantic import BaseModel
from rag_class import TelecomRAG
import requests
from dotenv import load_dotenv

load_dotenv()
# Pulled safely from .env instead of hardcoding
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

app = FastAPI(
    title="NileTel Arabic AI Assistant",
    description="RAG-based telecom support assistant with ticket automation",
    version="1.0"
)

# Load RAG system once
rag = TelecomRAG()

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    needs_action: str
    sources: list
    displayed_source: str

@app.get("/")
def root():
    return {"message": "NileTel AI Assistant API is running successfully!"}

@app.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest):
    print(f"\n[API] Received new query: {request.query}")
    
    response = rag.run_rag_pipeline(request.query)
    print(f"[API] Response ready | Needs Action: {response['needs_action']}")

    if response["needs_action"] == "YES":
        print("[API] Action detected → Triggering n8n workflow...")
        try:
            res = requests.post(
                N8N_WEBHOOK_URL,
                json={
                    "query": request.query,
                    "answer": response["answer"],
                    "sources": response["sources"]
                },
                timeout=5
            )
            print(f"[API] n8n status: {res.status_code}")
        except Exception as e:
            print(f"[API] n8n error: {str(e)}")
    else:
        print("[API] No action needed")

    return response