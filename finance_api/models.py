from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Household(models.Model):
    CYCLE_CHOICES = [
        ('CALENDAR_MONTH', 'Standard Calendar Month (1st to end)'),
        ('CUSTOM_DAY', 'Custom Day of Month'),
        ('DYNAMIC_INCOME', 'Dynamic (Earliest income of the month)'),
    ]

    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    split_mode_enabled = models.BooleanField(default=False)
    
    billing_cycle_type = models.CharField(
        max_length=20, 
        choices=CYCLE_CHOICES, 
        default='CALENDAR_MONTH'
    )
    
    payday_start = models.PositiveSmallIntegerField(
        default=1, 
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    
    members = models.ManyToManyField(User, through='HouseholdMember', related_name='households')

    def __str__(self):
        return self.name


class HouseholdMember(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('MEMBER', 'Member'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    household = models.ForeignKey(Household, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='MEMBER')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'household')

    def __str__(self):
        return f"{self.user.username} - {self.role} in {self.household.name}"


class Income(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='incomes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    title = models.CharField(max_length=100, default="Salary")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    is_recurring = models.BooleanField(default=True)
    date = models.DateField()

    def __str__(self):
        return f"{self.user.username}: {self.amount} ({self.title})"


class Category(models.Model):
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=50, default="folder") 
    color = models.CharField(max_length=7, default="#3f51b5") 
    household = models.ForeignKey(Household, on_delete=models.CASCADE, null=True, blank=True, related_name='categories')

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ('name', 'household')

    def __str__(self):
        return f"{self.name} ({'Global' if not self.household else self.household.name})"


class Budget(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    percentage = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(100)])

    class Meta:
        unique_together = ('household', 'category', 'month', 'year')

    def __str__(self):
        type_str = f"{self.amount}" if self.amount else f"{self.percentage}%"
        return f"Budget {self.category.name}: {type_str} ({self.month}/{self.year})"


class SavingsGoal(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='savings_goals')
    title = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    target_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.current_amount} / {self.target_amount})"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('SAVING', 'Saving'),
    ]
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions', null=True, blank=True)
    paid_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='transactions')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    transaction_type = models.CharField(max_length=7, choices=TRANSACTION_TYPES)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    savings_goal = models.ForeignKey(SavingsGoal, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    split_with = models.ManyToManyField(User, blank=True, related_name='shared_transactions')

    def __str__(self):
        return f"{self.title} ({self.amount}) - {self.transaction_type}"