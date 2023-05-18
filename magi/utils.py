# -*- coding: utf-8 -*-
from __future__ import division
import os, string, random, csv, tinify, cStringIO, pytz, simplejson, datetime, io, operator, re, math, requests, urllib, urllib2, json
from PIL import Image
from json.encoder import encode_basestring_ascii
from urlparse import urlparse
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from django.conf import settings as django_settings
from django.core.files.temp import NamedTemporaryFile
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import resolve
from django.core.validators import RegexValidator
from django.http import Http404
from django.utils.http import urlquote
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_text
from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _, get_language, activate as translation_activate
from django.utils.formats import dateformat, date_format
from django.utils.functional import Promise
from django.utils.safestring import mark_safe, SafeText, SafeBytes
from django.utils.html import escape
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.template import Context
from django.template.loader import get_template
from django.db import models
from django.db import connection
from django.db.models.fields import BLANK_CHOICE_DASH, FieldDoesNotExist
from django.db.models.related import RelatedObject
from django.db.models.query import QuerySet
from django.db.models import Q, Prefetch
from django.forms.models import model_to_dict
from django.forms import (
    NullBooleanField,
    BooleanField,
    TextInput,
    CharField as forms_CharField,
    URLField as forms_URLField,
    MultipleChoiceField as forms_MultipleChoiceField,
    CheckboxInput,
    HiddenInput,
    TimeField,
)
from django.core.mail import EmailMultiAlternatives
from django.core.files.images import ImageFile
from django_translated import t
from magi import seasons
from magi.raw import (
    DEFAULT_ICONS_BASED_ON_NAMES,
    FORM_FIELDS_EXTRA_VALUES,
    GET_PARAMETERS_NOT_IN_FORM,
    GET_PARAMETERS_IN_FORM_HANDLED_OUTSIDE,
    TWITTER_LINKS_COUNT_AS_X_CHARACTERS,
    TWITTER_MAX_CHARACTERS,
    RFC3066_TO_ISO6392,
    KNOWN_CRAWLERS,
    MAX_URL_LENGTH,
)
from magi.middleware.httpredirect import HttpRedirectException
from magi.default_settings import RAW_CONTEXT

try:
    CUSTOM_SEASONAL_MODULE_FOR_CONTEXT = __import__(django_settings.SITE + '.seasons_context', fromlist=[''])
except ImportError:
    CUSTOM_SEASONAL_MODULE_FOR_CONTEXT = None

############################################################
# Lazy

def _format_lazy(text, *args, **kwargs):
    return unicode(text).format(*args, **kwargs)

format_lazy = lazy(_format_lazy, unicode)
__ = format_lazy

# Example use:
# __(_('Select {}'), _('Idol'))
# __('{} - {}', _('Customize profile'), __(_('Select {}'), lowerTranslation(_('Idol'))))

def _lower_lazy(text):
    return unicode(text).lower()

lowerTranslation = lazy(_lower_lazy, unicode)

# Example use:
# lowerTranslation(_('Idol')) -> idol

def markSafeJoin(strings, separator=u' '):
    return mark_safe(separator.join([
        _markSafeFormatEscapeOrNot(string) for string in strings
        if string is not None
    ]))

def _join_lazy(strings, separator=u' - ', mark_safe=False):
    if mark_safe:
        return markSafeJoin(strings, separator=separator)
    return separator.join([ unicode(string) for string in strings if string is not None ])

joinTranslation = lazy(_join_lazy, unicode)

def andJoin(strings, translated=True, mark_safe=False, language=None, or_=False, max=None):
    if not strings:
        return u''
    if max is not None and len(strings) > max:
        strings = strings[:max] + [ _('More').lower() ]
    strings = [
        _markSafeFormatEscapeOrNot(string) if mark_safe else unicode(string)
        for string in strings if string is not None
    ]
    if len(strings) == 1:
        string = strings[0]
    else:
        comma = COMMA_PER_LANGUAGE.get('en' if not translated else (language or get_language()), COMMA_PER_LANGUAGE['en'])
        if or_:
            keyword = t['or'] if translated else 'or'
        else:
            keyword = t['and'] if translated else 'and'
        string = u''.join([
            comma.join(strings[:-1]),
            u' {} '.format(keyword),
            strings[-1],
        ])
    if mark_safe:
        return _mark_safe(string)
    return string

andJoinTranslation = lazy(andJoin, unicode)

def getTranslatedName(d, field_name='name', language=None):
    value = d.get(u'{}s'.format(field_name), {}).get(
        language or get_language(),
        d.get(field_name, None),
    )
    return unicode(value) if value is not None else None

getTranslatedNameLazy = lazy(getTranslatedName, unicode)

