# Dealership Management System

A comprehensive Django REST API system for managing car dealerships, suppliers, inventory, sales, customers, and promotions.

## Features

- **Car Models Management**: Manage car specifications, brands, and models
- **Customer Management**: Customer profiles with loyalty tracking and purchase history
- **Dealership Operations**: Dealership management with inventory and sales tracking
- **Supplier Management**: Supplier catalog with pricing and availability
- **Sales System**: Complete sales workflow with discount and promotion handling
- **Offers Matching**: Smart offer matching system connecting customers with dealerships
- **Promotions**: Flexible promotion system with dealership-specific discounts
- **Authentication**: JWT-based authentication with email verification
- **Geolocation**: PostGIS support for dealership location-based features
- **Async Tasks**: Celery integration for background task processing
- **Statistics & Analytics**: Comprehensive reporting and analytics endpoints

## Technologies

- **Framework**: Django 5.1.2
- **API**: Django REST Framework 3.15.2
- **Database**: PostgreSQL with PostGIS extension
- **Cache**: Redis
- **Task Queue**: Celery with Redis broker
- **Authentication**: JWT (Simple JWT)
- **Documentation**: Swagger/ReDoc (drf-yasg)
- **Testing**: Pytest with pytest-django

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 13+ with PostGIS extension
- Redis 6+

## API Documentation

Once the server is running, access the API documentation at:

- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/
- **JSON Schema**: http://localhost:8000/swagger.json

## API Endpoints

### Authentication

- `POST /api/v1/auth/register/` - Register new user
- `POST /api/v1/auth/token/` - Obtain JWT token
- `POST /api/v1/auth/token/refresh/` - Refresh JWT token
- `POST /api/v1/auth/logout/` - Logout (blacklist token)
- `GET /api/v1/auth/verify-email/<uidb64>/<token>/` - Verify email
- `POST /api/v1/auth/request-password-reset/` - Request password reset
- `POST /api/v1/auth/reset-password/<uidb64>/<token>/` - Reset password
- `POST /api/v1/auth/change-password/` - Change password
- `POST /api/v1/auth/change-email/` - Request email change
- `POST /api/v1/auth/change-username/` - Request username change

### Car Models

- `GET /api/v1/cars/` - List car models
- `POST /api/v1/cars/` - Create car model (admin only)
- `GET /api/v1/cars/{id}/` - Get car model details
- `PUT /api/v1/cars/{id}/` - Update car model (admin only)
- `DELETE /api/v1/cars/{id}/` - Soft delete car model (admin only)
- `GET /api/v1/cars/popular/` - Get popular models
- `GET /api/v1/cars/brands/` - Get list of brands
- `POST /api/v1/cars/{id}/restore/` - Restore deleted model (admin only)

### Customers

- `GET /api/v1/customers/` - List customers
- `POST /api/v1/customers/` - Create customer (admin only)
- `GET /api/v1/customers/{id}/` - Get customer details
- `GET /api/v1/customers/me/` - Get current customer profile
- `PATCH /api/v1/customers/update_profile/` - Update own profile
- `GET /api/v1/customers/my_purchases/` - Get customer's purchases
- `GET /api/v1/customers/{id}/statistics/` - Get customer statistics
- `POST /api/v1/customers/{id}/update_balance/` - Update balance (admin only)
- `GET /api/v1/customers/vip_customers/` - Get VIP customers list (admin only)

### Dealerships

- `GET /api/v1/dealerships/` - List dealerships
- `POST /api/v1/dealerships/` - Create dealership (admin only)
- `GET /api/v1/dealerships/{id}/` - Get dealership details
- `GET /api/v1/dealerships/{id}/inventory/` - Get dealership inventory
- `GET /api/v1/dealerships/{id}/sales/` - Get dealership sales
- `GET /api/v1/dealerships/{id}/statistics/` - Get dealership statistics
- `GET /api/v1/dealerships/top/` - Get top dealerships

### Suppliers

- `GET /api/v1/suppliers/` - List suppliers
- `POST /api/v1/suppliers/` - Create supplier (admin only)
- `GET /api/v1/suppliers/{id}/` - Get supplier details
- `GET /api/v1/suppliers/{id}/catalog/` - Get supplier catalog
- `GET /api/v1/suppliers/{id}/statistics/` - Get supplier statistics
- `GET /api/v1/suppliers/top/` - Get top suppliers

### Offers

