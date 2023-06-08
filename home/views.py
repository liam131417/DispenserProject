# home/views.py
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .forms import DispenseForm, ConfigForm
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.urls import reverse
from sensors.models import HumiditySensor
from sensors.models import MotionSensor
from sensors.models import UltrasonicSensor
from sensors.models import MedicalDispensor, DispenseRecord
from datetime import date, timedelta
from .analysis import predictTemp
from .analysis import predictHumidity
from sensors.views import isDispensing
from medicine.views import check_medicine, recommend, get_medicine
from medicine.models import MedicineDetail
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from .models import Threshold
from django.db.models import Avg
from django.db.models.functions import ExtractWeek, ExtractMonth, ExtractYear
from datetime import datetime, timedelta
from django.db.models.functions import TruncMonth, TruncWeek
from dateutil.relativedelta import relativedelta


# Main Page
def home(request):
    return render(request, 'home/frontpage.html')

# Signup Page
def signup(request):
    form = UserCreationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('home')

    return render(request, 'home/signup.html', {'form': form})

# Retrieve temperature, humidity and distance values from sensors
def get_sensor_values(request):
    md = MedicalDispensor.objects.get(pk=1)
    try:
        temp = HumiditySensor.objects.get(pk=md.tempId)
        dist = UltrasonicSensor.objects.get(pk=md.ultraId)
    except HumiditySensor.DoesNotExist or UltrasonicSensor.DoesNotExist:
        temp = HumiditySensor.objects.filter(pk__lte=md.tempId).first()
        dist = UltrasonicSensor.objects.filter(pk__lte=md.ultraId).first()

    return temp.temperature, temp.humidity, dist.distance

# Predict temperature and humidity for the next week
def get_forecast():
    next_week = date.today() + timedelta(weeks=1)
    return predictTemp(next_week.year, next_week.month, next_week.day), predictHumidity(next_week.year, next_week.month, next_week.day)

def get_dispenser_usage():
    now = datetime.now()

    # Calculate the date 1 year ago from now
    one_year_ago = now - timedelta(days=365)

    # Get all entries from the last 365 days
    entries_last_year = DispenseRecord.objects.filter(created_at__gte=one_year_ago)

    # Split entries into 3 groups based on dispId
    entries_group1 = entries_last_year.filter(dispId=1)
    entries_group2 = entries_last_year.filter(dispId=2)
    entries_group3 = entries_last_year.filter(dispId=3)

    # Get the monthly averages for the last 12 months for each group
    monthly_avg_group1 = entries_group1.annotate(month=TruncMonth('created_at')).values('month').annotate(avg_quantity=Avg('quantity')).order_by('-month')[:12]
    monthly_avg_group2 = entries_group2.annotate(month=TruncMonth('created_at')).values('month').annotate(avg_quantity=Avg('quantity')).order_by('-month')[:12]
    monthly_avg_group3 = entries_group3.annotate(month=TruncMonth('created_at')).values('month').annotate(avg_quantity=Avg('quantity')).order_by('-month')[:12]

    # Get the weekly averages for the last 12 weeks for each group
    weekly_avg_group1 = entries_group1.annotate(week=TruncWeek('created_at')).values('week').annotate(avg_quantity=Avg('quantity')).order_by('-week')[:12]
    weekly_avg_group2 = entries_group2.annotate(week=TruncWeek('created_at')).values('week').annotate(avg_quantity=Avg('quantity')).order_by('-week')[:12]
    weekly_avg_group3 = entries_group3.annotate(week=TruncWeek('created_at')).values('week').annotate(avg_quantity=Avg('quantity')).order_by('-week')[:12]

    return monthly_avg_group1, monthly_avg_group2,monthly_avg_group3,weekly_avg_group1,weekly_avg_group2,weekly_avg_group3

def get_months():
    now = datetime.now()

    # Create an array to store the months
    months = []

    # Iterate over the last 12 months
    for i in range(12):
        # Get the month by subtracting i months from the current date
        month = (now - relativedelta(months=i)).strftime('%b')
        # Add the month to the array
        months.append(month)

    # Reverse the array so that the months are in order
    months = months[::-1]

    return months

