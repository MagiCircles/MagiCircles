# -*- coding: utf-8 -*-
import datetime, time, sys, os, math, pytz
from collections import OrderedDict
from PIL import Image
from django.utils import timezone
from django.utils.translation import activate as translation_activate, ugettext_lazy as _, get_language
from django.utils.formats import date_format
from django.utils.html import escape
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings as django_settings
from django.db.models import Count
from django.forms import ModelChoiceField, NullBooleanField
from magi.utils import (
    andJoin,
    birthdays_within,
    camelToSnakeCase,
    snakeCaseToTitle,
    getMagiCollections,
    imageSquareThumbnailFromData,
    imageURLToImageFile,
    makeImageGrid,
    listUnique,
    saveLocalImageToModel,
    getEventStatus,
    create_user as utils_create_user,
    get_default_owner as utils_get_default_owner,
    birthdayOrderingQueryset,
    modelHasField,
    getCharacterImageFromPk,
    LANGUAGES_DICT,
    getMagiCollection,
    checkIsCurrentSeasonNotFromGeneratedSettings,
    getAllTranslations,
    isCharacterModelClass,
)
from magi.settings import (
    ACTIVITY_TAGS,
    FAVORITE_CHARACTERS_MODEL,
    FAVORITE_CHARACTERS_FILTER,
    GET_BACKGROUNDS,
    BACKGROUNDS_MODEL,
    BACKGROUNDS_FILTER,
    GET_HOMEPAGE_ARTS,
    OTHER_CHARACTERS_MODELS,
    SITE_STATIC_URL,
    STATIC_FILES_VERSION,
    SEASONS,
    USERS_BIRTHDAYS_BANNER,
    BIRTHDAY_BANNER_HIDE_TITLE,
    MANY_BACKGROUNDS_THRESHOLD,
    MANY_CHARACTERS_THRESHOLD,
    HAS_MANY_BACKGROUNDS,
    HAS_MANY_FAVORITE_CHARACTERS,
)
from magi import models, seasons

############################################################
# Create user

def create_user(*args, **kwargs):
    return utils_create_user(models.User, *args, **kwargs)

def get_default_owner(*args, **kwargs):
    return utils_get_default_owner(models.User, *args, **kwargs)

############################################################
# Get user from link

def getUserFromLink(value, type=None):
    if type:
        try:
            return models.UserLink.objects.select_related('owner', 'owner__preferences').filter(
                i_type=models.UserLink.get_i('type', type), value__iexact=value)[0].owner
        except IndexError:
            return None
    try:
        return models.User.objects.select_related('preferences').filter(links__value__iexact=value)[0]
    except IndexError:
        return None

############################################################
# Get total donators (for generated settings)

def totalDonatorsThisMonth():
    print 'Get total donators'
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
    print 'Get total donators'
    return models.UserPreferences.objects.filter(i_status__isnull=False).exclude(i_status__exact='').count()

############################################################
# Get latest donation month (for generated settings)

def latestDonationMonth(failsafe=False):
    print 'Get latest donation month'
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
# Get staff configurations + latest news(for generated settings)

def getStaffConfigurations(generated_settings=None):
    print 'Get staff configurations and latest news'
    staff_configurations = {}
    latest_news = {}
    for staffconfiguration in models.StaffConfiguration.objects.all():
        if staffconfiguration.value is None or staffconfiguration.value == '':
            continue
        if staffconfiguration.key.startswith('banner_'):
            number = int(staffconfiguration.key.split('_')[1])
            if number not in latest_news:
                latest_news[number] = {}
            latest_news[number]['_'.join(staffconfiguration.key.split('_')[2:])] = staffconfiguration.boolean_value
            continue
        if staffconfiguration.i_language:
            if staffconfiguration.key not in staff_configurations:
                staff_configurations[staffconfiguration.key] = {}
            staff_configurations[staffconfiguration.key][staffconfiguration.language] = staffconfiguration.value
        else:
            staff_configurations[staffconfiguration.key] = staffconfiguration.value
    latest_news = list(latest_news.items())
    latest_news.sort(key=lambda (k, v): k)
    latest_news = [
        news
        for number, news in latest_news
        if (news.get('image')
            and news.get('title')
            and news.get('url'))
    ]
    for news in latest_news:
        news['priority'] = 100
    if generated_settings is not None:
        generated_settings['STAFF_CONFIGURATIONS'] = staff_configurations
        if 'LATEST_NEWS' not in generated_settings:
            generated_settings['LATEST_NEWS'] = []
        generated_settings['LATEST_NEWS'] += latest_news

    return staff_configurations, latest_news

