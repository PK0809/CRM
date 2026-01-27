from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create or update UserProfile safely.
    - Creates profile if missing
    - Updates basic fields
    - NEVER raises exception in production
    """

    try:
        profile, _ = UserProfile.objects.get_or_create(user=instance)

        # Sync basic fields safely
        profile.name = instance.get_full_name() or instance.username
        profile.role = getattr(instance, "role", "User")
        profile.phone_number = getattr(instance, "mobile", "") or ""

        profile.save()

    except Exception as e:
        # ✅ Log error but DO NOT crash production
        logger.exception(
            "UserProfile sync failed | user_id=%s username=%s error=%s",
            instance.pk,
            instance.username,
            str(e),
        )
