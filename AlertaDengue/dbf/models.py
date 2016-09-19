from django.db import models
from datetime import date

def current_year():
    return date.today().year

class DBF(models.Model):
    file = models.FileField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    export_date = models.DateField()
    notification_year = models.IntegerField(default=current_year)
