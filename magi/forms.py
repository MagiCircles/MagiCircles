import re, datetime, pytz
from collections import OrderedDict
from copy import deepcopy
from dateutil.relativedelta import relativedelta
from multiupload.fields import MultiFileField
from snowpenguin.django.recaptcha3.widgets import ReCaptchaHiddenInput as _ReCaptchaHiddenInput
from snowpenguin.django.recaptcha3.fields import ReCaptchaField as _ReCaptchaField
from django import forms
from django.core.validators import MaxLengthValidator, MaxValueValidator
from django.http.request import QueryDict
from django.db import models as django_models
from django.db.models.fields import BLANK_CHOICE_DASH, FieldDoesNotExist, TextField, CharField, DateTimeField
from django.db.models.fields.files import ImageField
from django.db.models import Q
from django.forms.models import model_to_dict, fields_for_model
from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login as login_action
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.utils import NestedObjects
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, string_concat, get_language, activate as translation_activate
from django.utils.safestring import mark_safe
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.core.validators import MinValueValidator, MinLengthValidator
from django.shortcuts import get_object_or_404
from magi.middleware.httpredirect import HttpRedirectException
from magi.django_translated import t
from magi.raw import (
    GET_PARAMETERS_NOT_IN_FORM,
    GET_PARAMETERS_IN_FORM_HANDLED_OUTSIDE,
)
from magi import models
from magi.default_settings import RAW_CONTEXT
from magi.settings import (
    USER_COLORS,
    GAME_NAME,
    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT,
    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES,
    ON_PREFERENCES_EDITED,
    PROFILE_TABS,
    MINIMUM_LIKES_POPULAR,
    HOME_ACTIVITY_TABS,
    LANGUAGES_CANT_SPEAK_ENGLISH,
    MAX_LEVEL_BEFORE_SCREENSHOT_REQUIRED,
    MAX_LEVEL_UP_STEP_BEFORE_SCREENSHOT_REQUIRED,
    FIRST_COLLECTION,
    FIRST_COLLECTION_PER_ACCOUNT_TYPE,
    TRANSLATION_HELP_URL,
    PROFILE_BACKGROUNDS_NAMES,
    MAX_LEVEL,
    GOOD_REPUTATION_THRESHOLD,
    HAS_MANY_BACKGROUNDS,
    GLOBAL_OUTSIDE_PERMISSIONS,
)
from magi.utils import (
    addParametersToURL,
    randomString,
    shrinkImageFromData,
    imageThumbnailFromData,
    getMagiCollection,
    getMagiCollectionFromModelName,
    getAccountIdsFromSession,
    hasPermission,
    toHumanReadable,
    usersWithPermission,
    staticImageURL,
    markdownHelpText,
    LANGUAGES_DICT,
    LANGUAGES_NAMES,
    LANGUAGES_NAMES_TO_CODES,
    getSearchFieldHelpText,
    tourldash,
    jsv,
    CuteFormType,
    FilterByMode,
    filterByTranslatedValue,
    FormShowMore,
    hasCharacters,
    getCharacterLabel,
    getCharactersFavoriteFields,
    getCharactersFavoriteFilter,
    getCharactersChoices,
    getCharactersFavoriteCuteForm,
    getCharactersTotalFavoritable,
    getCharactersFavoriteFieldLabel,
    getCharactersHasMany,
    listUnique,
    modelHasField,
    changeFormField,
    formFieldFromOtherField,
    markSafe,
    markSafeFormat,
    markSafeJoin,
    localizeTimeOnly,
    getIndex,
    newOrder,
    setSubField,
    CuteFormTransform,
    filterEventsByStatus,
    TimeValidator,
    failSafe,
    HTMLAlert,
    getEnglish,
    toNullBool,
    getVerboseLanguage,
    formUniquenessCheck,
    addButtonsToSubCollection,
    CSVChoiceField,
    modelGetField,
    notTranslatedWarning,
    getAllModelRelatedFields,
    hasValue,
    reverseOrderingString,
    ordinalNumber,
    markSafeReplace,
    markSafeStrip,
    YouTubeVideoField,
    getTranslatedName,
    isCharacterModelClass,
)
from magi.magidisplay import MagiDisplay, _MagiDisplayMultiple, MagiDisplayLink
from versions_utils import sortByRelevantVersions

forms.Form.form_title = None
forms.Form.form_image = None
forms.Form.form_icon = None
forms.Form.error_css_class = ''

############################################################
# Internal utils

class MultiImageField(MultiFileField, forms.ImageField):
    pass

class DateInput(forms.DateInput):
    input_type = 'date'

def date_input(field, value=None):
    field = formFieldFromOtherField(field, forms.DateField)
    field.widget = DateInput()
    field.widget.attrs.update({
        'class': 'calendar-widget',
        'data-role': 'data',
    })
    if not any([isinstance(validator, MinValueValidator) for validator in field.validators]):
        field.validators += [
            MinValueValidator(datetime.date(1900, 1, 2)),
        ]
    field.help_text = markSafeFormat(
        u'{}<span class="format-help">{}yyyy-mm-dd</span>',
        field.help_text or '',
        mark_safe(u'<br>') if field.help_text else '',
    )
    field.input_formats = [
        '%Y-%m-%d'
    ]
    if value and isinstance(value, datetime.date):
        value = value.strftime(field.input_formats[0])
    return field, value

def has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False

def get_total_translations(queryset, field_name, limit_sources_to=[], exclude_sources=[]):
    # Filter fields that have a value in the source language(s)
    condition = Q()
    for language in queryset.model.get_field_translation_sources(field_name):
        if language not in (limit_sources_to or []):
            continue
        if language in exclude_sources:
            continue
        if language == 'en':
            condition |= Q(Q(**{ u'{}__isnull'.format(field_name): False }) & ~Q(**{ field_name: '' }))
        else:
            long_source_field_name = u'{}_{}'.format(LANGUAGES_NAMES.get(language, None), field_name)
            short_source_field_name = u'{}_{}'.format(language, field_name)
            if has_field(queryset.model, long_source_field_name):
                condition |= Q(Q(**{ u'{}__isnull'.format(long_source_field_name): False }) & ~Q(**{ long_source_field_name: '' }))
            elif has_field(queryset.model, short_source_field_name):
                condition |= Q(Q(**{ u'{}__isnull'.format(short_source_field_name): False }) & ~Q(**{ short_source_field_name: '' }))
            else: # dict
                condition |= Q(**{
                    u'd_{}s__contains'.format(field_name): u'"{}"'.format(language)
                })
    queryset = queryset.filter(condition)
    return queryset

def get_missing_translations(queryset, field_name, destination_languages, limit_sources_to=[]):
    # Filter fields that have a value in the source language(s)
    queryset = get_total_translations(
        queryset, field_name, limit_sources_to=limit_sources_to,
        exclude_sources=destination_languages,
    )
    # Filter fields that don't have a value in the destionation languages
    for language in destination_languages:
        if language == 'en':
            queryset = queryset.filter(
                Q(**{ u'{}__isnull'.format(field_name): True })
                | Q(** { field_name: '' })
            )
        else:
            long_source_field_name = u'{}_{}'.format(LANGUAGES_NAMES.get(language, None), field_name)
            short_source_field_name = u'{}_{}'.format(language, field_name)
            if has_field(queryset.model, long_source_field_name):
                queryset = queryset.filter(
                    Q(**{ u'{}__isnull'.format(long_source_field_name): True })
                    | Q(** { long_source_field_name: '' })
                )
            elif has_field(queryset.model, short_source_field_name):
                queryset = queryset.filter(
                    Q(**{ u'{}__isnull'.format(short_source_field_name): True })
                    | Q(** { short_source_field_name: '' })
                )
            else: # dict
                queryset = queryset.exclude(**{
                    u'd_{}s__contains'.format(field_name): u'"{}"'.format(language) })
    return queryset

CAPTCHA_CREDITS = u"""
<div class="row"><div class="col-sm-8 col-sm-offset-4"><p class="text-muted fontx0-8">
  This site is protected by reCAPTCHA and the Google
  <a href="https://policies.google.com/privacy">Privacy Policy</a> and
  <a href="https://policies.google.com/terms">Terms of Service</a> apply.
</p></div></div>
"""

class ReCaptchaHiddenInput(_ReCaptchaHiddenInput):
    def render(self, *args, **kwargs):
        return mark_safe('<input type="hidden" class="django-recaptcha-hidden-field" name="g-recaptcha-response">')

class ReCaptchaField(_ReCaptchaField):
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = ReCaptchaHiddenInput()
        super(ReCaptchaField, self).__init__(*args, **kwargs)

def _to_cuteform_for_auto_images(model, field_name, original_field_name):
    return lambda k, v: model.get_auto_image(
        field_name, failSafe(lambda: model.get_reverse_i(field_name, k), exceptions=[ ValueError ]),
        original_field_name=original_field_name,
    )

def groupSettingsFields(form, group_name, edited_preferences=None):
    new_fields = []
    group = models.UserPreferences.GROUPS[group_name]
    for setting in group.get('settings', []):
        if isinstance(group['settings'], dict):
            setting_details = group['settings'][setting]
        else:
            setting_details = {}
        field_name = u'group_settings_{}_{}'.format(group_name, setting)
        setting_label = toHumanReadable(setting, warning=False)
        label = markSafeFormat(
            u'<small><img height="20" alt="{name}" src="{img}"> {name}</small><br><b>{setting}</b>',
            name=group['translation'], setting=setting_label,
            img=staticImageURL(group_name, folder='groups', extension='png'),
        )
        initial = None
        if edited_preferences:
            initial = (getattr(edited_preferences, 'settings_per_groups', None) or {}).get(
                group_name, {}).get(setting, None)
        to_field = setting_details.get('to_form_field', None)
        if to_field:
            form.fields[field_name] = to_field()
            form.fields[field_name].initial = initial
        else:
            form.fields[field_name] = forms.CharField(required=False, label=label, initial=initial)
        form.fields[field_name].placeholder = setting_label
        new_fields.append(field_name)
    return new_fields

def saveGroupsSettingsFields(form, edited_preferences):
    j = {}
    for group_name, group in models.UserPreferences.GROUPS.items():
        for setting in group.get('settings', []):
            field_name = u'group_settings_{}_{}'.format(group_name, setting)
            cleaned_data = form.cleaned_data.get(field_name, None)
            if group_name not in j:
                j[group_name] = {}
            j[group_name][setting] = cleaned_data
    edited_preferences.save_j('settings_per_groups', j)

############################################################
# HiddenModelChoiceField is a form field type that will not retrieve
# the list of choices but will validate if the foreign key
# is valid when saved.

