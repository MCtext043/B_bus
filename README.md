# Система Расписания Автобусов

Веб-приложение для просмотра расписания автобусов с административной панелью управления.

## Возможности

### Для обычных пользователей:
- Просмотр расписания всех маршрутов без авторизации
- Фильтрация по дням недели (все дни, будни, выходные)
- Адаптивный дизайн для мобильных устройств

### Для администраторов:
- Регистрация и авторизация
- Управление маршрутами (добавление)
- Управление расписанием (добавление рейсов)
- Полный контроль над данными

## Технологии

- **Backend**: FastAPI
- **Frontend**: Bootstrap 5, Jinja2 Templates
- **База данных**: SQLite (по умолчанию)
- **Аутентификация**: JWT токены

## Установка и запуск

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Заполнение базы данных тестовыми данными

```bash
python fill_data.py
```

### 3. Запуск приложения

```bash
python main.py
```

Или через uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 4. Открытие в браузере

Перейдите по адресу: `http://localhost:8001`

## Использование

### Просмотр расписания
- Главная страница: `http://localhost:8001`
- Расписание: `http://localhost:8001/schedule`

### Администрирование
1. Регистрация администратора: `http://localhost:8001/admin/register`
2. Вход: `http://localhost:8001/admin/login`
3. Панель управления: `http://localhost:8001/admin/dashboard`

## Тестовые данные

После запуска `fill_data.py` будут созданы:

- **Администратор**: `admin` / `admin123`
- **Маршруты**: 1, 5A, 12Б, 7 с различными расписаниями

## Структура проекта

```
bus_schedule/
├── main.py              # Основной файл приложения FastAPI
├── models.py            # Модели базы данных (SQLAlchemy)
├── database.py          # Настройка подключения к БД
├── auth.py              # Логика аутентификации
├── fill_data.py         # Заполнение тестовыми данными
├── requirements.txt     # Зависимости Python
├── README.md           # Документация
├── templates/          # HTML шаблоны
│   ├── base.html
│   ├── index.html
│   ├── schedule.html
│   ├── admin_login.html
│   ├── admin_register.html
│   ├── admin_dashboard.html
│   ├── admin_routes.html
│   ├── admin_route_form.html
│   ├── admin_schedules.html
│   └── admin_schedule_form.html
└── static/             # Статические файлы (CSS, JS)
```

## API endpoints

### Публичные
- `GET /` - Главная страница
- `GET /schedule` - Просмотр расписания

### Администраторские
- `GET /admin/login` - Страница входа
- `POST /admin/login` - Авторизация
- `GET /admin/register` - Страница регистрации
- `POST /admin/register` - Регистрация
- `GET /admin/dashboard` - Панель управления
- `GET /admin/routes` - Список маршрутов
- `POST /admin/route/add` - Добавление маршрута
- `GET /admin/route/{id}/schedules` - Расписание маршрута
- `POST /admin/route/{id}/schedule/add` - Добавление рейса
- `POST /admin/logout` - Выход

## Безопасность

- JWT токены для аутентификации администраторов
- Пароли хешируются с использованием bcrypt
- Защищенные cookie для хранения токенов

## Настройка

### Переменные окружения

```bash
# URL базы данных (по умолчанию SQLite)
DATABASE_URL=sqlite:///./bus_schedule.db

# Секретный ключ для JWT (измените в продакшене!)
SECRET_KEY=your-secret-key-change-in-production
```

## Разработка

Для запуска в режиме разработки используйте:

```bash
uvicorn main:app --reload
```

## Лицензия

MIT License
