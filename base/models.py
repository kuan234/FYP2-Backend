from django.db import models
from datetime import datetime
from django.contrib.auth.hashers import make_password, check_password

# Create your models here.
class Employee(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=20)
    role = models.CharField(max_length=20)
    department = models.CharField(max_length=50)
    faceImage = models.ImageField(upload_to='images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AttendanceLog(models.Model):
    date = models.DateField(default=datetime.now)
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    description = models.CharField(max_length=200)


# class Item(models.Model):
#     name = models.CharField(max_length=200)
#     created_at = models.DateTimeField(auto_now_add=True)

# class ImageModel(models.Model):
#     image_path = models.ImageField(upload_to='images/')
#     created_at = models.DateTimeField(auto_now_add=True)