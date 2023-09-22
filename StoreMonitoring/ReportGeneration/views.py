
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from asgiref.sync import async_to_sync
import pandas as pd
from .models import *
from datetime import datetime
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import pytz
import uuid
from django.db.models import Q
import csv
import io
from django.core.files.base import ContentFile
# Create your views here.
@api_view(['GET'])
def index(request):
    return Response({"message": "Hello, world!"})


@api_view(['GET'])
def getStoreStatus(request):
    open_excel = pd.read_csv(
           "D:\Downloads\store status.csv"
        )
    # Define the format of your datetime string
    format_str = "%Y-%m-%d %H:%M:%S.%f %Z"
    for index, row in open_excel.iterrows():
            datetime_obj = datetime.strptime(row[2], format_str)
            datetime_obj = datetime_obj.replace(tzinfo=pytz.UTC)
            entry =StoreStatus(store_id=row[0],status=row[1],timestamp_utc=datetime_obj)
            entry.save()
        
    return Response({"message": "loaded store status successfully"})

@api_view(['GET'])
def getBusinessHours(request):
    
    open_excel = pd.read_csv(
           "D:\Downloads\Menu hours.csv"
        )
    for index, row in open_excel.iterrows():
        
            entry =BusinessHours(store_id=row[0],day_of_week=row[1],start_time_local=row[2],end_time_local=row[3])
            entry.save()
        

    
    return Response({"message": "Loaded Business hours successfully"})

@api_view(['GET'])
def getTimezones(request):
    open_excel = pd.read_csv(
            "D:\Downloads\zonedata.csv"
        )
    for index, row in open_excel.iterrows():
        
            entry =Timezone(store_id=row[0],timezone_str=row[1])
            entry.save()
        
    return Response({"message": "Loaded Timezones successfully"})


def convert_to_utc(local_time_str, timezone_str, day):
    # Parse the local time string into a datetime object
    local_time = datetime.strptime(str(local_time_str), '%H:%M:%S')

    # Get the store's timezone
    store_timezone = pytz.timezone(timezone_str)

    # Get the current date in the store's timezone
    current_date = datetime.now(tz=store_timezone).date()

    # Combine the current date and local time to create a datetime object
    local_datetime = store_timezone.localize(
        datetime(current_date.year, current_date.month, current_date.day,
                 hour=local_time.hour, minute=local_time.minute, second=local_time.second)
    )

    # Convert the local datetime to UTC
    utc_datetime = local_datetime.astimezone(pytz.UTC)
    return utc_datetime

@api_view(['GET'])
def getreportforstore(request,storeid):
    local_time = datetime.now(pytz.timezone('Asia/Kolkata'))
    print(local_time)
