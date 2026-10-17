from django.db import migrations


FEATURE_FLAG_KEYS = (
    'email_center',
    'contact_autoreply',
    'enrollment_emails',
    'notices',
    'support_assistant',
    'legal_pages',
    'social_proof',
    'course_reviews',
    'roles',
    'notifications',
    'assignments',
    'discussions',
    'programs',
    'analytics_dashboard',
    'ai_governance',
    'payments',
    'certificate_verify',
    'privacy_tools',
    'business_plan',
    'pitch_lab',
    'adaptive_learning',
    'startup_tools',
    'voice_audio',
    'pwa',
    'channels',
    'gamification',
    'challenges',
    'community',
    'ecosystem',
    'ethiopia_utils',
)


def seed_feature_flags(apps, schema_editor):
    FeatureFlag = apps.get_model('feature_flags', 'FeatureFlag')
    FeatureFlag.objects.using(schema_editor.connection.alias).bulk_create(
        [FeatureFlag(key=key, is_enabled=False) for key in FEATURE_FLAG_KEYS],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('feature_flags', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_feature_flags, migrations.RunPython.noop),
    ]
