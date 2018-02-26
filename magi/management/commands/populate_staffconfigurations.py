from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as django_settings
from magi.utils import ordinalNumber, LANGUAGES_DICT
from magi import models

def create(d):
    try:
        models.StaffConfiguration.objects.create(owner_id=1, **d)
        print u'Created {}{}'.format(d['key'], u'for language {}'.format(d['i_language']) if 'i_language' in d else '')
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
                'key': 'below_banners',
                'verbose_key': 'Below homepage banners',
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
        # create({
        #     'key': '',
        #     'verbose_key': '',
        #     'value': '',
        #     'is_markdown': True,
        #     'is_long': True,
        # })
