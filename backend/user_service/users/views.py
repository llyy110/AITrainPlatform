import random

from django.contrib.auth import get_user_model, authenticate
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import HttpRequest
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .UserSerializers import LoginSerializer, RegisterSerializer, UserSerializer, \
    ProfileUpdateSerializer, ResetPasswordSerializer, SendResetCodeSerializer

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])  # ← 加上这一行
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    username = serializer.validated_data['username']
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    code = serializer.validated_data['code']

    cached_code = cache.get(f'sms:{email}')
    print('cached_code', cached_code)
    if not cached_code or cached_code != code:
        return Response({'detail': '验证码错误或已过期'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'detail': '用户名已存在'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'detail': '该邮箱已注册'}, status=400)

    user = User.objects.create_user(username=username, email=email, password=password)
    return Response(UserSerializer(user).data, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    print('logining')
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    login_id = serializer.validated_data['loginId']
    password = serializer.validated_data['password']

    # 支持邮箱或用户名登录
    try:
        if '@' in login_id:
            user_obj = User.objects.get(email=login_id)
            username = user_obj.username
        else:
            username = login_id
    except User.DoesNotExist:
        username = None

    user = authenticate(request, username=username, password=password)

    # 如果用户不存在
    if not user:
        return Response({'detail': '用户名或邮箱不存在'}, status=401)

    refresh = RefreshToken.for_user(user)
    return Response({
        'detail': 'success',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user, context={'request': request}).data  # 传入 request
    })


def send_email_code(to_email, prefix='sms'):
    """
    发送邮箱验证码（内部函数，不对外暴露）
    :param to_email: 接收邮箱
    :param prefix: 缓存键前缀，如 'sms' 或 'reset'
    :return: Response 对象
    """
    print(f'send_email_code: {to_email}, prefix={prefix}')
    sms_code = '%06d' % random.randint(0, 999999)
    EMAIL_FROM = "3547262443@qq.com"
    email_title = '邮箱激活' if prefix == 'sms' else '找回密码'
    email_body = f"您的{'注册' if prefix == 'sms' else '找回密码'}验证码为：{sms_code}，有效期为5分钟，请及时验证。"
    send_status = send_mail(email_title, email_body, EMAIL_FROM, [to_email])
    print(f'{prefix}:{to_email}', sms_code)
    cache.set(f'{prefix}:{to_email}', sms_code, timeout=300)
    if send_status == 0:
        return Response({'detail': '邮件发送失败，请稍后重试'}, status=500)
    return Response({'detail': '验证码已发送'}, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_sms_code(request):
    """注册时发送验证码"""
    to_email = request.data.get('email')
    if not to_email:
        return Response({'detail': '请提供邮箱'}, status=400)
    return send_email_code(to_email, prefix='sms')


@api_view(['POST'])
@permission_classes([AllowAny])
def send_reset_code(request):
    """发送找回密码验证码"""
    serializer = SendResetCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']
    # 检查邮箱是否存在
    if not User.objects.filter(email=email).exists():
        return Response({'detail': '该邮箱未注册'}, status=400)

    return send_email_code(email, prefix='reset')


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    serializer = ProfileUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = request.user
    if 'username' in serializer.validated_data:
        user.username = serializer.validated_data['username']
        user.save()
    return Response(UserSerializer(user).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """重置密码"""
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    code = serializer.validated_data['code']
    new_password = serializer.validated_data['new_password']

    # 验证验证码
    cached_code = cache.get(f'reset:{email}')
    if not cached_code or cached_code != code:
        return Response({'detail': '验证码错误或已过期'}, status=400)

    # 更新密码
    user = User.objects.get(email=email)
    user.set_password(new_password)
    user.save()

    # 删除缓存的验证码，防止重复使用
    cache.delete(f'reset:{email}')

    return Response({'detail': '密码重置成功，请登录'}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request: HttpRequest):
    if 'avatar' not in request.FILES:
        return Response({'detail': '请上传头像文件'}, status=400)
    user = request.user
    user.avatar = request.FILES['avatar']
    user.save()
    # 构造绝对 URL
    avatar_url = request.build_absolute_uri(user.avatar.url)
    return Response({'url': avatar_url})