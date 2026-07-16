from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import close_pool, init_pool
from app.errors import AppError
from app.logging_config import configure_logging, get_logger
from app.routers import conversations, items, query, usage

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    logger.info("startup_complete")
    yield
    close_pool()


app = FastAPI(title="AI Knowledge Inbox", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "request_failed path=%s status=%d error=%s",
        request.url.path,
        exc.status_code,
        exc.message,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(items.router)
app.include_router(query.router)
app.include_router(conversations.router)
app.include_router(usage.router)
