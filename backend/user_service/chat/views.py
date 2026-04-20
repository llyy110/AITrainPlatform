from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Conversation, Message, Announcement
from .ChatSerializers import ConversationSerializer, MessageSerializer, AnnouncementSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class ConversationListView(generics.ListCreateAPIView):
    """获取当前用户的所有会话，或创建新会话"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """创建或获取与指定用户的会话"""
        other_user_id = request.data.get('user_id')
        if not other_user_id:
            return Response({'detail': '缺少用户ID'}, status=400)

        other_user = get_object_or_404(User, id=other_user_id)
        if other_user == request.user:
            return Response({'detail': '不能和自己聊天'}, status=400)

        # 查找已存在的会话
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(participants=other_user).first()

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)

        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MessageListView(generics.ListCreateAPIView):
    """获取会话消息，或发送新消息"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id, participants=self.request.user)
        return conversation.messages.all()

    def perform_create(self, serializer):
        conversation = get_object_or_404(Conversation, id=self.kwargs['conversation_id'], participants=self.request.user)
        serializer.save(sender=self.request.user, conversation=conversation)
        # 更新会话时间
        conversation.save()


class MarkAsReadView(APIView):
    """标记会话中的消息为已读"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        return Response({'status': 'ok'})


class UnreadCountView(APIView):
    """获取总未读消息数"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        return Response({'unread_count': count})


class AnnouncementListView(generics.ListAPIView):
    """获取活跃公告"""
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Announcement.objects.filter(is_active=True)


class AnnouncementCreateView(generics.CreateAPIView):
    """管理员发布公告"""
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(publisher=self.request.user)