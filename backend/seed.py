from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import User, Task, Comment
from .auth import hash_password

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if users already exist
    if db.query(User).count() > 0:
        db.close()
        return

    print("Наполнение базы данных демонстрационными данными...")

    # Create users
    u_admin = User(
        username="admin",
        full_name="Александр Громов",
        email="admin@tracker.local",
        hashed_password=hash_password("admin123"),
        avatar_color="#3b82f6",
        role="Project Manager"
    )
    u_alex = User(
        username="alex",
        full_name="Алексей Смирнов",
        email="alex@tracker.local",
        hashed_password=hash_password("alex123"),
        avatar_color="#10b981",
        role="Senior Frontend Developer"
    )
    u_maria = User(
        username="maria",
        full_name="Мария Иванова",
        email="maria@tracker.local",
        hashed_password=hash_password("maria123"),
        avatar_color="#ec4899",
        role="UI/UX Дизайнер"
    )
    u_dmitry = User(
        username="dmitry",
        full_name="Дмитрий Соколов",
        email="dmitry@tracker.local",
        hashed_password=hash_password("dmitry123"),
        avatar_color="#8b5cf6",
        role="Backend Разработчик"
    )

    db.add_all([u_admin, u_alex, u_maria, u_dmitry])
    db.commit()
    db.refresh(u_admin)
    db.refresh(u_alex)
    db.refresh(u_maria)
    db.refresh(u_dmitry)

    curr_m = datetime.now().strftime("%Y-%m")

    # Create tasks
    t1 = Task(
        title="Разработать дизайн-систему личного кабинета",
        description="Подготовить макеты UI компонентов (кнопки, карточки задач, графики статистики) в Figma и согласовать цветовые палитры.",
        status="done",
        priority="high",
        creator_id=u_admin.id,
        assignee_id=u_maria.id,
        due_date=f"{curr_m}-05",
        tags="UI/UX,Design"
    )
    t2 = Task(
        title="Интеграция авторизации JWT на Frontend",
        description="Реализовать сохранение токенов в localStorage, автообновление сессии и редирект неавторизованных пользователей на страницу входа.",
        status="in_progress",
        priority="urgent",
        creator_id=u_admin.id,
        assignee_id=u_alex.id,
        due_date=f"{curr_m}-10",
        tags="Frontend,Security"
    )
    t3 = Task(
        title="Оптимизировать SQL-запросы статистики личного кабинета",
        description="Добавить индексы для таблицы tasks по полю assignee_id и status для ускорения генерации отчёта продуктивности.",
        status="in_review",
        priority="medium",
        creator_id=u_alex.id,
        assignee_id=u_dmitry.id,
        due_date=f"{curr_m}-15",
        tags="Backend,Database"
    )
    t4 = Task(
        title="Тестирование отображения Kanban-доски на мобильных устройствах",
        description="Проверить скролл колонок и перетаскивание карточек на экранах с шириной меньше 640px.",
        status="todo",
        priority="low",
        creator_id=u_maria.id,
        assignee_id=u_alex.id,
        due_date=f"{curr_m}-20",
        tags="Mobile,QA"
    )
    t5 = Task(
        title="Настройка автоматических уведомлений по дедлайнам",
        description="Реализовать фоновую задачу для проверки задач, у которых дедлайн наступает в ближайшие 24 часа.",
        status="todo",
        priority="high",
        creator_id=u_admin.id,
        assignee_id=u_dmitry.id,
        due_date=f"{curr_m}-25",
        tags="Backend,Feature"
    )

    # Create bugs
    b1 = Task(
        title="Ошибка 500 при загрузке файла с пробелом в имени",
        description="При загрузке вложения с символами кириллицы или пробелами сервер возвращает ошибку 500 Internal Server Error.",
        status="todo",
        priority="urgent",
        task_type="bug",
        severity="critical",
        steps_to_reproduce="1. Перейти в задачу\n2. Нажать 'Прикрепить файл'\n3. Выбрать файл 'отчет 2026.pdf'\n4. Нажать Загрузить",
        creator_id=u_alex.id,
        assignee_id=u_dmitry.id,
        due_date=f"{curr_m}-12",
        tags="Bug,Backend,Critical"
    )
    b2 = Task(
        title="Смещение текста кнопки в Safari 17",
        description="Текст кнопки 'Зарегистрироваться' вылезает за нижнюю рамку в браузере Safari.",
        status="in_progress",
        priority="high",
        task_type="bug",
        severity="major",
        steps_to_reproduce="1. Открыть браузер Safari 17\n2. Переключиться на форму регистрации",
        creator_id=u_maria.id,
        assignee_id=u_alex.id,
        due_date=f"{curr_m}-18",
        tags="Bug,UI,Safari"
    )
    b3 = Task(
        title="Некорректная дата в футере после полуночи",
        description="При переходе даты на новые сутки счетчик дней не обновляется без перезагрузки страницы.",
        status="done",
        priority="low",
        task_type="bug",
        severity="minor",
        steps_to_reproduce="1. Оставить открытой вкладку с 23:59 до 00:01\n2. Посмотреть на дату дедлайна",
        creator_id=u_admin.id,
        assignee_id=u_alex.id,
        due_date=f"{curr_m}-28",
        tags="Bug,Frontend"
    )

    db.add_all([t1, t2, t3, t4, t5, b1, b2, b3])
    db.commit()
    db.refresh(t1)
    db.refresh(t2)
    db.refresh(b1)

    # Comments
    c1 = Comment(
        task_id=t2.id,
        author_id=u_admin.id,
        content="Алексей, обрати внимание, чтобы при ошибке 401 происходил плавный переход на форму логина."
    )
    c2 = Comment(
        task_id=t2.id,
        author_id=u_alex.id,
        content="Принято! Уже добавил обработчик в fetch-перехватчик."
    )
    c3 = Comment(
        task_id=t1.id,
        author_id=u_maria.id,
        content="Макеты загружены в фигму, статус готовности 100%."
    )

    db.add_all([c1, c2, c3])
    db.commit()
    db.close()
    print("Демо-данные успешно загружены.")

if __name__ == "__main__":
    seed_db()