# Convert to UTC
    # utc_time = local_time.astimezone(pytz.utc)
    utc_time = StoreStatus.objects.latest('timestamp_utc').timestamp_utc
  
    current_timestamp = StoreStatus.objects.latest('timestamp_utc').timestamp_utc
    local_time = datetime.now(pytz.timezone('Asia/Kolkata'))

    # for testing purpose i used current timestamp and changed the values in db for a particular store
    # utc_time = local_time.astimezone(pytz.utc)
    # current_timestamp = utc_time
  
    store_id = StoreStatus.objects.filter(store_id=storeid).first()
    report_id = str(uuid.uuid4())
    timezone_obj = Timezone.objects.filter(store_id=storeid).first()
   
    if timezone_obj :
            timezone_str = timezone_obj.timezone_str
            print(timezone_obj.timezone_str)
    else:
         timezone_str = 'America/Chicago'
         print(timezone_str)
    

    business_hours = BusinessHours.objects.filter(store_id=storeid)
    bhfound = True
    if not business_hours:
            bhfound = False
            # If no business hours provided, assume 24/7
            business_hours = [{'day_of_week': i, 'start_time_local': '00:00:00', 'end_time_local': '23:59:59'} for i in range(7)]
    

    # Calculate the time intervals for the last hour, day, and week
    last_hour_interval = current_timestamp - timedelta(hours=1)
    last_day_interval = current_timestamp - timedelta(days=1)
    last_week_interval = current_timestamp - timedelta(weeks=1) 

    obj1count= StoreStatus.objects.filter(store_id=storeid).count()
    obj1activecount = StoreStatus.objects.filter(store_id=storeid, status="active").count()
    puptime = obj1activecount/obj1count
  
   
    for bh in business_hours:
        if utc_time.weekday()==int(bh.day_of_week):
  
            starttimeutc=convert_to_utc(bh.start_time_local if bhfound else bh['start_time_local'],timezone_str,utc_time.weekday())
            endtimeutc=convert_to_utc(bh.end_time_local if bhfound else bh['end_time_local'],timezone_str,utc_time.weekday())

        
            #calculating store hours for each day , eg: 7am to 12pm = 5 hours
            storehours = (endtimeutc - starttimeutc).total_seconds() / 3600

            # ========================================
            #  checking uptime for last hours
            # ========================================
            # checks if current utc time lies between the start time and end time of store 
            if (utc_time>starttimeutc and utc_time<endtimeutc):
                
                # obj1= StoreStatus.objects.filter(store_id=storeid)
                
                # for ob in obj1: 
                #   print(ob.timestamp_utc)
                

                #  Gets the status whose timestamp is lies between last hour interval and current time stamp
                obj = StoreStatus.objects.filter(timestamp_utc__gt = last_hour_interval, timestamp_utc__lte = utc_time).first()
                
                # checks if the particular entry exist or set lasthouruptime to 0 and downtime to 60 (in mins)
                if obj and obj.status=="active":
                    # calculating seconds difference between current time stamp and store active time stamp
                     lasthouruptime= (utc_time-obj.timestamp_utc).total_seconds()
                    #  converting seconds to minutes
                     lasthouruptime = lasthouruptime / 60
                    #   calculating downtime 
                     lasthourdowntime = 60 - lasthouruptime
                 
                else:
                    lasthouruptime = 0
                    lasthourdowntime = 60 - lasthouruptime
                 
            else:  
                lasthouruptime = 0
                lasthourdowntime = 60 - lasthouruptime  
               


            # ============================================
            #  checks last day uptime
            # ============================================

            # checks for all active status in Storestatus table which lies between last day interval and current time stamp
            # also checks  only for hours that lies withing store business hours 
            uptime_count = StoreStatus.objects.filter(
            Q(store_id=store_id) &
            Q(status="active") &
            Q(timestamp_utc__gte=last_day_interval) &
            Q(timestamp_utc__gte=starttimeutc) &
            Q(timestamp_utc__lt=endtimeutc) &
            Q(timestamp_utc__lt=utc_time)
        ).count()
            downtime_count = StoreStatus.objects.filter(
            Q(store_id=store_id) &
            Q(status="inactive") &
            Q(timestamp_utc__gte=last_day_interval) &
            Q(timestamp_utc__gte=starttimeutc) &
            Q(timestamp_utc__lt=endtimeutc) &
            Q(timestamp_utc__lt=utc_time)
        ).count()
            # considering that status is updated every hour then each active uptime record in status table represents that store is active for 1 hour 
            # if uptime_count is 4 then store is open for 4 hours 
            # since it is mentioned that there might be a case where the record for particular hour is missing so we need to create a logic for calculating total uptime considering the missing values 
            # we can do this by calculating the probability active status out of all enteries for the particular store  
            
            # lefthours is the hours for which the record
            lefthours = storehours - (uptime_count+downtime_count)

            # calculating the active hours in the remaining time based on the probability of active hours 
            activeinlefthours = lefthours * puptime
        
            inactiveindaylefthours = lefthours -  activeinlefthours
            # Calculate uptime in minutes
          
            # total uptime in last day is uptime count + active hours in remaining time 
            uptimelastday=uptime_count+activeinlefthours
            # print("lastdayuptimehours-->",uptime_count+activeinlefthours)
            # print("lastdaydowntimehours-->",inactiveindaylefthours)
            
            
    # ============================================
    #  CALCULATING UPTIME FOR LAST WEEK 
    # ============================================

    totalweekhours=0
    totalweeklefthours=0
    totaluptimeweek=0

    # looping through all days of business hours 
    for bh in business_hours:

            # Calculating the utc time for the start time and end time for the store 
            starttimeutc=convert_to_utc(bh.start_time_local if bhfound else bh['start_time_local'] ,timezone_str,bh.day_of_week if bhfound else bh['day_of_week'])
            endtimeutc=convert_to_utc(bh.end_time_local if bhfound else bh['end_time_local'],timezone_str,bh.day_of_week if bhfound else bh['day_of_week'])
           
            # calculating store hours each day
            storehours = (endtimeutc - starttimeutc).total_seconds() / 3600
            # calculating total store hours in a week 
            totalweekhours+=storehours
           
    # Getting all the active status form store status tables that lies between last week interval and current timestamp 
    uptime_count = StoreStatus.objects.filter(
         Q(store_id=store_id) &
            Q(status="active") &
            Q(timestamp_utc__gte=last_week_interval)&
            Q(timestamp_utc__lt=utc_time)
        ).count()
            
    # getting all the inactive records
    downtime_count = StoreStatus.objects.filter(
         Q(store_id=store_id) &
            Q(status="inactive") &
            Q(timestamp_utc__gte=last_week_interval)&
            Q(timestamp_utc__lt=utc_time)
        ).count()

            # Calculating total uptime , total downtime and total remaining hours 
    totaluptimeweek=uptime_count
    lefthours = totalweekhours - (uptime_count+downtime_count)
    totalweeklefthours+=lefthours
                     
    # calculating the active hours in remaining hours by using probability of the uptime 
    activeinlefthours = totalweeklefthours*puptime
    totalactive=activeinlefthours+totaluptimeweek
    totalinactive=totalweekhours-totalactive        

    report = {
            "report_id":report_id,
            "store_id":store_id.store_id,
            "uptime_last_hour":lasthouruptime,
            "uptime_last_day":uptimelastday,
            "uptime_last_week":totalactive,
            "downtime_last_hour":lasthourdowntime,
            "downtime_last_day":inactiveindaylefthours,
            "downtime_last_week":totalinactive,
        }
    print("*"*10)
    print(report)
    print("*"*10)           
   
    return Response(report)

