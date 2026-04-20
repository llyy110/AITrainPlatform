from django.db import models

class TrainingRecord(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, db_column='user_id')
    task_id = models.CharField(max_length=64, unique=True)
    model_type = models.CharField(max_length=50)
    hidden_layer_sizes = models.IntegerField()
    max_iter = models.IntegerField()
    learning_rate = models.FloatField()
    data_path = models.TextField()
    status = models.CharField(max_length=20, default='pending')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    final_error = models.FloatField(null=True, blank=True)
    final_accuracy = models.FloatField(null=True, blank=True)
    final_mae = models.FloatField(null=True, blank=True)
    model_save_path = models.TextField(null=True, blank=True)
    training_log_path = models.TextField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'training_records'
        managed = False  # 告诉 Django 不要管理这张表