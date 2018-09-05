from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as django_settings
from magi.utils import ordinalNumber, LANGUAGES_DICT
from magi import models

def create(d):
    try:
        if not d.get('i_language', None) and models.StaffConfiguration.objects.filter(key=d['key']).count():
            print 'Failed to create {} with error: {}'.format(d['key'], 'Already exists')
            return
        models.StaffConfiguration.objects.create(owner_id=1, **d)
        print u'Created {}{}'.format(d['key'], u' for language {}'.format(d['i_language']) if 'i_language' in d else '')
    except Exception as e:
        print 'Failed to create {} with error: {}'.format(d['key'], e)

class Command(BaseCommand):
    can_import_settings = True

    def handle(self, *args, **options):

        ##################################
        # Translatable

        for language in LANGUAGES_DICT.keys():
            # Pages parts
            create({
                'key': 'below_homepage_banners',
                'verbose_key': 'Below homepage banners',
                'is_markdown': True,
                'is_long': True,
                'i_language': language,
            })
            create({
                'key': 'about_us',
                'verbose_key': '"About us" section in about page (second section)',
                'is_markdown': True,
                'is_long': True,
                'i_language': language,
            })
            create({
                'key': 'about_the_website',
                'verbose_key': '"About" section in about page (first section)',
                'is_markdown': True,
                'is_long': True,
                'i_language': language,
            })
            create({
                'key': 'below_about',
                'verbose_key': 'Below about section',
                'is_markdown': True,
                'is_long': True,
                'i_language': language,
            })
            create({
                'key': 'get_started',
                'verbose_key': 'Get started',
                'is_markdown': True,
                'is_long': True,
                'i_language': language,
            })

        ##################################
        # Non translatable

        # Homepage banners
        for i in range(1, 5):
            create({
                'key': 'banner_{}_title'.format(i),
                'verbose_key': '{} homepage banner: Text'.format(ordinalNumber(i)),
            })
            create({
                'key': 'banner_{}_url'.format(i),
                'verbose_key': '{} homepage banner: URL'.format(ordinalNumber(i)),
            })
            create({
                'key': 'banner_{}_image'.format(i),
                'verbose_key': '{} homepage banner: Image URL'.format(ordinalNumber(i)),
            })
            create({
                'key': 'banner_{}_hide_title'.format(i),
                'verbose_key': '{} homepage banner: Hide text'.format(ordinalNumber(i)),
                'is_boolean': True,
                'value': 'True',
            })
        create({
            'key': 'about_image',
            'verbose_key': 'Image under "About" section in about page (first section)',
        })
        create({
            'key': 'about_us_image',
            'verbose_key': 'Image under "About us" section in about page (second section)',
        })
        create({
            'key': 'below_about_image',
            'verbose_key': 'Image under the custom section under "About us" in about page',
        })
        create({
            'key': 'donators_goal',
            'verbose_key': 'Donations: Goal we\'re trying to reach (should match Patreon)',
        })
        create({
            'key': 'donate_image',
            'verbose_key': 'Donations: Illustration next to button on donation page',
        })
        # create({
        #     'key': '',
        #     'verbose_key': '',
        #     'value': '',
        #     'is_markdown': True,
        #     'is_long': True,
        # })
