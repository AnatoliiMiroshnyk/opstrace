from datetime import date

import pytest

from apps.workspaces.models import Membership, Workspace


@pytest.fixture
def owner_context(django_user_model):
    owner = django_user_model.objects.create_user(
        email="owner@example.com",
        password="A-Strong-Test-Password-2026!",
        first_name="Test",
        last_name="Owner",
    )
    workspace = Workspace.objects.create(name="Northwind Operations", created_by=owner)
    membership = Membership.objects.create(
        workspace=workspace,
        user=owner,
        role=Membership.Role.OWNER,
    )
    return {"owner": owner, "workspace": workspace, "membership": membership}


@pytest.fixture
def routine_factory(owner_context, django_user_model):
    from apps.operations.models import Routine

    def create(**overrides):
        defaults = {
            "workspace": owner_context["workspace"],
            "name": "Inspect backup appliance",
            "instructions": "Check backup completion and attach the report.",
            "cadence": Routine.Cadence.DAILY,
            "next_due_date": date(2025, 1, 1),
            "assigned_to": owner_context["owner"],
            "priority": Routine.Priority.NORMAL,
            "created_by": owner_context["owner"],
        }
        defaults.update(overrides)
        return Routine.objects.create(**defaults)

    return create
