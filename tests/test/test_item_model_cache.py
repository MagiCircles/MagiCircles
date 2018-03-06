# -*- coding: utf-8 -*-
from django.test import TestCase
from test import models

class ItemModelCacheTestCase(TestCase):
    def setUp(self):
        self.user = models.User.objects.create(id=1)
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
        )
        self.card.force_update_cache('idol')
        self.card.force_update_cache('gachas')

        self.card_without_gacha = models.Card.objects.create(
            owner=self.user,
        )

    def test_get_cached_one(self):
        self.assertEqual(self.card.cached_idol, {
            'id': 1,
            'pk': 1,
            'name': u'Deby',
            'japanese_name': u'デビ',
            'image': u'idols/deby.png',
            'image_url': u'//localhost:8000/idols/deby.png',
            'http_image_url': u'https://localhost:8000/idols/deby.png',
            'unicode': u'Deby',
            'item_url': u'/idol/1/Deby/',
            'ajax_item_url': u'/ajax/idol/1/',
            'full_item_url': u'http://test.com/idol/1/Deby/',
            'http_item_url': u'http://test.com/idol/1/Deby/',
        })

    def test_get_cached_list(self):
        self.assertEqual(self.card.cached_gachas, [
            {
                'pk': 1,
                'id': 1,
                'name': u'Gacha get all the cards',
                'item_url': u'/gacha/1/Gacha get all the cards/',
                'full_item_url': u'http://test.com/gacha/1/Gacha get all the cards/',
                'http_item_url': u'http://test.com/gacha/1/Gacha get all the cards/',
                'image': u'gacha/image.png',
                'image_url': u'//localhost:8000/gacha/image.png',
                'unicode': u'Gacha get all the cards',
                'http_image_url': u'https://localhost:8000/gacha/image.png',
                'ajax_item_url': u'/ajax/gacha/1/',
            },
            {
                'http_item_url': u'http://test.com/gacha/2/A different gacha/',
                'item_url': u'/gacha/2/A different gacha/',
                'name': u'A different gacha',
                'image': u'gacha/different_image.png',
                'full_item_url': u'http://test.com/gacha/2/A different gacha/',
                'image_url': u'//localhost:8000/gacha/different_image.png',
                'unicode': u'A different gacha',
                'pk': 2,
                'id': 2,
                'http_image_url': u'https://localhost:8000/gacha/different_image.png',
                'ajax_item_url': u'/ajax/gacha/2/',
            }
        ])

    def test_get_cached_none(self):
        self.assertEqual(self.card_without_gacha.cached_idol, None)
        self.assertEqual(self.card_without_gacha.cached_gachas, None)
