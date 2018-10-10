# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.test import TestCase
from test import models

class ItemModelCacheTestCase(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.attribute_i = models.Gacha.get_i('attribute', 'pure')
        self.power_i = 1 # It's not possible to use get_i when using translated values
        self.super_power_i = models.Gacha.get_i('super_power', 'rock')
        self.rarity_i = models.Gacha.get_i('rarity', 'N')

        self.user = models.User.objects.create(id=1, username='abc')
        self.idol = models.Idol.objects.create(
            owner=self.user,
            name=u'Deby',
            japanese_name=u'デビ',
            image=u'idols/deby.png',
        )
        self.card = models.Card.objects.create(
            owner=self.user,
            idol=self.idol,
        )
        self.gacha = models.Gacha.objects.create(
            owner=self.user,
            name=u'Gacha get all the cards',
            image=u'gacha/image.png',
            card=self.card,
        )
        self.gacha2 = models.Gacha.objects.create(
            owner=self.user,
            name=u'A different gacha',
            image=u'gacha/different_image.png',
            card=self.card,
            i_attribute=self.attribute_i,
            i_power=self.power_i,
            i_super_power=self.super_power_i,
            i_rarity=self.rarity_i,
        )
        self.card.update_cache('idol')
        self.card.update_cache('gachas')

        # doesnt have last_update, always needs to be manually updated
        self.card.update_cache('idol_name')
        self.card.update_cache('gacha_names')

        self.card.save()

        self.card_without_gacha = models.Card.objects.create(
            owner=self.user,
        )

    def test_get_cached_free_format(self):
        self.assertEqual(self.card.cached_idol_name, u'Deby')
        self.assertEqual(self.card.cached_idol_japanese_name, u'デビ')
        self.assertEqual(self.card.cached_total_gachas, 2)

    def test_get_cached_one(self):
        self.assertEqual(self.card.cached_idol, {
            'ajax_item_url': u'/ajax/idol/1/',
            'full_item_url': u'http://test.com/idol/1/Deby/',
            'http_item_url': u'http://test.com/idol/1/Deby/',
            u'id': 1,
            u'image': u'idols/deby.png',
            'image_url': u'//localhost:8000/idols/deby.png',
            u'http_image_url': u'https://localhost:8000/idols/deby.png',
            'item_url': u'/idol/1/Deby/',
            u'japanese_name': u'デビ',
            u'name': u'Deby',
            'pk': 1,
            'unicode': u'Deby',
        })

    def test_get_cached_list(self):
        self.assertEqual(self.card.cached_gachas, [
            {
                'pk': 1,
                'id': 1,
                'name': u'Gacha get all the cards',
                'item_url': u'/gacha/1/Gacha-get-all-the-cards/',
                'full_item_url': u'http://test.com/gacha/1/Gacha-get-all-the-cards/',
                'http_item_url': u'http://test.com/gacha/1/Gacha-get-all-the-cards/',
                'image': u'gacha/image.png',
                'image_url': u'//localhost:8000/gacha/image.png',
                'unicode': u'Gacha get all the cards',
                'http_image_url': u'https://localhost:8000/gacha/image.png',
                'ajax_item_url': u'/ajax/gacha/1/',
                'i_attribute': 0,
                'attribute': 'smile',
                't_attribute': 'smile',
                'i_power': 0,
                'power': _('Happy'),
                't_power': _('Happy'),
                'i_super_power': 0,
                'super_power': 'happy',
                't_super_power': _('Happy'),
                'i_rarity': 0,
                'rarity': 'N',
                't_rarity': 'N',
            },
            {
                'http_item_url': u'http://test.com/gacha/2/A-different-gacha/',
                'item_url': u'/gacha/2/A-different-gacha/',
                'name': u'A different gacha',
                'image': u'gacha/different_image.png',
                'full_item_url': u'http://test.com/gacha/2/A-different-gacha/',
                'image_url': u'//localhost:8000/gacha/different_image.png',
                'unicode': u'A different gacha',
                'pk': 2,
                'id': 2,
                'http_image_url': u'https://localhost:8000/gacha/different_image.png',
                'ajax_item_url': u'/ajax/gacha/2/',
                'i_attribute': self.attribute_i,
                'attribute': 'pure',
                't_attribute': 'pure',
                'i_power': self.power_i,
                'power': _('Cool'),
                't_power': _('Cool'),
                'i_super_power': self.super_power_i,
                'super_power': 'rock',
                't_super_power': _('Rock'),
                'i_rarity': self.rarity_i,
                'rarity': 'N',
                't_rarity': 'N',
            }
        ])

    def test_get_cached_csv(self):
        self.assertEqual(self.card.cached_gacha_names, ['Gacha get all the cards', 'A different gacha'])
        self.assertEqual(self.card.cached_gacha_ids, [1, 2])

    def test_get_cached_none(self):
        self.assertEqual(self.card_without_gacha.cached_idol, None)
        self.assertEqual(self.card_without_gacha.cached_gachas, None)
        self.assertEqual(self.card_without_gacha.cached_gacha_ids, [])
        self.assertEqual(self.card_without_gacha.cached_gacha_names, [])
        self.assertEqual(self.card_without_gacha.cached_idol_name, None)
        self.assertEqual(self.card_without_gacha.cached_idol_japanese_name, None)
        self.assertEqual(self.card_without_gacha.cached_total_gachas, 0)
