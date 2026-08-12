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

    def get_question_count(self, obj):
        return obj.questions.count()


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
        fields = ['id', 'quiz', 'started_at', 'submitted_at', 'score_percent', 'passed']
