from unittest.mock import patch

from django.core import mail
from freezegun import freeze_time
from mixer.backend.django import mixer

from elk.utils.testing import ClassIntegrationTestCase, create_customer, create_teacher
from market.models import Subscription
from timeline.tasks import notify_15min_to_class
from timeline.tasks import notify_study_sometimes


class TestStartingSoonEmail(ClassIntegrationTestCase):
    @patch('market.signals.Owl')
    def test_single_class_pre_start_notification(self, Owl):
        entry = self._create_entry()
        c = self._buy_a_lesson()
        self._schedule(c, entry)

        with freeze_time('2032-09-13 15:46'):   # entry will start in 14 minutes
            for i in range(0, 10):  # run this 10 times to check for repietive emails — all notifications should be sent one time
                notify_15min_to_class()

        self.assertEqual(len(mail.outbox), 2)  # if this test fails, carefully check the timezone you are in

        out_emails = [outbox.to[0] for outbox in mail.outbox]

        self.assertIn(self.host.user.email, out_emails)
        self.assertIn(self.customer.user.email, out_emails)

    @patch('market.signals.Owl')
    def test_two_classes_pre_start_notification(self, Owl):
        self.lesson = mixer.blend('lessons.MasterClass', host=self.host, slots=5)

        other_customer = create_customer()
        first_customer = self.customer

        entry = self._create_entry()
        entry.slots = 5
        entry.save()

        c = self._buy_a_lesson()
        self._schedule(c, entry)

        self.customer = other_customer
        c1 = self._buy_a_lesson()
        self._schedule(c1, entry)
        with freeze_time('2032-09-13 15:46'):   # entry will start in 14 minutes
            for i in range(0, 10):  # run this 10 times to check for repietive emails — all notifications should be sent one time
                notify_15min_to_class()

        self.assertEqual(len(mail.outbox), 3)  # if this test fails, carefully check the timezone you are in

        out_emails = [outbox.to[0] for outbox in mail.outbox]

        self.assertIn(self.host.user.email, out_emails)
        self.assertIn(first_customer.user.email, out_emails)
        self.assertIn(other_customer.user.email, out_emails)


class TestReminderEmail(ClassIntegrationTestCase):
    @staticmethod
    def _buy_a_subscription(customer, is_used):
        subscription = Subscription(
            buy_price_currency='USD',
            customer=customer,
            buy_price=60,
            product_id=1,
            product_type_id=13,
            is_fully_used=is_used,
        )
        subscription.save()
        return subscription

    @patch('market.signals.Owl')
    def test_one_customer_reminder(self, Owl):
        entry = self._create_entry()
        c = self._buy_a_lesson()
        self._schedule(c, entry)
        subscription = self._buy_a_subscription(c.customer, False)
        c.subscription = subscription
        c.save()
        with freeze_time('2032-09-21 20:00'):   # 2032-09-13 entry starts, send remind
            notify_study_sometimes()

        self.assertEqual(len(mail.outbox), 1)

        out_emails = [outbox.to[0] for outbox in mail.outbox]
        self.assertIn(c.customer.user.email, out_emails)

    @patch('market.signals.Owl')
    def test_one_good_study_not_remind(self, Owl):
        entry = self._create_entry()
        c = self._buy_a_lesson()
        self._schedule(c, entry)
        subscription = self._buy_a_subscription(c.customer, False)
        c.subscription = subscription
        c.save()
        with freeze_time('2032-09-15 20:00'):   # 2032-09-13 entry starts, not send remind
            notify_study_sometimes()

        self.assertEqual(len(mail.outbox), 0)

        out_emails = [outbox.to[0] for outbox in mail.outbox]
        self.assertNotIn(c.customer.user.email, out_emails)

    @patch('market.signals.Owl')
    def test_one_used_not_remind(self, Owl):
        entry = self._create_entry()
        c = self._buy_a_lesson()
        self._schedule(c, entry)
        subscription = self._buy_a_subscription(c.customer, True)
        c.subscription = subscription
        c.save()
        with freeze_time('2032-09-22 20:00'):   # 2032-09-13 entry starts, not send remind, subscribe is_fully_used
            notify_study_sometimes()

        self.assertEqual(len(mail.outbox), 0)

        out_emails = [outbox.to[0] for outbox in mail.outbox]
        self.assertNotIn(c.customer.user.email, out_emails)

    @patch('market.signals.Owl')
    def test_two_customer_reminder(self, Owl):
        self.lesson = mixer.blend('lessons.MasterClass', host=self.host, slots=5)

        other_customer = create_customer()

        entry = self._create_entry()
        entry.slots = 5
        entry.save()

        c = self._buy_a_lesson()
        self._schedule(c, entry)
        subscription_c = self._buy_a_subscription(c.customer, False)
        c.subscription = subscription_c
        c.save()

        self.customer = other_customer
        c1 = self._buy_a_lesson()
        self._schedule(c1, entry)
        subscription_c1 = self._buy_a_subscription(c1.customer, False)
        c1.subscription = subscription_c1
        c1.save()

        with freeze_time('2032-09-21 20:00'):   # 2032-09-13 entry starts, send remind for 2 students
            notify_study_sometimes()

        self.assertEqual(len(mail.outbox), 2)

        out_emails = [outbox.to[0] for outbox in mail.outbox]
        self.assertIn(c1.customer.user.email, out_emails)
        self.assertIn(c.customer.user.email, out_emails)

    @patch('market.signals.Owl')
    def test_two_subscribe_one_reminder(self, Owl):
        self.lesson = mixer.blend('lessons.MasterClass', host=self.host, slots=5)

        entry = self._create_entry()
        entry.slots = 5
        entry.save()

        self.host = create_teacher()
        self.lesson.host = self.host
        entry1 = self._create_entry()
        entry1.slots = 5
        entry1.save()

        c = self._buy_a_lesson()
        self._schedule(c, entry)

        c1 = self._buy_a_lesson()
        self._schedule(c1, entry)

        subscription_c = self._buy_a_subscription(c.customer, False)
        c.subscription = subscription_c
        c.save()

        subscription_c1 = self._buy_a_subscription(c1.customer, False)
        c1.subscription = subscription_c1
        c1.save()

        with freeze_time('2032-09-21 20:00'):   # 2032-09-13 entry starts, send one remind for 1 student, 2 subscribe
            notify_study_sometimes()

        self.assertEqual(len(mail.outbox), 1)

        out_emails = [outbox.to[0] for outbox in mail.outbox]
        self.assertIn(c1.customer.user.email, out_emails)
        self.assertIn(c.customer.user.email, out_emails)