def ordinalNumber(n):
    return "%d%s" % (n, "tsnrhtdd"[(n / 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])

def translatedOrdinalNumber(n):
    return unicode(_(ordinalNumber(n)))

ordinalNumberLazy = lazy(translatedOrdinalNumber, unicode)

############################################################
# Characters

ALL_CHARACTERS_KEYS = ['FAVORITE_CHARACTERS'] + getattr(django_settings, 'OTHER_CHARACTERS_KEYS', [])

_CHARACTERS_IMAGES = {
    _key: OrderedDict([
        (_pk, _image)
        for (_pk, _name, _image) in getattr(django_settings, _key, [])
    ]) for _key in ALL_CHARACTERS_KEYS
}

_CHARACTERS_IMAGES_UNICODE = {
    _key: OrderedDict([
        (unicode(_pk), _image)
        for (_pk, _name, _image) in getattr(django_settings, _key, [])
    ]) for _key in ALL_CHARACTERS_KEYS
}

_CHARACTERS_NAMES = {
    _key: OrderedDict([
        (_pk, _name)
        for (_pk, _name, _image) in getattr(django_settings, _key, [])
    ]) for _key in ALL_CHARACTERS_KEYS
}

_CHARACTERS_NAMES_UNICODE = {
    _key: OrderedDict([
        (unicode(_pk), _name)
        for (_pk, _name, _image) in getattr(django_settings, _key, [])
    ]) for _key in ALL_CHARACTERS_KEYS
}

_CHARACTERS_LOCALIZED_NAMES = {
    _key: getattr(django_settings, '{}_NAMES'.format(_key), {})
    for _key in ALL_CHARACTERS_KEYS
}

_CHARACTERS_LOCALIZED_NAMES_UNICODE = {
    _key: OrderedDict([
        (unicode(_pk), _names)
        for (_pk, _names) in getattr(django_settings, '{}_NAMES'.format(_key), {}).items()
    ]) for _key in ALL_CHARACTERS_KEYS
}

_CHARACTERS_BIRTHDAYS = {
    _key: getattr(django_settings, '{}_BIRTHDAYS'.format(_key), {})
    for _key in ALL_CHARACTERS_KEYS
}

_CHARACTERS_BIRTHDAYS_UNICODE = {
    _key: OrderedDict([
        (unicode(_pk), _birthday)
        for (_pk, _birthday) in getattr(django_settings, '{}_BIRTHDAYS'.format(_key), {}).items()
    ]) for _key in ALL_CHARACTERS_KEYS
}

def isCharacterModelClass(model_class):
    # /!\ Can't be called at global level
    if model_class == RAW_CONTEXT.get('favorite_characters_model', None):
        return 'FAVORITE_CHARACTERS'
    for key, character_details in RAW_CONTEXT.get('other_characters_models', None).items():
        if ((isinstance(character_details, dict) and model_class == character_details['model'])
            or model_class == character_details):
            return key
    return False

def getCharacterSetting(detail, key='FAVORITE_CHARACTERS', default=None):
    # /!\ Can't be called at global level
    if key == 'FAVORITE_CHARACTERS':
        if detail == 'model':
            return RAW_CONTEXT.get('favorite_characters_model', default)
        elif detail == 'how_many_favorites':
            return 3
        return default
    character_details = RAW_CONTEXT.get('other_characters_models', {}).get(key, {})
    if not isinstance(character_details, dict):
        if detail == 'model':
            return character_details
        return default
    return character_details.get(detail, default)

def getCharacters(key='FAVORITE_CHARACTERS'):
    return getattr(django_settings, key, [])

def hasCharacters(key='FAVORITE_CHARACTERS'):
    return bool(getCharacters(key=key))

def getTotalCharacters(key='FAVORITE_CHARACTERS'):
    return len(getCharacters(key=key))

def getCharactersPks(key='FAVORITE_CHARACTERS'):
    return _CHARACTERS_NAMES.get(key, {}).keys()

def isValidCharacterPk(pk, key='FAVORITE_CHARACTERS'):
    return (
        pk in _CHARACTERS_NAMES.get(key, {})
        or pk in _CHARACTERS_NAMES_UNICODE.get(key, {})
    )

def isValidCharacterNth(nth, key='FAVORITE_CHARACTERS'):
    return unicode(nth) in [ unicode(i) for i in range(1, getCharactersTotalFavoritable(key) + 1) ]

def getCharacterNamesFromPk(pk, key='FAVORITE_CHARACTERS'):
    return {
        'name': (
            _CHARACTERS_NAMES.get(key, {}).get(pk, None)
            or _CHARACTERS_NAMES_UNICODE.get(key, {}).get(pk, None)
        ),
        'names': (
            _CHARACTERS_LOCALIZED_NAMES.get(key, {}).get(pk, {})
            or _CHARACTERS_LOCALIZED_NAMES_UNICODE.get(key, {}).get(pk, {})
        ),
    }

def getCharacterCacheFromPk(pk, key='FAVORITE_CHARACTERS', with_extra=True):
    cache = getCharacterNamesFromPk(pk, key=key)
    cache['birthday'] = getCharacterBirthdayFromPk(pk, key=key)
    cache['image'] = getCharacterImageFromPk(pk, key=key)
    if with_extra:
        # /!\ Can't be called at global level
        cache = cacheRelExtra(
            cache, RAW_CONTEXT['cached_item_class'],
            id=pk, collection_name=getCharacterCollectionName(key),
            model_class=getCharacterSetting('model', key=key),
        )
    return cache

def getCharacterEnglishNameFromPk(pk, key='FAVORITE_CHARACTERS'):
    return _CHARACTERS_NAMES.get(key, {}).get(pk, None)

def getCharacterNameFromPk(pk, key='FAVORITE_CHARACTERS'):
    return getTranslatedNameLazy(getCharacterNamesFromPk(pk, key=key))

def getCharacterBirthdayFromPk(pk, failsafe=False, key='FAVORITE_CHARACTERS'):
    return (
        _CHARACTERS_BIRTHDAYS.get(key, {}).get(pk, None)
        or _CHARACTERS_BIRTHDAYS_UNICODE.get(key, {}).get(pk, None)
        or ((None, None) if failsafe else None)
    )

def getCharactersBirthdayToday(key='FAVORITE_CHARACTERS', check_date=True):
    if not check_date:
        return getattr(django_settings, u'{}_BIRTHDAY_TODAY'.format(key), [])
    birthday_today_setting = []
    for character_pk in getCharactersBirthdayToday(key=key, check_date=False):
        birthday = getCharacterBirthdayFromPk(character_pk, key=key)
        if birthday and getEventStatus(start_date=birthday, ends_within=1) == 'ended_recently':
            birthday_today_setting.append(character_pk)
    return birthday_today_setting

def getCharacterImageFromPk(pk, default=None, key='FAVORITE_CHARACTERS'):
    return (
        _CHARACTERS_IMAGES.get(key, {}).get(pk, None)
        or _CHARACTERS_IMAGES_UNICODE.get(key, {}).get(pk, None)
        or default
    )

def getCharacterURLFromPk(pk, key='FAVORITE_CHARACTERS', ajax=False):
    # /!\ Can't be called at global level
    if key == 'FAVORITE_CHARACTERS' and not getCharacterSetting('model', key=key):
        return u'{}{}'.format(
            u'/ajax' if ajax else '',
            RAW_CONTEXT.get('favorite_character_to_url', lambda _link: '#')({
                'raw_value': pk,
                'value': getCharacterNameFromPk(pk),
            }),
        )
    return u'{}/{}/{}/'.format(
        u'/ajax' if ajax else '',
        getCharacterCollectionName(key=key),
        pk,
        u'{}/'.format(tourldash(getCharacterNameFromPk(pk, key=key))) if not ajax else '',
    )

_CHARACTERS_CHOICES = {
    _key: [
        # It's OK to call getCharacterNameFromPk because translation is lazy
        (_pk, getCharacterNameFromPk(_pk, key=_key))
        for _pk, _character_name, _image in getattr(django_settings, _key, {})
    ] for _key in ALL_CHARACTERS_KEYS
}

def getCharactersChoices(key='FAVORITE_CHARACTERS'):
    return _CHARACTERS_CHOICES.get(key, [])

def getCharacterCollectionName(key='FAVORITE_CHARACTERS'):
    # /!\ Can't be called at global level
    model = getCharacterSetting('model', key=key)
    try:
        return model.collection_name if model else None
    except AttributeError:
        return None

def getCharacterCollection(key='FAVORITE_CHARACTERS'):
    # /!\ Can't be called at global level
    return getMagiCollection(getCharacterCollectionName(key=key))

def getCharacterLabel(key='FAVORITE_CHARACTERS'):
    # /!\ Can't be called at global level
    if key == 'FAVORITE_CHARACTERS' and RAW_CONTEXT.get('favorite_character_name', None):
        label = RAW_CONTEXT['favorite_character_name']
    else:
        label = failSafe(lambda: getCharacterCollection(key).title, exceptions=[ AttributeError ])
    if callable(label):
        label = label()
    if not label:
        label = _('Character')
    return label

def getCharacterPluralLabel(key='FAVORITE_CHARACTERS'):
    # /!\ Can't be called at global level
    label = failSafe(lambda: getCharacterCollection(key).plural_title, exceptions=[ AttributeError ])
    if callable(label):
        label = label()
    if not label:
        label = _('Characters')
    return label

# When used as favorites

def getCharactersTotalFavoritable(key='FAVORITE_CHARACTERS'):
    # /!\ Can't be called at global level
    return getCharacterSetting('how_many_favorites', key=key, default=1)

def getCharactersHasMany(key='FAVORITE_CHARACTERS'):
    return getattr(django_settings, u'HAS_MANY_{}'.format(key), False)

def getCharactersFavoriteFieldLabel(key='FAVORITE_CHARACTERS', nth=None, plural=False):
    # /!\ Can't be called at global level
    if not nth and plural:
        label = getCharacterPluralLabel(key=key)
    else:
        label = getCharacterLabel(key=key)
    if nth is None:
        return _(u'Favorite {thing}').format(
            thing=label.lower(),
        )
    return _('{nth} Favorite {thing}').format(
        nth=_(ordinalNumber(nth)),
        thing=label.lower(),
    )

def getCharactersKeys():
    return [
        key
        for key in ALL_CHARACTERS_KEYS
        if hasCharacters(key)
    ]

def getCharactersOtherExtraKey(key, nth=None, total_favoritable=None, collection_name=None):
    if not total_favoritable:
        total_favoritable = getCharactersTotalFavoritable(key)
    if not collection_name:
        collection_name = getCharacterCollectionName(key)
    return u'favorite_{}{}'.format(
        collection_name,
        nth if total_favoritable > 1 else '',
    )

def getCharactersFavoriteFields(only_one=False):
    """
    Returns dict: key => [ (field_name, field_label) ]
    """
    # /!\ Can't be called at global level
    fields = OrderedDict()
    for key in getCharactersKeys():
        collection_name = getCharacterCollectionName(key)
        total_favoritable = getCharactersTotalFavoritable(key)
        fields[key] = []
        if only_one:
            if key == 'FAVORITE_CHARACTERS':
                field_name = 'favorite_character'
            else:
                field_name = 'favorite_{}'.format(collection_name)
            label = getCharactersFavoriteFieldLabel(key=key)
            fields[key].append((field_name, label))
        else:
            for nth in range(1, total_favoritable + 1):
                if key == 'FAVORITE_CHARACTERS':
                    field_name = 'favorite_character{}'.format(nth)
                else:
                    field_name = u'd_extra-{}'.format(getCharactersOtherExtraKey(
                        key, nth=nth, total_favoritable=total_favoritable, collection_name=collection_name))
                label = getCharactersFavoriteFieldLabel(
                    key=key, nth=nth if not only_one and total_favoritable > 1 else None)
                fields[key].append((field_name, label))
    return fields

def getCharactersUsersFavorites(user, with_images=False, with_names=False):
    """
    Returns dict: key => { position: { field_name, field_label, pk, (image) } }
    """
    # /!\ Can't be called at global level
    favorites = OrderedDict()
    for key, fields in getCharactersFavoriteFields().items():
        favorites[key] = OrderedDict()
        for i, (field_name, field_label) in enumerate(fields):
            try:
                if field_name.startswith('d_extra-'):
                    pk = user.preferences.extra.get(field_name[len('d_extra-'):], None)
                else:
                    pk = getattr(user.preferences, field_name)
            except AttributeError:
                pk = None
            favorites[key][i + 1] = {
                'field_name': field_name,
                'field_label': field_label,
                'pk': pk,
            }
            if with_images:
                favorites[key][i + 1]['image'] = getCharacterImageFromPk(pk, key=key)
            if with_names:
                favorites[key][i + 1]['name'] = getCharacterNameFromPk(pk, key=key)
    return favorites

def isCharactersUserFavorite(pk, key='FAVORITE_CHARACTERS', favorite_characters=None, user=None):
    """
    Either specify user or already-retrieved favorite_characters (from getCharactersUsersFavorites).
    Set key to None to find in all keys (not recommended).
    """
    # /!\ Can't be called at global level
    if not favorite_characters:
        favorite_characters = getCharactersUsersFavorites(user)
    for current_key, current_favorite_characters in favorite_characters.items():
        if key and current_key != key:
            continue
        for position, favorite_character in current_favorite_characters.items():
            if favorite_character['pk'] and unicode(favorite_character['pk']) == unicode(pk):
                return position
    return False

def setCharactersUserFavorite(user, pk, nth=1, key='FAVORITE_CHARACTERS'):
    """You'll still need to call user.preferences.save() after"""
    # /!\ Can't be called at global level
    if not isValidCharacterNth(nth, key=key):
        raise ValueError(u'"{}" is not a valid position for {}'.format(nth, key))
    if key == 'FAVORITE_CHARACTERS':
        setattr(user.preferences, 'favorite_character{}'.format(nth), pk)
    else:
        user.preferences.add_d('extra', getCharactersOtherExtraKey(key, nth), pk)

def unsetCharactersUserFavorite(user, nth=1, key='FAVORITE_CHARACTERS'):
    """You'll still need to call user.preferences.save() after"""
    # /!\ Can't be called at global level
    if key == 'FAVORITE_CHARACTERS':
        setattr(user.preferences, 'favorite_character{}'.format(nth), None)
    else:
        user.preferences.remove_d('extra', getCharactersOtherExtraKey(key, nth))

def getCharactersFavoriteCuteForm(only_one=True):
    # /!\ Can't be called at global level
    def to_cuteform_lambda(key):
        return lambda k, v: getCharacterImageFromPk(k, key=key)
    return {
        field_name: {
            'title': verbose_field_name,
            'to_cuteform': to_cuteform_lambda(key),
            'extra_settings': {
	        'modal': 'true',
	        'modal-text': 'true',
            },
        }
        for key, fields in getCharactersFavoriteFields(only_one=only_one).items()
        for field_name, verbose_field_name in fields
    }

def getCharactersFavoriteFilter(key='FAVORITE_CHARACTERS', field_name=None, prefix=''):
    # /!\ Can't be called at global level
    """
    Returns the MagiFilter parameters for a field to filter by favorite character.
    When field_name is specified, will only look for given field.
    Otherwise, will look for all nth.
    """
    if prefix:
        prefix = u'{}__preferences__'.format(prefix)
    else:
        prefix = 'preferences__'
    total = getCharactersTotalFavoritable(key=key)
    if key == 'FAVORITE_CHARACTERS':
        if field_name:
            return { 'selector': '{}{}'.format(prefix, field_name) }
        elif total == 1: # shouldn't happen unless allowing configuration of total_favorite_character gets implemented
            return { 'selector': '{}favorite_character1'.format(prefix, field_name) }
        return {
            'selectors': [
                u'{}favorite_character{}'.format(prefix, nth)
                for nth in range(1, total + 1)
            ],
            'multiple': False,
        }
    if field_name:
        return {
            'to_queryset': lambda form, queryset, request, value: queryset.filter(**{
                u'{}d_extra__contains'.format(prefix): u'"{}": "{}"'.format(field_name, value)
            }),
        }
    collection_name = getCharacterCollectionName(key)
    if total == 1:
        return {
            'to_queryset': lambda form, queryset, request, value: queryset.filter(**{
                u'{}d_extra__contains'.format(prefix): u'"favorite_{}": "{}"'.format(
                    collection_name, value),
            }),
        }
    def _to_queryset(form, queryset, request, value):
        condition = Q()
        for nth in range(1, total + 1):
            condition |= Q(**{ u'{}d_extra__contains'.format(prefix): '"favorite_{}{}": "{}"'.format(
                collection_name, nth, value) })
        return queryset.filter(condition)
    return {
        'to_queryset': _to_queryset,
    }

def getCharactersFavoriteQueryset(queryset, value, key='FAVORITE_CHARACTERS', field_name=None, prefix=''):
    # /!\ Can't be called at global level
    if not prefix:
        queryset = queryset.select_related('preferences')
    magi_filter = getCharactersFavoriteFilter(key=key, field_name=field_name, prefix=prefix)
    if magi_filter.get('to_queryset', None):
        return magi_filter['to_queryset'](None, queryset, None, value)
    elif magi_filter.get('selector', None):
        return queryset.filter(**{ magi_filter['selector']: value })
    elif magi_filter.get('selectors', None):
        condition = Q()
        for selector in magi_filter['selectors']:
            condition |= Q(**{ selector: value })
        return queryset.filter(condition)
    return queryset

############################################################
# Languages

# es -> _("Spanish")
LANGUAGES_DICT = OrderedDict(django_settings.LANGUAGES)

# es -> "Español"
NATIVE_LANGUAGES = OrderedDict(getattr(django_settings, 'NATIVE_LANGUAGES', [])) or LANGUAGES_DICT

# es -> spanish
LANGUAGES_NAMES = {
    _language: unicode(_verbose_name).replace(' ', '_').lower()
    for _language, _verbose_name in LANGUAGES_DICT.items()
}
# spanish -> es
LANGUAGES_NAMES_TO_CODES = { _v: _k for _k, _v in LANGUAGES_NAMES.items() }

def getVerboseLanguage(language, in_native_language=False):
    if in_native_language:
        return NATIVE_LANGUAGES.get(language, None)
    return LANGUAGES_DICT.get(language, None)

def getLanguageImage(language):
    # /!\ Can't be called at global level
    return staticImageURL(language, folder='language', extension='png')

def getRomajiWithFallback(
        item, romaji_field_name='romaji_name', fallback_field_name='name',
        language=None, return_language=False,
):
    if not language:
        language = get_language()
    fallback_language, fallback = item.get_translation(fallback_field_name, language=language, return_language=True)
    if not couldSpeakEnglish(language=language, request=getattr(item, 'request', None)):
        if fallback:
            return (fallback_language, fallback) if return_language else fallback
        return ('en', item.romaji_name) if return_language else item.romaji_name
    else:
        if item.romaji_name:
            return (language or 'en', item.romaji_name) if return_language else item.romaji_name
        return (fallback_language, fallback) if return_language else fallback

############################################################
# Getters for django settings

def getStaffConfiguration(key, default=None, language=None, from_db_model_class=False, is_json=False):
    if language is not None:
        if language == True:
            language = get_language()
    if from_db_model_class:
        value = failSafe(lambda: from_db_model_class.objects.filter(**(
            { 'key': key } if not language else { 'key': key, 'language': language }))[0].value, exceptions=[
                IndexError])
    elif language:
        value = django_settings.STAFF_CONFIGURATIONS.get(key, {}).get(language, None)
    else:
        value = django_settings.STAFF_CONFIGURATIONS.get(key, None)
    if not value:
        return default
    return json.loads(value) if is_json else value

def getStaffConfigurationCache(model_class, key, default=None, is_json=True):
    default = {} if is_json else None
    tmp_default = -1 if default != -1 else -2
    # Always retrieves from db
    value = getStaffConfiguration(
        key, default=tmp_default, is_json=is_json,
        from_db_model_class=model_class)
    if value == tmp_default:
        value = default
        model_class.objects.create(
            owner=get_default_owner(model_class._meta.get_field('owner').rel.to), key=key,
            value=json.dumps(default), verbose_key='Internal cache: {}. Do not edit manually.'.format(key))
    return value

def saveStaffConfigurationCache(model_class, key, value, is_json=True):
    model_class.objects.filter(key=key).update(value=json.dumps(value) if is_json else value)

def hasCachedChoice(model_class, field_name, choice=None, i_choice=None, key_choice=None, default=None):
    """field_name should include i_/c_/d_ if needed. Either choice/i_choice/key_choice required."""
    if not model_class:
        return default
    if choice is None:
        if i_choice is not None:
            choice = i_choice
        elif key_choice is not None:
            choice = model_class.get_i(field_name[2:], key_choice)
    if choice is None:
        return default
    choices = getattr(django_settings, 'CACHED_FILTER_FORM_CHOICES', {}).get(
        model_class.collection_name, {})
    if field_name not in choices:
        return default
    return choice in choices[field_name]

############################################################
# Use a dict as a class

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def __unicode__(self):
        return self.__dict__.get('unicode', u', '.join([
            u'{}: {}'.format(k, v) for k, v in self.__dict__.items()]))

############################################################
# Permissions and groups utils

def hasGroup(user, group):
    return group in user.preferences.groups

def hasPermission(user, permission):
    """
    Has the given permission.
    """
    if user.is_superuser:
        return True
    for group in user.preferences.groups:
        if permission in user.preferences.GROUPS.get(group, {}).get('permissions', []):
            return True
    return False

def hasOneOfPermissions(user, permissions):
    """
    Has at least one of the listed permissions.
    """
    if user.is_superuser:
        return True
    for group in user.preferences.groups:
        for permission in permissions:
            if permission in user.preferences.GROUPS.get(group, {}).get('permissions', []):
                return True
    return False

def hasPermissions(user, permissions):
    """
    Has all the listed permissions.
    """
    if user.is_superuser:
        return True
    permissions = { p: False for p in permissions }
    for group in user.preferences.groups:
        for permission in permissions:
            if permission in user.preferences.GROUPS.get(group, {}).get('permissions', []):
                permissions[permission] = True
    return all(permissions.values())

def groupsForAllPermissions(groups):
    """
    Dictionary of permission -> dict of groups
    """
    a = {}
    for group_name, group in groups.items():
        for permission in group.get('permissions', []):
            if permission not in a:
                a[permission] = {}
            a[permission][group_name] = group
    return a

def allPermissions(groups):
    """
    List of all existing permissions
    """
    return groupsForAllPermissions(groups).keys()

def groupsPerPermission(groups, permission):
    """
    List of groups that have this permission
    """
    return groupsForAllPermissions(groups).get(permission, [])

def groupsWithPermissions(groups, permissions):
    """
    List of groups that have all these permissions
    Example:
    - group1: a, b, c
    - group2: a, b, d, e
    groupsWithPermissions(..., [a, b]) -> dict with group1, group2
    groupsWithPermissions(..., [c, a]) -> dict with group1
    """
    g = {}
    for group_name, group in groups.items():
        has_all = True
        for permission in permissions:
            if permission not in group.get('permissions', []):
                has_all = False
                break
        if has_all:
            g[group_name] = group
    return g

def groupsWithOneOfPermissions(groups, permissions):
    """
    List of groups that have one of these permissions
    Example:
    - group1: a, b, c
    - group2: a, b, d, e
    groupsWithOneOfPermissions(..., [c, a]) -> dict with group1, group2
    """
    g = {}
    all = groupsForAllPermissions(groups)
    for permission in permissions:
        for group_name, group in all.get(permission, {}).items():
            g[group_name] = group
    return g

def usersWithGroup(queryset, group):
    """
    Users in this group
    """
    return queryset.filter(preferences__c_groups__contains=u'"{}"'.format(group))

def usersWithGroups(queryset, groups):
    """
    Users in all these groups
    """
    q = Q()
    for group in groups:
        q &= Q(preferences__c_groups__contains=u'"{}"'.format(group))
    return queryset.filter(q)

def usersWithOneOfGroups(queryset, groups):
    """
    Users in at least one of these groups
    """
    q = Q()
    for group in groups:
        q |= Q(preferences__c_groups__contains=u'"{}"'.format(group))
    return queryset.filter(q)

def usersWithPermission(queryset, groups, permission):
    """
    Users with this permission
    """
    groups = groupsPerPermission(groups, permission)
    return usersWithOneOfGroups(queryset, groups) if groups else []

def usersWithPermissions(queryset, groups, permissions):
    """
    Users with all these permissions
    """
    # TODO: not working, need to find all the combinations of groups that work then make a query with all these groups
    groups = groupsWithPermissions(groups, permissions)
    return usersWithOneOfGroups(queryset, groups) if groups else []

def usersWithOneOfPermissions(queryset, groups, permissions):
    """
    Users with at least one of these permissions
    """
    groups = groupsWithOneOfPermissions(groups, permissions)
    return usersWithOneOfGroups(queryset, groups) if groups else []

def isBetaTestOnly(
        staff_required, permissions_required, one_of_permissions_required,
):
    """
    Call this after you checked permissions, the person doesn't have permissions,
    but you want to check if they would have permissions if they had beta test access
    """
    if staff_required:
        return False
    if ('beta_test_features' in one_of_permissions_required and
        (not permissions_required or permissions_required == [ 'beta_test_features' ])):
        return True
    if not one_of_permissions_required and permissions_required == [ 'beta_test_features' ]:
        return True
    return False

def isPageBetaTestOnly(page):
    if page.get('check_permissions', None):
        return False
    return isBetaTestOnly(
        page.get('staff_required', False),
        page.get('permissions_required', []),
        page.get('one_of_permissions_required', []),
    )

def isListViewBetaTestOnly(list_view):
    if list_view.has_method_been_overridden('check_permissions', check_collection_level=False):
        return False
    return isBetaTestOnly(
        list_view.staff_required,
        list_view.permissions_required,
        list_view.one_of_permissions_required,
    )

def receivedMessageFromStaffBefore(from_user, to_user):
    return bool(from_user.sent_messages.model.objects.filter(owner=to_user, to_user=from_user).count())

def hasPermissionToMessage(from_user, to_user):
    """
    to_user requires is_followed_by and followed to be added in queryset of to_user.
    The filtering logic for users who can be messaged is in UserFilterForm.filter_queryset.
    """
    # Can't send message to self
    if from_user == to_user:
        return False
    from_user_is_allowed = from_user.hasPermission('message_almost_anyone')
    to_user_is_allowed = to_user.hasPermission('message_almost_anyone')
    # Can't use private messages if reputation is not good enough
    if (not from_user.preferences.has_good_reputation
        or not to_user.preferences.has_good_reputation):
        # Staff can message people without reputation
        # Users can reply to staff who already messaged them
        if (not (from_user_is_allowed
                 or (to_user_is_allowed and receivedMessageFromStaffBefore(from_user, to_user)))):
            return False
    # Do not allow if blocked or blocked by
    if (to_user.id in from_user.preferences.cached_blocked_ids
        or to_user.id in from_user.preferences.cached_blocked_by_ids):
        return False
    # If messages are closed
    if (from_user.preferences.private_message_settings == 'nobody'
        or to_user.preferences.private_message_settings == 'nobody'):
        return False
    # If messages are only open to followed and not followed
    if ((from_user.preferences.private_message_settings == 'follow'
         and not to_user.followed)
        or ((to_user.preferences.private_message_settings == 'follow'
             and not to_user.is_followed_by))):
        # Staff can message users who don't follow them
        # Users can reply to staff who already messaged them
        if (not (from_user_is_allowed
                 or (to_user_is_allowed and receivedMessageFromStaffBefore(from_user, to_user)))):
            return False
    return True

############################################################
# Helpers for MagiCollections

def justReturn(string):
    return lambda *args, **kwargs: string

def lambdaClosure(f, *args, **kwargs):
    return lambda: f(*args, **kwargs)

def propertyFromCollection(property_name):
    def _propertyFromCollection(view):
        return getattr(view.collection, property_name)
    return _propertyFromCollection

"""
Use this to get the standard name for custom templates:
item_template = custom_item_template
"""
custom_item_template = property(lambda view: '{}Item'.format(view.collection.name))

############################################################
# Seasonal helpers

# For direct values (generated settings)

def getAllCurrentSeasons():
    return getattr(django_settings, 'SEASONAL_SETTINGS', {}).keys()

def getValueInSeason(season_name, key, default=None):
    return getattr(django_settings, 'SEASONAL_SETTINGS', {})[season_name].get(key, default)

def isValueInAnyCurrentSeason(key):
    return any(
        season.get(key, None)
        for season in getattr(django_settings, 'SEASONAL_SETTINGS', {}).values()
    )

def getValueInAllCurrentSeasons(key):
    return {
        season_name: season[key]
        for season_name, season in django_settings.SEASONAL_SETTINGS.items()
        if season.get(key, None)
    }

def getRandomValueInCurrentSeasons(key):
    return random.choice(getValueInAllCurrentSeasons(key).values())

# For variables in seasons.py module (will retrieve them from string names, ex: 'getAllArts')

def getVariableInSeason(season_name, key, custom_seasonal_module):
    value = getValueInSeason(season_name, key)
    if not value:
        return None
    return getVariableFromSeasonalModule(key, value, custom_seasonal_module)

def isVariableInAnyCurrentSeason(key):
    return isValueInAnyCurrentSeason(key)

def getVariableFromSeasonalModule(key, variable_name, custom_seasonal_module):
    variable = None
    if custom_seasonal_module:
        variable = getattr(custom_seasonal_module, variable_name, None)
    if not variable:
        try:
            variable = globals()[variable_name]
        except KeyError:
            raise NotImplementedError(
                u'Seasonal {} {} not found in {}/seasons{}.py'.format(
                    key, variable_name, django_settings.SITE,
                    '_context' if key == 'to_context' else ''))
    return variable

def getVariableInAllCurrentSeasons(key, custom_seasonal_module):
    return {
        season_name: getVariableFromSeasonalModule(key, season[key], custom_seasonal_module)
        for season_name, season in django_settings.SEASONAL_SETTINGS.items()
        if season.get(key, None)
    }

def getRandomVariableInCurrentSeasons(key, custom_seasonal_module):
    return getVariableFromSeasonalModule(key, random.choice([
        season
        for season_name, season in django_settings.SEASONAL_SETTINGS.items()
        if season.get(key, None)
    ])[key], custom_seasonal_module)

def checkIsCurrentSeasonNotFromGeneratedSettings(seasons_settings, season_name):
    """seasons_settings = from magi.settings import SEASONS"""
    return season_name in seasons_settings and getEventStatus(
        seasons_settings[season_name]['start_date'], seasons_settings[season_name]['end_date'],
        ends_within=1) in ['current', 'ended_recently']

############################################################
# Context for django requests

def globalContext(request=None, email=False):
    # /!\ Can't be called at global level
    if not request and not email:
        raise NotImplementedError('Request is required to get context.')

    context = RAW_CONTEXT.copy()
    context['ajax'] = isRequestAjax(request)

    if request:
        context['ajax_modal_only'] = context['ajax'] and 'ajax_modal_only' in request.GET
        context['is_authenticated'] = request.user.is_authenticated()
        context['request'] = request
        context['current'] = resolve(request.path_info).url_name
        context['current_url'] = request.get_full_path() + ('?' if request.get_full_path()[-1] == '/' else '&')
        language = request.LANGUAGE_CODE
    else:
        language = get_language()
        context['ajax_modal_only'] = False
        context['is_authenticated'] = False

    if context['is_authenticated']:
        context['is_crawler'] = False
    else:
        context['is_crawler'] = isRequestCrawler(request)

    context['page_title'] = None
    context['current_language'] = language
    context['localized_language'] = LANGUAGES_DICT.get(language, '')
    context['native_language'] = NATIVE_LANGUAGES.get(language, '')
    context['switch_languages_choices'] = NATIVE_LANGUAGES.items()
    context['t_site_name'] = getSiteName()
    context['t_site_image'] = context['site_image_per_language'].get(language, context['site_image'])
    context['t_game_name'] = context['game_name_per_language'].get(language, context['game_name'])
    context['t_full_site_image'] = context['full_site_image_per_language'].get(language, context['full_site_image'])
    context['t_email_image'] = context['email_image_per_language'].get(language, context['email_image'])
    context['t_full_email_image'] = context['full_email_image_per_language'].get(
        language, context['full_email_image'])
    context['js_variables'] = {}

    ############################################################
    # Debug

    if django_settings.DEBUG:
        # Ensures that static assets are always reloaded
        context['static_files_version'] = randomString(20)
        # Don't enforce recaptcha
        if not django_settings.RECAPTCHA_PUBLIC_KEY:
            context['disable_recaptcha'] = True

    ############################################################
    # Only email pages

    if email:
        if context['site_url'].startswith('//'):
            context['site_url'] = 'http:' + context['site_url']
        context['consider_donating_sentence'] = _('If you like {site_name}, please consider donating').format(
            site_name=getSiteName())

    ############################################################
    # Only ajax pages

    elif context['ajax']:
        pass

    ############################################################
    # Only non-ajax pages / non-email

    else:
        context['corner_popups'] = OrderedDict()

        if request:
            context['hidenavbar'] = 'hidenavbar' in request.GET
        context['javascript_translated_terms_json'] = simplejson.dumps(
            { term: unicode(_(term)) for term in context['javascript_translated_terms'] })

        cuteFormFieldsForContext({
            'language': {
                'selector': '#switchLanguage',
                'choices': NATIVE_LANGUAGES.items(),
            },
        }, context)

        # Seasonal
        for season_name, settings in getattr(django_settings, 'SEASONAL_SETTINGS', {}).items():
            for variable, value in settings.items():
                # Context variables to set
                if variable in seasons.CONTEXT_SETTINGS:
                    if variable == 'site_logo':
                        context['site_logo'] = staticImageURL(value)
                        context['full_site_logo'] = staticImageURL(value, full=True)
                    else:
                        context[variable] = value
                # When colors are changed, use a different stylesheet
                elif variable in seasons.CSS_SETTINGS:
                    context['stylesheet'] = season_name
                else:
                    # Add to context manually
                    if variable == 'ajax_callback':
                        if 'ajax_callbacks' not in context:
                            context['ajax_callbacks'] = []
                        context['ajax_callbacks'].append(value)
                    elif variable == 'js_variables':
                        if 'js_variables' not in context:
                            context['js_variables'] = {}
                        context['js_variables'].update(value)
                    # Call function to add more to context
                    elif variable == 'to_context':
                        getVariableFromSeasonalModule(
                            'to_context', value,
                            CUSTOM_SEASONAL_MODULE_FOR_CONTEXT,
                        )(request, context)

        # Corner popups
        if context['is_authenticated']:
            if isBirthdayToday(request.user.preferences.birthdate):
                context['corner_popups'][u'happy_birthday{}'.format(datetime.datetime.today().year)] = {
                    'title': mark_safe(u'<span class="fontx1-5">{} 🎉</span>'.format(_('Happy Birthday'))),
                    'content': mark_safe(u'<p class="fontx1-5">🗓 {}<br>🎂 {}</p>'.format(
                        request.user.preferences.formatted_birthday_date,
                        request.user.preferences.formatted_age,
                    )),
                    'image': context['corner_popup_image'],
                    'image_overflow': context['corner_popup_image_overflow'],
                    'allow_close_once': True,
                    'allow_close_forever': True,
                }
            if request.user.preferences.invalid_email and context['current'] != 'settings':
                context['corner_popups']['invalid_email'] = {
                    'title': _('Your email address is invalid.'),
                    'content': _('Some features might not work properly.'),
                    'buttons': {
                        'settings': {
                            'title': _('Open {thing}').format(thing=_('Settings').lower()),
                            'url': '/settings/#form',
                        },
                    },
                    'image': context['corner_popup_image'],
                    'image_overflow': context['corner_popup_image_overflow'],
                    'allow_close_once': True,
                    'allow_close_remind': 2,
                }

    return context

def getGlobalContext(request):
    if django_settings.GET_GLOBAL_CONTEXT:
        return django_settings.GET_GLOBAL_CONTEXT(request)
    return globalContext(request)

def emailContext():
    return globalContext(email=True)

def isRequestAjax(request):
    if not request:
        return False
    return request.path_info.startswith('/ajax/')

def isRequestCrawler(request):
    if not request or not request.META.get('HTTP_USER_AGENT', None):
        return False
    for known_crawler in KNOWN_CRAWLERS:
        if known_crawler in request.META['HTTP_USER_AGENT']:
            return True
    return False

def getDescriptionFromItem(item):
    description = unicode(item)
    for field_name, is_markdown in [
            ('t_m_description', True),
            ('t_description', False),
            ('m_description', True),
            ('description', False),
    ]:
        description = getattr(item, field_name, None)
        if description:
            if isinstance(description, tuple):
                description = description[1]
            description = (
                simplifyMarkdown if is_markdown else summarize
            )(description, max_length=158)
            break
    return description

def jsonLd(type, content, context=None):
    """
    Types: https://developers.google.com/search/docs/advanced/structured-data/search-gallery
    When context is specified, it just adds it in the context for you
    """
    json_ld = {
        "@context": "https://schema.org",
        "@type": type,
    }
    json_ld.update(content)
    if context:
        if 'json_ld' not in context:
            context['json_ld'] = []
        context['json_ld'].append(json_ld)
    return json_ld

def FAQjsonLd(faq, context=None):
    return jsonLd(
        'FAQPage',
        {
            'mainEntity': [
                {
                    '@type': 'Question',
                    'name': question,
                    'acceptedAnswer': {
                        '@type': 'Answer',
                        'text': answer,
                    }
                } for question, answer in faq
            ],
        },
        context=context,
    )

def getOwnerFromItem(item):
    """
    Returns an object that has at least: username and http_item_url,
    and may have: location
    """
    if modelHasField(type(item), '_cache_owner'):
        return item.cached_owner
    elif hasattr(item, 'cached_owner'):
        return item.cached_owner
    elif modelHasField(type(item), '_cache_owner_username'):
        return AttrDict({
            'username': item.cached_owner_username,
            'http_item_url': u'{}{}/{}/{}/'.format(
                django_settings.SITE_URL, 'user',
                item.owner_id, tourldash(item.cached_owner_username),
            ),
        })
    return item.owner

def articleJsonLd(
        article_title,
        owner,
        images_urls,
        article_type='Article',
        description=None,
        date_published=None,
        date_modified=None,
        keywords=[],
        body=None,
        context=None,
):
    """
    article_type can be: Article, NewsArticle, BlogPosting
    """
    content = {
        'headline': summarize(article_title, max_length=110),
        'author': authorJsonLd(owner),
        'image': images_urls,
    }
    for key, value in {
        'description': description,
        'datePublished': torfc2822(date_published) if date_published else None,
        'dateModified': torfc2822(date_modified) if date_modified else None,
        'keywords': u', '.join([unicode(keyword) for keyword in keywords ]),
        'articleBody': body,
    }.items():
        if value:
            content[key] = value
    return jsonLd(article_type, content, context=context)

def getAddressFromOwner(owner):
    """Owner retrieved by getOwnerFromItem"""
    if hasattr(owner, 'preferences'): # if it's the actual owner instance, or the cached owner has complex hierarchy
        return getattr(owner.preferences, 'location', None)
    elif hasattr(owner, 'preferences_location'): # if it was added in cached_owner manually
        return owner.preferences_location
    return None

def getTwitterFromOwner(owner, with_at=True):
    """Owner retrieved by getOwnerFromItem"""
    twitter = None
    if hasattr(owner, 'preferences'): # if it's the actual owner instance, or the cached owner has complex hierarchy
        twitter = getattr(owner.preferences, 'twitter', None)
    elif hasattr(owner, 'preferences_twitter'): # if it was added in cached_owner manually
        twitter = owner.preferences_twitter
    if twitter and with_at:
        return u'@{}'.format(twitter) if not twitter.startswith('@') else twitter
    elif twitter and not with_at:
        return twitter[1:] if twitter.startswith('@') else twitter
    return twitter

def authorJsonLd(owner):
    author = {
        '@type': 'Person',
        'name': owner.username,
        'url': owner.http_item_url,
    }
    address = getAddressFromOwner(owner)
    if address:
        author['address'] = address
    twitter = getTwitterFromOwner(owner)
    if twitter:
        author['additionalName'] = twitter
    return author

def articleJsonLdFromActivity(activity, context):
    articleJsonLd(
        article_type='NewsArticle' if 'news' in activity.tags else 'BlogPosting',
        article_title=activity.get_title(),
        owner=getOwnerFromItem(activity),
        images_urls=[ image for image in [
            activity.get_first_image(),
        ] if image ],
        description=activity.summarize(),
        date_published=activity.creation,
        date_modified=activity.creation,
        keywords=activity.t_tags.values() + RAW_CONTEXT.get('hashtags', []),
        body=activity.message[1],
        context=context,
    )

def articleJsonLdFromItem(item, body=None, context=None):
    articleJsonLd(
        article_title=unicode(item),
        owner=getOwnerFromItem(item),
        images_urls=[
            staticImageURL(
                getattr(item, 'top_image_item', None)
                or getattr(item, 'top_image', None)
                or getattr(item, 'image_url', None)
            ),
        ],
        description=getDescriptionFromItem(item),
        date_published=getattr(item, 'creation', None),
        date_modified=getattr(item, 'modification', None),
        body=body,
        context=context,
    )

def videoJsonLd(video_url, video_title, video_description, upload_date, context=None):
    return jsonLd(
        'VideoObject',
        {
            'name': video_title,
            'description': video_description,
            'thumbnailUrl': YouTubeVideoField.thumbnail_url(video_url),
            'uploadDate': failSafe(
                lambda: upload_date.isoformat(), exceptions=[ AttributeError ],
                default=(upload_date or 'unknown')),
            'contentUrl': video_url,
            'embedUrl': YouTubeVideoField.embed_url(video_url),
        },
        context=context,
    )

def getAccountIdsFromSession(request):
    # /!\ Can't be called at global level
    if not request.user.is_authenticated():
        return []
    if 'account_ids' not in request.session:
        request.session['account_ids'] = [
            account.id
            for account in RAW_CONTEXT['account_model'].objects.filter(**{
                    RAW_CONTEXT['account_model'].selector_to_owner():
                    request.user
            })
        ]
    return request.session['account_ids']

def getAccountVersionsFromSession(request):
    # /!\ Can't be called at global level
    if not request.user.is_authenticated():
        return []
    if 'account_versions' not in request.session:
        request.session['account_versions'] = [
            getattr(account, 'version', None)
            for account in RAW_CONTEXT['account_model'].objects.filter(**{
                    RAW_CONTEXT['account_model'].selector_to_owner():
                    request.user
            })
        ]
    return request.session['account_versions']

def addCornerPopupToContext(
        context, name, title, content=None, image=None, image_overflow=None, buttons=None,
        allow_close_once=False, allow_close_remind=None, allow_close_forever=False,
):
    """
    buttons is a dict with url, classes, ajax_url, ajax_title, title
    """
    context['corner_popups'][name] = {
        'title': title,
        'content': content,
        'image': image or context['corner_popup_image'],
        'image_overflow': image or context['corner_popup_image_overflow'],
        'allow_close_once': allow_close_once,
        'allow_close_remind': allow_close_remind,
        'allow_close_forever': allow_close_forever,
        'buttons': buttons,
    }

class CuteFormType:
    Images, HTML, YesNo, OnlyNone = range(4)
    to_string = ['images', 'html', 'html', 'html']
    default_to_cuteform = ['key', 'value', 'value', 'value']

class CuteFormTransform:
    No, ImagePath, Flaticon, FlaticonWithText, ImageWithText = range(5)
    default_field_type = [CuteFormType.Images, CuteFormType.Images, CuteFormType.HTML, CuteFormType.HTML, CuteFormType.HTML]

def _callToCuteForm(field_name, model, to_cuteform, key, value):
    if to_cuteform == 'key':
        return key
    elif to_cuteform == 'value':
        return value
    if (field_name.startswith('i_') # i_choices
        and to_cuteform.func_code.co_argcount == 3): # to_cuteform takes 3 arguments
        if not model:
            raise ValueError('When to_cuteform takes 3 arguments, it\'s required to specify the model class.')
        return to_cuteform(key, model.get_reverse_i(field_name[2:], key), value)
    return to_cuteform(key, value)

def cuteFormFieldsForContext(cuteform_fields, context, form=None, prefix=None, ajax=False, model=None):
    """
    Adds the necesary context to call cuteform in javascript.
    Prefix is a prefix to add to all selectors. Can be useful to isolate your cuteform within areas of your page.
    cuteform_fields: must be a dictionary of {
      field_name: {
        type: CuteFormType.Images, .HTML, .YesNo or .OnlyNone, will be images if not specified,
        to_cuteform: 'key' or 'value' or lambda that takes key and value, will be 'key' if not specified, Can also take i, key, value if i_choice
        choices: list of pair, if not specified will use form
        selector: will be #id_{field_name} if not specified,
        transform: when to_cuteform is a lambda: CuteFormTransform.No, .ImagePath, .Flaticon, .FlaticonWithText, .ImageWithText
        image_folder: only when to_cuteform = 'images' or transform = 'images', will specify the images path,
        extra_settings: dictionary of options passed to cuteform,
    }
    """
    if not cuteform_fields:
        return
    if form and not model:
        model = failSafe(lambda: getattr(form.Meta, 'model', None), exceptions=[ AttributeError ])
    if 'cuteform_fields' not in context:
        context['cuteform_fields'] = {}
        context['cuteform_fields_json'] = {}

    empty = context['full_empty_image']
    empty_image = u'<img src="{}" class="empty-image">'.format(empty)

    for field_name, field in cuteform_fields.items():
        transform = field.get('transform', CuteFormTransform.No)
        field_type = field.get('type', CuteFormTransform.default_field_type[transform])
        if 'selector' not in field:
            field['selector'] = '#id_{}'.format(field_name)
        if 'to_cuteform' not in field:
            field['to_cuteform'] = CuteFormType.default_to_cuteform[field_type]

        # Check if hidden
        if (form and field_name in form.fields
            and isinstance(form.fields[field_name].widget, HiddenInput)):
            continue
        # Get choices
        choices = field.get('choices', None)
        if choices is None and form and field_name in form.fields:
            if hasattr(form.fields[field_name], 'queryset'):
                choices = BLANK_CHOICE_DASH + list(form.fields[field_name].queryset)
            elif hasattr(form.fields[field_name], 'choices'):
                choices = form.fields[field_name].choices
        if choices == []:
            choices = BLANK_CHOICE_DASH
        if choices and field_type in [CuteFormType.YesNo, CuteFormType.OnlyNone]:
            transform = CuteFormTransform.FlaticonWithText
        if not choices and field_type in [CuteFormType.YesNo, CuteFormType.OnlyNone]:
            true = u'<i class="flaticon-checked"></i> {}'.format(
                _('Yes') if field_type == CuteFormType.YesNo else _('Only'),
            )
            false = u'<i class="flaticon-delete"></i> {}'.format(
                _('No') if field_type == CuteFormType.YesNo else _('None'),
            )
            if not form or field_name not in form or isinstance(form.fields[field_name], NullBooleanField):
                choices = [
                    ('1', empty_image),
                    ('2', true),
                    ('3', false),
                ]
            else:
                choices = [
                    ('0', true),
                    ('1', false),
                ]
        if not choices:
            continue
        selector = u'{}{}'.format((prefix if prefix else ''), field['selector'])
        # Initialize cuteform dict for field
        context['cuteform_fields'][selector] = {
            CuteFormType.to_string[field_type]: {},
        }
        # Add title if any
        if 'title' in field:
            context['cuteform_fields'][selector]['title'] = _(u'Select {}').format(unicode(field['title']).lower())
        # Add extra settings if any
        if 'extra_settings' in field:
            context['cuteform_fields'][selector].update(field['extra_settings'] if not ajax else {
                k:v for k, v in field['extra_settings'].items()
                if 'modal' not in k })
        for choice in choices:
            key, value = choice if isinstance(choice, tuple) else (choice.pk, choice)
            if key == '':
                cuteform = empty if field_type == CuteFormType.Images else empty_image
            else:
                # Get the cuteform value with to_cuteform
                cuteform_value = _callToCuteForm(field_name, model, field['to_cuteform'], key, value)
                # Transform to image path
                if (field_type == CuteFormType.Images
                    and (field['to_cuteform'] in ['key', 'value']
                         or transform == CuteFormTransform.ImagePath)):
                    if field_name.startswith('i_') or field_name.startswith('c_') or field_name.startswith('d_'):
                        new_field_name = field_name[2:]
                    else:
                        new_field_name = field_name
                    if model and getattr(model, u'{}_AUTO_IMAGES'.format(new_field_name.upper()), False):
                        cuteform = model.get_auto_image(new_field_name, failSafe(
                            lambda: model.get_reverse_i(new_field_name, key), exceptions=[ KeyError ], default=key),
                            original_field_name=field_name,
                        )
                    else:
                        cuteform = staticImageURL(
                            unicode(cuteform_value),
                            folder=field.get('image_folder', field_name),
                        )
                # Transform to flaticon
                elif transform in [CuteFormTransform.Flaticon, CuteFormTransform.FlaticonWithText]:
                    cuteform = u'<i class="flaticon-{icon}"></i>{text}'.format(
                        icon=cuteform_value,
                        text=u' {}'.format(value) if transform == CuteFormTransform.FlaticonWithText else '',
                    )
                    if transform == CuteFormTransform.Flaticon:
                        cuteform = u'<div data-toggle="tooltip" data-placement="top" data-trigger="hover" data-html="true" title="{}">{}</div>'.format(value, cuteform)
                # Transform to image with text
                elif transform == CuteFormTransform.ImageWithText:
                    cuteform = u'<img src="{img}"> {text}'.format(
                        img=staticImageURL(
                            unicode(cuteform_value),
                            folder=field.get('image_folder', field_name),
                        ),
                        text=u' {}'.format(value) if transform == CuteFormTransform.FlaticonWithText else '',
                    )
                else:
                    cuteform = unicode(cuteform_value)
            # Add in key, value in context for field
            context['cuteform_fields'][selector][CuteFormType.to_string[field_type]][key] = cuteform

        # Store a JSON version to be displayed in Javascript
        context['cuteform_fields_json'][selector] = simplejson.dumps(context['cuteform_fields'][selector])

def _auto_images_to_cuteform(model, new_field_name, original_field_name):
    return lambda key, value: model.get_auto_image(
        new_field_name, failSafe(lambda: model.get_reverse_i(
            new_field_name, key), exceptions=[ KeyError ], default=key),
        original_field_name=original_field_name,
    )
def mergedFieldCuteForm(
        cuteform, settings={},
        merged_fields={}, merged_field_name=None,
        model=None, as_modal=False, add_to_cuteform=True,
):
    if not merged_fields:
        return
    if not isinstance(merged_fields, dict):
        merged_fields = OrderedDict([(field_name, None) for field_name in merged_fields])
    if not merged_field_name:
        merged_field_name = '_'.join(merged_fields.keys())
    if as_modal:
        settings = mergeDicts(settings, {
            'extra_settings': {
                'modal': 'true',
                'modal-text': 'true',
            },
        })
    to_cuteforms = {}
    for field_name, to_cuteform in merged_fields.items():
        if not to_cuteform:
            to_cuteform = cuteform.get(field_name, {}).get('to_cuteform', None)
        if not to_cuteform:
            if field_name.startswith('i_') or field_name.startswith('c_') or field_name.startswith('d_'):
                new_field_name = field_name[2:]
            else:
                new_field_name = field_name
            if model and getattr(model, u'{}_AUTO_IMAGES'.format(new_field_name.upper()), False):
                to_cuteform = _auto_images_to_cuteform(model, new_field_name, field_name)
        if not to_cuteform:
            to_cuteform = settings.get('to_cuteform', CuteFormType.default_to_cuteform[
                settings.get('type', CuteFormTransform.default_field_type[
                    settings.get('transform', CuteFormTransform.No)
                ])
            ])
        to_cuteforms[field_name] = to_cuteform

    def _to_cuteform(k, v):
        for field_name, to_cuteform in to_cuteforms.items():
            if k.startswith(field_name):
                k = k[len(field_name) + 1:]
                return _callToCuteForm(
                    field_name, model,
                    to_cuteform,
                    int(k) if field_name.startswith('i_') and k.isdecimal() else k, v,
                )
    settings['to_cuteform'] = _to_cuteform
    if add_to_cuteform:
        cuteform[merged_field_name] = settings
    return (merged_field_name, settings)

class FormShowMore:
    def __init__(
            self,
            cutoff,
            including_cutoff=False,
            until=None,
            including_until=False,
            message_more=_('More'),
            message_less=_('Less'),
            check_values=True,
    ):
        self.cutoff = cutoff
        self.until = until
        self.including_cutoff = including_cutoff
        self.including_until = including_until
        self.message_more = message_more
        self.message_less = message_less
        self.check_values = check_values

def setJavascriptFormContext(form, form_selector, context, cuteforms, ajax):
    # CuteForm
    cuteform = dict(getattr(form, 'cuteform', {}).items())
    for a_cuteform in cuteforms:
        if a_cuteform:
            cuteform.update(a_cuteform)
    if cuteform:
        cuteFormFieldsForContext(
            cuteform,
            context, form=form,
            prefix=form_selector + ' ',
            ajax=ajax,
        )
    # Modal cuteform separators
    modal_cuteform_separators = getattr(form, 'modal_cuteform_separators', None)
    if modal_cuteform_separators:
        if 'modal_cuteform_separators' not in context:
            context['modal_cuteform_separators'] = {}
        if form_selector not in context['modal_cuteform_separators']:
            context['modal_cuteform_separators'][form_selector] = []
        context['modal_cuteform_separators'][form_selector].append(modal_cuteform_separators)
    # Show more
    form_show_more = getattr(form, 'show_more', None)
    if form_show_more:
        if 'form_show_more' not in context:
            context['form_show_more'] = {}
        if form_selector not in context['form_show_more']:
            context['form_show_more'][form_selector] = []
        context['form_show_more'][form_selector] += (
            [form_show_more] if not isinstance(form_show_more, list) else form_show_more
        )
    # On change value show
    on_change_value_show = getattr(form, 'get_on_change_value_show', lambda: {})()
    if on_change_value_show:
        if 'form_on_change_value_show' not in context:
            context['form_on_change_value_show'] = {}
        if form_selector not in context['form_on_change_value_show']:
            context['form_on_change_value_show'][form_selector] = {}
        context['form_on_change_value_show'][form_selector].update(on_change_value_show)
    # On change value trigger
    on_change_value_trigger = getattr(form, 'get_on_change_value_trigger', lambda: {})()
    if on_change_value_trigger:
        if 'form_on_change_value_trigger' not in context:
            context['form_on_change_value_trigger'] = {}
        if form_selector not in context['form_on_change_value_trigger']:
            context['form_on_change_value_trigger'][form_selector] = {}
        context['form_on_change_value_trigger'][form_selector].update(on_change_value_trigger)
    # Collectible variables
    collectible_variables = getattr(form, 'collectible_variables', {})
    if collectible_variables:
        if 'js_variables' not in context:
            context['js_variables'] = {}
        context['js_variables']['collectible_variables'] = collectible_variables

def filterRealAccounts(queryset):
    if modelHasField(queryset.model, 'is_playground'):
        queryset = queryset.exclude(is_playground=True)
    if modelHasField(queryset.model, 'is_hidden_from_leaderboard'):
        queryset = queryset.exclude(is_hidden_from_leaderboard=True)
    return queryset

def filterRealCollectiblesPerAccount(queryset):
    if modelHasField(queryset.model.account.field.rel.to, 'is_playground'):
        queryset = queryset.exclude(account__is_playground=True)
    if modelHasField(queryset.model.account.field.rel.to, 'is_hidden_from_leaderboard'):
        queryset = queryset.exclude(account__is_hidden_from_leaderboard=True)
    return queryset

############################################################
# Database upload to

class _uploadToBase(object):
    def __init__(self, prefix, length=6, limit=100):
        self.prefix = prefix
        self.length = length
        self.limit = limit

    def __call__(self, instance, filename):
        name, extension = os.path.splitext(filename)
        if not extension:
            extension = '.png'
        prefix = u''.join([
            RAW_CONTEXT['static_uploaded_files_prefix'],
            self.prefix,
        ]) + u'/'
        suffix = extension
        name = self.get_name(
            instance, filename,
            getattr(self, 'limit', 100) - len(prefix) - len(suffix) - 1,
        )
        return u'{}{}{}'.format(prefix, name, suffix)

@deconstructible
class uploadToKeepName(_uploadToBase):
    def get_name(self, instance, filename, limit_to):
        return u'{}{}'.format(
            filename[:(limit_to - self.length)],
            randomString(self.length),
        )

@deconstructible
class uploadToRandom(_uploadToBase):
    def __init__(self, prefix, length=30, *args, **kwargs):
        super(uploadToRandom, self).__init__(prefix, length=length, *args, **kwargs)

    def get_name(self, instance, filename, limit_to):
        return randomString(self.length)[:limit_to]

@deconstructible
class uploadItem(_uploadToBase):
    def get_name(self, instance, filename, limit_to):
        id = unicode(instance.pk if instance.pk else randomString(6))
        return u'{id}{string}-{random}'.format(
            id=id,
            string=tourldash(unicode(instance))[:(limit_to - len(id) - self.length)],
            random=randomString(self.length),
        )

@deconstructible
class uploadThumb(uploadItem):
    def __init__(self, prefix, *args, **kwargs):
        super(uploadThumb, self).__init__(
            prefix + ('thumb' if prefix.endswith('/') else '/thumb'),
            *args, **kwargs
        )

@deconstructible
class uploadTthumb(uploadItem):
    def __init__(self, prefix, *args, **kwargs):
        super(uploadTthumb, self).__init__(
            prefix + ('tthumb' if prefix.endswith('/') else '/tthumb'),
            *args, **kwargs
        )

@deconstructible
class uploadTiny(uploadItem):
    def __init__(self, prefix, *args, **kwargs):
        super(uploadTiny, self).__init__(
            prefix + ('tiny' if prefix.endswith('/') else '/tiny'),
            *args, **kwargs
        )

@deconstructible
class upload2x(uploadItem):
    def __init__(self, prefix, *args, **kwargs):
        super(upload2x, self).__init__(
            prefix + ('2x' if prefix.endswith('/') else '/2x'),
            *args, **kwargs
        )

############################################################
# Get MagiCollection(s)

def getMagiCollections():
    # /!\ Can't be called at global level
    try:
        return RAW_CONTEXT['magicollections']
    except KeyError:
        return []

def getMagiCollection(collection_name):
    # /!\ Can't be called at global level
    """
    May return None if called before the magicollections have been initialized
    """
    if collection_name and 'magicollections' in RAW_CONTEXT and collection_name in RAW_CONTEXT['magicollections']:
        return RAW_CONTEXT['magicollections'][collection_name]
    return None

def getMagiCollectionFromModelName(model_name):
    # /!\ Can't be called at global level
    for collection in getMagiCollections().values():
        if collection.model_name == model_name:
            return collection

def getMagiCollectionFromModel(model):
    # /!\ Can't be called at global level
    if not model:
        return None
    collection_name = getattr(model, 'collection_name', None)
    if collection_name:
        collection = getMagiCollection(collection_name)
        if collection:
            return collection
    return None

def makeCollectionCommunity(collection):
    """
    Takes a collection that either inherits from MainItemCollection or MagiCollection
    and sets default settings for collections expected to be filled by the community
    """
    class _CommunityCollection(collection):
        blockable = False
        reportable = True
        allow_suggest_edit = True
        allow_html_in_markdown = False
        auto_share_image = True

        class ItemView(collection.ItemView):
            show_suggest_edit_button = True
            share_templates = True

            @property
            def show_owner(self):
                return self.template == 'default'

            @property
            def show_faq(self):
                return self.template == 'default'

            @property
            def show_article_ld(self):
                return self.template == 'default'

        class AddView(collection.AddView):
            staff_required = False
            permissions_required = []
            max_per_user_per_day = 30

        class EditView(collection.EditView):
            staff_required = False
            permissions_required = []
            owner_only_or_permissions_required = [ 'manage_main_items' ]
            allow_delete = True
    return _CommunityCollection

############################################################
# Date to RFC 2822 format

def torfc2822(date):
    return date.strftime("%B %d, %Y %H:%M:%S %z")

def dateToMarkdownCompatibleTag(date):
    return date.strftime('%Y-%m-%dT%H:%M:%S')

def localizeTimeOnly(time):
    """
    Format: hh:mm:ss or hh:mm
    Will not change the time but will display it differently based on localization.
    Ex: ‘en’ will show ‘3 p.m’, ‘it’ will show ’15:00:00`, `ko` will show `오후 3:00:00`
    """
    parts = time.split(':')
    return date_format(timezone.now().replace(
        hour=int(parts[0]), minute=int(parts[1]), second=int(getIndex(parts, 2, 0)),
    ), format='TIME_FORMAT', use_l10n=True)

############################################################
# Birthday utils

def birthdays_within(days_after, days_before=0, field_name='birthday'):
    now = timezone.now()
    after = now - datetime.timedelta(days=days_before)
    before = now + datetime.timedelta(days=days_after)

    monthdays = [(now.month, now.day)]
    while after <= before:
        monthdays.append((after.month, after.day))
        after += datetime.timedelta(days=1)

    # Tranform each into queryset keyword args.
    monthdays = (dict(zip((
        u'{}__month'.format(field_name),
        u'{}__day'.format(field_name),
    ), t)) for t in monthdays)

    # Compose the djano.db.models.Q objects together for a single query.
    return reduce(operator.or_, (Q(**d) for d in monthdays))

def isBirthdayToday(date):
    if not date:
        return False
    today = datetime.date.today()
    return (
        today.day == date.day
        and today.month == date.month
    )

def getNextBirthday(date):
    today = datetime.date.today()
    birthday = date

    is_feb29 = False
    if birthday.month == 2 and birthday.day == 29:
        is_feb29 = True
        birthday = birthday.replace(
            month=date.month + 1,
            day=1,
        )

    birthday = birthday.replace(year=today.year)
    if birthday < today:
        birthday = birthday.replace(year=today.year + 1)

    if is_feb29:
        try: birthday = birthday.replace(month=2, day=29)
        except ValueError: pass
    return birthday

def birthdayURL(user):
    if not user.preferences.birthdate:
        return None
    return 'https://www.timeanddate.com/countdown/birthday?iso={date}T00&msg={username}%27s+birthday'.format(
        date=dateformat.format(getNextBirthday(user.preferences.birthdate), "Ymd"),
        username=user.username,
    )

def getAge(birthdate, formatted=False):
    if not birthdate:
        return None
    if isinstance(birthdate, str) or isinstance(birthdate, unicode):
        birthdate = parse_date(birthdate)
    today = datetime.date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    if formatted:
        return _(u'{age} years old').format(age=age)
    return age

def birthdayOrderingQueryset(queryset, field_name='birthday', order_by=True):
    queryset = queryset.extra(select={
        '{field_name}_month'.format(field_name=field_name):
        'strftime("%m", {field_name})'.format(field_name=field_name),
        '{field_name}_day'.format(field_name=field_name):
        'strftime("%d", {field_name})'.format(field_name=field_name),
    } if connection.vendor == 'sqlite' else {
        '{field_name}_month'.format(field_name=field_name):
        'MONTH({field_name})'.format(field_name=field_name),
        '{field_name}_day'.format(field_name=field_name):
        'DAY({field_name})'.format(field_name=field_name),
    })
    if order_by:
        queryset = queryset.order_by('birthday_month', 'birthday_day')
    return queryset

ASTROLOGICAL_SIGN_CHOICES = (
    ('leo', _('Leo')),
    ('aries', _('Aries')),
    ('libra', _('Libra')),
    ('virgo', _('Virgo')),
    ('scorpio', _('Scorpio')),
    ('capricorn', _('Capricorn')),
    ('pisces', _('Pisces')),
    ('gemini', _('Gemini')),
    ('cancer', _('Cancer')),
    ('sagittarius', _('Sagittarius')),
    ('aquarius', _('Aquarius')),
    ('taurus', _('Taurus')),
)

ASTROLOGICAL_SIGNS = [
    ((12, 22), 'capricorn'),
    ((11, 22), 'sagittarius'),
    ((10, 23), 'scorpio'),
    ((9, 23), 'libra'),
    ((8, 23), 'virgo'),
    ((7, 23), 'leo'),
    ((6, 21), 'cancer'),
    ((5, 21), 'gemini'),
    ((4, 20), 'taurus'),
    ((3, 20), 'aries'),
    ((2, 18), 'pisces'),
    ((1, 20), 'aquarius'),
    ((1, 1), 'capricorn'),
]

def getAstrologicalSign(month, day):
    for (start_month, start_day), sign in ASTROLOGICAL_SIGNS:
        if (month > start_month
            or (month == start_month and day >= start_day)):
            return sign
    return None

def reverseOrdering(ordering_fields):
    return [
        field_name[1:] if field_name.startswith('-') else u'-' + field_name
        for field_name in ordering_fields
    ]

def reverseOrderingString(ordering):
    return u','.join(reverseOrdering(ordering.split(',')))

def plainOrdering(ordering_fields):
    return [
        field_name[1:] if field_name.startswith('-') else field_name
        for field_name in ordering_fields
    ]

############################################################
# Event status using start and end date

def addYearToEventWithoutYear(start_date=None, end_date=None, return_have_year=False):
    """
    May raise ValueError on invalid dates formatting
    Allowed formats for strings: YYYY-MM-DD or MM-DD
    """
    # Fix None dates
    if not start_date and not end_date:
        if return_have_year:
            return None, None, [False, False]
        return None, None
    elif not start_date:
        start_date = end_date
    elif not end_date:
        end_date = start_date

    # Transform strings to dates
    if isinstance(start_date, basestring):
        try:
            start_date = pytz.utc.localize(datetime.datetime.strptime(start_date, '%Y-%m-%d'))
        except ValueError:
            start_date = datetime.datetime.strptime(start_date, '%m-%d')
            start_date = (start_date.month, start_date.day)
    if isinstance(end_date, basestring):
        try:
            end_date = pytz.utc.localize(datetime.datetime.strptime(end_date, '%Y-%m-%d'))
        except ValueError:
            end_date = datetime.datetime.strptime(end_date, '%m-%d')
            end_date = (end_date.month, end_date.day)

    now = timezone.now()
    tuples_have_year = [True, True]

    # Transform tuples to dates
    if isinstance(start_date, tuple):
        if len(start_date) == 3:
            start_date = datetime.datetime(start_date[0], start_date[1], start_date[2], tzinfo=timezone.utc)
        else:
            tuples_have_year[0] = False
            start_date = datetime.datetime(now.year, start_date[0], start_date[1], tzinfo=timezone.utc)
    if isinstance(end_date, tuple):
        if len(end_date) == 3:
            end_date = datetime.datetime(end_date[0], end_date[1], end_date[2], tzinfo=timezone.utc)
        else:
            tuples_have_year[1] = False
            end_date = datetime.datetime(now.year, end_date[0], end_date[1], tzinfo=timezone.utc)
        # If no year specified, auto fix order
        if tuples_have_year == [False, False] and start_date > end_date:
            end_date = end_date.replace(now.year + 1)

    if return_have_year:
        return start_date, end_date, tuples_have_year
    return start_date, end_date

def getEventStatus(start_date=None, end_date=None, ends_within=0, starts_within=0, without_year_return=None):
    """
    start_date and end_date need to be a datetime object or a tuple (month, day) or (year, month, day)

    Possible values:
    - If all parameters specified: [invalid, future, starts_soon, current, ended_recently, ended]
    - If all but end_date specified: All except current and invalid
    - If start_date and end_date specified: [invalid, future, current, ended]
    - If only start_date: [future, ended]
    """
    now = timezone.now()
    if type(start_date) == datetime.date:
        start_date = datetime.datetime.combine(start_date, now.time()).replace(tzinfo=timezone.utc)
    if type(end_date) == datetime.date:
        end_date = datetime.datetime.combine(end_date, now.time()).replace(tzinfo=timezone.utc)
    start_date, end_date, tuples_have_year = addYearToEventWithoutYear(
        start_date, end_date, return_have_year=True)
    if not start_date and not end_date:
        return 'invalid'
    without_year = tuples_have_year == [False, False]

    # Return status
    if start_date > end_date:
        return 'invalid'
    if now < (start_date - relativedelta(days=starts_within)):
        if without_year and without_year_return is not None:
            return without_year_return
        return 'future'
    elif now < start_date:
        return 'starts_soon'
    elif now < end_date:
        return 'current'
    elif now < (end_date + relativedelta(days=ends_within)):
        return 'ended_recently'
    if without_year and without_year_return is not None:
        return without_year_return
    return 'ended'

def filterEventsByStatus(queryset, status, prefix=''):
    if status == 'all':
        return queryset
    now = timezone.now()
    if status == 'ended':
        return queryset.filter(**{
            u'{}end_date__lt'.format(prefix): now,
        })
    elif status == 'current':
        return queryset.filter(**{
            u'{}start_date__lte'.format(prefix): now,
            u'{}end_date__gte'.format(prefix): now,
        })
    elif status == 'future':
        return queryset.filter(**{
            u'{}start_date__gt'.format(prefix): now,
        })
    return queryset

def getCurrentEvents(queryset, prefix='', ends_within=0, starts_within=0, start_field_name='start_date', end_field_name='end_date'):
    now = timezone.now()
    return queryset.filter(**{
        u'{}{}__lte'.format(prefix, start_field_name): now - relativedelta(days=starts_within),
        u'{}{}__gte'.format(prefix, end_field_name): now + relativedelta(days=ends_within),
    })

############################################################
# Send email

def send_email(subject, template_name, to=[], context=None, from_email=django_settings.AWS_SES_RETURN_PATH):
    if 'template_name' != 'notification':
        to.append(django_settings.LOG_EMAIL)
    subject = subject.replace('\n', '').replace('\r', '')
    if not context:
        context = emailContext()
    context = Context(context)
    plaintext = get_template('emails/' + template_name + '.txt').render(context)
    htmly = get_template('emails/' + template_name + '.html').render(context)
    email = EmailMultiAlternatives(subject, plaintext, from_email, to)
    email.attach_alternative(htmly, "text/html")
    email.send()

############################################################
# Various string/int/list tools

def failSafe(f, exceptions=None, default=None, log_exception=False, log_print=None):
    if exceptions is not None:
        try:
            return f()
        except tuple(exceptions):
            if django_settings.DEBUG and log_exception:
                import traceback
                traceback.print_exc()
            if django_settings.DEBUG and log_print:
                print log_print
            return default
    try:
        return f()
    except:
        if django_settings.DEBUG and log_exception:
            import traceback
            traceback.print_exc()
        if django_settings.DEBUG and log_print:
            print log_print
        return default

def recursiveCall(values, original_value, f):
    """
    Goes through a list of values and applies f to each.
    f takes the result value (original_value, then result of previous f)
    and the current value from the list.
    """
    if not values:
        return original_value
    return recursiveCall(values[1:], f(original_value, values[0]), f)

def randomString(length, choice=(string.ascii_letters + string.digits)):
    return ''.join(random.SystemRandom().choice(choice) for _ in range(length))

def isAscii(string):
    return all(ord(c) < 128 for c in string)

def getMedalImage(nth):
    return staticImageURL(u'medal{}'.format(4 - nth), folder='badges') if nth < 4 else None

def tourldash(string, separator=u'-'):
    separator = unicode(separator)
    if not string:
        return ''
    s =  u''.join(e if e.isalnum() else separator for e in string)
    return separator.join([s for s in s.split(separator) if s])[:MAX_URL_LENGTH]

def notTranslatedWarning(string):
    if string and isinstance(string, basestring) and django_settings.DEBUG:
        return u'❌🌏 {}'.format(string)
    return string

def toHumanReadable(string, capitalize=True, warning=False):
    """
    When warning is True, it will show a warning in DEBUG mode to help
    developers know it's not translated
    """
    string = string.lower().replace('_', ' ').replace('-', ' ').strip()
    if warning:
        string = notTranslatedWarning(string)
    if capitalize:
        return string.capitalize()
    return string

def getTranslation(term, language):
    """
    term accepts callable
    """
    if term is None:
        return None
    if language == 'en' and hasattr(term, '_proxy____args'):
        return term._proxy____args[0]
    old_lang = get_language()
    if old_lang != language:
        translation_activate(language)
    translation = unicode(term(language)) if callable(term) else unicode(term)
    if old_lang != language:
        translation_activate(old_lang)
    return translation

def getEnglish(term):
    return getTranslation(term, 'en')

def getAllTranslations(term, unique=False, include_en=True):
    translations = {}
    old_lang = get_language()
    for lang in LANGUAGES_DICT.keys():
        if not include_en and lang == 'en':
            continue
        translation_activate(lang)
        translations[lang] = unicode(term(lang)) if callable(term) else unicode(term)
    if unique:
        if include_en:
            en_translation = translations['en']
        else:
            translation_activate('en')
            en_translation = unicode(term(lang)) if callable(term) else unicode(term)
    translation_activate(old_lang)
    if unique:
        translations = {
            language: value
            for language, value in translations.items()
            if language == 'en' or en_translation != value
        }
    return translations

def spaceOutCode(code, block_size=2):
    code = unicode(code).replace(' ', '')
    return ' '.join(code[i:i + block_size] for i in range(0, len(code), block_size))

def getAllTranslationsOfModelField(item, field_name='name', unique=False):
    return getAllTranslations(
        lambda language: item.get_translation_from_dict(field_name, language=language),
        unique=unique,
    )

class LazyEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)
        return super(LazyEncoder, self).default(obj)

