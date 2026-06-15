from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, HouseholdSerializer, CategorySerializer, InviteSerializer
from ..models import Household, HouseholdMember, Category
from .permissions import IsHouseholdMember, IsHouseholdAdminOrReadOnly
from rest_framework.decorators import action
from rest_framework import mixins

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