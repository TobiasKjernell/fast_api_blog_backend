from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarlettehttPException

from contextlib import asynccontextmanager
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler

from database import Base, engine
from routers import posts, users

# @asynccontextmanager turns this method into a manager, be boot up the db
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as connect:
        await connect.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

# We consume the lifespan method and lets it start     
app = FastAPI(title="Blog Dev Test", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],        
)

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(posts.router, prefix="/api/posts", tags=["Posts"])



@app.exception_handler(StarlettehttPException)
async def general_http_exception_handler(request: Request, exception: StarlettehttPException):
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request=request, exc=exception)

@app.exception_handler(RequestValidationError)
async def validation_exeption_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request=request, exc=exception)
    


     