import json, datetime
from collections import OrderedDict
from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields.files import ImageFieldFile
from django.conf import settings as django_settings
from django.utils.translation import gettext_lazy as _, get_language
from django.utils import timezone
from magi.utils import (
    tourldash,
    getMagiCollection,
    join_data,
    split_data,
    AttrDict,
    getSubField,
    LANGUAGES_NAMES,
    listUnique,
    modelHasField,
    uploadToRandom,
    uploadThumb,
    staticImageURL,
)

############################################################
# Utils for translated fields

ALL_LANGUAGES = django_settings.LANGUAGES

ALL_ALT_LANGUAGES = [
    (_code, _verbose) for _code, _verbose in django_settings.LANGUAGES
    if _code != django_settings.LANGUAGE_CODE
]
NON_LATIN_LANGUAGES = [
    (_code, _verbose) for _code, _verbose in django_settings.LANGUAGES
    if _code in [ 'ja', 'ru', 'zh-hans', 'zh-hant', 'kr', 'th']
]

############################################################
# Utils for images / files

def get_file_url_from_path(filePath):
    if not filePath:
        return None
    fileURL = str(filePath)
    if '//' in fileURL:
        return fileURL
    if fileURL.startswith(django_settings.SITE + '/'):
        fileURL = fileURL.replace(django_settings.SITE + '/', '')
    if getattr(django_settings, 'DEBUG', False):
        uploaded_files_url = getattr(django_settings, 'UPLOADED_FILES_URL', None)
        if uploaded_files_url:
            return u'{}{}'.format(uploaded_files_url, fileURL)
    return u'{}{}'.format(django_settings.SITE_STATIC_URL, fileURL)

def get_file_url(instance, file_name='file'):
    return get_file_url_from_path(getattr(instance, file_name))

def get_http_file_url_from_path(filePath):
    fileURL = get_file_url_from_path(filePath)
    if not fileURL:
        return None
    if 'http' not in fileURL:
        fileURL = (u'http:' if 'localhost:' in fileURL else u'https:') + fileURL
    return fileURL

def get_http_file_url(instance, file_name='file'):
    return get_http_file_url_from_path(getattr(instance, file_name))

get_image_url_from_path = get_file_url_from_path
get_image_url = get_file_url
get_http_image_url_from_path = get_http_file_url_from_path
get_http_image_url = get_http_file_url

############################################################
# Utils for choices

def i_choices(choices, translation=True):
    if not choices:
        return []
    return [(i, choice[1 if translation else 0] if isinstance(choice, tuple) else choice) for i, choice in enumerate(choices.items() if isinstance(choices, dict) else choices)]

def getInfoFromChoices(field_name, details, key, default=None):
    def _getInfo(instance):
        value = getattr(instance, field_name)
        if (not value
            or value not in details
            or ((key >= len(details[value])
                if isinstance(details[value], tuple)
                else (key not in details[value])))
        ):
            if callable(default):
                return default(instance)
            return default
        return details[value][key]
    return _getInfo

############################################################
# Utils for owner

def get_selector_to_owner(cls):
    if cls.fk_as_owner:
        return u'{}__owner'.format(cls.fk_as_owner)
    return 'owner'

def get_owners_queryset(cls, user):
    if not cls.fk_as_owner:
        return [user]
    return cls._meta.get_field(cls.fk_as_owner).remote_field.model.objects.filter(**{
        cls.selector_to_owner()[(len(cls.fk_as_owner) + 2):]:
        user,
    })

def get_owner_ids(cls, user):
    if cls.fk_as_owner:
        return list(cls.owners_queryset(user).values_list('id', flat=True))
    return [user.id]

def get_owner_from_pk(cls, owner_pk):
    """
    Always performs a database query, use with caution.
    """
    return cls._meta.get_field(cls.fk_as_owner or 'owner').remote_field.model.objects.get(pk=owner_pk)

def get_owner_collection(cls):
    if cls.fk_as_owner:
        return getMagiCollection(cls.fk_as_owner)
    return getMagiCollection('user')

def get_allow_multiple_per_owner(cls):
    # todo
    print(cls.owner)
    return cls.owner

def get_is_owner(instance, user):
    return user and instance.owner_id == user.id

def get_owner_str(instance):
    if instance.fk_as_owner:
        fk_as_owner = getattr(instance, u'cached_{}'.format(instance.fk_as_owner))
        if not fk_as_owner:
            fk_as_owner = getattr(instance, instance.fk_as_owner)
        return fk_as_owner.unicode if hasattr(fk_as_owner, 'unicode') else str(fk_as_owner)
    return instance.owner.unicode if hasattr(instance.owner, 'unicode') else str(instance.owner)

