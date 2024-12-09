from rest_framework import serializers
from base.models import Employee, AttendanceLog

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceLog
        fields = '__all__'

    def get_total_hours(self, obj):
        # Calculate total hours worked and round to 2 decimal places
        total_seconds = (obj.check_out_time - obj.check_in_time).seconds
        total_hours = total_seconds / 3600
        return round(total_hours, 2)