# A function to convert QuerySet to list
def queryset_to_list(queryset):
    return list(queryset.values_list('avg_quantity', flat=True))

# Dashboard
@login_required
def dashboard(request):
    
    temp_data, hum_data, temp_week_data, hum_week_data = [], [], [], []

    # Get the current date
    now = datetime.now()


    for i in range(12):
        month_start = now - relativedelta(months=i+1)
        month_end = now - relativedelta(months=i)

        data = HumiditySensor.objects.filter(created_at__range=(month_start, month_end))
        data_count = data.count()
        
        if data_count > 0:
            avg_temp = sum(float(d.temperature) for d in data) / data_count
            avg_hum = sum(float(d.humidity) for d in data) / data_count

            temp_data.append(avg_temp)
            hum_data.append(avg_hum)

    # Calculate the average temperature and humidity for each of the last 12 weeks
    for i in range(12):
        week_start = now - timedelta(weeks=i+1)
        week_end = now - timedelta(weeks=i)

        week_data = HumiditySensor.objects.filter(created_at__range=(week_start, week_end))
        week_data_count = week_data.count()
        
        if week_data_count > 0:
            temp_week_data.append(sum(float(d.temperature) for d in week_data) / week_data_count)
            hum_week_data.append(sum(float(d.humidity) for d in week_data) / week_data_count)

    temp, humid, dist = get_sensor_values(request)
    temp = float(temp)
    humid = float(humid)
    stock = "{dist:.2f}".format(dist=(100-(int(round(float(dist)))/22)*100))
    predTemp, predHum = get_forecast()

    # Get dispenser usage
    usage_data = get_dispenser_usage()

    # Convert each QuerySet to a list
    usage_data = [queryset_to_list(queryset) for queryset in usage_data]

    # Unpack the data back into your variables
    md1, md2, md3, wd1, wd2, wd3 = usage_data

    months = get_months()
    
    context = {'temp': "{temp:.2f}".format(temp=temp),
               'humid': "{humid:.2f}".format(humid=humid),
               'dist': stock,
               'fTemp': "{pred:.2f}".format(pred=predTemp[0]),
               'fHum': "{pred:.2f}".format(pred=predHum[0]),
               'temp_data': temp_data,
               'hum_data': hum_data,
               'temp_week_data': temp_week_data,
               'hum_week_data': hum_week_data,
               'months': months,
               'md1': md1,
               'md2': md2,
               'md3': md3,
               'wd1': wd1,
               'wd2': wd2,
               'wd3': wd3}

    threshold = Threshold.objects.all()[0]
    if temp > threshold.TEMP_THRESHOLD:
        messages.success(request, f'Temperature exceeds the threshold({threshold.TEMP_THRESHOLD}).')
    if humid > threshold.HUMID_THRESHOLD:
        messages.success(request, f'Humidity exceeds the threshold({threshold.HUMID_THRESHOLD}).')
    
    return render(request, 'home/dashboard.html', context)


def is_dispenser_setup(dispenser):
    if len(dispenser.medicine) == 0:
        return f'{dispenser.id} is not setup'
    return None

def create_dispense_record(quantity, med_name):
    DispenseRecord.objects.create(dispId=1, medicine=med_name, quantity=quantity)

def get_dispenser_and_medicine(dispenser_dict, button_clicked):
    dispenser_key = button_clicked.title().replace('_', ' ')
    dispenser = dispenser_dict.get(dispenser_key, None)

    if dispenser is None:
        return None, None

    med_name = dispenser.medicine
    md = MedicineDetail.objects.get(pk=med_name)
    return dispenser, md

def format_data(data, preg, alcohol):
    formatted_data = ''
    for k, v in data.items():
        if k == 'alcohol':
            if alcohol == 'N':
                continue
            if str(v) == 'S':
                v = 'Considered safe for consumption by individuals with alcohol consumption'
            else:
                v = 'Potentially hazardous for individuals with alcohol consumption'

        if k == 'pregnant':
            if preg == 'N':
                continue
            if str(v) in {'A', 'B'}:
                v = 'Considered safe for consumption by pregnant women'
            else:
                v = 'Potentially hazardous for pregnant women'

        if k == 'rx_otc':
            if 'otc' in str(v):
                v = 'Available over the counter'
            else:
                v = 'Prescription needed for this medication'
        formatted_data += f"    - {k}: {v}\n"
    return formatted_data

