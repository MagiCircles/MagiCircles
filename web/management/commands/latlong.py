import time, sys
from django.core.management.base import BaseCommand, CommandError
from django.utils.html import escape
from django.conf import settings as django_settings
from web import models
from web.settings import SITE_STATIC_URL
from geopy.geocoders import Nominatim

def getLatLong(geolocator, user, retry):
    time.sleep(1)
    try:
        location = geolocator.geocode(user.location)
        if location is not None:
            user.latitude = location.latitude
            user.longitude = location.longitude
            user.location_changed = False
            user.save()
            print user.user, user.location, user.latitude, user.longitude
        else:
            user.location_changed = False
            user.save()
            print user.user, user.location, 'Invalid location'
    except:
        try:
            if retry:
                print u'{} {} Error, {} retry...'.format(user.user, user.location, sys.exc_info()[0])
                getLatLong(geolocator, user)
            else:
                print u'{} {} Error, {}'.format(user.user, user.location, sys.exc_info()[0])
        except:
            print 'Error with a user\'s location'

def latlong(opt):
    reload, retry = opt['reload'], opt['retry']
    map = models.UserPreferences.objects.filter(location__isnull=False).exclude(location__exact='')
    if not reload:
        map = map.filter(location_changed__exact=True)
    geolocator = Nominatim()
    for user in map:
        getLatLong(geolocator, user, retry)

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
            print 'One user not added in map'

    mapcache += '];</script><script src="' + SITE_STATIC_URL + 'static/js/map.js"></script>{% endlocalize %}{% endblock %}'

    with open(django_settings.BASE_DIR + '/' + django_settings.SITE + '/templates/pages/map.html', 'w') as f:
        f.write(mapcache.encode('UTF-8'))
    f.close()

class Command(BaseCommand):
    can_import_settings = True

    def handle(self, *args, **options):

        opt = {
            'reload': 'reload' in args,
            'retry': 'retry' in args,
        }

        latlong(opt)
