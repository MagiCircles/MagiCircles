# -*- coding: utf-8 -*-
import re
from copy import copy
from collections import OrderedDict
from django.conf import settings as django_settings
from django.db.models.fields import Field as ModelField
from django.db.models.related import RelatedObject
from django.db.models.query import QuerySet
from django.utils.formats import date_format
from django.utils.translation import (
    activate as translation_activate,
    get_language,
    string_concat,
    ugettext_lazy as _,
)
from magi.settings import (
    HASHTAGS,
    INSTAGRAM_HANDLE,
    LANGUAGES_CANT_SPEAK_ENGLISH,
    SITE_URL,
    TWITTER_HANDLE,
)
from magi.utils import (
    __,
    addParametersToURL,
    andJoin,
    articleJsonLdFromItem,
    AttrDict,
    cmToHumanReadable,
    ColorField,
    failSafe,
    FAQjsonLd,
    fieldNameMatch,
    flattenListOfLists,
    getAge,
    getAllModelFields,
    getCharacterImageFromPk,
    getCharacterLabel,
    getCharacterNameFromPk,
    getCharacterURLFromPk,
    getDomainFromURL,
    getEmojis,
    getEnglish,
    getEventStatus,
    getFilterFieldNameOfRelatedItem,
    getImageForPrefetched,
    getIndex,
    getLanguageImage,
    getListURL,
    getMagiCollection,
    getModelOfRelatedItem,
    getRelatedItemFromItem,
    getRelatedItemsFromItem,
    getRelOptionsDict,
    getSiteName,
    getValueIfNotProperty,
    getVerboseNameOfRelatedField,
    hasValue,
    inchesToHumanReadable,
    isFullURL,
    isMarkedSafe,
    isPreset,
    isRequestAjax,
    isRequestCrawler,
    isTranslationField,
    isTweetTooLong,
    listUnique,
    markSafe,
    markSafeFormat,
    markSafeJoin,
    mergeDicts,
    modelFieldVerbose,
    modelGetField,
    modelHasField,
    newOrder,
    recursiveCall,
    secondsToHumanReadable,
    setRelOptionsDefaults,
    split_data,
    staticImageURL,
    suggestFlaticonFromFieldName,
    toHumanReadable,
    tourldash,
    translationSentence,
    translationURL,
    videoJsonLd,
    YouTubeVideoField,
)
from magi import models
from magidisplay import *

SHOW_DEBUG = False
SHOW_DEBUG_LIST = False

if django_settings.DEBUG and getattr(django_settings, 'DEBUG_SHOW_MAGIFIELDS', True):
    import traceback
    from pprint import pprint
    SHOW_DEBUG = True
    if getattr(django_settings, 'DEBUG_SHOW_MAGIFIELDS_LIST', False):
        SHOW_DEBUG_LIST = True

############################################################
# Internal

type_f = type

PERMISSION_ITEM_OPTIONS = {
    # Used by has_permissions (show, at bound), classes, verbose_name_subtitle and annotation (at display)
    u'{}_STAFF_REQUIRED': False,

    # Used by has_permissions
    u'{}_LOGOUT_REQUIRED': False,
    u'{}_AUTHENTICATION_REQUIRED': False,
    u'{}_PRELAUNCH_STAFF_REQUIRED': False,
    u'{}_PERMISSIONS_REQUIRED': [],
    u'{}_ONE_OF_PERMISSIONS_REQUIRED': [],
    u'{}_OWNER_ONLY': False,
    u'{}_OWNER_OR_STAFF_ONLY': False,
    u'{}_OWNER_ONLY_OR_PERMISSIONS_REQUIRED': [],
    u'{}_OWNER_ONLY_OR_ONE_OF_PERMISSIONS_REQUIRED': [],
}

############################################################
############################################################
############################################################
# MagiField