def format_message(data, recommendations, preg, alcohol):
    formatted_data = format_data(data, preg, alcohol)
    formatted_recommendations = ''
    for recommendation in recommendations:
        formatted_recommendations_str = format_data(recommendation, preg, alcohol)
        formatted_recommendations += f"{formatted_recommendations_str}\n"

    message = (
        f"Current Medication:\n"
        f"{formatted_data}\n\n"
        f"Recommended Medicines:\n"
        f"{formatted_recommendations}"
    )
    return message

def format_message_html(message):
    formatted_message = message.replace(' - ', '</p><p>')
    formatted_message = formatted_message.replace('Current Medication:', '<h2>Current Medication:</h2><p>')
    formatted_message = formatted_message.replace('Recommended Medicines:', '</p><h2>Recommended Medicines:</h2><p>')
    return '<div>' + formatted_message + '</p></div>'



def get_medicine_info(request, current_obj, alcohol, preg, med_name, condition, recommendation):
    # Handle medicine attributes and add to messages
    msg, data = check_medicine(request, med_name, condition, preg, alcohol)
    recommendations = recommend(condition, alcohol, preg) if recommendation else []
    
    return format_message(data, recommendations, preg, alcohol)

@login_required
def dispense(request):
    form = DispenseForm(request.POST or None)

    dispensers = list(MedicalDispensor.objects.filter(pk__in=[1, 2, 3]))
    dispenser_dict = {f'Dispenser {i + 1}': dispenser for i, dispenser in enumerate(dispensers)}

    setup_messages = [is_dispenser_setup(dispenser) for dispenser in dispenser_dict.values() if is_dispenser_setup(dispenser) is not None]

    if setup_messages:
        message = ', '.join(setup_messages)
        return render(request, 'home/dispense.html', {'form': form, 'message': message})

    context = {f'dispenser{i+1}_quantity': getattr(dispenser, 'quantity') for i, dispenser in enumerate(dispensers)}

    for i, dispenser in enumerate(dispensers):
        context[f'dispenser{i+1}_medicine'] = getattr(dispenser, 'medicine').capitalize()

    
    if request.method == 'POST' and form.is_valid():
        button_clicked = request.POST.get('button')

        dispenser, medicine = get_dispenser_and_medicine(dispenser_dict, button_clicked)

        if dispenser is None:
            message = "Invalid Dispenser button. Please try again."
            return render(request, 'home/dispense.html', {'form': form, 'message': message})

        quantity = form.cleaned_data['quantity']

        if quantity <= 0:
            message = "The quantity must be a positive number. Please try again."
            return render(request, 'home/dispense.html', {'form': form, 'message': message})
        elif dispenser.quantity < quantity:
            message = f"Medical Dispenser {dispenser.id} has insufficient quantity. Please try again."
            return render(request, 'home/dispense.html', {'form': form, 'message': message})

        create_dispense_record(quantity, dispenser.medicine)
        context['message'] = '<h2>' + 'Dispense Successfully !' + '</h2>'

        # Retrieve the medicine's details and handle its attributes
        alcohol_input = form.cleaned_data['alcohol']
        preg_input = form.cleaned_data['pregnancy']
        recommendation = form.cleaned_data['recommendation']

        if alcohol_input is True:
            alcohol_input = 'Y'
        else:
            alcohol_input = 'N'
        
        if preg_input is True:
            preg_input = 'Y'
        else:
            preg_input = 'N'

        msg = get_medicine_info(request, medicine, alcohol_input, preg_input, dispenser.medicine, medicine.condition, recommendation)
        context['message'] += format_message_html(msg)
    context['form'] = form
    return render(request, 'home/dispense.html', context)

@login_required
def dispense_message(request):
    # Calculate the message
    message = 'You have dispensed your medicine!'
    return HttpResponse(message)

@login_required
def success(request):
    return render(request, 'home/success.html')

@login_required
def config(request):
    # Fetch the previous config if it exists
    med_dispense_config = MedicalDispensor.objects.all()
    threshold = Threshold.objects.all()[0]

    if request.method == 'POST':
        form = ConfigForm(request.POST)
        if form.is_valid():
            medicines = {
                'medicineA': form.cleaned_data['medicineA'].lower(),
                'medicineB': form.cleaned_data['medicineB'].lower(),
                'medicineC': form.cleaned_data['medicineC'].lower(),
            }
            quantities = {
                'quantityA': form.cleaned_data['quantityA'],
                'quantityB': form.cleaned_data['quantityB'],
                'quantityC': form.cleaned_data['quantityC'],
            }
            temp_threshold = form.cleaned_data['threshold_temp']
            humid_threshold = form.cleaned_data['threshold_humid']

            # Check if the inputs are the same
            if len(set(medicines.values())) != len(medicines):
                message = "The medicine names cannot be the same. Please try again."
                return render(request, 'home/config.html', {'message': message, 'form': form})
            
            # Check if quantities are more than 0
            if any(q <= 0 for q in quantities.values()):
                message = "The quantity must be a positive number. Please try again."
                return render(request, 'home/config.html', {'message': message, 'form': form})

            # Check if the inputs are valid medicine names
            for med in medicines.values():
                try:
                    MedicineDetail.objects.get(pk=med)
                except MedicineDetail.DoesNotExist:
                    message = f"Medicine {med} does not exist. Please try again."
                    return render(request, 'home/config.html', {'message': message, 'form': form})
            
            # Check if thresholds are more than 0
            if (temp_threshold <= 0 or humid_threshold <= 0):
                message = "The threshold values must be a positive number. Please try again."
                return render(request, 'home/config.html', {'message': message, 'form': form})

            # If correct inputs given, update the records
            for i, (med, qty) in enumerate(zip(medicines.values(), quantities.values()), start=1):
                obj = MedicalDispensor.objects.get(pk=i)
                obj.medicine = med
                obj.quantity = qty
                obj.save()

            message = "Setup Successfully !"

            if threshold:
                threshold.TEMP_THRESHOLD = temp_threshold
                threshold.HUMID_THRESHOLD = humid_threshold
            else:
                threshold = Threshold(
                    TEMP_THRESHOLD=temp_threshold,
                    HUMID_THRESHOLD=humid_threshold,
                )
            threshold.save()

            message = "Setup Successfully !"
            return render(request, 'home/config.html', {'message': message, 'form': form})
        else:
            message = "Form is not valid. Please check your inputs and try again."
            return render(request, 'home/config.html', {'message': message, 'form': form})

    else:
        if med_dispense_config.exists() and threshold:
            initial_data = {
                'medicineA': med_dispense_config[0].medicine if med_dispense_config.count() > 0 else None,
                'medicineB': med_dispense_config[1].medicine if med_dispense_config.count() > 1 else None,
                'medicineC': med_dispense_config[2].medicine if med_dispense_config.count() > 2 else None,
                'quantityA': med_dispense_config[0].quantity if med_dispense_config.count() > 0 else None,
                'quantityB': med_dispense_config[1].quantity if med_dispense_config.count() > 1 else None,
                'quantityC': med_dispense_config[2].quantity if med_dispense_config.count() > 2 else None,
                'threshold_temp': threshold.TEMP_THRESHOLD,
                'threshold_humid': threshold.HUMID_THRESHOLD,
            }
            form = ConfigForm(initial=initial_data)
        else:
            form = ConfigForm()
        return render(request, 'home/config.html', {'form': form})

    
def error_404_view(request, exception):
    data = {"name": "TheMedicineDispenser"}
    return render(request, 'home/error_404.html', data)

def error_500_view(request):
    data = {"name": "TheMedicineDispenser"}
    return render(request, 'home/error_500.html', data)


def displayMed(request):
    objects = MedicineDetail.objects.all()
    return render(request, 'home/displayMed.html', {'objects': objects})