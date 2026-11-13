from django.core.management.base import BaseCommand
from django.db.models import Count
from lost_pets.models import PushDelivery, MobilePushDevice


class Command(BaseCommand):
    help = "Show aggregate push outcomes without tokens or personal content."

    def handle(self, *args, **options):
        self.stdout.write(f"Active devices: {MobilePushDevice.objects.filter(active=True).count()}")
        for row in PushDelivery.objects.values("state", "outcome").annotate(total=Count("pk")).order_by("state", "outcome"):
            self.stdout.write(f"{row['state']} / {row['outcome'] or '-'}: {row['total']}")