def get_real_owner(instance):
    """
    In case of a cached owner, ensure the retriaval of the actual owner object.
    Performs extra query, use with caution.
    """
    if isinstance(instance, User):
        return instance
    if isinstance(instance.__class__.owner, property):
        if not getattr(instance, '_real_owner', None):
            instance._real_owner = getSubField(type(instance).objects.select_related(instance.selector_to_owner()).get(pk=instance.pk), instance.selector_to_owner().split('__'))
        return instance._real_owner
    return instance.owner

############################################################
# BaseMagiModel

class BaseMagiModel(models.Model):
    """
    Can be used for your models that don't have an associated MagiCollection.

    It comes with:
    - helpers for owner
    - helpers for i_ fields
      - i_something: raw integer value
      - something: string representation
      - t_something: i18n string representation
    - helpers for images
      - image_url, http_image_url where "image" is the name of the image field
    - tinypng_settings
    - helpers for CSV values
      - c_something: raw string
      - something: list of CSV values
      - t_something: list of translated values
      - add_c: add some new strings in the list
      - remove_c: remove some strings from the list
      - save_c: replace the full list of existing strings
    """
    tinypng_settings = {}
    request = None

    fk_as_owner = None
    selector_to_owner = classmethod(get_selector_to_owner)
    owners_queryset = classmethod(get_owners_queryset)
    owner_ids = classmethod(get_owner_ids)
    get_owner_from_pk = classmethod(get_owner_from_pk)
    allow_multiple_per_owner = classmethod(get_allow_multiple_per_owner)
    owner_collection = classmethod(get_owner_collection)
    is_owner = get_is_owner
    owner_unicode = property(get_owner_str)
    real_owner = property(get_real_owner)

    @classmethod
    def get_int_choices(self, field_name):
        """
        Return a list of integers that correspond to valid choices
        """
        return range(0, len(getattr(self, '{name}_CHOICES'.format(name=field_name.upper()))) + 1)

    @classmethod
    def get_choices(self, field_name):
        """
        Return value is a list of tuples with:
           (int, (string, translated string))
        or (int, string)
        """
        field_name = field_name[2:] if field_name.startswith('i_') else field_name
        try:
            choices = getattr(self, '{name}_CHOICES'.format(name=field_name.upper()))
            if getattr(self, u'{name}_WITHOUT_I_CHOICES'.format(name=field_name.upper()), False):
                return [(c[0], c) for c in choices]
            return list(enumerate(choices))
        except AttributeError:
            return list(self._meta.get_field('i_{name}'.format(name=field_name)).choices)

    @classmethod
    def get_i(self, field_name, string):
        """
        Takes a string value of a choice and return its internal value
        field_name = without i_
        """
        field_name = field_name[2:] if field_name.startswith('i_') else field_name
        try:
            return next(
                index
                for index, c in self.get_choices(field_name)
                if (c[0] if isinstance(c, tuple) else c) == string
            )
        except StopIteration:
            if string is None:
                return None
            raise KeyError(string)

    @classmethod
    def get_reverse_i(self, field_name, i):
        """
        Takes an int value of a choice and return its string value
        field_name = without i_
        """
        field_name = field_name[2:] if field_name.startswith('i_') else field_name
        try:
            return next(
                (c[0] if isinstance(c, tuple) else c)
                for index, c in self.get_choices(field_name)
                if str(index) == str(i)
            )
        except StopIteration:
            if i is None or i == '':
                return None
            raise KeyError(i)

    @classmethod
    def get_verbose_i(self, field_name, i):
        """
        Takes an int value of a choice and return its verbose value
        field_name = without i_
        """
        field_name = field_name[2:] if field_name.startswith('i_') else field_name
        try:
            return next(
                (c[1] if isinstance(c, tuple) else c)
                for index, c in self.get_choices(field_name)
                if str(index) == str(i)
            )
        except StopIteration:
            if i is None:
                return None
            raise KeyError(i)

    @classmethod
    def _dict_choices(self, field_name):
        return OrderedDict([
            ((choice[0] if isinstance(choice, tuple) else choice),
            (choice[1] if isinstance(choice, tuple) else _(choice)))
            for choice in getattr(self, u'{name}_CHOICES'.format(name=field_name.upper()), [])
        ])

    @classmethod
    def get_csv_values(self, field_name, values, translated=True):
        if not isinstance(values, list):
            values = split_data(values)
        if not translated:
            return values
        choices = self._dict_choices(field_name)
        return OrderedDict([(c, choices.get(c, c)) for c in values])

    @classmethod
    def get_dict_values(self, field_name, values, translated):
        if not values: return {}
        d = json.loads(values)
        if not translated:
            return d
        choices = self._dict_choices(field_name)
        return OrderedDict([
            (key, {
                'value': d[key],
                'verbose': choices.get(key, key),
            })
            for key in choices.keys()
            if key in d
        ])

    @classmethod
    def get_markdown_dict_values(self, field_name, values, translated):
        return OrderedDict([
            (k, (False, v))
            for k, v in self.get_dict_values(field_name, values, translated).items()
        ])

    @classmethod
    def get_json_value(self, field_name, value):
        if not value: return None
        return json.loads(value)

    @classmethod
    def cached_json_extra(self, field_name, d):
        # Get original model class for cached thing
        try: original_cls = self._meta.get_field(field_name).remote_field.model
        except FieldDoesNotExist: original_cls = None
        original_cls = getattr(self, u'_cache_{}_fk_class'.format(field_name), original_cls)
        if callable(original_cls): original_cls = original_cls()
        # Call pre if provided
        if hasattr(self, u'cached_{}_pre'.format(field_name)):
            getattr(self, u'cached_{}_pre'.format(field_name))(d)
        # Add id if missing
        if original_cls and 'id' not in d:
            d['id'] = getattr(self, u'{}_id'.format(field_name), None)
        # Add default unicode if missing
        if 'unicode' not in d:
            d['unicode'] = d['name'] if 'name' in d else (str(d['id']) if 'id' in d else '?')
        if 'id' in d:
            if 'pk' not in d:
                d['pk'] = d['id']
            # Set collection item URLs
            collection_name = getattr(self, u'_cached_{}_collection_name'.format(field_name), field_name)
            if 'item_url' not in d:
                d['item_url'] = u'/{}/{}/{}/'.format(collection_name, d['id'], tourldash(d['unicode']))
            if 'ajax_item_url' not in d:
                d['ajax_item_url'] = u'/ajax/{}/{}/'.format(collection_name, d['id'])
            if 'full_item_url' not in d:
                d['full_item_url'] = u'{}{}/{}/{}/'.format(django_settings.SITE_URL, collection_name, d['id'], tourldash(d['unicode']))
            if 'http_item_url' not in d:
                d['http_item_url'] = u'https:{}'.format(d['full_item_url']) if 'http' not in d['full_item_url'] else d['full_item_url']

        # Set image url helpers
        for image_field in getattr(self, u'_cache_{}_images'.format(field_name), []) + ['image']:
            if image_field in d:
                if u'{}_url'.format(image_field) not in d:
                    d[u'{}_url'.format(image_field)] = get_image_url_from_path(d[image_field])
                if u'http_{}_url'.format(image_field) not in d:
                    d[u'http_{}_url'.format(image_field)] = get_http_image_url_from_path(d[image_field])

        if original_cls:
            for k in list(d.keys()):
                # i_ fields
                if k.startswith('i_'):
                    d[k[2:]] = original_cls.get_reverse_i(k[2:], d[k])
                    d['t_{}'.format(k[2:])] = original_cls.get_verbose_i(k[2:], d[k])

        # Translated fields
        language = get_language()
        for k, v in d.items():
            if isinstance(d.get(u'{}s'.format(k), None), dict):
                if language == 'en':
                    d['t_{}'.format(k)] = v
                else:
                    d['t_{}'.format(k)] = d[u'{}s'.format(k)].get(language, v)
        # Call extra if provided
        if hasattr(self, u'cached_{}_extra'.format(field_name)):
            getattr(self, u'cached_{}_extra'.format(field_name))(d)
        return d

    @classmethod
    def get_cached_json(self, field_name, value):
        if value is None: return None
        d = json.loads(value)
        if d is None: return None
        if isinstance(d, list):
            d = map(lambda _d: AttrDict(self.cached_json_extra(field_name, _d)), d)
        else:
            d = AttrDict(self.cached_json_extra(field_name, d))
        return d

    @classmethod
    def get_cached_csv(self, field_name, value):
        if value is None: return []
        values = split_data(value)
        map_method = getattr(self, u'cached_{}_map'.format(field_name), None)
        return [map_method(i) for i in values] if map_method else values

    def _get_markdown_value(self, field_name):
        html = getattr(self, u'_cache_{}'.format(field_name), None)
        if html:
            return True, html
        markdown = getattr(self, u'm_{}'.format(field_name))
        return False, markdown

    def add_c(self, field_name, to_add):
        """
        Add strings from a CSV formatted c_something
        """
        current_c = getattr(self, field_name)
        setattr(self, 'c_{name}'.format(name=field_name),
                join_data(*(current_c + [c for c in to_add if c not in current_c])))

    def remove_c(self, field_name, to_remove):
        """
        Remove strings to a CSV formatted c_something
        """
        current_c = getattr(self, field_name)
        setattr(self, 'c_{name}'.format(name=field_name),
                join_data(*[c for c in current_c if c not in to_remove]))

    def save_c(self, field_name, c):
        """
        Completely replace any existing CSV formatted list into c_something
        """
        setattr(self, 'c_{name}'.format(name=field_name), join_data(*c) if c is not None else None)

    def add_d(self, field_name, key, value):
        current_d = getattr(self, field_name[2:] if field_name.startswith('m_') else field_name)
        current_d[key] = value
        setattr(self, u'd_{name}'.format(name=field_name), json.dumps(current_d))

    def remove_d(self, field_name, key):
        current_d = getattr(self, field_name[2:] if field_name.startswith('m_') else field_name)
        del(current_d[key])
        setattr(self, u'd_{name}'.format(name=field_name), json.dumps(current_d) if current_d else None)

    def save_d(self, field_name, d):
        setattr(self, u'd_{name}'.format(name=field_name), json.dumps(d) if d else None)

    def save_j(self, field_name, j):
        setattr(self, u'j_{name}'.format(name=field_name), json.dumps(j) if j else None)

    def _to_cache(self, field_name):
        to_cache_method = getattr(self, u'to_cache_{}'.format(field_name), None)
        if not to_cache_method:
            raise NotImplementedError(u'to_cache_{f} method is required for {f} cache'.format(f=field_name))
        return to_cache_method()

    def _update_cache(self, field_name, value):
        setattr(self, u'_cache_{}_last_update'.format(field_name), timezone.now())
        if hasattr(self, '_cache_j_{}'.format(field_name)):
            value = json.dumps(value) if value else None
            setattr(self, u'_cache_j_{}'.format(field_name), value)
        elif hasattr(self, '_cache_c_{}'.format(field_name)):
            value = join_data(*value) if value else None
            setattr(self, u'_cache_c_{}'.format(field_name), value)
        elif hasattr(self, '_cache_i_{}'.format(field_name)):
            setattr(self, u'_cache_i_{}'.format(field_name), value)
        setattr(self, u'_cache_{}'.format(field_name), value)

    def update_cache(self, field_name, save=False):
        self._update_cache(field_name, self._to_cache(field_name))
        if save:
            self.save()

    def update_cache_if_changed(self, field_name, save=True):
        current_value = getattr(self, u'cached_{}'.format(field_name))
        value = self._to_cache(field_name)
        if not current_value and not value: # For fields that save empty strings when no value, like images
            return False
        if current_value == value:
            return False
        self._update_cache(field_name, value)
        if save:
            self.save()
        return True

    def update_caches_if_changed(self, field_names, save=True):
        some_changed = False
        for field_name in field_names:
            changed = self.update_cache_if_changed(field_name, save=False)
            if changed:
                some_changed = True
        if some_changed and save:
            self.save()
        return some_changed

    def force_update_cache(self, field_name):
        self.update_cache(field_name, save=True)

    def _force_on_last_update_or_none(self, field_name, prefix=''):
        days = getattr(self, u'_cache_{}_days'.format(field_name), None)
        if days and hasattr(self, u'_cache_{}_last_update'.format(field_name)):
            last_update = getattr(self, u'_cache_{}_last_update'.format(field_name), None)
            if not last_update or last_update < timezone.now() - datetime.timedelta(days=days):
                self.force_update_cache(field_name)
        if (getattr(self, u'_cache_{}_update_on_none'.format(field_name), False)
            and getattr(self, u'_cache_{}{}'.format(prefix, field_name)) is None):
            self.force_update_cache(field_name)

    def get_thumbnail(self, field_name):
        thumbnail = getattr(self, u'_tthumbnail_{}'.format(field_name), None)
        if not thumbnail:
            thumbnail = getattr(self, u'_thumbnail_{}'.format(field_name), None)
        if not thumbnail:
            thumbnail = getattr(self, field_name)
        return thumbnail

    def get_original(self, field_name):
        return getattr(self, u'_original_{}'.format(field_name), None) or getattr(self, field_name)

    def get_2x(self, field_name):
        return getattr(self, u'_2x_{}'.format(field_name))

    def get_force_2x(self, field_name):
        return (
            getattr(self, u'_2x_{}'.format(field_name), None)
            or getattr(self, u'{}_original'.format(field_name), None)
        )

    @classmethod
    def get_auto_image(self, field_name, value):
        original_field_name = field_name
        for name_option in ['i_{}'.format(field_name), 'c_{}'.format(field_name)]:
            if modelHasField(self, name_option):
                original_field_name = name_option
                break
        return staticImageURL(value, folder=original_field_name)

    def _get_auto_image(self, field_name):
        original_field_name = None
        for name_option in ['i_{}'.format(field_name), 'c_{}'.format(field_name), field_name]:
            if hasattr(self, name_option):
                original_field_name = name_option
                break
        if not original_field_name:
            raise ValueError
        return staticImageURL(getattr(self, field_name), folder=original_field_name)

    @classmethod
    def get_field_translation_sources(self, field_name):
        return listUnique(getattr(self, u'{}_SOURCE_LANGUAGES'.format(
            field_name.upper()), []) + ['en'])

    @classmethod
    def get_field_translation_languages(self, field_name, include_english=True, as_choices=False):
        return ([('en', LANGUAGES_NAMES['en']) if as_choices else 'en'] if include_english else []) + [
            (language, verbose_language) if as_choices else language
            for language, verbose_language in LANGUAGES_NAMES.items()
            if (language in self._dict_choices(field_name + 's')
                or modelHasField(self, u'{}_{}'.format(LANGUAGES_NAMES.get(language, None), field_name))
                or modelHasField(self, u'{}_{}'.format(language, field_name)))
        ]

    def get_all_translations_of_field(self, field_name, include_english=True):
        return OrderedDict([(l, t) for l, t in [
            (language, self.get_translation(
                field_name, language=language,
                fallback_to_english=False,
                fallback_to_other_sources=False,
                return_language=False,
            ))
            for language in self.get_field_translation_languages(
                    field_name, include_english=include_english)
        ] if t])

    def get_translation(
            self, field_name, language=None, fallback_to_english=True, fallback_to_other_sources=True,
            return_language=False,
    ):
        d = getattr(self, u'{name}s'.format(name=field_name[2:] if field_name.startswith('m_') else field_name))
        if not language:
            language = get_language()
        result_language = language
        if language == 'en':
            value = getattr(self, field_name)
        else:
            value = getattr(self, u'{}_{}'.format(LANGUAGES_NAMES.get(language, None), field_name),
                            getattr(self, u'{}_{}'.format(language, field_name), None))
            if not value:
                value = d.get(language, None)
                if value and field_name.startswith('m_'):
                    value = value[1]
        if not value and fallback_to_english:
            value = getattr(self, field_name)
            if value:
                result_language = 'en'
        if not value and fallback_to_other_sources:
            for source in self.get_field_translation_sources(
                    field_name[2:] if field_name.startswith('m_') else field_name):
                if source != 'en':
                    value_for_source = d.get(source, None)
                    if value_for_source:
                        value = value_for_source
                        if field_name.startswith('m_'):
                            value = value[1]
                        if value:
                            result_language = source
                        break
        if return_language:
            return result_language, value
        return value

    get_translation_from_dict = get_translation # for retro-compatibility

    def get_displayed_timezones(self, name):
        timezones = ['Local time']
        saved_timezone = getattr(self, u'_{}_timezone'.format(name), None)
        if saved_timezone:
            timezones.append(saved_timezone)
        default_timezones = getattr(self, u'{}_DEFAULT_TIMEZONES'.format(name.upper()), None)
        if default_timezones:
            timezones += default_timezones
        return listUnique(timezones)

    def _attr_error(self, name):
        raise AttributeError("%r object has no attribute %r" % (self.__class__, name))

    def __getattr__(self, name):
        original_name = name

        # Reserved names
        if original_name in [
                'top_html',
                'top_html_list',
                'top_html_item',
                'top_image',
                'top_image_list',
                'top_image_item',
                'birthday_banner',
                'birthday_banner_hide_title',
                'birthday_banner_css_class',
                'share_image',
                'share_image_in_list',
                'display_name',
                'display_name_in_list',
                'blocked',
                'blocked_by_owner',
                'blocked_owner_id',
                'reverse_related',
                'html_attributes',
                'html_attributes_in_list',
                'thumbnail_size',
                'tinypng_settings',
                'icon_for_prefetched',
                'image_for_prefetched',
                'template_for_prefetched',
                'image_for_favorite_character',
                'display_item_url',
                'display_ajax_item_url',
                'show_section_header',
                'selector_to_collected_item',
                'get_item_url',
                'get_ajax_item_url',
        ]:
            return self._attr_error(original_name)

        # PREFIX + SUFFIX
        ############################################################
        # When accessing "something1_X_something2"

        if name.startswith('display_') and name.endswith('_timezones'):
            return type(self).get_displayed_timezones(name)

        # PREFIXES
        ############################################################
        # When accessing "X_something" where X is a MagiCircles prefix

        # When accessing "t_something", return the verbose value
        if name.startswith('t_'):
            name = name[2:]
            # For a i_choice
            if hasattr(self, 'i_{name}'.format(name=name)):
                return type(self).get_verbose_i(name, getattr(self, 'i_{name}'.format(name=name)))
            # For a CSV value: return dict {value: translated value}
            elif hasattr(self, 'c_{name}'.format(name=name)):
                return type(self).get_csv_values(name, getattr(self, name))
            # For a dict: return dict {key: {'value': value, 'verbose': translation}}
            elif hasattr(self, u'd_{name}'.format(name=name)):
                return type(self).get_dict_values(name, getattr(self, u'd_{name}'.format(name=name)), translated=True)
            # For a dict, if no _s exists: return value for language
            elif hasattr(self, u'd_{}s'.format(name)) and hasattr(self, name):
                return self.get_translation(name)
            return self._attr_error(original_name)

        # When accessing "has_something" and "i_something" exists
        if name.startswith('has_'):
            name = name[4:]
            # For a i_choice
            if hasattr(self, 'i_{name}'.format(name=name)):
                return getattr(self, 'i_{name}'.format(name=name)) is not None
            return self._attr_error(original_name)

        # Return cache
        elif name.startswith('cached_'):
            field_name = name[7:]
            cache = getattr(self, u'_internal_cache_{}'.format(field_name), -1)
            if cache != -1:
                return cache
            # Accessing cached_something when _cache_j_something exists
            if hasattr(self, '_cache_j_{}'.format(field_name)):
                self._force_on_last_update_or_none(field_name, prefix='j_')
                cache = type(self).get_cached_json(field_name, getattr(self, '_cache_j_{}'.format(field_name)))
            # Accessing cached_something when _cache_c_something exists
            elif hasattr(self, '_cache_c_{}'.format(field_name)):
                self._force_on_last_update_or_none(field_name, prefix='j_')
                cache = type(self).get_cached_csv(field_name, getattr(self, '_cache_c_{}'.format(field_name)))
            # Accessing cached_something when _cache_i_something exists
            elif hasattr(self, '_cache_i_{}'.format(field_name)):
                return type(self).get_reverse_i(
                    field_name, getattr(self, 'cached_i_{}'.format(field_name)),
                )
            # Accessing cached_t_something when _cache_i_something exists
            elif field_name.startswith('t_') and hasattr(self, '_cache_i_{}'.format(field_name[2:])):
                return type(self).get_verbose_i(
                    field_name[2:], getattr(self, 'cached_i_{}'.format(field_name[2:])),
                )
            # Accessing cached_something when _cache_something exists
            elif hasattr(self, '_cache_{}'.format(field_name)):
                self._force_on_last_update_or_none(field_name)
                cache = getattr(self, '_cache_{}'.format(field_name))
            if cache != -1:
                setattr(self, u'_internal_cache_{}'.format(field_name), cache)
                return cache
            return self._attr_error(original_name)

        # SUFFIXES
        ############################################################
        # When accessing "X_something" where X is a MagiCircles suffix

        # When accessing "something_thumbnail"
        if name.endswith('_thumbnail'):
            field_name = name[:-10]
            return self.get_thumbnail(field_name)

        # When accessing "something_original"
        elif name.endswith('_original'):
            field_name = name[:-9]
            return self.get_original(field_name)

        # When accessing "something_force_2x"
        elif name.endswith('_force_2x'):
            field_name = name[:-9]
            return self.get_force_2x(field_name)

        # When accessing "something_2x"
        elif name.endswith('_2x'):
            field_name = name[:-3]
            return self.get_2x(field_name)

        # When accessing "something_image"
        elif name.endswith('_image') and getattr(self, '{}_AUTO_IMAGES'.format(name[:-6].upper()), False):
            return self._get_auto_image(name[:-6])

        # When accessing "something_url"
        elif name.endswith('_url'):
            field_name = name.replace('http_', '')[:-4]
            try:
                field = self._meta.get_field(field_name)
            except FieldDoesNotExist:
                field = None
            if field:
                # For an image, return the url
                if isinstance(self._meta.get_field(field_name), models.ImageField):
                    return (get_http_image_url(self, field_name)
                            if name.startswith('http_')
                            else get_image_url(self, field_name))
                # For a file, return the url
                elif isinstance(self._meta.get_field(field_name), models.FileField):
                    return (get_http_file_url(self, field_name)
                            if name.startswith('http_')
                            else get_file_url(self, field_name))
                return self._attr_error(original_name)
            # If it's a string, just turn it into a path
            value = getattr(self, field_name)
            if (isinstance(value, basestring)
                or isinstance(value, ImageFieldFile)):
                return (get_http_file_url_from_path(str(value))
                        if name.startswith('http_')
                        else get_file_url_from_path(str(value)))
            return self._attr_error(original_name)

        # WITHOUT PREFIX
        ############################################################
        # When accessing "something" and "X_something" exists where X is a MagiCircles prefix

        for prefix in ['_', 'i_', 'c_', 'd_', 'm_', 'j_']:
            if name.startswith(prefix):
                return self._attr_error(original_name)

        # When accessing "something" and "i_something exists, return the readable key for the choice
        if hasattr(self, u'i_{name}'.format(name=name)):
            return type(self).get_reverse_i(name, getattr(self, u'i_{name}'.format(name=name)))

        # When accessing "something" and "c_something" exists, returns the list of CSV values
        elif hasattr(self, 'c_{name}'.format(name=name)):
            return type(self).get_csv_values(name, getattr(self, 'c_{name}'.format(name=name)), translated=False)

        # When accessing "something" and "d_m_something" exists, returns the dict
        elif hasattr(self, 'd_m_{name}'.format(name=name)):
            return type(self).get_markdown_dict_values(name, getattr(self, u'd_m_{name}'.format(name=name)), translated=False)

        # When accessing "something" and "d_something" exists, returns the dict
        elif hasattr(self, 'd_{name}'.format(name=name)):
            return type(self).get_dict_values(name, getattr(self, u'd_{name}'.format(name=name)), translated=False)

        # When accessing "something" and "m_something" exists, returns the html value if exists
        elif hasattr(self, 'm_{name}'.format(name=name)):
            return self._get_markdown_value(name)

        # When accessing "something" and "j_something" exists, return the python variable (dict, list, ...)
        elif hasattr(self, u'j_{}'.format(name)):
            return type(self).get_json_value(name, getattr(self, u'j_{}'.format(name)))

        return self._attr_error(original_name)

    class Meta:
        abstract = True