def jsv(v):
    if isinstance(v, list) or isinstance(v, dict):
        return mark_safe(json.dumps(v, cls=LazyEncoder).replace('"True"', '"true"').replace('"False"', '"false"'))
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, str) or isinstance(v, unicode):
        return mark_safe(u'"{}"'.format(v))
    return v

def templateVariables(string):
    return [x[1] for x in string._formatter_parser() if x[1]]

def validateTemplate(template, valid_variables, raise_error=True, raise_error_on_field_name=None):
    if template:
        variables = templateVariables(template)
        unknown_variables = [
            variable for variable in variables
            if variable not in valid_variables
        ]
        if unknown_variables:
            if raise_error:
                error = 'Unknown variables: {}'.format(andJoin(unknown_variables))
                if raise_error_on_field_name:
                    raise ValidationError({ raise_error_on_field_name: [ error ] })
                raise ValidationError(error)
            return unknown_variables
    return True

def oldStyleTemplateVariables(string):
    return [ s for s in [ s.split(')s')[0] if ')s' in s else None for s in  string.split('%(')[1:] ] if s ]

def snakeToCamelCase(string):
    return ''.join(x.capitalize() or '_' for x in string.split('_'))

def titleToSnakeCase(string):
    return string.lower().replace(' ', '_')

