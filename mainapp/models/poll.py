from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from mainapp.models.teachers import Faculty, TEACHER_TYPE, Teacher, TeacherNGroup


class Question(models.Model):
    name = models.CharField('Название', max_length=20, primary_key=True)
    order = models.PositiveIntegerField('№', default=0, blank=False, null=False)

    question_text = models.TextField('Вопрос')
    answer_tip = models.TextField('Примечания', blank=True, null=True)

    answer_options = models.PositiveSmallIntegerField('1-5 или нет/да', choices=((5, '1-5'), (2, 'Нет/Да')), default=5)

    is_for_eng = models.BooleanField('для Англ', default=False)
    is_for_lec = models.BooleanField('для Лектора', default=False)
    is_for_pra = models.BooleanField('для Практика', default=False)
    is_two_answers = models.BooleanField('Разделять ответы для лектора и практика', default=False)

    @classmethod
    def get_by_type(cls, type_):
        query_by_type_ = {
            'ENG': Q(is_for_eng=True),
            'LECTOR': Q(is_for_lec=True),
            'PRACTIC': Q(is_for_pra=True),
            'LECTOR_PRACTIC': Q(is_for_lec=True) | Q(is_for_pra=True)
        }
        return cls.objects.filter(query_by_type_[type_])

    def __str__(self):
        return self.question_text[:100]

    def need_two_answers(self, teacher_type):
        return teacher_type == 'LECTOR_PRACTIC' and self.is_for_lec and self.is_for_pra and self.is_two_answers

    class Meta:
        ordering = ['order']
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"


class Result(models.Model):
    user_id = models.CharField('ID ответившего', max_length=32)
    teacher_n_group = models.ForeignKey(TeacherNGroup, models.CASCADE, verbose_name='Препод и группа')
    teacher_type = models.CharField('Тип опросника', max_length=20, null=True, choices=TEACHER_TYPE.items())

    open_question_answer = models.TextField('Ответ свободного микрофона', null=True, blank=True)
    open_answer_moderate = models.BooleanField('Комментарий допущен?', null=True)

    is_active = models.BooleanField("Актуальный результат", default=False,
                                    help_text="Последний законченный результат этого юзера по этому преподу")
    time_start = models.DateTimeField('Время начала прохождения', auto_now_add=True)
    time_finish = models.DateTimeField('Время окончания прохождения', null=True, default=None)

    def finish(self, teacher_type, open_question_answer, other_answers):
        with transaction.atomic():
            self.teacher_type = teacher_type
            self.open_question_answer = open_question_answer
            self.is_active = True
            self.time_finish = timezone.now()
            self.save()

            for question_id, answers in other_answers.items():
                if len(answers) == 1:
                    answers.append(None)
                ResultAnswers.objects.create(result=self, question_id=question_id,
                                             answer_1=answers[0], answer_2=answers[1])

    def __str__(self):
        return f"{self.teacher_n_group} {self.get_teacher_type_display()}"

    class Meta:
        verbose_name = "Результат опроса"
        verbose_name_plural = "Результаты опроса"


class ResultAnswers(models.Model):
    result = models.ForeignKey(Result, models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, models.CASCADE, verbose_name='Вопрос')
    answer_1 = models.PositiveSmallIntegerField('Ответ')
    answer_2 = models.PositiveSmallIntegerField('Еще ответ', null=True, blank=True)

    def get_answers(self):
        gen, prac = self.question.name, self.question.name + '_p'
        if self.result.teacher_type == 'PRACTIC' and self.question.is_two_answers:
            return {prac: self.answer_1}
        res = {gen: self.answer_1, prac: self.answer_2}
        return {k: v for k, v in res.items() if v is not None}  # filter None values

    def __str__(self):
        return ''

    class Meta:
        verbose_name = "Ответ на вопрос"
        verbose_name_plural = "Ответы на вопросы"


class TeacherFacultyResult(models.Model):
    teacher = models.ForeignKey(Teacher, models.CASCADE, verbose_name='Препод')
    faculty = models.ForeignKey(Faculty, models.CASCADE, verbose_name='Факультет')

    @classmethod
    def is_posted(cls, teacher, faculty):
        return cls.objects.filter(teacher=teacher, faculty=faculty).exist()

    @classmethod
    def get_results(cls, teacher, faculty):
        return Result.objects.filter(is_active=True, teacher_n_group__teacher=teacher,
                                     teacher_n_group__group__faculty=faculty).prefetch_related('answers__question')

    def __str__(self):
        return f"{self.teacher} в {self.faculty}"

    class Meta:
        unique_together = ('teacher', 'faculty')
