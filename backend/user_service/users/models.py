from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='users_user_groups',   # 自定义反向名称
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )

    # 修改 user_permissions 字段
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='users_user_permissions',   # 自定义反向名称
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )







