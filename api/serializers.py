from rest_framework import serializers
from base.models import Employee

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'