class HiddenModelChoiceField(forms.IntegerField):
    widget = forms.HiddenInput

    def __init__(self, queryset=None, to_field_name='pk',
                 *args, **kwargs):
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.values = {}
        super(HiddenModelChoiceField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.values:
            return self.values[value]
        if value in self.empty_values:
            return None
        try:
            key = self.to_field_name
            self.values[value] = self.queryset.get(**{key: value})
        except (ValueError, self.queryset.model.DoesNotExist):
            raise forms.ValidationError(
                t['Select a valid choice. %(value)s is not one of the available choices.'],
                params={ 'value': value }, code='invalid_choice',
            )
        return self.values[value]

############################################################
# Recommended form for any MagiCollection item
# - Will make fields in `optional_fields` optional, regardless of db field
# - Will make fields in `hidden_foreign_keys` hidden and not do an extra query to get choices
# - Will show the correct date picker for date fields
# - Will replace any empty string with None for better database consistency
# - Will use tinypng to optimize images specified in tinypng_on_save and will use settings specified in models
# - When `save_owner_on_creation` is True in Meta form object, will save the field `owner` using the current user

class MagiForm(forms.ModelForm):
    form_title = None
    form_image = None
    form_icon = None
    error_css_class = ''
    order_settings = {}

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.collection = kwargs.pop('collection', None)
        self.form_type = kwargs.pop('type', None)
        self.ajax = kwargs.pop('ajax', False)
        self.allow_next = kwargs.pop('allow_next', False)
        super(MagiForm, self).__init__(*args, **kwargs)
        self.is_creating = not hasattr(self, 'instance') or not self.instance.pk
        self.view = ((self.collection.add_view if self.is_creating else self.collection.edit_view)
                     if self.collection else None)
        self.c_choices = []
        self.d_choices = {}
        self.userimages_fields = []
        self.date_fields = []
        self.date_previous_values = {}
        self.m_previous_values = {}
        self.keep_underscore_fields = []
        self.force_tinypng_on_save = []
        self.generate_thumbnails_for = []
        self.extra_fields_added = { None: [] } # None = not attached to any other field
        self.cuteform = getattr(self, 'cuteform', {})
        if self.order_settings:
            order_to_change = deepcopy(self.order_settings)
        else:
            order_to_change = {}
        delete_after_ordering = []

        # If is creating and item is unique per owner, redirect to edit unique
        if self.request and self.is_creating and self.collection and not isinstance(self, MagiFiltersForm) and not self.Meta.model.fk_as_owner and self.collection.add_view.unique_per_owner:
            existing = self.collection.edit_view.get_queryset(self.collection.queryset, {}, self.request).filter(**self.collection.edit_view.get_item(self.request, 'unique'))
            try: raise HttpRedirectException(existing[0].ajax_edit_url if self.ajax else existing[0].edit_url) # Redirect to edit
            except IndexError: pass # Can add!

        # Hidden foreign keys fields
        if hasattr(self.Meta, 'hidden_foreign_keys'):
            for field in self.Meta.hidden_foreign_keys:
                if field in self.fields:
                    changeFormField(self, field, HiddenModelChoiceField, {
                        'queryset': self.fields[field].queryset,
                        'widget': forms.HiddenInput,
                        'initial': (None if self.is_creating else getattr(self.instance, u'{}_id'.format(field))),
                    })
        # Fix optional fields
        if hasattr(self.Meta, 'optional_fields'):
            for field in self.Meta.optional_fields:
                if field in self.fields:
                    self.fields[field].required = False

        allow_initial_in_get = getattr(self.Meta, 'allow_initial_in_get', [])
        self.allow_upload_custom_thumbnail = False
        self.allow_upload_custom_2x = False
        self.allow_translate = False
        if (self.request
            and self.request.user.is_authenticated()):
            self.allow_upload_custom_thumbnail = self.request.user.hasPermission('upload_custom_thumbnails')
            self.allow_upload_custom_2x = self.request.user.hasPermission('upload_custom_2x')
            self.allow_translate = self.request.user.hasPermission('translate_items')

        fields_to_keep = []
        # When next is allowed, add next fields
        if self.request and self.allow_next:
            fields_to_keep += ['next', 'next_title']
        # Keep get_started
        if self.request and 'get_started' in self.request.GET:
            fields_to_keep += ['get_started']
        for field_name in fields_to_keep:
            if field_name not in self.fields:
                self.fields[field_name] = forms.CharField(
                    required=False, widget=forms.HiddenInput,
                    initial=self.request.GET.get(field_name, None),
                )
                self.extra_fields_added[None].append(field_name)
            if not getattr(self, u'{}_filter'.format(field_name), None):
                setattr(self, u'{}_filter'.format(field_name), MagiFilter(noop=True))

        for name, field in self.fields.items():
            # Fix optional fields using null=True
            try:
                model_field = self.Meta.model._meta.get_field(name)
            except FieldDoesNotExist:
                model_field = None
            if model_field is not None and model_field.null:
                self.fields[name].required = False

            # For ModelChoiceField, make sure .get_queryset is called
            if (isinstance(field, forms.ModelChoiceField)
                and field.queryset is not None):
                modelchoicefield_collection = getMagiCollection(
                    getattr(field.queryset.model, 'collection_name', None))
                if modelchoicefield_collection:
                    field.queryset = modelchoicefield_collection.get_queryset().distinct()
                    limit_choices_to = field.get_limit_choices_to()
                    if limit_choices_to is not None:
                        field.queryset = field.queryset.complex_filter(limit_choices_to)

            # Set initial value from GET
            if self.request and (allow_initial_in_get == '__all__' or name in allow_initial_in_get):
                value = self.request.GET.get(name, None)
                if value:
                    try:
                        field.show_value_instead = (
                            { unicode(k): v for k, v in dict(field.choices).items() }[unicode(value)]
                            if isinstance(field, forms.ChoiceField)
                            else value
                        )
                        field.initial = value
                        field.widget = field.hidden_widget()
                    except KeyError: # Invalid value specified in GET
                        pass

            # Show languages on translatable fields
            if self.collection and self.collection.translated_fields and name in self.collection.translated_fields:
                choices = self.Meta.model.get_field_translation_languages(name, as_choices=True)
                self.fields[name].below_field = mark_safe(
                    u'<div class="text-right"><i class="flaticon-translate text-muted"></i> {}</div>'.format(
                        u' '.join([
                            (u'{content}'
                             if (getattr(self, 'is_translate_form', False)
                                 or not self.request
                                 or not self.request.user.is_authenticated()
                                 or not self.request.user.hasPermission('translate_items'))
                             else u'<a href="{url}" target="_blank">{content}</a>').format(
                                content=u'<img src="{image}" alt="{language}" height="15">'.format(
                                    language=language,
                                    image=staticImageURL(language, folder='language', extension='png'),
                                ),
                                url=(self.collection.get_list_url(parameters={
                                    'missing_{}_translations'.format(name): language,
                                }) if self.is_creating
                                     else u'{}{}translate&language={}'.format(
                                             self.instance.edit_url,
                                             '&' if '?' in self.instance.edit_url else '?',
                                             language,
                                     )
                                ) if self.allow_translate else TRANSLATION_HELP_URL,
                            ) for language, language_verbose in choices
                        ]),
                    ))
            # Fix dates fields
            if (not name.startswith('_cache_')
                and (isinstance(field, forms.DateField)
                     or isinstance(field, forms.DateTimeField)
                     or name in getattr(self.Meta, 'date_fields', []))):
                self.date_fields.append(name)
                original_value_with_time = getattr(self.instance, name)
                # Save previous date: allows to keep the time on saving
                if not self.is_creating:
                    self.date_previous_values[name] = original_value_with_time
                # Change field to date input
                self.fields[name], value = date_input(field, value=(
                    getattr(self.instance, name, None) if not self.is_creating else None))
                # Set value in instance as date only, string, to be valid in date widget
                if value:
                    setattr(self.instance, name, value)
                # Add time + timezone fields if needed
                if name in getattr(self.Meta, 'date_fields_with_time', {}):
                    current_timezone = (
                        # From timezone model field, when editing
                        (getattr(self.instance, u'_{}_timezone'.format(name), None)
                         if not self.is_creating else None)
                        # From timezone model field default value, when adding
                        or (failSafe(lambda: self.Meta.model._meta.get_field(
                            '_{}_timezone'.format(name)).default, exceptions=[FieldDoesNotExist])
                            if self.is_creating else None)
                        # From form default_timezone
                        or self.Meta.date_fields_with_time[name].get('default_timezone', None)
                        # From default displayed timezone
                        or getIndex(getattr(self.Meta.model, u'{}_DEFAULT_TIMEZONES'.format(name.upper()), []) or [], 0)
                    )
                    # Change displayed date and time from UTC to selected timezone
                    initial_time = None
                    if not self.is_creating:
                        if original_value_with_time:
                            if current_timezone:
                                value_with_timezone = original_value_with_time.astimezone(pytz.timezone(current_timezone))
                                setattr(self.instance, name, value_with_timezone.strftime('%Y-%m-%d'))
                                initial_time = value_with_timezone.strftime('%H:%M:%S')
                            else:
                                initial_time = original_value_with_time.strftime('%H:%M:%S')
                    if not initial_time:
                        times = getattr(self.Meta, 'date_times', {})
                        if times and times.get(name, None):
                            initial_time = u'{:02d}:{:02d}:00'.format(times[name][0], times[name][1])
                    if not initial_time:
                        initial_time = '00:00:00'
                    # Add time field
                    if self.Meta.date_fields_with_time[name].get('manual_time', False):
                        # Manual time field
                        self.fields[u'{}_time'.format(name)] = forms.CharField(
                            label='',
                            required=field.required,
                            initial=initial_time,
                            help_text='HH:MM:SS',
                            validators=[TimeValidator],
                        )
                        self.fields[u'{}_time'.format(name)].placeholder = 'HH:MM:SS'
                        if name not in self.extra_fields_added:
                            self.extra_fields_added[name] = []
                        self.extra_fields_added[name].append(u'{}_time'.format(name))
                    else:
                        # Choice time field
                        choices = [
                            u'{:02d}:{:02d}:00'.format(hour, minute)
                            for hour in range(0, 24)
                            for minute in range(0, 60, self.Meta.date_fields_with_time[name].get(
                                    'minutes_interval', 60))
                        ]
                        self.fields[u'{}_time'.format(name)] = forms.ChoiceField(
                            label='',
                            required=field.required,
                            choices=[(v, localizeTimeOnly(v)) for v in choices] + (
                                [(initial_time, localizeTimeOnly(initial_time))]
                                if initial_time not in choices else []
                            ),
                            initial=initial_time,
                            validators=[TimeValidator],
                        )
                        if name not in self.extra_fields_added:
                            self.extra_fields_added[name] = []
                        self.extra_fields_added[name].append(u'{}_time'.format(name))
                    # Timezone field
                    self.fields[u'{}_timezone'.format(name)] = forms.ChoiceField(
                        label='',
                        required=field.required,
                        choices=[ (v, v) for v in pytz.all_timezones ],
                        initial=current_timezone or 'UTC',
                    )
                    if name not in self.extra_fields_added:
                        self.extra_fields_added[name] = []
                    self.extra_fields_added[name].append(u'{}_timezone'.format(name))
                    # When creating:
                    if self.is_creating:
                        # When no default timezone found, auto change to local timezone
                        if not current_timezone:
                            self.fields[u'{}_timezone'.format(name)].widget.attrs.update({
                                'data-auto-change-timezone': True,
                            })
                        # convert_default_to_timezone setting
                        if self.Meta.date_fields_with_time[name].get(
                            'convert_default_to_timezone', False):
                            self.fields[u'{}_time'.format(name)].widget.attrs.update({
                                'data-auto-convert-to-timezone': True,
                            })
                    # When editing:
                    else:
                        # When no timezone specified, convert to local timezone
                        if not current_timezone:
                            self.fields[u'{}_timezone'.format(name)].widget.attrs.update({
                                'data-auto-change-timezone': True,
                            })
                            self.fields[u'{}_time'.format(name)].widget.attrs.update({
                                'data-auto-convert-to-timezone': True,
                            })
                    # Make sure added time/timezone fields show under main date field
                    setSubField(order_to_change, 'insert_after', key=name, value=[
                        u'{}_time'.format(name), u'{}_timezone'.format(name)], force_add=True)
            # Make CSV values with choices use a CheckboxSelectMultiple widget
            elif name.startswith('c_'):
                choices = getattr(self.Meta.model, '{name}_CHOICES'.format(name=name[2:].upper()), None)
                if choices is not None:
                    self.c_choices.append(name)
                    if not choices:
                        self.fields.pop(name)
                    else:
                        auto_images = getattr(self.Meta.model, u'{name}_AUTO_IMAGES'.format(
                            name=name[2:].upper()), False)
                        def _get_choice(c):
                            k, v = (c[0], c[1]) if isinstance(c, tuple) else (c, c)
                            if auto_images:
                                return (k, markSafeFormat(
                                    u'<img src="{url}" alt="{v}" height="30"> {v}',
                                    url=self.Meta.model.get_auto_image(name[2:], k, original_field_name=name),
                                    v=v,
                                ))
                            return (k, v)
                        changeFormField(self, name, CSVChoiceField, {
                            'required': False,
                            'widget': forms.CheckboxSelectMultiple,
                            'choices': [_get_choice(c) for c in choices],
                        })
            # Add fields for d_ dict choices
            elif name.startswith('d_') and not isinstance(self, MagiFiltersForm):
                choices = getattr(self.Meta.model, u'{name}_CHOICES'.format(name=name[2:].upper()), None)
                if choices is not None:
                    if (not self.collection
                        or not self.collection.translated_fields
                        or name[2:-1] not in self.collection.translated_fields
                        or getattr(self, 'is_translate_form', False)):
                        self.d_choices[name[2:]] = []
                        choices_field_names = []
                        for choice in (choices.items() if isinstance(choices, dict) else choices):
                            key = choice[0] if isinstance(choice, tuple) else choice
                            verbose_name = choice[1] if isinstance(choice, tuple) else choice
                            verbose_name = verbose_name() if callable(verbose_name) else verbose_name
                            field_name = u'{}-{}'.format(name, key)
                            self.d_choices[name[2:]].append((field_name, key))
                            choices_field_names.append(field_name)

                            # Widget
                            widget = forms.TextInput
                            try: singular_field = self.Meta.model._meta.get_field(name[2:-1])
                            except FieldDoesNotExist: singular_field = None
                            if singular_field and isinstance(singular_field, TextField):
                                widget = forms.Textarea

                            # Label and help text
                            label = self.fields[name].label
                            if getattr(self.Meta.model, u'{}_CHOICES_KEYS_AS_LABELS'.format(name[2:].upper()), False):
                                help_text = self.fields[name].help_text
                                label = verbose_name
                            else:
                                if self.fields[name].help_text:
                                    help_text = markSafeFormat(
                                        u'{original}<br>{key}',
                                        original=self.fields[name].help_text,
                                        key=verbose_name,
                                    )
                                else:
                                    help_text = verbose_name
                            if self.is_creating:
                                initial = None
                            elif name.startswith('d_m_'):
                                initial = getattr(self.instance, name[4:]).get(key, None)
                                if initial:
                                    initial = initial[1]
                            else:
                                initial = getattr(self.instance, name[2:]).get(key, None)
                            self.fields[field_name] = forms.CharField(
                                required=False,
                                label=label,
                                help_text=help_text,
                                initial=initial,
                                widget=widget,
                            )
                            setSubField(order_to_change, 'insert_after', key=name, value=[
                                u'delete_{}'.format(name)], force_add=True)
                        if choices_field_names:
                            setSubField(
                                order_to_change, 'insert_after', force_add=True,
                                key=name, value=choices_field_names,
                            )
                    delete_after_ordering.append(name)
            # Make fields with soft choices use a ChoiceField
            elif getattr(self.Meta.model, u'{name}_SOFT_CHOICES'.format(name=name[2:].upper()), False):
                choices = getattr(self.Meta.model, '{name}_CHOICES'.format(name=name[2:].upper()), None)
                without_i = getattr(self.Meta.model, '{name}_WITHOUT_I_CHOICES'.format(name=name[2:].upper()), None)
                if choices is not None:
                    changeFormField(self, name, forms.ChoiceField, {
                        'choices': (BLANK_CHOICE_DASH if not field.required else []) + [
                            (c[0] if without_i else i, c[1]) if isinstance(c, tuple) else (c, c)
                            for i, c in enumerate(choices)
                        ],
                    })
            # Save previous values of markdown fields and set label
            elif name.startswith('m_') and not isinstance(self, MagiFiltersForm):
                if not self.is_creating:
                    self.m_previous_values[name] = getattr(self.instance, name)
                help_text = getattr(self.fields[name], 'help_text', '')
                markdown_help_text = markdownHelpText(request=self.request, ajax=self.ajax)
                if help_text:
                    self.fields[name].help_text = markSafeFormat(
                        u'{}<br><i class="text-muted fontx0-8">{}</i>',
                        help_text, markdown_help_text,
                    )
                else:
                    self.fields[name].help_text = markdown_help_text

            # Save previous values of reverse related caches
            elif (self.request and self.request.method == 'POST'
                  and not self.is_creating and name in [ r[0] for r in getattr(self.instance, 'REVERSE_RELATED_CACHES', []) ]):
                if not hasattr(self.request, '_reverse_related_caches_previous_values'):
                    self.request._reverse_related_caches_previous_values = {}
                is_m2m = next(r[2] for r in getattr(self.instance, 'REVERSE_RELATED_CACHES', []) if r[0] == name)
                if is_m2m:
                    self.request._reverse_related_caches_previous_values[name] = list(getattr(self.instance, name).all())
                else:
                    self.request._reverse_related_caches_previous_values[name] = getattr(self.instance, name)

            # Images selector
            elif (model_field
                  and isinstance(model_field, django_models.ManyToManyField)
                  and issubclass(model_field.rel.to, models.UserImage)):
                self.userimages_fields.append(name)
                max_images = getattr(self.Meta.model, u'{}_MAX'.format(name.upper()), 10)
                if not self.is_creating:
                    existing_images_choices = [
                        (userimage.id, markSafeFormat(
                            u'<img src="{}" alt="user image" height="30">',
                            userimage.image_thumbnail_url,
                        )) for userimage in getattr(self.instance, name).all()
                    ]
                    if max_images is not None:
                        max_images -= len(existing_images_choices)
                # Change form field to image selector
                changeFormField(self, name, MultiImageField, {
                    'min_num': 0,
                    'max_num': max_images,
                    'help_text': model_field.help_text,
                })
                if max_images <= 0:
                    self.fields[name].widget.attrs.update({
                        'class': 'hidden',
                    })
                # Add field to allow to delete existing images
                if not self.is_creating and existing_images_choices:
                    self.fields[u'delete_{}'.format(name)] = forms.MultipleChoiceField(
                        required=False,
                        widget=forms.CheckboxSelectMultiple,
                        choices=existing_images_choices,
                        label='',
                        help_text=t['Delete'],
                    )
                    setSubField(order_to_change, 'insert_after', key=name, value=[
                        u'delete_{}'.format(name)], force_add=True)
                    if name not in self.extra_fields_added:
                        self.extra_fields_added[name] = []
                    self.extra_fields_added[name].append(u'delete_{}'.format(name))

            elif name.startswith('_'):

                # Thumbnail
                if (not self.is_creating
                    and self.allow_upload_custom_thumbnail
                    and (name.startswith('_tthumbnail_')
                         or name.startswith('_thumbnail_'))):
                    # Check that there is a value
                    original_name = name[(12 if name.startswith('_tthumbnail_') else 11):]
                    original_field = self.fields[original_name]
                    if getattr(self.instance, original_name, None):
                        self.keep_underscore_fields.append(name)
                        # Change label, add class to hide by default
                        self.fields[name].label = mark_safe(u'<span class="text-secondary">[Thumbnail]</span> {}'.format(
                            original_field.label))
                        self.fields[name].placeholder = (
                            getattr(original_field, 'placeholder', None) or original_field.label)
                        self.fields[name].help_text = 'Thumbnails are generated automatically. You don\'t need to upload your own, unless you\'re not happy with the generated one.'
                        self.generate_thumbnails_for.append(name)
                        if name.startswith('_tthumbnail_'):
                            # Ensure image is compressed on save
                            self.force_tinypng_on_save.append(name)

                elif (self.allow_upload_custom_2x
                      and name.startswith('_2x_')):
                    self.keep_underscore_fields.append(name)
                    original_name = name[4:]
                    original_field = self.fields[original_name]
                    self.fields[name].label = mark_safe(u'<span class="text-secondary">[2x]</span> {}'.format(
                        original_field.label))
                    self.fields[name].placeholder = (
                        getattr(original_field, 'placeholder', None) or original_field.label)
                    self.fields[name].help_text = mark_safe(
                        u'High resolution image generated by AI. Recommended: <a href="http://waifu2x.udp.jp/">Waifu2x</a> with settings:<ul><li>Artwork</li><li>Highest</li><li>2x</li></ul>')

            # Auto cuteform for fields with auto images
            if (not isinstance(field, forms.MultipleChoiceField)
                and name.startswith('i_')
                and (getattr(self.Meta.model, '{}_AUTO_IMAGES'.format(name[2:].upper()), False))):
                self.cuteform[name] = {
                    'to_cuteform': _to_cuteform_for_auto_images(self.Meta.model, name[2:], name),
                }

        # Fix force required fields
        if hasattr(self.Meta, 'required_fields'):
            for field in self.Meta.required_fields:
                if field in self.fields:
                    self.fields[field].required = True
        # Hidden fields
        if hasattr(self.Meta, 'hidden_fields'):
            for field in self.Meta.hidden_fields:
                if field in self.fields:
                    self.fields[field].widget = self.fields[field].hidden_widget()

        # Show as required
        if hasattr(self.Meta, 'fields_show_as_required'):
            for field in self.Meta.fields_show_as_required:
                if field in self.fields:
                    self.fields[field].show_as_required = True

        # Has the form been opened in the context of a report or a suggested edit?
        self.is_reported = False
        self.is_suggestededit = False
        if (not self.is_creating
            and not isinstance(self, MagiFiltersForm)
            and self.request
            and self.request.user.is_authenticated()
            and hasattr(type(self.instance), 'owner') and self.instance.owner_id != self.request.user.id):
            self.is_reported = 'is_reported' in self.request.GET
            self.is_suggestededit = 'is_suggestededit' in self.request.GET

        # Add buttons to add/edit sub items
        if (not self.is_reported and not self.is_suggestededit
            and not getattr(self, 'is_translate_form', False)
            and self.collection
            and getattr(self.collection, 'sub_collections', None)
        ):
            self.sub_collections = []
            for sub_collection in getattr(self.collection, 'sub_collections', None).values():
                if sub_collection.main_many2many:
                    if sub_collection.main_related in self.fields:
                        addButtonsToSubCollection(self, sub_collection, sub_collection.main_related)
                elif not self.is_creating:
                    self.sub_collections.append(self.get_sub_collections_details(sub_collection))

        # ReCaptcha credit
        if ('captcha' in self.fields
            and isinstance(self.fields['captcha'], ReCaptchaField)):
            if (getattr(django_settings, 'DEBUG', False)
                and not getattr(django_settings, 'RECAPTCHA_PUBLIC_KEY', None)):
                del(self.fields['captcha'])
            else:
                if not getattr(self, 'afterfields', None):
                    self.afterfields = mark_safe(CAPTCHA_CREDITS)

        # Reorder if needed
        if order_to_change:
            self.reorder_fields(newOrder(self.fields.keys(), **order_to_change))

        # Delete after ordering if needed
        for field_name in delete_after_ordering:
            try: del(self.fields[field_name])
            except KeyError: pass

    def get_sub_collections_details(self, sub_collection):
        return {
            'plural_title': sub_collection.plural_title,
            'add_sentence': sub_collection.add_sentence,
            'add_url': sub_collection.get_add_url(item=self.instance),
            'ajax_add_url': sub_collection.get_add_url(ajax=True, item=self.instance),
            'items': getattr(self.instance, sub_collection.main_related).all(),
            'item_view_enabled': sub_collection.item_view.enabled,
        }

    def clean(self):
        # Check max_per_user
        owner = getattr(self, 'to_owner', self.request.user)
        if (self.is_creating and self.collection
            and not isinstance(self, MagiFiltersForm)
            and self.request and owner.is_authenticated()
            and not owner.hasPermission('bypass_max_per_user')):
            if self.collection.add_view.max_per_user_per_minute:
                already_added = self.Meta.model.objects.filter(**{
                    self.Meta.model.selector_to_owner(): owner,
                    'creation__gte': timezone.now() - relativedelta(minutes=1),
                }).count()
                if already_added >= self.collection.add_view.max_per_user_per_minute:
                    raise forms.ValidationError(
                        unicode(_('You\'ve added a lot of {things}, lately. Try to wait a little bit before adding more.'))
                        .format(things=unicode(self.collection.plural_title).lower()))
            if self.collection.add_view.max_per_user_per_hour:
                already_added = self.Meta.model.objects.filter(**{
                    self.Meta.model.selector_to_owner(): owner,
                    'creation__gte': timezone.now() - relativedelta(hours=1),
                }).count()
                if already_added >= self.collection.add_view.max_per_user_per_hour:
                    raise forms.ValidationError(
                        unicode(_('You\'ve added a lot of {things}, lately. Try to wait a little bit before adding more.'))
                        .format(things=unicode(self.collection.plural_title).lower()))
            if self.collection.add_view.max_per_user_per_day:
                already_added = self.Meta.model.objects.filter(**{
                    self.Meta.model.selector_to_owner(): owner,
                    'creation__gte': timezone.now() - relativedelta(days=1),
                }).count()
                if already_added >= self.collection.add_view.max_per_user_per_day:
                    raise forms.ValidationError(
                        unicode(_('You\'ve added a lot of {things}, lately. Try to wait a little bit before adding more.'))
                        .format(things=unicode(self.collection.plural_title).lower()))
            if self.collection.add_view.max_per_user:
                already_added = self.Meta.model.objects.filter(**{
                    self.Meta.model.selector_to_owner(): owner
                }).count()
                if already_added >= self.collection.add_view.max_per_user:
                    raise forms.ValidationError(unicode(_('You already have {total} {things}. You can only add up to {max} {things}.')).format(
                        total=already_added,
                        max=self.collection.add_view.max_per_user,
                        things=unicode(self.collection.plural_title).lower(),
                    ))
        # Strip all strings
        for field_name, field in self.fields.items():
            if isinstance(field, forms.CharField):
                value = self.cleaned_data.get(field_name, None)
                if value is not None:
                    try:
                        self.cleaned_data[field_name] = value.strip()
                    except AttributeError:
                        pass
        return self.cleaned_data

    def save(self, commit=True):
        instance = super(MagiForm, self).save(commit=False)
        # Save owner on creation when owner field is missing but there is a owner field in model
        if self.is_creating and 'owner' not in self.fields and has_field(self.Meta.model, 'owner'):
            owner = getattr(self, 'to_owner', None)
            if owner:
                instance.owner = owner
            else:
                instance.owner = self.request.user if self.request.user.is_authenticated() else None

        # Clean datetime times
        times = getattr(self.Meta, 'date_times', {})
        fields_with_time = getattr(self.Meta, 'date_fields_with_time', {})
        for field_name in self.date_fields:
            if field_name not in self.fields:
                continue
            # Save timezone in database if it has its own field
            if (self.cleaned_data.get(u'{}_timezone'.format(field_name), None)
                and modelHasField(self.Meta.model, u'_{}_timezone'.format(field_name))):
                setattr(
                    instance, u'_{}_timezone'.format(field_name),
                    self.cleaned_data[u'{}_timezone'.format(field_name)],
                )
            # No date value
            if not getattr(instance, field_name, None):
                continue
            model_field = modelGetField(self.Meta.model, field_name)
            # Date with time
            if model_field and isinstance(model_field, DateTimeField):
                current_date_as_string = getattr(instance, field_name).strftime('%Y-%m-%d')
                # From time/timezone field (added by date_fields_with_time): converts to UTC before saving
                if (self.cleaned_data.get(u'{}_timezone'.format(field_name), None)
                    and self.cleaned_data.get(u'{}_time'.format(field_name), None)):
                    timezone = self.cleaned_data[u'{}_timezone'.format(field_name)]
                    formatted_date = u'{}T{}'.format(
                        current_date_as_string,
                        self.cleaned_data[u'{}_time'.format(field_name)],
                    )
                    setattr(
                        instance, field_name,
                        pytz.timezone(timezone).localize(
                            datetime.datetime.strptime(formatted_date, '%Y-%m-%dT%H:%M:%S'),
                        ).astimezone(pytz.UTC),
                    )
                # From date_times in Meta: saves default time when creating or changing date
                elif (field_name in times
                      and (self.is_creating or not self.date_previous_values.get(field_name, None)
                           or current_date_as_string != self.date_previous_values[field_name].strftime('%Y-%m-%d'))):
                    setattr(
                        instance, field_name,
                        getattr(instance, field_name).replace(
                            hour=times[field_name][0], minute=times[field_name][1]))
                # No default time, but the date didn't change: make sure the time doesn't change either
                elif (not self.is_creating
                      and self.date_previous_values.get(field_name, None)
                      and current_date_as_string == self.date_previous_values[field_name].strftime('%Y-%m-%d')):
                    setattr(
                        instance, field_name,
                        getattr(instance, field_name).replace(
                            hour=self.date_previous_values[field_name].hour,
                            minute=self.date_previous_values[field_name].minute,
                            second=self.date_previous_values[field_name].second,
                        ),
                    )
            # Date without time
            else:
                pass

        # Save d_ dict choices
        for dfield, choices in self.d_choices.items():
            d = {}
            choices_keys_not_in_form = []
            known_keys = []
            for field, key in choices:
                known_keys.append(key)
                if field not in self.fields:
                    choices_keys_not_in_form.append(key)
                    continue
                if (self.cleaned_data[field]
                    or key in getattr(self.Meta, 'd_save_falsy_values_for_keys', {}).get(dfield, [])):
                    d[key] = self.cleaned_data[field]

            # Keep unknown keys and keys that are in choices but not in the form
            keep_unknwon_keys = dfield in getattr(self.Meta, 'keep_unknwon_keys_for_d', [])
            if keep_unknwon_keys or choices_keys_not_in_form:
                for key, value in getattr(instance, dfield).items():
                    if key not in known_keys or key in choices_keys_not_in_form:
                        d[key] = value

            instance.save_d(dfield, d)

        for field in self.fields.keys():
            # Fix empty strings to None
            if (hasattr(instance, field)
                and isinstance(self.fields[field], forms.Field)
                and has_field(instance, field)
                and (isinstance(getattr(instance, field), unicode) or isinstance(getattr(instance, field), str))
                and getattr(instance, field).strip() == ''):
                setattr(instance, field, None)
            # Remove cached HTML for markdown fields
            if (field.startswith('m_') and field in self.m_previous_values
                and has_field(instance, field)
                and self.m_previous_values[field] != getattr(instance, field)
                and has_field(instance, u'_cache_{}'.format(field[2:]))):
                setattr(instance, u'_cache_{}'.format(field[2:]), None)
            # Check for files upload then UPLOADED_FILES_URL is set
            if (field in self.cleaned_data
                and (isinstance(self.cleaned_data[field], InMemoryUploadedFile)
                     or isinstance(self.cleaned_data[field], TemporaryUploadedFile))
                and getattr(django_settings, 'DEBUG', False)
                and getattr(django_settings, 'UPLOADED_FILES_URL', None)
                and not getattr(django_settings, 'AWS_STORAGE_BUCKET_NAME', None)):
                raise forms.ValidationError(
                    'Debug mode: UPLOADED_FILES_URL is specified so you can\'t upload files.'
                )

            # Images
            if (hasattr(instance, field)
                and isinstance(self.fields[field], forms.Field)
                and has_field(instance, field)
                and type(self.Meta.model._meta.get_field(field)) == django_models.ImageField):
                image = self.cleaned_data[field]

                # If image has been cleared
                if image is False:
                    # Remove any cached processed image
                    setattr(instance, u'_tthumbnail_{}'.format(field), None)
                    setattr(instance, u'_thumbnail_{}'.format(field), None)
                    setattr(instance, u'_original_{}'.format(field), None)
                    setattr(instance, u'_2x_{}'.format(field), None)

                if image and (isinstance(image, InMemoryUploadedFile) or isinstance(image, TemporaryUploadedFile)):
                    filename = image.name
                    image_data = None

                    # Generate thumbnails from uploaded
                    if field in self.generate_thumbnails_for:
                        if image_data is None:
                            image_data = image.read()
                        thumbnail_size = getattr(instance._meta.model, 'thumbnail_size', {}).get(field, {})
                        image_data, thumbnail_image = imageThumbnailFromData(
                            image_data, filename,
                            width=thumbnail_size.get('width', 200),
                            height=thumbnail_size.get('height', 200),
                            return_data=True,
                        )

                    # Shrink images with TinyPNG
                    if (field in getattr(self.Meta, 'tinypng_on_save', [])
                        or field in self.force_tinypng_on_save):
                        if image_data is None:
                            image_data = image.read()
                        image_data = shrinkImageFromData(
                            image_data, filename,
                            settings=getattr(instance, 'tinypng_settings', {}).get(field, {}),
                        )

                    if image_data is not None:
                        image.name = instance._meta.model._meta.get_field(field).upload_to(instance, filename)
                        setattr(instance, field, image_data)
                    else:
                        # Remove any cached processed image from previously uploaded image
                        setattr(instance, u'_tthumbnail_{}'.format(field), None)
                        setattr(instance, u'_thumbnail_{}'.format(field), None)
                        setattr(instance, u'_original_{}'.format(field), None)
                        setattr(instance, u'_2x_{}'.format(field), None)

        # Images selector
        if self.userimages_fields:
            # Set save m2m (called later)
            super_save_m2m = self.save_m2m
            def _save_m2m(*args, **kwargs):
                for field_name in self.userimages_fields:
                    # Upload new images
                    for image in self.cleaned_data.get(field_name, []):
                        if isinstance(image, int) or isinstance(image, long):
                            imageObject = models.UserImage.objects.get(id=image)
                        else:
                            imageObject = models.UserImage.objects.create(
                                name=u'{}-{}'.format(self.Meta.model.__name__.lower(), field_name),
                            )
                            imageObject.image.save(randomString(64), image)
                        getattr(instance, field_name).add(imageObject)
                    del(self.cleaned_data[field_name])
                    # Delete existing images selected for deletion
                    pks_of_images_to_remove = self.cleaned_data.get(u'delete_{}'.format(field_name))
                    if pks_of_images_to_remove:
                        images_to_remove = list(getattr(instance, field_name).filter(pk__in=pks_of_images_to_remove))
                        images_to_remove_ids = [i.id for i in images_to_remove]
                        getattr(instance, field_name).remove(*images_to_remove)
                        models.UserImage.objects.filter(id__in=images_to_remove_ids).delete()
                super_save_m2m(*args, **kwargs)
            self.save_m2m = _save_m2m

        if commit:
            instance.save()
        return instance

    def _transform_on_change_value(self, values, add_affected_fields=True):
        def _get_i(field_name, value):
            if not isinstance(value, int):
                try: return self.Meta.model.get_i(field_name[2:], value)
                except (FieldDoesNotExist, KeyError): pass
            return value
        on_change_value = OrderedDict()
        for field_name, fields in values.items():
            # For c_ fields, specify all choices as their own fields (seperate checkboxes)
            # Example (with dict):
            # 'c_tags': { 'news': ['is_event_news'] },
            # => 'c_tags-news': ['is_event_news'],
            # Example (with list):
            # 'c_tags': ['staff_favorite'],
            # => 'c_tags_0': ['staff_favorite'], 'c_tags_2': ['staff_favorite'], ...
            if field_name.startswith('c_') and field_name in self.fields:
                for i, (choice, _v_choice) in enumerate(self.fields[field_name].choices):
                    if isinstance(fields, dict):
                        if choice in fields:
                            on_change_value[u'{}_{}'.format(field_name, i)] = fields[choice]
                    else:
                        on_change_value[u'{}_{}'.format(field_name, i)] = fields
            # For i_ fields, change to integer values if need be
            # Example:
            # 'i_rarity': { 'ur': ['special'] },
            # => 'i_rarity': { 2: ['special'] },
            elif field_name.startswith('i_') and isinstance(fields, dict):
                on_change_value[field_name] = {
                    _get_i(field_name, value): value_fields
                    for value, value_fields in fields.items()
                }
            else:
                on_change_value[field_name] = fields

        # Add extra added sub fields to fields to show/hide
        if add_affected_fields:
            for field_name, fields in on_change_value.items():
                if isinstance(fields, dict):
                    # Example (with dict):
                    # 'available_in_jp': { True: ['jp_start_date'] },
                    # => 'available_in_jp': { True: ['jp_start_date', 'jp_start_date_time', ...] },
                    for value, sub_fields in fields.items():
                        to_add = []
                        for sub_field_name in sub_fields:
                            if sub_field_name in self.extra_fields_added:
                                to_add += self.extra_fields_added[sub_field_name]
                        if to_add:
                            # create a new list, don't update existing one in case it's used elsewhere
                            on_change_value[field_name][value] = (
                                on_change_value[field_name][value]
                                + to_add
                            )
                else:
                    # Example (with list):
                    # 'available_in_jp': ['jp_start_date'],
                    # => 'available_in_jp': ['jp_start_date', 'jp_start_date_time', ...],
                    to_add = []
                    for sub_field_name in fields:
                        if sub_field_name in self.extra_fields_added:
                            to_add += self.extra_fields_added[sub_field_name]
                    if to_add:
                        # create a new list, don't update existing one in case it's used elsewhere
                        on_change_value[field_name] = (
                            on_change_value[field_name]
                            + to_add
                        )

        return on_change_value

    def get_on_change_value_show(self):
        on_change_value_show = getattr(self, 'on_change_value_show', None)
        if not on_change_value_show:
            return None
        return self._transform_on_change_value(on_change_value_show)

    def get_on_change_value_trigger(self):
        on_change_value_trigger = getattr(self, 'on_change_value_trigger', None)
        if not on_change_value_trigger:
            return None
        return self._transform_on_change_value(on_change_value_trigger, add_affected_fields=False)

    def reorder_fields(self, order=[], insert_after=None, insert_before=None, insert_instead=None,
                       insert_at=None, insert_at_instead=None, insert_at_from_last=None, insert_at_from_last_instead=None):
        """
        Reorder form fields by order.
        Fields not in order will be placed at the end.

        >>> reorder_fields(
        ...     OrderedDict([('a', 1), ('b', 2), ('c', 3)]),
        ...     ['b', 'c', 'a'])
        OrderedDict([('b', 2), ('c', 3), ('a', 1)])
        """
        sorted_keys = newOrder(
            listUnique(order + self.fields.keys()),
            insert_after=insert_after, insert_before=insert_before,
            insert_instead=insert_instead, insert_at=insert_at, insert_at_instead=insert_at_instead,
            insert_at_from_last=insert_at_from_last, insert_at_from_last_instead=insert_at_from_last_instead,
        )
        self.fields = OrderedDict(sorted(
            self.fields.items(),
            key=lambda k: sorted_keys.index(k[0]) if k[0] in sorted_keys else 99999,
        ))

    class Meta:
        pass

############################################################
# AutoForm will guess which fields to use in a model

class AutoForm(MagiForm):
    """
    This form can be used to include all the fields but ignore the _cache data or anything that starts with '_'
    with the exception of _ fields related to images, when the user has permissions
    """
    def __init__(self, *args, **kwargs):
        super(AutoForm, self).__init__(*args, **kwargs)

        if 'owner' in self.fields:
            del(self.fields['owner'])

        for field_name in self.fields.keys():
            if field_name.startswith('_') and field_name not in self.keep_underscore_fields:
                del(self.fields[field_name])
            if field_name in getattr(self.Meta, 'exclude_fields', []):
                del(self.fields[field_name])

    class Meta(MagiForm.Meta):
        fields = '__all__'

############################################################
# Translate form

def to_translate_form_class(view):
    if not view.collection.translated_fields:
        return None

    class _TranslateForm(MagiForm):

        def _language_to_field_name(self, field_name, language):
            if language == 'en':
                return field_name
            else:
                long_source_field_name = u'{}_{}'.format(LANGUAGES_NAMES.get(language, None), field_name)
                short_source_field_name = u'{}_{}'.format(language, field_name)
                if has_field(self.Meta.model, long_source_field_name):
                    return long_source_field_name
                elif has_field(self.Meta.model, short_source_field_name):
                    return short_source_field_name
                else: # dict
                    return u'd_{}s-{}'.format(field_name, language)

        def _language_help_text(self, language, verbose_language, field_name, sources):
            formatted_sources = [
                markSafeFormat(
                    u"""<span class="label label-info">{language_verbose}</span>
                    <span lang="{language}" style="white-space: pre-line;">{value}</span>""",
                    language=source_language,
                    language_verbose=getVerboseLanguage(source_language),
                    value=(
                        markSafeFormat(u'<pre style="white-space: pre-line;">{}</pre>', value)
                        if field_name.startswith('d_m_')
                        else value
                    ),
                ) for source_language, value in sources.items()
                if value and language != source_language
            ]
            original_help_text = markSafeStrip(markSafeReplace(
                self.fields[field_name].help_text, unicode(verbose_language), ''))
            self.fields[field_name].help_text = markSafeFormat(
                u'{is_source}{no_value}{original}{sources}<img src="{img}" height="20" /> {lang}',
                is_source=(
                    markSafe(u'<span class="label label-info pull-right">Source</span>')
                    if language in sources else ''
                ),
                no_value=(
                    markSafe(u'<span class="label label-danger pull-right">No value</span>')
                    if not formatted_sources and language not in sources else ''
                ),
                original=(
                    markSafeFormat(u'{}<br>', original_help_text)
                    if original_help_text
                    else ''
                ),
                img=staticImageURL(language, folder='language', extension='png'),
                lang=verbose_language,
                sources=(
                    markSafeFormat(
                        u'<div class="alert alert-info">{}</div>',
                        markSafeJoin(formatted_sources, separator=u'<br>')
                    ) if formatted_sources else ''
                ),
            )
            self.fields[field_name].widget.attrs['data-language'] = language

        def __init__(self, *args, **kwargs):
            self.is_translate_form = True
            super(_TranslateForm, self).__init__(*args, **kwargs)

            # Get spoken languages or languages specified in GET
            spoken_languages = (
                self.request.GET['language'].split(',')
                if self.request.GET.get('language', None)
                else (self.request.user.preferences.settings_per_groups or {}).get(
                        'translator', {}).get('languages', [])
            )

            for field_name in self.collection.translated_fields:
                # Get source values
                source_languages = self.Meta.model.get_field_translation_sources(field_name)
                sources = OrderedDict([
                    (language, self.instance.get_translation_from_dict(
                        field_name, language=language, fallback_to_english=False,
                        fallback_to_other_sources=False) or None)
                    for language in source_languages
                ])
                model_field = modelGetField(self.Meta.model, field_name)
                # Add validators from original field
                validators = getattr(self.collection, 'form_details', {}).get(
                    field_name, {}).get('validators', []) + getattr(model_field, 'validators', [])

                # Add a language help text on top of each field
                # with the list of sources + "Source" + "No value"
                self._language_help_text('en', t['English'], field_name, sources)
                for language, verbose_language in getattr(self.Meta.model, u'{name}S_CHOICES'.format(
                        name=field_name.upper()), []):
                    destination_field_name = u'd_{}s-{}'.format(field_name, language)
                    if destination_field_name in self.fields:
                        self._language_help_text(language, verbose_language, destination_field_name, sources)
                        self.fields[destination_field_name].validators += validators
                for language, fields in self.Meta.external_translation_fields.items():
                    if field_name in fields:
                        verbose_language = getVerboseLanguage(language)
                        self._language_help_text(language, verbose_language, fields[field_name], sources)
                        self.fields[fields[field_name]].validators += validators

                # Add English to spoken languages if needed
                if 'en' not in spoken_languages and set(source_languages).intersection(set(spoken_languages)):
                    spoken_languages.append('en')

            # Add Javascript buttons to show/hide languages
            self.beforefields = mark_safe(u'<div class="text-right languages-buttons" data-spoken-languages="{spoken_languages}" style="display: none"><a href="#translations_see_all" class="btn btn-main btn-sm">See all languages</a><br>{languages}</div><br>'.format(
                spoken_languages=u','.join(spoken_languages),
                languages=u' '.join([
                    u'<a href="#translations_see_language" data-language="{language}"><img src="{image}" width="20" alt="{vlanguage}"></a>'.format(
                        language=language,
                        vlanguage=verbose_language,
                        image=staticImageURL(language, folder='language', extension='png'),
                    ) for language, verbose_language in LANGUAGES_DICT.items()
                ]),
            ))

        class Meta(MagiForm.Meta):
            model = view.collection.queryset.model
            external_translation_fields = {}
            fields = []
            for translated_field in (view.collection.translated_fields or []):
                fields.append(translated_field)
                field_name = u'd_{}s'.format(translated_field)
                if has_field(model, field_name):
                    fields.append(field_name)
                    for language, language_name in LANGUAGES_NAMES.items():
                        for translated_field_name in [
                                u'{}_{}'.format(language_name, translated_field),
                                u'{}_{}'.format(language, translated_field),
                        ]:
                            if has_field(model, translated_field_name):
                                if language not in external_translation_fields:
                                    external_translation_fields[language] = {}
                                external_translation_fields[language][translated_field] = translated_field_name
                                fields.append(translated_field_name)
    return _TranslateForm

class TranslationCheckForm(forms.Form):
    form_title = 'POEditor translations term checker'
    submit_title = 'Check translations'

    term = forms.CharField(required=True)

############################################################
# MagiFiltersForm

class MagiFilter(object):
    """
    to_queryset: lambda that takes form, queryset, request, value and returns a queryset.
                 Optional, will filter automatically.
                 selector and to_value are ignored when specified.
    selector: will be the name of the field by default. example: owner__username.
    selectors: same as selector but works with multiple values.
    operator_for_multiple_selectors: how to filter when multiple selectors are provided.
    to_value: lambda that takes the value and transforms the value if needed.
    distinct: if your selector uses a many to many nested lookup, it's recommended to set
              distinct to true to avoid duplicates
    multiple: allow multiple values separated by commas. Set to False if your value may contain commas.
              defaults to False when to_queryset is provided
    operator_for_multiple: how to filter when multiple values are given separated with commas.
    noop: when set to true, will not affect result
    """
    def __init__(self,
                 to_queryset=None,
                 selector=None,
                 selectors=None,
                 to_value=None,
                 distinct=False,
                 multiple=None,
                 operator_for_multiple=None,
                 operator_for_multiple_selectors=None,
                 allow_csv=True,
                 noop=False,
    ):
        self.to_queryset = to_queryset
        self.selectors = selectors
        if not self.selectors and selector:
            self.selectors = [selector]
        self.to_value = to_value
        self.distinct = distinct
        if multiple is not None:
            self.multiple = multiple
        elif to_queryset:
            self.multiple = False
        else:
            self.multiple = True
        self.operator_for_multiple = operator_for_multiple
        self.operator_for_multiple_selectors = operator_for_multiple_selectors
        self.allow_csv = allow_csv
        self.noop = noop

class MagiFilterOperator:
    OrContains, OrExact, And = range(3)

    _default_per_field_type = {
        forms.fields.MultipleChoiceField: OrContains,
    }
    _default = OrExact

    @staticmethod
    def default_for_field(field):
        return MagiFilterOperator._default_per_field_type.get(type(field), MagiFilterOperator._default)

class MagiFilterOperatorSelector:
    Or, And = range(2)
    default = Or

def filter_ids(queryset, ids):
    if not ids:
        return queryset
    if ids.replace(',', '').isdigit():
        queryset = queryset.filter(pk__in=ids.split(','))
    return queryset

class MagiFiltersForm(AutoForm):
    cache_choices = []
    search = forms.CharField(required=False, label=t['Search'])

    def _search_to_queryset(self, queryset, request, value):
        terms = value.split(' ')
        for term in terms:
            condition = Q()
            for field_name in getattr(self, 'search_fields', []):
                # Translated fields
                if field_name.startswith('d_') and field_name[2:-1] in (
                        getattr(self, 'search_fields', []) + getattr(self, 'search_fields_exact', [])):
                    condition |= filterByTranslatedValue(
                        queryset, field_name[2:-1], value=term,
                        mode=FilterByMode.Contains, case_insensitive=True,
                        as_condition=True,
                        include_english=False,
                    )
                else:
                    condition |= Q(**{ '{}__icontains'.format(field_name): term })
            for field_name in getattr(self, 'search_fields_exact', []):
                # Translated fields
                if field_name.startswith('d_') and field_name[2:-1] in (
                        getattr(self, 'search_fields', []) + getattr(self, 'search_fields_exact', [])):
                    condition |= filterByTranslatedValue(
                        queryset, field_name[2:-1], value=term,
                        mode=FilterByMode.Exact, case_insensitive=True,
                        as_condition=True,
                        include_english=False,
                    )
                else:
                    condition |= Q(**{ '{}__iexact'.format(field_name): term })
            queryset = queryset.filter(condition)
        if self.search_filter.distinct or any(
            '__' in _term for _term in (
                getattr(self, 'search_fields', [])
                + getattr(self, 'search_fields_exact', []))):
            queryset = queryset.distinct()
        return queryset

    search_filter = MagiFilter(to_queryset=_search_to_queryset)

    ordering = forms.ChoiceField(label=_('Ordering'))
    ordering_filter = MagiFilter(multiple=False)
    reverse_order = forms.BooleanField(label=_('Reverse order'))

    view = forms.ChoiceField(label=_('View'))
    view_filter = MagiFilter(noop=True)

    def _to_missing_translation_lambda(self, field_name):
        def _to_missing_translation(form, queryset, request, value=None):
            limit_sources_to = listUnique((request.user.preferences.settings_per_groups or {}).get(
                'translator', {}).get('languages', []) + ['en'])
            return get_missing_translations(queryset, field_name, value.split(','), limit_sources_to=limit_sources_to)
        return _to_missing_translation

    presets = {}
    show_presets_in_navbar = True

    _internal_presets = {}
    @classmethod
    def get_presets(self):
        if not getattr(self, '_internal_presets', None) and self.presets:
            self._internal_presets = OrderedDict([
                (tourldash(k), {
                    'fields': v
                } if 'fields' not in v else v)
                for k, v in self.presets.items()
            ])
        return self._internal_presets

    @classmethod
    def get_presets_fields(self, preset, details=None):
        if details is None: details = self.get_presets()[preset]
        return {
            k: [ unicode(i) for i in v ] if isinstance(v, list) else unicode(v)
            for k, v in details['fields'].items()
        }

    @classmethod
    def update_filters_with_preset(self, preset, filters):
        filters.update(self.get_presets_fields(preset))

    @classmethod
    def get_preset_verbose_name(self, preset, details=None):
        if details is None: details = self.get_presets()[preset]
        verbose_name = details.get('verbose_name', preset)
        if callable(verbose_name):
            verbose_name = verbose_name()
        return verbose_name

    @classmethod
    def get_preset_label(self, preset, plural_title, details=None):
        if details is None: details = self.get_presets()[preset]
        label = details.get('label', None)
        if callable(label):
            label = label()
        if not label:
            verbose_name = self.get_preset_verbose_name(preset, details=details)
            label = _('All {type} {things}').format(
                type=verbose_name,
                things=plural_title.lower(),
            )
        return label

    @classmethod
    def get_preset_icon(self, preset, details=None):
        if details is None: details = self.get_presets()[preset]
        return details.get('icon', None)

    @classmethod
    def get_preset_image(self, preset, details=None):
        if details is None: details = self.get_presets()[preset]
        image = details.get('image', None)
        if image:
            return staticImageURL(image)
        return None

    def _get_all_presets_links(self):
        links = []
        for preset, preset_details in type(self).get_presets().items():
            label = self.get_preset_label(
                preset, plural_title=self.collection.plural_title,
                details=preset_details,
            )
            image = self.get_preset_image(preset, details=preset_details)
            if image:
                image = u'<img src="{}" alt="{}" width="27px" style="display: block; margin: -5px 0;">'.format(
                    image, label)
            icon = self.get_preset_icon(preset, details=preset_details)
            if icon:
                icon = u'<i class="flaticon-{}" ></i>'.format(icon)
            links.append(u'<a href="{}" class="list-group-item"><span class="pull-right">{}</span>{}</a>'.format(
                self.collection.get_list_url(preset=preset, parameters={
                    'view': self.request.GET['view'],
                } if self.request and self.request.GET.get('view', None) else None),
                image or icon or '',
                u'<span{}>{}</span>'.format(
                    u' style="display: inline-block; width: 140px;"' if image else '',
                    label,
                ),
            ))
        return links

    @classmethod
    def set_filters_defaults_when_missing(self, collection, filters):
        boolean_fields = []
        was_updated = False
        for field_name in collection.list_view.filters_with_default_form_values:
            if field_name not in filters:
                if collection.list_view.filters_details[field_name]['form_field_class'] != forms.fields.BooleanField:
                    was_updated = True
                    filters.update_key(
                        field_name, collection.list_view.filters_details[field_name]['form_default'],
                    )
                else:
                    boolean_fields.append(field_name)
        # If anything needed up an update, then we're in the case where the URL was set manually
        # and not set from a form, so we should also set the default values for booleans
        if was_updated:
            for field_name in boolean_fields:
                if collection.list_view.filters_details[field_name]['form_default']:
                    filters.update_key(field_name, True)

    @property
    def extra_buttons(self):
        buttons = OrderedDict()
        # Random
        if self.collection and self.collection.list_view.allow_random:
            buttons['random'] = {
                'icon': 'dice',
                'verbose_name': _('Random'),
                'url': self.collection.get_list_url(random=True),
                'ajax_callback': 'loadRandomFilters',
                'new_tab': True,
            }
        # Presets
        links = self._get_all_presets_links()
        if links:
            attributes = { 'style': 'display: none;' }
            if not self.show_presets_in_navbar:
                attributes['data-always-hidden'] = jsv(True)
            buttons['presets'] = {
                'icon': 'idea',
                'verbose_name': _('Suggestions'),
                'url': '#',
                'attributes': attributes,
                'ajax_callback': 'loadPresets',
                'insert_in_sidebar': (
                    u'<div style="display: none;" id="filter-form-presets">{title}{nav}</div>{back}'.format(
                        title=u'<h4>{}</h4>'.format(_('Suggestions')),
                        nav=u'<nav class="list-group">{}</nav>'.format(
                            u''.join(links),
                        ),
                        back=u'<div class="sticky-buttons back" style="display: none;"><a href="#" class="btn btn-secondary btn-block">{}</a></div>'.format(
                            _('Back to {page_name}').format(page_name=u'"{}"'.format(t['Search'].lower())),
                        ),
                    )),
            }

        if buttons:
            # Reset
            buttons['clear'] = {
                'icon': 'clear',
                'verbose_name': t['Clear'],
                'url': self.collection.list_view.get_clear_url(self.request),
            }
        return buttons

    @classmethod
    def foreach_merge_fields(self, foreach_merge_field):
        """
        Goes through merge fields and apply a function
        Your function takes: new_field_name (the name of the merged fields), details, fields
        details is a dict with details (keys: label, fields)
        fields is a dict of field_name -> field details (keys: label, choices, filter)
        Note: the field details are not filled automatically if not specified by the user
        If in the future, this function needs to be the one doing the work of filling up
        those details, see logic in _foreach_merge_field in __init__ of MagiFiltersForm
        """
        if not getattr(self, 'merge_fields', None):
            return
        for new_field_name, fields in (
                self.merge_fields.items()
                if isinstance(self.merge_fields, dict)
                else [('_'.join(fields['fields'] if isinstance(fields, dict) else fields), fields)
                      for fields in self.merge_fields]
        ):
            if 'fields' in fields:
                details = fields
                fields = details['fields']
            else:
                details = {}
            foreach_merge_field(new_field_name, details, (
                fields
                if isinstance(fields, dict)
                else OrderedDict([ (field, {}) for field in fields ])
            ))

    def __init__(self, *args, **kwargs):
        self.preset = kwargs.pop('preset', None)
        super(MagiFiltersForm, self).__init__(*args, **kwargs)
        language = self.request.LANGUAGE_CODE if self.request else get_language()

        # Set action when using a preset

        if self.preset and self.collection:
            try:
                self.action_url = self.collection.get_list_url()
            except AttributeError:
                pass

        # Add/delete fields

        # Collectible
        if self.collection and self.request and self.request.user.is_authenticated():
            for collection_name, collection in self.collection.collectible_collections.items():
                if (collection.queryset.model.fk_as_owner
                    and collection.add_view.enabled):
                    # Add add_to_{} to fields that are collectible and have a quick add option
                    if collection.add_view.quick_add_to_collection(self.request):
                        setattr(self, u'add_to_{}_filter'.format(collection_name), MagiFilter(noop=True))
                        queryset = collection.queryset.model.owners_queryset(self.request.user)
                        initial = getattr(self.request, u'add_to_{}'.format(collection_name), None)
                        label = collection.add_sentence
                        help_text = None
                        # Check if only one option, hide picker
                        total_fk_owner_ids = getattr(
                            self.request, u'total_fk_owner_ids_{}'.format(collection_name), None)
                        if total_fk_owner_ids is None:
                            if collection.queryset.model.fk_as_owner == 'account':
                                total_fk_owner_ids = len(getAccountIdsFromSession(self.request))
                                label = _('Account')
                                help_text = collection.add_sentence
                            else:
                                total_fk_owner_ids = len(queryset)
                        if total_fk_owner_ids <= 1:
                            self.fields[u'add_to_{}'.format(collection_name)] = forms.IntegerField(
                                initial=initial,
                                widget=forms.HiddenInput(attrs=({'value': initial} if initial else {})),
                            )
                        else:
                            self.fields = OrderedDict(
                                [(u'add_to_{}'.format(collection_name), forms.ModelChoiceField(
                                    queryset=queryset, required=True,
                                    initial=initial, label=label, help_text=help_text,
                                ))] + self.fields.items())
                        # Exclude limited account types
                        if collection and collection.collectible_limit_to_account_types is not None:
                            self.fields[u'add_to_{}'.format(collection_name)].choices = [
                                (c.pk, unicode(c)) for c in queryset
                                if c.type in collection.collectible_limit_to_account_types
                            ]

                if collection.add_view.enabled:
                    # Add added_{} for fields that are collectible
                    field_name = u'added_{}'.format(collection_name)
                    if field_name in self.request.GET:
                        parent_item_name = self.collection.model_name
                        related_name = collection.queryset.model._meta.get_field(
                            parent_item_name).related_query_name()
                        setattr(self, u'{}_filter'.format(field_name), MagiFilter(
                            selector=u'{}__{}'.format(
                                related_name,
                                collection.queryset.model.fk_as_owner or 'owner',
                            )))
                        initial = getattr(self.request, u'add_to_{}'.format(collection_name), None)
                        self.fields[field_name] = forms.IntegerField(
                            initial=initial,
                            widget=forms.HiddenInput(attrs=({'value': initial} if initial else {})),
                        )
        # Add missing_{}_translations for all translatable fields if the current user has permission
        if self.collection and self.request and self.request.user.is_authenticated() and self.allow_translate and self.collection.translated_fields:
            for field_name in self.collection.translated_fields:
                filter_field_name = u'missing_{}_translations'.format(field_name)
                if filter_field_name in self.request.GET:
                    setattr(self, u'{}_filter'.format(filter_field_name), MagiFilter(
                        to_queryset=self._to_missing_translation_lambda(field_name),
                    ))
                    self.fields[filter_field_name] = forms.CharField(
                        widget=forms.HiddenInput
                    )

        # Filter by owner
        if self.request and 'owner' in self.request.GET:
            self.owner_filter = MagiFilter(selector=self.Meta.model.selector_to_owner())
            changeFormField(self, 'owner', forms.CharField, {
                'widget': forms.HiddenInput,
            })

        # Filter by foreign keys, many2many and reverse relations
        for field_name in getAllModelRelatedFields(self.Meta.model).keys():
            if field_name not in self.fields and field_name in (self.request.GET if self.request else {}):
                self.fields[field_name] = forms.ChoiceField(widget=forms.HiddenInput)

        # Filter by multi-level reverse relations ("__")
        for field_name in (self.request.GET if self.request and self.request.GET else {}):
            if '__' in field_name and field_name not in self.fields:
                self.fields[field_name] = forms.ChoiceField(widget=forms.HiddenInput)

        if 'search' in self.fields:
            # Remove search from field if search_fields is not specified
            if not getattr(self, 'search_fields', None) and not getattr(self, 'search_fields_exact', None):
                del(self.fields['search'])
            else:
                self.fields['search'].widget.attrs['autocomplete'] = 'off'
                # Add search help text
                if not self.fields['search'].help_text:
                    if not hasattr(type(self), 'search_field_help_text'):
                        type(self).search_field_help_text = {}
                    if language not in type(self).search_field_help_text:
                        type(self).search_field_help_text[language] = getSearchFieldHelpText(
                            search_fields=(
                                list(getattr(self, 'search_fields', []))
                                + list(getattr(self, 'search_fields_exact', []))
                            ),
                            model_class=self.Meta.model,
                            labels=getattr(self, 'search_fields_labels', {}),
                            translated_fields=(self.collection.translated_fields if self.collection else []) or [],
                        )
                    if type(self).search_field_help_text[language]:
                        self.fields['search'].help_text = type(self).search_field_help_text[language]

        # Remove ordering form field if ordering_fields is not specified
        if not getattr(self, 'ordering_fields', None):
            if 'ordering' in self.fields:
                del(self.fields['ordering'])
            if 'reverse_order' in self.fields:
                del(self.fields['reverse_order'])

        order_to_change = {}

        # Modify fields

        # Set cached choices
        if self.request and self.cache_choices:
            all_cached_choices = getattr(django_settings, 'CACHED_FILTER_FORM_CHOICES', {}).get(
                self.collection.name, {})
            if all_cached_choices:
                for field_name in self.cache_choices:
                    if (field_name not in self.fields
                        or field_name not in all_cached_choices):
                        continue
                    cached_choices = all_cached_choices[field_name]
                    # 1/ Choices from character
                    if isinstance(self.fields[field_name], forms.ModelChoiceField):
                        characters_key = isCharacterModelClass(self.fields[field_name].queryset.model)
                        if characters_key:
                            self.fields[field_name].choices = BLANK_CHOICE_DASH + [
                                (key, verbose)
                                for key, verbose in getCharactersChoices(characters_key)
                                if key in cached_choices
                            ]
                            changeFormField(
                                self, field_name, forms.ChoiceField, force_add=False,
                                new_parameters={ 'choices': self.fields[field_name].choices },
                            )
                            continue
                    # 2/ or Choices from cached dict
                    if isinstance(cached_choices, dict):
                        self.fields[field_name].choices = BLANK_CHOICE_DASH + [
                            (key, getTranslatedName(details))
                            for key, details in cached_choices.items()
                        ]
                        if isinstance(self.fields[field_name], forms.ModelChoiceField):
                            changeFormField(
                                self, field_name, forms.ChoiceField, force_add=False,
                                new_parameters={ 'choices': self.fields[field_name].choices },
                            )
                        continue
                    # 3/ or Choices from Null boolean
                    if isinstance(self.fields[field_name], forms.NullBooleanField):
                        if not cached_choices:
                            self.fields[field_name].widget = self.fields[field_name].hidden_widget()
                        continue
                    # 3/ Filter existing choices using cache
                    self.fields[field_name]._choices_before_cache = self.fields[field_name].choices
                    self.fields[field_name].choices = [
                        (choice, verbose)
                        for choice, verbose in self.fields[field_name].choices
                        if choice in cached_choices
                    ]
                    if not self.fields[field_name].choices:
                        self.fields[field_name].widget = self.fields[field_name].hidden_widget()

        # Merge filters
        if getattr(self, 'merge_fields', None):

            def _foreach_merge_field(new_field_name, details, fields):
                choices = BLANK_CHOICE_DASH[:]
                label_parts = []
                met_first_field = False
                for field_name, field_details in fields.items():
                    if field_name in self.fields:
                        self.fields[field_name].widget = self.fields[field_name].hidden_widget()
                        if not met_first_field:
                            setSubField(order_to_change, 'insert_after', key=field_name, value=[
                                new_field_name], force_add=True)
                            met_first_field = True
                    if (not self.request # Avoid loading all choices when initializing collections
                        and isinstance(self.fields.get(field_name, None), forms.ModelChoiceField)):
                        field_choices = []
                    else:
                        field_choices = field_details.get('choices', None)
                        if field_choices is None:
                            field_choices = getattr(self.fields.get(field_name, None), 'choices', None)
                        if field_choices is None:
                            try:
                                field_choices = self.Meta.model.get_choices(field_name)
                            except FieldDoesNotExist:
                                field_choices = []
                        if callable(field_choices):
                            field_choices = field_choices()
                    choices += [
                        (u'{}-{}'.format(field_name, _k), _v)
                        for _k, _v in field_choices
                        if _v != BLANK_CHOICE_DASH[0][1]
                    ]
                    field_label = (
                        field_details.get('label', None)
                        or getattr(self.fields.get(field_name, None), 'label', None)
                    )
                    if not field_label:
                        try:
                            field_label = notTranslatedWarning(
                                self.Meta.model._meta.get_field(field_name).verbose_name)
                        except FieldDoesNotExist:
                            field_label = toHumanReadable(field_name, warning=True)
                    label_parts.append(unicode(field_label))
                self.fields[new_field_name] = forms.ChoiceField(
                    choices=choices,
                    label=details.get('label', u' / '.join(label_parts)),
                )
                setattr(self, u'{}_filter'.format(new_field_name), MagiFilter(noop=True))

            self.foreach_merge_fields(_foreach_merge_field)

        # Set default ordering initial value
        if 'ordering' in self.fields:
            if self.collection:
                default_ordering = self.collection.list_view.default_ordering
                reverse = False
                if default_ordering.startswith('-'):
                    reverse = True
                    default_ordering = reverseOrderingString(default_ordering)
                # Add "Default" in ordering options if the default ordering is not in ordering fields
                if default_ordering and default_ordering not in dict(self.ordering_fields):
                    self.ordering_fields = [(default_ordering, _('Default'))] + self.ordering_fields
                self.fields['ordering'].initial = default_ordering
                self.fields['reverse_order'].initial = reverse
            self.fields['ordering'].choices = [
                (k, v() if callable(v) else v)
                for k, v in self.ordering_fields
            ]

        # Set view selector
        if ('view' in self.fields
            and self.collection
            and self.collection.list_view.alt_views):
            # If it's shown in narbar or top button, then it won't show as a filter
            if not self.collection.list_view._alt_view_visible_choices:
                self.fields['view'].widget = self.fields['view'].hidden_widget()
            self.fields['view'].choices = self.collection.list_view._alt_view_choices
        else:
            del(self.fields['view'])

        # Set all fields as optional and empty
        # If initial shouldn't be empty (ex: by default, only show Rare cards), this can
        # be changed in the __init__ of your form
        if getattr(self.Meta, 'all_optional', True):
            for field_name, field in self.fields.items():
                # Add blank choice to list of choices that don't have one
                # + Set initial as empty
                if (isinstance(field, forms.fields.ChoiceField)
                    and not isinstance(field, forms.ModelChoiceField)
                    and field.choices
                    and field_name != 'ordering'
                    and not field_name.startswith('add_to_')):
                    if isinstance(field, forms.fields.MultipleChoiceField):
                        self.fields[field_name].initial = ''
                    else:
                        choices = list(self.fields[field_name].choices)
                        if choices and choices[0][0] != '':
                            self.fields[field_name].choices = BLANK_CHOICE_DASH + choices
                            self.fields[field_name].initial = ''
                # Marks all fields as not required
                field.required = False

        # Reorder if needed
        if order_to_change:
            self.reorder_fields(newOrder(self.fields.keys(), **order_to_change))

    def _filter_queryset_for_field(self, field_name, queryset, request, value=None, filter=None):
        if True:
            if value is None or value == '':
                return queryset

            if not filter:
                filter = MagiFilter()
            if filter.noop:
                return queryset

            # Filtering is provided by to_queryset
            if filter.to_queryset:
                queryset = filter.to_queryset(self, queryset, request,
                                              value=self._value_as_string(filter, value))
            # Automatic filtering
            else:
                field = self.fields.get(field_name, forms.CharField())
                operator_for_multiple = filter.operator_for_multiple or MagiFilterOperator.default_for_field(field)
                operator_for_multiple_selectors = filter.operator_for_multiple_selectors or MagiFilterOperatorSelector.default
                original_operator_for_multiple_selectors = operator_for_multiple_selectors
                selectors = filter.selectors if filter.selectors else [field_name]
                condition = Q()
                filters, exclude = {}, {}
                for selector in selectors:
                    sub_condition = Q()
                    # NullBooleanField
                    if isinstance(field, forms.fields.NullBooleanField):
                        value = self._value_as_nullbool(filter, value)
                        if value is not None:
                            # Special case for __isnull selectors
                            if selector.endswith('__isnull') and not filter.to_value:
                                original_selector = selector[:(-1 * len('__isnull'))]

                                # When filtering for items that don't have values ("No"), swap operator for multiple selector:
                                if not value:
                                    if original_operator_for_multiple_selectors == MagiFilterOperatorSelector.And:
                                        operator_for_multiple_selectors = MagiFilterOperatorSelector.Or
                                    elif original_operator_for_multiple_selectors == MagiFilterOperatorSelector.Or:
                                        operator_for_multiple_selectors = MagiFilterOperatorSelector.And

                                # Get what corresponds to an empty value (if any)
                                empty_value = None
                                try:
                                    model_field = queryset.model._meta.get_field(original_selector)
                                    if (isinstance(model_field, TextField)
                                        or isinstance(model_field, CharField)
                                        or isinstance(model_field, ImageField)
                                    ):
                                        empty_value = ''
                                except FieldDoesNotExist: pass

                                if empty_value is not None:
                                    if value:
                                        sub_condition = Q(
                                            Q(**{ selector: False })
                                            & ~Q(**{ original_selector: empty_value })
                                        )
                                    else:
                                        sub_condition = Q(
                                            Q(**{ selector: True })
                                            | Q(**{ original_selector: empty_value })
                                        )
                                else:
                                    sub_condition = Q(**{ selector: not value })
                            else:
                                filters[selector] = value
                    # MultipleChoiceField
                    elif (isinstance(field, forms.fields.MultipleChoiceField)
                          or filter.multiple):
                        values = value if isinstance(value, list) else [value]
                        if field_name.startswith('c_'):
                            values = [u'"{}"'.format(sub_value) for sub_value in values]
                        if operator_for_multiple == MagiFilterOperator.OrContains:
                            for sub_value in values:
                                sub_condition = sub_condition | Q(**{ u'{}__contains'.format(selector): sub_value })
                        elif operator_for_multiple == MagiFilterOperator.OrExact:
                            filters = { u'{}__in'.format(selector): values }
                        elif operator_for_multiple == MagiFilterOperator.And:
                            for sub_value in values:
                                sub_condition = sub_condition & Q(**{ u'{}__contains'.format(selector): sub_value })
                        else:
                            raise NotImplementedError('Unknown operator for multiple condition')
                    # Generic
                    else:
                        filters = { selector: self._value_as_string(filter, value) }
                    # Add filters to condition based on operator for selectors
                    if operator_for_multiple_selectors == MagiFilterOperatorSelector.Or:
                        condition = condition | Q(**filters) | sub_condition
                    else:
                        condition = condition & Q(**filters) & sub_condition
                queryset = queryset.filter(condition).exclude(**exclude)
                if filter.distinct:
                    queryset = queryset.distinct()
        return queryset

    def filter_queryset(self, queryset, parameters, request):
        # Generic filter for ids
        queryset = filter_ids(queryset, parameters.get('ids', None))
        # Go through form fields
        for field_name in self.fields.keys():
            # Some fields are handled in views collection
            if field_name in GET_PARAMETERS_NOT_IN_FORM + GET_PARAMETERS_IN_FORM_HANDLED_OUTSIDE:
                continue
            filter = getattr(self, '{}_filter'.format(field_name), None)
            if not filter:
                filter = MagiFilter()
            # Get value as list first
            value = None
            if field_name in parameters:
                if hasValue(parameters[field_name]):
                    value = parameters[field_name]
                    if ((isinstance(self.fields[field_name], forms.fields.MultipleChoiceField)
                         or filter.multiple)
                        and not isinstance(self.fields[field_name], forms.fields.NullBooleanField)):
                        value = self._value_as_list(filter, parameters, field_name, filter.allow_csv)
            # Use initial value if any
            else:
                value = self.fields[field_name].initial
            queryset = self._filter_queryset_for_field(field_name, queryset, request, value=value, filter=filter)
        return queryset

    def _value_as_string(self, filter, value):
        return filter.to_value(value) if filter.to_value else value

    def to_nullbool(self, value):
        return toNullBool(value)

    def _value_as_nullbool(self, filter, value):
        new_value = self.to_nullbool(value)
        return filter.to_value(new_value) if filter.to_value else new_value

    def _value_as_list(self, filter, parameters, field_name, allow_csv=True):
        if isinstance(parameters, QueryDict):
            value = parameters.getlist(field_name)
            if allow_csv and len(value) == 1:
                value = unicode(value[0] or '').split(',')
        else:
            value = parameters[field_name]
        return filter.to_value(value) if filter.to_value else value

    def _post_clean(self):
        """
        In django/forms/models.py, will try to construct an instance and will fail when some values are missing.
        Overriding this method will bypass the checks and allow fitlers to work even when some values are missing.
        """
        pass

    def save(self, commit=True):
        raise NotImplementedError('MagiFiltersForm are not meant to be used to save models. Use a regular MagiForm instead.')

def to_auto_filter_form(list_view):
    auto_search_fields = []
    auto_ordering_fields = []
    filter_fields = []
    for field in list_view.collection.queryset.model._meta.fields:
        field_name = field.name
        if field_name.startswith('_'):
            continue
        try:
            field = list_view.collection.queryset.model._meta.get_field(field_name)
        except FieldDoesNotExist: # ManyToMany and reverse relations
            continue
        if ((isinstance(field, django_models.CharField)
             or isinstance(field, django_models.TextField))
            # Fields with choices shouldn't be here
            and not getattr(list_view.collection.queryset.model, '{name}_CHOICES'.format(
                name=field_name[2:].upper()), None)
            and not isinstance(field, YouTubeVideoField)):
            auto_search_fields.append(field_name)

        if field_name in (getattr(list_view.collection.item_view, 'fields_exclude', []) or []):
            continue

        if (not field_name.startswith('i_')
            and field_name != 'id'
            and (('name' in field_name and not field_name.startswith('d_'))
                 or isinstance(field, django_models.IntegerField)
                 or isinstance(field, django_models.FloatField)
                 or isinstance(field, django_models.AutoField)
                 or isinstance(field, django_models.DateField)
            )
        ):
            auto_ordering_fields.append((field_name, field.verbose_name))

        if (field_name.startswith('i_')
            or (field_name.startswith('c_')
                and not getattr(list_view.collection.queryset.model, '{name}_CHOICES'.format(
                    name=field_name[2:].upper()), None))
            or isinstance(field, django_models.BooleanField)
            or isinstance(field, django_models.NullBooleanField)):
            filter_fields.append(field_name)

    class _AutoFiltersForm(MagiFiltersForm):
        if auto_search_fields:
            search_fields = auto_search_fields
        if auto_ordering_fields:
            ordering_fields = auto_ordering_fields

        def __init__(self, *args, **kwargs):
            super(_AutoFiltersForm, self).__init__(*args, **kwargs)
            self.cuteform = getattr(self, 'cuteform', {})
            for field_name in filter_fields:
                # Auto cuteform for boolean fields
                if field_name in self.fields and isinstance(self.fields[field_name], forms.BooleanField):
                    self.cuteform[field_name] = {
                        'type': CuteFormType.YesNo,
                    }
                    changeFormField(self, field_name, forms.NullBooleanField, {
                        'required': False,
                        'initial': None,
                    })

        class Meta(MagiFiltersForm.Meta):
            model = list_view.collection.queryset.model
            fields = ([
                'search',
            ] if auto_search_fields else []) + ([
                'ordering', 'reverse_order'
            ] if auto_ordering_fields else []) + (
                filter_fields
            )

    return _AutoFiltersForm

############################################################
############################################################

############################################################
# Accounts forms

class AccountForm(AutoForm):
    def __init__(self, *args, **kwargs):
        super(AccountForm, self).__init__(*args, **kwargs)
        if self.is_reported:
            for field in ['start_date', 'default_tab', 'center', 'is_playground']:
                if field in self.fields:
                    del(self.fields[field])
        else:
            if 'is_hidden_from_leaderboard' in self.fields:
                del(self.fields['is_hidden_from_leaderboard'])
        if 'center' in self.fields:
            if self.is_creating:
                del(self.fields['center'])
            else:
                self.fields['center'].queryset = self.fields['center'].queryset.filter(account=self.instance.id)
        if self.is_creating and 'nickname' in self.fields and self.request:
            if len(getAccountIdsFromSession(self.request)) == 0:
                self.fields['nickname'].widget = self.fields['nickname'].hidden_widget()
        if 'default_tab' in self.fields:
            if not self.collection or not hasattr(self.collection, 'get_profile_account_tabs'):
                del(self.fields['default_tab'])
            else:
                changeFormField(self, 'default_tab', forms.ChoiceField, {
                    'required': False,
                    'label': _('Default tab'),
                    'initial': (
                        FIRST_COLLECTION_PER_ACCOUNT_TYPE.get(self.form_type, None)
                        or FIRST_COLLECTION
                    ),
                    'choices': BLANK_CHOICE_DASH + [
                        (tab_name, tab['name'])
                        for tab_name, tab in
                        self.collection.get_profile_account_tabs(
                            self.request,
                            RAW_CONTEXT,
                            self.instance if not self.is_creating else None,
                            account_type=self.form_type,
                        ).items()
                    ],
                })
                if len(self.fields['default_tab'].choices) <= 2:
                    self.fields['default_tab'].widget = self.fields['default_tab'].hidden_widget()
        self.previous_level = None
        if 'level' in self.fields:
            if MAX_LEVEL:
                self.fields['level'].validators += [MaxValueValidator(MAX_LEVEL)]
            if not self.is_creating:
                self.previous_level = self.instance.level
        self.previous_screenshot = ''
        if 'screenshot' in self.fields and not self.is_creating:
            self.previous_screenshot = unicode(self.instance.screenshot) or ''
        if 'level_on_screenshot_upload' in self.fields:
            del(self.fields['level_on_screenshot_upload'])

    def clean(self):
        new_level = self.cleaned_data.get('level')
        screenshot_image = self.cleaned_data.get('screenshot') or ''
        previous_level = 0
        if not self.is_creating:
            previous_level = getattr(self.instance, 'level_on_screenshot_upload', self.previous_level) or 0
        is_playground = getattr(self.instance, 'is_playground', False) if not self.is_creating else False
        if self.cleaned_data.get('is_playground'):
            is_playground = True
        if (new_level
            and not is_playground
            and new_level != previous_level
            and has_field(self.Meta.model, 'screenshot')
            and new_level >= MAX_LEVEL_BEFORE_SCREENSHOT_REQUIRED
            and (new_level - previous_level) >= MAX_LEVEL_UP_STEP_BEFORE_SCREENSHOT_REQUIRED
            and unicode(screenshot_image) == unicode(self.previous_screenshot)):
            raise forms.ValidationError(
                message=_('Please provide an updated screenshot of your in-game profile to prove your level.'),
                code='level_proof_screenshot',
            )
        return self.cleaned_data

    def save(self, commit=True):
        instance = super(AccountForm, self).save(commit=False)
        if not self.is_creating and 'level' in self.fields and instance.level != self.previous_level and has_field(instance, '_cache_leaderboards_last_update'):
            instance._cache_leaderboards_last_update = None
        # When level screenshot gets updated, update level_on_screenshot_upload
        if (has_field(self.Meta.model, 'screenshot')
            and unicode(getattr(self, 'previous_screenshot', '')) != unicode(instance.screenshot)):
            instance.level_on_screenshot_upload = instance.level
        if commit:
            instance.save()
        return instance

    class Meta(AutoForm.Meta):
        model = models.Account
        fields = '__all__'
        save_owner_on_creation = True

def get_account_simple_form(account_form_class=None, simple_fields=['nickname', 'level', 'friend_id']):

    if not account_form_class:
        account_form_class = AccountForm

    class _AccountSimpleForm(account_form_class):
        def __init__(self, *args, **kwargs):
            super(_AccountSimpleForm, self).__init__(*args, **kwargs)
            if (not self.data.get('screenshot')
                and 'screenshot' in self.fields
                and int(self.data.get('level', 0) or 0) < MAX_LEVEL_BEFORE_SCREENSHOT_REQUIRED):
                self.fields['screenshot'].widget = forms.HiddenInput()
            if 'start_date' in self.fields:
                del(self.fields['start_date'])
            if 'default_tab' in self.fields:
                self.fields['default_tab'].widget = self.fields['default_tab'].hidden_widget()

        class Meta(AccountForm.Meta):
            fields = [
                field for field in simple_fields
                if has_field(account_form_class.Meta.model, field)
            ] + (['screenshot'] if (
                'level' in simple_fields
                and has_field(account_form_class.Meta.model, 'screenshot')
            ) else []) + ['default_tab']

    return _AccountSimpleForm

class AccountFilterForm(MagiFiltersForm):
    search_fields = ['owner__username', 'nickname', 'owner__links__value']
    search_fields_exact = ['owner__email']
    search_fields_labels = {
        'owner__username': _('Username'),
        'owner__links__value': _('Links'),
        'owner__email': _('Email'),
    }

    ordering_fields = [
        ('level', _('Level')),
        ('owner__username', _('Username')),
        ('creation', _('Join Date')),
        ('start_date', _('Start Date')),
        ('owner__preferences___cache_reputation', _('Most popular')),
    ]

    ordering_show_relevant_fields = {
        'owner__preferences___cache_reputation': [ 'reputation' ],
    }

    on_change_value_show = {
        'has_friend_id': {
            True: ['friend_id', 'accept_friend_requests'],
        },
    }
    show_more = FormShowMore(cutoff='i_os')

    if has_field(models.Account, 'friend_id'):
        has_friend_id = forms.NullBooleanField(
            required=False, initial=None,
            label=models.Account._meta.get_field('friend_id').verbose_name,
        )
        has_friend_id_filter = MagiFilter(selector='friend_id__isnull')

    if USER_COLORS:
        color = forms.ChoiceField(label=_('Color'), choices=BLANK_CHOICE_DASH + [
            (_color_name, _color_verbose_name)
            for (_color_name, _color_verbose_name, _color_css, _color_hex) in USER_COLORS
        ])
        color_filter = MagiFilter(selector='owner__preferences__color')

    def __init__(self, *args, **kwargs):
        super(AccountFilterForm, self).__init__(*args, **kwargs)

        # Friend ID placeholder
        if 'friend_id' in self.fields:
            self.fields['friend_id'].widget.attrs['placeholder'] = _('Optional')

        # Remove fields relevant for users list if users list in navbar
        user_collection = getMagiCollection('user')
        if user_collection and user_collection.navbar_link:
            for field_name in ['color']:
                if field_name in self.fields:
                    del(self.fields[field_name])
        else:

            # Add favorite characters fields

            characters_fields = getCharactersFavoriteFields(only_one=True)
            for key, fields in characters_fields.items():
                for (field_name, field_verbose_name) in fields:
                    if hasCharacters(key=key):
                        self.fields[field_name] = forms.ChoiceField(
                            label=field_verbose_name,
                            choices=BLANK_CHOICE_DASH + getCharactersChoices(key=key),
                            required=False,
                        )
                        setattr(
                            self, u'{}_filter'.format(field_name),
                            MagiFilter(**getCharactersFavoriteFilter(key=key, prefix='owner')))
            # Re-order
            self.reorder_fields(self.Meta.top_fields + [
                field_name
                for fields in characters_fields.values()
                for field_name, _verbose in fields
            ] + self.Meta.middle_fields)
            # CuteForm
            if not getattr(self, 'cuteform', None):
                self.cuteform = {}
            self.cuteform.update(getCharactersFavoriteCuteForm(only_one=True))

    class Meta(MagiFiltersForm.Meta):
        model = models.Account
        top_fields = [
            'search', 'ordering', 'reverse_order',
        ] + (
            (['has_friend_id', 'friend_id']
             + (['accept_friend_requests'] if has_field(models.Account, 'accept_friend_requests') else []))
            if has_field(models.Account, 'friend_id') else []
        )
        middle_fields = (
            ['color'] if USER_COLORS else []
        ) + (
            ['i_os'] if has_field(models.Account, 'i_os') else []
        ) + (
            ['i_play_with'] if has_field(models.Account, 'i_play_with') else []
        )
        fields = top_fields + middle_fields

############################################################
# Users forms

class _UserCheckEmailUsernameForm(MagiForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return None
        email = email.lower()
        # If the email didn't change
        if self.previous_email and self.previous_email == email:
            return email
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if re.search(r'^\d+$', username):
            raise forms.ValidationError(
                message=t["%(field_labels)s can\'t contain only digits."],
                code='unique_together',
                params={'field_labels': _('Username')},
            )
        return username

    def clean(self):
        super(_UserCheckEmailUsernameForm, self).clean()
        # If another user uses this email address or username
        formUniquenessCheck(
            self, edited_instance=self.instance,
            field_names=['email', 'username'],
            case_insensitive=True,
            unique_together=False,
            all_fields_required=True,
        )

    def __init__(self, *args, **kwargs):
        super(_UserCheckEmailUsernameForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True
        if not self.is_creating:
            self.previous_email = self.instance.email
        else:
            self.previous_email = None

    def save(self, commit=True):
        instance = super(_UserCheckEmailUsernameForm, self).save(commit=False)
        if self.previous_email and self.previous_email != instance.email and instance.preferences.invalid_email:
            instance.preferences.invalid_email = False
            instance.preferences.save()
        if commit:
            instance.save()
        return instance

class LoginForm(AuthenticationForm):
    # captcha = ReCaptchaField()

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        if (getattr(django_settings, 'DEBUG', False)
            and not getattr(django_settings, 'RECAPTCHA_PUBLIC_KEY', None)
            and 'captcha' in self.fields):
            del(self.fields['captcha'])

class CreateUserForm(_UserCheckEmailUsernameForm):
    # captcha = ReCaptchaField()
    submit_title = _('Sign Up')
    PREFERENCES_FIELDS = [ 'birthdate', 'show_birthdate_year' ]
    password = forms.CharField(widget=forms.PasswordInput(), min_length=6, label=t['Password'])

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        preferences_initial = (
            model_to_dict(instance.preferences, self.PREFERENCES_FIELDS)
            if instance is not None else {}
        )
        super(CreateUserForm, self).__init__(initial=preferences_initial, instance=instance, *args, **kwargs)
        self.fields.update(fields_for_model(models.UserPreferences, self.PREFERENCES_FIELDS))
        self.fields['birthdate'], value = date_input(self.fields['birthdate'])

        self.otherbuttons = mark_safe(u'<a href="{url}" class="btn btn-lg btn-link">{verbose}</a>'.format(
            url=addParametersToURL('/login/', parameters={ k: v for k, v in {
                'next': self.request.GET.get('next', None),
                'next_title': self.request.GET.get('next_title', None),
            }.items() if v }),
            verbose=_('Login'),
        ))

    class Meta(_UserCheckEmailUsernameForm.Meta):
        model = models.User
        fields = ('username', 'email', 'password')

class UserForm(_UserCheckEmailUsernameForm):
    form_title = string_concat(_('Username'), ' / ', t['Email'])
    form_icon = 'profile'

    class Meta(_UserCheckEmailUsernameForm.Meta):
        model = models.User
        fields = ('username', 'email',)

class EmailsPreferencesForm(MagiForm):
    form_title = _('Emails')
    form_icon = 'contact'

    def __init__(self, *args, **kwargs):
        super(EmailsPreferencesForm, self).__init__(*args, **kwargs)
        turned_off = self.request.user.preferences.email_notifications_turned_off
        for (type, message) in models.Notification.MESSAGES:
            value = True
            if type in turned_off:
                value = False
            self.fields['email{}'.format(type)] = forms.BooleanField(required=False, label=message['title'], initial=value)

    def save(self, commit=True):
        new_emails_settings = []
        for type in models.Notification.MESSAGES_DICT.keys():
            if not self.cleaned_data.get('email{}'.format(type), False):
                new_emails_settings.append(models.Notification.get_i('message', type))
        self.request.user.preferences.save_email_notifications_turned_off(new_emails_settings)
        if commit:
            self.request.user.preferences.save()
        return self.request.user.preferences

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = []

class ActivitiesPreferencesForm(MagiForm):
    form_title = _('Activities')
    form_icon = 'comments'

    def __init__(self, *args, **kwargs):
        super(ActivitiesPreferencesForm, self).__init__(*args, **kwargs)

        # Get allowed tags
        # Should only disallow tags from the future
        allowed_tags = models.getAllowedTags(
            self.request, check_hidden_by_user=False,
            as_dict=True, check_permissions_to_show=False,
        )

        # Remove past tags without any activity from tags choices
        allowed_tags = OrderedDict([
            (tag_name, tag_verbose)
            for tag_name, tag_verbose in allowed_tags.items()
            if getattr(django_settings, 'PAST_ACTIVITY_TAGS_COUNT', {}).get(tag_name, 1) != 0
        ])

        # Set initial values
        # and initialize dict if it's the first time a user changes their settings
        new_d = self.instance.hidden_tags.copy()
        for default_hidden in models.ACTIVITIES_TAGS_HIDDEN_BY_DEFAULT:
            if default_hidden not in new_d:
                new_d[default_hidden] = True
        self.instance.save_d('hidden_tags', new_d)
        self.old_hidden_tags = self.instance.hidden_tags
        for field_name in self.fields.keys():
            if field_name.startswith('d_hidden_tags'):
                tag_name = field_name.replace('d_hidden_tags-', '')
                if tag_name not in allowed_tags:
                    del(self.fields[field_name])
                else:
                    self.fields[field_name] = forms.BooleanField(
                        label=self.fields[field_name].label,
                        help_text=self.fields[field_name].help_text,
                        required=False,
                        initial=self.instance.hidden_tags.get(
                            field_name.replace('d_hidden_tags-', ''), False),
                )
        if 'view_activities_language_only' in self.fields:
            self.fields['view_activities_language_only'].label = u'{} ({})'.format(
                self.fields['view_activities_language_only'].label,
                self.instance.t_language,
            )
        if 'i_activities_language' in self.fields:
            self.fields['i_activities_language'].label = unicode(
                self.fields['i_activities_language'].label).format(language='')
        if ('i_default_activities_tab' in self.fields
            and self.request.LANGUAGE_CODE not in LANGUAGES_CANT_SPEAK_ENGLISH):
            self.fields['i_default_activities_tab'].below_field = mark_safe(
                u'<a href="/help/Activities%20tabs" data-ajax-url="/ajax/help/Activities%20tabs/" class="pull-right btn btn-link-muted" target="_blank">{}</a>'.format(
                    _('Learn more'),
                ))

    def clean(self):
        super(ActivitiesPreferencesForm, self).clean()
        # Check permission to show tags
        not_allowed_tags_and_reasons = models.getForbiddenTags(
            self.request, check_hidden_by_user=False)
        for field_name in self.fields.keys():
            if field_name.startswith('d_hidden_tags'):
                tag_name = field_name.replace('d_hidden_tags-', '')
                if (self.old_hidden_tags.get(tag_name, False)
                    and not self.cleaned_data.get(field_name, False)):
                    if tag_name in not_allowed_tags_and_reasons:
                        raise forms.ValidationError(not_allowed_tags_and_reasons[tag_name][1])

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = ('view_activities_language_only', 'i_default_activities_tab', 'i_activities_language', 'd_hidden_tags', )
        d_save_falsy_values_for_keys = {
            'hidden_tags': models.ACTIVITIES_TAGS_HIDDEN_BY_DEFAULT,
        }

class SecurityPreferencesForm(MagiForm):
    form_title = string_concat(_('Private messages'), ' (', _('Security'), ')')
    form_icon = 'contact'

    def __init__(self, *args, **kwargs):
        super(SecurityPreferencesForm, self).__init__(*args, **kwargs)

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = ('i_private_message_settings', )

class _DisplayOutsidePermissions(_MagiDisplayMultiple):
    template = u"""
        <div class="alert alert-warning">
          <h5>External permissions</h5>
          <p>
            <small class="text-muted">
              Added manually.
              Contact the <b>team manager</b> if you don't have them.
            </small>
          </p>
          <ul>
            {display_value}
          </ul>
        </div>
    """
    template_foreach = u'<li>{value}</li>'

DisplayOutsidePermissions = _DisplayOutsidePermissions()

class _DisplayGlobalOutsidePermissions(_MagiDisplayMultiple):
    template = u"""
  <div class="alert alert-warning">
    <h5>External permissions for all staff members.</h5>
    <p>
      <small class="text-muted">
        Added manually.
        Contact the <b>team manager</b> if you don't have them.
      </small>
    </p>
    <ul>
      {display_value}
    </ul>
  </div>
    """
    template_foreach = u'<li>{value}</li>'

def outsidePermissionsToParameters(key, value):
    return {
        'link': value.get('url', None) if isinstance(value, dict) else value,
        'text_image': staticImageURL(value.get('image', None) if isinstance(value, dict) else None),
        'text_image_height': 20,
        'text_icon': value.get('icon', None) if isinstance(value, dict) else (
            'link' if not isinstance(value, dict) or not value.get('image', None) else None),
    }

class _DisplayGroup(MagiDisplay):
    """Value = group_name"""
    OPTIONAL_PARAMETERS = {
        u'translation': None,
        u'description': None,
        u'verbose_permissions': None,
        u'requires_staff': None,
        u'outside_permissions': None,
        u'guide': None,
        u'ajax_guide': None,
        u'settings': None,
    }
    def to_parameters_extra(self, parameters):
        group = models.UserPreferences.GROUPS.get(parameters.display_value, None)
        if group:
            parameters.update(group)
            parameters.img = staticImageURL(parameters.display_value, folder='groups', extension='png')
        if parameters.ajax_guide:
            parameters.ajax_guide = markSafeFormat(u'data-ajax-url="{ajax_guide}"', ajax_guide=parameters.ajax_guide)
        if parameters.outside_permissions:
            parameters.outside_permissions = DisplayOutsidePermissions.to_html(
                parameters.item, value=parameters.outside_permissions,
                item_display_class=MagiDisplayLink,
                item_to_value=lambda value, _parameters_per_item: _parameters_per_item.key,
                item_to_parameters=outsidePermissionsToParameters,
            )

    template = u"""
    <div class="list-group-item">
      <img class="pull-right" alt="{translation}" src="{img}" height="100">
      <h3 class="list-group-item-heading">{translation}</h3>
      <p class="list-group-item-text">
        <blockquote class="fontx0-8">{description}</blockquote>
        {verbose_permissions}
        {outside_permissions}
      </p>
      {guide}
    </div>
    """
    template_verbose_permissions = u'<h5>Permissions</h5><ul>{verbose_permissions}</ul>'
    template_verbose_permissions_foreach = u'<li>{value}</li>'
    template_guide = u"""
      <div class="text-right">
        <a class="btn btn-lg btn-secondary btn-lines" href="{guide}" {ajax_guide} target="_blank">
          Read the {translation} guide <i class="flaticon-link"></i>
        </a>
      </div>
    """

DisplayGroup = _DisplayGroup()

class EditGroupsSettings(MagiForm):
    form_title = _('Roles')
    form_icon = 'staff'

    def __init__(self, *args, **kwargs):
        super(EditGroupsSettings, self).__init__(*args, **kwargs)
        # Add settings fields and groups details
        if self.instance:
            no_settings_groups = []
            for group_name in self.instance.groups:
                if group_name not in models.UserPreferences.GROUPS:
                    continue
                group = models.UserPreferences.GROUPS[group_name]
                new_fields = groupSettingsFields(self, group_name, edited_preferences=self.instance)
                if new_fields:
                    self.fields[new_fields[0]].before_field = markSafeJoin([
                        markSafe(DisplayGroup.to_html(self.instance, group_name)),
                        markSafe('<div class="list-group-item">'),
                    ])
                    self.fields[new_fields[-1]].after_field = markSafe('</div>')
                else:
                    no_settings_groups.append(markSafe(DisplayGroup.to_html(self.instance, group_name)))
            self.afterfields = markSafeJoin(no_settings_groups)
            self.beforefields = DisplayOutsidePermissions.to_html(
                self.instance, value=GLOBAL_OUTSIDE_PERMISSIONS,
                item_display_class=MagiDisplayLink,
                item_to_value=lambda value, _parameters_per_item: _parameters_per_item.key,
                item_to_parameters=outsidePermissionsToParameters,
            )

    def save(self, commit=True):
        instance = super(EditGroupsSettings, self).save(commit=False)
        saveGroupsSettingsFields(self, self.instance)
        if commit:
            instance.save()
        return instance

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = []

class UserPreferencesForm(MagiForm):
    form_title = _('Customize profile')
    form_icon = 'id'

    if USER_COLORS:
        color = forms.ChoiceField(label=_('Color'), required=False, choices=BLANK_CHOICE_DASH + [
            (_color_name, _color_verbose_name)
            for (_color_name, _color_verbose_name, _color_css, _color_hex) in USER_COLORS
        ])

    default_tab = forms.ChoiceField(
        label=_('Default tab'),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super(UserPreferencesForm, self).__init__(*args, **kwargs)

        order = ['m_description', 'location']

        # Remove color if needed
        if 'color' in self.fields and not USER_COLORS:
            del(self.fields['color'])

        # Default tab
        if 'default_tab' in self.fields:
            self.fields['default_tab'].choices = BLANK_CHOICE_DASH + [
                (tab_name, tab['name'])
                for tab_name, tab in PROFILE_TABS.items()
            ] + [
                (collection_name, getMagiCollection(collection_name).list_view.profile_tab_name)
                for collection_name in RAW_CONTEXT['collections_in_profile_tabs']
            ] + [
                (collection_name, collection.collectible_tab_name)
                for collection_name, collection
                in RAW_CONTEXT.get('collectible_collections', {}).get('owner', {}).items()
            ]

        # Make favorite characters fields a selection
        for key, fields in getCharactersFavoriteFields(only_one=False).items():
            for field_name, verbose_name in fields:
                if field_name in self.fields:
                    if getCharactersHasMany(key):
                        del(self.fields[field_name]) # will be in external page
                    else:
                        self.fields[field_name] = forms.ChoiceField(
                            required=False,
                            choices=BLANK_CHOICE_DASH + getCharactersChoices(key=key),
                            label=verbose_name,
                            initial=self.fields[field_name].initial,
                        )
                        order.append(field_name)
        if not hasCharacters() or getCharactersHasMany(): # will be in external page
            for field_name in ['favorite_character1', 'favorite_character2', 'favorite_character3']:
                if field_name in self.fields:
                    del(self.fields[field_name])

        # Backgrounds
        if 'd_extra-background' in self.fields:
            if (not PROFILE_BACKGROUNDS_NAMES
                or HAS_MANY_BACKGROUNDS):
                del(self.fields['d_extra-background'])
                self.d_choices['extra'] = [
                    (k, v) for k, v in self.d_choices['extra']
                    if k != 'd_extra-background'
                ]
            else:
                self.fields['d_extra-background'] = forms.ChoiceField(
                    required=False,
                    label=self.fields['d_extra-background'].label,
                    initial=self.fields['d_extra-background'].initial,
                    choices=BLANK_CHOICE_DASH + [(k, v()) for k, v in PROFILE_BACKGROUNDS_NAMES.items()],
                )

        # Location
        if 'location' in self.fields:
            self.fields['location'].help_text = mark_safe(
                u'{} <a href="/map/" target="_blank">{} <i class="flaticon-link"></i></a>'.format(
                    unicode(self.fields['location'].help_text),
                    unicode(_(u'Open {thing}')).format(thing=unicode(_('Map')).lower()),
                ))

        self.old_location = self.instance.location if self.instance else None
        if 'm_description' in self.fields:
            self.fields['m_description'].help_text = markdownHelpText(self.request, ajax=self.ajax)

        self.reorder_fields(order)

    def clean_birthdate(self):
        if 'birthdate' in self.cleaned_data:
            if self.cleaned_data['birthdate'] and self.cleaned_data['birthdate'] > datetime.date.today():
                raise forms.ValidationError(_('This date cannot be in the future.'))
        return self.cleaned_data['birthdate']

    def clean(self):
        super(UserPreferencesForm, self).clean()
        # All favorites must be unique
        for key, fields in getCharactersFavoriteFields(only_one=False).items():
            favorites = [value for value in [
                self.cleaned_data.get(field_name, None)
                for field_name, _verbose_name in fields
            ] if value]
            if len(favorites) != len(set(favorites)):
                raise forms.ValidationError(_('All your favorites must be unique'))
        return self.cleaned_data

    def save(self, commit=True):
        instance = super(UserPreferencesForm, self).save(commit=False)
        if self.old_location != instance.location:
            instance.location_changed = True
            instance.latitude = None
            instance.longitude = None
        if commit:
            instance.save()
        return instance

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = [
            'm_description', 'location',
            'favorite_character1', 'favorite_character2', 'favorite_character3',
            'color', 'birthdate', 'show_birthdate_year',
            'default_tab', 'd_extra',
        ]
        keep_unknwon_keys_for_d = ['extra']

class SetFavoriteCharacter(MagiForm):
    nth = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        self.key = kwargs.pop('key', 'FAVORITE_CHARACTERS')
        super(SetFavoriteCharacter, self).__init__(*args, **kwargs)
        total_favoritable = getCharactersTotalFavoritable(key=self.key)
        self.fields['nth'].label = getCharactersFavoriteFieldLabel(key=self.key)
        self.fields['nth'].choices = BLANK_CHOICE_DASH + [
            (i, _(ordinalNumber(i)))
            for i in range(1, total_favoritable + 1)
        ]

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = []

class StaffEditUser(_UserCheckEmailUsernameForm):
    class Meta(_UserCheckEmailUsernameForm.Meta):
        model = models.User
        fields = [ 'username', 'email' ]

class StaffAddRevokeOutsidePermissions(forms.Form):
    beforefields = markSafe("""
    <div class="alert alert-warning">
    <i class="flaticon-warning"></i> Some permissions need to be manually given to (or revoked from) this user.
    Please make sure you click on each link and add (or revoke) them.<br>
    <small><i>If you're having trouble with these or you're unsure how to do it,
    please message a Manager, Circles Manager or System administrator.</i></small>
    </div>
    """)

    def __init__(self, *args, **kwargs):
        to_add = kwargs.pop('to_add', {})
        to_revoke = kwargs.pop('to_revoke', {})
        super(StaffAddRevokeOutsidePermissions, self).__init__(*args, **kwargs)
        for name, details in to_revoke.items():
            self.fields[name] = forms.BooleanField(
                required=True, label=markSafe(
                    '<i class="flaticon-delete text-danger"></i> <b>REVOKE</b> access to',
                ), help_text=markSafeFormat(
                    '<a href="{url}" target="_blank"> {name} <i class="flaticon-{icon}"></i></a>',
                    url=details.get('url', '') if isinstance(details, dict) else details,
                    name=name, icon=details.get('icon', 'link') if isinstance(details, dict) else 'link',
                ),
            )
            if isinstance(details, dict):
                how_to = details.get('how_to_revoke', details.get('how_to', None))
                if how_to:
                    self.fields[name].below_field = markSafeFormat(
                        u'<div class="text-muted fontx0-8"><i class="flaticon-idea"></i> {}</div>', how_to)
        for name, details in to_add.items():
            self.fields[name] = forms.BooleanField(
                required=True, label=markSafe(
                    '<i class="flaticon-add text-success"></i> <b>GIVE</b> access to',
                ), help_text=markSafeFormat(
                    '<a href="{url}" target="_blank"> {name} <i class="flaticon-{icon}"></i></a>',
                    url=details.get('url', '') if isinstance(details, dict) else details,
                    name=name, icon=details.get('icon', 'link') if isinstance(details, dict) else 'link',
                ),
            )
            if isinstance(details, dict):
                how_to = details.get('how_to_add', details.get('how_to', None))
                if how_to:
                    self.fields[name].below_field = markSafeFormat(
                        u'<div class="text-muted fontx0-8"><i class="flaticon-idea"></i> {}</div>', how_to)

STAFFEDITUSERPREFERENCES_FIELDS_PER_PERMISSION = {
    # Edit reported things permission
    'edit_reported_things': [
        'm_description',
        'location',
        'force_remove_avatar',
    ],

    # Mark email addresses invalid permission
    'mark_email_addresses_invalid': [
        'invalid_email',
    ],

    # Edit roles permission
    'edit_roles': [
        'c_groups',
    ],

    # Edit donator status permission
    'edit_donator_status': [
        'i_status',
        'donation_link',
        'donation_link_title',
    ],
}

class StaffEditUserPreferences(MagiForm):
    BEFOREFIELDS_TEMPLATE = u"""
    <div class="row form-group">
    <label class="col-sm-4 text-right">Username</label>
      <div class="col-sm-8"><pre>{username}</pre></div>
    </div>
    <div class="row form-group">
      <label class="col-sm-4 text-right">E-mail address</label>
      <div class="col-sm-8"><pre>{email}</pre></div>
    </div>
    <div class="row form-group"><div class='col-sm-offset-4 col-sm-8'>
    <div class="alert alert-info">Inappropriate username or e-mail address?
    <a class="btn btn-main btn-sm" href="{edit_user_url}" data-ajax-url="{ajax_edit_user_url}">
    Edit username or e-mail address</a></div></div></div>"""

    force_remove_avatar = forms.BooleanField(required=False)

    cuteform = {
        'i_status': {
            'type': CuteFormType.HTML,
            'to_cuteform': lambda _key, _value: u'{}{}'.format(
                (u'<i class="flaticon-heart" style="color: {}"></i>'.format(
                    models.UserPreferences.STATUS_COLORS[_key])
                 if _key in models.UserPreferences.STATUS_COLORS else u''), _value),
        },
    }

    on_change_value_show = {
        'i_status': {
            _key: [ 'donation_link', 'donation_link_title' ]
            for _key, _verbose in models.UserPreferences.STATUS_CHOICES
            if _key != 'THANKS'
        },
        'c_groups': {
            _group: [ u'group_settings_{}_{}'.format(_group, _setting) for _setting in _details['settings'] ]
            for _group, _details in models.UserPreferences.GROUPS.items()
            if 'settings' in _details
        },
    }

    def _delete_all_unrelated_fields(self, _current_type):
        for _type, field_names in STAFFEDITUSERPREFERENCES_FIELDS_PER_PERMISSION.items():
            if _type != _current_type:
                for field_name in field_names:
                    del(self.fields[field_name])

    def __init__(self, *args, **kwargs):
        super(StaffEditUserPreferences, self).__init__(*args, **kwargs)
        if not self.request:
            return
        if not self.instance:
            raise PermissionDenied()
        # Used by save:
        self.previous_location = self.instance.location if self.instance else None
        # Used by redirect_after_edit:
        self.request._previous_groups = self.instance.groups if self.instance else []
        self.request._previous_is_staff = self.instance.owner.is_staff if self.instance else False

        # Edit reported things permission
        if self.is_reported:
            if not hasPermission(self.request.user, 'edit_reported_things'):
                raise PermissionDenied()
            self._delete_all_unrelated_fields('edit_reported_things')
            # Add user fields
            self.fields['force_remove_avatar'].help_text = markSafeFormat(
                u"""Check this box if the avatar is inappropriate.
                It will force the default avatar.
                <img src="{avatar_url}" alt="{username}" height="40" width="40">""",
                avatar_url=self.instance.owner.image_url, username=self.instance.owner.username,
            )
            self.beforefields = markSafeFormat(
                self.BEFOREFIELDS_TEMPLATE,
                username=self.instance.owner.username, email=self.instance.owner.email,
                edit_user_url=addParametersToURL(self.instance.owner.edit_url, parameters={
                    'edit_reported_user': '' }), ajax_edit_user_url=addParametersToURL(
                        self.instance.owner.ajax_edit_url, parameters={ 'edit_reported_user': '' }))

        # Mark email addresses invalid permission
        elif 'mark_email_addresses_invalid' in self.request.GET:
            if not hasPermission(self.request.user, 'mark_email_addresses_invalid'):
                raise PermissionDenied()
            self._delete_all_unrelated_fields('mark_email_addresses_invalid')
            self.fields['invalid_email'].above_field = markSafeFormat(
                u'<pre>{}</pre>', self.instance.owner.email)

        # Edit roles permission
        elif 'edit_roles' in self.request.GET:
            if not hasPermission(self.request.user, 'edit_roles'):
                raise PermissionDenied()
            self._delete_all_unrelated_fields('edit_roles')
            self.fields['c_groups'].choices = [
                (key, markSafeFormat(
                    u"""<img class="pull-right" height="60" alt="{name}" src="{img}">
                    <b>{name}</b><br><p>{reqstaff}<small class="text-muted">{description}</small></p>
                    <ul>{perms}</ul>{operms}<br>""",
                    img=staticImageURL(key, folder='groups', extension='png'),
                    name=group['translation'],
                    reqstaff=(
                        markSafe(u'<small class="text-danger">Requires staff status</small><br>')
                        if group.get('requires_staff', False) else u''
                    ),
                    description=group['description'],
                    perms=markSafeJoin([
                        markSafeFormat(
                            u'<li style="display: list-item"><small>{}</small></li>',
                            toHumanReadable(p, warning=False),
                        ) for p in group.get('permissions', [])
                    ]),
                    operms=markSafeFormat(
                        u"""<br><div class="alert alert-danger"><small>
                        Make sure you also grant/revoke {user} the following permissions <b>manually</b>:
                        </small> <ul>{permissions}</ul></div>""",
                        user=self.instance.owner.username,
                        permissions=markSafeJoin([
                            markSafeFormat(
                                u'<li style="display: list-item"><small>{}</small></li>',
                                p if not u
                                else markSafeFormat(
                                        u'<a href="{}" target="_blank">{} <i class="flaticon-link"></i></a>',
                                        u['url'] if isinstance(u, dict) else u, p
                                ),
                            ) for p, u in group['outside_permissions'].items()
                        ]),
                    ) if group.get('outside_permissions', {}) else u'',
                )) for key, group in models.UserPreferences.GROUPS.items()
            ]
            # Add settings
            for group_name in models.UserPreferences.GROUPS.keys():
                groupSettingsFields(self, group_name, edited_preferences=self.instance)

        # Edit donator status permission
        elif 'edit_donator_status' in self.request.GET:
            self._delete_all_unrelated_fields('edit_donator_status')
            self.fields['donation_link_title'].help_text = u"""
            If the donator is not interested in adding a link but are eligible for it,
            write "Not interested" and leave ""Donation link" empty"""

        else:
            raise PermissionDenied()

    def save(self, commit=True):
        instance = super(StaffEditUserPreferences, self).save(commit=False)
        save_owner = False

        # Force remove avatar
        if ('force_remove_avatar' in self.fields
            and self.cleaned_data['force_remove_avatar']
            and instance.owner.email):
            splitEmail = instance.owner.email.split('@')
            localPart = splitEmail.pop(0)
            instance.owner.email = localPart.split('+')[0] + u'+' + randomString(4) + '@' + ''.join(splitEmail)
            save_owner = True

        # Location
        if 'location' in self.fields and self.previous_location != self.cleaned_data['location']:
            instance.location_changed = True
            instance.latitude = None
            instance.longitude = None

        # Groups
        if 'c_groups' in self.fields and 'c_groups' in self.cleaned_data:
            save_owner = True
            if instance.owner.is_superuser:
                instance.owner.is_staff = True
            else:
                instance.owner.is_staff = False
                for group_name in instance.groups:
                    if models.UserPreferences.GROUPS.get(group_name, {}).get('requires_staff', False):
                        instance.owner.is_staff = True
                        break
            saveGroupsSettingsFields(self, self.instance)

        if save_owner:
            instance.owner.save()
        if commit:
            instance.save()
        return instance

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = sum(STAFFEDITUSERPREFERENCES_FIELDS_PER_PERMISSION.values(), [])

class ChangePasswordForm(MagiForm):
    form_title = _('Change your password')
    form_icon = 'lock'

    old_password = forms.CharField(widget=forms.PasswordInput(), label=_('Old Password'))
    new_password = forms.CharField(widget=forms.PasswordInput(), label=_('New Password'), min_length=6)
    new_password2 = forms.CharField(widget=forms.PasswordInput(), label=_('New Password Again'))

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        self.user = authenticate(username=self.request.user.username, password=old_password)
        if not self.user:
            raise forms.ValidationError(t['Your old password was entered incorrectly. Please enter it again.'])
        return old_password

    def clean(self):
        super(ChangePasswordForm, self).clean()
        new_password = self.cleaned_data.get('new_password', None)
        new_password2 = self.cleaned_data.get('new_password2', None)
        if new_password and new_password2 and new_password != new_password2:
            raise forms.ValidationError(t["The two password fields didn't match."])
        return self.cleaned_data

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()
        authenticate(username=self.user.username, password=self.cleaned_data['new_password'])
        login_action(self.request, self.user)

    class Meta(MagiForm.Meta):
        model = models.User
        fields = []

class UserFilterForm(MagiFiltersForm):
    search_fields = ('username', 'links__value')
    search_fields_exact = ('email', )
    search_fields_labels = {
        'links__value': _('Links'),
    }
    ordering_fields = (
        ('id', _('Join Date')),
        ('username', _('Username')),
        ('preferences___cache_reputation', _('Most popular')),
        ('followed,id', _('Following')),
    )

    ordering_show_relevant_fields = {
        'username': [],
    }

    show_more = FormShowMore(cutoff='color' if USER_COLORS else 'location')

    def _get_preset_language_label(verbose_language):
        return lambda: _('Users who can speak {language}').format(language=verbose_language)

    show_presets_in_navbar = False
    presets = OrderedDict([
        # Used when clicking on the language of a user
        (_language, {
            'verbose_name': _verbose_language,
            'label': _get_preset_language_label(_verbose_language),
            'fields': {
                'i_language': _language
            },
            'image': u'language/{}.png'.format(_language),
        }) for _language, _verbose_language in models.UserPreferences.LANGUAGE_CHOICES
    ])

    followers_of = HiddenModelChoiceField(queryset=models.User.objects.all())
    followers_of_filter = MagiFilter(selector='preferences__following')

    followed_by = HiddenModelChoiceField(queryset=models.User.objects.all())
    followed_by_filter = MagiFilter(selector='followers__user')

    liked_activity = HiddenModelChoiceField(queryset=models.Activity.objects.all())
    liked_activity_filter = MagiFilter(
        selectors=['activities', 'liked_activities'],
        distinct=True,
    )

    if USER_COLORS:
        color = forms.ChoiceField(label=_('Color'), choices=BLANK_CHOICE_DASH + [
            (c[0], c[1]) for c in USER_COLORS
        ])
        color_filter = MagiFilter(selector='preferences__color')

    location = forms.CharField(label=_('Location'))
    location_filter = MagiFilter(selector='preferences__location__icontains', multiple=False)

    i_language = forms.ChoiceField(label=_('Language'), choices=(
        BLANK_CHOICE_DASH + list(models.UserPreferences.LANGUAGE_CHOICES)))
    i_language_filter = MagiFilter(selector='preferences__i_language')

    def __init__(self, *args, **kwargs):
        super(UserFilterForm, self).__init__(*args, **kwargs)

        # Favorite characters
        characters_fields = getCharactersFavoriteFields(only_one=True)
        for key, fields in characters_fields.items():
            for (field_name, field_verbose_name) in fields:
                if hasCharacters(key=key):
                    self.fields[field_name] = forms.ChoiceField(
                        label=field_verbose_name,
                        choices=BLANK_CHOICE_DASH + getCharactersChoices(key=key),
                        required=False,
                    )
                    setattr(
                        self, u'{}_filter'.format(field_name),
                        MagiFilter(**getCharactersFavoriteFilter(key=key)),
                    )
            # Re-order
            self.reorder_fields(self.Meta.top_fields + [
                field_name
                for fields in characters_fields.values()
                for field_name, _verbose in fields
            ] + self.Meta.middle_fields)
            # CuteForm
            if not getattr(self, 'cuteform', None):
                self.cuteform = {}
            self.cuteform.update(getCharactersFavoriteCuteForm(only_one=True))

        # Hide following ordering option unless selected
        if ('ordering' in self.fields
            and self.request
            and self.request.GET.get('ordering', None) != 'followed,id'):
            self.fields['ordering'].choices = [
                (k, v)
                for k, v in self.fields['ordering'].choices
                if k != 'followed,id'
            ]

    def filter_queryset(self, queryset, parameters, request):
        queryset = super(UserFilterForm, self).filter_queryset(queryset, parameters, request)

        # Filter by who the user can private messages to
        # Should follow the logic of utils.hasPermissionToMessage
        if (request.GET.get('view', None) == 'send_private_message'
            and request.user.is_authenticated()):

            # Can't send message to self
            queryset = queryset.exclude(id=request.user.id)

            # Can't use private messages if reputation is not good enough
            if not request.user.preferences.has_good_reputation:
                queryset = queryset.filter(id=-1)
            queryset = queryset.filter(preferences___cache_reputation__gte=GOOD_REPUTATION_THRESHOLD)

            # Do not allow if blocked or blocked by
            queryset = queryset.exclude(blocked_by=request.user.preferences)
            queryset = queryset.exclude(preferences__blocked=request.user)

            # If messages are closed
            if request.user.preferences.private_message_settings == 'nobody':
                queryset = queryset.filter(id=-1)
            queryset = queryset.exclude(
                preferences__i_private_message_settings=models.UserPreferences.get_i(
                    'private_message_settings', 'nobody'),
            )

            # If messages are only open to followed and not followed
            # Following is already filtered by "followed_by" in GET
            queryset = queryset.exclude(
                Q(preferences__i_private_message_settings=models.UserPreferences.get_i(
                    'private_message_settings', 'follow'))
                & ~Q(preferences__following=request.user),
            )
        return queryset

    class Meta(MagiFiltersForm.Meta):
        model = models.User
        top_fields = [
            'search', 'ordering', 'reverse_order',
        ]
        middle_fields = (
            ['color'] if USER_COLORS else []
        ) + [
            'location',
            'i_language',
        ]
        fields = top_fields + middle_fields

############################################################
# User links

class AddLinkForm(MagiForm):
    action_url = '#links'
    form_icon = 'add'

    @property
    def form_title(self):
        return _(u'Add {thing}').format(thing=unicode(_('Link')).lower())

    def __init__(self, *args, **kwargs):
        super(AddLinkForm, self).__init__(*args, **kwargs)
        if 'i_relevance' in self.fields:
            self.fields['i_relevance'].label = _('How often do you tweet/stream/post about {}?').format(GAME_NAME)
        if 'i_type' in self.fields:
            self.fields['i_type'].choices = BLANK_CHOICE_DASH + [
                (name, localized)
                for (name, localized) in self.fields['i_type'].choices
                if name != django_settings.SITE
            ]

    def save(self, commit=True):
        instance = super(AddLinkForm, self).save(commit)
        if instance.i_type == 'twitter':
            self.request.user.preferences._cache_twitter = instance.value
            self.request.user.preferences.save()
            models.onPreferencesEdited(self.request.user)
            if ON_PREFERENCES_EDITED:
                ON_PREFERENCES_EDITED(self.request.user)
        return instance

    class Meta(MagiForm.Meta):
        model = models.UserLink
        fields = ('i_type', 'value', 'i_relevance')
        save_owner_on_creation = True

class DonationLinkForm(MagiForm):
    form_icon = 'promo'

    def clean(self):
        super(DonationLinkForm, self).clean()
        if self.cleaned_data.get('donation_link', None) and not self.cleaned_data.get('donation_link_title', None):
            raise forms.ValidationError({ 'donation_link_title': [t['This field is required.']] })
        elif not self.cleaned_data.get('donation_link', None) and self.cleaned_data.get('donation_link_title', None):
            raise forms.ValidationError({ 'donation_link': [t['This field is required.']] })

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = ('donation_link', 'donation_link_title')

############################################################
# Change language (on top bar)

class LanguagePreferencesForm(MagiForm):
    form_title = _('Language')
    form_icon = 'translate'

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = ('i_language',)

############################################################
# Confirm - works with everything

class ConfirmDelete(forms.Form):
    confirm = forms.BooleanField(required=True, initial=False, label=_('Confirm'))
    thing_to_delete = forms.IntegerField(widget=forms.HiddenInput, required=True)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.collection = kwargs.pop('collection', None)
        self.instance = kwargs.pop('instance', None)
        super(ConfirmDelete, self).__init__(*args, **kwargs)

    def _get_total_deleted(self, instances, total=0):
        for instance in instances:
            if isinstance(instance, list):
                total += self._get_total_deleted(instance, total=total)
            else:
                total += 1
        return total

    def clean(self):
        if not self.request or not self.collection or not self.instance:
            return
        if self.request.user.hasPermission('bypass_maximum_items_that_can_be_deleted_at_once'):
            return
        up_to = self.collection.edit_view.allow_cascade_delete_up_to(self.request)
        if not up_to:
            return
        collector = NestedObjects(using=self.instance._state.db)
        collector.collect([self.instance])
        total = self._get_total_deleted(collector.nested())
        if total >= up_to:
            raise forms.ValidationError(mark_safe(u'You are not allowed to delete this. {}'.format(
                'Ask a manager.' if self.request.user.is_staff else '<a href="/help/Delete%20error/" data-ajax-url="/ajax/help/Delete%20error/">Learn more</a>.',
            )))

class Confirm(forms.Form):
    confirm = forms.BooleanField(required=True, initial=False, label=_('Confirm'))

############################################################
# Staff configuration form

class StaffConfigurationForm(AutoForm):
    value = forms.NullBooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(StaffConfigurationForm, self).__init__(*args, **kwargs)
        if 'value' in self.fields and (self.is_creating or not self.instance.is_boolean):
            self.fields['value'] = forms.CharField(required=False)
            if not self.is_creating and not self.instance.is_long:
                self.fields['value'].widget = forms.TextInput()
            else:
                self.fields['value'].widget = forms.Textarea()
        if not self.is_creating and self.instance.is_markdown and 'value' in self.fields:
            self.fields['value'].help_text = markdownHelpText(self.request, ajax=self.ajax)

    def save(self, commit=True):
        instance = super(StaffConfigurationForm, self).save(commit=False)
        # Save owner as last updater
        instance.owner = self.request.user if self.request.user.is_authenticated() else None
        if commit:
            instance.save()
        return instance

    class Meta(AutoForm.Meta):
        model = models.StaffConfiguration
        save_owner_on_creation = True
        fields = '__all__'

class StaffConfigurationSimpleEditForm(StaffConfigurationForm):
    class Meta(StaffConfigurationForm.Meta):
        fields = ('verbose_key', 'value')

class StaffConfigurationFilters(MagiFiltersForm):
    search_fields = [ 'key', 'verbose_key', 'value' ]

    has_value = forms.NullBooleanField()
    has_value_filter = MagiFilter(selector='value__isnull')

    with_translations = forms.NullBooleanField()
    with_translations_filter = MagiFilter(selector='i_language__isnull')

    key = forms.CharField(widget=forms.HiddenInput)

    class Meta(MagiFiltersForm.Meta):
        model = models.StaffConfiguration
        fields = [
            'search', 'ordering', 'reverse_order',
            'i_language', 'has_value', 'key',
        ]

############################################################
# Staff details form

class StaffDetailsForm(AutoForm):
    for_user = forms.CharField(required=True)

    def clean_for_user(self):
        try:
            return models.User.objects.get(username=self.cleaned_data['for_user'], is_staff=True)
        except ObjectDoesNotExist:
            raise forms.ValidationError('User doesn\'t exist or is not staff')

    @property
    def to_owner(self):
        return self.cleaned_data.get('for_user', self.request.user)

    def __init__(self, *args, **kwargs):
        super(StaffDetailsForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            if (field_name == 'for_user'
                or field_name.startswith('d_availability')
                or field_name.startswith('d_weekend_availability')):
                continue
            if field_name in models.StaffDetails.PUBLIC_FIELDS:
                self.fields[field_name].help_text = mark_safe(u'{} (Public)'.format(self.fields[field_name].help_text))
            else:
                self.fields[field_name].help_text = mark_safe(u'{} (Only staff can see it)'.format(self.fields[field_name].help_text))
        if self.is_creating and self.request and hasPermission(self.request.user, 'edit_staff_details'):
            pass
        elif 'for_user' in self.fields:
            del(self.fields['for_user'])
        for field_name in self.fields.keys():
            if field_name.startswith('d_availability') or field_name.startswith('d_weekend_availability'):
                self.fields[field_name] = forms.BooleanField(
                    label=(
                        self.fields[field_name].label
                        if field_name.endswith(models.StaffDetails.AVAILABILITY_CHOICES[0][0])
                        else ''
                    ),
                    help_text=self.fields[field_name].help_text,
                    initial=self.fields[field_name].initial,
                    required=False,
                )

    class Meta(AutoForm.Meta):
        model = models.StaffDetails
        save_owner_on_creation = True
        tinypng_on_save = ('image',)
        fields = ['for_user', 'discord_username', 'preferred_name', 'pronouns', 'image', 'description', 'favorite_food', 'hobbies', 'nickname', 'c_hashtags', 'staff_since', 'i_timezone', 'availability_details', 'experience', 'other_experience', 'd_availability', 'd_weekend_availability']

class StaffDetailsFilterForm(MagiFiltersForm):
    search_fields = ['owner__username', 'discord_username', 'preferred_name', 'description', 'nickname']
    search_fields_labels = {
        'owner__username': _('Username'),
    }

    class Meta:
        model = models.StaffDetails
        fields = [ 'search' ]

############################################################
# Activity form

class ActivityForm(MagiForm):
    save_activities_language = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
        if ('fix_language' in self.request.GET
            or (not self.is_creating
                and self.instance.owner_id != self.request.user.id
                and not self.request.user.hasPermission('edit_reported_things'))):
            for field_name in self.fields.keys():
                if field_name not in ['i_language', 'save_activities_language']:
                    del(self.fields[field_name])
        if 'i_language' in self.fields:
            self.fields['i_language'].initial = (
                self.request.user.preferences.activities_language
                if self.request.user.is_authenticated() and self.request.user.preferences.activities_language
                else django_settings.LANGUAGE_CODE
            )
            if (self.request.user.preferences.view_activities_language_only
                and self.request.user.preferences.i_activities_language
                == self.request.user.preferences.i_language):
                self.fields['i_language'].widget = self.fields['i_language'].hidden_widget()
            # Option to change preferences to always post activities in selected language
            if 'save_activities_language' in self.fields:
                self.fields['save_activities_language'].label = mark_safe(
                    _('Always post activities in {language}').format(
                        language=u'<span class="selected_language">{}</span>'.format(
                            unicode(t['Language']).lower(),
                        ),
                    ),
                )
                if self.is_creating or self.instance.owner_id == self.request.user.id:
                    owner = self.request.user
                else:
                    owner = self.instance.owner
                self.previous_activities_language = owner.preferences.i_activities_language
                self.fields['save_activities_language'].widget.attrs[
                    'data-activities-language'] = self.previous_activities_language
                self.fields['save_activities_language'].initial = (self.previous_activities_language == (
                    self.fields['i_language'].initial if self.is_creating else self.instance.i_language
                ))
        elif 'save_activities_language' in self.fields:
            del(self.fields['save_activities_language'])

        if 'm_message' in self.fields:
            # Community managers are allowed to post activities with no character limit
            if (not self.request
                or not self.request.user.is_authenticated()
                or not self.request.user.hasPermission('post_news')):
                self.fields['m_message'].validators += [MaxLengthValidator(15000)]
        # Only allow users to add tags they are allowed to add or already had before
        if 'c_tags' in self.fields:
            self.fields['c_tags'].choices = models.getAllowedTags(
                self.request, is_creating=True,
                # Ensure previously added tags don't get deleted
                force_allow=self.instance.c_tags if not self.is_creating else None,
            )
        self.previous_m_message = None
        if 'm_message' in self.fields and not self.is_creating:
            self.previous_m_message = self.instance.m_message

    def clean(self):
        self.cleaned_data = super(ActivityForm, self).clean()
        # Needs either an image or a message
        image = self.cleaned_data.get('image', self.instance.image if not self.is_creating else None)
        m_message = self.cleaned_data.get('m_message', self.instance.m_message if not self.is_creating else None)
        if not image and not m_message:
            raise forms.ValidationError(_('{thing} required.').format(
                thing=u' {} '.format(t['or']).join([unicode(_('Message')), unicode(_('Image'))])))
        return self.cleaned_data

    def save(self, commit=False):
        instance = super(ActivityForm, self).save(commit=False)
        instance.update_cache('hidden_by_default')
        if not self.is_creating and instance.m_message != self.previous_m_message:
            instance.last_bump = timezone.now()
        if (hasattr(self, 'previous_activities_language')
            and 'save_activities_language' in self.cleaned_data
            and self.cleaned_data['save_activities_language']
            and self.previous_activities_language != instance.i_language):
            models.UserPreferences.objects.filter(user_id=instance.owner_id).update(
                i_activities_language=instance.i_language,
            )
        if commit:
            instance.save()
        return instance

    class Meta(MagiForm.Meta):
        model = models.Activity
        fields = ('m_message', 'image', 'c_tags', 'i_language', 'save_activities_language')
        save_owner_on_creation = True

class FilterActivities(MagiFiltersForm):
    search_fields = ['m_message', 'c_tags']
    ordering_fields = [
        ('last_bump', _('Hot')),
        ('creation', _('Creation')),
        ('_cache_total_likes,creation', string_concat(_('Most popular'), ' (', _('All time'), ')')),
        ('_cache_total_likes,id', string_concat(_('Most popular'), ' (', _('This week'), ')')),
    ]

    show_more = FormShowMore(cutoff='is_popular')

    c_tags_filter = MagiFilter(selector=u'c_tags', operator_for_multiple=MagiFilterOperator.And)

    c_past_tags = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, label=_('Past tags'))
    c_past_tags_filter = MagiFilter(selector=u'c_tags', operator_for_multiple=MagiFilterOperator.And)

    with_image = forms.NullBooleanField(label=_('Image'))
    with_image_filter = MagiFilter(selector='image__isnull')

    def _is_popular_to_queryset(self, queryset, request, value):
        # Skip the filter if owner is selected
        if self.data.get('owner', None):
            return queryset
        value = self.to_nullbool(value)
        if value is None:
            return queryset
        filter_popular = {
            '_cache_total_likes__{filter}'.format(filter='gte' if value else 'lt'):
            MINIMUM_LIKES_POPULAR,
        }
        # If logged in and default tab is popular and current tab is popular,
        # it's likely the user didn't change their settings and will expect to
        # see the activities they just posted on the homepage, so also return
        # own activities to avoid confusion
        if (request.user.is_authenticated()
            and self.active_tab == 'popular'
            and request.user.preferences.default_activities_tab == 'popular'):
            return queryset.filter(Q(**filter_popular) | Q(owner_id=request.user.id))
        # Really only popular
        return queryset.filter(**filter_popular)

    is_popular = forms.NullBooleanField(label=_('Popular'), initial=True)
    is_popular_filter = MagiFilter(to_queryset=_is_popular_to_queryset)

    hide_archived = forms.BooleanField(label=_('Hide archived activities'), initial=False)
    hide_archived_filter = MagiFilter(to_queryset=lambda form, queryset, request, value: queryset.exclude(
        archived_by_owner=True,
    ) if value else queryset)

    is_following = forms.BooleanField(label=string_concat(_('Following'), ' (', _('Only'), ')'), initial=False)
    is_following_filter = MagiFilter(to_queryset=lambda form, queryset, request, value: queryset.filter(
        Q(owner__in=request.user.preferences.following.all())
        | Q(owner_id=request.user.id)
    ) if value else queryset)

    liked = forms.BooleanField(label=string_concat(_('Liked'), ' (', _('Only'), ')'), initial=False)
    liked_filter = MagiFilter(to_queryset=lambda form, queryset, request, value: queryset.filter(
        Q(likes__id=request.user.id) | Q(owner_id=request.user.id),
    ).distinct() if value else queryset)

    def __init__(self, *args, **kwargs):
        super(FilterActivities, self).__init__(*args, **kwargs)
        # Only allow users to filter by tags they are allowed to see
        # Place past tags in past_tags
        if 'c_tags' in self.fields and 'c_past_tags' in self.fields:
            tags_choices = []
            c_past_tags_choices = []
            for tag_name, tag in models.getAllowedTags(self.request, full_tags=True):
                if tag['status'] == 'ended':
                    count = getattr(django_settings, 'PAST_ACTIVITY_TAGS_COUNT', {}).get(tag_name, None)
                    if count != 0:
                        c_past_tags_choices.append((
                            tag_name,
                            u'{} ({})'.format(tag['translation'] , count)
                            if count else tag['translation']
                        ))
                else:
                    tags_choices.append((tag_name, tag['translation']))
            if tags_choices:
                self.fields['c_tags'].choices = tags_choices
            else:
                del(self.fields['c_tags'])
            if c_past_tags_choices:
                self.fields['c_past_tags'].choices = c_past_tags_choices
            else:
                del(self.fields['c_past_tags'])
        # Default selected language
        if 'i_language' in self.fields:
            self.default_to_current_language = False
            if (self.request
                and (
                    (self.request.user.is_authenticated()
                     and self.request.user.preferences.view_activities_language_only)
                    or (not self.request.user.is_authenticated()
                        and (ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT
                             or self.request.LANGUAGE_CODE in ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES))
                )):
                self.default_to_current_language = True
                self.fields['i_language'].initial = self.request.LANGUAGE_CODE
        if self.request and not self.request.user.is_authenticated():
            if 'is_following' in self.fields:
                del(self.fields['is_following'])
            if 'liked' in self.fields:
                del(self.fields['liked'])
        self.active_tab = None
        if self.request and self.request.user.is_authenticated():
            # If a tab is selected in the request (URL)
            self.request_tab = None
            if self.request.path.startswith('/activities/'):
                self.request_tab = self.request.path.split('/')[2]
            elif self.request.path.startswith('/ajax/activities/'):
                self.request_tab = self.request.path.split('/')[3]
            if self.request_tab and self.request_tab in HOME_ACTIVITY_TABS:
                self.active_tab = self.request_tab
            # If the filter side bar has been used, no tab open
            elif self.data:
                self.active_tab = None
            # If the user has a preference
            elif self.request.user.preferences.i_default_activities_tab is not None:
                self.active_tab = self.request.user.preferences.default_activities_tab
            # Default to popular
            else:
                self.active_tab = 'popular'
            # Set the initial to the value of the preferences
            if self.active_tab:
                for field_name, value in HOME_ACTIVITY_TABS[self.active_tab]['form_fields'].items():
                    if field_name in self.fields:
                        self.fields[field_name].initial = value

    def filter_queryset(self, queryset, parameters, request):
        queryset = super(FilterActivities, self).filter_queryset(queryset, parameters, request)
        if (parameters.get('ordering', None) == '_cache_total_likes,id'
            or ('ordering' in self.fields
                and self.fields['ordering'].initial == '_cache_total_likes,id'
                and 'ordering' not in parameters)):
            queryset = queryset.filter(creation__gte=timezone.now() - relativedelta(weeks=1))
        return queryset

    @property
    def action_url(self):
        if self.request_tab:
            return '/'
        return self.request.path

    class Meta(MagiFiltersForm.Meta):
        model = models.Activity
        fields = [
            'search', 'ordering', 'reverse_order',
            'c_tags', 'is_popular',
            'is_following', 'liked',
            'hide_archived', 'with_image',
            'i_language',
            'c_past_tags',
        ]

ActivityFilterForm = FilterActivities

############################################################
# Notifications

class FilterNotification(MagiFiltersForm):
    search_fields = ['c_message_data', 'c_url_data']
    search_fields_labels = {
        'c_message_data': _('Message'),
        'c_url_data': t['URL'],
    }

    class Meta(MagiFiltersForm.Meta):
        model = models.Notification
        fields = ('search', 'i_message')

NotificationFilterForm = FilterNotification

############################################################
# Add/Edit reports

class BaseReportForm(MagiForm):
    def __init__(self, *args, **kwargs):
        self.type = kwargs.pop('type', None)
        super(BaseReportForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.reported_thing_id = self.instance.reported_thing_id
            self.type = self.instance.type
        elif self.request:
            if 'id' not in self.request.GET:
                raise PermissionDenied()
            self.reported_thing_id = self.request.GET['id']
            # Check if the reported thing exists
            get_object_or_404(getMagiCollectionFromModelName(self.type).queryset, pk=self.reported_thing_id)
        if 'images' in self.fields:
            self.fields['images'].help_text = _('Optional')

    def save(self, commit=True):
        instance = super(BaseReportForm, self).save(commit=False)
        collection = getMagiCollectionFromModelName(self.type)
        instance.reported_thing = collection.name
        instance.reported_thing_id = self.reported_thing_id
        instance.reported_thing_title = getEnglish(collection.title)
        return instance

    class Meta(MagiForm.Meta):
        model = models.Report
        fields = ('reason', 'message', 'images')
        save_owner_on_creation = True

class ReportForm(BaseReportForm):
    reason = forms.ChoiceField(required=True, label=_('Reason'))

    def __init__(self, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)
        reasons = OrderedDict()
        collection = getMagiCollectionFromModelName(self.type)
        if collection:
            for reason in (
                    collection.report_edit_templates.keys()
                    + collection.report_delete_templates.keys()
            ):
                reasons[reason] = reason
            self.fields['reason'].choices = BLANK_CHOICE_DASH + reasons.items()
            self.beforefields = HTMLAlert(
                message=markSafeFormat(
                    u'{message}<ul>{list}</ul>{learn_more}',
                    message=_(u'Only submit a report if there is a problem with this specific {thing}. If it\'s about something else, your report will be ignored. For example, don\'t report an account or a profile if there is a problem with an activity. Look for "Report" buttons on the following to report individually:').format(thing=collection.title.lower()),
                    list=markSafeJoin([
                        markSafeFormat(u'<li>{}</li>', unicode(type['plural_title']))
                        for name, type in self.collection.types.items() if name != self.type
                    ]),
                    learn_more=(
                        '' if (self.request.LANGUAGE_CODE if self.request else get_language()) in LANGUAGES_CANT_SPEAK_ENGLISH else
                        markSafeFormat(
                            u'<div class="text-right"><a href="/help/Report" data-ajax-url="/ajax/help/Report/" target="_blank" class="btn btn-warning">{}</a></div>',
                            _('Learn more'))),
                ))

class SuggestedEditForm(BaseReportForm):
    reason = forms.MultipleChoiceField(required=True, label=_('Reason'))

    def __init__(self, *args, **kwargs):
        super(SuggestedEditForm, self).__init__(*args, **kwargs)
        if not self.is_creating:
            self.instance.reason = (
                ', '.join(self.instance.reason) if isinstance(self.instance.reason, list) else self.instance.reason
            ).split(', ')
        if 'reason' in self.fields:
            collection = getMagiCollectionFromModelName(self.type)
            self.fields['reason'].label = _('Field(s) to edit')
            choices_dict = getattr(collection, 'suggest_edit_choices', {})
            self.fields['reason'].choices = listUnique(choices_dict.values())
            if (self.request and 'reason' in self.request.GET
                and self.request.GET['reason'] in choices_dict):
                self.fields['reason'].show_value_instead = choices_dict[self.request.GET['reason']][1]
                self.fields['reason'].initial = [choices_dict[self.request.GET['reason']][0]]
                self.fields['reason'].widget = self.fields['reason'].hidden_widget()
        if 'message' in self.fields:
            self.fields['message'].label = _('What should be edited?')

    def clean_reason(self):
        fields = self.cleaned_data['reason']
        return ', '.join(fields)

    def save(self, commit=True):
        instance = super(SuggestedEditForm, self).save(commit=False)
        instance.is_suggestededit = True
        return instance

class FilterReports(MagiFiltersForm):
    search_fields = ['owner__username', 'message', 'staff_message', 'reason', 'reported_thing_title']
    search_fields_labels = {
        'owner__username': _('Username'),
        'reported_thing_title': 'Name of the item',
    }
    ordering_fields = [
        ('i_status', 'Status'),
        ('creation', 'Creation'),
        ('modification', 'Last Update'),
    ]
    reported_thing = forms.ChoiceField(
        required=False,
        choices=[],
    )

    cuteform = {
        'i_status': { 'type': CuteFormType.HTML },
        'reported_thing': { 'type': CuteFormType.HTML },
    }

    reported_thing_filter = MagiFilter(to_value=lambda _model_name: (
        getMagiCollectionFromModelName(_model_name).name))

    def __init__(self, *args, **kwargs):
        super(FilterReports, self).__init__(*args, **kwargs)
        self.fields['reported_thing'].choices = BLANK_CHOICE_DASH + [ (name, info['title']) for name, info in self.collection.types.items() ]
        if self.collection.name == 'suggestededit':
            self.fields['reported_thing'].label = 'Item'
            permission = 'moderate_suggested_edits'
            self.fields['i_status'].choices = [
                (k, v) for k, v in self.fields['i_status'].choices
                if k != models.Report.get_i('status', 'Deleted')
            ]
        else:
            permission = 'moderate_reports'

    class Meta(MagiFiltersForm.Meta):
        model = models.Report
        fields = [
            'search', 'ordering', 'reverse_order',
            'i_status', 'reported_thing',
        ]

############################################################
# Donation Months forms

class DonateForm(AutoForm):
    def save(self, commit=True):
        instance = super(DonateForm, self).save(commit=False)
        instance.date = instance.date.replace(day=1)
        if commit:
            instance.save()
        return instance

    class Meta(AutoForm.Meta):
        model = models.DonationMonth
        fields = '__all__'
        tinypng_on_save = ('image',)
        save_owner_on_creation = True

############################################################
# Add/Edit Badges

class _BadgeForm(MagiForm):
    username = forms.CharField(max_length=32, label=_('Username'))

    def __init__(self, *args, **kwargs):
        super(_BadgeForm, self).__init__(*args, **kwargs)
        if not self.is_creating:
            self.fields['username'].initial = self.instance.user.username
            # this is set for after_save
            self.request._previous_show_on_top_profile = self.instance.show_on_profile

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            self.user = models.User.objects.get(username=username)
        except ObjectDoesNotExist:
            raise forms.ValidationError('Invalid username')
        return username

    def save(self, commit=True):
        instance = super(_BadgeForm, self).save(commit=False)
        instance.user = self.user
        if commit:
            instance.save()
        return instance

    class Meta(MagiForm.Meta):
        model = models.Badge
        save_owner_on_creation = True
        tinypng_on_save = ('image',)
        fields = '__all__'

class ExclusiveBadgeForm(_BadgeForm):
    def save(self, commit=True):
        instance = super(ExclusiveBadgeForm, self).save(commit=False)
        instance.show_on_profile = True
        instance.show_on_top_profile = False
        if commit:
            instance.save()
        return instance

    class Meta(_BadgeForm.Meta):
        required_fields = ('name',)
        fields = ('username', 'name', 'm_description', 'image', 'url', 'rank')

class CopyBadgeForm(_BadgeForm):
    def __init__(self, *args, **kwargs):
        super(CopyBadgeForm, self).__init__(*args, **kwargs)
        badge_id = self.request.GET.get('id', None)
        self.badge = get_object_or_404(models.Badge, pk=badge_id)
        if not self.is_creating or self.badge.type == 'donator':
            raise PermissionDenied()
        self.fields['name'].initial = self.badge.name
        self.fields['m_description'].initial = self.badge.m_description
        self.fields['rank'].initial = self.badge.rank
        self.fields['url'].initial = self.badge.url
        if not self.badge.url:
            del(self.fields['url'])

    def save(self, commit=True):
        instance = super(CopyBadgeForm, self).save(commit=False)
        instance.show_on_profile = True
        instance.show_on_top_profile = False
        instance.image = self.badge.image
        if instance.m_description == self.badge.m_description:
            instance._cache_description = self.badge._cache_description
        if commit:
            instance.save()
        return instance

    class Meta(_BadgeForm.Meta):
        required_fields = ('name',)
        fields = ('username', 'name', 'm_description', 'url', 'rank')

class DonatorBadgeForm(_BadgeForm):
    source = forms.ChoiceField(required=True, choices=[
        ('Patreon', 'Patreon'),
        ('PayPal', 'PayPal'),
        ('GratiPay', 'GratiPay'),
        # If you add more choices, make sure they don't contain any space.
    ])
    show_on_profile = forms.ChoiceField(required=True, choices=[
        ('True', t['Yes']),
        ('False', t['No']),
    ], label='Is the donation over $10?')
    is_special_offer = forms.BooleanField(required=False, label='Is it a special offer?', initial=False)

    def __init__(self, *args, **kwargs):
        super(DonatorBadgeForm, self).__init__(*args, **kwargs)
        self.fields['donation_month'].queryset = self.fields['donation_month'].queryset.order_by('-date')
        self.fields['donation_month'].required = True
        if not self.is_creating:
            self.fields['source'].initial = self.instance.donation_source

    def save(self, commit=True):
        instance = super(DonatorBadgeForm, self).save(commit=False)
        instance.date = instance.donation_month.date
        instance.image = instance.donation_month.image
        instance.name = None
        instance.m_description = self.cleaned_data['source']
        instance._cache_description = self.cleaned_data['source']
        instance.url = '/donate/'
        instance.show_on_top_profile = instance.show_on_profile
        if self.cleaned_data.get('is_special_offer', False):
            instance.show_on_profile = True
        if commit:
            instance.save()
        return instance

    class Meta(_BadgeForm.Meta):
        fields = ('username', 'donation_month', 'source', 'show_on_profile', 'is_special_offer', 'rank')

class FilterBadges(MagiFiltersForm):
    search_fields = ['user__username', 'name', 'm_description']
    search_fields_labels = {
        'user__username': _('Username'),
    }
    ordering_fields = [
        ('date', 'Date'),
        ('rank', 'Rank'),
    ]
    ordering_show_relevant_fields = {
        'rank': [],
    }

    added_by = forms.ModelChoiceField(label=_('Staff'), queryset=models.User.objects.filter(is_staff=True), )

    of_user = forms.IntegerField(widget=forms.HiddenInput)
    of_user_filter = MagiFilter(to_queryset=lambda form, queryset, request, value: queryset.filter(user_id=value, show_on_profile=True))

    class Meta(MagiFiltersForm.Meta):
        model = models.Badge
        fields = [
            'search', 'ordering', 'reverse_order',
            'rank', 'added_by', 'of_user',
        ]

############################################################
# Prizes form

class PrizeForm(AutoForm):
    class Meta(AutoForm.Meta):
        model = models.Prize
        fields = '__all__'
        save_owner_on_creation = True

class BasePrizeFilterForm(MagiFiltersForm):
    def __init__(self, *args, **kwargs):
        super(BasePrizeFilterForm, self).__init__(*args, **kwargs)
        if 'i_character' in self.fields:
            if not hasCharacters():
                del(self.fields['i_character'])
            else:
                self.fields['i_character'].label = getCharacterLabel()
                self.fields['i_character'].choices = BLANK_CHOICE_DASH + getCharactersChoices()

class PrizeFilterForm(BasePrizeFilterForm):
    search_fields = ['name', 'm_details']
    ordering_fields = [
        ('id', 'Creation'),
        ('value', 'Value'),
    ]

    has_giveaway = forms.NullBooleanField(label='Assigned to a giveaway or already given away', initial=False)
    has_giveaway_filter = MagiFilter(selector='giveaway_url__isnull')

    class Meta:
        model = models.Prize
        fields = [
            'search', 'ordering', 'reverse_order',
            'has_giveaway', 'i_character',
        ]

class PrizeViewingFilterForm(BasePrizeFilterForm):
    max_value = forms.IntegerField(widget=forms.HiddenInput)
    max_value_filter = MagiFilter(selector='value__lte', multiple=False)

    min_value = forms.IntegerField(widget=forms.HiddenInput)
    min_value_filter = MagiFilter(selector='value__gt', multiple=False)

    presets = OrderedDict([
        ('tier1', { 'fields': { 'min_value': 0, 'max_value': 5 }, 'verbose_name': 'tier 1' }),
        ('tier2', { 'fields': { 'min_value': 5, 'max_value': 10 }, 'verbose_name': 'tier 2' }),
        ('tier3', { 'fields': { 'min_value': 10, 'max_value': 15 }, 'verbose_name': 'tier 3' }),
        ('tier4', { 'fields': { 'min_value': 15 }, 'verbose_name': 'tier 4' }),
        ('tier1-2', { 'fields': { 'max_value': 10 }, 'verbose_name': 'tier 1 and 2' }),
        ('tier1-3', { 'fields': { 'max_value': 15 }, 'verbose_name': 'tier 1, 2 and 3' }),
        ('tier1-4', { 'fields': { }, 'verbose_name': 'tier 1 to 4' }),
    ])
    show_presets_in_navbar = False

    class Meta:
        model = models.Prize
        fields = ['i_character']

############################################################
# Private Message form

class PrivateMessageForm(MagiForm):
    def __init__(self, *args, **kwargs):
        super(PrivateMessageForm, self).__init__(*args, **kwargs)
        self.fields['to_user'].initial = (
            self.request.GET.get('to_user', None)
            if self.request else None)
        self.fields['message'].validators.append(MinLengthValidator(2))

    class Meta(MagiForm.Meta):
        model = models.PrivateMessage
        fields = ('to_user', 'message', )
        hidden_foreign_keys = ('to_user', )
        save_owner_on_creation = True

class PrivateMessageFilterForm(MagiFiltersForm):
    search_fields = ['message', 'to_user__username', 'owner__username']
    search_fields_labels = {
        'to_user__username': _('Username'),
        'owner__username': '',
    }

    to_user_filter = MagiFilter(to_queryset=(
        lambda form, queryset, request, value: queryset.filter(
            Q(owner_id=request.user.id, to_user_id=value)
            | Q(owner_id=value, to_user_id=request.user.id)
        )
    ))

    class Meta(MagiForm.Meta):
        model = models.PrivateMessage
        fields = ('to_user', )
        hidden_foreign_keys = ('to_user', )

############################################################
############################################################
############################################################
# Abstract collections

############################################################
# Base model with versions

def to_ModelWithVersionsForm(cls):
    class _ModelWithVersionsForm(AutoForm):
        # Show/hide versions fields details when versions are selected
        if modelHasField(cls.queryset.model, 'c_versions'):
            on_change_value_show = {
                'c_versions': cls.queryset.model.ALL_FIELDS_BY_VERSION,
            }

        class Meta(AutoForm.Meta):
            model = cls.queryset.model
    return _ModelWithVersionsForm

def to_ModelWithVersionsFilterForm(cls):
    form_class = to_auto_filter_form(cls)
    model_class = cls.collection.queryset.model
    form_class.Meta.with_versions = cls.collection.with_versions

    class _ModelWithVersionsFilterForm(form_class):
        # Filter by status
        def _status_to_queryset(self, queryset, request, value):
            if self.Meta.with_versions:
                if not self.data.get('version'):
                    return queryset
                return filterEventsByStatus(
                    queryset, value, prefix=model_class.VERSIONS[
                        self.data.get('version')]['prefix'])
            return filterEventsByStatus(queryset, value)

        cuteform = getattr(form_class, 'cuteform', {})

        if modelHasField(model_class, 'start_date') and modelHasField(model_class, 'end_date'):
            status = forms.ChoiceField(label=_('Status'), choices=[
                ('ended', _('Past')),
                ('current', _('Current')),
                ('future', _('Future')),
            ])
            status_filter = MagiFilter(to_queryset=_status_to_queryset)
            cuteform['status'] = {
                'type': CuteFormType.HTML,
            }

        # Versions
        if form_class.Meta.with_versions:

            # Add generic date field as first (default ordering option)
            ordering_fields = ([
                ('start_date', _('Date')),
            ] if modelHasField(model_class, 'start_date') else [
            ]) + getattr(form_class, 'ordering_fields', [])

            def filter_queryset(self, queryset, parameters, request, *args, **kwargs):
                queryset = super(_ModelWithVersionsFilterForm, self).filter_queryset(
                    queryset, parameters, request, *args, **kwargs)
                if (modelHasField(queryset.model, 'start_date')
                    and parameters.get('ordering', 'start_date') == 'start_date'):
                    queryset = sortByRelevantVersions(
                        queryset,
                        request=self.request, fallback_to_first=True,
                        versions=model_class.VERSIONS,
                    )
                return queryset

            presets = OrderedDict([
                (_version_name, {
                    'fields': { 'version': _version_name },
                    'verbose_name': _version['translation'],
                    'image': model_class.get_version_image(_version_name),
                }) for _version_name, _version in model_class.VERSIONS.items()
            ])

            # Filter by version
            # Note: c_versions allows multiple with a checkbox, we want just one at a time with a cuteform

            def version_to_queryset(self, queryset, request, value):
                if request and request.GET.get('version_exclusive', False):
                    return queryset.filter(c_versions=u'"{}"'.format(value))
                return queryset.filter(c_versions__contains=u'"{}"'.format(value))

            version = forms.ChoiceField(label=_(u'Server availability'), choices=model_class.VERSIONS_CHOICES)
            version_filter = MagiFilter(to_queryset=version_to_queryset)

            version_exclusive = forms.BooleanField(label=_('Exclusive'))
            version_exclusive_filter = MagiFilter(noop=True)

            if model_class.VERSIONS_HAVE_IMAGES:
                cuteform['version'] = {
                    'transform': CuteFormTransform.ImagePath,
                    'image_folder': '',
                    'to_cuteform': lambda _key, _value: model_class.get_version_image(_key),
                }
            elif model_class.VERSIONS_HAVE_ICONS:
                cuteform['version'] = {
                    'transform': CuteFormTransform.Flaticon,
                    'to_cuteform': lambda _key, _value: model_class.get_version_icon(_key),
                }

            # Show/hide status filter to show up only when filtering by version
            on_change_value_show = getattr(form_class, 'on_change_value_show', {})
            on_change_value_show['version'] = [ 'version_exclusive', 'status' ]

        class Meta(form_class.Meta):
            if form_class.Meta.with_versions:
                hidden_fields = getattr(form_class.Meta, 'hidden_fields', []) + ['c_versions']
                fields = form_class.Meta.fields + (
                    ['version'] if modelHasField(model_class, 'c_versions') else []
                ) + (
                    ['status']
                    if modelHasField(model_class, 'start_date') and modelHasField(model_class, 'end_date')
                    else []
                )

    return _ModelWithVersionsFilterForm

############################################################
# Event

def to_EventForm(cls):
    return to_ModelWithVersionsForm(cls)

def to_EventFilterForm(cls):
    return to_ModelWithVersionsFilterForm(cls)