class MagiField(object):
    """
    Fields are auto-determined using is_field, which is a required class method.
    Fields then get initiated without being bound to an item.
    field.bound_field gets called later, bounding the field to the item.
    """

    ############################################################
    # Settings
    # Can be overridden.

    # List of options that can be retrieved from the item, as model field or property,
    # and their default value if there's no value set.
    # They should always be all uppercase. "{}" will be replaced with the field name.
    # They'll also be available as kwargs by default. (Ex: '{}_SOMETHING' -> kwarg = 'something')
    BASE_VALID_ITEM_OPTIONS = mergeDicts({
        u'{}_SUGGEST_EDIT': False,
        u'{}_SUGGEST_EDIT_WHEN_EMPTY': False,

        u'{}_AUTO_IMAGES': False,
        # {}_AUTO_IMAGES_FOLDER + {}_AUTO_IMAGES_FROM_I also exist and are used by get_auto_image in item_model

        u'{}_QUESTION': None,
        u'{}_QUESTION_VARIABLES': {},
        u'{}_ANSWER': None,
        u'{}_FAQ': None,
        u'{}_TABLE_HEADER': None,
        u'{}_IS_PLURAL': None, # boolean, defaults to wether or not it ends with 's'
        u'{}_IS_PERSON': False,
    }, PERMISSION_ITEM_OPTIONS)
    VALID_ITEM_OPTIONS = {}

    # List of valid keys for kwargs passed to __init__
    # They can be different per field, allowing to easily customize a MagiFields class
    # Example:
    # class IdolFields(MagiFields):
    #     birthday = MagiBirthdayModelField(image='birthday_image')
    #     credits = MagiCharField(value=_('Courtesy of MEDIA inc.'), verbose_name=_('Credits'))
    # All item options are available as kwargs, so only use this if you only want them available
    # as kwargs and not item options.
    BASE_VALID_KWARGS = [
        'db_value', # Can be a callable that takes item (defaults to value if specified)
        'value', # Can be a callable that takes item
        'display_value', # Can be a callable that takes item
        'table_fields_only',
        'ordering_fields_only',
        'item_view_only',
        'item', # Only if the item referred to is different from the item being displayed by the view (rare)
        'item_access_field_name', # Mostly used by subfields
        # Can be a callable that takes item (the one from the view)
    ] + MagiDisplay.PARAMETERS.keys() # verbose_name, icon, etc
    VALID_KWARGS = []

    # Before bound
    @classmethod
    def is_field(self, field_name, options=None):
        return True

    # Before bound
    @classmethod
    def to_field_name(self, original_field_name):
        return original_field_name

    # If you need your field_name (that will be the dict key in .fields) to be
    # different from the field_name used to access the item, you can set it here:
    # Will not work for fields that need to be prefetched/preselected, as the queryset
    # will be made beforehand and will need to know the field names.

    # After bound
    def to_item_access_original_field_name(self):
        if 'item_access_field_name' in self.fields_kwargs:
            return self.fields_kwargs['item_access_field_name']
        return self.original_field_name

    # After bound
    def to_item_access_field_name(self):
        if 'item_access_field_name' in self.fields_kwargs:
            return self.fields_kwargs['item_access_field_name']
        return self.field_name

    ############################################################
    # Init
    # Can be overridden.

    def init(self):
        """Called at init time, bound_field has not been called yet."""
        pass

    def bound_init_before_item_options(self):
        """Called during bound, before item options are set."""
        pass

    def bound_init_before(self):
        """Called during bound, before values are retrieved."""
        pass

    def bound_init_after(self):
        """Called after bound, after values have been retrieved."""
        pass

    ############################################################
    # Value
    # After bound. Can be overridden.

    def to_db_value(self):
        """
        Raw value, as it would be found in a Django model instance.
        By default, tries to get it from the item (as a model field or a property).
        """
        if 'db_value' in self.fields_kwargs:
            if callable(self.fields_kwargs['db_value']):
                return self.fields_kwargs['db_value'](self.item)
            return self.fields_kwargs['db_value']
        elif 'value' in self.fields_kwargs:
            if callable(self.fields_kwargs['value']):
                return self.fields_kwargs['value'](self.item)
            return self.fields_kwargs['value']
        return getattr(self.item, self.item_access_original_field_name, None)

    def to_value(self):
        """
        Main value, which can be transformed from the db_value if needed.
        By default, tries to get it from the item (as a model field or a property).
        Typically contains a translation of the value when it applies (MagiModelField does that for you).
        In that case, to_value should also set self.language.
        """
        if 'db_value' in self.fields_kwargs and 'value' in self.fields_kwargs:
            if callable(self.fields_kwargs['value']):
                return self.fields_kwargs['value'](self.item)
            return self.fields_kwargs['value']
        elif 'value' in self.fields_kwargs:
            return self.db_value
        elif self.item_access_field_name != self.item_access_original_field_name:
            return getattr(self.item, self.item_access_field_name, self.db_value)
        return self.db_value

    def has_value(self):
        return hasValue(self.value)

    ############################################################
    # Special
    # After bound. Can be overridden.

    # When a field is usually used to save plural values (example: MagiCSVField)
    is_usually_plural = False

    @property
    def is_plural(self):
        """Used by question, in FAQ"""
        if self.item_options['IS_PLURAL'] is None:
            if self.is_usually_plural:
                return True
            return self.field_name.endswith('s') and not self.field_name.endswith('ss')
        return bool(self.item_options['IS_PLURAL'])

    def to_text_value(self):
        """
        Used:
        - to display Google Translate links with the text content passed via URL
        - default answer when using Q&A for SEO
        """
        if isMarkedSafe(self.value):
            return None
        return unicode(self.value)

    # Used to create an FAQ for SEO
    # To return multiple questions and answer, use to_faq instead
    @property
    def question(self):
        if self.item_options['IS_PERSON']:
            if self.is_plural:
                return _('Who are {name}\'s {things}?')
            return _('Who is {name}\'s {thing}?')
        if self.is_plural:
            return _('What are {name}\'s {things}?')
        return _('What is {name}\'s {thing}?')

    def to_question(self):
        if self.item_options['QUESTION']:
            if callable(self.item_options['QUESTION']):
                return self.item_options['QUESTION'](self.item)
            return self.item_options['QUESTION']
        return self.question

    def format_question(self, question):
        return question.format(**mergeDicts({
            'name': self.name_for_question,
            'thing': self.verbose_name_for_question,
            'things': self.verbose_name_for_question,
        }, self.item_options['QUESTION_VARIABLES']))

    @property
    def answer(self):
        return andJoin(self.to_text_value().split(u'\n'))

    def to_answer(self):
        if self.item_options['ANSWER']:
            if callable(self.item_options['ANSWER']):
                return self.item_options['ANSWER'](self.item)
            return self.item_options['ANSWER']
        return self.answer

    @property
    def faq(self):
        question = self.format_question(self.to_question())
        if question is not None:
            answer = self.to_answer()
            if hasValue(answer) and unicode(answer) != unicode(self.name_for_question):
                return [
                    (question, answer),
                ]
        return []

    def to_faq(self):
        if self.item_options['FAQ'] is not None:
            return self.item_options['FAQ']
        return self.faq

    def to_video_ld(self):
        return None

    # When full size template is specified, it will entirely replace the line, including the icon, title, etc.
    full_size_template = None

    def get_template(self):
        """
        When template is specified, it will be used within the display part of the line.
        display classes will not be used.
        Template is not compatible with multifields.
        """
        return None

    def extra_context(self):
        """Add something to the context. Can be useful when using custom templates."""
        return None

    ############################################################
    # Permissions

    # After bound, called by can_show
    _has_permissions = None
    def has_permissions(self):
        if not self.request:
            # When the request is unknown, if any permission setting is set, consider it doesn't have permission
            for option_name in PERMISSION_ITEM_OPTIONS.keys():
                if getattr(self, self.item_option_to_kwarg(option_name)):
                    return False
            return True
        if self._has_permissions is None:
            is_auth = self.is_authenticated
            user = self.request.user
            is_owner = self.is_owner()
            self._has_permissions = not (
                (self.logout_required and is_auth)
                or (self.authentication_required and not is_auth)
                or (self.staff_required and (not is_auth or not user.is_staff))
                or (self.prelaunch_staff_required and (
                    not is_auth or not user.hasPermission('access_site_before_launch')))
                or (self.permissions_required and (
                    not is_auth or not user.hasPermissions(self.permissions_required)))
                or (self.one_of_permissions_required and (
                    not is_auth or not user.hasOneOfPermissions(self.one_of_permissions_required)))
                or (self.owner_only and (not is_auth or (not is_owner and not user.is_superuser)))
                or (self.owner_or_staff_only and (
                    not is_auth or (not is_owner and not user.is_staff and not user.is_superuser)))
                or (self.owner_only_or_permissions_required and (not is_auth or (
                    not is_owner or not user.hasPermissions(self.owner_only_or_permissions_required))))
                or (self.owner_only_or_one_of_permissions_required and (not is_auth or (
                    not is_owner or not user.hasOneOfPermissions(self.owner_only_or_permissions_required))))
            )
        return self._has_permissions

    # After bound, called by has_permissions and is_staff_only
    def is_owner(self):
        return (
            self.request
            and self.is_authenticated
            and self.request.user.id == getattr(self.item, 'owner_id', None)
        )

    def is_staff_only(self):
        """
        Called by classes, to_verbose_subtitle and annotation
        to check if the field should be hidden by default and revealed by staff button
        """
        return (
            self.staff_required
            or ((self.permissions_required
                 or self.one_of_permissions_required
                 or self.prelaunch_staff_required)
                and self.is_authenticated and self.request.user.is_staff)
            or ((self.owner_only
                 or self.owner_or_staff_only
                 or self.owner_only_or_permissions_required
                 or self.owner_only_or_one_of_permissions_required)
                and not self.is_owner())
        )

    ############################################################
    # Translations
    # After bound. Can be overridden.

    @property
    def has_translations(self):
        return False

    def show_multiple_languages_translations(self):
        """Show other relevant translations, in addition to the main translated value."""
        return self.has_translations

    def get_translation_languages(self):
        """List of languages the field can be translated INTO."""
        return []

    def get_translation_sources(self):
        """List of languages the field can be translated FROM."""
        return [ 'en' ]

    def get_languages_to_display(self):
        """List of languages considered relevant to display in addition to the main translated value."""
        return self.get_translation_sources()

    ############################################################
    # Show/hide field
    # After bound. Can be overridden.

    def can_display(self):
        return True

    def can_display_if_other_language(self):
        """If it's not in the user's language, should it still be displayed?"""
        return (
            self.language == self.current_user_language
            or self.current_user_language not in LANGUAGES_CANT_SPEAK_ENGLISH
        )

    def can_display_if_default(self):
        """Check against a default value and decide wether to show or not."""
        return True

    ############################################################
    # Multifields
    # After bound. Can be overridden.

    # This allows to display multiple fields (rows of details)
    # using a single MagiField.

    # When multifields is enabled, to_db_value and to_value generally return
    # a list or a dict. The individual values are then called "iter_value".

    # Some settings won't care wether multifields is enabled or not and
    # will consider "the value" to be what your list/dict contains.
    # - Translations settings such as has_translations, show_multiple_languages_translations,
    #   get_translation_sources, etc.
    # - show, can_display_if_other_language, can_display_if_default

    # All display parameters can be specified per iter_value.
    # See display parameters section below.

    # get_template is not compatible with multifields.

    def is_multifields(self):
        return False

    def multifields_has_value(self, iter_value=None):
        """
        Used to decide wether to display this field (row) or not.
        It's also used by fields buttons.
        has_value still gets called to check if there are values overall.
        """
        return hasValue(iter_value)

    ############################################################
    # Display class
    # After bound, called by template. Can be overridden.

    display_class = MagiDisplayText

    ############################################################
    # Display value
    # After bound, called by template. Can be overridden.

    def to_display_value_from_value(self, value):
        """
        Value will either be iter_value (when multifields) or self.value (most likely).
        If there's a display value retrieved from the model class, this will not be called.
        """
        if self.is_multifields() and isinstance(value, tuple) and len(value) == 2:
            return value[1] # iter_value for dict = (key, value)
        return value

    def to_display_value(self, iter_value=None):
        """
        If needed, transform the value into what's expected in your display class.
        If to_display_value gets overridden, your code needs to ensure value_from_display_property
        gets used if any. In most cases, use to_display_value_from_value instead.
        """
        if self.is_multifields():
            return self.to_display_value_from_value(iter_value)
        return (
            self.value_from_display_property
            if self.retrieved_display_value
            else self.to_display_value_from_value(self.value)
        )

    ############################################################
    # Display parameters
    # After bound, called by template. Can be overridden.

    # All variables allowed by the display class can be set as variables or properties here.
    # Example:
    # spread_across = True

    # Some display classes use other display classes to display content.
    # For example, MagiDisplayLink allows to specify `link_content_display_class`.
    # In that case, you can also specify parameters of that display class here.
    # Example: MagiDisplayLink class with `link_content_display_class` = MagiDisplayText
    #   -> you can specify text_icon here.

    # For multifields, the same can be set as methods with prefix multifields_ that take iter_value:
    # multifields_spread_across, multifields_icon, ...

    default_verbose_name = None

    def to_verbose_name(self):
        """
        It's mainly used on the right of the field content.
        But it's also used in other places:
        - in URL fields, on the button to open the URL
        - In linked items, when opening in an ajax modal, will be displayed as a modal title
        - By template:
          - If you display an image on the left side (instead of an icon), it will be used as the "alt"
        """
        return (
            self.default_verbose_name
            or toHumanReadable(self.field_name, capitalize=True, warning=True)
        )

    def to_verbose_name_subtitle(self):
        return u'⚠️ Staff only' if self.is_staff_only() else None

    @property
    def verbose_name_for_buttons(self):
        """
        Used in various buttons:
        - Suggest edit buttons ("Edit x")
        - In single linked items (fk, etc):
          - when linking to see the full item ("Open x")
        - In multiple linked items (m2m, related, etc):
          - when there are more that are not displayed ("More x - View all")
          - when items are displayed in individual rows ("Open x")
          - when displaying the total number of items (cached) ("5 x")
             -> can be changed with rel_plural_verbose_name
        """
        return self.verbose_name.lower()

    @property
    def verbose_name_for_question(self):
        return self.verbose_name_for_buttons

    @property
    def verbose_name_for_table_header(self):
        return (
            self.item_options['TABLE_HEADER']
            or self.verbose_name
        )

    @property
    def verbose_name_for_collapsed_table_header(self):
        return self.verbose_name_for_table_header

    default_icon = None

    # default_icon actually defaults to "about" after trying to suggest
    # another icon using suggestFlaticonFromFieldName

    def to_icon(self):
        icon = (
            self.options.fields_icons.get(self.field_name, None)
            or self.collection.fields_icons.get(self.field_name, None)
            or (
                (
                    self.default_icon
                    or suggestFlaticonFromFieldName(self.field_name)
                    or 'about'
                ) if not self.image else None
            )
        )
        return icon(self.item) if callable(icon) else icon

    default_image = None

    def to_image(self):
        image = (
            self.options.fields_images.get(self.field_name, None)
            or self.collection.fields_images.get(self.field_name, None)
            or self.get_auto_image()
            or self.default_image
        )
        return staticImageURL(image(self.item) if callable(image) else image)

    def to_spread_across(self):
        return self.is_ajax_popover()

    @property
    def classes(self):
        return [ 'staff-only' ] if self.is_staff_only() else []

    @property
    def annotation(self):
        return u'⚠️ Staff only' if self.is_staff_only() else []

    ############################################################
    # Display buttons per field
    # After bound, called by template. Can be overridden.

    # Buttons retrieved by template.
    # Any new button added can have the following properties:
    # - show_XXX_button, boolean
    # - XXX_button_text
    # - XXX_button_url
    # - XXX_button_ajax_url
    # - XXX_button_ajax_link_title
    # - XXX_button_new_window
    # - XXX_button_icon
    # - XXX_button_image
    # For multifields, the same can be set as methods with prefix multifields_ that take iter_value:
    # multifields_XXX_button_text, multifields_show_XXX_button, ...
    # show_XXX_button still gets called with multifields to check if it's shown overall.

    BUTTONS = [ 'translate', 'suggest_edit' ]

    ############################################################
    # Buttons per field: Translations
    # After bound. Can be overridden.

    @property
    def show_translate_button(self):
        return (
            self.has_value()
            and self.has_translations
            and self.language != self.current_user_language
            and self.current_user_language in self.get_translation_languages()
        )

    def multifields_show_translate_button(self, iter_value=None):
        return (
            self.multifields_has_value(iter_value)
            and self.has_translations
            and self.language != self.current_user_language
        )

    @property
    def translate_button_text(self):
        return translationSentence(from_language=self.language, to_language=self.current_user_language)

    @property
    def translate_button_url(self):
        return self.get_translate_button_url(self.to_text_value())

    def multifields_translate_button_url(self, iter_value):
        return self.get_translate_button_url(self.to_text_value(iter_value))

    translate_button_icon = 'translate'
    translate_button_new_window = True

    ############################################################
    # Suggest edit button
    # Called if and when suggest edit button gets displayed.
    # After bound. Can be overridden.

    @property
    def show_suggest_edit_button(self):
        return (
                self.options.show_suggest_edit_button
                and (
                    self.field_name in self.options.fields_suggest_edit
                    or self.original_field_name in self.options.fields_suggest_edit
                    or self.item_options['SUGGEST_EDIT']
                    or (
                        self.item_options['SUGGEST_EDIT_WHEN_EMPTY']
                         and not self.has_value()
                    )
                )
        )

    @property
    def allows_upload(self):
        return False

    @property
    def suggest_edit_button_text(self):
        if self.allows_upload:
            return _('Upload {thing}').format(thing=self.verbose_name_for_buttons)
        if not self.has_value():
            return _('Add {thing}').format(thing=self.verbose_name_for_buttons)
        return _('Edit {thing}').format(thing=self.verbose_name_for_buttons)

    def multifields_suggest_edit_button_text(self, iter_value=None):
        if self.allows_upload:
            return _('Upload {thing}').format(thing=self.verbose_name_for_buttons)
        if not self.multifields_has_value(iter_value):
            return _('Add {thing}').format(thing=self.verbose_name_for_buttons)
        return _('Edit {thing}').format(thing=self.verbose_name_for_buttons)

    @property
    def suggest_edit_button_icon(self):
        if self.allows_upload:
            return 'download'
        return 'edit'

    @property
    def suggest_edit_button_url(self):
        if (self.request and self.collection
            and self.collection.edit_view.has_permissions(self.request, self.context, item=self.item)):
            return self.item.edit_url
        return addParametersToURL(self.item.suggest_edit_url, parameters={
            'reason': self.item_access_original_field_name,
        })

    @property
    def suggest_edit_button_new_window(self):
        return self.ajax

    ############################################################
    # Internals

    def check_valid_kwarg(self, kwarg_key):
        if kwarg_key in self.BASE_VALID_KWARGS + self.VALID_KWARGS:
            return True
        for option_name in self.BASE_VALID_ITEM_OPTIONS.keys() + self.VALID_ITEM_OPTIONS.keys():
            if kwarg_key == self.item_option_to_key(option_name).lower():
                return True
        raise TypeError(u'{} got an unexpected keyword argument \'{}\''.format(
            type(self).__name__, kwarg_key))

    def __init__(self, **kwargs):
        for kwarg_key in kwargs.keys():
            self.check_valid_kwarg(kwarg_key)
        self.fields_kwargs = kwargs.copy()

    def init_unbound_field(self, magifields=None, to_value=None):
        self.magifields = magifields
        if magifields:
            self.options = magifields.options
            self.ajax = magifields.ajax
            self.is_crawler = magifields.is_crawler
        else:
            self.options = {}
            self.ajax = False
            self.is_crawler = False
        # Set to_value kwargs
        if callable(to_value):
            self.fields_kwargs['to_value'] = to_value
        elif hasValue(to_value):
            self.fields_kwargs['value'] = to_value

        self.init()

    def bound_field(self, field_name, view, item, context):
        self.item = self.fields_kwargs.get('item', item) or item
        if callable(self.item):
            self.item = self.item(item)
        if self.magifields:
            self.name_for_question = self.magifields.name_for_questions
        self.original_field_name = field_name
        self.field_name = self.to_field_name(field_name)
        self.item_access_original_field_name = self.to_item_access_original_field_name()
        self.item_access_field_name = self.to_item_access_field_name()
        self.view = view
        self.model = type(item)
        self.context = context
        self.request = context.get('request', getattr(item, 'request', None))
        self.is_authenticated = self.request and self.request.user.is_authenticated()

        self.bound_init_before_item_options()

        # Set item options
        self.set_item_options()

        # Set useful shortcuts
        self.collection = view.collection

        self.bound_init_before()

        # Initialize values
        self.current_user_language = get_language()
        self.language = self.current_user_language
        self.db_value = self.to_db_value()
        self.value = self.to_value()
        self.get_value_from_display_property()

        # Set permission properties
        for option_name, default in PERMISSION_ITEM_OPTIONS.items():
            key = self.item_option_to_kwarg(option_name)
            if not hasattr(self, key):
                permission_value = (
                    # From item options (set earlier)
                    self.item_options[self.item_option_to_key(option_name)]
                    # Or from view `fields_{}` settings
                    or ((self.field_name in getattr(self.options, u'fields_{}'.format(key), []))
                        if isinstance(default, bool)
                        else (getattr(self.options, u'fields_{}'.format(key), {}).get(self.field_name, None)))
                )
                try: setattr(self, key, permission_value)
                except AttributeError: pass

        # Check if it should be displayed
        self.show = self.can_show()

        # Set display parameters for default MagiDisplay parameters
        # ex: self.icon, self.verbose_name, self.link, etc
        if self.show:
            for key, default_value in MagiDisplay.PARAMETERS.items():
                if not hasattr(self, key):
                    # From kwargs (ex: name = MagiCharModelField(icon='idol'))
                    if key in self.fields_kwargs:
                        value = self.fields_kwargs[key]
                        if key == 'image':
                            value = staticImageURL(value)
                        try: setattr(self, key, value)
                        except AttributeError: pass
                    else:
                        # From to_ methods (ex: self.to_icon())
                        try:
                            setattr(self, key, getattr(self, u'to_{}'.format(key))())
                        except AttributeError:
                            # From default value
                            try: setattr(self, key, default_value)
                            except AttributeError: pass

        # Custom template(s)
        self.template = self.get_template()
        self.extra_context()

        self.bound_init_after()

    def can_show(self):
        return not (
            not self.can_display()
            or not self.has_permissions()
            or (not self.options.table_fields and self.fields_kwargs.get('table_fields_only', False))
            or (not self.options.ordering_fields and self.fields_kwargs.get('ordering_fields_only', False))
            or (self.view.view != 'item_view' and self.fields_kwargs.get('item_view_only', False))
        )

    def set_item_options(self):
        self.item_options = {
            self.item_option_to_key(option_name): self.get_item_option_value(option_name, default)
            for option_name, default in self.BASE_VALID_ITEM_OPTIONS.items() + self.VALID_ITEM_OPTIONS.items()
        }

    @classmethod
    def item_option_to_key(self, option_name):
        return (
            (option_name[3:] if option_name.startswith('{}_') else None)
            or (option_name[:-3] if option_name.endswith('_{}') else None)
            or option_name.replace('_{}_', '_')
        )

    @classmethod
    def item_option_to_kwarg(self, option_name):
        return self.item_option_to_key(option_name).lower()

    def get_item_option_value(self, option_name, default):
        # First try to get from kwargs
        # Example: '{}_FAQ' -> fields_kwargs.faq
        value = self.fields_kwargs.get(self.item_option_to_kwarg(option_name), None)
        if hasValue(value):
            return value
        # Fallback to item.SOMETHING_FAQ (not I_SOMETHING_FAQ!)
        return getattr(
            self.item, option_name.format(self.item_access_field_name.upper()),
            # Fallback to: model.SOMETHING_FAQ
            getValueIfNotProperty(
                self.model, option_name.format(self.item_access_field_name.upper()),
                # Fallback to "default" value set in VALID_OPTIONS
                default=default),
        )

    @property
    def is_bound(self):
        return hasattr(self, 'item')

    def is_ajax_popover(self):
        return (
            self.ajax
            and self.view.view == 'item_view'
            and self.collection.list_view.ajax_item_popover
        )

    def get_display_parameters(self, iter_value=None, is_other_language=False):
        display_parameters = {}
        for key in self.display_class.valid_parameters + self.display_parameters_from_other_display_class_parameters:
            if (self.is_multifields()
                and hasattr(self, u'multifields_{}'.format(key))):
                if callable(getattr(self, u'multifields_{}'.format(key))):
                    display_parameters[key] = getattr(self, u'multifields_{}'.format(key))(iter_value)
                else:
                    display_parameters[key] = getattr(self, u'multifields_{}'.format(key))
            else:
                try:
                    display_parameters[key] = getattr(self, key)
                except AttributeError:
                    pass
            if is_other_language and key == 'text_image' and not display_parameters.get(key, None):
                display_parameters[key] = getLanguageImage(self.language)
                display_parameters['text_image_height'] = 20
        return display_parameters

    @property
    def display_parameters_from_other_display_class_parameters(self):
        parameters_used_by_display_class_parameters = []
        for display_class_parameter_name in self.display_class.WILL_USE_PARAMETERS_FROM:
            display_class = getattr(
                self, display_class_parameter_name,
                self.display_class.get_default_kwargs_parameter(display_class_parameter_name),
            )
            if display_class:
                parameters_used_by_display_class_parameters += display_class.valid_parameters
        return parameters_used_by_display_class_parameters

    def get_display_class_html(self, iter_value=None, is_other_language=False):
        value = (
            self.to_display_value(iter_value=iter_value)
            if self.is_multifields() else self.to_display_value()
        )
        display_parameters = self.get_display_parameters(iter_value=iter_value, is_other_language=is_other_language)
        return self.display_class.to_html(
            self.item, value,
            **display_parameters
        ), display_parameters, value

    def get_html(self, iter_value=None):
        if (self.template
            or (self.is_multifields() and not self.multifields_has_value(iter_value))
            or (not self.is_multifields() and not self.has_value())):
            return u'', self.get_display_parameters()
        if self.show_multiple_languages_translations():
            htmls, display_parameters = self.all_languages_html(iter_value)
            return markSafeJoin(htmls), display_parameters
        html, display_parameters, display_value = self.get_display_class_html(iter_value)
        return html, display_parameters

    _iter_flag = False
    @property
    def html(self):
        try:
            # Multifields
            if self.is_multifields():
                for iter_value in (
                        self.value_from_display_property
                        if self.retrieved_display_value
                        else (
                                self.value.items()
                                if isinstance(self.value, dict)
                                else self.value
                        )
                ) or []:
                    html, display_parameters = self.get_html(iter_value)
                    yield html, display_parameters, self.get_field_buttons_html(iter_value), True
                # If is_multifields and has no value but still has buttons, empty html with buttons
                if not self.has_value() and self.has_buttons_to_show() and not self._iter_flag:
                    self._iter_flag = True
                    yield u'', self.get_display_parameters(), self.get_field_buttons_html(), True
            # Not multifields
            elif not self._iter_flag:
                self._iter_flag = True
                html, display_parameters = self.get_html()
                yield html, display_parameters, self.get_field_buttons_html(), False
        except:
            if SHOW_DEBUG and (self.view.view == 'item_view' or SHOW_DEBUG_LIST):
                print self.field_name
                traceback.print_exc()

    def get_auto_image(self):
        """
        Most commonly used for i choices, but can work for any other field.
        Folder will be the item_access_original_field_name (ex: i_rarity)
        and filename will be the string value ('R', 'SR', etc)
        Used by to_image, which retrieves the `image` value displayed on the left of the field.
        """
        if self.item_options['AUTO_IMAGES']:
            return self.item.get_auto_image(
                instance=self.item,
                field_name=self.item_access_field_name,
                value=self.value,
                original_field_name=self.item_access_original_field_name,
            )
        return None

    def get_auto_image_foreach(self, value):
        """
        For fields that show multiple values (lists, dicts, etc).
        Most commonly used for CSV and Dict fields, but can work with other fields.
        Not to be confused with multifields.
        """
        if self.item_options['AUTO_IMAGES']:
            return self.item.get_auto_image(
                field_name=self.item_access_field_name,
                value=value,
                original_field_name=self.item_access_original_field_name,
            )
        return None

    def get_value_from_display_property(self):
        """
        Note: display_ is not compatible with related items (foreign keys, many to many, etc).
        """
        self.value_from_display_property = None
        self.retrieved_display_value = False
        # From kwargs
        if 'display_value' in self.fields_kwargs:
            if callable(self.fields_kwargs['display_value']):
                self.value_from_display_property = self.fields_kwargs['display_value'](self.item)
            else:
                self.value_from_display_property = self.fields_kwargs['display_value']
            self.retrieved_display_value = True
        # From display_{}_item or display_{}_in_list
        if not self.retrieved_display_value:
            if self.view.view == 'item_view':
                try:
                    self.value_from_display_property = getattr(self.item, u'display_{}_item'.format(
                        self.item_access_field_name))
                    self.retrieved_display_value = True
                except AttributeError:
                    pass
            elif self.view.view == 'list_view':
                try:
                    self.value_from_display_property = getattr(self.item, u'display_{}_in_list'.format(
                        self.item_access_field_name))
                    self.retrieved_display_value = True
                except AttributeError:
                    pass
        # From display_{}
        if not self.retrieved_display_value:
            try:
                self.value_from_display_property = getattr(self.item, u'display_{}'.format(
                    self.item_access_field_name))
                self.retrieved_display_value = True
            except AttributeError:
                pass

    def all_languages_html(self, iter_value=None):
        html, display_parameters, display_value = self.get_display_class_html(iter_value)
        current_user_language = self.current_user_language
        other_languages = self.get_languages_to_display()
        all_languages_html = OrderedDict({ current_user_language: html })
        all_languages_display_values = [ display_value ]
        for language in other_languages:
            if language == current_user_language:
                continue
            translation_activate(language)
            self.bound_field(self.original_field_name, self.view, self.item, self.context)
            _html, _display_parameters, _display_value = self.get_display_class_html(
                iter_value=iter_value, is_other_language=True)
            # Check display_value to avoid displaying the same value twice
            if hasValue(_display_value) and _display_value not in all_languages_display_values:
                all_languages_display_values.append(_display_value)
                all_languages_html[language] = _html
        translation_activate(current_user_language)
        self.bound_field(self.original_field_name, self.view, self.item, self.context)
        return [
            markSafeFormat(u'<div class="text-muted" lang="{}">{}</div>', language, html) if i != 0 else html
            for i, (language, html) in enumerate(all_languages_html.items())
        ], display_parameters

    def has_buttons_to_show(self, iter_value=None):
        for button_name in self.BUTTONS:
            if self.get_field_button_variable(button_name, prefix='show', iter_value=iter_value, default=False):
                return True
        return False

    def get_field_buttons_html(self, iter_value=None):
        return MagiDisplayButtons.to_html(
            self.item, OrderedDict([
                (button_name, self.get_field_button_variable(
                    button_name, 'text', iter_value=iter_value,
                    default=toHumanReadable(button_name)))
                for button_name in self.BUTTONS
                if self.get_field_button_variable(
                        button_name, prefix='show', iter_value=iter_value, default=True)
            ]),
            item_to_parameters=lambda button_name, _button_verbose: {
                'button': True,
                'button_class': 'link-muted',
                'link': self.get_field_button_variable(
                    button_name, 'url', iter_value=iter_value),
                'ajax_link': self.get_field_button_variable(
                    button_name, 'ajax_url', iter_value=iter_value),
                'ajax_link_title': self.get_field_button_variable(
                    button_name, 'ajax_link_title', iter_value=iter_value),
                'new_window': self.get_field_button_variable(
                    button_name, 'new_window', iter_value=iter_value, default=False),
                'text_icon': self.get_field_button_variable(
                    button_name, 'icon', iter_value=iter_value),
                'text_image': self.get_field_button_variable(
                    button_name, 'image', iter_value=iter_value),
            },
        )

    def get_field_button_variable(self, button_name, suffix='', prefix='', iter_value=None, default=None):
        variable_name = u'{}{}_button{}'.format(
            u'{}_'.format(prefix) if prefix else '', button_name, u'_{}'.format(suffix) if suffix else '',
        )
        if (self.is_multifields()
            and hasattr(self, u'multifields_{}'.format(variable_name))):
            return getattr(self, u'multifields_{}'.format(variable_name))(iter_value)
        elif hasattr(self, variable_name):
            return getattr(self, variable_name)
        return default

    def get_translate_button_url(self, text_value):
        return translationURL(
            self.to_text_value(),
            from_language=self.language,
            to_language=self.current_user_language,
            show_value=False, with_wrapper=False, markdown=False,
        )

    def add_json_ld_to_context(self):
        getJsonLd('Dataset', context=self.context)

