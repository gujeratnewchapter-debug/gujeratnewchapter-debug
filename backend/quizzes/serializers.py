from rest_framework import serializers
from .models import Quiz, Question, Choice, QuizAttempt, Answer


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order']  # is_correct hidden from students


class ChoiceWithAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order', 'is_correct']  # for instructors


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'order', 'points', 'choices']


class QuestionInstructorSerializer(serializers.ModelSerializer):
    """Same as QuestionSerializer but reveals is_correct — for the instructor
    course-builder view only, never served to students taking the quiz."""
    choices = ChoiceWithAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'quiz', 'text', 'question_type', 'order', 'points', 'correct_text_answer', 'choices']


class QuestionWriteSerializer(serializers.ModelSerializer):
    """Instructor create/update for a single question (course-builder 'add question' step)."""
    class Meta:
        model = Question
        fields = ['id', 'quiz', 'text', 'question_type', 'order', 'points', 'correct_text_answer']


class ChoiceWriteSerializer(serializers.ModelSerializer):
    """Instructor create/update for a single answer choice, including is_correct."""
    class Meta:
        model = Choice
        fields = ['id', 'question', 'text', 'is_correct', 'order']


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'course', 'section', 'lesson', 'title', 'is_final_exam', 'time_limit_minutes',
            'passing_score_percent', 'randomize_questions', 'max_attempts', 'questions',
            'question_count',
        ]

    def validate(self, attrs):
        course = attrs.get('course', getattr(self.instance, 'course', None))
        section = attrs.get('section', getattr(self.instance, 'section', None))
        lesson = attrs.get('lesson', getattr(self.instance, 'lesson', None))
        if section and section.course_id != course.id:
            raise serializers.ValidationError({'section': 'The section must belong to the selected course.'})
        if lesson and lesson.section.course_id != course.id:
            raise serializers.ValidationError({'lesson': 'The lesson must belong to the selected course.'})
        if section and lesson and lesson.section_id != section.id:
            raise serializers.ValidationError({'lesson': 'The lesson must belong to the selected section.'})
        return attrs

    def get_question_count(self, obj):
        return obj.questions.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.is_authenticated and (user.is_instructor or user.is_super_admin):
            return data

        accessible = bool(instance.lesson_id and instance.lesson.is_preview)
        if user and user.is_authenticated:
            from enrollments.models import Enrollment, LessonProgress, is_lesson_unlocked
            enrollment = Enrollment.objects.filter(
                student=user, course=instance.course,
            ).first()
            if enrollment:
                if instance.lesson_id:
                    accessible = is_lesson_unlocked(user, instance.lesson)
                elif instance.is_final_exam:
                    required_lessons = instance.section.lessons.all() if instance.section_id else instance.course.sections.values_list('lessons__id', flat=True)
                    required_ids = [lesson.id for lesson in required_lessons] if instance.section_id else list(required_lessons)
                    completed_ids = set(LessonProgress.objects.filter(
                        enrollment=enrollment, lesson_id__in=required_ids, is_completed=True,
                    ).values_list('lesson_id', flat=True))
                    accessible = bool(required_ids) and set(required_ids).issubset(completed_ids)

        if not accessible:
            data['questions'] = []
            data['question_count'] = 0
        return data


class QuizInstructorSerializer(QuizSerializer):
    """Instructor/admin view of a quiz while editing it in the course builder —
    reveals which choice is marked correct on every question."""
    questions = QuestionInstructorSerializer(many=True, read_only=True)


class AnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_choice_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    text_answer = serializers.CharField(required=False, allow_blank=True, default='')


class QuizSubmitSerializer(serializers.Serializer):
    answers = AnswerSubmitSerializer(many=True)


class QuizAttemptResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz', 'started_at', 'submitted_at', 'score_percent', 'passed', 'duration_seconds']
