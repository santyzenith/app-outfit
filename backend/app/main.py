from fastapi import APIRouter, FastAPI

from app.api import auth, garments, health, me, outfits

app = FastAPI(title="Outfit API")
app.include_router(health.router)

v1 = APIRouter(prefix="/v1")
v1.include_router(auth.router)
v1.include_router(me.router)
v1.include_router(garments.router)
v1.include_router(outfits.router)
app.include_router(v1)
