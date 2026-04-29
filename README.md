# Laundry Management System

A production-ready Laundry Management System built as a full-stack Django application with a polished browser UI, Django REST Framework APIs, JWT authentication, PostgreSQL-ready configuration, Docker, Gunicorn, and Nginx. The project is designed to feel like a real interview-grade system: clean APIs, role-based access control, order lifecycle management, analytics, OpenAPI docs, and deployment-friendly infrastructure.

## Features

- JWT-based authentication with signup, login, and refresh token support
- Role-based authorization for `USER` and `ADMIN`
- Responsive full-stack frontend for customers and admins
- Service catalog management
- Order creation and lifecycle tracking
- Nested order items with automatic total calculation
- Admin-only analytics endpoint
- Pagination, filtering, and structured API error responses
- OpenAPI schema with Swagger and ReDoc
- Docker, Gunicorn, Nginx, and PostgreSQL deployment support

## Tech Stack

- Python 3.12
- Django 5
- Django REST Framework
- SimpleJWT
- PostgreSQL / SQLite
- Docker Compose
- Gunicorn
- Nginx
- drf-spectacular

## Project Structure

```text
laundry-management-system/
├── config/
├── core/
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── gunicorn.conf.py
├── entrypoint.sh
├── requirements.txt
└── README.md
```

## Frontend Experience

- `/` - Browser-based LaundryHub dashboard
- Customer features:
  - Signup and login
  - Browse services
  - Create laundry orders
  - Filter and review personal order history
- Admin features:
  - View analytics
  - Create services
  - View all orders
  - Advance order status through the workflow

## API Endpoints

### Authentication

- `POST /api/auth/signup/` - Register a user
- `POST /api/auth/login/` - Obtain JWT access and refresh tokens
- `GET /api/auth/me/` - Fetch current authenticated user profile
- `POST /api/auth/token/refresh/` - Refresh JWT access token

### Services

- `GET /api/services/` - List services
- `POST /api/services/` - Create a service (`ADMIN`)
- `GET /api/services/{id}/` - Retrieve a service
- `PUT/PATCH /api/services/{id}/` - Update a service (`ADMIN`)
- `DELETE /api/services/{id}/` - Delete a service (`ADMIN`)

### Orders

- `GET /api/orders/` - List authenticated user's orders, or all orders for admin
- `POST /api/orders/` - Create a new order
- `GET /api/orders/{id}/` - Retrieve order details
- `PUT/PATCH /api/orders/{id}/` - Update an order
- `DELETE /api/orders/{id}/` - Delete a pending order
- `GET /api/orders/?status=PENDING` - Filter by order status

### Admin

- `PATCH /api/admin/orders/{id}/status/` - Update order status
- `GET /api/admin/analytics/` - Fetch order analytics

### Utility

- `GET /api/health/` - Authenticated health check
- `GET /api/schema/` - OpenAPI schema
- `GET /api/docs/swagger/` - Swagger UI
- `GET /api/docs/redoc/` - ReDoc

## Setup Instructions

### Local Development

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create environment variables:

```bash
cp .env.example .env
```

4. Apply migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

5. Create a superuser:

```bash
python manage.py createsuperuser
```

6. Start the development server:

```bash
python manage.py runserver
```

The app will be available at [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and the API docs at [http://127.0.0.1:8000/api/docs/swagger/](http://127.0.0.1:8000/api/docs/swagger/).

### Docker Setup

1. Copy env file:

```bash
cp .env.example .env
```

2. Set `DATABASE_URL` in `.env` for Docker:

```env
DATABASE_URL=postgresql://laundry_user:laundry_password@db:5432/laundry_db
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
SECURE_SSL_REDIRECT=False
```

3. Build and run:

```bash
docker compose up --build
```

The stack exposes:

- Django app on port `8000`
- Nginx on port `80`
- PostgreSQL on port `5432`

## Database Migrations and Setup Commands

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py test
```

## Deployment Steps

### Render

1. Create a new Web Service from this repository.
2. Set build command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

3. Set start command:

```bash
gunicorn --config gunicorn.conf.py config.wsgi:application
```

4. Add environment variables:
   `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DB_SSL_REQUIRED=True`
5. Provision a PostgreSQL instance and attach its URL as `DATABASE_URL`.

### Railway

1. Deploy the repository to Railway.
2. Add a PostgreSQL plugin.
3. Set the same environment variables as Render.
4. Use the same start command:

```bash
gunicorn --config gunicorn.conf.py config.wsgi:application
```

### AWS

1. Build the image with Docker.
2. Push it to ECR.
3. Run it on ECS/App Runner/EC2 behind Nginx or an ALB.
4. Provide production environment variables and an RDS PostgreSQL instance.

## Live Demo Instructions

- Local demo: run the Docker stack or `python manage.py runserver`, then open the homepage and test both customer and admin flows.
- Hosted demo: deploy on Render/Railway/AWS, configure production env vars, and share the base URL with `/api/docs/swagger/`.
- Recommended recruiter flow: open the homepage, create a customer account, place an order, then log in as admin to update statuses and show analytics.

## Sample Payloads

### Signup

```json
{
  "email": "jane@example.com",
  "username": "janedoe",
  "password": "StrongPass123!",
  "confirm_password": "StrongPass123!"
}
```

### Create Order

```json
{
  "pickup_date": "2026-05-01",
  "items": [
    {
      "service_id": 1,
      "quantity": 2
    }
  ]
}
```

## Testing

Basic API coverage is included for:

- user signup
- order creation with total price calculation
- admin status update flow

Run:

```bash
python manage.py test
```
