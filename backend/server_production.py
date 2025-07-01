import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from contextlib import asynccontextmanager
import uuid
import socketio
from fastapi_socketio import SocketManager
import secrets

# Environment variables with production defaults
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "agency_platform")
JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

# Validate required environment variables
if not MONGO_URL:
    raise ValueError("MONGO_URL environment variable is required")
if not JWT_SECRET:
    if ENVIRONMENT == "production":
        raise ValueError("JWT_SECRET environment variable is required in production")
    else:
        JWT_SECRET = "development-key-not-secure"
        print("⚠️  Using default JWT secret for development")

# MongoDB connection with error handling
try:
    client = MongoClient(MONGO_URL)
    # Test the connection
    client.admin.command('ping')
    db = client[DB_NAME]
    print(f"✅ Connected to MongoDB: {MONGO_URL}")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    raise

# Collections
users_collection = db.users
projects_collection = db.projects
tasks_collection = db.tasks

# Socket.io setup
sio = socketio.AsyncServer(
    cors_allowed_origins="*" if ENVIRONMENT == "development" else CORS_ORIGINS,
    logger=True,
    engineio_logger=True
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Digital Agency Platform Starting...")
    print(f"📊 Environment: {ENVIRONMENT}")
    print(f"🗃️  Database: {DB_NAME}")
    print(f"🌐 CORS Origins: {CORS_ORIGINS}")
    
    # Create indexes for better performance
    try:
        users_collection.create_index("email", unique=True)
        projects_collection.create_index("project_id", unique=True)
        tasks_collection.create_index("task_id", unique=True)
        tasks_collection.create_index("project_id")
        print("✅ Database indexes created")
    except Exception as e:
        print(f"⚠️  Index creation warning: {e}")
    
    yield
    print("🔄 Shutting down...")

# FastAPI app
app = FastAPI(
    title="Digital Agency Management Platform",
    description="A comprehensive platform for managing digital agency operations",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware with production settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if ENVIRONMENT == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount socket.io
socket_manager = SocketManager(app=app, socketio_path="/ws")

# Security
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "developer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    created_at: datetime

class ProjectCreate(BaseModel):
    name: str
    description: str
    client_name: str
    status: str = "planning"
    team_members: List[str] = []

class ProjectResponse(BaseModel):
    project_id: str
    name: str
    description: str
    client_name: str
    status: str
    team_members: List[dict]
    created_at: datetime
    created_by: str

class TaskCreate(BaseModel):
    title: str
    description: str
    status: str = "todo"
    assigned_to: Optional[str] = None
    priority: str = "medium"

class TaskResponse(BaseModel):
    task_id: str
    title: str
    description: str
    status: str
    assigned_to: Optional[dict] = None
    priority: str
    project_id: str
    created_at: datetime
    created_by: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = users_collection.find_one({"user_id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Socket.io events
@sio.event
async def connect(sid, environ):
    print(f"Client {sid} connected")
    await sio.emit('message', {'data': 'Connected to Digital Agency Platform!'}, room=sid)

@sio.event
async def disconnect(sid):
    print(f"Client {sid} disconnected")

@sio.event
async def join_project(sid, data):
    project_id = data.get('project_id')
    if project_id:
        await sio.enter_room(sid, f"project_{project_id}")
        await sio.emit('message', {'data': f'Joined project {project_id}'}, room=sid)

@sio.event
async def task_updated(sid, data):
    project_id = data.get('project_id')
    if project_id:
        await sio.emit('task_update', data, room=f"project_{project_id}")

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Digital Agency Management Platform API",
        "version": "1.0.0",
        "status": "healthy",
        "environment": ENVIRONMENT
    }

@app.get("/api/health")
async def health_check():
    try:
        # Test database connection
        client.admin.command('ping')
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "message": "Digital Agency Management Platform API",
        "environment": ENVIRONMENT,
        "database": db_status,
        "timestamp": datetime.utcnow()
    }

# Auth routes
@app.post("/api/auth/register")
async def register_user(user: UserCreate):
    # Check if user exists
    existing_user = users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user.password)
    
    new_user = {
        "user_id": user_id,
        "name": user.name,
        "email": user.email,
        "password": hashed_password,
        "role": user.role,
        "created_at": datetime.utcnow()
    }
    
    users_collection.insert_one(new_user)
    
    # Create token
    access_token = create_access_token(data={"sub": user_id})
    
    return {
        "message": "User created successfully",
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**new_user)
    }

@app.post("/api/auth/login")
async def login_user(user_login: UserLogin):
    # Find user
    user = users_collection.find_one({"email": user_login.email})
    if not user or not verify_password(user_login.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    access_token = create_access_token(data={"sub": user["user_id"]})
    
    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user)
    }

@app.get("/api/auth/me")
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)

