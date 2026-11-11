from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'moderator'
            self.is_staff = True
        elif self.role in ['admin', 'moderator']:
            self.is_staff = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

class Event(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('canceled', 'Canceled'),
        ('completed', 'Completed'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)
    date = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    def is_available_for_booking(self):
        if self.status in ['canceled', 'completed', 'draft']:
            return False
        if self.date <= timezone.now():
            return False
        return True

    def __str__(self):
        return self.title

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')

    def clean(self):
        if self.event.organizer == self.user:
            raise ValidationError("You cannot book your own event.")
        if not self.event.is_available_for_booking():
            raise ValidationError("This event is no longer available for booking (past event or unavailable).")

    def __str__(self):
        return f"{self.user.username} - {self.event.title}"