def hasNewsOfCategory(latest_news, category):
    for news in latest_news:
        if news.get('category', None) == category:
            return True
    return False

############################################################
# Get characters birthdays (for generated settings)

def defaultGetNameImageURLFromCharacter(character):
    image = None
    for image_field in [
            'birthday_banner_url',
            'art_url'
    ]:
        image = getattr(character, image_field, None)
        if image:
            break
    return getattr(character, 'first_name', unicode(character)), image, character.item_url

def getCharactersBirthdays(queryset, get_name_image_url_from_character=defaultGetNameImageURLFromCharacter,
                           latest_news=None, days_after=12, days_before=1, field_name='birthday',
                           category='characters_birthdays'):
    print 'Show a banner for current and upcoming {}'.format(snakeCaseToTitle(category))
    if not latest_news:
        latest_news = []
    now = timezone.now()
    characters = list(queryset.filter(
        birthdays_within(days_after=days_after, days_before=days_before, field_name=field_name)
    ).order_by('name'))
    characters.sort(key=lambda c: getattr(c, field_name).replace(year=2000))
    for character in characters:
        name, image, url = get_name_image_url_from_character(character)
        if name is None:
            continue
        t_titles = {}
        old_lang = get_language()
        for lang in LANGUAGES_DICT.keys():
            translation_activate(lang)
            t_titles[lang] = u'{}, {}! {}'.format(
                _('Happy Birthday'),
                name,
                date_format(getattr(character, field_name), format='MONTH_DAY_FORMAT', use_l10n=True),
            )
        translation_activate(old_lang)
        latest_news.append({
            'background': image,
            'category': category,
            'color': getattr(character, 'color', None),
            't_titles': t_titles,
            'url': url,
            'hide_title': getattr(character, 'birthday_banner_hide_title', BIRTHDAY_BANNER_HIDE_TITLE),
            'ajax': False,
            'css_classes': getattr(character, 'birthday_banner_css_class', 'birthday'),
        })
    return latest_news

############################################################
# Get users birthdays (for generated settings)

