from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, HouseholdSerializer, AddMemberSerializer
from ..models import Household, HouseholdMember
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
    A ViewSet that handles Listing, Creating, Retrieving, Updating, and Deleting Households.
    """
    serializer_class = HouseholdSerializer
    permission_classes = [permissions.IsAuthenticated, IsHouseholdMember]

    def get_queryset(self):
        """
        CRITICAL SECURITY: This ensures a user CAN ONLY SEE households 
        where they are actually a registered member.
        """
        return Household.objects.filter(members=self.request.user)

    def perform_create(self, serializer):
        """
        When a user creates a household, they automatically become the ADMIN of it.
        """
        household = serializer.save()
        
        HouseholdMember.objects.create(
            user=self.request.user,
            household=household,
            role='ADMIN'
        )
    
    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        """
        Endpoint: POST /api/households/<id>/add-member/
        Allows a household ADMIN to add another user to the household.
        """
        household = self.get_object()
       
        current_member_status = HouseholdMember.objects.filter(user=request.user, household=household).first()
        if not current_member_status or current_member_status.role != 'ADMIN':
            return Response(
                {"detail": "You do not have permission to add members. Only Admins can do this."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AddMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        target_user = User.objects.get(username=serializer.validated_data['username'])

        if HouseholdMember.objects.filter(user=target_user, household=household).exists():
            return Response(
                {"detail": f"User '{target_user.username}' is already a member of this household."},
                status=status.HTTP_400_BAD_REQUEST
            )

        HouseholdMember.objects.create(
            user=target_user,
            household=household,
            role='MEMBER' 
        )

        return Response(
            {"message": f"User '{target_user.username}' was successfully added to the household."},
            status=status.HTTP_200_OK
        )