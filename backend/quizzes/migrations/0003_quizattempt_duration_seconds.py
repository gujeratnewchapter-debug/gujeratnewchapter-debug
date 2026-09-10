from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('quizzes', '0002_quiz_lesson_alter_quiz_max_attempts_and_more')]

    operations = [
        migrations.AddField(
            model_name='quizattempt',
            name='duration_seconds',
            field=models.PositiveIntegerField(default=0),
        ),
    ]