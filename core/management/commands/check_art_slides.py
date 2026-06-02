from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import ArtSlide


class Command(BaseCommand):
    help = "Verify active art slides reference files that exist under static/."

    def handle(self, *args, **options):
        static_root = Path(settings.BASE_DIR) / "static"
        missing = []
        inactive_missing = []

        for slide in ArtSlide.objects.order_by("sort_order", "title"):
            path = static_root / slide.static_path
            if path.is_file():
                continue
            if slide.is_active:
                missing.append(slide)
            else:
                inactive_missing.append(slide)

        if missing:
            self.stdout.write(self.style.ERROR(f"Active slides missing files ({len(missing)}):"))
            for slide in missing:
                self.stdout.write(f"  - {slide.title}: {slide.static_path}")
        else:
            self.stdout.write(self.style.SUCCESS("All active slides have image files on disk."))

        active_count = ArtSlide.objects.filter(is_active=True).count()
        on_disk = sum(
            1
            for slide in ArtSlide.objects.filter(is_active=True)
            if (static_root / slide.static_path).is_file()
        )
        self.stdout.write(f"Active in DB: {active_count}, files present: {on_disk}")

        if inactive_missing:
            self.stdout.write(f"Inactive slides with missing files: {len(inactive_missing)}")

        if missing:
            raise SystemExit(1)
