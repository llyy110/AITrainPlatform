from django.db import models
from django.utils import timezone

class TrainingRecord(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    model_type = models.CharField(max_length=50)   # train_cnn_img_classifier ...
    hidden_layer_sizes = models.IntegerField()
    max_iter = models.IntegerField()
    learning_rate = models.FloatField()
    data_path = models.CharField(max_length=500)   # HDFS路径
    status = models.CharField(max_length=20)       # completed, failed, training
    metrics = models.JSONField(default=dict)       # 存储accuracy, loss等
    training_duration = models.FloatField(null=True)
    data_loading_duration = models.FloatField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    can_download = models.BooleanField(default=True)  # 一年内可下载

    def save(self, *args, **kwargs):
        # 自动判断：超过一年则can_download=False
        if self.created_at and (timezone.now() - self.created_at).days > 365:
            self.can_download = False
        super().save(*args, **kwargs)