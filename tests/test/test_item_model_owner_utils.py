from django.test import TestCase
from magi import models as magi_models
from test import models

class ItemModelOwnerUtilslTestCase(TestCase):
    def setUp(self):
        self.user = models.User.objects.create(id=123, username='134')
        self.user.preferences = magi_models.UserPreferences(user=self.user)
        self.user.preferences.save()
        self.user.save()
        self.book = models.Book.objects.create(owner=self.user, id=1)
        self.book2 = models.Book.objects.create(owner=self.user, id=2)
        self.chapters = {}
        for i in range(1, 5):
            self.chapters[i] = models.Chapter.objects.create(book=self.book, id=i)
        self.paragraphs = {}
        for chapter in self.chapters.values():
            self.paragraphs[chapter.id] = {}
            for i in range(1, 5):
                self.paragraphs[chapter.id][i] = models.Paragraph.objects.create(
                    chapter=chapter, id=(i + (chapter.id * 10)))

        self.other_user = models.User.objects.create(id=2)

    def test_got_created(self):
        self.assertEqual([u.id for u in models.User.objects.filter(id=123)], [123])
        self.assertEqual([b.id for b in models.Book.objects.all()], [1,2])
        self.assertEqual([c.id for c in models.Chapter.objects.all()], [1,2,3,4])
        self.assertEqual([p.id for p in models.Paragraph.objects.all()], [11,12,13,14,21,22,23,24,31,32,33,34,41,42,43,44])

    def test_fk_as_owner(self):
        self.assertEqual(models.Book.fk_as_owner, None)
        self.assertEqual(models.Chapter.fk_as_owner, 'book')
        self.assertEqual(models.Paragraph.fk_as_owner, 'chapter')

    def test_selector_to_owner(self):
        self.assertEqual(models.Book.selector_to_owner(), 'owner')
        self.assertEqual(models.Chapter.selector_to_owner(), 'book__owner')
        self.assertEqual(models.Paragraph.selector_to_owner(), 'chapter__book__owner')

    def test_owners_queryset(self):
        self.assertEqual([u.id for u in models.Book.owners_queryset(self.user)], [123])
        self.assertEqual([b.id for b in models.Chapter.owners_queryset(self.user)], [1,2])
        self.assertEqual([c.id for c in models.Paragraph.owners_queryset(self.user)], [1, 2, 3, 4])

    def test_owner_ids(self):
        self.assertEqual(models.Book.owner_ids(self.user), [123])
        self.assertEqual(models.Chapter.owner_ids(self.user), [1,2])
        self.assertEqual(models.Paragraph.owner_ids(self.user), [1, 2, 3, 4])

    def test_real_owner(self):
        self.assertEqual(self.user.real_owner, self.user)
        self.assertEqual(self.book.real_owner, self.user)
        self.assertEqual(self.chapters[1].real_owner, self.user)
        self.assertEqual(self.paragraphs[1][1].real_owner, self.user)

    def test_cache_owner(self):
        cached_owner = {
            'username': '134',
            'http_item_url': 'http://test.com/user/123/134/',
            'item_url': '/user/123/134/',
            'preferences': {
                'status': None,
                't_status': None,
                'localized_color': None,
                'rgb_color': None,
                'color': None,
                'hex_color': None,
                'twitter': None,
                'css_color': None,
                'i_status': None,
            },
            'share_url': 'http://test.com/user/123/134/',
            'email': u'',
            'full_item_url': 'http://test.com/user/123/134/',
            'pk': 123,
            'id': 123,
            'ajax_item_url': '/ajax/user/123/'
        }
        self.assertEqual(self.book.cached_owner, cached_owner)
        self.assertEqual(self.chapters[1].cached_owner, cached_owner)
        self.assertEqual(self.paragraphs[1][1].cached_owner, cached_owner)
