import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from lost_pets.push import process_push_batch


class Command(BaseCommand):
    help = "Process Expo outbox and receipts; --once runs one bounded batch."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write("Expo push worker started")
        while True:
            close_old_connections()
            count = process_push_batch()
            if options["once"]:
                self.stdout.write(f"Processed: {count}")
                return
            time.sleep(2)
