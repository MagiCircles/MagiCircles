# -*- coding: utf-8 -*-
import datetime, time, sys
from django.utils import timezone
from django.utils.translation import activate as translation_activate, ugettext_lazy as _, get_language
from django.utils.formats import date_format
from django.utils.html import escape
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings as django_settings
from django.db.models import Count
from magi.utils import birthdays_within
from magi.settings import SITE_STATIC_URL, STATIC_FILES_VERSION
from magi import models

############################################################
# Create user

def create_user(username, email=None, password=None, language='en', is_superuser=False):
    new_user = models.User.objects.create_user(
        username=username,
        email=email or u'{}@yopmail.com'.format(username),
        password=username * 2,
        is_superuser=is_superuser,
        is_staff=is_superuser,
    )
    preferences = models.UserPreferences.objects.create(
        user=new_user,
        i_language=language,
    )
    new_user.preferences = preferences
    return new_user

def get_default_owner():
    try:
        return models.User.objects.filter(is_superuser=True).order_by('-id')[0]
    except IndexError:
        return create_user('db0', is_superuser=True)

############################################################
# Get total donators (for generated settings)

def totalDonatorsThisMonth():
    now = timezone.now()
    this_month = datetime.datetime(year=now.year, month=now.month, day=1)
    try:
        donation_month = models.DonationMonth.objects.get(date=this_month)
    except ObjectDoesNotExist:
        try:
            donation_month = models.DonationMonth.objects.order_by('-date')[0]
        except IndexError:
            return 0
    return models.Badge.objects.filter(donation_month=donation_month).values('user').distinct().count()

def totalDonators():
    return models.UserPreferences.objects.filter(i_status__isnull=False).exclude(i_status__exact='').count()

############################################################
# Get latest donation month (for generated settings)

def latestDonationMonth(failsafe=False):
    now = timezone.now()
    this_month = datetime.datetime(year=now.year, month=now.month, day=1)
    try:
        donation_month = models.DonationMonth.objects.get(date=this_month)
    except ObjectDoesNotExist:
        if not failsafe:
            return None
        try:
            donation_month = models.DonationMonth.objects.order_by('-date')[0]
        except IndexError:
            donation_month = None
    if not donation_month:
        return {
            'percent': 0,
            'percent_int': 0,
            'date': this_month,
            'donations': 0,
            'reached_100_percent': False,
        }
    return {
        'percent': donation_month.percent,
        'percent_int': donation_month.percent_int,
        'date': donation_month.date,
        'donations': donation_month.donations,
        'reached_100_percent': donation_month.reached_100_percent,
    }

############################################################
# Get staff configurations (for generated settings)

def getStaffConfigurations():
    staff_configurations = {}
    latest_news = { i: {} for i in range(1, 5) }
    for staffconfiguration in models.StaffConfiguration.objects.all():
        if staffconfiguration.value is None or staffconfiguration.value == '':
            continue
        if staffconfiguration.key.startswith('banner_'):
            latest_news[int(staffconfiguration.key.split('_')[1])]['_'.join(staffconfiguration.key.split('_')[2:])] = staffconfiguration.boolean_value
            continue
        if staffconfiguration.i_language:
            if staffconfiguration.key not in staff_configurations:
                staff_configurations[staffconfiguration.key] = {}
            staff_configurations[staffconfiguration.key][staffconfiguration.language] = staffconfiguration.value
        else:
            staff_configurations[staffconfiguration.key] = staffconfiguration.value
    return staff_configurations, [
        latest_news[i] for i in range(1, 5)
        if latest_news[i] and latest_news[i].get('image') and latest_news[i].get('title') and latest_news[i].get('url') ]

############################################################
# Get characters birthdays (for generated settings)

def getCharactersBirthdays(queryset, get_name_image_url_from_character,
                           latest_news=None, days_after=12, days_before=1, field_name='birthday'):
    if not latest_news:
        latest_news = []
    now = timezone.now()
    characters = list(queryset.filter(
        birthdays_within(days_after=days_after, days_before=days_before, field_name=field_name)
    ).order_by('name'))
    characters.sort(key=lambda c: getattr(c, field_name).replace(year=2000))
    for character in characters:
        name, image, url = get_name_image_url_from_character(character)
        if name is None or image is None:
            continue
        t_titles = {}
        old_lang = get_language()
        for lang, _verbose in django_settings.LANGUAGES:
            translation_activate(lang)
            t_titles[lang] = u'{}, {}! {}'.format(
                _('Happy Birthday'),
                name,
                date_format(getattr(character, field_name), format='MONTH_DAY_FORMAT', use_l10n=True),
            )
        translation_activate(old_lang)
        latest_news.append({
            't_titles': t_titles,
            'background': image,
            'url': url,
            'hide_title': False,
            'ajax': False,
            'css_classes': 'birthday',
        })
    return latest_news

