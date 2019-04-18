from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone
from magi import utils

class UtilsTestCase(TestCase):
    def test_getEventStatus(self):
        now = timezone.now()

        in_one_day = timezone.now() + relativedelta(days=1)
        in_one_week = timezone.now() + relativedelta(days=7)
        in_two_weeks = timezone.now() + relativedelta(days=14)

        one_day_ago = timezone.now() - relativedelta(days=1)
        one_week_ago = timezone.now() - relativedelta(days=7)
        two_weeks_ago = timezone.now() - relativedelta(days=14)

        self.assertEqual(utils.getEventStatus(
            None, None
        ), None)

        self.assertEqual(utils.getEventStatus(
            in_one_week, one_week_ago,
        ), 'invalid')

        self.assertEqual(utils.getEventStatus(
            in_one_week, in_two_weeks,
        ), 'future')

        self.assertEqual(utils.getEventStatus(
            in_one_week, in_two_weeks,
            ends_within=3, starts_within=3,
        ), 'future')

        self.assertEqual(utils.getEventStatus(
            in_one_day, in_one_week,
        ), 'future')

        self.assertEqual(utils.getEventStatus(
            in_one_day, in_one_week,
            ends_within=3, starts_within=3,
        ), 'starts_soon')

        self.assertEqual(utils.getEventStatus(
            one_week_ago, in_one_week,
        ), 'current')

        self.assertEqual(utils.getEventStatus(
            one_week_ago, one_day_ago,
        ), 'ended')

        self.assertEqual(utils.getEventStatus(
            two_weeks_ago, one_day_ago,
            ends_within=3, starts_within=3,
        ), 'ended_recently')

        self.assertEqual(utils.getEventStatus(
            two_weeks_ago, one_week_ago,
        ), 'ended')
