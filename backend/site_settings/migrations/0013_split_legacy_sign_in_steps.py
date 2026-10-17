from django.db import migrations


def split_legacy_items(content):
    if not isinstance(content, dict):
        return None

    localized_content = []
    if 'items' in content:
        localized_content.append((None, content))
    localized_content.extend(
        (language, value)
        for language, value in content.items()
        if isinstance(value, dict) and 'items' in value
    )

    updated_content = dict(content)
    changed = False
    for language, localized in localized_content:
        if 'account_setup_steps' in localized or 'learning_steps' in localized:
            continue
        items = localized['items']
        if not isinstance(items, list) or len(items) != 13:
            continue

        def to_step(item):
            if isinstance(item, dict):
                return {
                    'title': item.get('title', ''),
                    'desc': item.get('desc', item.get('description', '')),
                }
            if isinstance(item, (list, tuple)):
                return {
                    'title': item[0] if item else '',
                    'desc': item[1] if len(item) > 1 else '',
                }
            return {'title': str(item), 'desc': ''}

        migrated = dict(localized)
        migrated.setdefault('account_setup_title', 'Set up your account')
        migrated.setdefault('learning_title', 'Start learning')
        migrated['account_setup_steps'] = [to_step(item) for item in items[:7]]
        migrated['learning_steps'] = [to_step(item) for item in items[7:]]
        if language is None:
            updated_content = migrated
        else:
            updated_content[language] = migrated
        changed = True

    return updated_content if changed else None


def split_home_sign_in_steps(apps, schema_editor):
    PageContent = apps.get_model('site_settings', 'PageContent')
    PageSection = apps.get_model('site_settings', 'PageSection')
    section = PageSection.objects.filter(
        page__slug='home',
        key='sign-in-process',
    ).first()
    if section is None:
        return

    migrated_content = split_legacy_items(section.content)
    if migrated_content is not None:
        section.content = migrated_content
        section.save(update_fields=['content'])


class Migration(migrations.Migration):
    dependencies = [('site_settings', '0012_seed_sign_in_process')]

    operations = [
        migrations.RunPython(split_home_sign_in_steps, migrations.RunPython.noop),
    ]
