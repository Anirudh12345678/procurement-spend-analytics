import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings
from app.logging_config import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


app = FastAPI(
    title="Procurement Spend Analytics API",
    version="0.2.0",
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
app.include_router(api_router)

logger = logging.getLogger(__name__)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request failure: %s %s", request.method, request.url.path)
        raise
    duration_ms = (perf_counter() - started) * 1000
    logger.info(
        "%s %s -> %s (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        detail = exc.detail
    else:
        detail = {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(Exception)
async def internal_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected server error occurred",
            }
        },
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
