from django import forms

from apps.accounts.models import User
from apps.operations.models import Evidence, Routine


class RoutineForm(forms.ModelForm):
    class Meta:
        model = Routine
        fields = (
            "name",
            "instructions",
            "cadence",
            "next_due_date",
            "assigned_to",
            "priority",
            "is_active",
        )
        labels = {
            "name": "Назва регламенту",
            "instructions": "Інструкція / критерії виконання",
            "cadence": "Періодичність",
            "next_due_date": "Перша дата виконання",
            "assigned_to": "Відповідальний",
            "priority": "Пріоритет",
            "is_active": "Регламент активний",
        }
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 4}),
            "next_due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.fields["assigned_to"].queryset = User.objects.filter(
            memberships__workspace=workspace,
            memberships__is_active=True,
        ).distinct().order_by("email")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.workspace = self.workspace
        if commit:
            instance.full_clean()
            instance.save()
            self.save_m2m()
        return instance


class EvidenceForm(forms.ModelForm):
    class Meta:
        model = Evidence
        fields = ("file", "description")
        labels = {"file": "Файл підтвердження", "description": "Коментар до файлу"}
        widgets = {"description": forms.TextInput(attrs={"maxlength": 240})}


class ReviewForm(forms.Form):
    decision = forms.ChoiceField(
        label="Рішення",
        choices=(("approved", "Прийняти"), ("rejected", "Повернути на доопрацювання")),
        widget=forms.RadioSelect,
    )
    review_note = forms.CharField(
        label="Коментар",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == "rejected" and not cleaned.get("review_note", "").strip():
            self.add_error("review_note", "Вкажіть причину повернення на доопрацювання.")
        return cleaned
