import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks(["dealerships", "suppliers", "offers"])

app.conf.beat_schedule = {
    "dealership-purchase-cars-every-10-minutes": {
        "task": "dealerships.tasks.dealership_purchase_cars",
        "schedule": crontab(minute="*/10"),
    },
    "update-supplier-preferences-every-hour": {
        "task": "suppliers.tasks.update_supplier_preferences",
        "schedule": crontab(minute=0),
    },
}

app.conf.beat_scheduler = "celery.beat:PersistentScheduler"
