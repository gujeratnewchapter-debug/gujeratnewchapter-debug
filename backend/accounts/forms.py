from django import forms

from .models import User


class AdminUserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'
        labels = {
            'avatar': 'Instructor photo',
        }
        help_texts = {
            'avatar': 'Upload the photo shown beside this instructor\'s courses.',
        }