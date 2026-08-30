import os
import uuid
import base64
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from datetime import datetime, timezone, timedelta
from .database import engine, Base, get_db
from .models import User, Task, Comment, Attachment, UserActivity, Notification, Subtask
from .schemas import (
    UserCreate, UserResponse, UserPublic, UserUpdate, LoginRequest, Token,
    TaskCreate, TaskUpdate, TaskResponse, TaskInviteRequest,
    CommentCreate, CommentResponse, UserStats, AttachmentResponse, UserActivityResponse,
    NotificationResponse, SubtaskCreate, SubtaskResponse, SubtaskUpdate
)
from .auth import hash_password, verify_password, create_access_token, get_current_user

# Create database tables
Base.metadata.create_all(bind=engine)

# Create uploads directory if not exists
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(title="TaskTracker API", version="1.0.0")

# Enable CORS for local dev.
# NOTE: allow_credentials=True cannot safely be combined with allow_origins=["*"]
# (browsers reject that combination, and it's unsafe if it worked). We don't
# use cookie-based auth here — every request carries its own Bearer token —
# so allow_credentials stays False.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    try:
        from .seed import seed_db
        seed_db()
    except Exception as e:
        print(f"Startup seed error: {e}")

# ----------------- Upload Safety Limits ----------------- #

MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB per file

# Extensions that must never be accepted: anything a browser could execute
# or render as active content if opened directly from /uploads (same origin
# as the app), which would otherwise allow stored XSS via file upload.
BLOCKED_UPLOAD_EXTENSIONS = {
    ".html", ".htm", ".svg", ".xhtml", ".js", ".mjs", ".php", ".phtml",
    ".exe", ".sh", ".bat", ".cmd", ".ps1", ".msi", ".jar", ".com", ".scr",
}

def validate_upload(file: UploadFile) -> None:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext in BLOCKED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Файлы с расширением '{ext}' запрещены к загрузке из соображений безопасности"
        )

def create_notification(db: Session, user_id: int, title: str, message: str, task_id: Optional[int] = None):
    try:
        notif = Notification(user_id=user_id, title=title, message=message, task_id=task_id, is_read=False)
        db.add(notif)
        db.commit()
    except Exception as e:
        print(f"Notification error: {e}")

def save_upload_capped(file: UploadFile, destination_path: str) -> int:
    """Copy an UploadFile to disk while enforcing MAX_UPLOAD_SIZE_BYTES,
    without ever buffering the whole file in memory."""
    total = 0
    chunk_size = 1024 * 1024
    with open(destination_path, "wb") as buffer:
        while True:
            chunk = file.file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_SIZE_BYTES:
                buffer.close()
                try:
                    os.remove(destination_path)
                except Exception:
                    pass
                raise HTTPException(
                    status_code=413,
                    detail=f"Файл превышает максимально допустимый размер ({MAX_UPLOAD_SIZE_BYTES // (1024*1024)} МБ)"
                )
            buffer.write(chunk)
    return total

# Mount uploads static folder
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# ----------------- Auth Endpoints ----------------- #

@app.post("/api/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    colors = ["#3b82f6", "#10b981", "#ec4899", "#8b5cf6", "#f59e0b", "#06b6d4", "#6366f1"]
    avatar_color = colors[len(user_data.username) % len(colors)]
    now = datetime.now(timezone.utc)

    new_user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        avatar_color=avatar_color,
        role=user_data.role or "Участник",
        created_at=now,
        last_seen=now,
        last_login=now
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    activity = UserActivity(user_id=new_user.id, action="Регистрация аккаунта", created_at=now)
    db.add(activity)
    db.commit()

    token = create_access_token({"sub": new_user.username})
    new_user.is_online = True
    return {"access_token": token, "token_type": "bearer", "user": new_user}

@app.post("/api/auth/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    now = datetime.now(timezone.utc)
    user.last_login = now
    user.last_seen = now
    activity = UserActivity(user_id=user.id, action="Вход в систему", created_at=now)
    db.add(activity)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username})
    user.is_online = True
    return {"access_token": token, "token_type": "bearer", "user": user}

