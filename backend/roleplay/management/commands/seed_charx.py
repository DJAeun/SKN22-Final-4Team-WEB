import json
import os
import zipfile

from django.conf import settings
from django.core.management.base import BaseCommand

from roleplay.models import RpgCharacterImage, RpgLorebook


class Command(BaseCommand):
    help = 'Seeds RpgLorebook and RpgCharacterImage from a RisuAI .charx file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the .charx file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        with zipfile.ZipFile(file_path, 'r') as z:
            card_json = z.read('card.json').decode('utf-8')
            card_data = json.loads(card_json).get('data', {})

            # Wipe existing to prevent duplicates.
            RpgLorebook.objects.all().delete()
            RpgCharacterImage.objects.all().delete()
            self.stdout.write("Deleted existing RpgLorebook and RpgCharacterImage entries.")

            # 1. Base Setup (Description + Personality)
            base_content = f"Name: {card_data.get('name', 'Unknown')}\n\n"
            base_content += f"Description: {card_data.get('description', '')}\n\n"
            base_content += f"Personality: {card_data.get('personality', '')}\n\n"
            base_content += f"Scenario: {card_data.get('scenario', '')}\n"

            RpgLorebook.objects.create(
                keywords=["기본프로필", "페르소나", "핵심설정"],
                lorebook=base_content,
                priority=100,  # Base profile usually highest priority to stay
                is_constant=True,
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS("Seeded Base Profile into RpgLorebook"))

            # Save the First Message separately.
            RpgLorebook.objects.create(
                keywords=["FirstMessage"],
                lorebook=card_data.get('first_mes', '안녕!'),
                priority=0,
                is_constant=False,
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS("Seeded First Message"))

            # 2. Lorebook Entries
            char_book = card_data.get('character_book', {})
            entries = char_book.get('entries', [])
            count = 0
            for entry in entries:
                keys = entry.get('keys', [])
                content = entry.get('content', '')
                if keys and content:
                    RpgLorebook.objects.create(
                        keywords=keys,
                        lorebook=content,
                        priority=entry.get('priority', 50),
                        is_constant=entry.get('constant', False),
                        is_active=True,
                    )
                    count += 1
            self.stdout.write(self.style.SUCCESS(f"Seeded {count} Lorebook entries"))

            # 3. Extract Images
            media_dir = os.path.join(settings.BASE_DIR, 'media', 'character_images')
            os.makedirs(media_dir, exist_ok=True)

            img_count = 0
            for name in z.namelist():
                if name.startswith('assets/other/image/') or name.startswith('assets/icon/image/'):
                    filename = os.path.basename(name)
                    basename, ext = os.path.splitext(filename)
                    if not ext:
                        continue

                    target_path = os.path.join(media_dir, filename)
                    with open(target_path, 'wb') as f:
                        f.write(z.read(name))

                    rel_url = f'character_images/{filename}'
                    RpgCharacterImage.objects.create(
                        clothes=basename,
                        emotion="neutral",
                        image_url=rel_url,
                        is_active=True,
                    )
                    img_count += 1

            self.stdout.write(self.style.SUCCESS(f"Extracted and seeded {img_count} images into RpgCharacterImage"))
