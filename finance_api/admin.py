from django.contrib import admin
from .models import Household, HouseholdMember, Income, Category, Budget, SavingsGoal, Transaction

admin.site.register(Household)
admin.site.register(HouseholdMember)
admin.site.register(Income)
admin.site.register(Category)
admin.site.register(Budget)
admin.site.register(SavingsGoal)
admin.site.register(Transaction)