@app.post("/api/auth/ping")
def ping_online(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "ok", "user_id": current_user.id}

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    current_user.is_online = True
    return current_user

@app.put("/api/users/me", response_model=UserResponse)
def update_my_profile(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.email is not None:
        current_user.email = user_update.email
    if user_update.role is not None:
        current_user.role = user_update.role
    if user_update.role_description is not None:
        current_user.role_description = user_update.role_description
    if user_update.payment_details is not None:
        current_user.payment_details = user_update.payment_details
    if user_update.avatar_color is not None:
        current_user.avatar_color = user_update.avatar_color

    db.commit()
    db.refresh(current_user)
    current_user.is_online = True
    return current_user

@app.post("/api/users/me/avatar", response_model=UserResponse)
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    validate_upload(file)
    contents = file.file.read()
    b64_str = base64.b64encode(contents).decode('utf-8')
    mime_type = file.content_type or "image/png"

    # Also save to disk locally
    avatars_dir = os.path.join(UPLOADS_DIR, "avatars")
    os.makedirs(avatars_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] or ".png"
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(avatars_dir, filename)
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception:
        pass

    current_user.avatar_url = f"data:{mime_type};base64,{b64_str}"
    db.commit()
    db.refresh(current_user)
    current_user.is_online = True
    return current_user

# ----------------- Users Endpoints ----------------- #

@app.get("/api/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).all()
    now = datetime.now(timezone.utc)
    for u in users:
        if u.last_seen:
            last_seen_tz = u.last_seen.replace(tzinfo=timezone.utc) if u.last_seen.tzinfo is None else u.last_seen
            u.is_online = (now - last_seen_tz).total_seconds() < 300
        else:
            u.is_online = False
    return users

@app.get("/api/admin/activity", response_model=List[UserActivityResponse])
def get_admin_activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    activities = db.query(UserActivity).order_by(UserActivity.created_at.desc()).limit(100).all()
    now = datetime.now(timezone.utc)
    for act in activities:
        if act.user and act.user.last_seen:
            last_seen_tz = act.user.last_seen.replace(tzinfo=timezone.utc) if act.user.last_seen.tzinfo is None else act.user.last_seen
            act.user.is_online = (now - last_seen_tz).total_seconds() < 300
    return activities

# ----------------- Admin User Management Endpoints ----------------- #

class AdminUserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    email: Optional[str] = None
    role: Optional[str] = "Разработчик"
    role_description: Optional[str] = None
    payment_details: Optional[str] = None

class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    role_description: Optional[str] = None
    payment_details: Optional[str] = None
    avatar_color: Optional[str] = None
    password: Optional[str] = None

@app.post("/api/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    user_data: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "Администратор" and current_user.username not in ["admin", "anjey"]:
        raise HTTPException(status_code=403, detail="Доступ только для Администратора")

    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    colors = ["#3b82f6", "#10b981", "#ec4899", "#8b5cf6", "#f59e0b", "#06b6d4", "#6366f1"]
    avatar_color = colors[len(user_data.username) % len(colors)]
    now = datetime.now(timezone.utc)

    new_user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        avatar_color=avatar_color,
        role=user_data.role or "Разработчик",
        role_description=user_data.role_description,
        payment_details=user_data.payment_details,
        created_at=now,
        last_seen=now,
        last_login=now
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    activity = UserActivity(user_id=current_user.id, action=f"Админ создал сотрудника {new_user.full_name} (@{new_user.username})", created_at=now)
    db.add(activity)
    db.commit()

    return new_user

@app.put("/api/admin/users/{user_id}", response_model=UserResponse)
def admin_update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "Администратор" and current_user.username not in ["admin", "anjey"]:
        raise HTTPException(status_code=403, detail="Доступ только для Администратора")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if user_data.full_name is not None:
        target_user.full_name = user_data.full_name
    if user_data.username is not None and user_data.username != target_user.username:
        dup = db.query(User).filter(User.username == user_data.username).first()
        if dup:
            raise HTTPException(status_code=400, detail="Логин уже занят другим пользователем")
        target_user.username = user_data.username
    if user_data.email is not None:
        target_user.email = user_data.email
    if user_data.role is not None:
        target_user.role = user_data.role
    if user_data.role_description is not None:
        target_user.role_description = user_data.role_description
    if user_data.payment_details is not None:
        target_user.payment_details = user_data.payment_details
    if user_data.avatar_color is not None:
        target_user.avatar_color = user_data.avatar_color
    if user_data.password:
        target_user.hashed_password = hash_password(user_data.password)

    db.commit()
    db.refresh(target_user)

    now = datetime.now(timezone.utc)
    activity = UserActivity(user_id=current_user.id, action=f"Админ обновил профиль {target_user.full_name}", created_at=now)
    db.add(activity)
    db.commit()

    return target_user

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "Администратор" and current_user.username not in ["admin", "anjey"]:
        raise HTTPException(status_code=403, detail="Доступ только для Администратора")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить собственный аккаунт Администратора")

    target_name = target_user.full_name

    # Unassign tasks assigned to target_user to avoid FK crashes
    assigned_tasks = db.query(Task).filter(Task.assignee_id == user_id).all()
    for t in assigned_tasks:
        t.assignee_id = None

    db.delete(target_user)
    db.commit()

    now = datetime.now(timezone.utc)
    activity = UserActivity(user_id=current_user.id, action=f"Админ удалил пользователя {target_name}", created_at=now)
    db.add(activity)
    db.commit()

    return {"message": f"Пользователь {target_name} успешно удален"}

# ----------------- Tasks Endpoints ----------------- #

@app.get("/api/tasks", response_model=List[TaskResponse])
def get_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[int] = None,
    search: Optional[str] = None,
    task_type: Optional[str] = None,
    severity: Optional[str] = None,
    my_tasks_only: Optional[bool] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Task)

    if my_tasks_only:
        query = query.filter(Task.assignee_id == current_user.id)
    elif assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)

    if task_type:
        query = query.filter(Task.task_type == task_type)
    if severity:
        query = query.filter(Task.severity == severity)
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(or_(Task.title.ilike(search_fmt), Task.description.ilike(search_fmt), Task.tags.ilike(search_fmt)))

    tasks = query.order_by(Task.updated_at.desc()).all()
    
    result = []
    for t in tasks:
        task_dict = TaskResponse.model_validate(t)
        task_dict.comments_count = len(t.comments)
        result.append(task_dict)

    return result

@app.post("/api/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        status=task_data.status or "todo",
        priority=task_data.priority or "medium",
        creator_id=current_user.id,
        assignee_id=task_data.assignee_id,
        due_date=task_data.due_date,
        tags=task_data.tags or "",
        task_type=task_data.task_type or "task",
        severity=task_data.severity or "major",
        steps_to_reproduce=task_data.steps_to_reproduce or ""
    )
    if task_data.watcher_ids:
        watchers_list = db.query(User).filter(User.id.in_(task_data.watcher_ids)).all()
        new_task.watchers = watchers_list

    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    if new_task.assignee_id and new_task.assignee_id != current_user.id:
        create_notification(
            db, new_task.assignee_id,
            "Вам назначена задача",
            f"{current_user.full_name} назначил(а) вам задачу #{new_task.id} «{new_task.title}»",
            new_task.id
        )

    res = TaskResponse.model_validate(new_task)
    res.comments_count = 0
    return res

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    res = TaskResponse.model_validate(task)
    res.comments_count = len(task.comments)
    return res

@app.patch("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    update_dict = task_data.model_dump(exclude_unset=True)
    if "watcher_ids" in update_dict:
        watcher_ids = update_dict.pop("watcher_ids")
        if watcher_ids is not None:
            watchers_list = db.query(User).filter(User.id.in_(watcher_ids)).all()
            task.watchers = watchers_list

    old_assignee = task.assignee_id
    old_status = task.status

    for field, val in update_dict.items():
        setattr(task, field, val)

    db.commit()
    db.refresh(task)

    if task.assignee_id and task.assignee_id != old_assignee and task.assignee_id != current_user.id:
        create_notification(
            db, task.assignee_id,
            "Вам назначена задача",
            f"{current_user.full_name} назначил(а) вам задачу #{task.id} «{task.title}»",
            task.id
        )

    if task.status != old_status:
        target_notify_id = task.assignee_id if (task.assignee_id and task.assignee_id != current_user.id) else (task.creator_id if task.creator_id != current_user.id else None)
        if target_notify_id:
            create_notification(
                db, target_notify_id,
                "Изменён статус задачи",
                f"Статус задачи #{task.id} «{task.title}» изменён на «{task.status.upper()}» ({current_user.full_name})",
                task.id
            )

    res = TaskResponse.model_validate(task)
    res.comments_count = len(task.comments)
    return res

@app.post("/api/tasks/{task_id}/watchers/toggle", response_model=TaskResponse)
def toggle_watcher(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if any(w.id == current_user.id for w in task.watchers):
        task.watchers = [w for w in task.watchers if w.id != current_user.id]
    else:
        task.watchers.append(current_user)

    db.commit()
    db.refresh(task)

    res = TaskResponse.model_validate(task)
    res.comments_count = len(task.comments)
    return res

@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    db.delete(task)
    db.commit()
    return None

# ----------------- Comments Endpoints ----------------- #

@app.get("/api/tasks/{task_id}/comments", response_model=List[CommentResponse])
def get_comments(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return db.query(Comment).filter(Comment.task_id == task_id).order_by(Comment.created_at.asc()).all()

@app.post("/api/tasks/{task_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    task_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    new_comment = Comment(
        task_id=task_id,
        author_id=current_user.id,
        content=comment_data.content
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    notify_user_ids = set()
    if task.assignee_id and task.assignee_id != current_user.id:
        notify_user_ids.add(task.assignee_id)
    if task.creator_id and task.creator_id != current_user.id:
        notify_user_ids.add(task.creator_id)
    for u_id in notify_user_ids:
        create_notification(
            db, u_id,
            "Новый комментарий в задаче",
            f"{current_user.full_name} оставил(а) комментарий к задаче #{task.id} «{task.title}»",
            task.id
        )

    return new_comment

@app.post("/api/tasks/{task_id}/invite", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def invite_user_to_discussion(
    task_id: int,
    req: TaskInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    invited_user = db.query(User).filter(User.id == req.user_id).first()
    if not invited_user:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    # Add to watchers if not already present
    if not any(w.id == invited_user.id for w in task.watchers):
        task.watchers.append(invited_user)

    # System comment announcing invitation
    sys_comment = Comment(
        task_id=task_id,
        author_id=current_user.id,
        content=f"📢 {current_user.full_name} пригласил(а) @{invited_user.username} ({invited_user.full_name}) к обсуждению!"
    )
    db.add(sys_comment)
    db.commit()
    db.refresh(sys_comment)

    create_notification(
        db, invited_user.id,
        "Вас пригласили к обсуждению",
        f"{current_user.full_name} пригласил(а) вас в обсуждение задачи #{task.id} «{task.title}»",
        task.id
    )

    return sys_comment

# ----------------- Attachments Endpoints ----------------- #

@app.post("/api/tasks/{task_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    validate_upload(file)
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    saved_file_path = os.path.join(UPLOADS_DIR, unique_filename)

    file_size = save_upload_capped(file, saved_file_path)
    public_url = f"/uploads/{unique_filename}"

    new_attachment = Attachment(
        task_id=task_id,
        filename=file.filename,
        file_path=public_url,
        file_size=file_size
    )
    db.add(new_attachment)
    db.commit()
    db.refresh(new_attachment)
    return new_attachment

@app.post("/api/tasks/{task_id}/attachments/batch", response_model=List[AttachmentResponse], status_code=status.HTTP_201_CREATED)
async def upload_batch_attachments(
    task_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    attachments = []
    for file in files:
        validate_upload(file)
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        saved_file_path = os.path.join(UPLOADS_DIR, unique_filename)

        file_size = save_upload_capped(file, saved_file_path)
        public_url = f"/uploads/{unique_filename}"

        new_attachment = Attachment(
            task_id=task_id,
            filename=file.filename,
            file_path=public_url,
            file_size=file_size
        )
        db.add(new_attachment)
        attachments.append(new_attachment)

    db.commit()
    for att in attachments:
        db.refresh(att)
    return attachments

@app.delete("/api/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Вложение не найдено")

    # Delete file from disk if exists
    filename = os.path.basename(attachment.file_path)
    full_path = os.path.join(UPLOADS_DIR, filename)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except Exception:
            pass

    db.delete(attachment)
    db.commit()
    return None

# ----------------- Notifications Endpoints ----------------- #

@app.get("/api/notifications", response_model=List[NotificationResponse])
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(50).all()

@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if notif:
        notif.is_read = True
        db.commit()
    return {"status": "ok"}

@app.post("/api/notifications/read-all")
def mark_all_notifications_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"status": "ok"}

# ----------------- Subtasks Endpoints ----------------- #

@app.get("/api/tasks/{task_id}/subtasks", response_model=List[SubtaskResponse])
def get_subtasks(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Subtask).filter(Subtask.task_id == task_id).order_by(Subtask.created_at.asc()).all()

@app.post("/api/tasks/{task_id}/subtasks", response_model=SubtaskResponse, status_code=status.HTTP_201_CREATED)
def create_subtask(task_id: int, subtask_data: SubtaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    subtask = Subtask(task_id=task_id, title=subtask_data.title, is_completed=False)
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return subtask

@app.patch("/api/subtasks/{subtask_id}", response_model=SubtaskResponse)
def update_subtask(subtask_id: int, subtask_data: SubtaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subtask = db.query(Subtask).filter(Subtask.id == subtask_id).first()
    if not subtask:
        raise HTTPException(status_code=404, detail="Подзадача не найдена")
    if subtask_data.title is not None:
        subtask.title = subtask_data.title
    if subtask_data.is_completed is not None:
        subtask.is_completed = subtask_data.is_completed
    db.commit()
    db.refresh(subtask)
    return subtask

@app.delete("/api/subtasks/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subtask(subtask_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subtask = db.query(Subtask).filter(Subtask.id == subtask_id).first()
    if subtask:
        db.delete(subtask)
        db.commit()
    return None

# ----------------- AI Assistant Endpoints ----------------- #

@app.post("/api/tasks/{task_id}/ai-generate-subtasks", response_model=List[SubtaskResponse])
def ai_generate_subtasks(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    title_lower = task.title.lower()
    
    if task.task_type == 'bug':
        generated_titles = [
            "Воспроизвести ошибку в тестовой среде",
            "Локализовать проблемный модуль и проверить логи",
            "Подготовить исправление (фикс) и протестировать",
            "Провести регрессионное тестирование и закрыть баг"
        ]
    elif "дизайн" in title_lower or "ui" in title_lower or "макет" in title_lower:
        generated_titles = [
            "Собрать референсы и согласовать концепцию",
            "Отрисовать фигма-макеты мобильной и десктопной версий",
            "Подготовить UI-кит и сопутствующие иконки",
            "Передать макеты разработчикам и проверить верстку"
        ]
    elif "api" in title_lower or "бэкенд" in title_lower or "бд" in title_lower:
        generated_titles = [
            "Спроектировать OpenAPI схему и структуру данных",
            "Реализовать API эндпоинты и проверить валидацию",
            "Покрыть бизнес-логику модульными тестами",
            "Составить документацию и провести интеграцию"
        ]
    else:
        generated_titles = [
            f"Анализ требований по задаче «{task.title}»",
            "Разработка основного функционала и связка компонентов",
            "Тестирование на краевые случаи и правка замечаний",
            "Финальная приёмка и публикация изменений"
        ]

    created_subtasks = []
    for st_title in generated_titles:
        sub = Subtask(task_id=task.id, title=st_title, is_completed=False)
        db.add(sub)
        created_subtasks.append(sub)
    
    db.commit()
    for s in created_subtasks:
        db.refresh(s)
    
    return created_subtasks

@app.post("/api/tasks/{task_id}/ai-summarize")
def ai_summarize_discussion(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    comments = db.query(Comment).filter(Comment.task_id == task_id).order_by(Comment.created_at.asc()).all()
    if not comments:
        return {"summary": "В этой задаче пока нет сообщений для ИИ-анализа."}

    participants = list(set([c.author.full_name for c in comments if c.author]))
    
    summary_text = f"🤖 **ИИ-Резюме обсуждения задачи «{task.title}»**:\n\n"
    summary_text += f"• **Участники ({len(participants)})**: {', '.join(participants)}\n"
    summary_text += f"• **Всего реплик**: {len(comments)}\n"
    summary_text += f"• **Ключевой итог**: Обсуждены основные детали реализации. Команда согласовала дальнейшие шаги.\n"
    summary_text += f"• **Текущий статус**: {task.status.upper()} | Приоритет: {task.priority.upper()}"

    return {"summary": summary_text}

# ----------------- Stats & Dashboard Endpoints ----------------- #

@app.get("/api/stats/my-summary", response_model=UserStats)
def get_my_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_assigned = db.query(Task).filter(Task.assignee_id == current_user.id).count()
    in_progress = db.query(Task).filter(Task.assignee_id == current_user.id, Task.status == "in_progress").count()
    completed = db.query(Task).filter(Task.assignee_id == current_user.id, Task.status == "done").count()
    urgent = db.query(Task).filter(Task.assignee_id == current_user.id, Task.priority == "urgent", Task.status != "done").count()
    created_by_me = db.query(Task).filter(Task.creator_id == current_user.id).count()
    open_bugs_count = db.query(Task).filter(Task.task_type == "bug", Task.status != "done").count()

    return UserStats(
        total_assigned=total_assigned,
        in_progress=in_progress,
        completed=completed,
        urgent=urgent,
        created_by_me=created_by_me,
        open_bugs_count=open_bugs_count
    )

@app.get("/api/stats/full")
def get_full_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    all_items = db.query(Task).all()
    tasks_list = [i for i in all_items if i.task_type == 'task']
    bugs_list = [i for i in all_items if i.task_type == 'bug']

    total_tasks = len(tasks_list)
    completed_tasks = len([t for t in tasks_list if t.status == 'done'])
    total_bugs = len(bugs_list)
    fixed_bugs = len([b for b in bugs_list if b.status == 'done'])
    critical_bugs = len([b for b in bugs_list if b.severity == 'critical' and b.status != 'done'])

    # Status breakdown
    statuses = ["todo", "in_progress", "in_review", "done"]
    status_breakdown = {s: len([i for i in all_items if i.status == s]) for s in statuses}

    # Bug severity breakdown
    severities = ["critical", "major", "minor", "trivial"]
    bug_severity_breakdown = {s: len([b for b in bugs_list if b.severity == s]) for s in severities}

    # Priority breakdown for tasks
    priorities = ["urgent", "high", "medium", "low"]
    priority_breakdown = {p: len([t for t in tasks_list if t.priority == p]) for p in priorities}

    # User performance
    users = db.query(User).all()
    user_perf = []
    for u in users:
        u_tasks = [t for t in tasks_list if t.assignee_id == u.id]
        u_tasks_done = len([t for t in u_tasks if t.status == 'done'])
        u_bugs = [b for b in bugs_list if b.assignee_id == u.id]
        u_bugs_done = len([b for b in u_bugs if b.status == 'done'])

        user_perf.append({
            "id": u.id,
            "full_name": u.full_name,
            "role": u.role,
            "avatar_color": u.avatar_color,
            "avatar_url": u.avatar_url,
            "assigned_tasks": len(u_tasks),
            "completed_tasks": u_tasks_done,
            "assigned_bugs": len(u_bugs),
            "fixed_bugs": u_bugs_done
        })

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "tasks_completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
        "total_bugs": total_bugs,
        "fixed_bugs": fixed_bugs,
        "bugs_resolution_rate": round((fixed_bugs / total_bugs * 100) if total_bugs > 0 else 0, 1),
        "critical_bugs": critical_bugs,
        "status_breakdown": status_breakdown,
        "bug_severity_breakdown": bug_severity_breakdown,
        "priority_breakdown": priority_breakdown,
        "user_performance": user_perf
    }

# ----------------- Static Files Serving ----------------- #

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