def snakeCaseToTitle(string):
    return string.replace('_', ' ').title()

def camelToSnakeCase(string, upper=False):
    string = re.sub(
        '([a-z0-9])([A-Z])', r'\1_\2',
        re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)
    )
    return string.upper() if upper else string.lower()

def chainedReplace(string, replace_dict, reverse=False):
    new_string = string
    for replace_this, with_that in replace_dict.items():
        if reverse:
            new_string = new_string.replace(with_that, replace_this)
        else:
            new_string = new_string.replace(replace_this, with_that)
    return new_string

def hexToRGB(hex_color):
    """
    Converts an hex color string (ex: #FFFFFF) to a RGB color tuple (ex: (255, 255, 255))
    """
    return tuple(int(hex_color[1:][i:i+2], 16) for i in (0, 2, 4))

def RGBToHex(rgb):
    """
    Converts a RGB color tuple (ex: (255, 255, 255)) to an hex color string (ex: #FFFFFF)
    """
    return '#%02x%02x%02x' % rgb

def hilo(a, b, c):
    # Sum of the min & max of (a, b, c)
    if c < b: b, c = c, b
    if b < a: a, b = b, a
    if c < b: b, c = c, b
    return a + c

def cmToInches(cm):
    return cm / 2.54

def cmToHumanReadable(cm, return_list=False, cm_only=False):
    if cm_only:
        return u'{}cm'.format(cm)
    if cm < 0:
        cm = cm * -1
        is_negative = True
    else:
        is_negative = False
    values = []
    for unit, cm_per_unit in [
            ('km', 100000),
            ('m', 100),
            ('cm', 1),
    ]:
        value = int(math.floor(cm / cm_per_unit))
        if value != 0:
            values.append((value, unit))
        cm = cm - (value * cm_per_unit)
    if return_list:
        return (is_negative, values)
    return (
        (u'-' if is_negative else u'')
        + (u' '.join([ u'{}{}'.format(value, unit) for value, unit in values ]))
    )

def inchesToHumanReadable(inches=None, cm=None, return_list=False, inches_only=False):
    if cm is not None and inches is None:
        inches = cmToInches(cm)
    if inches_only:
        return u'{}"'.format(int(round(inches)))
    if inches < 0:
        inches = inches * -1
        is_negative = True
    else:
        is_negative = False
    values = []
    use_short_units = True
    for unit, short_unit, inches_per_unit in [
            ('mi', None, 63360),
            ('ft', '\'', 12),
            ('in', '"', 1),
    ]:
        value = int(math.floor(inches / inches_per_unit))
        if unit == 'mi' and value:
            use_short_units = False
        if value != 0:
            values.append((value, short_unit if use_short_units else unit))
        inches = int(inches - (value * inches_per_unit))
    if return_list:
        return (is_negative, values)
    return (
        (u'-' if is_negative else u'')
        + (u'' if use_short_units else u' ').join([ u'{}{}'.format(value, unit) for value, unit in values ])
    )

def secondsToHumanReadable(seconds, return_list=False):
    if seconds is None:
        return None
    if seconds < 0:
        seconds = seconds * -1
        is_negative = True
    else:
        is_negative = False
    values = []
    for unit, seconds_per_unit in [
            (_('days'), 86400),
            (_('hours'), 3600),
            (_('minutes'), 60),
            (_('seconds'), 1),
    ]:
        value = int(math.floor(seconds / seconds_per_unit))
        if value != 0:
            values.append((value, unit))
        seconds = seconds - (value * seconds_per_unit)
    if return_list:
        return (is_negative, values)
    return u' '.join([ u'{} {}'.format(value, unit) for value, unit in values ])

def complementaryColor(hex_color=None, rgb=None):
    if hex_color:
        r, g, b = hexToRGB(hex_color)
    else:
        r, g, b = rgb
    k = hilo(r, g, b)
    new_rgb = tuple(k - u for u in (r, g, b))
    if hex_color:
        return RGBToHex(new_rgb)
    return new_rgb

def listUnique(list, remove_empty=False):
    """remove_empty will call hasValue and skip"""
    return OrderedDict([(item, None) for item in list if not remove_empty or hasValue(item)]).keys()

class MagiQueryDict(object):
    """
    Wrapper around QueryDict
    On init, querydict is request.GET
    To pass the querydict to a form, make sure you use .querydict
    """
    def __init__(self, querydict):
        self.querydict = querydict

    def get(self, key, default=None, as_list=False):
        """when as_list=False, only returns the first specified value (if multiple specified)"""
        try: values = self.querydict.getlist(key) # for QueryDict
        except AttributeError: values = [ self.querydict[key] ] # for dict
        if key.startswith('c_'):
            if not values:
                return values
            elif isinstance(values[0], list):
                if as_list:
                    return values
                else:
                    return values[0]
            else:
                return values
        if as_list:
            return values
        if not values:
            return default
        return values[0]

    def getlist(self, key):
        return self.get(key, as_list=True)

    def only_form_filters(self, collection, include_handled_outside=False, include_view=False):
        form_filters = []
        for key in self.keys():
            if key in GET_PARAMETERS_NOT_IN_FORM:
                continue
            if (not include_handled_outside
                and key in GET_PARAMETERS_IN_FORM_HANDLED_OUTSIDE):
                continue
            if (not include_view
                and key == 'view' and not collection.list_view._alt_view_visible_choices):
                continue
            form_filters.append(key)
        return form_filters

    def is_form_filled(self, collection, include_view=True):
        return bool(self.only_form_filters(collection, include_handled_outside=True, include_view=include_view))

    def update_key(self, key, new_value):
        """
        If dict values are lists, then it will consider that you're passing multiple options,
        not that your list is the value in itself.
        """
        if not self.querydict._mutable:
            self.querydict = self.querydict.copy()
        try: # for QueryDict
            self.querydict.setlist(key, new_value if isinstance(new_value, list) else [ new_value ])
        except AttributeError: # for dict
            self.querydict[key] = new_value


    def update(self, new_filters):
        """
        If dict values are lists, then it will consider that you're passing multiple options,
        not that your list is the value in itself.
        """
        if not new_filters:
            return
        for key, new_value in new_filters.items():
            self.update_key(key, new_value)

    # Imitate dict behavior

    def __getitem__(self, key):
        return self.get(key, as_list=False)

    def __contains__(self, key):
        return key in self.querydict

    def items(self):
        for key in self.querydict.keys():
            yield key, self.get(key)

    def items_as_lists(self):
        for key in self.querydict.keys():
            yield key, self.get(key, as_list=True)

    def __iter__(self):
        for key in self.querydict.keys():
            yield key

    def keys(self):
        for key in self.querydict.keys():
            yield key

    def values(self):
        for key in self.querydict.keys():
            yield self.get(key)

    def __setitem__(self, key, value):
        self.update_key(key, value)

    def __delitem__(self, key):
        del self.querydict[key]

    def __len__(self):
        return len(self.querydict)

    # Fallback

    def __getattr__(self, name):
        if django_settings.DEBUG:
            print u"""
            [Warning] An unknown property of querydict was called,
            which MagiQueryDict doesn\'t know of and doesn\'t wrap,
            which could result in unexpected behavior.
            """
        try:
            return getattr(self.querydict, name)
        except AttributeError:
            return None

    # Unicode
    def __unicode__(self):
        return unicode(self.querydict)

def getIndex(list, index, default=None):
    try:
        return list[index]
    except IndexError:
        return default

def updatedDict(d, *args, **kwargs):
    if kwargs.get('copy', False):
	d = d.copy()
    for new_d in args:
	d.update(new_d)
    return d

def mergeDicts(d, *args):
    return updatedDict(d, *args, copy=True)

def fieldNameMatch(original_field_name, *field_names):
    for field_name in field_names:
        if (
                original_field_name == field_name
                or original_field_name.startswith(u'{}_'.format(field_name))
                or original_field_name.endswith(u'_{}'.format(field_name))
                or u'_{}_'.format(field_name) in original_field_name
        ):
            return True
    return False

NUMBER_AND_FLOAT_REGEX = '[-+]?[0-9]*\.?[0-9]+'

def makeTemplateFromString(string, regexes, variable_name='value'):
    """
    Takes a string and a regex, and returns a template by replacing the matches with {v1} variables.
    Ex:
    makeTemplateFromString("For the next 5 seconds, score boosted by +3.5%.", [NUMBER_AND_FLOAT_REGEX])
    -> "For the next {v1} seconds, score boosted by +{v1}%."
    """
    regex = re.compile(u'({})'.format(u'|'.join(regexes)))
    string = re.sub(regex, u'{v}', string)
    i = 1
    while '{v}' in string:
        string = string.replace('{v}', '{{{}{}}}'.format(variable_name, i), 1)
        i += 1
    return string

def matchesTemplate(template, string):
    template = re.escape(template).replace('\{', '{').replace('\}', '}')
    if '{}' in template:
        regex = re.compile(template.format(*['(.+)'] * template.count('{}')))
        match = regex.match(string)
        if match:
            return match.groups()
        return None
    variables = templateVariables(template)
    regex = re.compile(template.format(**{
        variable: u'(?P<{}>.+)'.format(variable)
        for variable in variables
    }))
    match = regex.match(string)
    if match:
        return match.groupdict()
    return None

def summarize(string, max_length=100):
    if string is None: return None
    string = ' '.join(string.split(' '))
    if max_length is not None and len(string) > max_length:
        string = u' '.join(string[:max_length + 1].split(' ')[0:-1]) + u'...'
    return string

def simplifyMarkdown(markdown_string, max_length=None):
    if string is None or not string: return None
    markdown_string = summarize(markdown_string, max_length=max_length)
    if not markdown_string: return ''
    for c in ['*', '>', '#', '-', '+', '![', '[', ']', '(', ')', 'https://', 'http://', '//']:
        markdown_string = markdown_string.replace(c, ' ')
    return markdown_string

def tweetLength(tweet):
    length = 0
    # Links have a fixed length
    for tweet_part in tweet.split('http'):
        if tweet_part.startswith('s://') or tweet_part.startswith('://'):
            length += TWITTER_LINKS_COUNT_AS_X_CHARACTERS
            rest_of_tweet_part = ' '.join(tweet_part.split(' ')[1:])
            if rest_of_tweet_part:
                length += 1 # space separator
                length += len(rest_of_tweet_part)
        else:
            length += len(tweet_part)
    # Note: some emojis count as multiple characters, but len(...) already counts them that way
    return length

def isTweetTooLong(tweet):
    return tweetLength(tweet) > TWITTER_MAX_CHARACTERS

HTML_CLEANER = re.compile('<(.|\n)*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});', re.MULTILINE)

def simplifyHTML(html, max_length=None):
    for replace_from, replace_to in [
            ('<li>\n', '<li>'),
            ('<li>', '- '),
    ] + [
        ('<h{}>'.format(i), u'★ ')
        for i in range(1, 6)
    ] + [
        ('</h{}>'.format(i), u' ★')
        for i in range(1, 6)
    ]:
        html = html.replace(replace_from, replace_to)
    html = re.sub(HTML_CLEANER, '', html)
    html = u'\n'.join([ s.strip() for s in html.split('\n') ])
    return summarize(html, max_length=max_length) if max_length else html

def addParametersToURL(url, parameters={}, anchor=None):
    existing_anchor = u'#'.join(url.split('#')[1:])
    return u'{}{}{}{}'.format(
        url.split('#')[0],
        ('?' if '?' not in url else ('&' if not url.endswith('&') else '')) if parameters else u'',
        '&'.join([u'{}={}'.format(k, v) for k, v in parameters.items() if v is not None]),
        u'#{}'.format(anchor or existing_anchor) if anchor or existing_anchor else '',
    )

def isFullURL(url):
    return url.startswith('//') or url.startswith('http://') or url.startswith('https://')

def getListURL(
        collection_plural_name, ajax=False, modal_only=False,
        parameters=None, preset=None, random=False, full=False,
):
    url = u'{}{}{}/'.format(
        django_settings.SITE_URL if full else '',
        u'/' if not full else '',
        u'/'.join([ s for s in [
            'ajax' if ajax else None,
            collection_plural_name,
            preset,
            'random' if random else None,
        ] if s ]),
    )
    parameters = parameters.copy() if parameters else {}
    if modal_only:
        parameters['ajax_modal_only'] = ''
    return addParametersToURL(url, parameters)

def getDomainFromURL(url):
    return urlparse(url).netloc

def getSiteName(language=None):
    # /!\ Can't be called at global level
    return RAW_CONTEXT['site_name_per_language'].get(language if language else get_language(), RAW_CONTEXT['site_name'])

def getEmojis(how_many=1):
    # /!\ Can't be called at global level
    if len(RAW_CONTEXT['site_emojis'] or []) == 0:
        return [''] * how_many
    elif len(RAW_CONTEXT['site_emojis']) < how_many:
        return (RAW_CONTEXT['site_emojis'] + (RAW_CONTEXT['site_emojis'] * (
            how_many / len(RAW_CONTEXT['site_emojis']))))[:how_many]
    return RAW_CONTEXT['site_emojis'][:how_many]

def getSiteNameWithEmojis(language=None):
    emojis = getEmojis(2)
    return u'{emoji1} {site_name} {emoji2}'.format(
        emoji1=emojis[0], site_name=getSiteName(language=language), emoji2=emojis[1],
    )

def couldSpeakEnglish(language=None, request=None):
    # /!\ Can't be called at global level
    if not language:
        language = request.LANGUAGE_CODE if request else get_language()
    return language not in RAW_CONTEXT.get('languages_cant_speak_english', [])

############################################################
# Page titles and prefixes utils

def pageTitleFromPrefixes(title_prefixes, page_title):
    return u' | '.join([
        unicode(page_title)
    ] + [
        unicode(prefix['title'])
        for prefix in reversed(title_prefixes or [])
        if prefix.get('include_in_title', True)
    ])

def h1ToContext(h1, context):
    for h1_key in ['title', 'icon', 'image', 'classes', 'attributes', 'image_size']:
        value = h1.get(h1_key, None)
        if h1_key == 'title':
            context[u'h1_page_title'] = value
        else:
            context[u'h1_page_title_{}'.format(h1_key)] = value