############################################################
# Utils for collection (used by MagiModel and addMagiModelProperties)

############################################################
# Get collection

def get_collection(instance):
    return getMagiCollection(instance.collection_name)

############################################################
# Get URLs

# Will not check if the views are enabled.
# If you'd like to check, you can do:
#   ```
#   if instance.collection.item_view.enabled and instance.collection.item_view.ajax:
#     return instance.collection.item_view_url
#   ```
# Checking adds a significant cost since it accesses the collection, so only do it when necessary.

def get_item_url(instance):
    return (
        getattr(instance, 'get_item_url', lambda: None)()
        or u'/{}/{}/{}/'.format(instance.collection_name, instance.pk, tourldash(str(instance)))
    )

def get_ajax_item_url(instance):
    return (
        getattr(instance, 'get_ajax_item_url', lambda: None)()
        or u'/ajax/{}/{}/'.format(instance.collection_name, instance.pk)
    )

def get_full_item_url(instance):
    display_url = getattr(instance, 'get_ajax_item_url', lambda: None)()
    if display_url:
        if '//' not in display_url[:8]:
            return u'{}{}'.format(django_settings.SITE_URL, display_url)
        return display_url
    return u'{}{}/{}/{}/'.format(django_settings.SITE_URL, instance.collection_name, instance.pk, tourldash(str(instance)))

