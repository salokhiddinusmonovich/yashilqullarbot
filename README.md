
# yashilqullarbot
=======
# django-aiogram-template

Шаблон для создания Telegram-бота на AIOgram с админкой Django.


## Запуск
- скачайте проект
- файл ".env.dist" переименуйте в ".env" и пропишите необходимые настройки
- выполните команды (должен быть запущен Docker):
```bash
# смонтировать контейнер:
docker-compose build
# запустить контейнер:
docker-compose up -d
# остановить контейнер:
docker-compose down
# если в код были внесены изменения, необходимо заново смонтировать контейнер
```


## Миграции
Команды выполняются при запущенном контейнере
```bash
# создание миграций
docker-compose exec web sh -c "python manage.py makemigrations"
# применение миграций
docker-compose exec web sh -c "python manage.py migrate"
# создание суперпользователя
docker-compose exec web sh -c "python manage.py createsuperuser"
```

Теперь можно перейти на http://0.0.0.0:8000/admin/ и войти в админку под суперпользователем

## Просмотр БД через Adminer
Посетите http://localhost:8080/ и введите следующие параметры:
- System: PostgreSQL
- Server: db
- Username: postgres
- Password: postgres
- Database: template-db
>>>>>>> 3b1241a (salom)
# yashilqullarbot
# yashilqullarbot




AUTH

POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET /api/auth/me
POST /api/auth/refresh

USERS

GET /api/users/:id
PATCH /api/users/:id
GET /api/users/leaderboard

BLOG

GET /api/posts
GET /api/posts/:id
POST /api/posts
PATCH /api/posts/:id
DELETE /api/posts/:id
POST /api/posts/:id/like

COMMENTS

GET /api/comments?postId=xxx
POST /api/comments
DELETE /api/comments/:id
POST /api/comments/:id/like

PROJECTS

GET /api/projects
GET /api/projects/:id
POST /api/projects
PATCH /api/projects/:id

CONTACT

POST /api/contact

UPLOAD

POST /api/upload/image