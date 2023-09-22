from django.urls import path
from . import views
urlpatterns = [
    path("", views.index,name="index"),
    path("getbusinesshours/", views.getBusinessHours,name="getbusinesshours"),
    path("getstorestatus/", views.getStoreStatus,name="getstorestatus"),
    path("gettimezone/", views.getTimezones,name="gettimezone"),
    path("getreportforstore/<storeid>", views.getreportforstore,name="getreportforstore"),
    path("getreport/<report_id>", views.getreport,name="getreport"),
    path("trigger_report/", views.triggerreport,name="triggerreport"),
    path("delete_all/", views.cleardbtables,name="delete_all"),
]