from django.core.management.base import BaseCommand
from chat.memory_vector import process_new_contents


class Command(BaseCommand):
    help = "Summarize and embed any generated_contents rows missing summary or content_vector."

    def handle(self, *args, **options):
        count = process_new_contents()
        self.stdout.write(self.style.SUCCESS(f"Processed {count} content(s)."))