# User routes
@app.get("/api/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    users = list(users_collection.find({}, {"password": 0}))
    return [UserResponse(**user) for user in users]

# Project routes
@app.post("/api/projects")
async def create_project(project: ProjectCreate, current_user: dict = Depends(get_current_user)):
    project_id = str(uuid.uuid4())
    
    # Get team member details
    team_member_details = []
    if project.team_members:
        team_members = list(users_collection.find({"user_id": {"$in": project.team_members}}, {"password": 0}))
        team_member_details = [UserResponse(**member).model_dump() for member in team_members]
    
    new_project = {
        "project_id": project_id,
        "name": project.name,
        "description": project.description,
        "client_name": project.client_name,
        "status": project.status,
        "team_members": team_member_details,
        "created_at": datetime.utcnow(),
        "created_by": current_user["user_id"]
    }
    
    projects_collection.insert_one(new_project)
    
    return {
        "message": "Project created successfully",
        "project": ProjectResponse(**new_project)
    }

@app.get("/api/projects")
async def get_projects(current_user: dict = Depends(get_current_user)):
    projects = list(projects_collection.find())
    return [ProjectResponse(**project) for project in projects]

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    project = projects_collection.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(**project)

@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, project_update: ProjectCreate, current_user: dict = Depends(get_current_user)):
    project = projects_collection.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get team member details
    team_member_details = []
    if project_update.team_members:
        team_members = list(users_collection.find({"user_id": {"$in": project_update.team_members}}, {"password": 0}))
        team_member_details = [UserResponse(**member).model_dump() for member in team_members]
    
    update_data = {
        "name": project_update.name,
        "description": project_update.description,
        "client_name": project_update.client_name,
        "status": project_update.status,
        "team_members": team_member_details,
        "updated_at": datetime.utcnow()
    }
    
    projects_collection.update_one({"project_id": project_id}, {"$set": update_data})
    
    updated_project = projects_collection.find_one({"project_id": project_id})
    return ProjectResponse(**updated_project)

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, current_user: dict = Depends(get_current_user)):
    project = projects_collection.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete project and all its tasks
    projects_collection.delete_one({"project_id": project_id})
    tasks_collection.delete_many({"project_id": project_id})
    
    return {"message": "Project deleted successfully"}

# Task routes (Kanban Board)
@app.post("/api/projects/{project_id}/tasks")
async def create_task(project_id: str, task: TaskCreate, current_user: dict = Depends(get_current_user)):
    # Verify project exists
    project = projects_collection.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task_id = str(uuid.uuid4())
    
    # Get assigned user details if provided
    assigned_user = None
    if task.assigned_to:
        assigned_user_data = users_collection.find_one({"user_id": task.assigned_to}, {"password": 0})
        if assigned_user_data:
            assigned_user = UserResponse(**assigned_user_data).model_dump()
    
    new_task = {
        "task_id": task_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "assigned_to": assigned_user,
        "priority": task.priority,
        "project_id": project_id,
        "created_at": datetime.utcnow(),
        "created_by": current_user["user_id"]
    }
    
    tasks_collection.insert_one(new_task)
    
    # Emit real-time update
    await sio.emit('task_created', {
        "task": TaskResponse(**new_task).model_dump(),
        "project_id": project_id
    }, room=f"project_{project_id}")
    
    return {
        "message": "Task created successfully",
        "task": TaskResponse(**new_task)
    }

@app.get("/api/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str, current_user: dict = Depends(get_current_user)):
    tasks = list(tasks_collection.find({"project_id": project_id}))
    return [TaskResponse(**task) for task in tasks]

@app.put("/api/projects/{project_id}/tasks/{task_id}")
async def update_task(project_id: str, task_id: str, task_update: TaskUpdate, current_user: dict = Depends(get_current_user)):
    task = tasks_collection.find_one({"task_id": task_id, "project_id": project_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {}
    for field, value in task_update.model_dump(exclude_unset=True).items():
        if field == "assigned_to" and value:
            # Get assigned user details
            assigned_user_data = users_collection.find_one({"user_id": value}, {"password": 0})
            if assigned_user_data:
                update_data["assigned_to"] = UserResponse(**assigned_user_data).model_dump()
            else:
                update_data["assigned_to"] = None
        else:
            update_data[field] = value
    
    update_data["updated_at"] = datetime.utcnow()
    
    tasks_collection.update_one({"task_id": task_id}, {"$set": update_data})
    
    updated_task = tasks_collection.find_one({"task_id": task_id})
    
    # Emit real-time update
    await sio.emit('task_updated', {
        "task": TaskResponse(**updated_task).model_dump(),
        "project_id": project_id
    }, room=f"project_{project_id}")
    
    return TaskResponse(**updated_task)

@app.delete("/api/projects/{project_id}/tasks/{task_id}")
async def delete_task(project_id: str, task_id: str, current_user: dict = Depends(get_current_user)):
    task = tasks_collection.find_one({"task_id": task_id, "project_id": project_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tasks_collection.delete_one({"task_id": task_id})
    
    # Emit real-time update
    await sio.emit('task_deleted', {
        "task_id": task_id,
        "project_id": project_id
    }, room=f"project_{project_id}")
    
    return {"message": "Task deleted successfully"}

# Generate a secure JWT secret
def generate_jwt_secret():
    return secrets.token_urlsafe(64)

# For production deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)