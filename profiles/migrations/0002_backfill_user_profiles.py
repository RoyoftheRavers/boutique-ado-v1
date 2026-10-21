from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    """
    Create a UserProfile for every existing User that doesn't have one.

    Needed because the post_save signal on User only creates a profile
    going forward - without this, any existing user's next login (which
    saves the User instance via update_last_login) would crash trying
    to access/save a UserProfile that was never created for them.
    """
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('profiles', 'UserProfile')

    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)


def noop(apps, schema_editor):
    """ No-op reverse - profiles created here are left in place """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_missing_profiles, noop),
    ]
