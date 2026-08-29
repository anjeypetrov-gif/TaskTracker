import os
import shutil
from backend.database import engine, Base, SessionLocal
from backend.models import User, Task, Comment, Attachment, task_watchers
from backend.auth import hash_password

def reset_database():
    print("=== Clearing database and uploaded files ===")

    # 1. Clear uploads folder
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    if os.path.exists(uploads_dir):
        for filename in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
        print("Uploads folder cleared.")

    # 2. Reset database tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database tables recreated.")

    db = SessionLocal()
    try:
        # 3. Create default clean Admin user
        admin_user = User(
            username="admin",
            full_name="Администратор",
            email="admin@tracker.local",
            hashed_password=hash_password("admin123"),
            avatar_color="#3b82f6",
            role="Project Manager / Администратор"
        )
        db.add(admin_user)
        db.commit()
        print("Default Administrator created successfully:")
        print("   - Username: admin")
        print("   - Password: admin123")
        print("Database is clean and ready for real testing!")
    except Exception as e:
        db.rollback()
        print(f"Error creating administrator: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_database()
