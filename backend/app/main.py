from fastapi import APIRouter, FastAPI

from app.api import auth, basics, garments, health, inspirations, me, outfits, saved_outfits

app = FastAPI(title="Outfit API")
app.include_router(health.router)

v1 = APIRouter(prefix="/v1")
v1.include_router(auth.router)
v1.include_router(me.router)
v1.include_router(garments.router)
v1.include_router(basics.router)
v1.include_router(outfits.router)
v1.include_router(inspirations.router)
v1.include_router(saved_outfits.router)
app.include_router(v1)