def get_http_item_url(instance):
    url = get_full_item_url(instance)
    if url and 'http' not in url:
        url = 'https:' + url
    return url

def get_share_url(instance):
    return instance.http_item_url

def get_edit_url(instance):
    return u'/{}/edit/{}/'.format(instance.collection_plural_name, instance.pk)

def get_report_url(instance):
    return u'/reports/add/{}/?id={}'.format(instance.collection.model_name, instance.pk)

def get_suggestedit_url(instance):
    return u'/suggestededits/add/{}/?id={}'.format(instance.collection.model_name, instance.pk)

def get_ajax_edit_url(instance):
    return u'/ajax/{}/edit/{}/'.format(instance.collection_plural_name, instance.pk)

############################################################
# Get sentences

def get_open_sentence(instance):
    return _('Open {thing}').format(thing=str(instance.collection_title).lower())

def get_edit_sentence(instance):
    return _('Edit {thing}').format(thing=str(instance.collection_title).lower())

def get_delete_sentence(instance):
    return _('Delete {thing}').format(thing=str(instance.collection_title).lower())

def get_report_sentence(instance):
    return _('Report {thing}').format(thing=str(instance.collection_title).lower())

def get_suggestedit_sentence(instance):
    return _('Suggest edit')

def get_collection_plural_name(instance):
    if not getattr(instance, '_collection_plural_name', None):
        instance._collection_plural_name = instance.collection.plural_name
    return instance._collection_plural_name

