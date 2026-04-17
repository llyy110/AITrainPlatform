from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'phone', 'avatar', 'email', 'date_joined')

    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

class LoginSerializer(serializers.Serializer):
    loginId = serializers.CharField()  # 兼容邮箱/用户名
    password = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.CharField()
    code = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'code')

    def validate(self, attrs):
        # 密码强度验证
        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        validated_data.pop('code')
        return User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data['email']
        )


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'avatar', 'first_name', 'last_name')
        read_only_fields = ('id', 'username')


class ProfileUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)


# 发送重置验证码序列化器
class SendResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()


# 重置密码序列化器
class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value
