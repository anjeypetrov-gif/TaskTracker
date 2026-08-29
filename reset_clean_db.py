import os
import secrets
import shutil
from backend.database import engine, Base, SessionLocal
from backend.models import User, Task, Comment, Attachment, task_watchers
from backend.auth import hash_password

def _confirm_destructive_action():
    """This script drops every table. If DATABASE_URL is set, we're almost
    certainly pointed at a real (Postgres/Render) database rather than the
    local SQLite file, so refuse to run silently — require an explicit
    confirmation so nobody wipes production data by running this from the
    wrong terminal."""
    if not os.getenv("DATABASE_URL"):
        return  # local SQLite dev db — proceed as before
    if os.getenv("CONFIRM_DESTRUCTIVE_RESET") == "yes":
        return
    print("DATABASE_URL is set — this looks like a non-local database.")
    print("This script permanently deletes ALL tasks, users, comments and files.")
    answer = input("Type YES to permanently wipe this database: ").strip()
    if answer != "YES":
        print("Aborted. No changes made.")
        raise SystemExit(1)

def reset_database():
    _confirm_destructive_action()
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
        # 3. Create default clean Admin user with a freshly generated password
        # (not a fixed "admin123" — that's exactly the kind of default
        # credential that gets guessed if this ever faces the internet).
        admin_password = secrets.token_urlsafe(9)
        admin_user = User(
            username="admin",
            full_name="Администратор",
            email="admin@tracker.local",
            hashed_password=hash_password(admin_password),
            avatar_color="#3b82f6",
            role="Project Manager / Администратор"
        )
        db.add(admin_user)
        db.commit()
        print("Default Administrator created successfully:")
        print("   - Username: admin")
        print(f"   - Password: {admin_password}")
        print("   (save this now — it is not stored anywhere else)")
        print("Database is clean and ready for real testing!")
    except Exception as e:
        db.rollback()
        print(f"Error creating administrator: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_database()