def get_collection_title(instance):
    if not getattr(instance, '_collection_title', None):
        instance._collection_title = instance.collection.title
    return instance._collection_title

def get_collection_plural_title(instance):
    if not getattr(instance, '_collection_plural_title', None):
        instance._collection_plural_title = instance.collection.plural_title
    return instance._collection_plural_title

############################################################
# Transform an existing model to an MagiModel
# Used for the User model

def addMagiModelProperties(modelClass, collection_name):
    """
    Takes an existing Model class and adds the missing properties that would make it a proper MagiModel.
    Useful if you can't write a certain model yourself but you wish to use a MagiCollection for that model.
    Will not have the properties and tools provided by BaseMagiModel, except helpers for images, c_ and i_fields.
    """
    modelClass.collection_name = collection_name
    modelClass.collection = property(get_collection)
    modelClass.collection_plural_name = property(get_collection_plural_name)
    modelClass.collection_title = property(get_collection_title)
    modelClass.collection_plural_title = property(get_collection_plural_title)
    modelClass.item_url = property(get_item_url)
    modelClass.ajax_item_url = property(get_ajax_item_url)
    modelClass.full_item_url = property(get_full_item_url)
    modelClass.http_item_url = property(get_http_item_url)
    modelClass.share_url = property(get_share_url)
    modelClass.edit_url = property(get_edit_url)
    modelClass.report_url = property(get_report_url)
    modelClass.suggestedit_url = property(get_suggestedit_url)
    modelClass.ajax_edit_url = property(get_ajax_edit_url)
    modelClass.image_url = property(get_image_url)
    modelClass.http_image_url = property(get_http_image_url)
    modelClass.open_sentence = property(get_open_sentence)
    modelClass.edit_sentence = property(get_edit_sentence)
    modelClass.delete_sentence = property(get_delete_sentence)
    modelClass.report_sentence = property(get_report_sentence)
    modelClass.suggestedit_sentence = property(get_suggestedit_sentence)
    modelClass.tinypng_settings = {}
    modelClass.request = None

    modelClass.fk_as_owner = None
    modelClass.selector_to_owner = classmethod(get_selector_to_owner)
    modelClass.owners_queryset = classmethod(get_owners_queryset)
    modelClass.owner_ids = classmethod(get_owner_ids)
    modelClass.get_owner_from_pk = classmethod(get_owner_from_pk)
    modelClass.allow_multiple_per_owner = classmethod(get_allow_multiple_per_owner)
    modelClass.owner_collection = classmethod(get_owner_collection)
    modelClass.is_owner = get_is_owner
    modelClass.owner_unicode = property(get_owner_str)
    modelClass.real_owner = property(get_real_owner)
    modelClass.request = None

