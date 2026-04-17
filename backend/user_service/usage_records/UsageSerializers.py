from rest_framework import serializers
from .models import TrainingRecord

class TrainingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRecord
        fields = '__all__'
        read_only_fields = ('id', 'user', 'created_at', 'updated_at', 'can_download')

class TrainingRecordExportSerializer(serializers.Serializer):
    records = serializers.ListField(child=serializers.DictField())