- `GET /api/v1/offers/` - List offers
- `POST /api/v1/offers/` - Create offer
- `GET /api/v1/offers/{id}/` - Get offer details
- `GET /api/v1/offers/my_offers/` - Get customer's offers
- `POST /api/v1/offers/{id}/cancel/` - Cancel offer
- `GET /api/v1/offers/{id}/match_dealerships/` - Find matching dealerships

### Promotions

- `GET /api/v1/promotions/` - List promotions
- `POST /api/v1/promotions/` - Create promotion (admin only)
- `GET /api/v1/promotions/{id}/` - Get promotion details
- `GET /api/v1/promotions/active/` - Get active promotions
- `GET /api/v1/promotions/{id}/statistics/` - Get promotion statistics

### Sales

- `GET /api/v1/sales/` - List sales
- `POST /api/v1/sales/` - Create sale (admin only)
- `GET /api/v1/sales/{id}/` - Get sale details
- `GET /api/v1/sales/statistics/` - Get sales statistics

## Project Structure

```
django-task/
├── cars/                   # Car models app
│   ├── models.py          # CarModel
│   ├── views.py           # API views
│   ├── serializers.py     # DRF serializers
│   ├── services.py        # Business logic
│   └── filters.py         # Query filters
├── customers/             # Customers and sales app
│   ├── models.py         # Customer, Sale
│   ├── views.py          # API views
│   ├── serializers.py    # DRF serializers
│   └── services.py       # Business logic
├── dealerships/          # Dealerships app
│   ├── models.py         # Dealership, Inventory, Purchase, Preference
│   ├── views.py          # API views
│   ├── serializers.py    # DRF serializers
│   ├── services.py       # Business logic
│   └── tasks.py          # Celery tasks
├── suppliers/            # Suppliers app
│   ├── models.py         # Supplier, SupplierCar, SupplierDiscount
│   ├── views.py          # API views
│   ├── serializers.py    # DRF serializers
│   ├── services.py       # Business logic
│   └── tasks.py          # Celery tasks
├── offers/               # Offers matching app
│   ├── models.py         # Offer
│   ├── views.py          # API views
│   ├── serializers.py    # DRF serializers
│   ├── services.py       # Business logic
│   └── tasks.py          # Celery tasks
├── promotions/           # Promotions app
│   ├── models.py         # Promotion, PromotionDealership, PromotionSupplier
│   ├── views.py          # API views
│   ├── serializers.py    # DRF serializers
│   └── services.py       # Business logic
├── config/               # Project configuration
│   ├── settings.py       # Django settings
│   ├── urls.py           # URL configuration
│   ├── celery.py         # Celery configuration
│   ├── authentication.py # Auth views
│   ├── permissions.py    # Custom permissions
│   ├── emails.py         # Email service
│   ├── services.py       # Auth services
│   └── models.py         # Base model
└── manage.py
```

## Business Logic

### Soft Delete Pattern

All models inherit from `BaseModel` which implements soft delete functionality:
- Records are never permanently deleted
- `is_active` flag marks deletion status
- `soft_delete()` and `restore()` methods available

### Service Layer Architecture

Business logic is separated into service classes:
- Views handle HTTP requests/responses
- Services contain business logic
- Models define data structure
- Cleaner code and easier testing

### Offer Matching System

Automated offer matching process:
1. Customer creates offer with max price and car model
2. Background task searches dealerships with matching inventory
3. Best matches are found based on price and availability
4. Customer is notified of matches

### Promotion System

Flexible promotion system:
- Time-based promotions with start/end dates
- Different discount rates for different dealerships
- Automatic application during sales
- Promotion statistics tracking

### Inventory Management

Real-time inventory tracking:
- Automatic inventory updates on purchase
- Low stock notifications
- Multi-dealership inventory management


## Production Deployment

### Using Docker

1. Build images:
```bash
docker-compose -f docker-compose.prod.yml build
```

2. Start services:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. Run migrations:
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

4. Collect static files:
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### Environment Variables

For production, ensure these environment variables are properly set:
- `DEBUG=False`
- `SECRET_KEY` - Strong random key
- `ALLOWED_HOSTS` - Your domain names
- Database credentials
- Redis credentials
- Email server credentials
- `SITE_URL` - Your domain URL

## Security Considerations

- JWT tokens with blacklisting
- Email verification required
- Permission-based access control
- Secure password validation
- HTTPS in production (configured in nginx)
- CSRF protection
- SQL injection protection (Django ORM)
- XSS protection

## Performance Optimization

- Database query optimization with `select_related`/`prefetch_related`
- Redis caching for frequently accessed data
- Celery for async task processing
- Database indexing on frequently queried fields
- Pagination for large datasets