############################################################
# MagiModel

class MagiModel(BaseMagiModel):
    """
    The model you must inherit from
    """
    collection_name = ''
    request = None

    collection = property(get_collection)
    collection_plural_name = property(get_collection_plural_name)
    collection_title = property(get_collection_title)
    collection_plural_title = property(get_collection_plural_title)
    item_url = property(get_item_url)
    ajax_item_url = property(get_ajax_item_url)
    full_item_url = property(get_full_item_url)
    http_item_url = property(get_http_item_url)
    share_url = property(get_share_url)
    edit_url = property(get_edit_url)
    report_url = property(get_report_url)
    suggestedit_url = property(get_suggestedit_url)
    ajax_edit_url = property(get_ajax_edit_url)
    open_sentence = property(get_open_sentence)
    edit_sentence = property(get_edit_sentence)
    delete_sentence = property(get_delete_sentence)
    report_sentence = property(get_report_sentence)
    suggestedit_sentence = property(get_suggestedit_sentence)

    allow_multiple_per_owner = classmethod(get_allow_multiple_per_owner)

    def __unicode__(self):
        try:
            return str(self.t_name)
        except AttributeError:
            pass
        try:
            return str(self.collection_title)
        except AttributeError:
            pass
        return str(self.collection_name)

    class Meta:
        abstract = True

############################################################
# Utility Models

class UserImage(BaseMagiModel):
    image = models.ImageField(upload_to=uploadToRandom('user_images'))
    _thumbnail_image = models.ImageField(null=True, upload_to=uploadThumb('user_images'))
    name = models.CharField(_('Title'), max_length=100, null=True)

    def __unicode__(self):
        return str(_('Image'))
