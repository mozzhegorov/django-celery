from datetime import timedelta
from datetime import datetime
from datetime import timezone
from django.db.models import Max

from elk.celery import app as celery
from mailer.owl import Owl
from market.models import Class
from crm.models import Customer
from timeline.signals import class_starting_student, class_starting_teacher


@celery.task
def notify_15min_to_class():
    for i in Class.objects.starting_soon(timedelta(minutes=30)).filter(pre_start_notifications_sent_to_teacher=False).distinct('timeline'):
        for other_class_with_the_same_timeline in Class.objects.starting_soon(timedelta(minutes=30)).filter(timeline=i.timeline):
            """
            Set all other starting classes as notified either.
            """
            other_class_with_the_same_timeline.pre_start_notifications_sent_to_teacher = True
            other_class_with_the_same_timeline.save()
        class_starting_teacher.send(sender=notify_15min_to_class, instance=i)

    for i in Class.objects.starting_soon(timedelta(minutes=30)).filter(pre_start_notifications_sent_to_student=False):
        i.pre_start_notifications_sent_to_student = True
        i.save()
        class_starting_student.send(sender=notify_15min_to_class, instance=i)


@celery.task
def notify_study_sometimes():
    customers_with_emails = []
    last_week = datetime.now(timezone.utc) - timedelta(days=7)
    customers_weeked_lessons = Class.objects. \
        values('customer_id', 'subscription'). \
        annotate(
            timeline_max=Max('timeline__start'),
        ). \
        filter(
            subscription__is_fully_used=False,
            timeline_max__lt=last_week,
        )
    """
    See all customers who have not lessons on open subscribes last 7 days 
    """
    for market_class in customers_weeked_lessons:
        customer_id = market_class['customer_id']
        if customer_id not in customers_with_emails:
            customers_with_emails.append(customer_id)
            customer = Customer.objects.get(id=customer_id)
            owl = Owl(
                template='mail/reminder_for_inactive_students.html',
                ctx={
                    'c': customer,
                },
                to=[customer.user.email],
                timezone=customer.user.crm.timezone,
            )
            owl.send()
