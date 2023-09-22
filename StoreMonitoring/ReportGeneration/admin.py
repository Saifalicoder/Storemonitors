from django.contrib import admin
from . import models
# Register your models here.
admin.site.register(models.StoreStatus)
admin.site.register(models.Report)
admin.site.register(models.Timezone)
admin.site.register(models.BusinessHours)
