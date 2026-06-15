from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import Household, HouseholdMember

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
    

class HouseholdSerializer(serializers.ModelSerializer):
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Household
        fields = ('id', 'name', 'billing_cycle_type', 'payday_start', 'split_mode_enabled', 'created_at', 'user_role')
        read_only_fields = ('id', 'created_at')

    def get_user_role(self, obj):
        """
        Dynamically fetches the role of the requesting user in this household.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            member = HouseholdMember.objects.filter(user=request.user, household=obj).first()
            if member:
                return member.role
        return None