from django import forms
from django.contrib import admin
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User


class EmailUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Підтвердження пароля", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email",)

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Паролі не збігаються.")
        if password1:
            try:
                password_validation.validate_password(password1, self.instance)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self.save_m2m()
        return user


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = EmailUserCreationForm
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Особиста інформація", {"fields": ("first_name", "last_name")}),
        (
            "Права доступу",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Дати", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
