from fastapi import FastAPI

# from app.core.config import settings
# from app.api.v1.health import router as health_router

# app = FastAPI(
#     title=settings.app_name,
#     description=settings.app_description,
#     version=settings.app_version
# )

app = FastAPI(
    title="My API")

@app.get("/")
async def read_root():
    return {"message": "Welcome to My API!"}

#app.include_router(health_router, prefix="/api/v1")