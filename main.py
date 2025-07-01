from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from controllers import auth_controller, file_controller, group_controller, event_controller, survey_controller
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

app = FastAPI()

origins = [
    'http://localhost:3000',  
    'https://your-frontend-domain.com',
    'http://100.90.147.122:8000',
    'http://100.100.11.120',  
    'http://100.90.147.122',
    'http://10.126.11.212:5173/'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_controller.router, prefix="/api/v1")
app.include_router(file_controller.router, prefix="/api/v1/images")
app.include_router(group_controller.router, prefix="/api/v1/groups")
app.include_router(event_controller.router, prefix="/api/v1/events")
app.include_router(survey_controller.router, prefix="/api/v1/survey")

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
