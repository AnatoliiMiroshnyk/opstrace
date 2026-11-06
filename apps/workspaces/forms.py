from django import forms
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.workspaces.models import Membership


class TeamMemberForm(forms.Form):
    email = forms.EmailField(label="Email користувача")
    role = forms.ChoiceField(
        label="Роль",
        choices=(
            (Membership.Role.ADMIN, "Адміністратор"),
            (Membership.Role.REVIEWER, "Перевіряльник"),
            (Membership.Role.MEMBER, "Учасник"),
        ),
    )

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.user_to_add = None

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        self.user_to_add = User.objects.filter(email__iexact=email, is_active=True).first()
        if self.user_to_add is None:
            raise ValidationError(
                "Обліковий запис не знайдено. Спочатку користувач має зареєструватися в OpsTrace."
            )
        if Membership.objects.filter(workspace=self.workspace, user=self.user_to_add).exists():
            raise ValidationError("Цей користувач уже має членство в робочому просторі.")
        return email

    def save(self):
        if not self.is_valid():
            raise ValueError("Cannot save an invalid form.")
        return Membership.objects.create(
            workspace=self.workspace,
            user=self.user_to_add,
            role=self.cleaned_data["role"],
        )
