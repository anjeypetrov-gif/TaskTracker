import uvicorn
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    print("==================================================")
    print("TaskTracker & BugTracker Enterprise Server")
    print("==================================================")
    print("Local URL:      http://127.0.0.1:8000")
    print("Network Wi-Fi:  http://0.0.0.0:8000")
    print("==================================================")

    try:
        from backend.seed import seed_db
        seed_db()
    except Exception as e:
        print(f"Seed warning: {e}")

    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
