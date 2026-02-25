from fastapi import FastAPI
from app.state_manager import StateManager

app = FastAPI(title="Belt ML Runtime")

@app.get("/")
def read_root():
    return {"status": "online", "component": "belt-ml-runtime"}

@app.get("/state/{belt_id}")
def get_state_test(belt_id: str):
    """
    Test endpoint for state recovery.
    """
    sm = StateManager()
    return sm.get_state(belt_id)
