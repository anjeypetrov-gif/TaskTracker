import uvicorn
from backend.app import app
from backend.seed import seed_db

if __name__ == "__main__":
    print("Инициализация базы данных...")
    seed_db()
    print("Запуск сервера TaskTracker на http://0.0.0.0:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
