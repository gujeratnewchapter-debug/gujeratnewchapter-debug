from django.contrib import admin
from .models import Enrollment, LessonProgress, Bookmark

admin.site.register(Enrollment)
admin.site.register(LessonProgress)
admin.site.register(Bookmark)