############################################################
############################################################
############################################################
############################################################
# Model fields

############################################################
# MagiModelField

class MagiModelField(MagiField):
    BASE_VALID_ITEM_OPTIONS = mergeDicts(MagiField.BASE_VALID_ITEM_OPTIONS, {
        u'{}_HIDE_WHEN_DEFAULT': False,
    })

    @classmethod
    def is_field(self, field_name, model_field, options):
        return True

    ############################################################
    # Value
    # After bound. Can be overridden.

    def to_value(self):
        if self.has_translations:
            self.language, value = self.item.get_translation(
                self.item_access_field_name, language=self.current_user_language, return_language=True)
            return value
        if self.item_access_field_name.startswith('_cache_'):
            cached_field_name = self.item_access_field_name[len('_cache_'):]
            if (cached_field_name.startswith('i_') or cached_field_name.startswith('j_')
                or cached_field_name.startswith('c_')):
                cached_field_name = cached_field_name[2:]
            try:
                return getattr(self.item, u'cached_{}'.format(cached_field_name))
            except AttributeError:
                return super(MagiModelField, self).to_value()
        return super(MagiModelField, self).to_value()

    ############################################################
    # Translations

    @property
    def has_translations(self):
        return self.item_access_original_field_name in (getattr(self.collection, 'translated_fields', []) or [])

    def get_translation_languages(self):
        return self.item.get_field_translation_languages(self.item_access_field_name)

    def get_translation_sources(self):
        return self.item.get_display_translation_sources(self.item_access_field_name)

    ############################################################
    # Show/hide field

    def can_display_if_default(self):
        return (
            not self.model_field
            or not self.item_options['HIDE_WHEN_DEFAULT']
            or self.db_value != self.model_field.default
        )

    ############################################################
    # Display parameters

    def to_verbose_name(self):
        if self.model_field:
            verbose_name = getattr(self.model_field, '_verbose_name', None)
            if verbose_name:
                return verbose_name
        return super(MagiModelField, self).to_verbose_name()

    ############################################################
    # Display buttons per field

    # Suggest edit button

    @property
    def allows_upload(self):
        return (
            self.model_field
            and (isinstance(self.model_field, models.models.ImageField)
                 or isinstance(self.model_field, models.models.FileField)
                 or (isinstance(self.model_field, models.models.ManyToManyField)
                     and issubclass(self.model_field.rel.to, models.UserImage)))
        )

    ############################################################
    # Internals

    def init_unbound_field(self, model_field=None, **kwargs):
        self.model_field = model_field
        super(MagiModelField, self).init_unbound_field(**kwargs)

############################################################
############################################################
############################################################
# Field classes that work as model or non-model

############################################################
# Number field

class MagiNumberFieldMixin(object):
    @property
    def question(self):
        if self.is_plural and not isinstance(self.value, float):
            return _('How many {things} does {name} have?')
        try:
            return BaseMagiRelatedField.question.fget(self)
        except AttributeError:
            return BaseMagiRelatedField.question

class MagiNumberField(MagiNumberFieldMixin, MagiField):
    """
    Value: Integer or float
    """
    pass

class MagiNumberModelField(MagiNumberFieldMixin, MagiModelField):
    """
    Model field: IntegerField, PositiveIntegerField, FloatField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        for cls in [ models.models.PositiveIntegerField, models.models.IntegerField, models.models.FloatField ]:
            if isinstance(model_field, cls):
                return True
        return False

############################################################
# Char field

class MagiCharFieldMixin(object):
    pass

class MagiCharField(MagiCharFieldMixin, MagiField):
    """
    Value: String
    """
    pass

class MagiCharModelField(MagiCharFieldMixin, MagiModelField):
    """
    Model field: any
    """
    pass

############################################################
# Long text field

class MagiTextFieldMixin(object):
    faq = None

    display_class = MagiDisplayLongText
    default_verbose_name = _('Details')
    spread_across = True
    text_align = 'left'

class MagiTextField(MagiTextFieldMixin, MagiField):
    """
    Value: String
    """
    pass

class MagiTextModelField(MagiTextFieldMixin, MagiModelField):
    """
    Model field: TextField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return isinstance(model_field, models.models.TextField)

############################################################
# Textarea

class MagiTextareaFieldMixin(object):
    default_icon = 'developer'
    display_class = MagiDisplayTextarea
    faq = None

class MagiTextareaField(MagiTextareaFieldMixin, MagiField):
    """
    Value: String
    """
    pass

class MagiTextareaModelField(MagiTextareaFieldMixin, MagiModelField):
    """
    Model field: any
    """
    pass

############################################################
# Countdown

class MagiCountdownFieldMixin(object):
    default_icon = 'times'
    display_class = MagiDisplayCountdown
    default_verbose_name = _('Countdown')

class MagiCountdownField(MagiCountdownFieldMixin, MagiField):
    """
    Value: datetime.datetime
    """
    pass

class MagiCountdownModelField(MagiCountdownFieldMixin, MagiModelField):
    """
    Model field: DateTimeField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return isinstance(model_field, models.models.DateTimeField)

############################################################
# Date and date time field

class BaseMagiDateFieldMixin(object):
    @property
    def question(self):
        if (getEventStatus(self.value) == 'ended'
            and not fieldNameMatch(self.field_name, 'birthday')):
            return _('When was {name}\'s {thing}?')
        return _('When is {name}\'s {thing}?')

    @property
    def answer(self):
        try:
            return date_format(self.value, format='DATETIME_FORMAT', use_l10n=True)
        except AttributeError:
            return unicode(self.value)

    default_icon = 'date'
    default_verbose_name = _('Date')

class MagiDateTimeFieldMixin(BaseMagiDateFieldMixin):
    VALID_ITEM_OPTIONS = {
        '{}_FORMAT': {},
        # https://github.com/MagiCircles/MagiCircles/wiki/HTML-elements-with-automatic-Javascript-behavior#timezones
        # Example: { 'month': 'short' }
    }
    @property
    def display_class(self):
        if not hasattr(self.value, 'strftime'):
            return MagiDisplayText
        return MagiDisplayDateTimeWithTimezones

    timezones = [ 'Local time' ]

    @property
    def format(self):
        return self.item_options['FORMAT']

class MagiDateTimeField(MagiDateTimeFieldMixin, MagiField):
    """
    Value: datetime.datetime or string
    """
    pass

class MagiDateTimeModelField(MagiDateTimeFieldMixin, MagiModelField):
    """
    Model field: DateTimeField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return isinstance(model_field, models.models.DateTimeField)

    @property
    def timezones(self):
        return self.item.get_displayed_timezones(self.item_access_field_name)

class MagiDateFieldMixin(BaseMagiDateFieldMixin):
    VALID_ITEM_OPTIONS = {
        u'SHOW_{}_YEAR': True,
        u'{}_FORMAT': None,
        # https://github.com/MagiCircles/MagiCircles/wiki/DateTime-fields#format
        # Example: 'MONTH_DAY_FORMAT'
    }

    def to_display_value_from_value(self, value):
        if not value:
            return None
        if not hasattr(value, 'strftime'):
            return value
        if self.item_options['FORMAT']:
            return date_format(value, format=self.item_options['FORMAT'], use_l10n=True)
        elif not self.item_options['SHOW_YEAR']:
            return date_format(value, format='MONTH_DAY_FORMAT', use_l10n=True)
        return date_format(value, format='DATE_FORMAT', use_l10n=True)

    @property
    def answer(self):
        return self.to_display_value_from_value(self.value)

    display_class = MagiDisplayText

class MagiDateField(MagiDateFieldMixin, MagiField):
    """
    Value: datetime.datetime or string
    """
    pass

class MagiDateModelField(MagiDateFieldMixin, MagiModelField):
    """
    Model field: DateField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return isinstance(model_field, models.models.DateField)

############################################################
# Image field

class MagiImageFieldMixin(object):
    VALID_KWARGS = [
        'thumbnail',
        'hq',
        'original',
    ]
    faq = None

    # Display

    default_verbose_name = _('Image')
    display_class = MagiDisplayImage

    @property
    def thumbnail(self):
        return (
            staticImageURL(self.fields_kwargs.get('thumbnail', None))
            or getattr(self.item, u'{}_thumbnail_url'.format(self.item_access_field_name), None)
        )

    @property
    def hq(self):
        return (
            staticImageURL(self.fields_kwargs.get('hq', None))
            or getattr(self.item, u'{}_2x_url'.format(self.item_access_field_name), None)
        )

    @property
    def original(self):
        return (
            staticImageURL(self.fields_kwargs.get('original', None))
            or getattr(self.item, u'{}_original_url'.format(self.item_access_field_name), None)
        )

class MagiImageField(MagiImageFieldMixin, MagiField):
    """
    Value: URL
    """
    pass

class MagiImageModelField(MagiImageFieldMixin, MagiModelField):
    """
    Model field: ImageField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return isinstance(model_field, models.models.ImageField)

    def to_display_value_from_value(self, value):
        return getattr(self.item, u'{}_url'.format(self.item_access_field_name), None)

############################################################
# File field

class MagiFileFieldMixin(object):
    # Value

    def to_display_value(self, iter_value=None):
        # value_from_display_property is used in link.
        return _('Download')

    faq = None

    # Display

    display_class = MagiDisplayLink
    default_icon = 'download'
    default_verbose_name = _('Download')
    new_window = True
    button = True
    button_class = 'link-secondary padding-nohorizontal'
    text_icon = 'download'

    @property
    def link(self):
        return (
            self.value_from_display_property
            if self.retrieved_display_value
            else self.db_value
        )

class MagiFileField(MagiFileFieldMixin, MagiField):
    """
    Value: URL
    """
    pass

class MagiFileModelField(MagiFileFieldMixin, MagiModelField):
    """
    Model field: FileField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return isinstance(model_field, models.models.FileField)

    @property
    def link(self):
        return (
            self.value_from_display_property
            if self.retrieved_display_value
            else getattr(self.item, u'{}_url'.format(self.item_access_field_name), None)
        )

############################################################
# Main image field

class MagiMainImageFieldMixin(object):
    default_icon = 'download'
    default_verbose_name = _('Image')
    verbose_name_for_collapsed_table_header = ''

    def can_display(self):
        # Don't show main image because it's assumed to be shown on top of the fields
        # Exceptions: if it's specified in only_fields or it has a 2x value or suggest edit is on
        if ('image' not in (self.options.only_fields or [])
            and not getattr(self.item, u'{}_2x_url'.format(self.item_access_field_name), None)
            and not self.show_suggest_edit_button):
            return False
        return True

    def has_value(self):
        return hasValue(self.value) or hasValue(self.thumbnail)

    # Table view only: Links to open the item

    @property
    def link(self):
        if (self.options.table_view
            and self.collection.item_view.enabled):
            return self.item.item_url
        return None

    @property
    def ajax_link(self):
        if (self.options.table_view
            and self.collection.item_view.enabled
            and self.collection.item_view.ajax):
            return self.item.ajax_item_url
        return None

    @property
    def ajax_link_title(self):
        return self.item if self.options.table_fields else None

    @property
    def thumbnail(self):
        if self.options.table_fields:
            return self.item.display_image_in_list
        return MagiImageFieldMixin.thumbnail.fget(self)

class MagiMainImageField(MagiMainImageFieldMixin, MagiImageField):
    """
    Value: URL
    """
    @classmethod
    def is_field(self, field_name, options):
        return field_name == 'image'

class MagiMainImageModelField(MagiMainImageFieldMixin, MagiImageModelField):
    """
    Model field: ImageField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return field_name == 'image'

############################################################
# Birthday field

class MagiBirthdayFieldMixin(object):
    def to_faq(self):
        faq_for_field = super(MagiBirthdayFieldMixin, self).to_faq()
        if (not self.item_options['SHOW_YEAR']
            or 'age' in self.magifields.fields):
            return faq_for_field
        faq_for_field.append((
            _('How old is {name}?').format(
                name=self.name_for_question,
            ), getAge(self.value, formatted=True),
        ))
        return faq_for_field

    # Display

    default_icon = 'birthday'
    default_verbose_name = _('Birthday')

    @property
    def annotation(self):
        if not self.item_options['SHOW_YEAR']:
            return None
        return getAge(self.db_value, formatted=True)

class MagiBirthdayField(MagiBirthdayFieldMixin, MagiDateField):
    """
    Value: datetime.datetime or string
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return fieldNameMatch(field_name, 'birthday')

class MagiBirthdayModelField(MagiBirthdayFieldMixin, MagiDateModelField):
    """
    Model field: DateField
    Condition: Name contains "birthday"
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return (
            isinstance(model_field, models.models.DateField)
            and fieldNameMatch(field_name, 'birthday')
        )

############################################################
# Boolean field

class MagiBooleanFieldMixin(object):
    def to_display_value_from_value(self, value):
        return _('Yes') if value else _('No')

    question = _('Is {name} {thing}?')

    @property
    def answer(self):
        return self.to_display_value_from_value(self.value)

    # Display

    @property
    def text_icon(self):
        return 'checked' if self.db_value else 'delete'

class MagiBooleanField(MagiBooleanFieldMixin, MagiField):
    """
    Value: Bool
    """
    pass

class MagiBooleanModelField(MagiBooleanFieldMixin, MagiModelField):
    """
    Model field: BooleanField or NullBooleanField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return (
            isinstance(model_field, models.models.BooleanField)
            or isinstance(model_field, models.models.NullBooleanField)
        )

############################################################
# iTunes field

class MagiITunesFieldMixin(object):
    faq = None
    display_class = MagiDisplayITunes
    default_icon = 'play'
    default_verbose_name = _('Preview')

class MagiITunesField(MagiITunesFieldMixin, MagiField):
    """
    Value: Integer or string
    """
    pass

class MagiITunesModelField(MagiITunesFieldMixin, MagiModelField):
    """
    Model field: any
    Condition: Name contains "itunes_id
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return fieldNameMatch(field_name, 'itunes_id')

############################################################
# Age field

class MagiAgeFieldMixin(object):
    question = _('How old is {name}?')

    @property
    def answer(self):
        return self.to_display_value(self.value)

    def to_display_value_from_value(self, value):
        return _(u'{age} years old').format(age=value)

    default_icon = 'scoreup'
    default_verbose_name = _('Age')

class MagiAgeField(MagiAgeFieldMixin, MagiField):
    """
    Value: Integer or string
    """
    pass

