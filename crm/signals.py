from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

import logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    try:
        if created:
            UserProfile.objects.create(user=instance)
        else:
            UserProfile.objects.update_or_create(user=instance)
    except Exception as e:
        logger.error(f"Profile sync failed for user {instance.username}: {e}")
