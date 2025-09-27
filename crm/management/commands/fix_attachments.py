import os
from django.core.management.base import BaseCommand
from django.conf import settings
from crm.models import Estimation

class Command(BaseCommand):
    help = "Fix broken PO attachments in Estimation table"

    def handle(self, *args, **kwargs):
        media_root = os.path.join(settings.MEDIA_ROOT, "po_attachments")

        # Pick a fallback file (first valid one found)
        fallback_file = None
        for f in os.listdir(media_root):
            if f.endswith(".pdf"):
                fallback_file = f"po_attachments/{f}"
                break

        if not fallback_file:
            self.stdout.write(self.style.ERROR("❌ No PDF found in po_attachments. Nothing to fix."))
            return

        fixed = 0
        for e in Estimation.objects.exclude(po_attachment=""):
            file_path = os.path.join(settings.MEDIA_ROOT, os.path.basename(e.po_attachment.name))
            if not os.path.exists(file_path):
                self.stdout.write(f"[MISSING] {e.id} → {e.po_attachment.name} → replaced with {fallback_file}")
                e.po_attachment.name = fallback_file
                e.save()
                fixed += 1
            else:
                self.stdout.write(f"[OK] {e.id} → {e.po_attachment.name}")

        self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed} broken attachments"))
