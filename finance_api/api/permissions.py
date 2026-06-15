from rest_framework import permissions
from ..models import HouseholdMember

class IsHouseholdMember(permissions.BasePermission):
    """
    Custom permission to only allow members of a household to view or edit its data.
    """
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'members'):
            return HouseholdMember.objects.filter(user=request.user, household=obj).exists()
        
        if hasattr(obj, 'household'):
            return HouseholdMember.objects.filter(user=request.user, household=obj.household).exists()
            
        return False

class IsHouseholdAdminOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return HouseholdMember.objects.filter(user=request.user, household=obj).exists()

        membership = HouseholdMember.objects.filter(user=request.user, household=obj).first()
        return membership is not None and membership.role == 'ADMIN'