@api_view(['GET'])
def triggerreport(request):
    report_id = str(uuid.uuid4())
    report = Report(report_id=report_id,status=False)
    report.save()
    report_generate(report_id)
    return Response({"report_id": report_id})

                    
def report_generate(report_id):
    report_id = report_id
    allstores = Timezone.objects.all()
    utc_time = StoreStatus.objects.latest('timestamp_utc').timestamp_utc
    current_timestamp = StoreStatus.objects.latest('timestamp_utc').timestamp_utc
    local_time = datetime.now(pytz.timezone('Asia/Kolkata'))
    utc_time = local_time.astimezone(pytz.utc)
    current_timestamp = utc_time
    store_data_list=[]
    counter=0
    for store in allstores:

        counter+=1
        if counter == 2000:
            break
        store_id = StoreStatus.objects.filter(store_id=store.store_id).first()
   
        timezone_obj = Timezone.objects.filter(store_id=store.store_id).first()
    
        if timezone_obj :
                timezone_str = timezone_obj.timezone_str
                print(timezone_obj.timezone_str)
        else:
            timezone_str = 'America/Chicago'
            print(timezone_str)
        

        business_hours = BusinessHours.objects.filter(store_id=store.store_id)
       
        if not business_hours :
                # If no business hours provided, assume 24/7
                found = False
                business_hours = [{'day_of_week': i, 'start_time_local': '00:00:00', 'end_time_local': '23:59:59'} for i in range(7)]
        else:
             found = True
        
        # Calculate the time intervals for the last hour, day, and week
        last_hour_interval = current_timestamp - timedelta(hours=1)
        last_day_interval = current_timestamp - timedelta(days=1)
        last_week_interval = current_timestamp - timedelta(weeks=1) 

        obj1count= StoreStatus.objects.filter(store_id=store.store_id).count()
        obj1activecount = StoreStatus.objects.filter(store_id=store.store_id, status="active").count()
        if obj1count!=0:
            puptime = obj1activecount/obj1count
        else:
            continue
    
    
        for bh in business_hours:
            weekday = int(bh.day_of_week if found else bh['day_of_week'])
            print(weekday)
            if utc_time.weekday()==int(bh.day_of_week if found else bh['day_of_week']):
    
                starttimeutc=convert_to_utc(bh.start_time_local if found else bh['start_time_local'],timezone_str,utc_time.weekday())
                endtimeutc=convert_to_utc(bh.end_time_local if found else bh['end_time_local'],timezone_str,utc_time.weekday())

            
                #calculating store hours for each day , eg: 7am to 12pm = 5 hours
                storehours = (endtimeutc - starttimeutc).total_seconds() / 3600

                # ========================================
                #  checking uptime for last hours
                # ========================================
                # checks if current utc time lies between the start time and end time of store 
                if (utc_time>starttimeutc and utc_time<endtimeutc):
                    
                    # obj1= StoreStatus.objects.filter(store_id=store.store_id)
                    
                    # for ob in obj1: 
                    #   print(ob.timestamp_utc)
                    

                    #  Gets the status whose timestamp is lies between last hour interval and current time stamp
                    obj = StoreStatus.objects.filter(timestamp_utc__gt = last_hour_interval, timestamp_utc__lte = utc_time).first()
                    
                    # checks if the particular entry exist or set lasthouruptime to 0 and downtime to 60 (in mins)
                    if obj and obj.status=="active":
                        # calculating seconds difference between current time stamp and store active time stamp
                        lasthouruptime= (utc_time-obj.timestamp_utc).total_seconds()
                        #  converting seconds to minutes
                        lasthouruptime = lasthouruptime / 60
                        #   calculating downtime 
                        lasthourdowntime = 60 - lasthouruptime
                    
                    else:
                        lasthouruptime = 0
                        lasthourdowntime = 60 - lasthouruptime
                    
                else:  
                    lasthouruptime = 0
                    lasthourdowntime = 60 - lasthouruptime  
                


                # ============================================
                #  checks last day uptime
                # ============================================

                # checks for all active status in Storestatus table which lies between last day interval and current time stamp
                # also checks  only for hours that lies withing store business hours 
                uptime_count = StoreStatus.objects.filter(
                Q(store_id=store_id) &
                Q(status="active") &
                Q(timestamp_utc__gte=last_day_interval) &
                Q(timestamp_utc__gte=starttimeutc) &
                Q(timestamp_utc__lt=endtimeutc) &
                Q(timestamp_utc__lt=utc_time)
            ).count()
                downtime_count = StoreStatus.objects.filter(
                Q(store_id=store_id) &
                Q(status="inactive") &
                Q(timestamp_utc__gte=last_day_interval) &
                Q(timestamp_utc__gte=starttimeutc) &
                Q(timestamp_utc__lt=endtimeutc) &
                Q(timestamp_utc__lt=utc_time)
            ).count()
                # considering that status is updated every hour then each active uptime record in status table represents that store is active for 1 hour 
                # if uptime_count is 4 then store is open for 4 hours 
                # since it is mentioned that there might be a case where the record for particular hour is missing so we need to create a logic for calculating total uptime considering the missing values 
                # we can do this by calculating the probability active status out of all enteries for the particular store  
                
                # lefthours is the hours for which the record
                lefthours = storehours - (uptime_count+downtime_count)

                # calculating the active hours in the remaining time based on the probability of active hours 
                activeinlefthours = lefthours * puptime
            
                inactiveindaylefthours = lefthours -  activeinlefthours
                # Calculate uptime in minutes
            
                # total uptime in last day is uptime count + active hours in remaining time 
                uptimelastday=uptime_count+activeinlefthours
                # print("lastdayuptimehours-->",uptime_count+activeinlefthours)
                # print("lastdaydowntimehours-->",inactiveindaylefthours)
                
                
        # ============================================
        #  CALCULATING UPTIME FOR LAST WEEK 
        # ============================================

        totalweekhours=0
        totalweeklefthours=0
        totaluptimeweek=0

        # looping through all days of business hours 
        for bh in business_hours:

                # Calculating the utc time for the start time and end time for the store 
                starttimeutc=convert_to_utc(bh.start_time_local if found else bh['start_time_local'] ,timezone_str,bh.day_of_week if found else bh['day_of_week'])
                endtimeutc=convert_to_utc(bh.end_time_local if found else bh['end_time_local'],timezone_str,bh.day_of_week if found else bh['day_of_week'])
            
                # calculating store hours each day
                storehours = (endtimeutc - starttimeutc).total_seconds() / 3600
                # calculating total store hours in a week 
                totalweekhours+=storehours
            
        # Getting all the active status form store status tables that lies between last week interval and current timestamp 
        uptime_count = StoreStatus.objects.filter(
            Q(store_id=store_id) &
                Q(status="active") &
                Q(timestamp_utc__gte=last_week_interval)&
                Q(timestamp_utc__lt=utc_time)
            ).count()
                
        # getting all the inactive records
        downtime_count = StoreStatus.objects.filter(
            Q(store_id=store_id) &
                Q(status="inactive") &
                Q(timestamp_utc__gte=last_week_interval)&
                Q(timestamp_utc__lt=utc_time)
            ).count()

                # Calculating total uptime , total downtime and total remaining hours 
        totaluptimeweek=uptime_count
        lefthours = totalweekhours - (uptime_count+downtime_count)
        totalweeklefthours+=lefthours
                        
        # calculating the active hours in remaining hours by using probability of the uptime 
        activeinlefthours = totalweeklefthours*puptime
        totalactive=activeinlefthours+totaluptimeweek
        totalinactive=totalweekhours-totalactive        

        report = {
                "store_id":store_id.store_id,
                "uptime_last_hour":lasthouruptime,
                "uptime_last_day":uptimelastday,
                "uptime_last_week":totalactive,
                "downtime_last_hour":lasthourdowntime,
                "downtime_last_day":inactiveindaylefthours,
                "downtime_last_week":totalinactive,
            }
        store_data_list.append(report)

    report = Report.objects.filter(report_id=report_id).first()    
    csv_file_path = f"{report_id}.csv"
    csv_header = [
    "store_id",
    "uptime_last_hour",
    "uptime_last_day",
    "uptime_last_week",
    "downtime_last_hour",
    "downtime_last_day",
    "downtime_last_week",
]
    # with open(csv_file_path, mode="w", newline="") as csv_file:
    #     writer = csv.DictWriter(csv_file, fieldnames=csv_header)
    
    # # Write the header row
    #     writer.writeheader()
    
    # # Write the data for each store
    #     writer.writerows(store_data_list)

    # print("CSV file has been created:", csv_file_path)
    with io.StringIO() as csv_buffer:
       writer = csv.DictWriter(csv_buffer, fieldnames=csv_header)
       writer.writeheader()
    
    # Write the data for each store to the CSV buffer
       writer.writerows(store_data_list)
    
    # Save the CSV data to the report's csv_file field
       report.csv_file.save(csv_file_path, ContentFile(csv_buffer.getvalue()), save=False)

    report.status=True
    report.save()    
    return  

@api_view(['GET'])
def getreport(request,report_id):
   try:  
     report=Report.objects.filter(report_id=report_id).first()
     if report.status:
          with open(report.csv_file.path, 'rb') as csv_file:
                response = HttpResponse(csv_file.read(), content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{report_id}.csv"'
                return response
     else:
          return Response({"message": "Running"})
   except Report.DoesNotExist:
        return JsonResponse({"status": "Report not found"}, status=404)  
     


@api_view(['GET'])
def cleardbtables(request):
    
    # Delete all records from the StoreStatus table
    # StoreStatus.objects.all().delete()

    # Delete all records from the BusinessHours table
    # BusinessHours.objects.all().delete()

    # Delete all records from the Timezone table
    # Timezone.objects.all().delete()

    return Response({"message":"deleted"})