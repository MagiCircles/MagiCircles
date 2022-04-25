from collections import OrderedDict
from django.test import TestCase
from django.utils.translation import gettext_lazy as _
from magi.item_model import i_choices
from test import models

class IChoicesTestModelTestCase(TestCase):
    def setUp(self):
        self.attribute_i = models.IChoicesTest.get_i('attribute', 'pure')
        self.power_i = 1 # It's not possible to use get_i when using translated values
        self.super_power_i = models.IChoicesTest.get_i('super_power', 'rock')
        self.rarity_i = models.IChoicesTest.get_i('rarity', 'N')
        self.language_i = 'it'
        self.notification_i = models.IChoicesTest.get_i('notification', 'follow')
        self.play_with_i = None

        self.ichoices_test = models.IChoicesTest.objects.create(
            i_attribute=self.attribute_i,
            i_power=self.power_i,
            i_super_power=self.super_power_i,
            i_rarity=self.rarity_i,
            i_language=self.language_i,
            i_notification=self.notification_i,
            i_play_with=self.play_with_i,
        )

    def test_i_choices(self):
        self.assertEqual(i_choices(models.IChoicesTest.ATTRIBUTE_CHOICES), [
            (0, 'smile'),
            (1, 'pure'),
            (2, 'cool'),
        ])
        self.assertEqual(i_choices(models.IChoicesTest.POWER_CHOICES), [
            (0, _('Happy')),
            (1, _('Cool')),
            (2, _('Rock')),
        ])
        self.assertEqual(i_choices(models.IChoicesTest.SUPER_POWER_CHOICES), [
            (0,  _('Happy')),
            (1, _('Cool')),
            (2, _('Rock')),
        ])
        self.assertEqual(i_choices(models.IChoicesTest.NOTIFICATION_CHOICES), [
            (0, _('When someone likes your activity.')),
            (1, _('When someone follows you.')),
        ])
        self.assertEqual(i_choices(models.IChoicesTest.PLAY_WITH_CHOICES), [
            (0, _('Thumbs')),
            (1, _('All fingers')),
            (2, _('Index fingers')),
            (3, _('One hand')),
            (4,  _('Other')),
        ])

    # Class methods

    def test_get_choices(self):
        self.assertEqual(models.IChoicesTest.get_choices('attribute'), [
            (0, 'smile'),
            (1, 'pure'),
            (2, 'cool'),
        ])
        self.assertEqual(models.IChoicesTest.get_choices('power'), [
            (0, _('Happy')),
            (1, _('Cool')),
            (2, _('Rock')),
        ])
        self.assertEqual(models.IChoicesTest.get_choices('super_power'), [
            (0, ('happy', _('Happy'))),
            (1, ('cool', _('Cool'))),
            (2, ('rock', _('Rock'))),
        ])
        self.assertEqual(models.IChoicesTest.get_choices('rarity'), [
            (0, 'N'),
            (1, 'R'),
            (2, 'SR'),
        ])
        self.assertEqual(models.IChoicesTest.get_choices('language'), [
            ('en', ('en', _('English'))),
            ('es', ('es', _('Spanish'))),
            ('ru', ('ru', _('Russian'))),
            ('it', ('it', _('Italian'))),
        ])
        self.assertEqual(models.IChoicesTest.get_choices('notification'), [
            (0, ('like', _('When someone likes your activity.'))),
            (1, ('follow', _('When someone follows you.'))),
        ])
        self.assertEqual(models.IChoicesTest.get_choices('play_with'), [
            (0, ('Thumbs', _('Thumbs'))),
            (1, ('Fingers', _('All fingers'))),
            (2, ('Index', _('Index fingers'))),
            (3, ('Hand', _('One hand'))),
            (4,  ('Other', _('Other'))),
        ])

    def test_get_i(self):
        self.assertEqual(self.attribute_i, 1)
        self.assertEqual(self.power_i, 1)
        self.assertEqual(self.super_power_i, 2)
        self.assertEqual(self.rarity_i, 0)
        self.assertEqual(self.language_i, 'it')
        self.assertEqual(self.notification_i, 1)
        self.assertEqual(self.play_with_i, None)

    def test_get_reverse_i(self):
        self.assertEqual(models.IChoicesTest.get_reverse_i('attribute', 2), 'cool')
        self.assertEqual(models.IChoicesTest.get_reverse_i('power', 1), _('Cool'))
        self.assertEqual(models.IChoicesTest.get_reverse_i('super_power', 0), 'happy')
        self.assertEqual(models.IChoicesTest.get_reverse_i('rarity', 0), 'N')
        self.assertEqual(models.IChoicesTest.get_reverse_i('language', 'ru'), 'ru')
        self.assertEqual(models.IChoicesTest.get_reverse_i('notification', 1), 'follow')
        self.assertEqual(models.IChoicesTest.get_reverse_i('play_with', None), None)

    def test_get_verbose_i(self):
        self.assertEqual(models.IChoicesTest.get_verbose_i('attribute', 2), 'cool')
        self.assertEqual(models.IChoicesTest.get_verbose_i('power', 1), _('Cool'))
        self.assertEqual(models.IChoicesTest.get_verbose_i('super_power', 0), _('Happy'))
        self.assertEqual(models.IChoicesTest.get_verbose_i('rarity', 0), 'N')
        self.assertEqual(models.IChoicesTest.get_verbose_i('language', 'ru'), _('Russian'))
        self.assertEqual(models.IChoicesTest.get_verbose_i('notification', 1), _('When someone follows you.'))
        self.assertEqual(models.IChoicesTest.get_verbose_i('play_with', None), None)

    # Instance properties

    def test_i_something(self):
        self.assertEqual(self.ichoices_test.i_attribute, self.attribute_i)
        self.assertEqual(self.ichoices_test.i_power, self.power_i)
        self.assertEqual(self.ichoices_test.i_super_power, self.super_power_i)
        self.assertEqual(self.ichoices_test.i_rarity, self.rarity_i)
        self.assertEqual(self.ichoices_test.i_language, self.language_i)
        self.assertEqual(self.ichoices_test.i_notification, self.notification_i)
        self.assertEqual(self.ichoices_test.i_play_with, self.play_with_i)

    def test_something(self):
        self.assertEqual(self.ichoices_test.attribute, 'pure')
        self.assertEqual(self.ichoices_test.power, _('Cool'))
        self.assertEqual(self.ichoices_test.super_power, 'rock')
        self.assertEqual(self.ichoices_test.rarity, 'N')
        self.assertEqual(self.ichoices_test.language, 'it')
        self.assertEqual(self.ichoices_test.notification, 'follow')
        self.assertEqual(self.ichoices_test.play_with, None)

    def test_t_something(self):
        self.assertEqual(self.ichoices_test.t_attribute, 'pure')
        self.assertEqual(self.ichoices_test.t_power, _('Cool'))
        self.assertEqual(self.ichoices_test.t_super_power, _('Rock'))
        self.assertEqual(self.ichoices_test.t_rarity, 'N')
        self.assertEqual(self.ichoices_test.t_language, _('Italian'))
        self.assertEqual(self.ichoices_test.t_notification, _('When someone follows you.'))
        self.assertEqual(self.ichoices_test.t_play_with, None)

    # Instance methods

    def test_notification_icon(self):
        self.assertEqual(self.ichoices_test.notification_icon, 'users')
        self.ichoices_test.i_notification = models.IChoicesTest.get_i('notification', 'like')
        self.assertEqual(self.ichoices_test.notification_icon, 'heart')

