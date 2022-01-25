# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone
from django.utils.safestring import mark_safe
from magi import utils

class UtilsTestCase(TestCase):
    def test_getAstrologicalSign(self):
        self.assertEqual(utils.getAstrologicalSign(11, 26), 'sagittarius')
        self.assertEqual(utils.getAstrologicalSign(6, 28), 'cancer')
        self.assertEqual(utils.getAstrologicalSign(6, 1), 'gemini')
        self.assertEqual(utils.getAstrologicalSign(10, 17), 'libra')
        self.assertEqual(utils.getAstrologicalSign(3, 16), 'pisces')
        self.assertEqual(utils.getAstrologicalSign(6, 3), 'gemini')
        self.assertEqual(utils.getAstrologicalSign(6, 23), 'cancer')
        self.assertEqual(utils.getAstrologicalSign(9, 29), 'libra')
        self.assertEqual(utils.getAstrologicalSign(3, 30), 'aries')
        self.assertEqual(utils.getAstrologicalSign(4, 30), 'taurus')
        self.assertEqual(utils.getAstrologicalSign(5, 15), 'taurus')
        self.assertEqual(utils.getAstrologicalSign(7, 22), 'cancer')
        self.assertEqual(utils.getAstrologicalSign(9, 8), 'virgo')
        self.assertEqual(utils.getAstrologicalSign(4, 3), 'aries')
        self.assertEqual(utils.getAstrologicalSign(11, 30), 'sagittarius')
        self.assertEqual(utils.getAstrologicalSign(2, 27), 'pisces')
        self.assertEqual(utils.getAstrologicalSign(3, 5), 'pisces')
        self.assertEqual(utils.getAstrologicalSign(7, 5), 'cancer')
        self.assertEqual(utils.getAstrologicalSign(8, 17), 'leo')
        self.assertEqual(utils.getAstrologicalSign(2, 20), 'pisces')
        self.assertEqual(utils.getAstrologicalSign(5, 22), 'gemini')
        self.assertEqual(utils.getAstrologicalSign(12, 23), 'capricorn')
        self.assertEqual(utils.getAstrologicalSign(10, 15), 'libra')
        self.assertEqual(utils.getAstrologicalSign(11, 15), 'scorpio')
        self.assertEqual(utils.getAstrologicalSign(12, 22), 'capricorn')
        self.assertEqual(utils.getAstrologicalSign(1, 8), 'capricorn')
        self.assertEqual(utils.getAstrologicalSign(1, 14), 'capricorn')
        self.assertEqual(utils.getAstrologicalSign(2, 3), 'aquarius')
        self.assertEqual(utils.getAstrologicalSign(2, 15), 'aquarius')
        self.assertEqual(utils.getAstrologicalSign(3, 3), 'pisces')
        self.assertEqual(utils.getAstrologicalSign(3, 19), 'pisces')
        self.assertEqual(utils.getAstrologicalSign(4, 5), 'aries')
        self.assertEqual(utils.getAstrologicalSign(4, 17), 'aries')
        self.assertEqual(utils.getAstrologicalSign(5, 4), 'taurus')
        self.assertEqual(utils.getAstrologicalSign(5, 29), 'gemini')
        self.assertEqual(utils.getAstrologicalSign(6, 5), 'gemini')
        self.assertEqual(utils.getAstrologicalSign(6, 21), 'cancer')
        self.assertEqual(utils.getAstrologicalSign(7, 12), 'cancer')
        self.assertEqual(utils.getAstrologicalSign(7, 24), 'leo')
        self.assertEqual(utils.getAstrologicalSign(8, 1), 'leo')
        self.assertEqual(utils.getAstrologicalSign(8, 16), 'leo')
        self.assertEqual(utils.getAstrologicalSign(9, 11), 'virgo')
        self.assertEqual(utils.getAstrologicalSign(9, 27), 'libra')
        self.assertEqual(utils.getAstrologicalSign(10, 1), 'libra')
        self.assertEqual(utils.getAstrologicalSign(10, 10), 'libra')
        self.assertEqual(utils.getAstrologicalSign(11, 9), 'scorpio')
        self.assertEqual(utils.getAstrologicalSign(11, 20), 'scorpio')
        self.assertEqual(utils.getAstrologicalSign(12, 2), 'sagittarius')
        self.assertEqual(utils.getAstrologicalSign(12, 14), 'sagittarius')

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

    def test_markSafeJoin(self):
        self.assertEqual(unicode(utils.markSafeJoin([
            mark_safe('<b>hello</b>'),
            utils.markSafeFormat('<b>{}</b>', 'world'),
            '<b>unsafe</b>',
        ], separator=' test ')), u'<b>hello</b> test <b>world</b> test &lt;b&gt;unsafe&lt;/b&gt;')

    def test_andJoin(self):
        self.assertEqual(unicode(utils.andJoin([
            '<b>hello</b>',
        ])), u'<b>hello</b>')
        self.assertEqual(unicode(utils.andJoin([
            '<b>hello</b>',
        ], mark_safe=True)), u'&lt;b&gt;hello&lt;/b&gt;')
        self.assertEqual(unicode(utils.andJoin([
            '<b>hello</b>',
            mark_safe('<b>world</b>'),
        ])), u'<b>hello</b> and <b>world</b>')
        self.assertEqual(unicode(utils.andJoin([
            '<b>hello</b>',
            mark_safe('<b>world</b>'),
        ], mark_safe=True)), u'&lt;b&gt;hello&lt;/b&gt; and <b>world</b>')
        self.assertEqual(unicode(utils.andJoin([
            '<b>hello</b>',
            '<b>world</b>',
            mark_safe('<b>foo</b>'),
        ])), u'<b>hello</b>, <b>world</b> and <b>foo</b>')
        self.assertEqual(unicode(utils.andJoin([
            '<b>hello</b>',
            '<b>world</b>',
            mark_safe('<b>foo</b>'),
        ], mark_safe=True)), u'&lt;b&gt;hello&lt;/b&gt;, &lt;b&gt;world&lt;/b&gt; and <b>foo</b>')

        # Other language
        utils.translation_activate('ja')
        self.assertEqual(unicode(utils.andJoin([
            u'<b>こんにちは</b>',
        ])), u'<b>こんにちは</b>')
        self.assertEqual(unicode(utils.andJoin([
            u'<b>こんにちは</b>',
        ], mark_safe=True)), u'&lt;b&gt;こんにちは&lt;/b&gt;')
        self.assertEqual(unicode(utils.andJoin([
            u'<b>こんにちは</b>',
            mark_safe(u'<b>世界</b>'),
        ])), u'<b>こんにちは</b> と <b>世界</b>')
        self.assertEqual(unicode(utils.andJoin([
            u'<b>こんにちは</b>',
            mark_safe(u'<b>世界</b>'),
        ], mark_safe=True)), u'&lt;b&gt;こんにちは&lt;/b&gt; と <b>世界</b>')
        self.assertEqual(unicode(utils.andJoin([
            u'<b>こんにちは</b>',
            u'<b>世界</b>',
            mark_safe(u'<b>フー</b>'),
        ])), u'<b>こんにちは</b>、<b>世界</b> と <b>フー</b>')
        self.assertEqual(unicode(utils.andJoin([
            u'<b>こんにちは</b>',
            u'<b>世界</b>',
            mark_safe(u'<b>フー</b>'),
        ], mark_safe=True)), u'&lt;b&gt;こんにちは&lt;/b&gt;、&lt;b&gt;世界&lt;/b&gt; と <b>フー</b>')
        self.assertEqual(unicode(utils.andJoin([
            u'<b>こんにちは</b>',
            u'<b>世界</b>',
            mark_safe(u'<b>フー</b>'),
        ], mark_safe=True, translated=False)), u'&lt;b&gt;こんにちは&lt;/b&gt;, &lt;b&gt;世界&lt;/b&gt; and <b>フー</b>')
