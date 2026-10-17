from django.db import migrations


SIGN_IN_PROCESS_CONTENT = {
    'en': {
        'account_setup_title': 'Set up your account',
        'learning_title': 'Start learning',
        'account_setup_steps': [
            {
                'title': 'Create your account',
                'desc': 'Choose Sign up and enter the details requested on the registration form.',
            },
            {
                'title': 'Choose a sign-up method',
                'desc': 'Register with email, or continue with a supported Google or GitHub account.',
            },
            {
                'title': 'Check your inbox',
                'desc': 'If you registered with email, look for the verification message we send you.',
            },
            {
                'title': 'Verify your email',
                'desc': 'Open the verification link before signing in with your email and password.',
            },
            {
                'title': 'Return to sign in',
                'desc': 'After verification, use the same email and password you registered with.',
            },
            {
                'title': 'Complete your profile',
                'desc': 'Add the details that help make your learning experience your own.',
            },
            {
                'title': 'Choose a learning goal',
                'desc': 'Decide what you would like to learn or build first.',
            },
        ],
        'learning_steps': [
            {
                'title': 'Browse the course catalog',
                'desc': 'Explore practical topics in entrepreneurship, AI, finance, marketing, and leadership.',
            },
            {
                'title': 'Choose a course',
                'desc': 'Select a learning path that matches your interests and goals.',
            },
            {
                'title': 'Enroll and open the first lesson',
                'desc': 'Join the course and begin learning at your own pace.',
            },
            {
                'title': 'Learn with your AI Tutor',
                'desc': 'Ask questions and get help when a lesson concept is unclear.',
            },
            {
                'title': 'Practice as you go',
                'desc': 'Work through activities and quizzes to check your understanding.',
            },
            {
                'title': 'Complete your course',
                'desc': 'Finish the required lessons and quizzes to earn your certificate.',
            },
        ],
    },
}


def seed_sign_in_process(apps, schema_editor):
    PageContent = apps.get_model('site_settings', 'PageContent')
    PageSection = apps.get_model('site_settings', 'PageSection')
    home, _ = PageContent.objects.get_or_create(
        slug='home',
        defaults={
            'title': 'Ethiopian Startup School',
            'description': 'Learn entrepreneurship, AI, and business skills with practical guidance.',
        },
    )
    PageSection.objects.get_or_create(
        page=home,
        key='sign-in-process',
        defaults={
            'title': 'Sign in and get started',
            'body': '',
            'content': SIGN_IN_PROCESS_CONTENT,
            'order': 2,
            'is_published': True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [('site_settings', '0011_generalize_advisor_page_copy')]

    operations = [
        migrations.RunPython(seed_sign_in_process, migrations.RunPython.noop),
    ]
