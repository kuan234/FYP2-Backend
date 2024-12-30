from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from base.models import Employee, AttendanceLog, CheckInCheckOutTime

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'
        extra_kwargs = {
            'faceImage': {'required': False},  # Make faceImage optional
        }
    def create(self, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)
 
class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceLog
        fields = '__all__'

    def get_total_hours(self, obj):
        # Calculate total hours worked and round to 2 decimal places
        total_seconds = (obj.check_out_time - obj.check_in_time).seconds
        total_hours = total_seconds / 3600
        return round(total_hours, 2)
    
class CheckInCheckOutTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckInCheckOutTime
        fields = '__all__'