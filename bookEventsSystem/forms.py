from django import forms
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Event

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'role')

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name')

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'category', 'date', 'price', 'status']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date <= timezone.now():
            raise forms.ValidationError("The event date must be in the future.")
        return date