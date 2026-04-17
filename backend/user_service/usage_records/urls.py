from django.urls import path
from .views import TrainingRecordListView, TrainingRecordDetailView, ExportTrainingResultView, DownloadDataFileView

urlpatterns = [
    path('records/', TrainingRecordListView.as_view(), name='record-list'),
    path('records/<int:pk>/', TrainingRecordDetailView.as_view(), name='record-detail'),
    path('records/<int:pk>/export/', ExportTrainingResultView.as_view(), name='record-export'),
    path('records/<int:pk>/download-data/', DownloadDataFileView.as_view(), name='record-download-data'),
]