# -*- coding: utf-8 -*-
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _, get_language, activate as activate_language
from test import models

class ItemModelDict(TestCase):
    def setUp(self):
        self.item = models.TranslatedNames(name='Maria')

    def test_empty(self):
        self.assertEqual(self.item.names, {})
        self.assertEqual(self.item.colors, {})
        self.assertEqual(self.item.items, {})

    def test_save_d(self):
        self.item.save_d('names', {'ja': u'マリア', 'ru': u'Мария'})
        self.assertEqual(self.item.names, {'ja': u'マリア', 'ru': u'Мария'})

    def test_save_empty(self):
        self.item.save_d('names', None)
        self.assertEqual(self.item.d_names, None)
        self.assertEqual(self.item.names, {})
        self.item.save_d('names', {})
        self.assertEqual(self.item.d_names, None)
        self.assertEqual(self.item.names, {})

    def test_add_d(self):
        self.item.save_d('names', None)
        self.item.add_d('names', 'ja', u'マリア')
        self.assertEqual(self.item.names, {'ja': u'マリア'})
        self.item.add_d('names', 'ru', u'Мария')
        self.assertEqual(self.item.names, {'ja': u'マリア', 'ru': u'Мария'})

    def test_remove_d(self):
        self.item.save_d('names', {'ja': u'マリア', 'ru': u'Мария'})
        self.item.remove_d('names', 'ja')
        self.assertEqual(self.item.names, {'ru': u'Мария'})
        self.item.remove_d('names', 'ru')
        self.assertEqual(self.item.d_names, None)
        self.assertEqual(self.item.names, {})

    def test_t_something(self):
        self.item.save_d('names', {'ja': u'マリア', 'ru': u'Мария'})
        self.assertEqual(self.item.t_names, {
            'ja': {
                'value': u'マリア',
                'verbose': _('Japanese'),
            },
            'ru': {
                'value': u'Мария',
                'verbose': _('Russian'),
            },
        })
        self.item.save_d('colors', {'blue': 'something', 'green': 'something else'})
        self.assertEqual(self.item.t_colors, {
            'blue': {
                'value': 'something',
                'verbose': 'blue',
            },
            'green': {
                'value': 'something else',
                'verbose': 'green',
            },
        })
        self.item.save_d('items', {'gem': 5, 'coins': 3, 'bought': True})
        self.assertEqual(self.item.t_items, {
            'gem': {
                'value': 5,
                'verbose': 'gem',
            },
            'coins': {
                'value': 3,
                'verbose': 'coins',
            },
            'bought': {
                'value': True,
                'verbose': 'bought',
            },
        })

    def test_t_something_single(self):
        old_lang = get_language()
        self.item.save_d('names', {'ja': u'マリア', 'ru': u'Мария'})
        activate_language('ja')
        self.assertEqual(self.item.t_name, u'マリア')
        activate_language('ru')
        self.assertEqual(self.item.t_name, u'Мария')
        activate_language('zh-hans')
        self.assertEqual(self.item.t_name, u'Maria')
        activate_language('en')
        self.assertEqual(self.item.t_name, u'Maria')
        activate_language(old_lang)
