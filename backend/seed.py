from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import User, Task, Comment, UserActivity, task_watchers
from .auth import hash_password

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if DB already populated
    if db.query(User).count() > 0:
        db.close()
        return

    print("Populating database with commercial dataset...")

    now = datetime.now(timezone.utc)
    curr_m = datetime.now().strftime("%Y-%m")

    # 1. Corporate Team Users
    u_admin = User(
        username="admin",
        full_name="Александр Громов",
        email="gromov@company.ru",
        hashed_password=hash_password("admin123"),
        avatar_color="#3b82f6",
        role="Project Manager / CPO",
        created_at=now - timedelta(days=30),
        last_seen=now,
        last_login=now
    )
    u_alex = User(
        username="alex",
        full_name="Алексей Смирнов",
        email="alex@company.ru",
        hashed_password=hash_password("alex123"),
        avatar_color="#10b981",
        role="Senior Frontend Developer",
        created_at=now - timedelta(days=25),
        last_seen=now - timedelta(minutes=2),
        last_login=now - timedelta(hours=1)
    )
    u_dmitry = User(
        username="dmitry",
        full_name="Дмитрий Соколов",
        email="dmitry@company.ru",
        hashed_password=hash_password("dmitry123"),
        avatar_color="#8b5cf6",
        role="Lead Backend Developer",
        created_at=now - timedelta(days=20),
        last_seen=now - timedelta(minutes=10),
        last_login=now - timedelta(hours=3)
    )
    u_maria = User(
        username="maria",
        full_name="Мария Иванова",
        email="maria@company.ru",
        hashed_password=hash_password("maria123"),
        avatar_color="#ec4899",
        role="UI/UX Lead Designer",
        created_at=now - timedelta(days=18),
        last_seen=now - timedelta(minutes=25),
        last_login=now - timedelta(hours=5)
    )
    u_elena = User(
        username="elena",
        full_name="Елена Кузнецова",
        email="elena@company.ru",
        hashed_password=hash_password("elena123"),
        avatar_color="#f59e0b",
        role="QA Lead / Тестировщик",
        created_at=now - timedelta(days=15),
        last_seen=now - timedelta(hours=1),
        last_login=now - timedelta(days=1)
    )
    u_sergey = User(
        username="sergey",
        full_name="Сергей Морозов",
        email="sergey@company.ru",
        hashed_password=hash_password("sergey123"),
        avatar_color="#06b6d4",
        role="DevOps & Security Engineer",
        created_at=now - timedelta(days=12),
        last_seen=now - timedelta(hours=4),
        last_login=now - timedelta(days=2)
    )

    db.add_all([u_admin, u_alex, u_dmitry, u_maria, u_elena, u_sergey])
    db.commit()
    for u in [u_admin, u_alex, u_dmitry, u_maria, u_elena, u_sergey]:
        db.refresh(u)

    # 2. Add Login Activities Audit Log
    activities = [
        UserActivity(user_id=u_admin.id, action="Вход в систему", created_at=now - timedelta(minutes=5)),
        UserActivity(user_id=u_alex.id, action="Вход в систему", created_at=now - timedelta(hours=1)),
        UserActivity(user_id=u_dmitry.id, action="Вход в систему", created_at=now - timedelta(hours=3)),
        UserActivity(user_id=u_maria.id, action="Вход в систему", created_at=now - timedelta(hours=5)),
        UserActivity(user_id=u_elena.id, action="Регистрация аккаунта", created_at=now - timedelta(days=15)),
        UserActivity(user_id=u_sergey.id, action="Регистрация аккаунта", created_at=now - timedelta(days=12))
    ]
    db.add_all(activities)

    # 3. Tasks Dataset
    t1 = Task(
        title="Разработать дизайн-систему продуктовой панели",
        description="Подготовить базовые токены стилей (цвета, шрифты, отступы) и интерфейсную библиотеку компонентов в Figma.",
        status="done",
        priority="high",
        creator_id=u_admin.id,
        assignee_id=u_maria.id,
        due_date=f"{curr_m}-05",
        tags="UI/UX,Design,Figma"
    )

    t2 = Task(
        title="Интеграция авторизации JWT и защита роутов",
        description="Реализовать обработку Bearer токенов на бэкенде, сохранение сессии и авто-редирект при истёкшем токене.",
        status="in_progress",
        priority="urgent",
        creator_id=u_admin.id,
        assignee_id=u_alex.id,
        due_date=f"{curr_m}-12",
        tags="Frontend,Security"
    )

    t3 = Task(
        title="Оптимизировать SQL-индексы и скорость запросов аналитики",
        description="Добавить составные индексы в SQLite для таблиц tasks и comments для ускорения сборки метрик продуктивности.",
        status="in_review",
        priority="medium",
        creator_id=u_alex.id,
        assignee_id=u_dmitry.id,
        due_date=f"{curr_m}-18",
        tags="Backend,Database,Performance"
    )

    t4 = Task(
        title="Тестирование адаптивности двухколоночного модального окна",
        description="Проверить корректность отображения чата и блока задачи на мобильных устройствах (ширина от 360px до 768px).",
        status="in_progress",
        priority="low",
        creator_id=u_maria.id,
        assignee_id=u_elena.id,
        due_date=f"{curr_m}-24",
        tags="QA,Mobile,Responsive"
    )

    t5 = Task(
        title="Настройка Docker-контейнеризации и CI/CD автоматизации",
        description="Подготовить Dockerfile и конфигурации деплоя для автоматической сборки на Render и Railway при push в main.",
        status="in_progress",
        priority="high",
        creator_id=u_admin.id,
        assignee_id=u_sergey.id,
        due_date=f"{curr_m}-28",
        tags="DevOps,Docker,CI/CD"
    )

    # 4. Bugs Dataset
    b1 = Task(
        title="Ошибка при повторном клике на кнопку 'Создать задачу'",
        description="При медленном интернет-соединении и частом клике на кнопку отправки формы создавались дублирующие задачи.",
        status="done",
        priority="urgent",
        task_type="bug",
        severity="critical",
        steps_to_reproduce="1. Открыть форму создания задачи\n2. Заполнить название\n3. Включить 3G пресет сети\n4. Быстро нажать на кнопку 'Создать' несколько раз",
        creator_id=u_elena.id,
        assignee_id=u_alex.id,
        due_date=f"{curr_m}-08",
        tags="Frontend,Bug"
    )

    b2 = Task(
        title="Смещение фокуса в поле ввода командного чата на iOS Safari",
        description="При открытии экранной клавиатуры на устройствах iPhone поле ввода чата частично перекрывается нижней панелью браузера.",
        status="in_progress",
        priority="high",
        task_type="bug",
        severity="major",
        steps_to_reproduce="1. Открыть карточку задачи на iPhone (Safari)\n2. Кликнуть на поле 'Написать сообщение'\n3. Поле ввода уходит под панель навигации",
        creator_id=u_maria.id,
        assignee_id=u_alex.id,
        due_date=f"{curr_m}-15",
        tags="Mobile,Safari,UI"
    )

    b3 = Task(
        title="Ошибка 500 при загрузке файлов с кириллическими символами",
        description="Вложение с именем вида 'отчет_2026.pdf' вызывает сбой валидации пути файла на бэкенде.",
        status="todo",
        priority="urgent",
        task_type="bug",
        severity="critical",
        steps_to_reproduce="1. Открыть чат задачи\n2. Нажать скрепку 📎\n3. Выбрать документ с кириллицей в имени\n4. Отправить",
        creator_id=u_elena.id,
        assignee_id=u_dmitry.id,
        due_date=f"{curr_m}-22",
        tags="Backend,Bug,Files"
    )

    db.add_all([t1, t2, t3, t4, t5, b1, b2, b3])
    db.commit()

    # Assign Watchers
    t2.watchers.extend([u_admin, u_maria, u_elena])
    b2.watchers.extend([u_maria, u_alex])
    db.commit()

    # 5. Comments & Chat Discussion Dataset
    c1 = Comment(
        task_id=t2.id,
        author_id=u_admin.id,
        content="📢 @alex обрати внимание на верстку двух колонок. Коллега @maria подготовила финальные макеты!",
        created_at=now - timedelta(hours=4)
    )
    c2 = Comment(
        task_id=t2.id,
        author_id=u_alex.id,
        content="Принял в работу! Авторизацию по JWT завершил, тестирую автопродление сессий.",
        created_at=now - timedelta(hours=2)
    )
    c3 = Comment(
        task_id=t2.id,
        author_id=u_maria.id,
        content="📎 **Прикреплен(ы) файл(ы):** preview_ui_v2.png",
        created_at=now - timedelta(minutes=30)
    )

    c4 = Comment(
        task_id=b1.id,
        author_id=u_elena.id,
        content="Обнаружен блокер на прод-стенде при отправке форм при медленном 3G.",
        created_at=now - timedelta(days=2)
    )
    c5 = Comment(
        task_id=b1.id,
        author_id=u_alex.id,
        content="Исправил! Добавил состояние submittingTask, блокировку disabled и спиннер загрузки.",
        created_at=now - timedelta(days=1)
    )

    db.add_all([c1, c2, c3, c4, c5])
    db.commit()
    db.close()

    print("Commercial dataset successfully populated!")

if __name__ == "__main__":
    seed_db()
