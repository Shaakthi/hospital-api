from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from dotenv import load_dotenv
import jwt
import bcrypt
import os
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta

# Initialize FastAPI application
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the 'static' folder to serve frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load .env file for environment variables
load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET", "default_secret")

# OAuth2PasswordBearer for login and token management
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# In-memory data storage (for demonstration; use a database for production)
users = []
health_metrics = {}

# Utility functions for JWT and password hashing
def create_access_token(data: dict):
    return jwt.encode(data, JWT_SECRET, algorithm="HS256")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Models
class User(BaseModel):
    id: int
    username: str
    role: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class HealthMetrics(BaseModel):
    sleep: int
    exercise: int
    waterIntake: int
    sex: Optional[str] = None

# 1. User Management Endpoints
@app.post("/register", response_model=User)
async def register_user(user: UserCreate):
    user_id = len(users) + 1  # Simple ID generation
    hashed_password = hash_password(user.password)
    new_user = {"id": user_id, "username": user.username, "role": user.role, "password": hashed_password}
    users.append(new_user)
    return {"id": new_user["id"], "username": new_user["username"], "role": new_user["role"]}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = next((user for user in users if user["username"] == form_data.username), None)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

# 2. Health Dashboard Endpoints
@app.get("/dashboard", response_model=HealthMetrics)
async def get_dashboard(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        username = payload.get("sub")
        user = next((user for user in users if user["username"] == username), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_metrics = health_metrics.get(user["id"], {"sleep": 0, "exercise": 0, "waterIntake": 0, "sex": "f/m"})
        return user_metrics
    except jwt.exceptions.PyJWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

@app.post("/dashboard/update", response_model=HealthMetrics)
async def update_dashboard(health_data: HealthMetrics, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        username = payload.get("sub")
        user = next((user for user in users if user["username"] == username), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        health_metrics[user["id"]] = health_data.dict()
        return health_data
    except jwt.exceptions.PyJWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

# 3. Root Endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Health API"}

# 4. Doctor list and appointments storage
doctors = [
    {"id": 1, "name": "Dr. Alice Smith", "specialty": "Cardiology"},
    {"id": 2, "name": "Dr. Bob Johnson", "specialty": "Pediatrics"},
    {"id": 3, "name": "Dr. Carol Williams", "specialty": "Mental Health"},
]
appointments = []

class Appointment(BaseModel):
    patient_id: int
    doctor_id: int
    date: datetime
    reason: Optional[str] = None

# Get list of doctors
@app.get("/doctors")
async def get_doctors():
    return doctors

# Schedule an appointment
@app.post("/appointments")
async def create_appointment(appointment: Appointment, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        username = payload.get("sub")
        user = next((user for user in users if user["username"] == username), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if doctor exists
        doctor = next((doc for doc in doctors if doc["id"] == appointment.doctor_id), None)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # Validate appointment date
        if appointment.date <= datetime.now():
            raise HTTPException(status_code=400, detail="Appointment date must be in the future.")
        
        # Add appointment
        new_appointment = {
            "patient_id": user["id"],
            "doctor_id": appointment.doctor_id,
            "date": appointment.date,
            "reason": appointment.reason,
            "doctor_name": doctor["name"],
            "specialty": doctor["specialty"]
        }
        appointments.append(new_appointment)
        return {"message": "Appointment scheduled successfully", "appointment": new_appointment}
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

# 5. Symptom Checker
class SymptomCheck(BaseModel):
    symptoms: List[str]

SYMPTOM_CONDITIONS = {
    "fever": ["Flu", "COVID-19", "Infection"],
    "cough": ["Flu", "COVID-19", "Cold"],
    "headache": ["Migraine", "Tension headache", "Sinusitis"],
    "sore throat": ["Cold", "Flu", "Strep throat"],
    "fatigue": ["Anemia", "Depression", "Chronic fatigue syndrome"],
    "stomach pain": ["bug, food posioning"]
}

@app.post("/symptom-checker")
async def check_symptoms(symptom_check: SymptomCheck, token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        username = payload.get("sub")
        user = next((user for user in users if user["username"] == username), None)
        if not user:
            raise HTTPException(status_code=404, detail="User  not found")

        matched_conditions = set()
        for symptom in symptom_check.symptoms:
            if symptom in SYMPTOM_CONDITIONS:
                matched_conditions.update(SYMPTOM_CONDITIONS[symptom])

        if not matched_conditions:
            return {"message": "No matching conditions found for the provided symptoms."}

        return {"matched_conditions": list(matched_conditions)}

    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
