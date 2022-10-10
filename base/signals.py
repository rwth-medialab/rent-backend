from django.contrib.auth.models import User, Group, Permission
import logging

logger = logging.getLogger("django")


def populate_models(sender, **kwargs):
    # create groups
    try:
        # test if a user exists, if not create a adminuser asuming the first user would be the admin user. 
        # If the user exists assume that the creation of the default objects already happenend
        User.objects.get(id=1)
    except:
        new_User = User.objects.create(
            username='admin', is_staff=True, is_superuser=True)
        new_User.set_password('admin')
        new_User.save()
        send_log_created(name="admin", created=True)
        mitarbeiter_group, created = Group.objects.get_or_create(
            name='mitarbeiter')
        send_log_created(name="mitarbeiter", created=created)
        verleiher_group, created = Group.objects.get_or_create(name='verleiher')
        send_log_created(name="verleiher", created=created)
        # assign permissions to groups
        mitarbeiter_group.permissions.add()
        # create users


def send_log_created(name: str, created: bool):
    if created:
        logger.info(f"{name} created")
    else:
        logger.debug(f"{name} already exists")
