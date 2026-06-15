from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, HouseholdSerializer, AddMemberSerializer, CategorySerializer
from ..models import Household, HouseholdMember, Category
from .permissions import IsHouseholdMember
from rest_framework.decorators import action

class RegisterView(generics.CreateAPIView):
    """
    API Endpoint that allows new users to register.
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User registered successfully.",
                "user": {
                    "username": user.username,
                    "email": user.email
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class HouseholdViewSet(viewsets.ModelViewSet):
    """
    A ViewSet that handles all Household operations and nested Categories.
    """
    serializer_class = HouseholdSerializer
    permission_classes = [permissions.IsAuthenticated, IsHouseholdMember]

    def get_queryset(self):
        """
        CRITICAL SECURITY: Users can only see households they belong to.
        """
        return Household.objects.filter(members=self.request.user)

    def perform_create(self, serializer):
        """
        1. Creates the household.
        2. Makes the creator the ADMIN.
        3. Automatically generates the 6 default categories.
        """
        household = serializer.save()
        
        HouseholdMember.objects.create(
            user=self.request.user,
            household=household,
            role='ADMIN'
        )
        
        default_categories = [
            {'name': 'Groceries', 'color': '#FF5733', 'icon': 'shopping_cart'},
            {'name': 'Rent / Housing', 'color': '#3357FF', 'icon': 'home'},
            {'name': 'Subscriptions', 'color': '#E74C3C', 'icon': 'smart_display'},
            {'name': 'Transportation', 'color': '#F1C40F', 'icon': 'directions_car'},
            {'name': 'Internet / Phone Bill', 'color': '#3498DB', 'icon': 'language'},
            {'name': 'Salary', 'color': '#2ECC71', 'icon': 'payments'},
        ]

        for cat in default_categories:
            Category.objects.create(
                household=household,
                name=cat['name'],
                color=cat['color'],
                icon=cat['icon']
            )

    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        """
        POST /api/households/<id>/add-member/
        """
        household = self.get_object()
        current_member_status = HouseholdMember.objects.filter(user=request.user, household=household).first()
        if not current_member_status or current_member_status.role != 'ADMIN':
            return Response({"detail": "Only Admins can do this."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AddMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        target_user = User.objects.get(username=serializer.validated_data['username'])
        if HouseholdMember.objects.filter(user=target_user, household=household).exists():
            return Response({"detail": "User is already a member."}, status=status.HTTP_400_BAD_REQUEST)

        HouseholdMember.objects.create(user=target_user, household=household, role='MEMBER')
        return Response({"message": f"User '{target_user.username}' added."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='categories')
    def get_categories(self, request, pk=None):
        """
        EXAKT WAS DU WOLLTEST:
        GET /api/households/<id>/categories/
        Lists all categories belonging specifically to this household.
        """
        household = self.get_object() 
        categories = Category.objects.filter(household=household)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.get_serializer_class() if hasattr(serializer, 'get_serializer_class') else serializer.data, status=status.HTTP_200_OK)

