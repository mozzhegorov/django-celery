from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.shortcuts import get_list_or_404, get_object_or_404, render
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from timeline.forms import EntryForm as TimelineEntryForm
from timeline.models import Entry as TimelineEntry


@login_required
def calendar(request, username):
    return render(request, 'calendar/user.html', context={
        'object': get_object_or_404(User, username=username)
    })


class calendar_create(CreateView):
    template_name = 'forms/entry.html'
    form_class = TimelineEntryForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = get_object_or_404(User, username=self.kwargs['username'])
        return context

    def get_success_url(self):
        return reverse('timeline:timeline', kwargs=self.kwargs)


@login_required
def calendar_json(request, username):
    user = get_object_or_404(User, username=username)
    entries = []
    start = request.GET.get('start', '1970-01-01')  # TODO set more convienient default values, i.e. last month
    end = request.GET.get('end', '2100-01-01')

    for entry in get_list_or_404(TimelineEntry,
                                 start_time__range=(start, end),
                                 teacher=user
                                 ):
        entries.append(entry.as_dict())

    return JsonResponse(entries, safe=False)


@login_required
def available_lessons_json(request, username):
    lesson_id = request.GET.get('lesson_id')

    Model = ContentType.objects.get(app_label='lessons', pk=lesson_id).model_class()

    lessons = []
    for lesson in get_list_or_404(Model):
        lessons.append(lesson.as_dict())

    return JsonResponse(lessons, safe=False)
