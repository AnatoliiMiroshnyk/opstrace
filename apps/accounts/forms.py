from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.workspaces.models import Membership, Workspace


class RegistrationForm(forms.ModelForm):
    workspace_name = forms.CharField(
        label="Назва робочого простору",
        max_length=120,
        help_text="Наприклад, назва вашої компанії або команди.",
    )
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Підтвердження пароля",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": "Ім’я",
            "last_name": "Прізвище",
            "email": "Email",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Користувач із таким email вже існує.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Паролі не збігаються.")
        if password1:
            candidate = User(
                email=cleaned.get("email", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                password_validation.validate_password(password1, candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            raise ValueError("Registration must be saved atomically.")
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password1"])
        user.save()
        workspace = Workspace.objects.create(
            name=self.cleaned_data["workspace_name"].strip(),
            created_by=user,
        )
        Membership.objects.create(
            workspace=workspace,
            user=user,
            role=Membership.Role.OWNER,
        )
        return user, workspace
