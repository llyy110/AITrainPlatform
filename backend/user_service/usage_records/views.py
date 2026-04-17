from django.db import models
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from rest_framework.views import APIView

from .models import TrainingRecord
from .UsageSerializers import TrainingRecordSerializer
import json
import csv

class TrainingRecordListView(generics.ListCreateAPIView):
    serializer_class = TrainingRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TrainingRecord.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TrainingRecordDetailView(generics.RetrieveAPIView):
    serializer_class = TrainingRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TrainingRecord.objects.filter(user=self.request.user)

class ExportTrainingResultView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        record = TrainingRecord.objects.get(id=kwargs['pk'], user=request.user)
        # 准备导出数据
        data = {
            'id': record.id,
            'model_type': record.model_type,
            'hyperparameters': {
                'hidden_layer_sizes': record.hidden_layer_sizes,
                'max_iter': record.max_iter,
                'learning_rate': record.learning_rate,
            },
            'data_path': record.data_path,
            'status': record.status,
            'metrics': record.metrics,
            'training_duration': record.training_duration,
            'data_loading_duration': record.data_loading_duration,
            'created_at': record.created_at.isoformat(),
        }
        # 支持 CSV 或 JSON，通过 query param ?format=csv
        format = request.query_params.get('format', 'json')
        if format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="training_record_{record.id}.csv"'
            writer = csv.writer(response)
            writer.writerow(['Field', 'Value'])
            for key, value in data.items():
                if isinstance(value, dict):
                    writer.writerow([key, json.dumps(value)])
                else:
                    writer.writerow([key, value])
            return response
        else:
            return Response(data, headers={'Content-Disposition': f'attachment; filename="training_record_{record.id}.json"'})

class DownloadDataFileView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        record = TrainingRecord.objects.get(id=kwargs['pk'], user=request.user)
        if not record.can_download:
            return Response({'error': '数据文件已超过一年保留期，仅可查看记录，不可下载'}, status=status.HTTP_403_FORBIDDEN)
        # 调用训练服务的 HDFS 下载接口
        import requests
        training_service_url = "http://training-service:8001/api/hdfs/download"
        params = {'path': record.data_path}
        resp = requests.get(training_service_url, params=params, stream=True)
        if resp.status_code == 200:
            return FileResponse(resp.raw, content_type='application/octet-stream', filename=record.data_path.split('/')[-1])
        else:
            return Response({'error': '文件下载失败'}, status=resp.status_code)

class TrainingStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        records = TrainingRecord.objects.filter(user=user)
        total = records.count()
        completed = records.filter(status='completed').count()
        failed = records.filter(status='failed').count()
        # 计算平均准确率（如果有）
        avg_accuracy = records.filter(status='completed', metrics__has_key='accuracy').aggregate(avg=models.Avg('metrics__accuracy'))['avg']
        return Response({
            'total': total,
            'completed': completed,
            'failed': failed,
            'success_rate': round(completed/total*100, 2) if total else 0,
            'avg_accuracy': avg_accuracy
        })








