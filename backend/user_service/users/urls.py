from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import login, register, send_sms_code, update_profile, upload_avatar, send_reset_code

urlpatterns = [
    path('login', login, name='login'),
    path('register', register, name='register'),
    path('send-code', send_sms_code, name='send_sms_code'),
    path('reset-password', send_reset_code, name='send_reset_code'),
    # path('send-code/', include('phone_verify.urls')),  # 发送验证码接口
    path('profile', update_profile, name='user_profile'),
    path('avatar', upload_avatar, name='user_profile'),
    path('refresh', TokenRefreshView.as_view(), name='token_refresh'),

]