# Generated by Django 4.2 on 2023-05-08 09:21

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('sensors', '0002_humiditysensor_created_at_motionsensor_created_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MedicalDispensor',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('isDispensing', models.BooleanField(default=False)),
                ('medicine', models.CharField(max_length=100, null=True)),
                ('ultraId', models.IntegerField(default=1000)),
                ('tempId', models.IntegerField(default=1000)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
    ]