############################################################
# Get users birthdays (for generated settings)

def getUsersBirthdaysToday(image, latest_news=None, max_usernames=4):
    if not latest_news:
        latest_news = []
    now = timezone.now()
    users = list(models.User.objects.filter(
        preferences__birthdate__day=now.day,
        preferences__birthdate__month=now.month,
    ).order_by('-preferences___cache_reputation'))
    if users:
        usernames = u'{}{}'.format(
            u', '.join([user.username for user in users[:max_usernames]]),
            u' + {}'.format(len(users[max_usernames:])) if users[max_usernames:] else '',
        )
        t_titles = {}
        old_lang = get_language()
        for lang, _verbose in django_settings.LANGUAGES:
            translation_activate(lang)
            t_titles[lang] = u'{} 🎂🎉 {}'.format(
                _('Happy Birthday'),
                usernames,
            )
        translation_activate(old_lang)
        latest_news.append({
            't_titles': t_titles,
            'image': image,
            'url': (
                users[0].item_url
                if len(users) == 1
                else u'/users/?ids={}&ordering=preferences___cache_reputation&reverse_order=on'.format(u','.join([unicode(user.id) for user in users]))
            ),
            'hide_title': False,
            'css_classes': 'birthday font0-5',
        })
    return latest_news

############################################################
# Generate settings (for generated settings)

def generateSettings(values, imports=[]):
    s = u'\
# -*- coding: utf-8 -*-\n\
import datetime\n\
' + u'\n'.join(imports) + '\n\
' + u'\n'.join([
    u'{key} = {value}'.format(key=key, value=unicode(value))
    for key, value in values.items()
]) + '\n\
GENERATED_DATE = datetime.datetime.fromtimestamp(' + unicode(time.time()) + u')\n\
'
    print s
    with open(django_settings.BASE_DIR + '/' + django_settings.SITE + '_project/generated_settings.py', 'w') as f:
        f.write(s.encode('utf8'))
        f.close()

############################################################
# Generate map

def generateMap():
    print '[Info]', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'Generating map...'
    map = models.UserPreferences.objects.filter(latitude__isnull=False).select_related('user')

    mapcache = u'{# this file is generated, do not edit it #}{% extends "base.html" %}{% load l10n %}{% block content %}<div class="padding15" id="map-title">{% include \'include/page_title.html\' with show_small_title=True %}</div><div id="map"></div>{% endblock %}{% block afterjs %}{% localize off %}<script>var center=new google.maps.LatLng({% if center %}{{ center.latitude }},{{ center.longitude }}{% else %}30,0{% endif %});var zoom={% if zoom %}{{ zoom }}{% else %}2{% endif %};var addresses = ['

    for u in map:
        try:
            mapcache += u'{open}"username": "{username}","avatar": "{avatar}","location": "{location}","icon": "{icon}","latlong": new google.maps.LatLng({latitude},{longitude}){close},'.format(
                open=u'{',
                username=escape(u.user.username),
                avatar=escape(models.avatar(u.user)),
                location=escape(u.location),
                icon=escape(u.favorite_character1_image if u.favorite_character1_image else SITE_STATIC_URL + u'static/img/default_map_icon.png'),
                latitude=u.latitude,
                longitude=u.longitude,
                close=u'}',
            )
        except:
            print 'One user not added in map', u.user.username, u.location
            print sys.exc_info()[0]

    mapcache += u'];</script><script src="' + SITE_STATIC_URL + u'static/js/map.js?' + STATIC_FILES_VERSION + u'"></script>{% endlocalize %}{% endblock %}'

    with open(django_settings.BASE_DIR + '/' + django_settings.SITE + '/templates/pages/map.html', 'w') as f:
        f.write(mapcache.encode('UTF-8'))
    f.close()
    print '[Info]', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'Done'
