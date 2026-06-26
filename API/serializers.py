from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers
from app_telegram.models import TGUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TGUser
        fields = [
            'tg_id', 'fullname', 'age', 'email', 'phone', 
            'username', 'experience', 'photo', 'region', 
            'education_place', 'balance', 'is_tester'
        ]
        read_only_fields = ['balance', 'is_admin', 'is_tester']

    def validate_tg_id(self, value):
        # Prevent database crashes by catching duplicate registrations early
        if TGUser.objects.filter(tg_id=value).exists():
            raise serializers.ValidationError("A profile with this Telegram ID already exists.")
        return value

    def create(self, validated_data):
        tg_id = validated_data.get('tg_id')
        
        # Wrap in a transaction so if profile creation fails, the user isn't left orphaned
        with transaction.atomic():
            # Create standard authentication shadow user account
            django_user, created = User.objects.get_or_create(username=str(tg_id))
            if created:
                django_user.set_unusable_password()
                django_user.save()

            # Create the custom TGUser profile linked to the shadow auth user
            tg_user = TGUser.objects.create(user=django_user, **validated_data)
            return tg_user