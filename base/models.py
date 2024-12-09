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
    date = models.DateField(auto_now_add=True)
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Attendance for {self.employee.name} on {self.date}"
    
    def calculate_total_hours(self):
        # Calculate total hours worked
            # Ensure both check-in and check-out times are present
        if self.check_in_time and self.check_out_time:
            # Calculate the total duration in seconds
            total_seconds = (self.check_out_time - self.check_in_time).seconds
            
            # Convert seconds to hours and minutes
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            # Return formatted string
            return f"{hours} hrs {minutes} minutes"
        return "N/A"  # Handle cases where check-in or check-out is missing

    def is_checked_in(self):
        return self.check_in_time is not None

    def is_checked_out(self):
        return self.check_out_time is not None

# class Item(models.Model):
#     name = models.CharField(max_length=200)
#     created_at = models.DateTimeField(auto_now_add=True)

# class ImageModel(models.Model):
#     image_path = models.ImageField(upload_to='images/')
#     created_at = models.DateTimeField(auto_now_add=True)