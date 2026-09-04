from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.analysis import router as analysis_router
from app.katago.client import start_katago, stop_katago


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_katago()

    yield

    stop_katago()


app = FastAPI(lifespan=lifespan)

app.include_router(analysis_router)


@app.get("/")
def health_check():
    return {"status": "ok"}