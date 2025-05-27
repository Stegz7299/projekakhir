from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from controllers import auth_controller, file_controller
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from controllers import group_controller

app = FastAPI()

origins = [
    "http://localhost:3000",  
    "https://your-frontend-domain.com",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_controller.router, prefix="/api/v1")
app.include_router(file_controller.router, prefix="/api/v1/images")
app.include_router(group_controller.router, prefix="/api/v1/groups")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail["message"] if isinstance(exc.detail, dict) and "message" in exc.detail else str(exc.detail)
        }
    )