def getNavbarPrefix(navbar_link_list, request, context, append_to=None):
    if navbar_link_list:
        if navbar_link_list == 'staff' and not request.user.is_staff:
            return None
        navbar_list_details = context['navbar_links'].get(navbar_link_list, {})
        title = (
            _('More') if navbar_link_list == 'more'
            else navbar_list_details.get('title', string.capwords(navbar_link_list))
        )
        prefix = {
            'title': title(context) if callable(title) else title,
            'url': u'/{}/'.format(navbar_link_list),
        }
        if append_to is not None:
            append_to.append(prefix)
        return prefix
    return None

def getNavbarHeaderPrefix(navbar_link_list, is_link, context, append_to=None):
    if navbar_link_list:
        if navbar_link_list == 'staff':
            return None
        navbar_list_details = context['navbar_links'].get(navbar_link_list, {})
        header = None
        header_name = None
        for link_name, link in navbar_list_details['links'].items():
            if link.get('is_header', False):
                header = link
                header_name = link_name
            if is_link(link_name):
                if header:
                    prefix = {
                        'title': header['title'],
                        'url': header.get('url', u'/{}/#{}'.format(navbar_link_list, header_name)),
                    }
                    if append_to is not None:
                        append_to.append(prefix)
                    return prefix
                return None
    return None

def getNavbarHeaderPrefixForCollection(collection, context, append_to=None):
    return getNavbarHeaderPrefix(
        navbar_link_list=collection.navbar_link_list,
        is_link=lambda link_name: link_name.startswith(u'{}_'.format(collection.name)),
        context=context, append_to=append_to,
    )

def getNavbarHeaderPrefixForPage(page_name, page, context, append_to=None):
    return getNavbarHeaderPrefix(
        navbar_link_list=page['navbar_link_list'],
        is_link=lambda link_name: link_name == page_name,
        context=context, append_to=append_to,
    )

############################################################
# Redirections

def redirectToProfile(request, account=None):
    raise HttpRedirectException(u'/user/{}/{}/'.format(request.user.id, request.user.username, '#{}'.format(account.id) if account else ''))

def redirectWhenNotAuthenticated(request, context, next_title=None):
    if request and not request.user.is_authenticated():
        current_url = context.get('current_url', request.get_full_path() if request else '')
        if current_url.startswith('/ajax/'):
            raise HttpRedirectException(u'/signup/')
        raise HttpRedirectException(u'/signup/{}'.format(u'?next={}{}'.format(
            current_url, u'&next_title={}'.format(unicode(next_title)) if next_title else u'')))

############################################################
# Fail safe get_object_or_404

def get_one_object_or_404(queryset, *args, **kwargs):
    """
    Equivalent of get_object_or_404 but if more than 1, will return first result
    """
    existing = queryset.filter(**kwargs)
    try:
        return existing[0]
    except IndexError:
        raise Http404('No %s matches the given query.' % queryset.model._meta.object_name)

############################################################
# Model utils

def dumpModel(instance):
    """
    Take an instance of a model and transform it into a string with all its info.
    Allows to delete an instance without losing data.
    """
    dump = model_to_dict(instance)
    for key in dump.keys():
        if isinstance(dump[key], models.Model):
            dump[key] = dump[key].pk
        else:
            dump[key] = unicode(dump[key])
    return dump

def prepareCache(d):
    if isinstance(d, dict):
        return {
            key: prepareCache(value)
            for key, value in d.items()
        }
    elif isinstance(d, list):
        return [ prepareCache(value) for value in d ]
    elif isinstance(d, tuple):
        return tuple([ prepareCache(value) for value in d ])
    is_supported = False
    for supported_type in [ basestring, int, float, bool, type(None) ]:
        if isinstance(d, supported_type):
            is_supported = True
            break
    if not is_supported:
        try:
            json.dumps(d)
        except TypeError:
            return unicode(d)
    return d

def cacheRelExtra(
        d, cached_item_class, id=None,
        collection_name=None,
        model_class=None,
        images_field_names=[],
):
    """Takes a dict and adds details to mimic a cached related item"""
    d = cached_item_class(d)
    # Get collection_name + model_class
    if model_class:
        d.model_class = model_class
        d.collection_name = getattr(model_class, 'collection_name', None)
        collection = d.collection
    elif collection_name:
        d.collection_name = collection_name
        collection = d.collection
        d.model_class = failSafe(lambda: collection.queryset.model, exceptions=[ AttributeError ])
    else:
        d.model_class = None
        d.collection_name = None
        collection = None
    # Add id if missing
    if 'id' not in d and id is not None:
        d.id = id
    if 'pk' not in d:
        d.pk = d.get('id', None)
    return d

