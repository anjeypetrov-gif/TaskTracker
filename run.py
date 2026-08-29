import uvicorn
from backend.seed import seed_db

if __name__ == "__main__":
    print("Инициализация базы данных...")
    seed_db()
    print("Запуск сервера TaskTracker на http://127.0.0.1:8000...")
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
