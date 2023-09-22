from django.db import models

# Create your models here.
class StoreStatus(models.Model):
    store_id = models.CharField(max_length=100)
    timestamp_utc = models.DateTimeField()
    status = models.CharField(max_length=10)  # 'active' or 'inactive'
    def __str__(self):
        return str(self.store_id)

class BusinessHours(models.Model):
    store_id = models.CharField(max_length=100)
    day_of_week = models.IntegerField()  # 0=Monday, 6=Sunday
    start_time_local = models.TimeField()
    end_time_local = models.TimeField()
    def __str__(self):
        return str(self.store_id)

class Timezone(models.Model):
    store_id = models.CharField(max_length=100)
    timezone_str = models.CharField(max_length=100)
    def __str__(self):
        return str(self.store_id)

class Report(models.Model):
    report_id = models.CharField(max_length=100)
    csv_file = models.FileField(upload_to='csv_files/',null=True)
    status=models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.report_id




