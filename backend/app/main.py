"""FastAPI 应用入口。"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import excel, follow_sell, mapping
from app.config import CORS_ORIGINS, HOST, PORT

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AMZEU Add Color Size Backend",
    description="欧洲亚马逊加色加码后端骨架",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mapping.router)
app.include_router(excel.router)
app.include_router(follow_sell.router)


@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "AMZEU Add Color Size Backend", "status": "running", "version": "0.1.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
