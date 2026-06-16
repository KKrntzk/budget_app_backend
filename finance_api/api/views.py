from rest_framework.views import APIView
from rest_framework import generics, permissions, status, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import Sum

from .serializers import (
    RegisterSerializer, 
    HouseholdSerializer, 
    CategorySerializer, 
    InviteSerializer,
    HouseholdSettingsSerializer, 
    IncomeSerializer,
    TransactionSerializer
)
from finance_api.models import Household, HouseholdMember, Category, Transaction
from finance_api.api.permissions import IsHouseholdMember, IsHouseholdAdminOrReadOnly

from rest_framework.settings import api_settings
print(f"DEBUG: EXCEPTION_HANDLER ist vom Typ {type(api_settings.EXCEPTION_HANDLER)}")
print(f"DEBUG: Der Wert ist: {api_settings.EXCEPTION_HANDLER}")

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
    permission_classes = [permissions.IsAuthenticated, IsHouseholdAdminOrReadOnly]

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

    @action(
        detail=True, 
        methods=['post'], 
        url_path='invite', 
        permission_classes=[permissions.IsAuthenticated, IsHouseholdMember]
    )
    def invite_member(self, request, pk=None):
        """
        POST /api/households/<id>/invite/
        Invites a user to the household using EITHER their username OR their email.
        Accessible by both ADMINs and MEMBERs.
        """
        household = self.get_object()
        
        serializer = InviteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        identifier = serializer.validated_data['identifier']
        
        from django.db.models import Q
        target_user = User.objects.filter(Q(email=identifier) | Q(username=identifier)).first()
        
        if not target_user:
            return Response(
                {"detail": f"No user found with username or email '{identifier}'."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if HouseholdMember.objects.filter(user=target_user, household=household).exists():
            return Response(
                {"detail": "This user is already a member of this household."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        HouseholdMember.objects.create(
            user=target_user, 
            household=household, 
            role='MEMBER'
        )
        
        return Response(
            {"message": f"User '{target_user.username}' successfully added to the household."}, 
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get', 'post'], url_path='categories')
    def manage_categories(self, request, pk=None):
        """
        GET  /api/households/<id>/categories/ -> Lists all categories for this household.
        POST /api/households/<id>/categories/ -> Creates a new custom category for this household.
        """

        household = self.get_object() 

        if request.method == 'GET':
            categories = Category.objects.filter(household=household)
            serializer = CategorySerializer(categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == 'POST':

            serializer = CategorySerializer(data=request.data)
            
            if serializer.is_valid():

                serializer.save(household=household)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(
        detail=True, 
        methods=['get', 'patch'], 
        url_path='settings',
        permission_classes=[permissions.IsAuthenticated, IsHouseholdAdminOrReadOnly]
    )
    def update_household_settings(self, request, pk=None):
        household = self.get_object()

        if request.method == 'GET':
            serializer = HouseholdSettingsSerializer(household)
            return Response(serializer.data)

        if request.method == 'PATCH':
            serializer = HouseholdSettingsSerializer(household, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

    @action(
        detail=True, 
        methods=['patch'], 
        url_path='members/(?P<username>[^/.]+)',
        permission_classes=[permissions.IsAuthenticated, IsHouseholdAdminOrReadOnly]
    )
    def update_member_role(self, request, pk=None, username=None):
        """
        PATCH /api/households/<pk>/members/<username>/
        Ändert die Rolle eines Members basierend auf dem Usernamen.
        """
        household = self.get_object()
        
        try:
            member = HouseholdMember.objects.get(
                user__username=username, 
                household=household
            )
        except HouseholdMember.DoesNotExist:
            return Response(
                {"detail": f"User '{username}' is not a member of this household."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        new_role = request.data.get('role')
        if new_role not in ['ADMIN', 'MEMBER']:
            return Response(
                {"detail": "Invalid role. Choose 'ADMIN' or 'MEMBER'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if member.user == request.user and new_role == 'MEMBER':
            return Response(
                {"detail": "You cannot demote yourself from ADMIN to MEMBER."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        member.role = new_role
        member.save()

        return Response(
            {"message": f"User '{username}' is now {new_role}."}, 
            status=status.HTTP_200_OK
        )
    
    @action(
        detail=True, 
        methods=['get', 'post'], 
        url_path='incomes',
        permission_classes=[permissions.IsAuthenticated, IsHouseholdMember]
    )
    def incomes(self, request, pk=None):
        household = self.get_object()

        if request.method == 'GET':
            incomes = household.incomes.all()
            serializer = IncomeSerializer(incomes, many=True)
            return Response(serializer.data)

        if request.method == 'POST':
            serializer = IncomeSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(household=household, user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    @action(
        detail=True, 
        methods=['get', 'post'], 
        url_path='transactions',
        permission_classes=[permissions.IsAuthenticated, IsHouseholdMember]
    )
    def transactions(self, request, pk=None):
        household = self.get_object()

        if request.method == 'GET':
            transactions = household.transactions.all()
            serializer = TransactionSerializer(transactions, many=True)
            return Response(serializer.data)
        
        if request.method == 'POST':
            serializer = TransactionSerializer(data=request.data, context={'view': self})
            if serializer.is_valid():
                transaction = serializer.save(household=household, paid_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['get'])
    def category_stats(self, request, pk=None):
        household = self.get_object()
    
        stats = household.transactions.filter(
            transaction_type='EXPENSE'
        ).values('category__name', 'category__icon', 'category__color').annotate(
            total_spent=Sum('amount')
        )
    
        return Response(stats)

class CategoryViewSet(mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    Handles ONLY updating (PATCH) and deleting (DELETE) individual categories via /api/categories/<id>/
    """
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsHouseholdMember]

    def get_queryset(self):
        """
        SECURITY: A user can only access a category if they are a member 
        of the household that the category belongs to.
        """
        return Category.objects.filter(household__members=self.request.user)

class TransactionViewSet(mixins.RetrieveModelMixin, 
                         mixins.UpdateModelMixin, 
                         mixins.DestroyModelMixin, 
                         viewsets.GenericViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsHouseholdMember]

    def get_queryset(self):
        return Transaction.objects.filter(household__members=self.request.user)