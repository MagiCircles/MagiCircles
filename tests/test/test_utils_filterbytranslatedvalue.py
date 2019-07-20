# -*- coding: utf-8 -*-
from django.test import TestCase
from django.db.models.query import QuerySet
from magi.utils import (
    filterByTranslatedValue,
    FilterByMode,
)
from test import models

class FilterByTranslationTestCase(TestCase):
    def setUp(self):
        item = models.TranslatedNames.objects.create(
            name='abcdef',
            korean_name=u'ㄱㄴㄷㄹㅁㅂㅅㅇ',
        )
        item.add_d('names', 'ja', u'あいうえお')
        item.save()

        ambiguous_item = models.TranslatedNames.objects.create(
            name='hello world',
        )
        ambiguous_item.add_d('names', 'ja', u'nothing in common')
        ambiguous_item.add_d('names', 'ru', u'welcome to the world!')
        ambiguous_item.save()

        never_returned_item = models.TranslatedNames.objects.create(
            name='Passage weather as up am exposed.',
        )
        never_returned_item.add_d('names', 'ja', 'Vanity day giving points')
        never_returned_item.add_d('names', 'zh-hans', 'Position two saw greatest stronger old')
        never_returned_item.save()

        empty_item = models.TranslatedNames.objects.create()

        self.queryset = models.TranslatedNames.objects.all()

    def _toNameList(self, queryset):
        return [
            item.name
            for item in queryset
        ]

    def test_no_language_no_value(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
        )), ['abcdef', 'hello world', 'Passage weather as up am exposed.', ''])

    def test_english_exact(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='en',
            value='abcdef',
            mode=FilterByMode.Exact,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='en',
            value='abc',
            mode=FilterByMode.Exact,
        )), [])

    def test_english_contains(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='en',
            value='abc',
            mode=FilterByMode.Contains,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='en',
            value='lala',
            mode=FilterByMode.Contains,
        )), [])

    def test_english_starts_with(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='en',
            value='abc',
            mode=FilterByMode.StartsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='en',
            value='def',
            mode=FilterByMode.StartsWith,
        )), [])

    def test_english_ends_with(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='en',
            value='def',
            mode=FilterByMode.EndsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='en',
            value='abc',
            mode=FilterByMode.EndsWith,
        )), [])

    def test_language_in_own_field_exact(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㄱㄴㄷㄹㅁㅂㅅㅇ',
            mode=FilterByMode.Exact,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㄹㅁㅂㅅ',
            mode=FilterByMode.Exact,
        )), [])

    def test_language_in_own_field_contains(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㄹㅁㅂ',
            mode=FilterByMode.Contains,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value='lala',
            mode=FilterByMode.Contains,
        )), [])

    def test_language_in_own_field_starts_with(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㄱㄴㄷ',
            mode=FilterByMode.StartsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㅂㅅㅇ',
            mode=FilterByMode.StartsWith,
        )), [])

    def test_language_in_own_field_ends_with(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㅂㅅㅇ',
            mode=FilterByMode.EndsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㄱㄴㄷ',
            mode=FilterByMode.EndsWith,
        )), [])

    def test_Language_only(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ru',
        )), ['hello world'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='it',
        )), [])

    def test_exact_with_language_and_value(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'あいうえお',
            mode=FilterByMode.Exact,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'いえ',
            mode=FilterByMode.Exact,
        )), [])

    def test_exact_value_only(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'あいうえお',
            mode=FilterByMode.Exact,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'ㄱㄴㄷㄹㅁㅂㅅㅇ',
            mode=FilterByMode.Exact,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'abcdef',
            mode=FilterByMode.Exact,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'lala',
            mode=FilterByMode.Exact,
        )), [])

    def test_contains_with_language_and_value(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'いう',
            mode=FilterByMode.Contains,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㅁㅂ',
            mode=FilterByMode.Contains,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'lala',
            mode=FilterByMode.Contains,
        )), [])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ru',
            value=u'world',
            mode=FilterByMode.Contains,
        )), ['hello world'])

    def test_contains_value_only(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'いう',
            mode=FilterByMode.Contains,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'ㄹㅁ',
            mode=FilterByMode.Contains,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'bcd',
            mode=FilterByMode.Contains,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'lala',
            mode=FilterByMode.Contains,
        )), [])

    def test_contains_strict(self):
        # Without strict, returns value because it's in ru
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'world',
            mode=FilterByMode.Contains,
        )), ['hello world'])
        # With strict, will check and only return ja value
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'world',
            strict=True,
            mode=FilterByMode.Contains,
        )), [])

    def test_contains_strict_force_queryset(self):
        # Without force queryset, no result
        result = filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'world',
            strict=True,
            force_queryset=False,
            mode=FilterByMode.Contains,
        )
        self.assertEqual(
            (self._toNameList(result), isinstance(result, QuerySet)),
            ([], False),
        )
        # With force queryset, results
        result = filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'world',
            strict=True,
            force_queryset=True,
            mode=FilterByMode.Contains,
        )
        self.assertEqual(
            (self._toNameList(result), isinstance(result, QuerySet)),
            ([], True),
        )
        # Without force queryset, no result
        result = filterByTranslatedValue(
            self.queryset, 'name',
            language='ru',
            value=u'world',
            strict=True,
            force_queryset=False,
            mode=FilterByMode.Contains,
        )
        self.assertEqual(
            (self._toNameList(result), isinstance(result, QuerySet)),
            (['hello world'], False),
        )
        # With force queryset, results
        result = filterByTranslatedValue(
            self.queryset, 'name',
            language='ru',
            value=u'world',
            strict=True,
            force_queryset=True,
            mode=FilterByMode.Contains,
        )
        self.assertEqual(
            (self._toNameList(result), isinstance(result, QuerySet)),
            (['hello world'], True),
        )

    def test_starts_with_with_language_and_value(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'あい',
            mode=FilterByMode.StartsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㄱㄴ',
            mode=FilterByMode.StartsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'lala',
            mode=FilterByMode.StartsWith,
        )), [])

    def test_starts_with_value_only(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'あい',
            mode=FilterByMode.StartsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'ㄱㄴ',
            mode=FilterByMode.StartsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'えお',
            mode=FilterByMode.StartsWith,
        )), [])

    def test_ends_with_with_language_and_value(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'えお',
            mode=FilterByMode.EndsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='kr',
            value=u'ㅅㅇ',
            mode=FilterByMode.EndsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'あい',
            mode=FilterByMode.EndsWith,
        )), [])

    def test_ends_with_value_only(self):
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'えお',
            mode=FilterByMode.EndsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'ㅅㅇ',
            mode=FilterByMode.EndsWith,
        )), ['abcdef'])
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            value=u'あい',
            mode=FilterByMode.EndsWith,
        )), [])


    def test_endswith_strict(self):
        # Without strict, returns value because it's in ru
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'world!',
            mode=FilterByMode.EndsWith,
        )), ['hello world'])
        # With strict, will check and only return ja value
        self.assertEqual(self._toNameList(filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'world!',
            strict=True,
            mode=FilterByMode.EndsWith,
        )), [])

    def test_endswith_strict_force_queryset(self):
        # Without force queryset, no result
        result = filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'world!',
            strict=True,
            force_queryset=False,
            mode=FilterByMode.EndsWith,
        )
        self.assertEqual(
            (self._toNameList(result), isinstance(result, QuerySet)),
            ([], False),
        )
        # With force queryset, results
        result = filterByTranslatedValue(
            self.queryset, 'name',
            language='ja',
            value=u'world!',
            strict=True,
            force_queryset=True,
            mode=FilterByMode.EndsWith,
        )
        self.assertEqual(
            (self._toNameList(result), isinstance(result, QuerySet)),
            ([], True),
        )
        # Without force queryset, no result
        result = filterByTranslatedValue(
            self.queryset, 'name',
            language='ru',
            value=u'world!',
            strict=True,
            force_queryset=False,
            mode=FilterByMode.EndsWith,
        )
        self.assertEqual(
            (self._toNameList(result), isinstance(result, QuerySet)),
            (['hello world'], False),
        )
        # With force queryset, results
        result = filterByTranslatedValue(
            self.queryset, 'name',
            language='ru',
            value=u'world!',
            strict=True,
            force_queryset=True,
            mode=FilterByMode.EndsWith,
        )
        self.assertEqual(
            (self._toNameList(result), isinstance(result, QuerySet)),
            (['hello world'], True),
        )
