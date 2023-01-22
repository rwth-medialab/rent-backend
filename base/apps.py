from django.apps import AppConfig
from django.db.models.signals import post_migrate


class BaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'base'

    def ready(self) -> None:
        from .signals import populate_models
        post_migrate.connect(populate_models, sender=self)
        
        """
        create every setting from settings.py that is supposed to exist in db in the db. we need to do those ugly imports here because models are not initialized otherwise
        """
        from base import models
        from django.conf import settings
        if not models.Settings.objects.filter(type='lenting_day').exists():
            models.Settings.objects.create(
                type='lenting_day', value=settings.DEFAULT_LENTING_DAY_OF_WEEK, public=True)

        if not models.Settings.objects.filter(type='lenting_start_hour').exists():
            models.Settings.objects.create(
                type='lenting_start_hour', value=settings.DEFAULT_LENTING_START_HOUR, public=True)

        if not models.Settings.objects.filter(type='lenting_end_hour').exists():
            models.Settings.objects.create(
                type='lenting_end_hour', value=settings.DEFAULT_LENTING_END_HOUR, public=True)

        if not models.Settings.objects.filter(type='returning_day').exists():
            models.Settings.objects.create(
                type='returning_day', value=settings.DEFAULT_RETURNING_DAY_OF_WEEK, public=True)

        if not models.Settings.objects.filter(type='returning_start_hour').exists():
            models.Settings.objects.create(
                type='returning_start_hour', value=settings.DEFAULT_RETURNING_START_HOUR, public=True)

        if not models.Settings.objects.filter(type='returning_end_hour').exists():
            models.Settings.objects.create(
                type='returning_end_hour', value=settings.DEFAULT_RETURNING_END_HOUR, public=True)

        if not models.Settings.objects.filter(type='email_validation_regex').exists():
            models.Settings.objects.create(type='email_validation_regex', value=settings.EMAIL_VALIDATION_REGEX, public=True)

        """
        populate some defaults, for example the default priority class, or default texts
        """
        if not models.Priority.objects.filter(prio=99).exists():
            models.Priority.objects.create(
                prio=99, name="unverified", description="Default renting class, should be the one with the shortest renting durations")
        if not models.Priority.objects.filter(prio=50, name="automatically verified").exists():
            models.Priority.objects.create(
                prio=50, name="automatically verified", description="Person is automatically verified.")
        if not models.Priority.objects.filter(prio=49).exists():
            models.Priority.objects.create(
                prio=49, name="manually verified", description="Person is manually verified.")

        if not models.Text.objects.filter(name='signup_mail').exists():
            models.Text.objects.create(
                name='signup_mail', content="Hallo {{first_name}}, bitte aktiviere dein Konto unter {{validation_link}}")
