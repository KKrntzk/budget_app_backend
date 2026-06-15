from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.contrib.auth.models import User
from .serializers import RegisterSerializer, HouseholdSerializer
from ..models import Household, HouseholdMember
from .permissions import IsHouseholdMember

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