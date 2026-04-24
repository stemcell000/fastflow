# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import forms # type: ignore
from django.contrib.auth.forms import UserCreationForm # type: ignore
from authentication.models import CustomUser # type: ignore


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control"
            }
        ))
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control"
            }
        ))


class SignUpForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control"
            }
        ))
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email",
                "class": "form-control"
            }
        ))
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control"
            }
        ))
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password check",
                "class": "form-control"
            }
        ))


    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')
        
class CustomUserCreationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'avatar', 'is_active', 'is_staff', 'is_superuser', 'is_human', 'groups')

    def save(self, commit=True):
        user = super().save(commit=False)
        # Do not set password as it's handled by LDAP
        if commit:
            user.save()
        return user

class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'avatar', 'is_active', 'is_staff', 'is_superuser', 'is_human', 'groups')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password1 and password2 fields as they are handled by LDAP
        self.fields.pop('password1', None)
        self.fields.pop('password2', None)
