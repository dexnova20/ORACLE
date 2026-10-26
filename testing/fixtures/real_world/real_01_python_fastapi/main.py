from fastapi import FastAPI
from routers.items import router as items_router

app = FastAPI(title="RealWorld FastAPI Service")
app.include_router(items_router)

@app.get("/health")
def health():
    return {"status": "ok"}
