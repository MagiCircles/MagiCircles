import datetime, sys
from django.core.management.base import BaseCommand, CommandError
from django.utils.html import escape
from django.conf import settings as django_settings
from magi import models
from magi.settings import SITE_STATIC_URL, STATIC_FILES_VERSION

def latlong():
    map = models.UserPreferences.objects.filter(latitude__isnull=False).select_related('user')

    mapcache = '{# this file is generated, do not edit it #}{% extends "base.html" %}{% load i18n %}{% load l10n %}{% block title %}{% trans "Map" %}{% endblock %}{% block content %}<div id="map"></div>{% endblock %}{% block afterjs %}{% localize off %}<script>var center=new google.maps.LatLng({% if center %}{{ center.latitude }},{{ center.longitude }}{% else %}30,0{% endif %});var zoom={% if zoom %}{{ zoom }}{% else %}2{% endif %};var addresses = ['

    for u in map:
        try:
            mapcache += '{open}"username": "{username}","avatar": "{avatar}","location": "{location}","icon": "{icon}","latlong": new google.maps.LatLng({latitude},{longitude}){close},'.format(
                open='{',
                username=escape(u.user.username),
                avatar=escape(models.avatar(u.user)),
                location=escape(u.location),
                icon=escape(u.favorite_character1_image if u.favorite_character1_image else SITE_STATIC_URL + 'static/img/default_map_icon.png'),
                latitude=u.latitude,
                longitude=u.longitude,
                close='}',
            )
        except:
            print 'One user not added in map', u
            print sys.exc_info()[0]

    mapcache += '];</script><script src="' + SITE_STATIC_URL + 'static/js/map.js?' + STATIC_FILES_VERSION + '"></script>{% endlocalize %}{% endblock %}'

    with open(django_settings.BASE_DIR + '/' + django_settings.SITE + '/templates/pages/map.html', 'w') as f:
        f.write(mapcache.encode('UTF-8'))
    f.close()

class Command(BaseCommand):
    can_import_settings = True

    def handle(self, *args, **options):
        print '[Info]', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'Generating map...'
        latlong()
        print '[Info]', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'Done'