class MagiAgeModelField(MagiAgeFieldMixin, MagiModelField):
    """
    Model field: any
    Condition: Name contains "age"
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return fieldNameMatch(field_name, 'age')

############################################################
# Seconds field

class MagiDurationFieldMixin(object):
    def to_display_value_from_value(self, value):
        return secondsToHumanReadable(value)

    @property
    def answer(self):
        return self.to_display_value_from_value(self.value)

    default_icon = 'times'
    default_verbose_name = _('Length')

class MagiDurationField(MagiDurationFieldMixin, MagiNumberField):
    """
    Value: Integer (seconds)
    """
    pass

class MagiDurationModelField(MagiDurationFieldMixin, MagiNumberModelField):
    """
    Model field: see number
    Condition: Name contains length and help_text contains "seconds", or name contains duration
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return (
            (fieldNameMatch(field_name, 'length')
             and model_field.help_text and 'seconds' in getEnglish(model_field.help_text))
            or fieldNameMatch(field_name, 'duration'))

############################################################
# Size field

class MagiSizeFieldMixin(object):
    VALID_ITEM_OPTIONS = {
        u'{}_CM_ONLY': False, # will not convert to km, m, cm
        u'{}_INCHES_ONLY': False, # will not convert to miles, feet, inches
    }

    @property
    def question(self):
        if fieldNameMatch(self.field_name, 'height'):
            return _('How tall is {name}?')
        elif fieldNameMatch(self.field_name, 'size') or fieldNameMatch(self.field_name, 'length'):
            return _('What is {name}\'s {thing}?')
        return _('What is {name}\'s {thing} size?')

    def to_display_value_from_value(self, value):
        return cmToHumanReadable(value, cm_only=self.cm_only)

    @property
    def annotation(self):
        if self.language in [ 'en', 'my' ]:
            return inchesToHumanReadable(cm=self.value, inches_only=self.inches_only)
        return None

    @property
    def answer(self):
        if self.language in [ 'en', 'my' ]:
            return u'{} ({})'.format(
                cmToHumanReadable(cm=self.value, cm_only=self.cm_only),
                inchesToHumanReadable(cm=self.value, inches_only=self.inches_only),
            )
        return self.to_display_value(self.value)

    default_icon = 'measurements'
    default_verbose_name = _('Height')

    ############################################################
    # Tools

    @property
    def inches_only(self):
        if self.item_options['INCHES_ONLY']:
            return True
        for field_name_match in [ 'bust', 'waist', 'hips' ]:
            if fieldNameMatch(self.field_name, field_name_match):
                return True
        return False

    @property
    def cm_only(self):
        return self.item_options['CM_ONLY']

class MagiSizeField(MagiSizeFieldMixin, MagiNumberField):
    """
    Value: Integer
    """
    pass

class MagiSizeModelField(MagiSizeFieldMixin, MagiNumberModelField):
    """
    Model field: see number
    Condition: Name contains height, size, length, bust, waist, hips
    """
    _FIELD_NAME_MATCHES = [
        'height', 'size', 'length', 'bust', 'waist', 'hips',
    ]
    @classmethod
    def is_field(self, field_name, model_field, options):
        for field_name_match in self._FIELD_NAME_MATCHES:
            if fieldNameMatch(field_name, field_name_match):
                return True
        return False

############################################################
# Money field

class MagiMoneyFieldMixin(object):
    VALID_ITEM_OPTIONS = {
        u'{}_CURRENCY_SYMBOL': '$',
        u'{}_CURRENCY_AS_PREFIX': True,
    }

    question = _('How much does {name} cost?')

    def format_value_with_currency(self, value):
        if self.item_options['CURRENCY_AS_PREFIX']:
            return markSafeFormat(u'{}{}', self.item_options['CURRENCY_SYMBOL'], value)
        return markSafeFormat(u'{} {}', value, self.item_options['CURRENCY_SYMBOL'])

    def to_display_value_from_value(self, value):
        return self.format_value_with_currency(value)

    @property
    def answer(self):
        return self.format_value_with_currency(self.value)

    default_icon = 'money'

    @property
    def default_verbose_name(self):
        if fileNameMatch(field_name, 'cost'):
            return _('Cost')
        return _('Price')

class MagiMoneyField(MagiMoneyFieldMixin, MagiField):
    """
    Value: Integer or string
    """
    pass