class CCSVTestModelTestCase(TestCase):
    def setUp(self):
        self.ccsv_test = models.CCSVTest()

    def test_empty(self):
        self.assertEqual(self.ccsv_test.data, [])
        self.assertEqual(self.ccsv_test.abilities, [])
        self.assertEqual(self.ccsv_test.tags, [])

    # data
    # Without choices restriction

    def test_data_save_c(self):
        self.ccsv_test.save_c('data', ['hello', 'world'])
        self.assertEqual(self.ccsv_test.c_data, '"hello","world"')
        self.assertEqual(self.ccsv_test.data, ['hello', 'world'])
        self.assertEqual(self.ccsv_test.t_data, OrderedDict([
            ('hello', 'hello'),
            ('world', 'world'),
        ]))

    def test_data_add_c(self):
        self.ccsv_test.save_c('data', ['hello', 'world'])
        self.ccsv_test.add_c('data', ['boo'])
        self.assertEqual(self.ccsv_test.c_data, '"hello","world","boo"')
        self.assertEqual(self.ccsv_test.data, ['hello', 'world', 'boo'])
        self.assertEqual(self.ccsv_test.t_data, OrderedDict([
            ('hello', 'hello'),
            ('world', 'world'),
            ('boo', 'boo'),
        ]))

    def test_data_remove_c(self):
        self.ccsv_test.save_c('data', ['hello', 'boo', 'world'])
        self.ccsv_test.remove_c('data', ['boo'])
        self.assertEqual(self.ccsv_test.c_data, '"hello","world"')
        self.assertEqual(self.ccsv_test.data, ['hello', 'world'])
        self.assertEqual(self.ccsv_test.t_data, OrderedDict([
            ('hello', 'hello'),
            ('world', 'world'),
        ]))

    # Abilities
    # With choices restrictions with translations

    def test_abilities_save_c(self):
        self.ccsv_test.save_c('abilities', ['fly', 'sing'])
        self.assertEqual(self.ccsv_test.c_abilities, '"fly","sing"')
        self.assertEqual(self.ccsv_test.abilities, ['fly', 'sing'])
        self.assertEqual(self.ccsv_test.t_abilities, OrderedDict([
            ('fly', _('Fly')),
            ('sing', _('Sing')),
        ]))

    def test_abilities_add_c(self):
        self.ccsv_test.save_c('abilities', ['fly', 'sing'])
        self.ccsv_test.add_c('abilities', ['heal'])
        self.assertEqual(self.ccsv_test.c_abilities, '"fly","sing","heal"')
        self.assertEqual(self.ccsv_test.abilities, ['fly', 'sing', 'heal'])
        self.assertEqual(self.ccsv_test.t_abilities, OrderedDict([
            ('fly', _('Fly')),
            ('sing', _('Sing')),
            ('heal', _('Heal')),
        ]))

    def test_abilities_remove_c(self):
        self.ccsv_test.save_c('abilities', ['fly', 'heal', 'sing'])
        self.ccsv_test.remove_c('abilities', ['heal'])
        self.assertEqual(self.ccsv_test.c_abilities, '"fly","sing"')
        self.assertEqual(self.ccsv_test.abilities, ['fly', 'sing'])
        self.assertEqual(self.ccsv_test.t_abilities, OrderedDict([
            ('fly', _('Fly')),
            ('sing', _('Sing')),
        ]))

    # Tags
    # With choices restrictions without translations

    def test_tags_save_c(self):
        self.ccsv_test.save_c('tags', ['party', 'christmas'])
        self.assertEqual(self.ccsv_test.c_tags, '"party","christmas"')
        self.assertEqual(self.ccsv_test.tags, ['party', 'christmas'])
        self.assertEqual(self.ccsv_test.t_tags, OrderedDict([
            ('party', 'party'),
            ('christmas', 'christmas'),
        ]))

    def test_tags_add_c(self):
        self.ccsv_test.save_c('tags', ['party', 'christmas'])
        self.ccsv_test.add_c('tags', ['NSFW'])
        self.assertEqual(self.ccsv_test.c_tags, '"party","christmas","NSFW"')
        self.assertEqual(self.ccsv_test.tags, ['party', 'christmas', 'NSFW'])
        self.assertEqual(self.ccsv_test.t_tags, OrderedDict([
            ('party', 'party'),
            ('christmas', 'christmas'),
            ('NSFW', 'NSFW'),
        ]))

    def test_tags_remove_c(self):
        self.ccsv_test.save_c('tags', ['party', 'NSFW', 'christmas'])
        self.ccsv_test.remove_c('tags', ['NSFW'])
        self.assertEqual(self.ccsv_test.c_tags, '"party","christmas"')
        self.assertEqual(self.ccsv_test.tags, ['party', 'christmas'])
        self.assertEqual(self.ccsv_test.t_tags, OrderedDict([
            ('party', 'party'),
            ('christmas', 'christmas'),
        ]))
