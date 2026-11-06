from datetime import date

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.operations.management.commands.generate_work_items import Command
from apps.operations.models import AuditEvent, Evidence, WorkItem
from apps.operations.services import (
    add_evidence,
    review_work_item,
    start_work_item,
    submit_work_item,
)
from apps.workspaces.models import Membership, Workspace

pytestmark = pytest.mark.django_db


def make_work_item(routine, **overrides):
    defaults = {
        "workspace": routine.workspace,
        "routine": routine,
        "scheduled_for": date(2025, 1, 1),
        "due_date": date(2025, 1, 1),
        "title": routine.name,
        "instructions": routine.instructions,
        "assigned_to": routine.assigned_to,
        "priority": routine.priority,
    }
    defaults.update(overrides)
    return WorkItem.objects.create(**defaults)


def test_scheduler_generates_missing_occurrences_once(routine_factory):
    routine = routine_factory()

    command = Command()
    command.handle(through=date(2025, 1, 2))
    command.handle(through=date(2025, 1, 2))

    assert WorkItem.objects.filter(routine=routine).count() == 2
    routine.refresh_from_db()
    assert routine.next_due_date == date(2025, 1, 3)
    assert AuditEvent.objects.filter(
        event_type=AuditEvent.EventType.ITEM_GENERATED
    ).count() == 2


def test_monthly_schedule_clamps_to_last_day():
    from apps.operations.management.commands.generate_work_items import add_months

    assert add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_workflow_requires_evidence_and_records_transitions(
    owner_context, routine_factory, django_user_model, tmp_path
):
    assignee = django_user_model.objects.create_user(
        email="operator@example.com", password="A-Strong-Test-Password-2026!"
    )
    Membership.objects.create(
        workspace=owner_context["workspace"], user=assignee, role=Membership.Role.MEMBER
    )
    routine = routine_factory(assigned_to=assignee)
    item = make_work_item(routine)

    start_work_item(item, assignee)
    with pytest.raises(ValidationError):
        submit_work_item(item, assignee)

    upload = SimpleUploadedFile(
        "inspection.pdf", b"%PDF-1.4 test evidence", content_type="application/pdf"
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        evidence = add_evidence(item, assignee, upload, "Inspection report")
        assert len(evidence.sha256) == 64
        submit_work_item(item, assignee)
        review_work_item(item, owner_context["owner"], WorkItem.Status.APPROVED)

    item.refresh_from_db()
    assert item.status == WorkItem.Status.APPROVED
    assert item.reviewed_by == owner_context["owner"]
    assert item.audit_events.count() == 4
    assert Evidence.objects.filter(work_item=item).count() == 1


def test_rejection_requires_a_reason(owner_context, routine_factory, django_user_model):
    reviewer = django_user_model.objects.create_user(
        email="reviewer@example.com", password="A-Strong-Test-Password-2026!"
    )
    Membership.objects.create(
        workspace=owner_context["workspace"], user=reviewer, role=Membership.Role.REVIEWER
    )
    item = make_work_item(routine_factory(), status=WorkItem.Status.SUBMITTED)

    with pytest.raises(ValidationError):
        review_work_item(item, reviewer, WorkItem.Status.REJECTED, "   ")

    review_work_item(item, reviewer, WorkItem.Status.REJECTED, "Report is incomplete")
    item.refresh_from_db()
    assert item.status == WorkItem.Status.REJECTED
    assert item.reviewed_by == reviewer
    assert item.review_note == "Report is incomplete"


def test_assignee_cannot_review_own_result(owner_context, routine_factory):
    item = make_work_item(routine_factory(), status=WorkItem.Status.SUBMITTED)

    with pytest.raises(PermissionDenied):
        review_work_item(item, owner_context["owner"], WorkItem.Status.APPROVED)


def test_member_cannot_review_submitted_item(owner_context, routine_factory, django_user_model):
    member = django_user_model.objects.create_user(
        email="member@example.com", password="A-Strong-Test-Password-2026!"
    )
    Membership.objects.create(
        workspace=owner_context["workspace"], user=member, role=Membership.Role.MEMBER
    )
    item = make_work_item(routine_factory(), status=WorkItem.Status.SUBMITTED)

    with pytest.raises(PermissionDenied):
        review_work_item(item, member, WorkItem.Status.APPROVED)


def test_audit_events_are_append_only(owner_context):
    event = AuditEvent.objects.create(
        workspace=owner_context["workspace"],
        actor=owner_context["owner"],
        event_type=AuditEvent.EventType.ROUTINE_CREATED,
        details={"name": "Daily check"},
    )

    event.details["name"] = "tampered"
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
    with pytest.raises(ValidationError):
        AuditEvent.objects.filter(pk=event.pk).update(details={"changed": True})
    with pytest.raises(ValidationError):
        AuditEvent.objects.filter(pk=event.pk).delete()


def test_user_cannot_see_another_workspace_items(client, owner_context, routine_factory, django_user_model):
    routine = routine_factory()
    foreign_owner = django_user_model.objects.create_user(
        email="other@example.com", password="A-Strong-Test-Password-2026!"
    )
    foreign_workspace = Workspace.objects.create(name="Other Workspace", created_by=foreign_owner)
    foreign_routine = routine_factory(
        workspace=foreign_workspace,
        assigned_to=foreign_owner,
        created_by=foreign_owner,
        name="Foreign confidential check",
    )
    foreign_item = make_work_item(foreign_routine)

    client.force_login(owner_context["owner"])
    response = client.get(reverse("operations:items"))

    assert response.status_code == 200
    assert str(foreign_item.pk) not in response.content.decode()
    assert "Foreign confidential check" not in response.content.decode()
    assert routine.name not in response.content.decode()  # no due occurrences were generated


def test_registration_creates_workspace_and_owner_membership(client, django_user_model):
    response = client.post(
        reverse("accounts:register"),
        {
            "first_name": "New",
            "last_name": "Owner",
            "email": "new-owner@example.com",
            "workspace_name": "New Team",
            "password1": "A-Unique-Strong-Password-2026!",
            "password2": "A-Unique-Strong-Password-2026!",
        },
    )

    assert response.status_code == 302
    user = django_user_model.objects.get(email="new-owner@example.com")
    membership = Membership.objects.get(user=user)
    assert membership.role == Membership.Role.OWNER
    assert membership.workspace.name == "New Team"