def modelHasField(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False

def modelGetField(model, field_name):
    try:
        return model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return None

def modelFieldVerbose(model, field_name, fallback=True):
    return (
        notTranslatedWarning(model._meta.get_field(field_name)._verbose_name)
        or (toHumanReadable(field_name, warning=True) if fallback else None)
    )

def modelFieldHelpText(model, field_name):
    return model._meta.get_field(field_name).help_text

def getRelatedItemFromItem(item, related_item_field_name, unique=True, count=False):
    """
    Example: getRelatedItemFromItem(idol 'cards__voice_actresses')
    Make sure everything has been preselected/prefetched!
    Unique: If the result is a lit of items, make sure there's no duplicate
    Count: Return the total number of items instead of the items.
           If you use a multi-level lookup, it will still retrieve the intermediary items.
    """
    value = item # for readability, because it can be a list when it's called recursively
    if '__' in related_item_field_name:
        first_level_field_name = related_item_field_name.split('__')[0]
        next_level_field_names = u'__'.join(related_item_field_name.split('__')[1:])
    else:
        first_level_field_name = related_item_field_name
        next_level_field_names = None
    if isinstance(value, list):
        next_level_sub_lists_or_totals = []
        for item in value:
            if hasattr(getattr(item, first_level_field_name), 'all'):
                if count and not next_level_field_names:
                    next_level_sub_lists_or_totals.append(
                        getattr(item, first_level_field_name).count()
                    )
                else:
                    next_level_sub_lists_or_totals.append(
                        list(getattr(item, first_level_field_name).all())
                    )
            else:
                if count and not next_level_field_names:
                    next_level_sub_lists_or_totals.append(1)
                else:
                    next_level_sub_lists_or_totals.append([
                        getattr(item, first_level_field_name),
                    ])
        if count and not next_level_field_names:
            next_level_value = sum(next_level_sub_lists_or_totals)
        else:
            next_level_value = sum(next_level_sub_lists_or_totals, [])
    elif not value:
        if count and not next_level_field_names:
            next_level_value = 0
        elif next_level_field_names:
            next_level_value = []
        else:
            next_level_value = None
    else:
        if hasattr(getattr(value, first_level_field_name), 'all'):
            if count and not next_level_field_names:
                next_level_value = getattr(value, first_level_field_name).count()
            else:
                next_level_value = list(getattr(value, first_level_field_name).all())
        else:
            if count and not next_level_field_names:
                next_level_value = 1
            else:
                next_level_value = getattr(value, first_level_field_name)
    if unique and isinstance(next_level_value, list):
        next_level_value = listUnique(next_level_value)
    if next_level_field_names:
        return getRelatedItemFromItem(next_level_value, next_level_field_names, unique=unique, count=count)
    if count and not isinstance(next_level_value, int): # should never happen
        if isinstance(next_level_value, list):
            return len(next_level_value)
        return 1
    return next_level_value

getRelatedItemsFromItem = getRelatedItemFromItem

def getModelOfRelatedItem(
        model, related_item_field_name,
        return_model_field=False, return_is_plural=False,
):
    """return_model_field and return_is_plural are not supported with multi-level lookups"""
    def _return(model, model_field, is_plural):
        if return_model_field and return_is_plural:
            return model, model_field, is_plural
        elif return_model_field:
            return model, model_field
        elif return_is_plural:
            return model, is_plural
        return model
    if '__' in related_item_field_name:
        model_class = getModelOfRelatedItem(model, related_item_field_name.split('__')[0])
        if not model_class:
            return _return(None, None, None)
        return getModelOfRelatedItem(model_class, u'__'.join(related_item_field_name.split('__')[1:]))
    # Foreign key or many to many
    field = modelGetField(model, related_item_field_name)
    if field:
        return _return(field.rel.to, field, isinstance(field, models.ManyToManyField))
    # Reverse related objects
    for r in model._meta.get_all_related_objects():
        if r.get_accessor_name() == related_item_field_name:
            return _return(r.model, r, False)
    # Many to many reverse related objects
    for r in model._meta.get_all_related_many_to_many_objects():
        if r.get_accessor_name() == related_item_field_name:
            return _return(r.model, r, True)
    return _return(None, None, None)

def _getFilterFieldNameOfRelatedItem(model, related_item_field_name, suffix=u''):
    if '__' in related_item_field_name:
        filter_field_name = _getFilterFieldNameOfRelatedItem(model, related_item_field_name.split('__')[0])
        if not filter_field_name:
            return None
        model_class = getModelOfRelatedItem(model, related_item_field_name.split('__')[0])
        return _getFilterFieldNameOfRelatedItem(
            model_class,
            u'__'.join(related_item_field_name.split('__')[1:]),
            suffix=clearJoin([ filter_field_name, suffix ], u'__'),
        )
    filter_field_name = failSafe(
        lambda: getattr(model, related_item_field_name).field.related_query_name(),
        exceptions=[ AttributeError ],
    ) or failSafe(
        lambda: getattr(model, related_item_field_name).related.field.name,
        exceptions=[ AttributeError ],
    ) or failSafe(
        lambda: getattr(model, related_item_field_name).name,
        exceptions=[ AttributeError ],
    )
    if not filter_field_name:
        return None
    return clearJoin([ filter_field_name, suffix], u'__')

def _getVerboseNameOfRelatedFieldAsList(
        model, related_item_field_name, model_field=None, plural=None,
        rel_options=None, collection=None, current_list=None, default=None,
):
    if not current_list:
        current_list = []
    if '__' in related_item_field_name:
        # rel_options and model_field are not used
        first_level_field_name = related_item_field_name.split('__')[0]
        first_level_model, first_level_model_field, first_level_plural = getModelOfRelatedItem(
            model, first_level_field_name,
            return_model_field=True, return_is_plural=True,
        )
        # Call it with just the first level
        first_level_verbose_name = _getVerboseNameOfRelatedFieldAsList(
            model, first_level_field_name, model_field=first_level_model_field,
            plural=first_level_plural,
        )[0]
        current_list.append(first_level_verbose_name)
        # Then add the rest
        # plural and collection get passed all the way down to the last level
        return _getVerboseNameOfRelatedFieldAsList(
            first_level_model, u'__'.join(related_item_field_name.split('__')[1:]),
            plural=plural, collection=collection,
            current_list=current_list,
        )
    # From rel_options
    if not rel_options:
        rel_options = getRelOptionsDict(model_class=model, field_name=related_item_field_name)
    verbose_name = getattr(rel_options, 'verbose_name', None)
    if callable(verbose_name):
        verbose_name = verbose_name()
    # From model field
    rel_model = None
    if not verbose_name:
        if not model_field:
            rel_model, model_field, is_plural = getModelOfRelatedItem(
                model, related_item_field_name, return_model_field=True,
                return_is_plural=True,
            )
            if plural is None:
                plural = is_plural
        verbose_name = getattr(model_field, '_verbose_name', None)
    # From default
    if not verbose_name:
        if default:
            verbose_name = default
    # From collection
    if not verbose_name:
        if not collection:
            if not rel_model:
                rel_model, is_plural = getModelOfRelatedItem(
                    model, related_item_field_name, return_is_plural=True,
                )
                if plural is None:
                    plural = is_plural
            collection = getMagiCollection(getattr(rel_model, 'collection_name', None))
        if plural:
            verbose_name = getattr(collection, 'plural_title', None)
        else:
            verbose_name = getattr(collection, 'title', None)
    # Fallback to the field name in human readable norm
    if not verbose_name:
        verbose_name = toHumanReadable(related_item_field_name, capitalize=True, warning=True)
    # Return
    current_list.append(verbose_name)
    return current_list

def getPrefetchedRelatedItems(item, field_name, request):
    # Items have not been prefetched due to high traffic
    if request and field_name in getattr(request, '_not_prefetched_for_high_traffic', []):
        return []
    # Retrieve items that have been prefetched manually with a limit
    elif request and getattr(request, '_prefetched_with_max', {}).get(field_name):
        return request._prefetched_with_max[field_name][0]
    # Non-explicit relationships: manual queryset
    elif isinstance(getattr(item, field_name, None), QuerySet):
        return getattr(item, field_name)
    # Retrieve items that have been prefetched with .all()
    else:
        return getRelatedItemsFromItem(item, field_name)

def getVerboseNameOfRelatedField(
        model, related_item_field_name, model_field=None, plural=None,
        rel_options=None, collection=None, prefix=None, default=None,
        # For multi-level relationships:
        return_as_list=False, separator=u' - '
):
    """
    Example: Card contains fk to idol.
    Then params will be:
    - model=models.Card
    - related_item_field_name='idol',
    - model_field=<django.db.models.fields.related.ForeignKey: idol>
    - plural=False
    The result will be: "Idols"

    rel_options and collection can be retrieved from the model if they're not specified.
    It's just to avoid fetching them again if you already have them handy.

    - plural = wether or not there are multiple items (fk vs m2m for ex)

    Supports multi-level relationships.
    In that case, it will return the chain of relationship seperated with " - " (or separator).
    You can also get the list of verbose names using return_as_list.

    When multi-level:
    - if there's a verbose_name in rel_options, it will just return it and not do anything else
    - otherwise: rel_options and model_field are not used
    - plural and collection will be used for the last level

    Example: Song contains singers. Singers (idols) contain voice actresses.
    The params will be:
    - model=Song
    - related_item_field_name='singers__voice_actress'
    - model_field=<django.db.models.fields.related.ManyToManyField: singers>
    - plural=True
    The result will be: "Singers - Voice actresses"
    And if you set return_as_list, you will get:
    [ "Singers", "Voice actresses" ]

    You should always use return_as_list and not try to split them
    yourself, you never know if one of the verbose names uses your separator too.
    """
    if rel_options and rel_options.get('verbose_name', None):
        verbose_name = rel_options['verbose_name']
        if callable(verbose_name):
            verbose_name = verbose_name()
        l = [ verbose_name ]
    else:
        l = _getVerboseNameOfRelatedFieldAsList(
            model, related_item_field_name, model_field=model_field, plural=plural,
            rel_options=rel_options, collection=collection, default=default,
        )
    if prefix:
        l = [ prefix ] + l
    if return_as_list:
        return l
    return separator.join([unicode(verbose_name) for verbose_name in l ])

def getFilterFieldNameOfRelatedItem(model, related_item_field_name):
    return _getFilterFieldNameOfRelatedItem(model, related_item_field_name)

def selectRelatedDictToStrings(select_related, prefix=None):
    if not isinstance(select_related, dict):
        return []
    new = []
    for key, values in select_related.items():
        if prefix:
            key = u'{}__{}'.format(prefix, key)
        new.append(key)
        new += selectRelatedDictToStrings(values, prefix=key)
    return new

def getAllModelFields(model, only_related_fields=False):
    """
    Retrieve all the fields available in a model, including related and reverse related.
    Sorted.
    only_related_fields will only include fields related to other items (foreign keys included).
    """
    return OrderedDict([
        (
            model_field.get_accessor_name()
            if isinstance(model_field, RelatedObject)
            else model_field.name,
            model_field
        ) for model_field in (
            sorted(
                # Model fields
                ([ f for f in (
                    model._meta.concrete_fields
                    + [f for f in model._meta.virtual_fields if isinstance(f, ModelField)]
                ) if (not only_related_fields
                      or isinstance(f, models.ForeignKey)
                      or isinstance(f, models.OneToOneField))
                  ])
                # Many to many
                + model._meta.many_to_many
            ) + (
                # Reverse related
                model._meta.get_all_related_objects()
                + model._meta.get_all_related_many_to_many_objects()
            )
        )
    ])

def getAllModelRelatedFields(model):
    return getAllModelFields(model, only_related_fields=True)

def displayQueryset(queryset, prefix=u''):
    result = u''
    if queryset is None:
        result += u'{}None\n'.format(prefix)
    else:
        result += u'{}{}\n'.format(prefix, queryset.model)
    result += u'{}{}\n'.format(prefix, '  Select related:')
    result += u'{}{}{}\n'.format(prefix, '    ', queryset.query.select_related)
    result += u'{}{}\n'.format(prefix, '  Prefetch related:')
    if queryset._prefetch_related_lookups:
        for p in queryset._prefetch_related_lookups:
            if isinstance(p, Prefetch):
                result += u'{}{}{}\n'.format(prefix, '    ', p.prefetch_to)
                result += displayQueryset(p.queryset, prefix=prefix + u'      ')
            else:
                result += u'{}{}{}\n'.format(prefix, '    ', p)
    else:
        result += u'{}{}{}\n'.format(prefix, '    ', None)
    return result

def hasValue(value, false_bool_is_value=True, none_string_is_value=False):
    """
    Bool: False IS considered value. (can be changed with false_bool_is_value)
    Int: 0 IS considered value.
    None: NOT considered value
    Images: '' NOT considered value.
    Strings: '' NOT considered value.
    Lists: [] NOT considered value.
    Dicts: {} NOT considered value.
    Tuples: () NOT considered value.
    ManyToMany: [] NOT considered value.
    """
    if (isinstance(value, list)
        or isinstance(value, dict)
        or isinstance(value, tuple)):
        return bool(value)
    if value == 'None' and none_string_is_value:
        return True
    return value is not None and unicode(value) not in ['', 'None'] + (
        ['False'] if not false_bool_is_value else [])

def getRelOptionsDict(rel_options=None, model_class=None, field_name=None):
    """
    Either (rel_options) or (model_class + field_name required)
    Will not add default values, call setRelOptionsDefaults for that.
    """
    if rel_options is None:
        rel_options = failSafe(lambda: next(
            r for r in (
                getattr(model_class, 'REVERSE_RELATED', [])
                + getattr(model_class, 'reverse_related', []) # for backwards compatibility
            ) if (r[0] if isinstance(r, tuple) else r['field_name']) == field_name
        ), exceptions=[ StopIteration ], default={})
    if isinstance(rel_options, tuple):
        rel_options = {
            'field_name': getIndex(rel_options, 0),
            'url': getIndex(rel_options, 1),
            'verbose_name': getIndex(rel_options, 2),
            'filter_field_name': getIndex(rel_options, 3),
        }
    rel_options = AttrDict(rel_options)
    return rel_options

def setRelOptionsDefaults(model_class, field_name, rel_collection, rel_options, is_multiple=True):
    # Set defaults to None
    for key in [
            'verbose_name',
            'icon',
            'image',
            # URL stuff:
            'url',
            'filter_field_name',
            'to_preset',
            'new_window',
            # For fields in REVERSE_RELATED only (unknown from model):
            'collection_name',
            # Other:
            'template_for_prefetched',
            'template_for_preselected',
    ]:
        if key not in rel_options:
            rel_options[key] = None
    # Other defaults
    for key, default in {
            # For non-explicit relationships only
            'prefetched': False,
            'prefetched_together': False,
            # URL stuff
            'allow_ajax_per_item': True,
            'allow_ajax_for_more': True,
    }.items():
        if key not in rel_options:
            rel_options[key] = default

    # Multiple
    if is_multiple:
        # Defaults
        for key, default in {
                # Display grid
                'col_break': 'sm',
                'align': 'right',
        }.items():
            if key not in rel_options:
                rel_options[key] = default

        # Max and per line
        rel_options.show_per_line = _getPerLineShownForPrefetchedTogether(
            model_class, field_name, rel_collection, rel_options=rel_options)
        rel_options.max = getMaxShownForPrefetchedTogether(
            model_class, field_name, rel_collection, rel_options=rel_options)

def _getPerLineShownForPrefetchedTogether(model_class, field_name, rel_collection, rel_options):
    return (
        getattr(rel_options, 'show_per_line', None)
        or getattr(rel_options, 'max_per_line', None)
        or getattr(model_class, u'{}_SHOW_PER_LINE'.format(field_name.upper()), None)
        or getattr(model_class, u'{}_MAX_PER_LINE'.format(field_name.upper()), None)
        or (
            rel_collection.list_view.prefetched_per_line
            if rel_collection and rel_collection.list_view.prefetched_per_line >= 3
            else None
        )
        or 5
    )

def getMaxShownForPrefetchedTogether(model_class, field_name, rel_collection, rel_options=None):
    if not rel_options:
        rel_options = getRelOptionsDict(model_class=model_class, field_name=field_name)
    max = None
    if 'max' in rel_options:
        max = rel_options.max
    elif 'max_per_line' in rel_options:
        max = rel_options.max_per_line
    elif hasattr(model_class, u'{}_MAX'.format(field_name.upper())):
        max = getattr(model_class, u'{}_MAX'.format(field_name.upper()))
    elif hasattr(model_class, u'{}_MAX_PER_LINE'.format(field_name.upper())):
        max = getattr(model_class, u'{}_MAX_PER_LINE'.format(field_name.upper()))
    elif rel_collection and rel_collection.list_view.prefetched_page_size >= 3:
        max = rel_collection.list_view.prefetched_page_size
    elif rel_collection:
        max = 5
    # Round up to make sure the last line isn't weird
    if max:
        if 'show_per_line' in rel_options:
            per_line = rel_options.show_per_line
        else:
            per_line = _getPerLineShownForPrefetchedTogether(model_class, field_name, rel_collection, rel_options)
        max = max + (per_line - (max % per_line))
    return max

def getValueIfNotProperty(cls, field_name, default=None):
    """When trying to access a variable of a class and not its instance, makes sure it doesn't return falsely positive value."""
    value = getattr(cls, field_name, default)
    return value if not isinstance(value, property) else default

def getQuerysetFromModel(model, request=None, return_collection=False):
    """
    Request is optional.
    See collection.get_queryset to see how it's used.
    """
    if not model:
        return (None, None) if return_collection else None
    collection = getMagiCollectionFromModel(model)
    if collection:
        queryset = collection.get_queryset()
    else:
        queryset = model.objects.all()
    if return_collection:
        return collection, queryset
    return queryset

def addRelatedCaches(model_class, caches):
    if not getattr(model_class, 'RELATED_CACHES', []):
        model_class.RELATED_CACHES = []
    for cache_name, details in caches.items():
        model_class.RELATED_CACHES.append(cache_name)
        if 'to_fields' not in details:
            details['to_fields'] = {}
        model_field = modelGetField(model_class, cache_name)
        if model_field:
            rel_model_class = model_field.rel.to
            if not getattr(rel_model_class, 'REVERSE_RELATED_CACHES', []):
                rel_model_class.REVERSE_RELATED_CACHES = []
            is_m2m = isinstance(model_field, models.ManyToManyField)
            rel_model_class.REVERSE_RELATED_CACHES.append((
                model_field.related.get_accessor_name(),
                cache_name, is_m2m,
            ))
            label = notTranslatedWarning(model_field._verbose_name)
            rel_collection_name = getattr(rel_model_class, 'collection_name', None)
        else: # Assume reverse related
            label = toHumanReadable(cache_name, warning=True)
            rel_model_class = None
            is_m2m = True
            rel_collection_name = None
        character_key = details.get('character_key', details.get('is_character', None))
        if character_key == True:
            character_key = 'FAVORITE_CHARACTERS'
        if not details.get('fields', []) and character_key:
            if is_m2m:
                cache_field_name = u'_cache_c_{}'.format(cache_name)
                to_cache = _addRelatedCaches_to_cache_m2m_csv(cache_name)
                setattr(model_class, u'cached_{}_map'.format(
                    cache_name), classmethod(_addRelatedCaches_cached_map_for_characters(character_key)))
            else:
                setattr(model_class, u'cached_{}'.format(cache_name), property(
                    _addRelatedCaches_cached_character))
        else:
            cache_field_name = u'_cache_j_{}'.format(cache_name)
            if character_key:
                fields = [ 'id' ]
            elif rel_model_class and rel_model_class.__name__ == 'UserImage':
                fields = [ 'id', 'image', 'image_thumbnail' ]
            elif rel_model_class and rel_model_class.__name__ == 'User':
                fields = [ 'id', 'image', 'username' ]
            else:
                fields = [ 'id', 'unicode', 'unicodes' ]
            fields = listUnique(fields + details.get('fields', []))
            # Go through fields
            translated_fields = details.get('translated_fields', []) + getattr(
                rel_model_class, 'TRANSLATED_FIELDS', [])
            for field_name in fields:
                # Add images (doesn't work for reverse related)
                if rel_model_class:
                    if field_name.endswith('_thumbnail'):
                        field = modelGetField(rel_model_class, field_name[:len('_thumbnail') * -1])
                    else:
                        field = modelGetField(rel_model_class, field_name)
                    if isinstance(field, models.ImageField):
                        if not hasattr(model_class, u'_cache_{}_images'.format(cache_name)):
                            setattr(model_class, u'_cache_{}_images'.format(cache_name), [ field_name ])
                        else:
                            getattr(model_class, u'_cache_{}_images'.format(cache_name)).append(field_name)
                # Add translations for translatable fields (doesn't work for related fields)
                if field_name in translated_fields:
                    fields.append('{}s'.format(field_name))
                    details['to_fields'][field_name] = _addRelatedCaches_toTranslationField(field_name)
                    details['to_fields']['{}s'.format(field_name)] = _addRelatedCaches_toTranslationsField(
                        field_name)
            if is_m2m:
                to_cache = _addRelatedCaches_to_cache_m2m(
                    cache_name, fields, rel_collection_name, details['to_fields'])
            else:
                to_cache = _addRelatedCaches_to_cache_fk(cache_name, fields, details['to_fields'])
            if not model_field:
                # For reverse relationships, because models have not been fully loaded yet,
                # some details get added in magi.urls
                if not getattr(model_class, '_UNSET_REVERSE_RELATED_CACHES', []):
                    model_class._UNSET_REVERSE_RELATED_CACHES = []
                model_class._UNSET_REVERSE_RELATED_CACHES.append((cache_name, details, fields))
            # Add pre for characters
            if character_key:
                setattr(model_class, u'cached_{}_pre'.format(
                    cache_name), classmethod(_addRelatedCaches_cache_pre_for_characters(character_key)))
        image_for_prefetched = details.get('image_for_prefetched', None)
        text_image_for_prefetched = details.get('text_image_for_prefetched', None)
        # Add pre for users
        if rel_model_class and rel_model_class.__name__ == 'User':
            if not image_for_prefetched:
                image_for_prefetched = lambda _item, _d: -1
                text_image_for_prefetched = lambda _item, _d: _d.image_url
            setattr(model_class, u'cached_{}_pre'.format(cache_name), classmethod(
                _addRelatedCaches_cache_pre_for_user))
        # Add extra to add image_for_prefetched if set
        if image_for_prefetched or text_image_for_prefetched:
            setattr(model_class, u'cached_{}_extra'.format(cache_name), classmethod(
                _addRelatedCaches_cache_extra_image_for_prefetched(
                    image_for_prefetched, text_image_for_prefetched)))
        cache_model_field = models.TextField(label, null=True)
        model_class.add_to_class(cache_field_name, cache_model_field)
        setattr(model_class, u'to_cache_{}'.format(cache_name), to_cache)
        if rel_collection_name:
            setattr(model_class, u'_cached_{}_collection_name'.format(cache_name), rel_collection_name)

def _addRelatedCaches_to_cache_m2m_csv(cache_name):
    def _to_cache(item):
        return [
            rel_item.pk
            for rel_item in getattr(item, cache_name).all()
        ]
    return _to_cache

def _addRelatedCaches_to_rel_item_cache(rel_item, fields, to_fields):
    return {
        field_name: (
            to_fields[field_name](rel_item)
            if field_name in to_fields
            else getattr(rel_item, field_name)
        ) for field_name in fields
    }

def _addRelatedCaches_to_cache_m2m(cache_name, fields, rel_collection_name, to_fields):
    def _to_cache(item):
        max = None
        if rel_collection_name:
            rel_collection = getMagiCollection(rel_collection_name)
            max = getMaxShownForPrefetchedTogether(type(item), cache_name, rel_collection)
        queryset = getattr(item, cache_name).all()
        if max:
            queryset = queryset[:max]
        return [
            _addRelatedCaches_to_rel_item_cache(rel_item, fields, to_fields)
            for rel_item in queryset
        ]
    return _to_cache

def _addRelatedCaches_to_cache_fk(cache_name, fields, to_fields):
    def _to_cache(item):
        rel_item = getattr(item, cache_name)
        if not rel_item:
            return None
        return _addRelatedCaches_to_rel_item_cache(rel_item, fields, to_fields)
    return _to_cache

def _addRelatedCaches_cached_map_for_characters(character_key):
    def _cached_map(item, pk):
        return getCharacterCacheFromPk(pk, key=character_key)
    return _cached_map

def _addRelatedCaches_cache_pre_for_characters(character_key):
    def _cache_pre(item, d):
        for key, value in getCharacterCacheFromPk(d['id'], key=character_key, with_extra=False).items():
            if key not in d:
                d[key] = value
    return _cache_pre

def _addRelatedCaches_cached_character(character_key):
    def _cached_character(item):
        return getCharacterCacheFromPk(getattr(item, u'{}_id'.format(field_name)), key=character_key)
    return _cached_character

def _addRelatedCaches_cache_extra_image_for_prefetched(image_for_prefetched, text_image_for_prefetched):
    def _cached_extra(item, d):
        if image_for_prefetched:
            d['image_for_prefetched'] = image_for_prefetched(item, d)
        if text_image_for_prefetched:
            d['text_image_for_prefetched'] = text_image_for_prefetched(item, d)
        return d
    return _cached_extra

def _addRelatedCaches_cache_pre_for_user(item, d):
    d['unicode'] = d['username']
    d['avatar'] = d['image']

def _addRelatedCaches_toTranslationField(field_name):
    def _to_field(item):
        return item.get_translation(field_name, language='en', fallback_to_other_sources=False)
    return _to_field

def _addRelatedCaches_toTranslationsField(field_name):
    def _to_field(item):
        return item.get_all_translations_of_field(field_name, include_english=False, unique=True)
    return _to_field

def updateAllRelatedCaches():
    # /!\ Can't be called at global level
    for collection_name, collection in getMagiCollections().items():
        print collection_name
        try:
            collection.queryset.model.update_all_related_caches_of_model(update_reverse_related_caches=False)
        except AttributeError:
            pass

class ColorInput(TextInput):
    input_type = 'color'

    def render(self, name, value, attrs=None):
        rendered = super(ColorInput, self).render(name, value, attrs=attrs)
        if not self.is_required:
            return mark_safe(u'{input} <input type="checkbox" name="unset-{name}"{checked}> {none}'.format(
                input=rendered,
                name=name,
                none=t['Clear'],
                checked='' if value else ' checked',
            ))
        return rendered

    def value_from_datadict(self, data, files, name):
        value = super(ColorInput, self).value_from_datadict(data, files, name)
        if not self.is_required and CheckboxInput().value_from_datadict(
                data, files, u'unset-{}'.format(name)):
            return None
        return value

class FilterByMode:
    Exact, Contains, StartsWith, EndsWith = range(4)

def filterByTranslatedValue(
        queryset, field_name, language=None, value=None,
        mode=FilterByMode.Exact, case_insensitive=False,
        as_condition=False,
        # only for Contains and EndsWith:
        strict=False, force_queryset=False,
        # only when language is not specified:
        include_english=True,
):
    """
    When mode is Contains or EndsWith:
      If strict = False, you'll always get a queryset, but if another
      language contains or ends with the same value, they'll be returned as well.
      You can set strict to True to avoid that, but the query will run and you'll
      get a list and not a queryset as the returned value.
      Only in that specific case, you can use force_queryset to return a queryset,
      but it will be rebuilt from the result, which means the extra query can't
      be avoided.
    """
    def _return(condition=None):
        if as_condition:
            return condition
        if not condition:
            return queryset
        return queryset.filter(condition)

    i = 'i' if case_insensitive else ''
    if language:
        special_field_name = None

        long_source_field_name = u'{}_{}'.format(LANGUAGES_NAMES.get(language, None), field_name)
        short_source_field_name = u'{}_{}'.format(language, field_name)
        if language == 'en':
            special_field_name = field_name
        elif modelHasField(queryset.model, long_source_field_name):
            special_field_name = long_source_field_name
        elif modelHasField(queryset.model, short_source_field_name):
            special_field_name = short_source_field_name

        if value is None:
            if special_field_name:
                return _return(
                    Q(**{ u'{}__isnull'.format(special_field_name): False })
                    & ~Q(**{ special_field_name: '' })
                )
            return _return(Q(**{
                u'd_{}s__{}contains'.format(field_name, i): u'"{}": '.format(language),
            }))

        if special_field_name:
            if mode == FilterByMode.Exact:
                return _return(Q(**{ u'{}__{}exact'.format(special_field_name, i): value }))
            elif mode == FilterByMode.Contains:
                return _return(Q(**{ u'{}__{}contains'.format(special_field_name, i): value }))
            elif mode == FilterByMode.StartsWith:
                return _return(Q(**{ u'{}__{}startswith'.format(special_field_name, i): value }))
            elif mode == FilterByMode.EndsWith:
                return _return(Q(**{ u'{}__{}endswith'.format(special_field_name, i): value }))
            return _return()
    else:
        if value is None:
            return _return()

        other_languages_fields = [field_name] if include_english else []
        for other_language, other_language_name in LANGUAGES_NAMES.items():
            long_source_field_name = u'{}_{}'.format(other_language_name, field_name)
            short_source_field_name = u'{}_{}'.format(other_language, field_name)
            if modelHasField(queryset.model, long_source_field_name):
                other_languages_fields.append(long_source_field_name)
            elif modelHasField(queryset.model, short_source_field_name):
                other_languages_fields.append(short_source_field_name)

    if isinstance(value, basestring):
        d_value = encode_basestring_ascii(value)[1:-1]

    if mode == FilterByMode.Exact:
        if isinstance(value, basestring):
            d_value = u'"{}"'.format(d_value)
        if language:
            return _return(
                Q(**{ u'd_{}s__{}contains'.format(field_name, i): u'"{}": {},'.format(language, d_value) })
                | Q(**{ u'd_{}s__{}contains'.format(field_name, i): u'"{}": {}}}'.format(language, d_value) }),
            )
        else:
            condition = (
                Q(**{ u'd_{}s__{}contains'.format(field_name, i): u'": {},'.format(d_value) })
                | Q(**{ u'd_{}s__{}contains'.format(field_name, i): u'": {}}}'.format(d_value) })
            )
            for other_field_name in other_languages_fields:
                condition |= Q(**{ other_field_name: value })
            return _return(condition)

    elif mode == FilterByMode.StartsWith:
        if isinstance(value, basestring):
            d_value = u'"{}'.format(d_value)
        if language:
            return _return(Q(**{
                u'd_{}s__{}contains'.format(field_name, i): u'"{}": {}'.format(language, d_value),
            }))
        else:
            condition = Q(**{ u'd_{}s__{}contains'.format(field_name, i): u'": {}'.format(d_value) })
            for other_field_name in other_languages_fields:
                condition |= Q(**{ u'{}__{}contains'.format(other_field_name, i): value })
            return _return(condition)

    elif mode in [FilterByMode.Contains, FilterByMode.EndsWith]:
        condition = Q()
        if language:
            condition &= Q(**{
                u'd_{}s__{}contains'.format(field_name, i): u'"{}": '.format(language),
            })
        if mode == FilterByMode.EndsWith:
            condition &= Q(**{ u'd_{}s__{}contains'.format(field_name, i): u'{}"'.format(d_value) })
            if not language:
                for other_field_name in other_languages_fields:
                    condition |= Q(**{ u'{}__{}endswith'.format(other_field_name, i): value })
        else: # Contains
            condition = Q(**{ u'd_{}s__{}contains'.format(field_name, i): d_value })
            if not language:
                for other_field_name in other_languages_fields:
                    condition |= Q(**{ u'{}__{}contains'.format(other_field_name, i): value })
        if language and strict and not as_condition:
            queryset = queryset.filter(condition)
            items = []
            for item in queryset:
                value_for_language = item.get_translation_from_dict(
                    field_name, language=language, fallback_to_english=False, fallback_to_other_sources=False,
                )
                if mode == FilterByMode.EndsWith and value_for_language.endswith(value):
                    items.append(item)
                elif value in value_for_language:
                    items.append(item)
            if force_queryset:
                return queryset.filter(pk__in=[item.pk for item in items])
            return items
        return _return(condition)

    return _return()

############################################################
# Model / Form fields

class ManyToManyCSVField(forms_CharField):
    # Only works if pk is an integer or long

    def __init__(self, model_class, field_name, lookup_field_name='name', verbose_name=None, lowercase_verbose_name=True, queryset=None, *args, **kwargs):
        self.m2m_model_class = model_class
        self.m2m_field_name = field_name
        self.m2m_lookup_field_name = lookup_field_name
        self.m2m_items_model_class = getattr(self.m2m_model_class, self.m2m_field_name).field.rel.to
        self.queryset = queryset or self.m2m_items_model_class.objects.all()
        self._known_items_by_pk = {}
        help_text = _('Separate {things} with commas. Example: "Apple, Orange"').format(
            things=(
                (verbose_name.lower() if verbose_name and lowercase_verbose_name else verbose_name)
                or failSafe(lambda: getattr(self.m2m_model_class, self.m2m_field_name).field.verbose_name.lower())
                or toHumanReadable(lookup_field_name, capitalize=False, warning=True)
            ))
        kwargs['help_text'] = (
            markSafeFormat(u'{}<br>{}', kwargs['help_text'], help_text)
            if kwargs.get('help_text', None) else help_text
        )
        super(ManyToManyCSVField, self).__init__(*args, **kwargs)

    def _save_known_items(self, items):
        for item in items:
            self._known_items_by_pk[item.pk] = item

    def prepare_value(self, value):
        if not value:
            return None
        if isinstance(value, list):
            if isinstance(value[0], self.m2m_items_model_class):
                value = [getattr(item, self.m2m_lookup_field_name) for item in value]
            elif isinstance(value[0], int) or isinstance(value[0], long): # pk
                try:
                    value = [ getattr(self._known_items_by_pk[item_pk], self.m2m_lookup_field_name) for item_pk in value ]
                except KeyError:
                    items = list(self.queryset.filter(pk__in=value))
                    self._save_known_items(items)
                    value = [ getattr(item, self.m2m_lookup_field_name) for item in items ]
            if not isinstance(value[0], basestring):
                raise ValueError('Unknown value {} ({})'.format(type(value), value))
            return u', '.join(value)
        elif isinstance(value, basestring):
            return value
        raise ValueError('Unknown value {} ({})'.format(type(value), value))

    def clean(self, data, initial=None):
        value = super(ManyToManyCSVField, self).clean(data)
        items_names = [s.strip() for s in split_data(value) if s.strip()]
        items = list(self.queryset.filter(**{
            u'{}__in'.format(self.m2m_lookup_field_name): items_names,
        }).distinct())
        self._save_known_items(items)
        if len(items) != len(items_names):
            found_items = [getattr(item, self.m2m_lookup_field_name) for item in items]
            raise ValidationError(u'{}: {}'.format(
                join_data(*[ name for name in items_names if name not in found_items ]),
                _('No result.'),
            ))
        return items

class CSVChoiceField(forms_MultipleChoiceField):
    def prepare_value(self, value):
        if not value:
            return None
        if isinstance(value, list):
            return value
        elif isinstance(value, basestring):
            return split_data(value)
        raise ValueError('Unknown value {} ({})'.format(type(value), value))

    def clean(self, data, initial=None):
        return join_data(*super(CSVChoiceField, self).clean(data))

class ColorFormField(forms_CharField):
    pass

class ColorField(models.CharField):
    default_validators = [
        RegexValidator(
            re.compile('^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'),
            u'Enter a valid hex color.',
            'invalid',
        ),
    ]

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 10
        super(ColorField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['form_class'] = ColorFormField
        kwargs['widget'] = ColorInput
        return super(ColorField, self).formfield(**kwargs)

class _YouTubeFieldsHelpTextMixin(object):
    HELP_TEXT = u'Enter a valid YouTube URL with format: https://www.youtube.com/watch?v=xxxxxxxxxxx. Time can also be added with &t=xxx where xxx is the number of seconds'

    def __init__(self, *args, **kwargs):
        kwargs['help_text'] = (
            markSafeFormat(u'{}<br>{}', kwargs['help_text'], self.HELP_TEXT)
            if kwargs.get('help_text', None) else self.HELP_TEXT
        )
        super(_YouTubeFieldsHelpTextMixin, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(_YouTubeFieldsHelpTextMixin, self).deconstruct()
        del kwargs['help_text']
        return name, path, args, kwargs

class YouTubeVideoField(_YouTubeFieldsHelpTextMixin, models.URLField):
    REGEX = re.compile(r'^https\:\/\/www\.youtube\.com\/watch\?v\=(?P<code>[a-zA-Z0-9\_-]+)(&t=(?P<start_time>[0-9]+))?&?$')

    # Regex Validator for YouTube URLs with or without timestamp

    default_validators = models.URLField.default_validators + [
        RegexValidator(REGEX, _YouTubeFieldsHelpTextMixin.HELP_TEXT, 'invalid'),
    ]

    # Utils class methods

    @classmethod
    def parse_url(self, url):
        match = self.REGEX.match(url)
        if not match:
            raise ValidationError(self.HELP_TEXT)
        d = match.groupdict()
        return d

    @classmethod
    def url_from_code(self, code, start_time=None):
        return u'https://www.youtube.com/watch?v={}{}'.format(
            code, '' if not start_time else '&t={}'.format(start_time),
        )

    @classmethod
    def embed_url_from_code(self, code, start_time=None):
        parameters = {
            'modestbranding': 1,
            'rel': 0,
        }
        if start_time:
            parameters['start'] = start_time
        return addParametersToURL(u'https://www.youtube.com/embed/{}'.format(code), parameters=parameters)

    @classmethod
    def embed_url(self, url):
        d = self.parse_url(url)
        return self.embed_url_from_code(code=d['code'], start_time=d.get('start_time', None))

    @classmethod
    def translated_embed_url_from_embed_url(self, embed_url, language=None):
        if not language:
            language = get_language()
        google_language = googleTranslateFixLanguage(language)
        return addParametersToURL(embed_url, parameters={
            'hl': google_language,
            'cc_lang_pref': google_language,
            'cc_load_policy': 1,
        })

    @classmethod
    def translated_embed_url(self, url, language=None):
        return self.translated_embed_url_from_embed_url(self.embed_url(url), language=language)

    @classmethod
    def translated_embed_url_from_code(self, code, language=None):
        return self.translated_embed_url_from_embed_url(self.embed_url_from_code(code), language=language)

    @classmethod
    def thumbnail_url_from_code(self, code, size='default'):
        """Sizes: default, mqdefault, hqdefault, sddefault, maxresdefault"""
        return u'https://i.ytimg.com/vi/{code}/{size}.jpg'.format(
            code=code, size=size,
        )

    @classmethod
    def thumbnail_url(self, url, size='default'):
        d = self.parse_url(url)
        return self.thumbnail_url_from_code(d['code'], size=size)

class YouTubeVideoTranslationsField(_YouTubeFieldsHelpTextMixin, models.TextField):
    pass

def presetsFromChoices(
        model, field_name,
        get_label=None, get_image=None, get_field_value=None, get_icon=None,
        get_key=None, form_model_class=None,
        should_include=None,
        extra_fields={},
        to_extra_fields=lambda i, value, verbose: {},
):
    if form_model_class is None:
        form_model_class = model
    prefix = 'i_' if modelHasField(model, 'i_{}'.format(field_name)) else (
        'c_' if modelHasField(model, 'c_{}'.format(field_name)) else '')
    without_i_choices = getattr(model, u'{name}_WITHOUT_I_CHOICES'.format(name=field_name.upper()), False)
    return [
        (value if not get_key else get_key(i, value, verbose), {
            'label': get_label(i, value, verbose) if get_label else None,
            'verbose_name': verbose,
            'fields': updatedDict({
                u'{}{}'.format(prefix, field_name):
                get_field_value(i, value, verbose)
                if get_field_value else (value if prefix == 'c_' or without_i_choices else i),
            }, extra_fields, to_extra_fields(i, value, verbose)),
            'image': get_image(i, value, verbose) if get_image else (
                model.get_auto_image(field_name, value, with_static_url=False)
                if getattr(model, u'{}_AUTO_IMAGES'.format(field_name.upper()), False) else None
            ),
            'icon': get_icon(i, value, verbose) if get_icon else None,
        }) for i, (value, verbose) in model.get_choices(field_name)
        if (hasCachedChoice(
                form_model_class, u'{}{}'.format(prefix, field_name), default=True,
                i_choice=(None if without_i_choices or prefix != 'i_' else i),
                choice=(value if without_i_choices or prefix != 'i_' else None),
        ) and (True if not should_include else should_include(i, value, verbose)))
    ]

def presetsFromCharacters(
        field_name, get_label=None, get_field_value=None, key='FAVORITE_CHARACTERS',
        extra_fields={}, should_include=None, form_model_class=None,
        to_extra_fields=lambda i, value, verbose: {},
):
    """form_model_class is used to check for cache choices"""
    def _lambda(pk):
        return lambda: getCharacterNameFromPk(pk, key=key)
    return [
        (name, {
            'label': get_label(pk, name, name) if get_label else None,
            'verbose_name': _lambda(pk),
            'fields': updatedDict({
                field_name: get_field_value(pk, name, name) if get_field_value else pk,
            }, extra_fields, to_extra_fields(pk, name, name)),
            'image': getCharacterImageFromPk(pk, key=key),
        }) for (pk, name, _image) in getattr(django_settings, key, [])
        if ((not should_include or should_include(pk))
            and hasCachedChoice(form_model_class, field_name, choice=pk, default=True))
    ]

def _getAllEquivalentsOfField(field_name, model_field_class_or_form_field_class, value):
    if (model_field_class_or_form_field_class == NullBooleanField
        or model_field_class_or_form_field_class == BooleanField):
        return validNullBoolOptions(value)
    elif field_name.startswith('c_'):
        if isinstance(value, list):
            return [ value ]
        else:
            return [ split_data(value) ]
    if not hasValue(value):
        return listUnique([ value, '', None ])
    return [ value ]

def _equivalentFilters_isFilterEqual(key, values, field_details, value_to_compare):
    """value_to_compare = either default or preset value"""
    for option in _getAllEquivalentsOfField(
            key, field_details['model_field_class'] or field_details['form_field_class'],
            value_to_compare,
    ):
        if isinstance(option, list):
            if sorted(values) == sorted(option):
                return True
        elif len(values) == 1:
            if unicode(values[0]) == unicode(option):
                return True
        else:
            # If multiple values are specified for a field that's not multi-values,
            # it can't be equivalent to the default value or a preset (multi not supported)
            pass
    return False

def _equivalentFilters(collection, filters, preset_filters, ignore_filters=[]):
    if not preset_filters:
        return False
    # 1. Check if all preset keys are specified in filters
    for key, value in preset_filters.items():
        if key not in filters:
            return False
    flag = False
    # 2. Go through each filter
    for key, values in (
            [ (k, [ v ]) for k, v in filters.items() ]
            if isinstance(filters, dict)
            else filters.items_as_lists()
    ):
        if key in ignore_filters:
            continue
        field_details = collection.list_view.filters_details.get(key, {})
        # 3. If we don't know the details about this field, then we know it's not equivalent
        if not field_details:
            return False
        # 4. If the key is not in preset filters,
        #    check if it matches the default value in form. If it does, it can be ignored.
        if (key not in preset_filters and _equivalentFilters_isFilterEqual(
                key, values, field_details, field_details['form_default'])):
            continue
        # 5. If the key is not in preset filters and doesn't match the default value,
        #    then we know it's not equivalent
        if key not in preset_filters:
            return False
        # 6. Check that the value in filters matches the value in preset filters
        #    If it doesn't, then we know they're not equivalent
        if not _equivalentFilters_isFilterEqual(key, values, field_details, preset_filters.get(key, None)):
            return False
        flag = True
    if flag:
        return True
    return False

def isPreset(collection, filters, disable_cleaning=False):
    """
    Filters can be MagiQueryDict or dict

    When disable_cleaning = False (default)
    - will check for equivalent values. For example: True can be '2', 2, 'true', etc
    - will look for merge fields and make sure they're ignored
    - if a field is set and is not in presets, but it's the default value, it will be ignored
    - so it's useful when the filters come from a user, so you're not sure what's in it (empty/default values)

    When disable_cleaning = True
    - it will skip the steps above
    - but it will be faster
    - so it's useful if you're creating the filters to check against yourself, so
      you know the values will be correct and they'll be no extra values
    """
    if not filters:
        return None
    form_class = collection.list_view.filter_form
    if not form_class:
        return None
    # Get merge fields so that they're ignored
    ignore_filters = []
    if not disable_cleaning:
        def _foreach_merge_fields(new_field_name, details, fields):
            ignore_filters.append(new_field_name)
        form_class.foreach_merge_fields(_foreach_merge_fields)
    # Go through each presets to check if it's a match
    for preset, details in getattr(form_class, 'presets', {}).items():
        if disable_cleaning:
            if filters == details['fields']:
                return tourldash(preset)
        else:
            if _equivalentFilters(
                    collection, filters, details['fields'],
                    ignore_filters=ignore_filters,
            ):
                return tourldash(preset)
    return None

def unifyMergedFields(collection, filters):
    form_class = collection.list_view.filter_form
    if not form_class:
        return
    def _unifyMergedFields_foreach(new_field_name, details, fields):
        # If the merge field was used, set original fields too.
        # Ex: idol_i_unit=i_unit-1, then set i_unit=1
        merge_field_value = filters.get(new_field_name)
        if merge_field_value:
            for field_name in fields.keys():
                if merge_field_value.startswith(field_name):
                    filters.update_key(field_name, merge_field_value[len(field_name) + 1:])
                    merge_field_updated = True
        # If the original fields were used, set merge field too (only 1st)
        # Ex: i_unit=1, then set idol_i_unit=i_unit-1
        else:
            for field_name in fields.keys():
                field_value = filters.get(field_name)
                if field_value:
                    filters.update_key(new_field_name, u'{}-{}'.format(
                        field_name, field_value,
                    ))
                    break
    form_class.foreach_merge_fields(_unifyMergedFields_foreach)

def formFieldFromOtherField(field, to_new_field, new_parameters={}):
    parameters = {
        'label': field.label,
        'required': field.required,
        'initial': field.initial,
        'validators': field.validators,
        'help_text': field.help_text,
    }
    parameters.update(new_parameters)
    new_field = to_new_field(**parameters)
    for key in FORM_FIELDS_EXTRA_VALUES:
        if hasattr(field, key):
            setattr(new_field, key, getattr(field, key))
    return new_field

def changeFormField(form, field_name, to_new_field, new_parameters={}, force_add=True):
    if field_name in form.fields:
        form.fields[field_name] = formFieldFromOtherField(form.fields[field_name], to_new_field, new_parameters)
    elif force_add:
        form.fields[field_name] = to_new_field(**new_parameters)

def newOrder(current_order, insert_after=None, insert_before=None, insert_instead=None,
             insert_at=None, insert_at_instead=None, insert_at_from_last=None,
             insert_at_from_last_instead=None, dict_values={}, insert_in_dict_when_missing=True, order=[]):
    """
    All insert_ parameters are dictionaries with key = the name of the field to look at
    and value = a list to insert
    For insert_at_, key is the index (int)
    Note: won't work if you refer to a field both as a marker and as an inserted thing. needs to be called twice in that case.
    Works with dicts. If you're inserting an item not in the dict, you need to provide a value for the key in dict_values.
    """
    if isinstance(current_order, OrderedDict):
        order = listUnique(order + current_order.keys())
    else:
        order = listUnique(order + current_order)
    will_be_reinserted_fields = flattenListOfLists(sum([
        (insert_after or {}).values(), (insert_before or {}).values(), (insert_instead or {}).values(),
        (insert_at or {}).values(), (insert_at_instead or {}).values(), (insert_at_from_last or {}).values(),
        (insert_at_from_last_instead or {}).values(),
    ], []))
    filtered_order = [field for field in order if field not in will_be_reinserted_fields]
    if insert_after or insert_before or insert_instead:
        new_order = []
        for order_field_name in filtered_order:
            if order_field_name in (insert_before or {}):
                new_order += insert_before[order_field_name]
            if order_field_name in (insert_instead or {}):
                new_order += insert_instead[order_field_name]
            else:
                new_order.append(order_field_name)
            if order_field_name in (insert_after or {}):
                new_order += insert_after[order_field_name]
    else:
        new_order = filtered_order
    for position, to_insert in (insert_at or {}).items():
        new_order = new_order[:position] + to_insert + new_order[position:]
    for position, to_insert in (insert_at_instead  or {}).items():
        new_order = new_order[:position] + to_insert + new_order[position + 1:]
    for position, to_insert in (insert_at_from_last or {}).items():
        if position == 0:
            new_order += to_insert
        else:
            new_order = new_order[:-position] + to_insert + new_order[-position:]
    for position, to_insert in (insert_at_from_last_instead or {}).items():
        if position == 0:
            new_order = new_order[:-1] + to_insert
        new_order = new_order[:-position - 1] + to_insert + new_order[-position:]
    if isinstance(current_order, OrderedDict):
        return OrderedDict([
            ( key, dict_values.get(key, current_order.get(key, None)) )
            for key in new_order
            if (key in current_order or key in dict_values) or insert_in_dict_when_missing
        ])
    return new_order


VALID_NULLBOOL_OPTIONS = {
    True: [ True, '2', 2, 'True', 'true', 'on' ],
    False: [ False, '3', 3, 'False', 'false' ],
    None: [ None, '1', 1, 'null' ],
}

def validNullBoolOptions(value, return_bool_value=False, **kwargs):
    for main_value, valid_options in VALID_NULLBOOL_OPTIONS.items():
        for valid_option in valid_options:
            if value == valid_option:
                if return_bool_value:
                    return main_value
                return valid_options
    if 'default' in kwargs:
        return kwargs['default']
    raise ValueError

def toNullBool(value):
    return validNullBoolOptions(value, return_bool_value=True, default=None)

def formUniquenessCheck(
        form,
        edited_instance=None,
        field_names=None,
        filters=None,
        model_class=None,
        max=1,
        labels=None,
        model_title=None,
        case_insensitive=False,
        clean_per_field=False,
        unique_together=True,
        all_fields_required=False,
):
    if not model_class:
        model_class = form.Meta.model
    fields_dict = dict(filters or {})
    for field_name in field_names:
        if form.cleaned_data.get(field_name, None):
            fields_dict[u'{}__iexact'.format(field_name) if case_insensitive else field_name] = form.cleaned_data[field_name]
        elif all_fields_required:
            return False
    if unique_together:
        condition = Q(**fields_dict)
    else:
        condition = Q()
        for field_name, value in fields_dict.items():
            condition |= Q(**{ field_name: value })
    queryset = model_class.objects.filter(condition)
    if edited_instance:
        queryset = queryset.exclude(pk=edited_instance.pk)
    if queryset.count() >= max:
        if not labels:
            labels = [
                getattr(form.fields.get(field_name.split('__')[0], object()),
                        'label', toHumanReadable(field_name.split('__')[0], warning=True)).lower()
                for field_name in field_names
            ]
        if not model_title:
            collection = getMagiCollection(getattr(model_class, 'collection_name', None))
            model_title = collection.title if collection else model_class._meta.verbose_name
        validation_error = ValidationError(
            message=t["%(model_name)s with this %(field_labels)s already exists."],
            code='unique_together',
            params={
                'model_name': model_title,
                'field_labels': andJoin(labels, or_=not unique_together),
            },
        )
        if len(fields_dict) == 1 and not clean_per_field:
            form.add_error(fields_dict.keys()[0], validation_error)
            return False
        else:
            raise validation_error
    return True

def addButtonsToSubCollection(form, sub_collection, field_name):
    if not sub_collection:
        return
    form.fields[field_name].below_field = mark_safe(u"""
    <div class="btn-group btn-group-justified">
      <a href="{list_url}" target="_blank"
        class="btn btn-secondary">{plural_title}</a>
      <a href="{add_url}" target="_blank"
        class="btn btn-secondary">{add_sentence}</a>
    </div>
    """.format(
        list_url=sub_collection.get_list_url(),
        plural_title=sub_collection.plural_title,
        add_url=sub_collection.get_add_url(),
        add_sentence=sub_collection.add_sentence,
    ))

############################################################
# Set a field in a sub dictionary

def setSubField(fields, field_name, value, key='icon', force_add=False):
    if isinstance(fields, list):
        added = False
        for name, details in fields:
            if name == field_name:
                details[key] = value(field_name) if callable(value) else value
                added = True
        if not added and force_add:
            fields.append((name, { key: value(field_name) if callable(value) else value }))
    else:
        if field_name in fields:
            fields[field_name][key] = value(field_name) if callable(value) else value
        elif force_add:
            fields[field_name] = { key: value(field_name) if callable(value) else value }

def getSubField(fields, l, default=None):
    """
    Takes a list of sub attributes to look for.
    Ex: fields = { 'fruits': ['banana', 'apple'] }, l = ['fruits', 1] will return 'apple'
    """
    ret = fields
    for i in l:
        if isinstance(ret, dict):
            try:
                ret = ret[i]
            except KeyError:
                return default
        elif isinstance(ret, list):
            try:
                ret = ret[i]
            except IndexError:
                return default
        else:
            try:
                ret = getattr(ret, i)
            except AttributeError:
                return default
    return ret

############################################################
# List utils

def flattenListOfLists(list_of_lists):
    return [item for sublist in list_of_lists for item in sublist]

############################################################
# to_fields utils

def toFieldsItemsGallery(d, items, image_field='image_url'):
    d['type'] = 'images_links'
    d['images'] = [{
        'link': item.item_url,
        'ajax_link': item.ajax_item_url,
        'link_text': unicode(item),
        'value': getattr(item, image_field, None),
    } for item in items if getattr(item, image_field, None)]
    return d

def toFieldsAddAttribute(fields, field_name, attribute, value):
    attributes = getSubField(fields, [field_name, 'attributes'], {})
    attributes[attribute] = value
    setSubField(fields, field_name, key='attributes', value=attributes)

def getImageForPrefetched(item, return_field_name=False, in_list=True):
    for image_field in [
            'image_for_prefetched',
    ] + (['top_image_list'] if in_list else []) + [
        'top_image',
        'image_thumbnail_url',
        'image_url',
        'icon_image_url',
    ]:
        if getattr(item, image_field, None):
            if getattr(item, image_field) == -1:
                return (None, None) if return_field_name else None
            image = getattr(item, image_field)
            return (image_field, image) if return_field_name else image
    return (None, None) if return_field_name else None

# Extra fields for navigation between ordered items
def extraFieldsNavigation(item, extra_fields, to_order_field_value=None, field_name='order', starts_at=1, to_queryset=None, to_image=None, allow_more_than_1=True):
    order_field_value = to_order_field_value(item) if to_order_field_value else getattr(item, field_name)
    def _extra_field_episode_navigation(number_operation, navigation_field_name, icon, verbose):
        if to_queryset:
            items = to_queryset(item, order_field_value, number_operation)
        else:
            items = item._meta.model.objects.filter(**{
                field_name: number_operation(order_field_value),
            })
        if not allow_more_than_1:
            items = items[:1]
        for other_item in items:
            extra_fields.append((navigation_field_name, {
                'verbose_name': verbose,
                'icon': icon,
                'link_text': _('Open {thing}').format(thing=unicode(other_item.collection_title).lower()),
                'value': unicode(other_item),
                'link': other_item.item_url,
                'ajax_link': other_item.ajax_item_url,
                'image_for_link': to_image(other_item) if to_image else getImageForPrefetched(other_item),
                'type': 'text_with_link',
            }))
    if order_field_value is not None:
        # Next
        _extra_field_episode_navigation(
            lambda x: x + 1, 'next_{}'.format(item.collection_name), 'toggler',
            _('Next {thing}').format(thing=unicode(item.collection_title).lower()),
        )
        # Previous
        if order_field_value > starts_at:
            _extra_field_episode_navigation(
                lambda x: x - 1, 'previous_{}'.format(item.collection_name), 'back',
                _('Previous {thing}').format(thing=unicode(item.collection_title).lower()),
            )

############################################################
# Join / Split data stored as string in database

def split_data(data):
    """
    Takes a unicode CSV string and return a list of strings.
    """
    if not data:
        return []
    if isinstance(data, list):
        return data
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    def unicode_csv_reader(unicode_csv_data, **kwargs):
        csv_reader = csv.reader(utf_8_encoder(unicode_csv_data), **kwargs)
        for row in csv_reader:
            yield [unicode(cell, 'utf-8') for cell in row]

    reader = unicode_csv_reader([data])
    for reader in reader:
        return [r for r in reader]
    return []

def join_data(*args):
    """
    Takes a list of unicode strings and return a CSV string.
    """
    data = u'\"' + u'","'.join([unicode(value).replace('\n', ' ').replace('\r', ' ').replace('"','\"') for value in args]) + u'\"'
    return data if data != '""' else None

def csvToDict(row, titles_row, snake_case=False):
    return OrderedDict([
        ((titleToSnakeCase(title) if snake_case else title).decode('utf-8'),
         getIndex(row, i, default=u'').decode('utf-8'))
        for i, title in enumerate(titles_row)
    ])

############################################################
# Validators

def FutureOnlyValidator(value):
    if value < datetime.date.today():
        raise ValidationError(_('This date has to be in the future.'), code='future_value')

def PastOnlyValidator(value):
    if value > datetime.date.today():
        raise ValidationError(_('This date cannot be in the future.'), code='past_value')

TIME_REGEX = re.compile('^(?:([01]?\d|2[0-3]):([0-5]?\d):)?([0-5]?\d)$')

TimeValidator = RegexValidator(TIME_REGEX, TimeField.default_error_messages['invalid'], 'invalid')

############################################################
# Image manipulation

def dataToImageFile(data):
    image = NamedTemporaryFile(delete=False)
    image.write(data)
    image.flush()
    return ImageFile(image)

def _imageProcessing(data, filename, processing, return_data=False, return_pil_image=False):
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    pil_image = Image.open(cStringIO.StringIO(data))
    pil_image = processing(pil_image)
    output = io.BytesIO()
    pil_image.save(output, format={
        'png': 'PNG',
        'jpg': 'JPEG',
        'jpeg': 'JPEG',
        'gif': 'GIF',
    }.get(extension.lower(), 'PNG'))
    data = output.getvalue()
    image = dataToImageFile(data)
    if return_pil_image and return_data:
        return data, pil_image, image
    elif return_pil_image:
        return pil_image, image
    elif return_data:
        return data, image
    return image

def imageDataToPilImage(data, filename):
    return _imageProcessing(data, filename, lambda i: i, return_data=False, return_pil_image=True)[0]

def imageThumbnailFromData(data, filename, width=200, height=200, return_data=False, return_pil_image=False):
    def _toThumbnail(image):
        image.thumbnail((width, height))
        return image
    return _imageProcessing(data, filename, _toThumbnail, return_data=return_data, return_pil_image=return_pil_image)

def imageResizeFromData(data, filename, width=200, height=200, return_data=False, return_pil_image=False):
    def _toResize(image):
        return image.resize((width, height))
    return _imageProcessing(data, filename, _toResize, return_data=return_data, return_pil_image=return_pil_image)

def imageSquareThumbnailFromData(data, filename, size=200, return_data=False, return_pil_image=False):
    def _toSquareThumbnail(image):
        width, height = image.size
        if width > height:
            new_height = size
            new_width = getWidthFromHeight(image, new_height)
            top = 0
            left = (new_width / 2) - (size / 2)
            bottom = size
            right = new_width - left
        else:
            new_width = size
            new_height = getHeightFromWidth(image, new_width)
            top = (new_height / 2) - (size / 2)
            left = 0
            bottom = new_height - top
            right = size
        image = image.resize((int(new_width), int(new_height)), Image.ANTIALIAS)
        image = image.crop((int(left), int(top), int(right), int(bottom)))
        return image
    return _imageProcessing(
        data, filename, _toSquareThumbnail, return_data=return_data, return_pil_image=return_pil_image)

def getHeightFromWidth(image, width):
    image_width, image_height = image.size
    return int(math.ceil((width / image_width) * image_height))

def getWidthFromHeight(image, height):
    image_width, image_height = image.size
    return int(math.ceil((height / image_height) * image_width))

def imageResizeScaleFromData(data, filename, width=None, height=None, return_data=False):
    def _toThumbnail(image):
        new_width = width or getWidthFromHeight(image, height)
        new_height = height or getHeightFromWidth(image, width)
        image.thumbnail((new_width, new_height))
        return image
    return _imageProcessing(data, filename, _toThumbnail, return_data=return_data)

def shrinkImageFromData(data, filename, settings={}):
    """
    Optimize images with TinyPNG
    """
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    api_key = getattr(django_settings, 'TINYPNG_API_KEY', None)
    if not api_key or extension not in ['.png', '.jpg', '.jpeg']:
        return dataToImageFile(data)
    tinify.key = api_key
    source = tinify.from_buffer(data)
    if (settings.get('resize', None) == 'fit'
        and settings.get('width', None)
        and settings.get('height', None)):
        source = source.resize(
            method='fit',
            width=settings['width'],
            height=settings['height'],
        )
    elif settings.get('resize', None) == 'fit':
        image = Image.open(cStringIO.StringIO(data))
        max_width = settings.get('max_width', django_settings.MAX_WIDTH)
        max_height = settings.get('max_height', django_settings.MAX_HEIGHT)
        min_width = settings.get('min_width', django_settings.MIN_WIDTH)
        min_height = settings.get('min_height', django_settings.MIN_HEIGHT)
        width, height = image.size
        if width > max_width:
            height = (max_width / width) * height
            width = max_width
        if height > max_height:
            width = (max_height / height) * width
            height = max_height
        if height < min_height:
            height = min_height
        if width < min_width:
            width = min_width
        source = source.resize(
            method='fit',
            width=int(width),
            height=int(height),
        )
    elif settings.get('resize', None) == 'cover':
        source = source.resize(
            method='cover',
            width=settings.get('width', 300),
            height=settings.get('height', 300),
        )
    elif settings.get('resize', None) == 'scale':
        if settings.get('width', None):
            source = source.resize(
                method='scale',
                width=settings['width'],
            )
        if settings.get('height', None):
            source = source.resize(
                method='scale',
                height=settings['height'],
            )
    elif settings.get('resize', None) == 'thumb':
        source = source.resize(
            method='thumb',
            width=settings.get('width', 300),
            height=settings.get('height', 300),
        )
    try:
        data = source.to_buffer()
    except: # Retry without resizing
        try:
            data = tinify.from_buffer(data).to_buffer()
        except: # Just return the original data
            pass
    return dataToImageFile(data)

def localImageToImageFile(path, return_data=False):
    try:
        fd = open(path, 'r')
    except IOError as e:
        if return_data:
            return None, None
        return None
    data = fd.read()
    fd.close()
    image = dataToImageFile(data)
    if return_data:
        return (data, image)
    return image

def saveLocalImageToModel(item, field_name, path, return_data=False):
    data, image = localImageToImageFile(path, return_data=True)
    setattr(item, field_name, image)
    # Remove any cached processed image
    setattr(item, u'_tthumbnail_{}'.format(field_name), None)
    setattr(item, u'_thumbnail_{}'.format(field_name), None)
    setattr(item, u'_original_{}'.format(field_name), None)
    setattr(item, u'_2x_{}'.format(field_name), None)
    if return_data:
        return (data, image)
    return image

def saveLocalImageToModelImagesField(item, path, unique_image_name=None, field_name='images', return_data=False):
    data, image = localImageToImageFile(path, return_data=True)
    image_item = None
    if unique_image_name:
        # Check if exists
        try: image_item = getattr(item, field_name).filter(name=unique_image_name)[0]
        except IndexError: pass
    if not image_item:
        image_item = getattr(item, field_name).model.objects.create(image='')
    image_item.image = image
    image_item._thumbnail_image = None
    image_item.name = unique_image_name
    image_item.save()
    getattr(item, field_name).add(image_item)
    if return_data:
        return (data, image)
    return image

def imageURLToImageFile(url, return_data=False, request_options={}):
    if not url:
        return None
    if url.startswith('//'):
        url = (u'http:' if 'localhost:' in url else u'https:') + url
    img_temp = NamedTemporaryFile(delete=True)
    r = requests.get(url, **request_options)
    if r.status_code != 200:
        if return_data:
            return None, None
        return None
    # Read the streamed image in sections
    for block in r.iter_content(1024 * 8):
        # If no more file then stop
        if not block:
            break
        # Write image block to temporary file
        img_temp.write(block)
    img_temp.flush()
    image = ImageFile(img_temp)
    if return_data:
        image.seek(0)
        return image.read(), image
    return image

def saveImageURLToModel(item, field_name, url, return_data=False, request_options={}):
    data, image = imageURLToImageFile(url, return_data=True, request_options=request_options)
    if not image:
        if return_data:
            return None, None
        return None
    filename = url.split('/')[-1].split('\\')[-1]
    image.name = item._meta.model._meta.get_field(field_name).upload_to(item, filename)
    setattr(item, field_name, image)
    # Remove any cached processed image
    setattr(item, u'_tthumbnail_{}'.format(field_name), None)
    setattr(item, u'_thumbnail_{}'.format(field_name), None)
    setattr(item, u'_original_{}'.format(field_name), None)
    setattr(item, u'_2x_{}'.format(field_name), None)
    if return_data:
        return (data, image)
    return image

def saveGeneratedImage(image, path=None, upload=False, instance=None, model=None, field_name='image', previous_url=None):
    from wand.image import Image as WandImage
    # Save image locally
    if not path or not path.startswith('/'):
        path = os.path.dirname(os.path.dirname(__file__)) + u'/' + (path or 'tmp.png')
    if isinstance(image, WandImage):
        image.save(filename=path)
    elif isinstance(image, Image.Image):
        image.save(path)
    else:
        raise NotImplementedError(u'Can\'t save image, unknwon type ' + unicode(type(image)))
    # Return local image path or upload
    if not upload:
        return path
    # Retrieve existing uploaded image
    if (not instance and not model) or (instance and model):
        raise NotImplementedError('Save image: instance OR model required.')
    if not instance:
        if previous_url:
            try: instance = model.objects.filter(**{ field_name: previous_url })[0]
            except IndexError: pass
        if not instance:
            instance = model.objects.create(**{ field_name: '' })
    saveLocalImageToModel(instance, field_name, path)
    instance.save()
    return instance

def makeImageGrid(
        images, per_line=3, size_per_tile=200, width=None, path=None,
        # Upload options:
        upload=False,
        model=None,
        field_name='image',
        instance=None,
        previous_url=None,
):
    # Create grid
    if width:
        size_per_tile = width / per_line
    total_lines = math.ceil(len(images) / per_line)
    grid_width = int(size_per_tile * per_line)
    grid_height = int(size_per_tile * total_lines)
    grid_image = Image.new('RGBA', (grid_width, grid_height))
    line = 0
    position = 0
    for image in images:
        if isinstance(image, basestring):
            data, imagefile = imageURLToImageFile(image, return_data=True)
            if not imagefile:
                continue
            name = imagefile.name
        else:
            data = image.read()
            name = image.name
        if not data:
            continue
        pil_image, _imagefile = imageSquareThumbnailFromData(
            data, filename=name, size=size_per_tile, return_pil_image=True)
        top = int(size_per_tile * line)
        left = int(size_per_tile * position)
        grid_image.paste(pil_image, box=(left, top))
        if position == (per_line - 1):
            line += 1
            position = 0
        else:
            position += 1
    # Save
    return saveGeneratedImage(
        grid_image, path=path, upload=upload, instance=instance,
        model=model, field_name=field_name, previous_url=previous_url,
    )

def makeBadgeImage(badge=None, badge_image=None, badge_rank=None, width=None, path=None, upload=False, instance=None, model=None, field_name='image', previous_url=None, with_padding=0):
    # Either badge or badge_image required
    from wand.image import Image as WandImage
    # /!\ Can't be called at global level
    if badge:
        badge_image = badge.image
        badge_rank = badge.rank
    # Get border
    filename = 'badge{}'.format(badge_rank or '')
    border_image_url = staticImageURL(filename, folder='badges', full=True)
    try:
        border_image = WandImage(file=urllib2.urlopen(border_image_url))
    except:
        border_image = WandImage(file=urllib2.urlopen('https://i.imgur.com/g2bVQoS.png'))
    width = width or border_image.width
    if width != border_image.width:
        border_image.resize(width=width, height=width)
    # Get badge image
    badge_image_data = badge_image.read()
    badge_image = WandImage(blob=badge_image_data)
    badge_image.resize(width=width, height=width)
    # Initialize image
    image = WandImage(width=width + (with_padding * 2), height=width)
    # Add badge image + border to image
    image.composite(badge_image, left=with_padding, top=0)
    image.composite(border_image, left=with_padding, top=0)
    # Save
    return saveGeneratedImage(
        image, upload=upload, instance=instance,
        model=model, field_name=field_name, previous_url=previous_url,
    )

############################################################
# Image URLs

def staticFileURL(
        path, folder=None, extension=None, versionned=True,
        full=False, with_static_url=True, static_url=None,
        default_extension=None, default_folder=None):
    # /!\ Can't be called at global level, unless with_static_url=False
    if not hasValue(path, false_bool_is_value=False):
        return None
    path = unicode(path)
    if not extension and '.' not in path and default_extension:
        extension = default_extension
    if isFullURL(path):
        return path
    if with_static_url and not static_url:
        static_url = RAW_CONTEXT['static_url'] if not full else RAW_CONTEXT['full_static_url']
    return u'{static}{default_folder}{folder}{path}{extension}{version}'.format(
        static=static_url if with_static_url else '',
        default_folder=default_folder or '',
        folder=u'{}/'.format(folder) if folder else '',
        path=path,
        extension=u'.{}'.format(extension) if extension else '',
        version=u'' if not versionned else u'{suffix}{version}'.format(
            suffix='?' if '?' not in path and '?' not in (extension or '') else '&',
            version=RAW_CONTEXT['static_files_version'] if with_static_url else '',
        ),
    )

def staticImageURL(
        path, folder=None, extension=None, versionned=True,
        full=False, static_url=None, with_static_url=True):
    # /!\ Can't be called at global level, unless with_static_url=False
    if failSafe(lambda: path.startswith('img/'), exceptions=[ AttributeError ]):
        path = path[len('img/'):]
    return staticFileURL(
        path, folder=folder, extension=extension, versionned=versionned, full=full,
        static_url=static_url, default_extension='png', default_folder='img/', with_static_url=with_static_url)

def linkToImageURL(link):
    # /!\ Can't be called at global level
    return staticImageURL(u'links/{}'.format(link.i_type), extension=u'png')

############################################################
# HTML tools

def toTimeZoneDateTime(date, timezones, ago=False):
    if not date:
        return u''
    date = torfc2822(date)
    return u'{}{}'.format(u'<br>'.join([
        u'<span class="timezone" data-to-timezone="{timezone}"><span class="datetime">{date}</span>(<span class="current_timezone">UTC</span>)</span>'.format(
            timezone=timezone,
            date=date,
        )
        for timezone in timezones
    ]), u'<br><small class="text-muted"><span class="timezone" data-timeago="true" style="display: none;"><span class="datetime">{date}</span></span></small>'.format(
        date=date,
    ) if ago else '')

def toCountDown(date, sentence, classes=None):
    if not date or date < timezone.now():
        return u''
    return u'<span class="countdown {classes}" data-date="{date}" data-format="{sentence}"></span>'.format(
        date=torfc2822(date), sentence=sentence, classes=u' '.join(classes or []),
    )

def getColSize(per_line):
    if per_line == 5:
        return 'special-5'
    elif per_line == 7:
        return 'special-7'
    elif per_line == 8:
        return 'special-8'
    elif per_line == 9:
        return 'special-9'
    return int(math.ceil(12 / (per_line or 1)))

def getColOffset(align='right', per_line=5, total=15, i=0):
    """
    If a class exists for the right offset: True, offset (ex: 8, can use class="... col-md-offset-8")
    If it's not a rounded offset: False, margin in % (ex: 75, can use style="margin-left: 75%;")
    """
    if i != math.floor(total / per_line) * per_line:
        return False, None
    number_of_empty_items = per_line - (total - i)
    if align == 'right':
        offset = number_of_empty_items * (12 / per_line)
    elif align == 'center':
        offset = (number_of_empty_items * (12 / per_line)) / 2
    if offset and math.floor(offset) != offset:
        return False, (100 / per_line) * number_of_empty_items
    return True, int(offset) if offset else None

ALERT_TEMPLATE = u"""
<div class="alert alert-{alert_type}">
  <div class="row">
    <div class="col-sm-2 text-center hidden-xs">
      <i class="flaticon-{alert_icon} fontx2"></i>
    </div>
    <div class="col-sm-{alert_col_size}">
      {alert_title}
      {alert_message}
    </div>
    {alert_button}
  </div>
</div><br>
"""

ALERT_BUTTON_TEMPLATE = u"""
<div class="col-sm-3 hidden-xs">
  <a href="{url}" class="btn btn-main btn-lg btn-block" target="_blank">
    {verbose}
    <i class="flaticon-{icon}"></i>
  </a>
</div>
"""
ALERT_BUTTON_TEMPLATE_VARIABLES = [ 'url', 'verbose', 'icon' ]

def HTMLAlert(type='warning', flaticon='about', title=None, message=None, button=None):
    """
    button is a dict that contains url and verbose
    """
    if button:
        alert_button = {
            key: button.get(key, u'')
            for key in ALERT_BUTTON_TEMPLATE_VARIABLES
        }
    return markSafeFormat(
        ALERT_TEMPLATE,
        alert_type=type,
        alert_icon=flaticon,
        alert_title=markSafeFormat(u'<h4>{title}</h4>', title=title) if title else '',
        alert_message=message or '',
        alert_col_size=7 if button else 10,
        alert_button=markSafeFormat(ALERT_BUTTON_TEMPLATE, **alert_button) if button else '',
    )

markSafe = mark_safe
markUnsafe = escape

def isMarkedSafe(string):
    return isinstance(string, SafeText)

def _markSafeFormatEscapeOrNot(string):
    return unicode(string if (
        isinstance(string, SafeText)
        or isinstance(string, SafeBytes)
    ) else escape(string))

def markSafeFormat(string, *args, **kwargs):
    """The first string doesn't need to be marked safe, it's assumed safe"""
    return mark_safe(string.format(*[
        _markSafeFormatEscapeOrNot(arg) for arg in args
    ], **{
        key: _markSafeFormatEscapeOrNot(value) for key, value in kwargs.items()
    }))

def markSafeReplace(string, replace_from, replace_to):
    return markSafe(
        _markSafeFormatEscapeOrNot(string).replace(
            _markSafeFormatEscapeOrNot(replace_from),
            _markSafeFormatEscapeOrNot(replace_to),
        )
    )

def markSafeStrip(string):
    return markSafe(_markSafeFormatEscapeOrNot(string).strip())

COMMA_PER_LANGUAGE = {
    'en': u', ', # kr, ru, th use English comma
    'ja': u'、',
    'zh-hant': u'，',
    'zh-hans': u'，',
}
_mark_safe = mark_safe

def clearJoin(strings, separator=u''):
    return separator.join([ s for s in strings if s ])

def getWesternName(t_name, is_western_name=False, language=None):
    """
    When names are assumed to be Japanese, they're assumed to be stored with last name then first name.
    Because western names are not displayed that way, in the exception that the current item has a
    western name, this function will do the job of swapping names for display.
    """
    if is_western_name:
        language = language or get_language()
        if language == 'ja':
            return u'・'.join(reversed(t_name.split(' ')))
        if language in ['zh-hant', 'zh-hans']:
            return u'·'.join(reversed(t_name.split(' ')))
        return u' '.join(reversed(t_name.split(' ')))
    return t_name

WESTERN_NAME_HELP_TEXT = u"""
Family name should always be first.
Ex: "Kousaka Honoka" or "Verde Emma".
Use spaces to separate names.
If a name has multiple words, copy-paste this character to use as space: " ".
"""

WESTERN_OPTION_HELP_TEXT = u"""
When checked, the order of the name will be swapped to look more like a Western name.
Ex: "Emma Verde" or "エマ・ヴェルデ"
"""

############################################################
# Form labels and help texts

def markdownHelpText(request=None, ajax=False):
    # /!\ Can't be called at global level
    if ('help' in RAW_CONTEXT['all_enabled']
        and (not request or request.LANGUAGE_CODE not in RAW_CONTEXT['languages_cant_speak_english'])):
        return markSafeFormat(
            u'{} <a href="/help/Markdown" {} target="_blank">{}.</a>',
            _(u'You may use Markdown formatting.'),
            markSafe(u'data-ajax-url="/ajax/help/Markdown/"') if not ajax else '',
            _(u'Learn more'),
        )
    else:
        return _(u'You may use Markdown formatting.')

def flaticonHelpText(help_text=None):
    # /!\ Can't be called at global level
    return markSafeFormat(
        u'{}{}{}',
        help_text or '',
        ' - ' if help_text else '',
        markSafeFormat(
            '<a href="{}" target="_blank">{}</a>',
            staticFileURL('css/flaticon.html'),
            _('View all'),
        ),
    )

def suggestFlaticonFromFieldName(field_name, default='about'):
    for base_field_name, icon in DEFAULT_ICONS_BASED_ON_NAMES.items():
        if fieldNameMatch(field_name, base_field_name):
            return icon
    return default

def getSearchSingleFieldLabel(field_name, model_class, labels={}, translated_fields=[]):
    if field_name in labels:
        return labels[field_name]
    if isTranslationField(field_name, translated_fields):
        return ''
    try: return model_class._meta.get_field(field_name)._verbose_name
    except FieldDoesNotExist: return None

def getSearchFieldHelpText(search_fields, model_class, labels, translated_fields, all_lower=False):
    field_labels = []
    and_more = False
    first = True
    for field_name in search_fields:
        label = getSearchSingleFieldLabel(field_name, model_class, labels, translated_fields)
        # If a label is equal to '' it means it can safely be ignored without adding '...'
        if label is None:
            and_more = True
        elif label:
            label = unicode(label)
            field_labels.append(label if first and not all_lower else label.lower())
            first = False
    if field_labels:
        return u'{}{}'.format(
            u', '.join(field_labels),
            ', ...' if and_more else '',
        )
    return None

############################################################
# Async update function

def locationOnChange(user_preferences):
    # This function is only called by the async script so to avoid loading includes when the site is running,
    # it's included within the function
    import sys
    from geopy.geocoders import Nominatim
    from tools import generateMap

    geolocator = Nominatim()
    try:
        location = geolocator.geocode(user_preferences.location)
        if location is not None:
            user_preferences.latitude = location.latitude
            user_preferences.longitude = location.longitude
            user_preferences.location_changed = False
            user_preferences.save()
            print user_preferences.user, user_preferences.location, user_preferences.latitude, user_preferences.longitude
            generateMap()
        else:
            user_preferences.location_changed = False
            user_preferences.save()
            print user_preferences.user, user_preferences.location, 'Invalid location'
    except:
        print u'{} {} Error, {}'.format(user_preferences.user, user_preferences.location, sys.exc_info()[0])
        # Will not mark as not changed, so it will be retried at next iteration
    return True

############################################################
# Translations

def duplicateTranslation(model, field, term, only_for_language=None, print_log=True, html_log=False):
    logs = []
    items = list(model.objects.filter(**{ field: term }))
    known_translations = []
    for item in items:
        for language, translation in getattr(item, u'{}s'.format(field[2:] if field.startswith('m_') else field)).items():
            if only_for_language and language != only_for_language:
                continue
            if language not in known_translations:
                for s_item in items:
                    existing = getattr(s_item, u'{}s'.format(field[2:] if field.startswith('m_') else field))
                    if language not in existing:
                        s_item.add_d(u'{}s'.format(field), language, translation[1] if field.startswith('m_') else translation)
                        log = u'Add {language} translations to {open_a}#{id} {item}{close_a}'.format(
                            language=language,
                            open_a=u'<a href="{}" target="_blank">'.format(s_item.http_item_url) if html_log else '',
                            id=s_item.pk,
                            item=s_item,
                            close_a='</a>' if html_log else '',
                        )
                        if print_log:
                            print log
                        logs.append(log)
                    s_item.save()
                known_translations.append(language)
    return logs

def _translations_count_has(model, field, term, language):
    return model.objects.filter(**{
        field: term,
        u'd_{}s__icontains'.format(field): '"{}"'.format(language),
    }).count()

def _translations_count_to_apply_to(model, field, term, language):
    return model.objects.filter(**{
        field: term,
    }).exclude(**{
        u'd_{}s__icontains'.format(field): '"{}"'.format(language),
    }).count()

def findAllTranslations(model, field, only_for_language=None, with_count_has=True, with_count_to_apply_to=True):
    """
    Returns a dict of:
    base term in English
    -> (Dict of:
       Language
       -> (List of translations,
           Count other item with term present in that language,
           Count how many items could get their translation duplicated automatically),
       total can be duplicated to,
       display term (for markdown))
    """
    translations = {}
    for item in model.objects.filter(**{ u'{}__isnull'.format(field): False}).exclude(**{ field: '' }):
        term = getattr(item, field)
        if term not in translations:
            translations[term] = {}
        for language, translation in getattr(item, u'{}s'.format(field[2:] if field.startswith('m_') else field)).items():
            if only_for_language and language != only_for_language:
                continue
            if language not in translations[term]:
                translations[term][language] = (
                    [],
                    _translations_count_has(model, field, term, language) if with_count_has else 0,
                    _translations_count_to_apply_to(model, field, term, language) if with_count_to_apply_to else 0,
                )
            if translation not in translations[term][language][0]:
                translations[term][language][0].append(
                    mark_safe(u'<p class="to-markdown">{}</p>'.format(translation[1]))
                    if field.startswith('m_') else translation)
    for term in translations.keys():
        translations[term] = (
            translations[term],
            reduce(lambda a, b: a + b, [_t[2] for _t in translations[term].values()], 0),
            mark_safe(u'<p class="to-markdown">{}</p>'.format(term)) if field.startswith('m_') else term,
        )

    return translations

def rfc3066ToIso6392(language):
    return RFC3066_TO_ISO6392.get(language, language)

googleTranslateFixLanguage = rfc3066ToIso6392

def translationSentence(from_language, to_language):
    return unicode(_(u'Translate from %(from_language)s to %(to_language)s')).replace(
        '%(from_language)s', unicode(LANGUAGES_DICT.get(from_language, '')),
    ).replace(
        '%(to_language)s', unicode(LANGUAGES_DICT.get(to_language, '')),
    )

def translationURL(
        value, from_language='en', to_language=None,
        with_wrapper=True, markdown=False, one_line=False,
        show_value=True, sentence=None,
):
    if not to_language:
        to_language = get_language()
    url = u'https://translate.google.com/?sl={from_language}&tl={to_language}&text={value}&op=translate'.format(
        to_language=googleTranslateFixLanguage(to_language),
        from_language=googleTranslateFixLanguage(from_language),
        value=urlquote(value, ''),
    )
    if with_wrapper:
        return markSafeFormat(
            (
                u'{value}{newline}[{translate}]({url})'
                if markdown else
                u'{value}{newline}<a href="{url}" target="_blank"><small class="text-muted">{translate} <i class="flaticon-link"></i></small></a>'),
            newline=' ' if one_line or not show_value else ('\n\n' if markdown else markSafe('<br>')),
            url=url,
            value=value if show_value else u'',
            translate=sentence or translationSentence(from_language=from_language, to_language=to_language),
        )
    return url

def openGoogleTranslateURL(url, from_language='en', to_language=None):
    if not to_language: to_language = get_language()
    return u'https://translate.google.com/translate?js=n&sl={from_language}&tl={to_language}&u={url}'.format(
        from_language=googleTranslateFixLanguage(from_language), to_language=googleTranslateFixLanguage(to_language), url=url)

def openGoogleTranslateHTMLLink(url, from_language='en', to_language=None):
    return u'<small><a href="{url}" class="text-muted">{sentence}</a></small>'.format(
        url=openGoogleTranslateURL(url, from_language=from_language, to_language=to_language),
        sentence=translationSentence(from_language, to_language),
    )

def isTranslationField(field_name, translated_fields):
    field_name = field_name.split('__')[-1]
    if (field_name.startswith('d_') and field_name.endswith('s')
        and field_name[2:-1] in translated_fields):
        return True
    for translated_field in translated_fields:
        if field_name.endswith(translated_field):
            for language, verbose_language in LANGUAGES_NAMES.items():
                if (field_name == u'{}_{}'.format(verbose_language, translated_field)
                    or field_name == u'{}_{}'.format(language, translated_field)):
                    return True
    return False

############################################################
# Homepage previews

def artSettingsToGetParameters(settings):
    # /!\ Can't be called at global level
    parameters = {}
    for k, v in settings.items():
        if k in ['gradient', 'ribbon']:
            v = int(v)
        if k == 'position':
            for pk, pv in v.items():
                parameters['position_{}_preview'.format(pk)] = pv
        elif k == 'url':
            parameters['preview'] = urllib.quote(staticImageURL(v).encode('utf8'))
        elif k == 'foreground_url':
            parameters['foreground_preview'] = urllib.quote(staticImageURL(v).encode('utf8'))
        else:
            parameters[u'{}_preview'.format(k)] = v
    return parameters

def artPreviewButtons(view, buttons, request, item, images, get_parameter='url', settings=None):
    if (not request.user.is_authenticated()
        or not request.user.hasPermission('manage_main_items')):
        return
    for field_name, in_use in (images if isinstance(images, dict) else { k: None for k in images }).items():
        image = getattr(item, u'{}_url'.format(field_name), None)
        if not image:
            continue
        parameters = { get_parameter: image }
        if settings:
            parameters.update(artSettingsToGetParameters(settings))
        if get_parameter == 'preview':
            parameters['hd_url_preview'] = getattr(item, u'{}_force_2x_url'.format(field_name), None)
        buttons[u'preview_{}'.format(field_name)] = {
            'classes': view.item_buttons_classes + ['staff-only'],
            'show': True,
            'url': addParametersToURL('/', parameters),
            'icon': 'home',
            'title': u'Preview {} on homepage'.format(toHumanReadable(field_name, warning=False)),
            'subtitle': None if in_use is None else u'Currently {}abled'.format('en' if in_use else 'dis'),
            'has_permissions': True,
            'open_in_new_window': True,
        }

BASE_BUTTON = {
    'show': True,
    'has_permissions': True,
    'title': None,
    'icon': False,
    'image': False,
    'url': False,
    'open_in_new_window': False,
    'ajax_url': False,
    'ajax_title': False, # By default will use title
}

def baseButton(
        button_name=None, buttons=None, extras=None, extra_classes=None,
        # Either:
        view=None, request=None, context=None, item=None,
        # Or:
        classes=None,
):
    if not classes:
        classes = view.get_item_buttons_classes(request, context, item=item)
    if extra_classes:
        classes += extra_classes
    button = mergeDicts(BASE_BUTTON, { 'classes': classes })
    if extras:
        button = updatedDict(button, extras)
    if buttons is not None:
        buttons[button_name] = button
    return button

############################################################
# Create user

def create_user(user_model, username, email=None, password=None, language='en', is_superuser=False):
    new_user = getattr(user_model.objects, 'create_user' if not is_superuser else 'create_superuser')(
        username=username,
        email=email or u'{}@yopmail.com'.format(username),
        password=username * 2,
    )
    preferences = user_model.preferences.related.model.objects.create(
        user=new_user,
        i_language=language,
    )
    new_user.preferences = preferences
    return new_user

def get_default_owner(user_model):
    try:
        return user_model.objects.filter(is_superuser=True).order_by('-id')[0]
    except IndexError:
        return create_user(user_model, 'db0', is_superuser=True)

############################################################
# Seasonal

def adventCalendar(request, context):
    # /!\ Can't be called at global level
    """
    In python:
    - add list of open days to js_variables
    - add list of images to js_variables
    - add corner popup for advent calendar
    In js:
    - check if today is in the calendar
    - yes: do nothing
    - no: show button to open
    - button to open is ajax call to open calendar with GET parameter for today's day
    If 25th:
    - add badge
    """
    if not request.user.is_authenticated():
        return
    today = datetime.date.today()
    if today.month != 12 or today.day > 26:
        return
    if 'js_variables' not in context:
        context['js_variables'] = {}
    context['js_variables']['advent_calendar_days_opened'] = request.user.preferences.extra.get(
        'advent_calendar{}'.format(today.year), '').split(',')
    context['corner_popups']['advent_calendar'] = {
        'title': _('Merry Christmas!'),
        'image': staticImageURL(django_settings.STAFF_CONFIGURATIONS.get(
            'season_advent_calendar_corner_popup_image', None)),
        'image_overflow': context['corner_popup_image_overflow'],
        'buttons': {
            'open_calendar': {
                'url': '/adventcalendar/',
                'title': _('Open {thing}').format(thing=_('Advent calendar').lower()),
                'ajax_url': '/ajax/adventcalendar/',
            },
        },
        'allow_close_once': True,
    }