def getUsersBirthdaysToday(image=None, latest_news=None, max_usernames=4):
    print 'Show a happy birthday banner for the users whose birthday is today'
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
        for lang in LANGUAGES_DICT.keys():
            translation_activate(lang)
            t_titles[lang] = u'{} 🎂🎉 {}'.format(
                _('Happy Birthday'),
                usernames,
            )
        translation_activate(old_lang)
        latest_news.append({
            'category': 'users_birthdays',
            't_titles': t_titles,
            'image': image or USERS_BIRTHDAYS_BANNER,
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
# Get backgrounds

def generateBackgroundsList(queryset=None, filter_queryset=None, check_for_threshold=False):
    if not queryset:
        if not BACKGROUNDS_MODEL:
            return None
        backgrounds_collection = getMagiCollection(getattr(BACKGROUNDS_MODEL, 'collection_name', None))
        if backgrounds_collection:
            queryset = backgrounds_collection.get_queryset()
        else:
            queryset = BACKGROUNDS_MODEL.objects.all()
    queryset = BACKGROUNDS_FILTER(queryset)
    if filter_queryset:
        queryset = filter_queryset(queryset)
    total = queryset.count()
    if check_for_threshold:
        if total > MANY_BACKGROUNDS_THRESHOLD:
            queryset = queryset.order_by('?')[:MANY_BACKGROUNDS_THRESHOLD]
    backgrounds = []
    for background in queryset:
        image = getattr(background, 'background_image_url', getattr(background, 'image_url', None))
        backgrounds.append({
            'id': background.pk,
            'image': image,
            'thumbnail': getattr(
                background, 'background_image_thumbnail_url',
                getattr(background, 'image_thumbnail_url', image),
            ),
            'hd_image': getattr(
                background, 'background_image_2x_url',
                getattr(background, 'image_2x_url', image),
            ),
            'name': unicode(background),
            'names': background.unicodes,
            'homepage': getattr(
                background, 'show_background_on_homepage',
                getattr(background, 'show_image_on_homepage', False),
            ),
            'profile': getattr(background, 'show_background_on_profile', True),
        })
    return backgrounds, total

def getBackgroundsFromModel():
    print 'Get backgrounds'
    return generateBackgroundsList(check_for_threshold=True)

############################################################
# Get seasonal activity tag banners

def getSeasonalActivityTagBanners(latest_news=None, seasonal_settings=None):
    print 'Get seasonal activity tag banners'
    if latest_news is None:
        latest_news = []
    if not seasonal_settings:
        return latest_news
    for current_season_name, current_season in seasonal_settings.items():
        season = SEASONS.get(current_season_name, {})
        show = season.get('show_activity_tag_banner_on_homepage', True)
        if not show:
            continue
        tag = season.get('activity_tag', None)
        if tag:
            image = current_season.get('activity_tag_banner', None) or None
            t_titles = {}
            old_lang = get_language()
            for lang in LANGUAGES_DICT.keys():
                translation_activate(lang)
                t_titles[lang] = unicode(tag)
                translation_activate(old_lang)
            latest_news.append({
                'category': 'seasonal_activity_tag',
                't_titles': t_titles,
                'image': image,
                'url': u'/activities/?search=&c_tags=season-{}&is_popular=1'.format(current_season_name),
                'hide_title': bool(image),
            })
    return latest_news

############################################################
# Generate details per chatacters

def generateCharactersSettings(
        queryset, generated_settings, imports=None,
        for_favorite=True, base_name=None,
        to_image=None, has_many=None, threshold=MANY_CHARACTERS_THRESHOLD,
):
    imports.append('from collections import OrderedDict')

    if not base_name:
        if for_favorite:
            base_name = 'FAVORITE_CHARACTERS'
        else:
            base_name = camelToSnakeCase(queryset.model.__name__, upper=True) + u'S'

    print u'Get the {}'.format(snakeCaseToTitle(base_name))

    generated_settings[base_name] = []
    original_names = {}
    for character in queryset:
        name = unicode(character)
        if to_image:
            image = to_image(character)
        else:
            for image_field in [
                    'image_for_favorite_character',
                    'top_image_list', 'top_image',
                    'image_thumbnail_url', 'image_url',
            ]:
                image = getattr(character, image_field, None)
                if image:
                    break
        if image and name:
            original_names[character.pk] = name
            generated_settings[base_name].append((
                character.pk,
                name,
                image,
            ))

    all_names = OrderedDict()
    for language in LANGUAGES_DICT.keys():
        for character in queryset:
            if character.pk not in original_names:
                continue
            translation_activate(language)
            name = unicode(character)
            if name != original_names[character.pk]:
                if character.pk not in all_names:
                    all_names[character.pk] = {}
                all_names[character.pk][language] = name
    translation_activate('en')
    generated_settings[u'{}_NAMES'.format(base_name)] = all_names

    if has_many is not None:
        generated_settings[u'HAS_MANY_{}'.format(base_name)] = has_many
    else:
        generated_settings[u'HAS_MANY_{}'.format(base_name)] = len(original_names) > threshold

    if modelHasField(queryset.model, 'birthday'):
        generated_settings[u'{}_BIRTHDAYS'.format(base_name)] = OrderedDict([
            (character.pk, (character.birthday.month, character.birthday.day))
            for character in birthdayOrderingQueryset(queryset.exclude(birthday=None), order_by=True)
            if character.pk in original_names and getattr(character, 'birthday', None)
        ])

        generated_settings[u'{}_BIRTHDAY_TODAY'.format(base_name)] = queryset.filter(
            birthdays_within(days_after=1, days_before=1)).values_list(
                'pk', flat=True)

############################################################
# Generate share images for list views

# Can be changed:
IMAGES_PER_SHARE_IMAGE = 9
SHARE_IMAGE_PER_LINE = 3
SHARE_IMAGES_SIZE = 200

def generateShareImageForMainCollections(collection):
    # Get queryset to get items in list view
    try:
        queryset = collection.list_view.get_queryset(collection.queryset, {}, None)
    except:
        queryset = collection.queryset
    queryset = queryset.order_by(*collection.list_view.default_ordering.split(','))[:100]
    # Get images for each item
    images = []
    for item in queryset:
        for field_name in ['share_image_in_list', 'share_image', 'top_image_list', 'top_image', 'image']:
            image = getattr(item, field_name, None)
            if image:
                images.append(image)
                break
        if len(images) == IMAGES_PER_SHARE_IMAGE:
            break
    if len(images) != IMAGES_PER_SHARE_IMAGE:
        print '!! Warning: Not enough images to generate share image for', collection.plural_name
        return None
    # Create share image from images
    image_instance = makeImageGrid(
        images,
        per_line=SHARE_IMAGE_PER_LINE,
        size_per_tile=SHARE_IMAGES_SIZE,
        upload=True,
        model=models.UserImage,
        previous_url=getattr(django_settings, 'GENERATED_SHARE_IMAGES', {}).get(collection.name, None),
    )
    image_instance._thumbnail_image = image_instance.image
    image_instance.save()
    return unicode(image_instance.image)

def getCacheForFilterFormChoices():
    print 'Get cache of filter form choices'
    cached_choices = {}
    for collection_name, collection in getMagiCollections().items():
        if not collection.list_view.filters_details:
            continue
        filter_form = collection.list_view.filter_form(
            {}, request=None, ajax=False, collection=collection, preset=None, allow_next=False,
        )
        cache_choices_for_fields = getattr(filter_form, 'cache_choices', [])
        if not cache_choices_for_fields or not hasattr(filter_form, 'filter_queryset'):
            continue
        queryset = collection.list_view.get_queryset(collection.queryset, {}, None)
        cached_choices[collection.name] = {}
        for field_name in cache_choices_for_fields:
            if field_name not in filter_form.fields:
                continue
            if isinstance(filter_form.fields[field_name], NullBooleanField):
                choices = [ (1, ''), (2, 'Yes'), (3, 'No') ]
            else:
                choices = filter_form.fields[field_name].choices
            cache_verbose_from_items = False
            if (isinstance(filter_form.fields[field_name], ModelChoiceField)
                and not isCharacterModelClass(filter_form.fields[field_name].queryset.model)):
                cache_verbose_from_items = True
                items = { item.pk: item for item in filter_form.fields[field_name].queryset }
                filtered_choices = OrderedDict()
            else:
                filtered_choices = []
            kept = []
            removed = []
            for choice, verbose in choices:
                if choice == '':
                    continue
                if filter_form.filter_queryset(queryset, { field_name: choice }, None).count():
                    kept.append(verbose)
                    if cache_verbose_from_items:
                        choice_details = { 'key': choice }
                        if choice in items:
                            all_translations = getAllTranslations(items[choice], unique=True)
                            choice_details['name'] = all_translations['en']
                            if len(all_translations) > 1:
                                del(all_translations['en'])
                                choice_details['names'] = all_translations
                        else:
                            choice_details['name'] = verbose
                        filtered_choices[choice] = choice_details
                    else:
                        filtered_choices.append(choice)
                else:
                    removed.append(verbose)
            cached_choices[collection.name][field_name] = filtered_choices
            if django_settings.DEBUG and getattr(django_settings, 'DEBUG_SHOW_CACHED_CHOICES', True):
                print u'  {} filter form: {} Removed {} choices, choices left: {}'.format(
                    collection.title, filter_form.fields[field_name].label, len(removed),
                    (andJoin(kept) if kept else 'none') if removed else 'all',
                )
    return cached_choices

############################################################
# Generate settings (for generated settings)

def seasonalGeneratedSettings(staff_configurations):
    print 'Get seasonal settings'
    seasonal_settings = {}
    for season_name, season in SEASONS.items():
        if checkIsCurrentSeasonNotFromGeneratedSettings(SEASONS, season_name):
            print '  Current season:', season_name
            seasonal_settings[season_name] = {}
            for variable in seasons.AVAILABLE_SETTINGS:
                if variable in season:
                    seasonal_settings[season_name][variable] = season[variable]
            for variable in seasons.STAFF_CONFIGURATIONS_SETTINGS + season.get('staff_configurations_settings', []):
                value = staff_configurations.get(u'season_{}_{}'.format(season_name, variable), None)
                if value is not None:
                    seasonal_settings[season_name][variable] = value
    return seasonal_settings

def magiCirclesGeneratedSettings(existing_values):
    now = timezone.now()
    one_week_ago = now - datetime.timedelta(days=10)

    generated_settings = {}
    imports = []

    ############################################################
    # Get settings only when missing:

    # Get staff configurations and latest news
    staff_configurations = existing_values.get('STAFF_CONFIGURATIONS', None)
    latest_news = []
    if not staff_configurations:
        staff_configurations, more_latest_news = getStaffConfigurations()
        latest_news += more_latest_news

    # Get favorite characters
    if FAVORITE_CHARACTERS_MODEL:
        queryset = FAVORITE_CHARACTERS_FILTER(FAVORITE_CHARACTERS_MODEL.objects.all())
        # Cache
        if not existing_values.get('FAVORITE_CHARACTERS', None):
            generateCharactersSettings(
                queryset,
                generated_settings=generated_settings,
                imports=imports, has_many=HAS_MANY_FAVORITE_CHARACTERS,
                threshold=MANY_CHARACTERS_THRESHOLD,
            )
        # Get birthday banners
        if modelHasField(FAVORITE_CHARACTERS_MODEL, 'birthday'):
            if not hasNewsOfCategory(latest_news, 'characters_birthdays'):
                latest_news = getCharactersBirthdays(
                    queryset,
                    latest_news=latest_news,
                )

    # Other characters
    if OTHER_CHARACTERS_MODELS:
        generated_settings['OTHER_CHARACTERS_KEYS'] = OTHER_CHARACTERS_MODELS.keys()
        for key, character_details in OTHER_CHARACTERS_MODELS.items():
            if not isinstance(character_details, dict):
                character_details = { 'model': character_details }
            queryset = character_details.get('filter', lambda q: q)(character_details['model'].objects.all())
            # Cache
            if not existing_values.get(key, None):
                generateCharactersSettings(
                    queryset,
                    generated_settings=generated_settings,
                    imports=imports,
                    for_favorite=False,
                    base_name=key,
                    has_many=character_details.get('has_many', None),
                    threshold=character_details.get('many_threshold', MANY_CHARACTERS_THRESHOLD),
                )
            # Get birthday banners
            if modelHasField(character_details['model'], 'birthday'):
                category = u'{}_birthdays'.format(key.lower())
                if not hasNewsOfCategory(latest_news, category):
                    latest_news = getCharactersBirthdays(
                        queryset,
                        category=category,
                        latest_news=latest_news,
                    )

    # Get total donators
    if not existing_values.get('TOTAL_DONATORS', None):
        generated_settings['TOTAL_DONATORS'] = totalDonatorsThisMonth() or '\'\''

    # Get latest donation month
    if not existing_values.get('DONATION_MONTH', None):
        generated_settings['DONATION_MONTH'] = latestDonationMonth(failsafe=True)

    # Get seasonal settings
    if not existing_values.get('SEASONAL_SETTINGS', None):
        generated_settings['SEASONAL_SETTINGS'] = seasonalGeneratedSettings(staff_configurations)

    # Add banners for seasonal hashtags
    if not hasNewsOfCategory(latest_news, 'seasonal_activity_tag'):
        latest_news = getSeasonalActivityTagBanners(
            seasonal_settings=existing_values.get('SEASONAL_SETTINGS', None) or generated_settings['SEASONAL_SETTINGS'],
            latest_news=latest_news,
        )

    # Get users birthdays
    if not hasNewsOfCategory(latest_news, 'users_birthdays'):
        latest_news = getUsersBirthdaysToday(
            latest_news=latest_news,
        )

    ############################################################
    # Always get:

    # Generate share images once a week
    if django_settings.DEBUG:
        generated_share_images_last_date = now
        generated_share_images = {}
    else:
        generated_share_images_last_date = getattr(django_settings, 'GENERATED_SHARE_IMAGES_LAST_DATE', None)
        if (generated_share_images_last_date
            and generated_share_images_last_date.replace(tzinfo=pytz.utc) > one_week_ago):
            generated_share_images = getattr(django_settings, 'GENERATED_SHARE_IMAGES', {})
        else:
            generated_share_images_last_date = now
            generated_share_images = {}
            print 'Generate auto share images'
            for collection_name, collection in getMagiCollections().items():
                if collection.auto_share_image:
                    generated_share_images[collection.name] = generateShareImageForMainCollections(collection)
    generated_settings['GENERATED_SHARE_IMAGES_LAST_DATE'] = 'datetime.datetime.fromtimestamp(' + unicode(
        time.mktime(generated_share_images_last_date.timetuple())
    ) + ')'
    generated_settings['GENERATED_SHARE_IMAGES'] = generated_share_images

    # Get homepage arts
    if GET_HOMEPAGE_ARTS:
        generated_settings['HOMEPAGE_ARTS'] = GET_HOMEPAGE_ARTS()

    # Get backgrounds
    if GET_BACKGROUNDS:
        generated_settings['BACKGROUNDS'] = GET_BACKGROUNDS()
        total = len(generated_settings['BACKGROUNDS'])
    elif BACKGROUNDS_MODEL:
        generated_settings['BACKGROUNDS'], total = getBackgroundsFromModel()

    backgrounds_collection = getMagiCollection(getattr(BACKGROUNDS_MODEL, 'collection_name', None))
    if HAS_MANY_BACKGROUNDS is not None:
        generated_settings['HAS_MANY_BACKGROUNDS'] = HAS_MANY_BACKGROUNDS
    else:
        generated_settings['HAS_MANY_BACKGROUNDS'] = backgrounds_collection and total > MANY_BACKGROUNDS_THRESHOLD

    # Get past tags count
    generated_settings['PAST_ACTIVITY_TAGS_COUNT'] = {}
    for tag_name, tag in ACTIVITY_TAGS.items():
        if getEventStatus(
                tag.get('start_date', None),
                tag.get('end_date', None),
                without_year_return='ended',
        ) == 'ended':
            generated_settings['PAST_ACTIVITY_TAGS_COUNT'][tag_name] = models.Activity.objects.filter(
                c_tags__contains='"{}"'.format(tag_name)).count()

    # Cache choices
    generated_settings['CACHED_FILTER_FORM_CHOICES'] = getCacheForFilterFormChoices()

    ############################################################
    # Save

    generated_settings.update({
        'STAFF_CONFIGURATIONS': staff_configurations,
        'LATEST_NEWS': latest_news,
    })

    return generated_settings, imports

def generateSettings(values, imports=[]):
    m_values, m_imports = magiCirclesGeneratedSettings(values)
    # Existing values have priority
    # Dicts and lists get merged
    for key, value in values.items():
        if isinstance(value, list):
            m_values[key] = value + m_values.get(key, [])
        elif isinstance(value, dict):
            d = m_values.get(key, {})
            d.update(value)
            m_values[key] = d
        else:
            m_values[key] = value

    # Resort latest news if needed
    if m_values.get('LATEST_NEWS', []):
        m_values['LATEST_NEWS'].sort(key=lambda news: int(news.get('priority', 1)) * -1)

    imports = m_imports + imports

    s = u'\
# -*- coding: utf-8 -*-\n\
import datetime\n\
' + u'\n'.join(listUnique(imports)) + '\n\
' + u'\n'.join([
    u'{key} = {value}'.format(key=key, value=unicode(value))
    for key, value in m_values.items()
]) + u'\n\
GENERATED_DATE = datetime.datetime.fromtimestamp(' + unicode(time.time()) + u')\n\
'
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
            mapcache += u'{open}"user_id": {user_id}, "username": "{username}","avatar": "{avatar}","location": "{location}","icon": "{icon}","latlong": new google.maps.LatLng({latitude},{longitude}){close},'.format(
                open=u'{',
                user_id=u.user_id,
                username=escape(u.user.username),
                avatar=escape(models.avatar(u.user)),
                location=escape(u.location),
                icon=escape(
                    getCharacterImageFromPk(u.favorite_character1)
                    if u.favorite_character1 is not None
                    else SITE_STATIC_URL + u'static/img/default_map_icon.png',
                ),
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
