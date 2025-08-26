# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from api.models import Usuário

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def vincular_usuario_api(sender, instance, created, **kwargs):
    if created:
        try:
            usuario = Usuário.objects.get(email=instance.email)
            usuario.user = instance
            usuario.save()
        except Usuário.DoesNotExist:
            pass  # se não existir avaliação prévia, não faz nada
