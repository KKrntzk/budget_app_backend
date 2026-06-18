from rest_framework import serializers
from django.contrib.auth.models import User
from finance_api.models import (
    Household,
    HouseholdMember,
    Category,
    Income,
    Transaction,
    Budget,
    SavingsGoal,
)
from django.db.models import Q
from decimal import Decimal


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class HouseholdSerializer(serializers.ModelSerializer):
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Household
        fields = (
            "id",
            "name",
            "billing_cycle_type",
            "payday_start",
            "split_mode_enabled",
            "created_at",
            "user_role",
        )
        read_only_fields = ("id", "created_at")

    def get_user_role(self, obj):
        """
        Dynamically fetches the role of the requesting user in this household.
        """
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            member = HouseholdMember.objects.filter(
                user=request.user, household=obj
            ).first()
            if member:
                return member.role
        return None


class InviteSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "household", "name", "color", "icon")
        read_only_fields = ("id", "is_default")


class HouseholdSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ("split_mode_enabled", "billing_cycle_type", "payday_start")


class IncomeSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Income
        fields = ["id", "username", "title", "amount", "is_recurring", "date"]
        read_only_fields = ["username"]


class TransactionSerializer(serializers.ModelSerializer):
    paid_by_username = serializers.ReadOnlyField(source="paid_by.username")

    split_with = serializers.SlugRelatedField(
        many=True, queryset=User.objects.all(), slug_field="username", required=False
    )

    category = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ["household", "paid_by"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        view = self.context.get("view")
        if view and hasattr(view, "get_object"):
            try:
                household = view.get_object()
                self.fields["category"].queryset = Category.objects.filter(
                    Q(household=household) | Q(household__isnull=True)
                )
            except:
                pass

    def create(self, validated_data):
        split_with_users = validated_data.pop("split_with", [])
        transaction = Transaction.objects.create(**validated_data)
        transaction.split_with.set(split_with_users)
        return transaction

    def validate_split_with(self, value):
        view = self.context.get("view")
        if view and hasattr(view, "get_object"):
            household = view.get_object()
            for user in value:
                if not household.members.filter(id=user.id).exists():
                    raise serializers.ValidationError(
                        f"User '{user.username}' is not a member of this household."
                    )
        return value

    def validate_category(self, value):
        if value:
            view = self.context.get("view")
            if view and hasattr(view, "get_object"):
                household = view.get_object()
                if value.household is not None and value.household != household:
                    raise serializers.ValidationError(
                        "Diese Kategorie gehört nicht zu diesem Haushalt."
                    )
        return value


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source="category.name")

    class Meta:
        model = Budget
        fields = [
            "id",
            "category",
            "category_name",
            "month",
            "year",
            "amount",
            "percentage",
        ]


class SavingsGoalSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = SavingsGoal
        fields = [
            "id",
            "title",
            "target_amount",
            "current_amount",
            "target_date",
            "is_completed",
            "remaining_amount",
        ]
        read_only_fields = ["current_amount", "is_completed", "remaining_amount"]

    def get_remaining_amount(self, obj):
        remaining = obj.target_amount - obj.current_amount
        return max(Decimal("0.00"), remaining)
