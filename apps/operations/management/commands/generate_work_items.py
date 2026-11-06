"""Generate due work items from active routines.

Safe to run repeatedly. A database uniqueness constraint guarantees that a
routine can have only one work item for a given scheduled date.
"""
import calendar
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.operations.models import AuditEvent, Routine, WorkItem


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_occurrence(value: date, cadence: str) -> date:
    if cadence == Routine.Cadence.DAILY:
        return value + timedelta(days=1)
    if cadence == Routine.Cadence.WEEKLY:
        return value + timedelta(weeks=1)
    if cadence == Routine.Cadence.MONTHLY:
        return add_months(value, 1)
    if cadence == Routine.Cadence.QUARTERLY:
        return add_months(value, 3)
    if cadence == Routine.Cadence.YEARLY:
        return add_months(value, 12)
    raise ValueError(f"Unsupported cadence: {cadence}")


class Command(BaseCommand):
    help = "Generate scheduled work items for active routines."

    def add_arguments(self, parser):
        parser.add_argument(
            "--through",
            type=date.fromisoformat,
            default=timezone.localdate(),
            help="Generate occurrences through this date (YYYY-MM-DD). Defaults to today.",
        )

    def handle(self, *args, **options):
        through = options["through"]
        if through > timezone.localdate() + timedelta(days=366):
            raise CommandError("The generation horizon cannot be more than one year ahead.")

        created_count = 0
        processed_count = 0
        routine_ids = list(
            Routine.objects.filter(is_active=True, next_due_date__lte=through)
            .order_by("pk")
            .values_list("pk", flat=True)
        )

        for routine_id in routine_ids:
            with transaction.atomic():
                routine = (
                    Routine.objects.select_for_update()
                    .select_related("workspace", "assigned_to")
                    .get(pk=routine_id)
                )
                occurrence = routine.next_due_date
                while occurrence <= through:
                    processed_count += 1
                    item, created = WorkItem.objects.get_or_create(
                        routine=routine,
                        scheduled_for=occurrence,
                        defaults={
                            "workspace": routine.workspace,
                            "due_date": occurrence,
                            "title": routine.name,
                            "instructions": routine.instructions,
                            "assigned_to": routine.assigned_to,
                            "priority": routine.priority,
                        },
                    )
                    if created:
                        created_count += 1
                        AuditEvent.objects.create(
                            workspace=routine.workspace,
                            work_item=item,
                            event_type=AuditEvent.EventType.ITEM_GENERATED,
                            details={
                                "routine_id": routine.pk,
                                "scheduled_for": occurrence.isoformat(),
                            },
                        )
                    occurrence = next_occurrence(occurrence, routine.cadence)

                routine.next_due_date = occurrence
                routine.save(update_fields=("next_due_date", "updated_at"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {processed_count} occurrence(s); created {created_count} work item(s)."
            )
        )
