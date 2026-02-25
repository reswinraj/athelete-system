from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import auth, users, workouts, nutrition, predictions

app = FastAPI(
    title="Athlete Nutrition & Training System API",
    description="API for AI-powered athlete training and nutrition optimization.",
    version="1.0.0"
)

# CORS Configuration
origins = [
    "http://localhost:3000",  # Next.js Frontend
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(workouts.router)
app.include_router(nutrition.router)
app.include_router(predictions.router)

@app.get("/")
def root():
    return {"message": "Welcome to the Athlete AI System API"}
