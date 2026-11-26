from contextlib import asynccontextmanager
from fastapi import FastAPI
from neo4j import GraphDatabase
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from qa import AUTH, MODEL_NAME, URI, ask

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    question: str
    answer: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        app.state.driver = driver
        app.state.model = SentenceTransformer(MODEL_NAME)
        yield

app = FastAPI(title="GraphRAG", lifespan=lifespan)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest) -> AskResponse:
    answer = ask(req.question, app.state.driver, app.state.model)
    return AskResponse(question=req.question, answer=answer)