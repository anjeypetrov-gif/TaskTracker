from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

# User Schemas
class UserBase(BaseModel):
    username: str
    full_name: str
    email: Optional[str] = None
    role: Optional[str] = "Разработчик"
    role_description: Optional[str] = None
    payment_details: Optional[str] = None
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    role_description: Optional[str] = None
    payment_details: Optional[str] = None
    avatar_color: Optional[str] = None

class UserResponse(UserBase):
    id: int
    avatar_color: str
    created_at: datetime
    last_seen: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_online: Optional[bool] = False

    class Config:
        from_attributes = True

class UserActivityResponse(BaseModel):
    id: int
    user_id: int
    action: str
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LoginRequest(BaseModel):
    username: str
    password: str

# Comment Schemas
class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    task_id: int
    content: str
    created_at: datetime
    author: UserResponse

    class Config:
        from_attributes = True

class TaskInviteRequest(BaseModel):
    user_id: int

# Task / Bug Schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = ""
    status: Optional[str] = "todo" # todo, in_progress, in_review, done
    priority: Optional[str] = "medium" # low, medium, high, urgent
    assignee_id: Optional[int] = None
    due_date: Optional[str] = None
    tags: Optional[str] = ""
    task_type: Optional[str] = "task" # task, bug
    severity: Optional[str] = "major" # critical, major, minor, trivial
    steps_to_reproduce: Optional[str] = ""

class TaskCreate(TaskBase):
    watcher_ids: Optional[List[int]] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    due_date: Optional[str] = None
    tags: Optional[str] = None
    task_type: Optional[str] = None
    severity: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    watcher_ids: Optional[List[int]] = None

# Attachment Schema
class AttachmentResponse(BaseModel):
    id: int
    task_id: int
    filename: str
    file_path: str
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True

class TaskResponse(TaskBase):
    id: int
    creator_id: int
    created_at: datetime
    updated_at: datetime
    creator: UserResponse
    assignee: Optional[UserResponse] = None
    watchers: Optional[List[UserResponse]] = []
    comments_count: Optional[int] = 0
    attachments: Optional[List[AttachmentResponse]] = []

    class Config:
        from_attributes = True

# User Dashboard Stats Schema
class UserStats(BaseModel):
    total_assigned: int
    in_progress: int
    completed: int
    urgent: int
    created_by_me: int
    open_bugs_count: Optional[int] = 0

