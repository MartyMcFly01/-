from collections import defaultdict

from django.contrib import admin
from django.http import HttpResponse

from .models import Locale, Question, Teacher, Result, ResultAnswers, Group, TeacherNGroup, Faculty


@admin.register(Locale)
class LocaleAdmin(admin.ModelAdmin):
    empty_value_display = 'Не заполнено'
    list_display = ('key', 'value')
    list_editable = ('value', )


#

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    def export(self, request, queryset):
        fac2group = defaultdict(list)
        for group in queryset:
            fac2group[group.faculty.name].append(group)
        text = "\n".join([
            f"{fac: ^30}\n" + '\n'.join([
                f"{group.name: <20} {group.link()}"
                for group in groups
            ])
            for fac, groups in fac2group.items()
        ])
        return HttpResponse(f"<pre>{text}</pre>")

    class TeacherInline(admin.TabularInline):
        model = TeacherNGroup
        extra = 1

    list_display = ('name', 'faculty', 'link')
    list_filter = ('faculty', )
    search_fields = ('name', )
    actions = ('export', )
    inlines = [
        TeacherInline,
    ]


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    def faculties(self, obj):
        return list(Faculty.objects.filter(group__teachers__id=obj.id).distinct())

    list_display = ('name', 'faculties')



@admin.register(TeacherNGroup)
class TeacherNGroupAdmin(admin.ModelAdmin):
    def faculty(self, obj):
        return obj.group.faculty

    list_display = ('teacher', 'group', 'faculty', 'link')
#

#


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'answer_tip', 'is_for_eng', 'is_for_lec', 'is_for_pra', 'is_two_answers')
    list_editable = ('answer_tip', )


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    class AnswerInline(admin.TabularInline):
        model = ResultAnswers
        extra = 0

    def teacher(self, obj):
        return obj.teacher_n_group.teacher

    def group(self, obj):
        return obj.teacher_n_group.group

    list_display = ('user_id', 'teacher', 'group', 'teacher_type')
    raw_id_fields = ('teacher_n_group', )
    inlines = [
        AnswerInline,
    ]
