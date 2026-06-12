from django.core.management.base import BaseCommand

from core.art_slides import slide_has_source
from core.models import ArtSlide


class Command(BaseCommand):
    help = "Verify active art slides have an uploaded image or bundled static file."

    def handle(self, *args, **options):
        missing = []
        inactive_missing = []

        for slide in ArtSlide.objects.order_by("sort_order", "title"):
            if slide_has_source(slide):
                continue
            if slide.is_active:
                missing.append(slide)
            else:
                inactive_missing.append(slide)

        if missing:
            self.stdout.write(self.style.ERROR(f"Active slides missing files ({len(missing)}):"))
            for slide in missing:
                source = slide.image.name if slide.image else slide.static_path or "(no source)"
                self.stdout.write(f"  - {slide.title}: {source}")
        else:
            self.stdout.write(self.style.SUCCESS("All active slides have image files on disk."))

        active_count = ArtSlide.objects.filter(is_active=True).count()
        on_disk = sum(1 for slide in ArtSlide.objects.filter(is_active=True) if slide_has_source(slide))
        self.stdout.write(f"Active in DB: {active_count}, files present: {on_disk}")

        if inactive_missing:
            self.stdout.write(f"Inactive slides with missing files: {len(inactive_missing)}")

        if missing:
            raise SystemExit(1)
