from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers import auth_controller, file_controller
from fastapi.staticfiles import StaticFiles

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

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