class MagiMoneyModelField(MagiMoneyFieldMixin, MagiModelField):
    """
    Model field: any
    Condition: Name must contain either "price", "cost" or "fee"
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return fieldNameMatch(field_name, 'price', 'cost', 'fee')

############################################################
# Video field

class MagiYouTubeVideoFieldMixin(object):
    faq = None

    def to_video_ld(self):
        if not self.has_value():
            return None
        return {
            'video_url': self.value,
            'video_title': u'{} - {}'.format(self.item, self.verbose_name),
            'video_description': (
                self.verbose_name_subtitle
                or self.annotation
                or self.verbose_name
            ),
            'upload_date': (
                getattr(self.item, 'creation', None)
                or getattr(self.item, 'release_date', None)
                or 'unknown'
            ),
        }

    # Translations

    @property
    def show_translate_button(self):
        return False

    def show_multiple_languages_translations(self):
        return False

    # Display

    display_class = MagiDisplayYouTubeVideo
    default_icon = 'play'
    default_verbose_name = _('Video')
    spread_across = True

    def to_display_value_from_value(self, value):
        if not value:
            return value
        if self.has_translations and self.language != self.current_user_language:
            return YouTubeVideoField.translated_embed_url(value, language=self.current_user_language)
        return YouTubeVideoField.embed_url(value)

    @property
    def url(self):
        return self.db_value

    @property
    def thumbnail(self):
        if not self.has_value():
            return None
        return YouTubeVideoField.thumbnail_url(self.value, size='maxresdefault')

class MagiYouTubeVideoField(MagiYouTubeVideoFieldMixin, MagiField):
    """
    Value: URL (https://www.youtube.com/watch?v=xxxxxxxxxxx)
    """
    pass

class MagiYouTubeVideoModelField(MagiYouTubeVideoFieldMixin, MagiModelField):
    """
    Model field: YouTubeVideoField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return isinstance(model_field, YouTubeVideoField)

############################################################
# Color field

class MagiColorFieldMixin(object):
    display_class = MagiDisplayColor
    default_icon = 'palette'
    default_verbose_name = _('Color')

class MagiColorField(MagiColorFieldMixin, MagiField):
    """
    Value: Hex code
    """
    pass

class MagiColorModelField(MagiColorFieldMixin, MagiModelField):
    """
    Model field: ColorField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return isinstance(model_field, ColorField)

############################################################
# URL field

class MagiURLFieldMixin(object):
    def to_display_value(self):
        # value_from_display_property is used in link.
        return self.verbose_name

    faq = None

    @property
    def verbose_name_for_buttons(self):
        return _('Link').lower()

    # Display

    display_class = MagiDisplayLink
    default_icon = 'world'
    default_verbose_name = _('Link')
    new_window = True
    external_link_icon = True
    button = True

    @property
    def link(self):
        return (
            self.value_from_display_property
            if self.retrieved_display_value
            else self.value
        )

    def link_content_to_parameters(self, parameters):
        return {
            'text_icon': self.icon,
        }

    @property
    def annotation(self):
        if self.db_value:
            return getDomainFromURL(self.db_value)
        return None

class MagiURLField(MagiURLFieldMixin, MagiField):
    """
    Value: URL
    """
    pass

class MagiURLModelField(MagiURLFieldMixin, MagiModelField):
    """
    Model field: URLField
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return isinstance(model_field, models.models.URLField)

############################################################
# i_ Choice field

class MagiIChoiceFieldMixin(object):
    # Internally:
    # db_value = integer value, as stored in db
    # value = string value
    # display_value = translated string

    @classmethod
    def to_field_name(self, original_field_name):
        if original_field_name.startswith('i_'):
            return original_field_name[2:]
        return original_field_name

    @property
    def answer(self):
        display_value = self.to_display_value()
        if isMarkedSafe(display_value):
            return self.value
        return display_value

    # Display

    @property
    def text_image(self):
        if self.options.table_fields:
            return self.get_auto_image()
        return None

class MagiIChoiceField(MagiIChoiceFieldMixin, MagiField):
    """
    DB value: int
    Value: string
    ℹ️  https://github.com/MagiCircles/MagiCircles/wiki/Save-choices-values-as-integer-rather-than-strings

    It's required to specify either kwargs:
    - item
    - model_class
    field_name defaults to self.original_field_name
    You should specify either db_value or value, but not both or none.
    """
    VALID_KWARGS = [
        'model_class',
        'field_name',
    ]

    # Shortcuts

    @property
    def rel_model_class(self):
        # If item specified, default to item model class
        if self.fields_kwargs.get('item', None):
            return type(self.item)
        if not self.fields_kwargs.get('model_class', None):
            raise ValueError('model_class is required in MagiIChoiceField')
        return self.fields_kwargs['model_class']

    @property
    def rel_field_name(self):
        if 'field_name' not in self.fields_kwargs:
            return self.original_field_name
        return self.fields_kwargs['field_name']

    # Field name

    def to_item_access_original_field_name(self):
        if modelHasField(self.rel_model_class, self.rel_field_name):
            return self.rel_field_name
        if (not self.rel_field_name.startswith('i_')
            and modelHasField(self.rel_model_class, u'i_{}'.format(self.rel_field_name))):
            return u'i_{}'.format(self.rel_field_name)
        return self.rel_field_name

    def to_item_access_field_name(self):
        return self.rel_field_name

    # Init

    def bound_init_before_item_options(self):
        self.model = self.rel_model_class
        self.model_field = modelGetField(self.rel_model_class, self.item_access_original_field_name)

    def to_verbose_name(self):
        if self.model_field:
            verbose_name = getattr(self.model_field, '_verbose_name', None)
            if verbose_name:
                return verbose_name
        return super(MagiIChoiceFieldMixin, self).to_verbose_name()

    # Value

    def to_value(self):
        value = super(MagiIChoiceFieldMixin, self).to_value()
        # If value was specified but not db_value, set db_value from value with get_i
        if 'db_value' not in self.fields_kwargs:
            self.db_value = self.rel_model_class.get_i(self.rel_field_name, value)
        return value

    def to_display_value(self):
        return self.rel_model_class.get_verbose_i(self.rel_field_name, self.db_value)

class MagiIChoiceModelField(MagiIChoiceFieldMixin, MagiModelField):
    """
    Model field: PositiveIntegerField
    Condition: Name starts with "i_"
    ℹ️  https://github.com/MagiCircles/MagiCircles/wiki/Save-choices-values-as-integer-rather-than-strings
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return field_name.startswith('i_')

    def to_item_access_field_name(self):
        item_access_field_name = super(MagiIChoiceModelField, self).to_item_access_field_name()
        if item_access_field_name.startswith('i_'):
            return item_access_field_name[2:]
        return item_access_field_name

    def to_display_value(self):
        return getattr(self.item, u't_{}'.format(self.item_access_field_name))

############################################################
# CSV field

class MagiCSVFieldMixin(MagiModelField):
    """
    Value: String or List or OrderedDict({ value: translation })
    """
    VALID_ITEM_OPTIONS = {
        u'{}_LINK_TO_FILTER': False,
        u'{}_LINK_TO_PRESET': False,
    }

    ############################################################
    # Init

    def get_auto_image(self):
        # Auto image exists for CSV values, but it's used per value individually and not as overall image
        return None

    ############################################################
    # Value

    def to_db_value(self):
        # Ensure value is always an OrderedDict or list
        db_value = super(MagiCSVFieldMixin, self).to_db_value()
        if isinstance(db_value, basestring):
            db_value = split_data(db_value)
        return db_value

    def to_text_value(self):
        return andJoin([
            value for value in self.value.values() if not isMarkedSafe(value)
        ])

    is_usually_plural = True

    ############################################################
    # Display

    display_class = MagiDisplayList
    default_icon = 'icons-list'
    default_verbose_name = __(_('{things} list'), things=_('Items'))

    @property
    def item_display_class(self):
        if self.item_options['LINK_TO_FILTER'] or self.item_options['LINK_TO_PRESET']:
            return MagiDisplayLink
        return MagiDisplayText

    def item_to_parameters(self, value, verbose_value):
        if self.item_display_class == MagiDisplayLink:
            return self.get_link_parameters(value, verbose_value)
        return self.get_text_parameters(value, verbose_value)

    ############################################################
    # Parameters for item

    def get_text_parameters(self, value, verbose_value):
        return {
            'text_image': self.get_auto_image_foreach(value),
            'text_image_alt': verbose_value,
        }

    def get_link_parameters(self, value, verbose_value):
        parameters = {
            'link': (
                self.collection.get_list_url(ajax=self.ajax, modal_only=self.ajax, preset=value)
                if self.item_options['LINK_TO_PRESET']
                else self.collection.get_list_url(ajax=self.ajax, modal_only=self.ajax, parameters={
                        self.item_access_original_field_name: value,
                })
            ),
            'link_content_to_parameters': lambda _parameters: self.get_text_parameters(value, verbose_value),
        }
        if self.collection.list_view.ajax:
            parameters['ajax_link'] = (
                self.collection.get_list_url(ajax=True, modal_only=True, preset=value)
                if self.item_options['LINK_TO_PRESET']
                else self.collection.get_list_url(ajax=True, modal_only=True, parameters={
                        self.item_access_original_field_name: value,
                })
            )
            parameters['ajax_link_title'] = verbose_value
        return parameters

class MagiCSVField(MagiCSVFieldMixin, MagiField):
    """
    Value: String or List or OrderedDict({ value: translation })
    """
    pass

class MagiCSVModelField(MagiCSVFieldMixin, MagiModelField):
    """
    Model field: TextField
    Condition: Name starts with "c_"
    ℹ️  https://github.com/MagiCircles/MagiCircles/wiki/Store-comma-separated-values
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return field_name.startswith('c_')

    @classmethod
    def to_field_name(self, original_field_name):
        if original_field_name.startswith('c_'):
            return original_field_name[2:]
        return original_field_name

    def to_item_access_field_name(self):
        item_access_field_name = super(MagiCSVModelField, self).to_item_access_field_name()
        if item_access_field_name.startswith('c_'):
            return item_access_field_name[2:]
        return item_access_field_name

    def to_value(self):
        return getattr(self.item, u't_{}'.format(self.item_access_field_name))

############################################################
# Markdown field

class MagiMarkdownFieldMixin(object):
    # Value

    def has_value(self):
        return hasValue(self.value[1])

    faq = None

    def to_text_value(self):
        return self.value[1]

    # Display

    display_class = MagiDisplayMarkdown
    default_icon = 'list'
    default_verbose_name = _('Details')

    @property
    def allow_html(self):
        return self.collection.allow_html_in_markdown or None

class MagiMarkdownField(MagiMarkdownFieldMixin, MagiTextField):
    """
    Value: tuple

           (True, '<b>something</b>')
        or (False, '**something**')
        or (True, '<b>something</b>', '**something**')
    """

    def to_text_value(self):
        return getIndex(self.value, 2, default=self.value[1])

class MagiMarkdownModelField(MagiMarkdownFieldMixin, MagiTextModelField):
    """
    Model field: TextField
    Condition: Name starts with "m_"
    ℹ️  https://github.com/MagiCircles/MagiCircles/wiki/Store-Markdown-texts
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return field_name.startswith('m_')

    @classmethod
    def to_field_name(self, original_field_name):
        if original_field_name.startswith('m_'):
            return original_field_name[2:]
        return original_field_name

    def to_item_access_field_name(self):
        item_access_field_name = super(MagiMarkdownModelField, self).to_item_access_field_name()
        if item_access_field_name.startswith('m_'):
            return item_access_field_name[2:]
        return item_access_field_name

    def to_text_value(self):
        # Always Markdown as stored in db (not HTML)
        return self.db_value

############################################################
# Dict field

class MagiDictFieldMixin(object):
    @classmethod
    def to_field_name(self, original_field_name):
        if original_field_name.startswith('d_'):
            return original_field_name[2:]
        return original_field_name

    ############################################################
    # Init

    def get_auto_image(self):
        # Auto image exists for dict, but it's used per dict keys individually and not as overall image
        return None

    ############################################################
    # Value

    def to_text_value(self):
        return u'\n'.join([
            u'{} - {}'.format(*(
                [ value['verbose'], value['value'] ]
                if isinstance(value, dict)
                else [ key, value ]
            )) for key, value in self.value.items()
            if not isMarkedSafe(value['value'] if isinstance(value, dict) else value)
        ])

    faq = None

    is_usually_plural = True

    ############################################################
    # Display

    display_class = MagiDisplayDescriptionList
    default_icon = 'icons-list'
    default_verbose_name = _('Details')
    spread_across = True
    text_align = 'left'

    def item_key_to_parameters(self, key, value):
        return {
            'text_image': self.get_auto_image_foreach(key),
        }

class MagiDictField(MagiDictFieldMixin, MagiField):
    """
    Value: OrderedDict({ choice_value: { verbose (choice verbose), value } })
           or { key: value }
    """
    pass

class MagiDictModelField(MagiDictFieldMixin, MagiModelField):
    """
    Model field: TextField
    Condition: Name starts with "d_"
    ℹ️  https://github.com/MagiCircles/MagiCircles/wiki/Store-dictionaries
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return field_name.startswith('d_')

    def to_item_access_field_name(self):
        item_access_field_name = super(MagiDictModelField, self).to_item_access_field_name()
        if item_access_field_name.startswith('d_'):
            return item_access_field_name[2:]
        return item_access_field_name

    def to_value(self):
        return getattr(self.item, u't_{}'.format(self.item_access_field_name))

############################################################
# Character field

class MagiICharacterFieldMixin(object):
    display_class = MagiDisplayTextWithLink

    def to_display_value_from_value(self, value):
        return getCharacterNameFromPk(value)

    def to_verbose_name(self):
        return getCharacterLabel()

    @property
    def link(self):
        return getCharacterURLFromPk(self.value)

    @property
    def ajax_link(self):
        return getCharacterURLFromPk(self.value, ajax=True)

    @property
    def link_text(self):
        return _('Open {thing}').format(thing=getCharacterLabel().lower())

    @property
    def image_for_link(self):
        return getCharacterImageFromPk(self.value)

class MagiICharacterField(MagiICharacterFieldMixin, MagiIChoiceField):
    pass

class MagiICharacterModelField(MagiICharacterFieldMixin, MagiIChoiceModelField):
    @classmethod
    def is_field(self, field_name, model_field, options):
        return (
            super(MagiIChoiceModelField, self).is_field(field_name, model_field, options)
            and fieldNameMatch(field_name, 'character')
        )

############################################################
# Leaderboard position field

class MagiLeaderboardPositionFieldMixin(object):
    default_verbose_name = _('Leaderboard position')
    default_icon = 'trophy'

    @property
    def display_class(self):
        return (
            MagiDisplayImage
            if self.value <= 3
            else MagiDisplayText
        )

    def to_display_value_from_value(self, value):
        if value <= 3:
            return staticImageURL(u'badges/medal{}.png'.format(4 - value))
        return u'#{}'.format(value)

    @property
    def link(self):
        return self.collection.get_list_url()

class MagiLeaderboardPositionField(MagiLeaderboardPositionFieldMixin, MagiField):
    """
    Value: Integer
    """
    pass

class MagiLeaderboardPositionModelField(MagiLeaderboardPositionFieldMixin, MagiModelField):
    """
    Model field: IntegerField
    Condition: Name contains "leaderboard"
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return (
            isinstance(model_field, models.models.IntegerField)
            and fieldNameMatch(field_name, 'leaderboard')
        )

############################################################
############################################################
############################################################
# Field classes that don't work for model fields

############################################################
# Unicode field

class MagiUnicodeField(MagiField):
    """
    Auto-value (unicode(item))
    """
    @classmethod
    def is_field(self, field_name, options):
        return field_name == 'unicode'

    @property
    def default_verbose_name(self):
        return self.collection.title

    def to_db_value(self):
        return getattr(self.item, 'name', unicode(self.item))

    def to_value(self):
        return unicode(self.item)

    def has_value(self):
        return True

############################################################
# Empty field

class MagiEmptyField(MagiField):
    """
    Auto-value ('')
    """
    @classmethod
    def is_field(self, field_name, options):
        return True

    def to_db_value(self):
        return None

    def to_display_value(self, iter_value=None):
        return u''

    def has_value(self):
        return True

    default_verbose_name = ' '

############################################################
# Social media template

class MagiSocialMediaTemplateField(MagiTextareaField):
    """
    Value: String or None
    Will be displayed within the template
    "extra" can also be specified in item (ex: TWITTER_EXTRA) or as kwargs
    """
    TEMPLATE = u"""🆕 New {thing}! {unicode}

{value}

{url}

{link_in_bio_sentence}
{bio_link}

{extra}

{hashtags}"""

    LINK_IN_BIO_SENTENCE = u'↓ Link in bio to see all {things} ↓'
    BIO_LINK = u'{emoji1} @{handle} {emoji2}'

    VALID_ITEM_OPTIONS = {
        u'{}_TEMPLATE': TEMPLATE,
        u'{}_EXTRA': None,
        u'{}_TEMPLATE_VARIABLES': {},
    }

    default_icon = 'share'
    default_verbose_name = _('Share')

    def to_handle(self):
        return django_settings.SITE

    def apply_template(self, variables):
        return re.sub(r'\n{3,}', '\n\n', self.item_options['TEMPLATE'].format(**variables)).strip()

    def to_template_variables(self):
        emojis = getEmojis(how_many=2)
        template_variables = {
            'site_name': getSiteName(),
            'list_url': self.collection.get_list_url(full=True) if self.collection else SITE_URL,
            'thing': self.collection.title,
            'things': self.collection.plural_title,
            'unicode': unicode(self.item),
            'value': self.db_value or '',
            'url': self.item.http_item_url,
            'emoji1': emojis[0],
            'emoji2': emojis[1],
            'handle': self.to_handle(),
            'extra': self.item_options['EXTRA'] or '',
            'hashtags': u' '.join([ u'#{}'.format(hashtag) for hashtag in HASHTAGS ]),
        }
        template_variables.update({
            'link_in_bio_sentence': self.LINK_IN_BIO_SENTENCE.format(**template_variables),
            'bio_link': self.BIO_LINK.format(**template_variables),
        })
        template_variables.update(self.item_options['TEMPLATE_VARIABLES'])
        return template_variables

    def has_value(self):
        return True

    def to_value(self):
        return self.apply_template(self.to_template_variables())

############################################################
# Twitter template

class MagiTwitterTemplateField(MagiSocialMediaTemplateField):
    """
    Value: String or None
    Will be displayed within the tweet
    "extra" can also be specified in item (ex: TWITTER_EXTRA) or as kwargs
    """
    BASE_VALID_ITEM_OPTIONS = mergeDicts(MagiSocialMediaTemplateField.BASE_VALID_ITEM_OPTIONS, {
        '{}_PERMISSIONS_REQUIRED': [ 'post_on_twitter' ],
    })
    share_template_field_name = 'twitter'
    default_image = 'groups/twitter_cm'
    default_verbose_name = _('Twitter')

    LINK_IN_BIO_SENTENCE = u'↓ Check out {site_name} to see all {things} ↓'
    BIO_LINK = u'{emoji1} {list_url} {emoji2}'

    def to_handle(elf):
        return TWITTER_HANDLE

    def to_value(self):
        value = super(MagiTwitterTemplateField, self).to_value()
        if isTweetTooLong(value):
            variables = self.to_template_variables()
            # Try to reduce tweet size by removing tweet parts
            for key in [ 'extra', 'emoji2', 'emoji2', 'link_in_bio_sentence', 'bio_link', 'value' ]:
                variables[key] = u''
                new_tweet = self.apply_template(variables)
                if not isTweetTooLong(new_tweet):
                    return new_tweet
        return value

############################################################
# Instagram template

class MagiInstagramTemplateField(MagiSocialMediaTemplateField):
    """
    Value: String or None
    Will be displayed within the tweet
    "extra" can also be specified in item (ex: TWITTER_EXTRA) or as kwargs
    """
    BASE_VALID_ITEM_OPTIONS = mergeDicts(MagiSocialMediaTemplateField.BASE_VALID_ITEM_OPTIONS, {
        '{}_PERMISSIONS_REQUIRED': [ 'post_on_instagram' ],
    })
    share_template_field_name = 'instagram'
    default_image = 'groups/instagram_cm'
    default_verbose_name = _('Instagram')

    def to_handle(self):
        return INSTAGRAM_HANDLE

############################################################
############################################################
############################################################
# Field classes that only work with model fields

############################################################
# Base for foreign key fields and related fields

class BaseMagiRelatedField(MagiModelField):

    ############################################################
    # Init

    def get_rel_model_class(self):
        raise NotImplementedError('get_model_class is required in BaseMagiRelatedField')

    def bound_init_before(self):
        self._set_rel_options()
        self.rel_model_class = self.get_rel_model_class()
        self.rel_collection_name = (
            getattr(self.rel_model_class, 'collection_name', None)
            or getattr(self.rel_options, 'collection_name', None)
        )
        self.rel_collection = (
            getMagiCollection(self.rel_collection_name)
            if self.rel_collection_name else None
        )
        if not self.rel_model_class and self.rel_collection:
            self.rel_model_class = self.rel_collection.queryset.model
        self._set_rel_options_defaults()

    ############################################################
    # Value

    @property
    def is_multiple(self):
        raise NotImplementedError(
            '{} is_multiple is required in BaseMagiRelatedField'.format(self.field_name))

    # Note: is_multiple = there are multiple items showing within the same field
    # Not to be confused with is_multifields = multiple "rows" of fields from the same MagiFields

    ############################################################
    # Display

    def get_verbose_name_list(self):
        verbose_name_list = getattr(self, '_verbose_name_list', None)
        if verbose_name_list is None:
            verbose_name_list = getVerboseNameOfRelatedField(
                self.model, self.item_access_field_name, self.model_field,
                rel_options=self.rel_options,
                collection=self.rel_collection,
                plural=self.is_multiple,
                default=self.default_verbose_name,
                return_as_list=True,
            )
            self._verbose_name_list = verbose_name_list
        return verbose_name_list

    def to_verbose_name(self):
        if 'verbose_name' in self.fields_kwargs:
            return self.fields_kwargs['verbose_name']
        return u' - '.join([
            unicode(v) for v in self.get_verbose_name_list()
        ])

    @property
    def verbose_name_for_buttons(self):
        """
        For multi-level lookups, to avoid showing all the levels.
        Instead of: "More singers - voice actresses - View all"
        --> "More voice actresses - View all"
        """
        return self.get_verbose_name_list()[-1].lower()

    def to_icon(self):
        return (
            self.rel_options.icon
            or (
                getattr(self.rel_item, 'flaticon', None)
                if hasattr(self, 'rel_item')
                else None
            )
            or (
                getValueIfNotProperty(self.rel_model_class, 'flaticon')
                if self.rel_model_class
                else None
            )
            or (
                self.rel_collection.icon
                if self.rel_collection
                else None
            )
            or super(BaseMagiRelatedField, self).to_icon()
        )

    def to_image(self):
        image = (
            self.options.fields_images.get(self.field_name, None)
            or self.collection.fields_images.get(self.field_name, None)
            or self.get_auto_image()
            or self.rel_options.image
            or self.rel_collection.image if self.rel_collection else None
            or self.default_image
        )
        return staticImageURL(image(self.item) if callable(image) else image)

    @property
    def new_window(self):
        """
        Used by:
        - Single item - MagiDisplayTextWithLink
        - Multiple items - MagiDisplayGrid/MagiDisplayList MagiDisplayLink
        """
        if self.rel_options.new_window is not None:
            return self.rel_options.new_window
        return True

    ############################################################
    # Internal

    def _set_rel_options(self):
        if (isinstance(self.model_field, ReverseRelatedDetails)
            or isinstance(self.model_field, ForeignKeyRelatedDetails)):
            self.rel_options = self.model_field
        else:
            self.rel_options = getRelOptionsDict(
                model_class=self.model,
                field_name=self.item_access_field_name,
            )

    @property
    def rel_options_is_multiple(self):
        raise NotImplementedError(
            '{} rel_options_is_multiple is required in BaseMagiRelatedField'.format(self.field_name))

    def _set_rel_options_defaults(self):
        setRelOptionsDefaults(
            self.model, self.original_field_name,
            self.rel_collection, self.rel_options, is_multiple=self.rel_options_is_multiple)

############################################################
# Foreign key field

class MagiForeignKeyModelField(BaseMagiRelatedField):
    """
    Model field: ForeignKey or OneToOneField
                 or property or reverse relation
    Condition: field_name specified in:
               - collection.fields_preselected
               - or item.REVERSE_RELATED
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return (
            isinstance(model_field, models.models.ForeignKey)
            or isinstance(model_field, models.models.OneToOneField)
            or isinstance(model_field, ForeignKeyRelatedDetails)
        )

    ############################################################
    # Init

    def get_rel_model_class(self):
        if isinstance(self.model_field, ForeignKeyRelatedDetails):
            return getModelOfRelatedItem(self.model, self.item_access_field_name)
        return self.model_field.rel.to

    ############################################################
    # Value

    is_multiple = False
    rel_options_is_multiple = False

    def to_db_value(self):
        """
        Value: Item instance, cached item or None
        """
        if self.is_preselected:
            rel_item = getRelatedItemFromItem(self.item, self.item_access_field_name)
            self.retrieved_from = 'db'
        elif hasattr(self.item, 'cached_' + self.item_access_field_name):
            rel_item = getattr(self.item, 'cached_' + self.item_access_field_name, None)
            self.retrieved_from = 'cache'
        else:
            rel_item = None
            self.retrieved_from = None
        if rel_item:
            rel_item.request = self.request
            self.rel_item_url = (
                getattr(rel_item, 'item_url', None)
                if self.rel_collection.item_view.has_permissions(self.request, self.context, item=self.item)
                else None
            )
        else:
            self.rel_item_url = None
        return rel_item

    def to_value(self):
        return self.db_value

    @property
    def question(self):
        if getattr(self.rel_model_class, 'IS_PERSON', False):
            if self.is_plural:
                return _('Who are {name}\'s {things}?')
            return _('Who is {name}\'s {thing}?')
        try:
            return BaseMagiRelatedField.question.fget(self)
        except AttributeError:
            return BaseMagiRelatedField.question

    ############################################################
    # Special

    def get_template(self):
        return (
            self.rel_options.template_for_preselected
            or getattr(self.rel_model_class, 'template_for_preselected', None)
        )

    ############################################################
    # Show/hide field

    def can_display(self):
        return bool(self.retrieved_from)

    ############################################################
    # Display class

    @property
    def display_class(self):
        if self.rel_item and self.rel_item_url:
            return MagiDisplayTextWithLink
        return MagiDisplayText

    @property
    def default_verbose_name(self):
        return self.rel_collection.title

    # MagiDisplayTextWithLink
    # -----------------------

    @property
    def link_text(self):
        return _(u'Open {thing}').format(thing=self.verbose_name_for_buttons)

    @property
    def link(self):
        return self.rel_item_url

    @property
    def ajax_link(self):
        return (
            self.rel_item.ajax_item_url
            if (self.rel_item_url
                and self.rel_options.allow_ajax_per_item
                and self.rel_collection
                and self.rel_collection.item_view.ajax)
            else None
        )

    @property
    def ajax_link_title(self):
        return unicode(self.rel_item)

    @property
    def image_for_link(self):
        return staticImageURL(getImageForPrefetched(self.rel_item))

    # MagiDisplayText
    # ---------------

    text_image = image_for_link
    text_image_alt = ajax_link_title

    ############################################################
    # Tools

    # Shortcut for code readability
    @property
    def rel_item(self):
        return self.value

    @property
    def is_preselected(self):
        return (
            self.field_name in self.options.preselected_field_names
        )

############################################################
# Owner

class MagiOwnerModelField(MagiForeignKeyModelField):
    """
    Model field: See MagiForeignKeyModelField
    Condition: See MagiForeignKeyModelField + Name must be "owner"
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return (
            field_name == 'owner'
            and super(MagiOwnerModelField, self).is_field(field_name, model_field, options)
        )

    faq = None

    default_verbose_name = __(_('Added by {username}'), username='')

    @property
    def verbose_name_for_buttons(self):
        return self.rel_collection.title if self.rel_collection else _('User')

    def to_icon(self):
        icon = super(MagiOwnerModelField, self).to_icon()
        if icon == 'users' and self.rel_options.icon != 'users':
            return 'profile'
        return icon

############################################################
# Base for Many to many field + Cached total field

class ReverseRelatedDetails(AttrDict):
    pass

class ForeignKeyRelatedDetails(AttrDict):
    pass

class BaseMagiManyToManyModelField(BaseMagiRelatedField):
    @classmethod
    def is_prefetched(self, field_name, model_field, options):
        return (
            field_name in options.prefetched_field_names
            or field_name in options.prefetched_together_field_names
            or (
                isinstance(model_field, ReverseRelatedDetails)
                and (
                    model_field.get('prefetched', False)
                    or model_field.get('prefetched_together', False)
                )
            )
        )

    ############################################################
    # Init

    def get_rel_model_class(self):
        if isinstance(self.model_field, models.models.ManyToManyField):
            return self.model_field.rel.to
        elif isinstance(self.model_field, RelatedObject):
            return self.model_field.model
        elif isinstance(self.model_field, ReverseRelatedDetails):
            return getModelOfRelatedItem(self.model, self.item_access_field_name)
        return None

    def bound_init_after(self):
        self.rel_filter_field_name = self.get_rel_filter_field_name()
        self.cached_total = self.get_total_cache()

    is_usually_plural = True

    ############################################################
    # Tools

    def get_total_cache(self):
        try: return getattr(self.item, 'cached_total_{}'.format(self.item_access_field_name))
        except AttributeError: return None

    def get_cached_total_sentence(self):
        if self.cached_total == 0:
            return _('No result.')
        rel_plural_verbose_name = self.rel_plural_verbose_name
        if '{total}' in unicode(rel_plural_verbose_name):
            if self.cached_total is None:
                return rel_plural_verbose_name.format(total=u'')
            return rel_plural_verbose_name.format(total=self.cached_total)
        if self.cached_total is None:
            return _('Open {things}').format(things=rel_plural_verbose_name)
        return u'{total} {items}'.format(
            total=self.cached_total,
            items=rel_plural_verbose_name,
        )

    @property
    def rel_plural_verbose_name(self):
        """Used in cached total sentence"""
        return (
            self.rel_options.get('plural_verbose_name', None)
            or self.verbose_name_for_buttons
        )

    def get_rel_filter_field_name(self):
        """Used in get_list_url"""
        return (
            self.rel_options.filter_field_name
            or getFilterFieldNameOfRelatedItem(self.model, self.item_access_field_name)
            or self.collection.name
        )

    @property
    def rel_list_url(self):
        """
        Used by and_more button and cached total.
        """
        return self.get_list_url()

    @property
    def rel_list_ajax_url(self):
        return self.get_list_url(ajax=True)

    _list_url = None
    def get_list_url(self, ajax=False):
        if self._list_url is None:
            # If url is in rel_options, return url
            if self.rel_options.url and isFullURL(self.rel_options.url):
                self._list_url = self.rel_options.url
            # If it's a collectible collection, it should link to the owner's collection
            elif self.is_collectible():
                self._list_url = self.get_list_url_for_collectible(ajax=ajax)
            # Create link to rel_collection
            else:
                if self.rel_options.to_preset:
                    preset = tourldash(self.rel_options.to_preset(self.item))
                elif self.rel_collection:
                    preset = isPreset(self.rel_collection, {
                        self.rel_filter_field_name: self.item.pk,
                    }, disable_cleaning=True)
                else:
                    preset = None
                parameters = {}
                if not preset:
                    parameters[self.rel_filter_field_name] = self.item.pk
                if self.rel_options.url:
                    self._list_url = getListURL(
                        self.rel_options.url,
                        preset=preset,
                        parameters=parameters,
                    )
                elif self.rel_collection:
                    if (not self.rel_collection.list_view.enabled
                        or not self.rel_collection.list_view.has_permissions(self.request, self.context)
                        or (ajax and not self.rel_collection.list_view.ajax)):
                        self._list_url = ''
                    else:
                        self._list_url = self.rel_collection.get_list_url(
                            preset=preset,
                            ajax=ajax, modal_only=ajax,
                            parameters=parameters,
                        )
        if ajax:
            if (isFullURL(self._list_url)
                or (self.rel_collection and not self.rel_collection.list_view.ajax)):
                return None
            return addParametersToURL(u'/ajax{}'.format(self._list_url), parameters={ 'ajax_modal_only': '' })
        return self._list_url or None

    def is_collectible(self):
        return self.rel_collection and getattr(self.rel_collection, 'parent_collection', None)

    def get_list_url_for_collectible(self, ajax=False):
        owner_model_class = self.rel_model_class.owner_model_class()
        owner_collection = self.rel_model_class.owner_collection()
        filter_field_name = (
            self.rel_options.filter_field_name
            or u'{}__{}'.format(
                getFilterFieldNameOfRelatedItem(self.rel_model_class, self.rel_model_class.fk_as_owner or 'owner'),
                self.rel_collection.item_field_name,
            )
        )
        if self.rel_options.to_preset:
            preset = tourldash(self.rel_options.to_preset(self.item))
        elif self.rel_collection:
            preset = isPreset(owner_collection, {
                filter_field_name: self.item.pk,
            }, disable_cleaning=True)
        else:
            preset = None
        parameters = {}
        if not preset:
            parameters[filter_field_name] = self.item.pk
        if self.rel_options.url:
            return getListURL(
                self.rel_options.url,
                preset=preset,
                parameters=parameters,
            )
        elif self.rel_collection:
            if (not owner_collection.list_view.enabled
                or not owner_collection.list_view.has_permissions(self.request, self.context)
                or (ajax and not owner_collection.list_view.ajax)):
                return ''
            else:
                return owner_collection.get_list_url(
                    preset=preset,
                    ajax=ajax, modal_only=ajax,
                    parameters=parameters,
                )

############################################################
# Many to many field

class MagiManyToManyModelField(BaseMagiManyToManyModelField):
    """
    Model field: ManyToManyField
                 or property or reverse relation
    Condition: field_name specified in:
               - collection.fields_prefetched
               - or collection.fields_prefetched_together
               - or item.REVERSE_RELATED

    ITEM_OPTIONS:
    - {}_MAX
    - {}_SHOW_PER_LINE
    - {}_MAX_PER_LINE
    are all available as item options but not as kwargs.
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return (
            (
                isinstance(model_field, models.models.ManyToManyField)
                or isinstance(model_field, RelatedObject)
                or isinstance(model_field, ReverseRelatedDetails)
            )
            and self.is_prefetched(field_name, model_field, options)
        )

    ############################################################
    # Value

    def _not_prefetched_for_high_traffic(self):
        return self.original_field_name in getattr(self.request, '_not_prefetched_for_high_traffic', [])

    @property
    def is_multiple(self):
        return not self.is_multifields()

    rel_options_is_multiple = True

    def is_multifields(self):
        return (
            not self._not_prefetched_for_high_traffic()
            and (
                self.field_name in self.options.prefetched_field_names
                or getattr(self.rel_options, 'prefetched', False)
            )
        )

    def _and_more_button_total_from_rel_items(self, rel_items):
        if len(rel_items) > (self.rel_options.max or 0):
            cached_total = self.get_total_cache()
            if cached_total is not None and cached_total >= len(rel_items):
                self.and_more_button_total = cached_total - (len(rel_items) - 1)
            else:
                self.and_more_button_total = -1
        else:
            self.and_more_button_total = 0

    def to_db_value(self):
        if self.rel_options.max == 0:
            return []

        if self._not_prefetched_for_high_traffic():
            self.and_more_button_total = 0
            return []
        elif getattr(self.request, '_prefetched_with_max', {}).get(self.original_field_name):
            # Retrieve items that have been prefetched manually with a limit
            rel_items, self.rel_options.max = self.request._prefetched_with_max[self.original_field_name]
            self._and_more_button_total_from_rel_items(rel_items)
        elif isinstance(getattr(self.item, self.item_access_field_name, None), QuerySet):
            # Non-explicit relationships: manual queryset with a limit
            rel_items = getattr(self.item, self.field_name)[:self.rel_options.max + 1]
            self._and_more_button_total_from_rel_items(rel_items)
        else:
            # Retrieve items that have been prefetched with .all()
            rel_items = getRelatedItemsFromItem(self.item, self.item_access_field_name)
            self.and_more_button_total = len(rel_items) - (self.rel_options.max or 0)
            if self.and_more_button_total < 0:
                self.and_more_button_total = 0
        if self.rel_options.max:
            rel_items = rel_items[:self.rel_options.max]
        self.with_images = True
        self.with_links_to_collection = True
        self.with_links = True
        for rel_item in rel_items:
            if not rel_item:
                continue
            rel_item.request = self.request
            # Set image and link, if any
            image_field_name, image = getImageForPrefetched(
                rel_item, in_list=self.view.view == 'list_view', return_field_name=True,
            )
            rel_item._magimanytomanyfield_image = image
            rel_item._magimanytomanyfield_image_link = (
                getattr(rel_item, 'image_url')
                if image_field_name == 'image_thumbnail_url'
                else None
            )
            rel_item._magimanytomanyfield_item_url = (
                getattr(rel_item, 'item_url', None)
                if rel_item.has_item_view_permissions()
                else None
            )
            if not rel_item._magimanytomanyfield_image:
                self.with_images = False
            if not rel_item._magimanytomanyfield_item_url:
                self.with_links_to_collection = False
            if not rel_item._magimanytomanyfield_item_url and not rel_item._magimanytomanyfield_image_link:
                self.with_links = False
        return rel_items

    def to_value(self):
        return self.db_value

    @property
    def faq(self):
        # When there are no items, no question
        if not self.rel_items:
            return None
        faq_for_field = []
        # If we know how many items there are, ask how many
        if (self.and_more_button_total == 0
            or self.cached_total is not None):
            faq_for_field.append((
                _('How many {things} does {name} have?').format(
                    name=self.name_for_question,
                    things=self.verbose_name_for_question,
                ), (
                    len(self.rel_items) if self.and_more_button_total == 0
                    else self.cached_total
                )
            ))
        # List of items
        list_of_items = andJoin([ unicode(item) for item in self.rel_items ] + (
            [ _('More').lower() ] if self.and_more_button_total != 0 else []
        ))
        if getattr(self.rel_model_class, 'IS_PERSON', False):
            faq_for_field.append((
                _('Who are {name}\'s {things}?').format(
                    name=self.name_for_question,
                    things=self.verbose_name_for_question,
                ), list_of_items,
            ))
        else:
            faq_for_field.append((
                _('What are {name}\'s {things}?').format(
                    name=self.name_for_question,
                    things=self.verbose_name_for_question,
                ), list_of_items,
            ))
        return faq_for_field

    def to_text_value(self, iter_value=None):
        if self.is_multifields():
            return unicode(iter_value)
        return u'\n'.join([ unicode(item) for item in self.rel_items ] + (
            [ _('More').lower() ] if self.and_more_button_total != 0 else []
        ))

    def has_value(self):
        if hasValue(self.value):
            return True
        if self._not_prefetched_for_high_traffic():
            if self.is_crawler and not self.rel_list_url and self.cached_total is None:
                return False
            if self.cached_total is None or self.cached_total > 0:
                return True
        return False

    ############################################################
    # Special

    def get_template(self):
        return (
            not self.is_multifields()
            and not self._not_prefetched_for_high_traffic()
            and (
                self.rel_options.template_for_prefetched
                or getattr(self.rel_model_class, 'template_for_prefetched', None)
            )
        )

    ############################################################
    # Display

    @property
    def display_class(self):
        # Not prefetched due to high traffic
        if self._not_prefetched_for_high_traffic():
            if self.is_crawler:
                if self.rel_list_url:
                    return MagiDisplayLink
                return MagiDisplayText
            return MagiDisplayAlert
        # Multifields:
        if self.is_multifields():
            if self.with_links_to_collection:
                return MagiDisplayTextWithLink
            elif self.with_images:
                return MagiDisplayImage
            return MagiDisplayText
        # Prefetched together:
        else:
            if self.with_images:
                return MagiDisplayGrid
            return MagiDisplayList

    def to_display_value(self, iter_value=None):
        if self._not_prefetched_for_high_traffic():
            if self.is_crawler:
                return self.get_cached_total_sentence()
            return []
        if self.is_multifields() and self.display_class == MagiDisplayImage:
            return getattr(iter_value, '_magimanytomanyfield_image', None)
        return super(MagiManyToManyModelField, self).to_display_value(iter_value=iter_value)

    @property
    def default_verbose_name(self):
        if not self.rel_collection:
            return None
        if self.is_multiple:
            return self.rel_collection.plural_title
        return self.rel_collection.title

    # High traffic, when is_crawler
    # -----------------------------

    @property
    def link(self):
        return self.rel_list_url

    # High traffic, when not is_crawler
    # ---------------------------------

    @property
    def text_align(self):
        if self._not_prefetched_for_high_traffic() and not self.is_crawler:
            return 'center'
        return BaseMagiManyToManyModelField.text_align.fget(self)

    alert_title = 'This section is temporarily disabled due to high traffic'

    @property
    def alert_message(self):
        return markSafeFormat(
            u'{}<br><i class="fontx0-8">{}. {}</i>',
            markSafe(u"""
            You can can <a href="/signup/" target="_blank">signup <i class="flaticon-link"></i></a>
            or <a href="/login/" target="_blank">login <i class="flaticon-link"></i></a> to access it."""),
            _('If you like {site_name}, please consider donating').format(site_name=getSiteName()),
            _('This will help us cover the costs of the servers and allow us to keep it running for free and with minimal ads.'),
        )

    alert_button = {
        'url': '/donate/',
        'verbose': _('Donate'),
        'icon': 'heart',
    }

    # Multifields:
    # ------------

    def multifields_spread_across(self, iter_value):
        return self.is_ajax_popover()

    # Used by MagiDisplayTextWithLink and MagiDisplayImage

    def multifields_link(self, iter_value):
        return (
            iter_value._magimanytomanyfield_item_url
            or iter_value._magimanytomanyfield_image_link
        ) if iter_value is not None else None

    def multifields_ajax_link(self, iter_value):
        return (
            iter_value.ajax_item_url
            if (iter_value._magimanytomanyfield_item_url
                and self.rel_collection
                and self.rel_collection.item_view.ajax)
            else None
        ) if iter_value is not None else None

    def multifields_ajax_link_title(self, iter_value):
        return unicode(iter_value)

    # Used by MagiDisplayTextWithLink

    @property
    def multifields_link_text(self):
        return _(u'Open {thing}').format(thing=self.verbose_name_for_buttons)

    def multifields_image_for_link(self, iter_value):
        return iter_value._magimanytomanyfield_image if iter_value is not None else None

    # Used by MagiDisplayText

    multifields_text_image = multifields_image_for_link
    multifields_text_image_alt = multifields_ajax_link_title

    # Prefetched together:
    # --------------------

    @property
    def spread_across(self):
        return (
            self._not_prefetched_for_high_traffic()
            or self.is_ajax_popover()
            or self.with_images
        )

    @property
    def item_display_class(self):
        if self.with_links:
            return MagiDisplayLink
        elif self.with_images:
            return MagiDisplayImage
        return MagiDisplayText

    def item_to_value(self, rel_item, parameters_per_item):
        if self.with_images and not self.with_links:
            return rel_item._magimanytomanyfield_image
        return rel_item

    def _get_image_parameters(self, rel_item):
        return {
            'alt': rel_item,
            'with_link_wrapper': False,
            'tooltip': True,
        }

    def item_to_parameters(self, _key, rel_item):
        parameters = {}
        if self.with_links:
            parameters.update({
                'link': (
                    getattr(rel_item, '_magimanytomanyfield_item_url', None)
                    or getattr(rel_item, '_magimanytomanyfield_image_link', None)
                ),
                'new_window': self.new_window,
            })
            if (
                    getattr(rel_item, '_magimanytomanyfield_item_url', None)
                    and self.rel_collection
                    and self.rel_collection.item_view.ajax
                    and self.rel_options.allow_ajax_per_item
            ):
                parameters.update({
                    'ajax_link': getattr(rel_item, 'ajax_item_url', None),
                    'ajax_link_title': rel_item,
                })
        if self.with_images and self.with_links:
            parameters.update({
                'link_content_display_class': MagiDisplayImage,
                'link_content_to_value': lambda _rel_item, _parameters: getattr(
                    _rel_item, '_magimanytomanyfield_image', None),
                'link_content_to_parameters': self._get_image_parameters(rel_item),
            })
        elif self.with_links:
            text_image = (
                getattr(rel_item, 'text_image_for_prefetched', None)
                or rel_item._magimanytomanyfield_image
            )
            parameters.update({
                'button': True,
                'button_class': 'link-secondary',
                'link_classes': [ 'padding-novertical' ],
                'text_image': text_image,
                'text_icon': self.rel_collection.icon if not text_image else None,
                'text_image_alt': rel_item,
            })
        elif self.with_images:
            parameters.update(self._get_image_parameters(rel_item))
        return parameters

    # When display class is MagiDisplayGrid

    col_break = property(lambda _s: _s.rel_options.col_break)
    per_line = property(lambda _s: _s.rel_options.show_per_line)
    align = property(lambda _s: _s.rel_options.align)

    # When display class is MagiDisplayList

    @property
    def inline(self):
        return self.with_links or self.with_images

    ############################################################
    # Display buttons per field

    BUTTONS = [
        'and_more',
    ] + MagiField.BUTTONS

    # And more button

    @property
    def show_and_more_button(self):
        return (
            not self._not_prefetched_for_high_traffic()
            and not self.is_multifields()
            and self.rel_options.max
            and self.and_more_button_total
            and self.rel_list_url
        )

    @property
    def and_more_button_text(self):
        return u'+ {} {} - {}'.format(
            _('More') if self.and_more_button_total == -1 else self.and_more_button_total,
            self.verbose_name_for_buttons, _('View all'),
        )

    @property
    def and_more_button_url(self):
        if self.should_link_to_page2:
            return addParametersToURL(self.rel_list_url, anchor=u'{collection_name}-end-of-page-1'.format(
                collection_name=self.rel_collection_name))
        return self.rel_list_url

    @property
    def and_more_button_ajax_url(self):
        if not self.rel_options.allow_ajax_for_more:
            return None
        if self.should_link_to_page2:
            return addParametersToURL(self.rel_list_ajax_url, parameters={ 'page': 2 })
        return self.rel_list_ajax_url

    @property
    def and_more_button_ajax_link_title(self):
        return u'{} - {}'.format(self.item, self.verbose_name)

    @property
    def and_more_button_new_window(self):
        return self.new_window

    ############################################################
    # Tools

    # Shortcut for code readability
    @property
    def rel_items(self):
        return self.value

    @property
    def should_link_to_page2(self):
        """If the number of items displayed matches the number of items displayed by list view"""
        return (
            self.rel_list_ajax_url
            and self.rel_collection
            and self.rel_options.max
            and self.rel_options.max >= self.rel_collection.list_view.page_size
        )

############################################################
# Cached total field

class MagiCachedTotalModelField(BaseMagiManyToManyModelField):
    """
    Model field: ManyToManyField or reverse relation
    Condition: field_name NOT specified in:
               - collection.fields_prefetched
               - or collection.fields_prefetched_together

    OR

    Model field: property
    Condition: specified in item.REVERSE_RELATED
    """
    @classmethod
    def is_field(self, field_name, model_field, options):
        return (
            isinstance(model_field, models.models.ManyToManyField)
            or isinstance(model_field, RelatedObject)
            or isinstance(model_field, ReverseRelatedDetails)
        )

    ############################################################
    # Value

    is_multiple = True
    rel_options_is_multiple = False

    def to_db_value(self):
        return self.get_total_cache()

    def to_value(self):
        return self.db_value

    def to_display_value_from_value(self, value):
        return self.get_cached_total_sentence()

    def has_value(self):
        return super(MagiCachedTotalModelField, self).has_value() and self.value != 0

    question = _('How many {things} does {name} have?')

    ############################################################
    # Display

    @property
    def display_class(self):
        if (self.db_value == 0
            or not self.rel_list_url):
            return MagiDisplayText
        return MagiDisplayTextWithLink

    @property
    def default_verbose_name(self):
        return self.rel_collection.plural_title

    def to_verbose_name(self):
        return super(MagiCachedTotalModelField, self).to_verbose_name().replace('{total}', '')

    @property
    def link(self):
        return self.rel_list_url

    @property
    def link_text(self):
        return _('View all')

    @property
    def ajax_link(self):
        return self.rel_list_ajax_url

    @property
    def ajax_link_title(self):
        return u'{} - {}'.format(self.item, self.verbose_name)

    @property
    def image_for_link(self):
        return (
            self.rel_collection.list_view.share_image(self.context, item=self.item)
            if self.rel_collection else None
        )

############################################################
############################################################
############################################################
# MagiButtonField
# Used by buttons retrieved from buttons_per_item.
# Unlike most fields, it should never retrieve anything from the item,
# but from the button_options instead.

class MagiButtonField(MagiField):
    """
    Auto-value
    """
    @classmethod
    def is_field(self, field_name, options, button_options):
        return True

    ############################################################
    # Init

    def init_unbound_field(self, button_options=None, **kwargs):
        self.button_options = AttrDict(button_options)
        super(MagiButtonField, self).init_unbound_field(**kwargs)

    def bound_init_after(self):
        # Set parameters from button_options
        for button_option_name, parameter_name in [
                ('url', 'link'),
                ('ajax_url', 'ajax_link'),
                ('ajax_title', 'ajax_link_title'),
                ('open_in_new_window', 'new_window'),
                ('extra_attributes', 'data_attributes'),
                ('badge', 'text_badge'),
        ]:
            if not hasattr(self, parameter_name) and hasattr(self.button_options, button_option_name):
                try:
                    setattr(self, parameter_name, getattr(self.button_options, button_option_name))
                except AttributeError:
                    pass

    ############################################################
    # Value

    def to_db_value(self):
        return self.button_options

    def to_value(self):
        if self.options.show_item_buttons_as_icons:
            return u''
        return (
            self.button_options.get('button_title', None)
            or self._get_verbose_name()
        )

    def has_value(self):
        return True

    def can_display(self):
        return (
            getattr(self.button_options, 'show', True)
            and getattr(self.button_options, 'has_permissions', True)
        )

    def get_template(self):
        return self.button_options.get('template', None)

    def extra_context(self):
        if self.original_button_name == 'share':
            self.context['share_url'] = self.item.share_url
            self.context['share_btn_class'] = u' '.join(self.link_classes).replace('btn btn-', '')
            self.context['share_sentence'] = unicode(self.item)
            self.context['share_btn_group'] = True

    @property
    def has_translations(self):
        return False

    faq = None

    ############################################################
    # Permissions

    def is_staff_only(self):
        if 'staff-only' in self.button_options.get('classes', []):
            return True
        return super(MagiButtonField, self).is_staff_only()

    ############################################################
    # Display

    display_class = MagiDisplayButton

    def to_verbose_name(self):
        return self._get_verbose_name()

    def to_verbose_name_subtitle(self):
        return (
            self.button_options.get('subtitle', None)
            or super(MagiButtonField, self).to_verbose_name_subtitle()
        )

    default_icon = None

    def to_icon(self):
        return (
            self.button_options.get('icon', None)
            or self.default_icon
        )

    def to_image(self):
        return (
            staticImageURL(self.button_options.get('image', None))
            or super(MagiButtonField, self).to_image()
        )

    @property
    def text_image(self):
        return self.image

    button = False # button classes get added by link_classes

    @property
    def link_classes(self):
        return [ cls for cls in self.button_options.get('classes', []) if cls != 'staff-only' ]

    @property
    def attributes(self):
        return {
            'data-button': self.original_button_name,
        }

    @property
    def link_attributes(self):
        return {
            'data-btn-name': self.original_button_name,
            'title': self.verbose_name,
        }

    @property
    def text_icon(self):
        return (
            self.button_options.get('button_icon')
            or self.icon
        )

    @property
    def annotation(self):
        return self.button_options.get('annotation', None)

    ############################################################
    # Display buttons per field

    BUTTONS = []

    ############################################################
    # Internals

    @property
    def original_button_name(self):
        return self.field_name[7:]

    def _get_verbose_name(self):
        verbose_name = self.button_options.get('title', None)
        if not verbose_name:
            verbose_name = toHumanReadable(self.original_button_name, capitalize=True, warning=True)
        return verbose_name(self.item) if callable(verbose_name) else verbose_name

    def get_value_from_display_property(self):
        self.value_from_display_property = None
        self.retrieved_display_value = False

############################################################
############################################################
############################################################

############################################################
# MagiFields

class MagiFields(object):
    ############################################################
    # Optional variables

    order_settings = {}
    # See options of newOrder in utils.

    exclude_fields = []
    # Exclude fields with these names (original field name "i_XXX" or field name both work).

    allow_special_fields = []
    # 'id' field, any field that start with an "_" and
    # translation fields will never be displayed unless
    # they're specifically listed here.

    preselected_subfields = {}
    # If a foreign key has been preselected, the following sub-fields can be displayed

    ############################################################
    # Optional variables than can also be given to __init__

    OPTIONS = {
        'table_fields': None,
        # List of field names.
        # Will set only_fields to the same list, force_all_fields to True, and order to the same list of fields.

        'ordering_fields': False,
        # List of field names.
        # Will set only_fields to the same list.

        'only_fields': None,
        # List of field names.
        # Don't show any other field than the one that have their names listed here.

        'force_all_fields': False,
        # All valid fields will be displayed, even when they don't have a value.
        # Can be used in combination with only_fields, which will ensure all fields specified
        # will be returned. Unknown field names in only_fields will be empty fields.

        'order': None,
        # Specify the fields order (list of field names).
    }

    # List of configurations that should be retrieved from the view
    # with their default value when it's not set
    OPTIONS_FROM_VIEW = mergeDicts({
        'fields_exclude': [],
        'fields_icons': {},
        'fields_images': {},
        'fields_order': [],
        'fields_suggest_edit': [],
        'get_fields_order': None,
        'fields_order_settings': {},
        'fields_preselected': [],
        'fields_preselected_subfields': {},
        'fields_prefetched': [],
        'fields_prefetched_together': [],
        'show_suggest_edit_button': True,
        'show_item_buttons_as_icons': False,
    }, {
        u'fields_{}'.format(MagiField.item_option_to_kwarg(_option_name)): {}
        for _option_name in PERMISSION_ITEM_OPTIONS.keys()
    })
    # Note: The following options are deprecated (when MagiFields class was introduced):
    # - fields_extra
    # - get_extra_fields

    ############################################################
    # Extra fields

    # Fields get retrieved automatically from the model class.

    # To add any extra field, you can just set their class or instance
    # as object variables.
    # Example with an extra field (not a model field):
    #   warning = MagiCharField(verbose_name=_('Warning'), value='Only available in the shop.')

    # You can also specify one for existing model fields as a way to
    # customize how it's displayed.
    # Example with a model's property:
    #   rarity_image = MagiImageField

    # If you pass an instance, you can initialize it with:
    # db_value, value, and any other variable you can find in
    # MagiDisplay.PARAMETERS except field_name
    # (verbose_name, icon, image, ...).
    # value and db_value can be callables that take item.

    # Below is the list of classes that can be used for extra fields.
    # Listed solely for reference, this variable is not used anywhere.
    # You're free to setup your own field classes by inheriting from MagiField.
    # For model fields, you should inherit from MagiModelField.
    # You can also inherit from existing sub classes.
    _EXTRA_FIELD_CLASSES = [
        MagiMainImageField,
        MagiNumberField,
        MagiCharField,
        MagiTextField,
        MagiCSVField,
        MagiIChoiceField,
        MagiMarkdownField,
        MagiDictField,
        MagiImageField,
        MagiFileField,
        MagiBooleanField,
        MagiDateTimeField,
        MagiCountdownField,
        MagiBirthdayField,
        MagiDateField,
        MagiITunesField,
        MagiColorField,
        MagiYouTubeVideoField,
        MagiURLField,
        MagiAgeField,
        MagiDurationField,
        MagiSizeField,
        MagiMoneyField,
        MagiTextareaField,
        MagiSocialMediaTemplateField,
        MagiTwitterTemplateField,
        MagiInstagramTemplateField,
        MagiLeaderboardPositionField,
        MagiICharacterField,
        MagiUnicodeField,
        MagiEmptyField,
    ]

    # In addition to adding fields by setting their class or instance as object variables,
    # it's also possible to add them to this dict - although it's generally less readable,
    # so not the most recommended option.
    # You can also override "prepare_extra_fields" to fill this up.
    # If you do, Make sure you reset it (self.EXTRA_FIELDS = OrderedDict())
    EXTRA_FIELDS = OrderedDict()

    ############################################################
    # List of field classes, sorted
    # When fields are determined automatically, "is_field" gets
    # called for each of them, and the first one that returns
    # True is the class that gets used.

    # Model fields, including many to many fields
    # and reverse many to many fields.
    MODEL_FIELD_CLASSES = [
        MagiMainImageModelField,
        MagiManyToManyModelField,
        MagiCachedTotalModelField,
        MagiOwnerModelField,
        MagiForeignKeyModelField,
        MagiICharacterModelField,
        MagiIChoiceModelField,
        MagiMarkdownModelField,
        MagiCSVModelField,
        MagiDictModelField,
        MagiImageModelField,
        MagiBooleanModelField,
        MagiDateTimeModelField,
        MagiBirthdayModelField,
        MagiDateModelField,
        MagiFileModelField,
        MagiITunesModelField,
        MagiColorModelField,
        MagiYouTubeVideoModelField,
        MagiURLModelField,
        MagiLeaderboardPositionModelField,
        MagiAgeModelField,
        MagiDurationModelField,
        MagiSizeModelField,
        MagiMoneyModelField,
        MagiTextModelField,
        MagiNumberModelField,

        # Catch-all:
        MagiCharModelField,

        # Never used automatically, but can be used by users when customizing their MagiFields class:
        MagiTextareaModelField,
        MagiCountdownModelField,
    ]

    # Virtual fields specified in REVERSE_RELATED, preselected,
    # prefetched or prefetched_together that don't match many
    # to many model fields or reverse many to many model fields.
    RELATED_FIELD_CLASSES = [
        MagiManyToManyModelField,
        MagiCachedTotalModelField,
        MagiForeignKeyModelField,
    ]

    # When all fields are forced and a field class could
    # not be auto-determined, these classes will be used.
    MISSING_FIELD_CLASSES = [
        MagiMainImageField, # 'image' field name
        MagiUnicodeField, # 'unicode' field name
        MagiEmptyField,
    ]

    # All of these will be called in item view if share_templates is True
    # They all need a variable or property `share_template_field_name`
    SHARE_TEMPLATES_FIELD_CLASSES = [
        MagiTwitterTemplateField,
        MagiInstagramTemplateField,
    ]

    # Buttons displayed at the end, retrieved from buttons_per_item.
    BUTTON_FIELD_CLASSES = [
        MagiButtonField,
    ]

    ############################################################
    # Methods that can be overridden

    # Called at beginning of bound
    def to_name_for_questions(self):
        if not getattr(self.view, 'show_faq', False):
            return None
        try:
            return self.item.name_for_questions
        except AttributeError:
            try:
                return self.item.t_name
            except AttributeError:
                return unicode(self.item)

    ############################################################
    # Init
    # Request + context used when:
    # - Permissions to show suggest edit button, permissions to list/item url
    # - Retrieve buttons_per_item
    # Context used when:
    # - share_image for many to many cached total
    # Request used when:
    # - To retrieve current language (fallsback to get_language)
    # - Set in rel_items (sometimes used by model properties)
    # - Determine if currently ajax
    # Item can be None. In that case, you're expected to call "bound_fields(item)" yourself later.

    def __init__(self, view, item, context, **kwargs):
        self.item = item # May be None
        self.view = view
        self.context = context

        self.request = getattr(item, 'request', None)
        if self.context and 'ajax' in self.context:
            self.ajax = self.context['ajax']
        else:
            self.ajax = isRequestAjax(self.request)
        if self.context and 'is_crawler' in self.context:
            self.is_crawler = self.context['is_crawler']
        else:
            self.is_crawler = isRequestCrawler(self.request)
        self.collection = view.collection
        self.model = self.collection.queryset.model

        self.options = AttrDict(dict([
            (option, getattr(view, option, default))
            for option, default in self.OPTIONS_FROM_VIEW.items()
        ] + [
            (option, kwargs.get(option, default))
            for option, default in self.OPTIONS.items()
        ]))
        if self.options.table_fields:
            self.options.only_fields = self.options.table_fields
            self.options.force_all_fields = True
            self.options.order = self.options.table_fields
        elif self.options.ordering_fields:
            self.options.only_fields = self.options.ordering_fields

        self.prepare_fields()
        self.set_fields()
        if item:
            self.order_fields()
            self.bound_fields(item)

    def prepare_fields(self):
        self.prepare_model_fields_options()
        self.prepare_related_fields_options()
        self.prepare_extra_fields()

    def set_fields(self):
        self.excluded = []
        self.skipped = []
        self.fields = OrderedDict()
        self.fields_per_category = OrderedDict()

        self.set_model_fields()
        self.set_related_fields()
        self.set_extra_fields()
        self.set_missing_fields()
        self.set_share_templates_fields()
        if self.item: # Buttons may be set again on bound
            self.set_button_fields()

        if SHOW_DEBUG and (self.view.view == 'item_view' or SHOW_DEBUG_LIST):
            print self.__class__.__name__
            print 'Skipped:', andJoin(self.skipped, translated=False)
            print 'Excluded:', andJoin(self.excluded, translated=False) if self.excluded else u'None'

    def order_fields(self):
        if (
                self.order_settings # Set in custom MagiFields class
                or self.options.order # Passed as __init__ of MagiFields (ex: table)
                or self.options.fields_order # In view
                or self.options.fields_order_settings # In view
                or (self.options.get_fields_order and self.item) # In view
        ):
            self.fields = newOrder(
                self.fields,
                order=(
                    (self.options.order or [])
                    + (self.options.fields_order or [])
                    + (self.options.get_fields_order(self.item)
                       if self.item and self.options.get_fields_order else [])
                ),
                insert_in_dict_when_missing=False,
                **mergeDicts(self.order_settings, self.options.fields_order_settings)
            )

    def set_unbound_field(
            self, type, field_name, cls=None,
            kwargs_for_init_only={}, field_name_for_is_field=None,
            **kwargs):
        """
        Determines which class to use for a given field
        type can be MODEL, RELATED, EXTRA, MISSING, BUTTON
        cls can also be an instance of that class.
        kwargs are parameters given to is_field + init_unbound_field.
        - MODEL, RELATED: model_field
        - BUTTON: button_options
        """
        # From attribute (similar to Django form)
        if not cls and type != 'BUTTON':
            cls = getattr(self, field_name, None)
            if (
                    not failSafe(lambda: issubclass(cls, MagiField), exceptions=[ TypeError ], default=False)
                    and not isinstance(cls, MagiField)
            ):
                cls = None
        # From classes list, first for which is_field returns True
        if not cls:
            for class_option in getattr(self, u'{}_FIELD_CLASSES'.format(type)):
                if class_option.is_field(field_name_for_is_field or field_name, options=self.options, **kwargs):
                    cls = class_option
                    break

        if cls:
            # The class can already have been instanciated, or not
            if isinstance(cls, MagiField):
                kwargs_for_init = mergeDicts(cls.fields_kwargs, kwargs_for_init_only)
                field = type_f(cls)(**kwargs_for_init)
            else:
                field = cls(**kwargs_for_init_only)
            field.init_unbound_field(magifields=self, **kwargs)

            if field:
                if self._should_exclude_field(field_name, field):
                    self.excluded.append(field_name)
                else:
                    self.fields[field_name] = field
                    if type not in self.fields_per_category:
                        self.fields_per_category[type] = OrderedDict()
                    self.fields_per_category[type][field_name] = field

    ############################################################
    # Model fields

    def prepare_model_fields_options(self):
        self.options.preselected_field_names = [
            p[0] if isinstance(p, tuple) else p
            for p in self.options.fields_preselected
        ]

    def set_model_fields(self):
        self._found_preselected_subfields = {}
        for field_name, model_field in getAllModelFields(self.model).items():

            if (
                    field_name not in self.allow_special_fields

                    and (

                        # Skip id
                        field_name == 'id'

                        # Skip hidden fields (cache, thumbnails, etc)
                        or field_name.startswith('_')

                        # Skip fields used to save translations (shown by main field)
                        or isTranslationField(field_name, self.collection.translated_fields or [])

                    )
            ):
                self.skipped.append(field_name)
                continue

            self.set_unbound_field('MODEL', field_name, model_field=model_field)
            if field_name in self.options.fields_preselected_subfields:
                self.set_model_preselected_subfields(
                    field_name, model_field, self.options.fields_preselected_subfields[field_name])
            elif field_name in self.preselected_subfields:
                self.set_model_preselected_subfields(
                    field_name, model_field, self.preselected_subfields[field_name])

    def set_model_preselected_subfields(self, field_name, model_field, subfields_list):
        for subfield_field_name in subfields_list:
            if isinstance(model_field, RelatedObject):
                subfield_model_field = modelGetField(model_field.model, subfield_field_name)
            else:
                subfield_model_field = modelGetField(model_field.rel.to, subfield_field_name)
            if subfield_model_field:
                new_subfield_field_name = u'{}__{}'.format(field_name, subfield_field_name)
                self.set_unbound_field(
                    'MODEL', new_subfield_field_name, model_field=subfield_model_field,
                    kwargs_for_init_only={ 'item_access_field_name': subfield_field_name },
                    field_name_for_is_field=subfield_field_name,
                )
                self._found_preselected_subfields[new_subfield_field_name] = (field_name, subfield_field_name)
            else:
                # Only works with simple subfields
                if django_settings.DEBUG:
                    raise NotImplementedError(u"""
                    Preselected subfields only supports basic subfields
                    (no reverse relations or extra fields)
                    Unknown: {}""".format(subfield_field_name))

    ############################################################
    # Related fields

    def prepare_related_fields_options(self):
        self.options.prefetched_field_names = [
            p[0] if isinstance(p, tuple) else p
            for p in self.options.fields_prefetched
        ]
        self.options.prefetched_together_field_names = [
            p[0] if isinstance(p, tuple) else p
            for p in self.options.fields_prefetched_together
        ]

    def set_related_fields(self):
        # Field names specified in prefetched and prefetched_together but
        # couldn't be guessed from the model class
        for field_name in self.options.fields_preselected:
            rel_options = getRelOptionsDict(model_class=self.model, field_name=field_name)
            if field_name not in self.fields:
                self.set_unbound_field(
                    'RELATED', field_name, model_field=ForeignKeyRelatedDetails(rel_options))
        for field_name in self.options.fields_prefetched + self.options.fields_prefetched_together:
            if isinstance(field_name, tuple):
                field_name = field_name[0]
            rel_options = getRelOptionsDict(model_class=self.model, field_name=field_name)
            if field_name not in self.fields:
                self.set_unbound_field(
                    'RELATED', field_name, model_field=ReverseRelatedDetails(rel_options))
        # Any other field in REVERSE_RELATED
        for rel_options in (
                getattr(self.model, 'REVERSE_RELATED', [])
                + getattr(self.model, 'reverse_related', []) # for backwards compatibility
        ):
            rel_options = getRelOptionsDict(rel_options=rel_options)
            if rel_options.field_name not in self.fields:
                self.set_unbound_field(
                    'RELATED', rel_options.field_name, model_field=ReverseRelatedDetails(rel_options))

    ############################################################
    # Extra fields

    def prepare_extra_fields(self):
        pass

    def set_extra_fields(self):
        for field_name, cls in self.EXTRA_FIELDS.items():
            self.set_unbound_field('EXTRA', field_name, cls=cls)
        for field_name in dir(self):
            if field_name not in self.fields and field_name != 'faq':
                cls = getattr(self, field_name)
                if (
                        failSafe(
                            lambda: issubclass(cls, MagiField),
                            exceptions=[ TypeError ], default=False,
                        )
                        or isinstance(cls, MagiField)
                ):
                    self.set_unbound_field('EXTRA', field_name, cls=cls)

    ############################################################
    # Missing fields

    def set_missing_fields(self):
        if self.options.force_all_fields and self.options.only_fields is not None:
            for field_name in self.options.only_fields:
                if field_name not in self.fields:
                    self.set_unbound_field('MISSING', field_name)

    ############################################################
    # Share template fields

    def set_share_templates_fields(self):
        if self.view.view != 'item_view' or not self.view.share_templates:
            return
        to_set = self.SHARE_TEMPLATES_FIELD_CLASSES[:]
        for field in self.fields.values():
            for cls in to_set:
                if isinstance(field, cls):
                    to_set.remove(cls)
        for cls in to_set:
            self.set_unbound_field('SHARE_TEMPLATES', cls.share_template_field_name, cls=cls)

    ############################################################
    # Buttons

    def set_button_fields(self):
        if not self.item or self.view.show_item_buttons_in_one_line:
            return
        buttons = self.view.buttons_per_item(self.request, self.context, self.item)
        if self.view.view == 'list_view':
            self.collection.set_buttons_auto_open(buttons)
        for button_name, button_options in buttons.items():
            self.set_unbound_field(
                'BUTTON', u'button_{}'.format(button_name), button_options=button_options)

    def unset_button_fields(self):
        for field_name in self.fields_per_category['BUTTON'].keys():
            self.fields.pop(field_name)
        self.fields_per_category.pop('BUTTON')

    ############################################################
    # Imitate dict behavior

    def items(self):
        for field_name, value in self.fields.items():
            yield field_name, value

    def __iter__(self):
        for _field_name, value in self.items():
            yield value

    def keys(self):
        for field_name, _value in self.items():
            yield field_name

    def values(self):
        for _field_name, value in self.items():
            yield value

    ############################################################
    # Bound

    def bound_fields(self, item):
        # If item changed
        if item != self.item:
            self.item = item
            # Reset buttons fields
            self.unset_button_fields()
            self.set_button_fields()
            # Re-order if needed
            if self.options.get_fields_order:
                self.order_fields()
        else:
            self.item = item
        self.name_for_questions = self.to_name_for_questions()

        if SHOW_DEBUG and (self.view.view == 'item_view' or SHOW_DEBUG_LIST):
            print 'Unbound fields:'
            if self.fields:
                for field_name, field in self.fields.items():
                    print u'  {:30}\t{:30}'.format(field_name, field.__class__.__name__)
            else:
                print '  None'
        bound_and_displayed = []
        bound_and_not_displayed = OrderedDict()
        for field_name, field in self.fields.items():
            field.display_field = False

            if field_name in self._found_preselected_subfields:
                sub_item_field_name, subfield_field_name = self._found_preselected_subfields[field_name]
                sub_item = getattr(self.item, sub_item_field_name)
                field.bound_field(field_name, self.view, sub_item, self.context)
            else:
                field.bound_field(field_name, self.view, self.item, self.context)

            if (
                    self.options.force_all_fields
                    or (
                        field.show
                        and (
                            field.has_buttons_to_show()
                            or (
                                field.has_value()
                                and field.can_display_if_other_language()
                                and field.can_display_if_default()
                            )
                        )
                    )
            ):
                field.display_field = True
                bound_and_displayed.append(field_name)
            else:
                reason = None
                if SHOW_DEBUG:
                    if not field.has_permissions():
                        reason = '!permission'
                    elif not field.can_display():
                        reason = '!can_display'
                    elif not field.show:
                        reason = '!show'
                    elif not field.has_value():
                        reason = '!has_value'
                bound_and_not_displayed[field.field_name] = reason
        if SHOW_DEBUG and (self.view.view == 'item_view' or SHOW_DEBUG_LIST):
            print 'Bound and displayed:', andJoin(
                bound_and_displayed, translated=False) if bound_and_displayed else 'None'
            print 'Bound and not displayed:', andJoin([
                u'{} ({})'.format(key, value) for key, value in bound_and_not_displayed.items()
            ], translated=False) if bound_and_not_displayed else 'None'

        self.extra_context()

    ############################################################
    # Extra context
    # Called at the end of bound

    def extra_context(self):
        # SEO: Article + F.A.Q.
        if not self.ajax and self.view.view == 'item_view':
            if getattr(self.view, 'show_article_ld', False):
                articleJsonLdFromItem(self.item, body=self.get_article_body(), context=self.context)
            if getattr(self.view, 'show_faq', False):
                FAQjsonLd(flattenListOfLists(self.faq.values()), context=self.context)
            for field_name, field in self.fields.items():
                video_ld = field.to_video_ld()
                if video_ld:
                    videoJsonLd(context=self.context, **video_ld)

    ############################################################
    # SEO: Article
    # Called at the end of bound (by extra_context) for item views

    def get_article_body(self):
        return u'\n'.join([
            u'{}: {}'.format(
                field.verbose_name,
                (field.to_text_value() or '').replace(u'\n', ', '),
            )
            for field_name, field in self.fields.items()
            if field.display_field and not isinstance(field, MagiButtonField)
        ])

    ############################################################
    # SEO: F.A.Q.
    # Called at the end of bound (by extra_context) and by template for item views

    faq_title = _('F.A.Q.')

    @property
    def faq(self):
        if (not getattr(self.view, 'show_faq', False)
            or not self.name_for_questions):
            return {}
        if not hasattr(self, '_faq'):
            faq = OrderedDict()
            for field_name, field in self.fields.items():
                if field.display_field and field.has_value() and not field.is_multifields():
                    faq_for_field = field.to_faq()
                    if faq_for_field:
                        faq[field_name] = faq_for_field
            self._faq = faq
        return self._faq

    ############################################################
    # Table headers

    def get_table_headers(self):
        if self.view.hide_table_fields_headers:
            return []
        return [
            (field_name, field.verbose_name_for_table_header)
            for field_name, field in self.fields.items()
        ]

    def get_table_headers_sections(self):
        return self.view.table_fields_headers_sections(view=self.context.get('view', None))

    ############################################################
    # Internal

    # Called before bound, when setting fields
    def _should_exclude_field(self, field_name, field):
        field_name_options = [ field_name, field.to_field_name(field_name) ]
        # Options: self.exclude_fields or self.options.fields_exclude
        for field_name_option in field_name_options:
            if (field_name_option in self.exclude_fields
                or field_name_option in self.options.fields_exclude):
                return True
        # Option: self.options.only_fields
        if self.options.only_fields is not None:
            for field_name_option in field_name_options:
                if field_name_option in self.options.only_fields:
                    return False
            return True
        return False

############################################################
############################################################
############################################################
# MagiFields classes

############################################################
# Account & users

class AccountFriendId(MagiCharModelField):
    @property
    def permissions_required(self):
        if getattr(self.item, 'show_friend_id', True):
            return []
        return [ 'see_account_verification_details' ]

class AccountFields(MagiFields):
    allow_special_fields = [ '_cache_leaderboard' ]
    reputation = MagiCharField(
        verbose_name='Reputation',
        value=lambda _item: _item.owner.preferences.cached_reputation,
        ordering_fields_only=True,
        permissions_required=[ 'see_reputation' ],
    )

    friend_id = AccountFriendId

############################################################
# User

class UserFields(MagiFields):
    preselected_subfields = { 'preferences': [ '_cache_reputation' ] }
    preferences___cache_reputation = MagiCharModelField(
        permissions_required=[ 'see_reputation '], ordering_fields_only=True,
    )

############################################################
# Prizes

class PrizeFields(MagiFields):
    i_character = MagiICharacterModelField

############################################################
# Staff configurations

class StaffConfigurationValueField(MagiTextModelField):
    @property
    def display_class(self):
        if self.item.is_markdown:
            return MagiDisplayMarkdown
        elif self.item.is_image:
            return MagiDisplayImage
        return MagiDisplayText

    def to_display_value_from_value(self, value):
        if self.item.is_markdown:
            return (False, value or '')
        elif self.item.is_image:
            return staticImageURL(value)
        elif self.item.is_boolean:
            return _('Yes') if value else _('No')
        return value or ''

    @property
    def text_icon(self):
        if self.item.is_boolean:
            return 'checked' if self.db_value else 'delete'
        return None

class StaffConfigurationFields(MagiFields):
    value = StaffConfigurationValueField

############################################################
############################################################
############################################################
# Abstract MagiFields classes

############################################################
# Events

# Event field: Versions

class EventVersions(MagiCSVModelField):
    @classmethod
    def is_field(self, field_name, model_field, options):
        return field_name == 'c_versions'

    # Links to scroll to version details smoothly
    @property
    def item_display_class(self):
        if self.ajax:
            return MagiDisplayText
        return MagiDisplayLink

    def get_link_parameters(self, value, verbose_value):
        return {
            'link': u'#version{}'.format(value),
            'link_content_to_parameters': lambda _parameters: self.get_text_parameters(value, verbose_value),
            'link_classes': [ 'page-scroll' ],
        }

# Event field: Mixin with and without version

class EventFieldMixin(object):
    # Shortcuts
    event_status = property(lambda _s: _s.item.status)
    event_start_date = property(lambda _s: _s.item.start_date)
    event_end_date = property(lambda _s: _s.item.end_date)

class EventVersionFieldMixin(object):
    VALID_KWARGS = [
        'version_name',
    ]

    # Shortcuts
    version_name = property(lambda _s: _s.fields_kwargs['version_name'])
    version = property(lambda _s: _s.model.VERSIONS[_s.version_name])
    event_status = property(lambda _s: _s.item.get_status_for_version(_s.version_name))
    event_start_date = property(lambda _s: _s.item.get_start_date_for_version(_s.version_name))
    event_end_date = property(lambda _s: _s.item.get_end_date_for_version(_s.version_name))

    # Value
    to_value = lambda _s: ''
    has_value = lambda _s: True

    def can_display(self):
        return (
            super(EventVersionFieldMixin, self).can_display()
            and self.version_name in self.item.versions
        )

# Event field: Version title

class EventVersionTitleField(EventVersionFieldMixin, MagiCharField):
    # Display basics
    verbose_name = property(lambda _s: _s.item.get_name_for_version(_s.version_name) or unicode(_s.item))
    verbose_name_subtitle = property(lambda _s: _s.item.get_version_name(_s.version_name))
    image = property(lambda _s: _s.item.get_version_image(_s.version_name))
    icon = property(lambda _s: _s.item.get_version_icon(_s.version_name))
    attributes = property(lambda _s: { 'id': _s.anchor })

    # Display class
    display_class = property(lambda _s: MagiDisplayImage if _s.get_relevant_image() else MagiDisplayText)
    to_display_value = lambda _s: _s.get_relevant_image() or ''

    # Display class: image
    link = property(lambda _s: addParametersToURL(_s.item.item_url, anchor=_s.anchor))
    link_text = property(lambda _s: _s.item.get_name_for_version(_s.version_name))
    new_window = False

    # Utils
    anchor = property(lambda _s: u'version{}'.format(_s.version_name))
    def get_relevant_image(self):
        if '{}image' in self.model.FIELDS_PER_VERSION_AND_LANGUAGE:
            return self.item.get_value_of_relevant_language_for_version('image_url', self.version_name)
        return self.item.get_field_for_version('image_url', self.version_name)

# Event field: Countdown + Version countdown

class EventCountdownFieldMixin(object):
    def can_display(self):
        return (
            super(EventCountdownFieldMixin, self).can_display()
            and self.event_status not in [ 'ended', 'invalid' ]
        )

    def to_value(self):
        if self.event_status == 'current':
            return self.event_end_date
        return self.event_start_date

    @property
    def countdown_template(self):
        if self.event_status == 'current':
            return _('{time} left')
        return _('Starts in {time}')

class EventVersionCountdownField(EventCountdownFieldMixin, EventVersionFieldMixin, MagiCountdownField):
    pass

class EventCountdownField(EventCountdownFieldMixin, EventFieldMixin, MagiCountdownField):
    pass

# BaseEventFields class

class BaseEventFields(MagiFields):
    MODEL_FIELD_CLASSES = [
        EventVersions,
    ] + MagiFields.MODEL_FIELD_CLASSES

    def prepare_extra_fields(self):
        self.EXTRA_FIELDS = OrderedDict()
        if self.collection.with_versions:
            for version_name in self.model.VERSIONS.keys():
                # Add event version title field
                self.EXTRA_FIELDS[version_name] = EventVersionTitleField(version_name=version_name)
                # Add version countdown field
                self.EXTRA_FIELDS[
                    self.model.get_field_name_for_version('{}countdown', version_name)
                ] = EventVersionCountdownField(version_name=version_name)
        else:
            self.EXTRA_FIELDS['countdown'] = EventCountdownField

    @property
    def order_settings(self):
        if self.collection.with_versions:
            return {
                # Insert title and countdown before first field per version
                'insert_before': {
                    fields_per_version[0]: [
                        version_name,
                        self.model.get_field_name_for_version('{}countdown', version_name),
                    ] for version_name, fields_per_version in self.model.ALL_FIELDS_BY_VERSION.items()
                },
            }
        else:
            # Insert countdown before start_date
            return {
                'insert_before': {
                    'start_date': [ 'countdown' ],
                },
            }
