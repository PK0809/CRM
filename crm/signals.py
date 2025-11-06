from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile when a new User is created.
    This will NOT cause recursive save() calls.
    """
    try:
        if created:
            # Create profile only for new users
            UserProfile.objects.create(
                user=instance,
                name=instance.get_full_name() or instance.username,
                phone_number=getattr(instance, "mobile", ""),
                role=getattr(instance, "role", "User"),
            )
            logger.info(f"✅ Created UserProfile for user: {instance.username}")
        else:
            # Update existing profile safely without recursion
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            profile.name = instance.get_full_name() or instance.username
            profile.role = getattr(instance, "role", "User")
            profile.save(update_fields=["name", "role", "updated_at"])
            logger.info(f"🔁 Updated UserProfile for user: {instance.username}")

    except Exception as e:
        logger.error(f"⚠️ Profile sync failed for user {getattr(instance, 'username', 'unknown')}: {e}")
