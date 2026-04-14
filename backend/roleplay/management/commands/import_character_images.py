from pathlib import Path
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from roleplay.models import RpgCharacterImage


DIRECTORY_TO_CLOTHES = {
    "roleplayimg_daily": "daily",
    "roleplayimg_suit": "suit",
    "roleplayimg_baking": "baking",
}

VALID_EMOTIONS = {
    "serious",
    "depressed",
    "angry",
    "aroused",
    "bored",
    "curious",
    "disgust",
    "embarrassed",
    "excited",
    "happy",
    "nervous",
    "neutral",
    "panic",
    "pout",
    "proud",
    "sad",
    "sleepy",
    "smug",
    "surprised",
    "thinking",
    "worried",
}

EMOTION_ALIASES = {
    "suprised": "surprised",
}


class Command(BaseCommand):
    help = "Imports CharacterImage rows from backend/media/character_images subfolders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            type=str,
            default=None,
            help="Optional base directory containing roleplayimg_daily/suit/baking folders.",
        )

    def handle(self, *args, **options):
        base_dir = Path(options["base_dir"]) if options["base_dir"] else settings.MEDIA_ROOT / "character_images"
        base_dir = base_dir.resolve()

        if not base_dir.exists():
            raise CommandError(f"Character image directory not found: {base_dir}")

        imported_count = 0
        updated_count = 0
        skipped_files: list[str] = []

        for directory_name, clothes in DIRECTORY_TO_CLOTHES.items():
            source_dir = base_dir / directory_name
            if not source_dir.exists():
                self.stdout.write(self.style.WARNING(f"Skipped missing directory: {source_dir}"))
                continue

            for file_path in sorted(path for path in source_dir.iterdir() if path.is_file()):
                emotion = self._extract_emotion(file_path.name)
                if not emotion:
                    skipped_files.append(str(file_path))
                    continue

                image_url = f"/media/character_images/{directory_name}/{file_path.name}"
                obj, created = RpgCharacterImage.objects.update_or_create(
                    clothes=clothes,
                    emotion=emotion,
                    defaults={
                        "image_url": image_url,
                        "is_active": True,
                    },
                )

                if created:
                    imported_count += 1
                else:
                    updated_count += 1

                self.stdout.write(
                    f"{'Created' if created else 'Updated'}: {obj.clothes}_{obj.emotion} -> {image_url}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Character image import complete. Created={imported_count}, Updated={updated_count}, Skipped={len(skipped_files)}"
            )
        )

        if skipped_files:
            self.stdout.write(self.style.WARNING("Skipped files:"))
            for skipped in skipped_files:
                self.stdout.write(f"- {skipped}")

    def _extract_emotion(self, filename: str) -> str:
        stem = Path(filename).stem
        if stem.lower() == "hari_neutral":
            return "neutral"

        match = re.match(r"^Hari_([A-Za-z]+)", stem)
        if not match:
            return ""

        raw_emotion = match.group(1).lower()
        normalized_emotion = EMOTION_ALIASES.get(raw_emotion, raw_emotion)

        if normalized_emotion not in VALID_EMOTIONS:
            return ""

        return normalized_emotion
