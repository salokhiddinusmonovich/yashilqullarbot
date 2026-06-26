from rest_framework import serializers
from app_telegram.models import TGUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TGUser
        fields = '__all__'
        read_only_fields = ['balance', 'is_admin', 'is_tester']