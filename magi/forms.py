import re, datetime
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from multiupload.fields import MultiFileField
from snowpenguin.django.recaptcha3.widgets import ReCaptchaHiddenInput as _ReCaptchaHiddenInput
from snowpenguin.django.recaptcha3.fields import ReCaptchaField as _ReCaptchaField
from django import forms
from django.core.validators import MaxLengthValidator, MaxValueValidator
from django.http.request import QueryDict
from django.db import models as django_models
from django.db.models.fields import BLANK_CHOICE_DASH, FieldDoesNotExist, TextField, CharField
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
    FAVORITE_CHARACTERS,
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
    TRANSLATION_HELP_URL,
    PROFILE_BACKGROUNDS_NAMES,
    MAX_LEVEL,
    GOOD_REPUTATION_THRESHOLD,
)
from magi.utils import (
    addParametersToURL,
    randomString,
    shrinkImageFromData,
    imageThumbnailFromData,
    getMagiCollection,
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
    getFavoriteCharacterChoices,
    FilterByMode,
    filterByTranslatedValue,
    FormShowMore,
)

############################################################
# Internal utils

class MultiImageField(MultiFileField, forms.ImageField):
    pass

class DateInput(forms.DateInput):
    input_type = 'date'

def date_input(field, value=None):
    field = forms.DateField(
        label=field.label,
        required=field.required,
        initial=field.initial,
        validators=field.validators,
    )
    field.widget = DateInput()
    field.widget.attrs.update({
        'class': 'calendar-widget',
        'data-role': 'data',
    })
    if not any([isinstance(validator, MinValueValidator) for validator in field.validators]):
        field.validators += [
            MinValueValidator(datetime.date(1900, 1, 2)),
        ]
    field.help_text = 'yyyy-mm-dd'
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
    for language in queryset.model.get_field_translation_sources(field_name):
        if limit_sources_to and language not in limit_sources_to:
            continue
        if language in exclude_sources:
            continue
        if language == 'en':
            queryset = queryset.filter(**{ u'{}__isnull'.format(field_name): False,
            }).exclude(**{ field_name: '' })
        else:
            long_source_field_name = u'{}_{}'.format(LANGUAGES_NAMES.get(language, None), field_name)
            short_source_field_name = u'{}_{}'.format(language, field_name)
            if has_field(queryset.model, long_source_field_name):
                queryset = queryset.filter(**{ u'{}__isnull'.format(long_source_field_name): False,
                }).exclude(**{ long_source_field_name: '' })
            elif has_field(queryset.model, short_source_field_name):
                queryset = queryset.filter(**{ u'{}__isnull'.format(short_source_field_name): False,
                }).exclude(**{ short_source_field_name: '' })
            else: # dict
                queryset = queryset.filter(**{
                    u'd_{}s__contains'.format(field_name): u'"{}"'.format(language) })
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

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.collection = kwargs.pop('collection', None)
        self.form_type = kwargs.pop('type', None)
        self.ajax = kwargs.pop('ajax', False)
        self.allow_next = kwargs.pop('allow_next', False)
        super(MagiForm, self).__init__(*args, **kwargs)
        self.is_creating = not hasattr(self, 'instance') or not self.instance.pk
        self.c_choices = []
        self.d_choices = {}
        self.date_fields = []
        self.m_previous_values = {}
        self.keep_underscore_fields = []
        self.force_tinypng_on_save = []
        self.generate_thumbnails_for = []

        # If is creating and item is unique per owner, redirect to edit unique
        if self.is_creating and self.collection and not isinstance(self, MagiFiltersForm) and not self.Meta.model.fk_as_owner and self.collection.add_view.unique_per_owner:
            existing = self.collection.edit_view.get_queryset(self.collection.queryset, {}, self.request).filter(**self.collection.edit_view.get_item(self.request, 'unique'))
            try: raise HttpRedirectException(existing[0].ajax_edit_url if self.ajax else existing[0].edit_url) # Redirect to edit
            except IndexError: pass # Can add!

        # Hidden foreign keys fields
        if hasattr(self.Meta, 'hidden_foreign_keys'):
            for field in self.Meta.hidden_foreign_keys:
                if field in self.fields:
                    self.fields[field] = HiddenModelChoiceField(
                        queryset=self.fields[field].queryset,
                        widget=forms.HiddenInput,
                        initial=(None if self.is_creating else getattr(self.instance, u'{}_id'.format(field))),
                    )
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

        # When next is allowed, add next fields
        if self.request and self.allow_next:
            if 'next' not in self.fields:
                self.fields['next'] = forms.CharField(
                    required=False, widget=forms.HiddenInput(),
                    initial=self.request.GET.get('next', None))
            if 'next_title' not in self.fields:
                self.fields['next_title'] = forms.CharField(
                    required=False, widget=forms.HiddenInput(),
                    initial=self.request.GET.get('next_title', None))

        for name, field in self.fields.items():
            # Fix optional fields using null=True
            try:
                model_field = self.Meta.model._meta.get_field(name)
            except FieldDoesNotExist:
                model_field = None
            if model_field is not None and model_field.null:
                self.fields[name].required = False

            # Set initial value from GET
            if allow_initial_in_get == '__all__' or name in allow_initial_in_get:
                value = self.request.GET.get(name, None)
                if value:
                    field.initial = value
                    field.widget = field.hidden_widget()
                    field.show_value_instead = (
                        { unicode(k): v for k, v in dict(field.choices).items() }[value]
                        if isinstance(field, forms.ChoiceField)
                        else value
                    )

            # Show languages on translatable fields
            if self.collection and self.collection.translated_fields and name in self.collection.translated_fields:
                choices = getattr(self.Meta.model, u'{name}S_CHOICES'.format(name=name.upper()), [])
                self.fields[name].below_field = mark_safe(
                    u'<div class="text-right"><i class="flaticon-translate text-muted"></i> {}</div>'.format(
                        u' '.join([
                            u'<a href="{url}"><img src="{image}" alt="{language}" height="15"></a>'.format(
                                language=language,
                                image=staticImageURL(language, folder='language', extension='png'),
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
                    )
                )
            # Fix dates fields
            if (not name.startswith('_cache_')
                and (isinstance(field, forms.DateField)
                     or isinstance(field, forms.DateTimeField)
                     or name in getattr(self.Meta, 'date_fields', []))):
                self.fields[name], value = date_input(field, value=(getattr(self.instance, name, None) if not self.is_creating else None))
                self.date_fields.append(name)
                if value:
                    setattr(self.instance, name, value)
            # Make CSV values with choices use a CheckboxSelectMultiple widget
            elif name.startswith('c_'):
                choices = getattr(self.Meta.model, '{name}_CHOICES'.format(name=name[2:].upper()), None)
                if choices is not None:
                    self.c_choices.append(name)
                    if not choices:
                        self.fields.pop(name)
                    else:
                        self.fields[name] = forms.MultipleChoiceField(
                            required=False,
                            widget=forms.CheckboxSelectMultiple,
                            choices=[(c[0], c[1]) if isinstance(c, tuple) else (c, c) for c in choices],
                            label=field.label,
                        )
                        if not self.is_creating:
                            # Set the value in the object to the list to pre-select the right options
                            setattr(self.instance, name, getattr(self.instance, name[2:]))
            # Add fields for d_ dict choices
            elif name.startswith('d_') and not isinstance(self, MagiFiltersForm):
                choices = getattr(self.Meta.model, u'{name}_CHOICES'.format(name=name[2:].upper()), None)
                if choices is not None:
                    if (not self.collection
                        or not self.collection.translated_fields
                        or name[2:-1] not in self.collection.translated_fields
                        or getattr(self, 'is_translate_form', False)):
                        self.d_choices[name[2:]] = []
                        for choice in (choices.items() if isinstance(choices, dict) else choices):
                            key = choice[0] if isinstance(choice, tuple) else choice
                            verbose_name = choice[1] if isinstance(choice, tuple) else choice
                            verbose_name = verbose_name() if callable(verbose_name) else verbose_name
                            field_name = u'{}-{}'.format(name, key)
                            self.d_choices[name[2:]].append((field_name, key))

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
                                help_text = mark_safe(u'{original}{key}'.format(
                                    original=u'{}<br>'.format(self.fields[name].help_text) if self.fields[name].help_text else '',
                                    key=verbose_name,
                                ))
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
                    del(self.fields[name])
            # Make fields with soft choices use a ChoiceField
            elif getattr(self.Meta.model, u'{name}_SOFT_CHOICES'.format(name=name[2:].upper()), False):
                choices = getattr(self.Meta.model, '{name}_CHOICES'.format(name=name[2:].upper()), None)
                without_i = getattr(self.Meta.model, '{name}_WITHOUT_I_CHOICES'.format(name=name[2:].upper()), None)
                if choices is not None:
                    self.fields[name] = forms.ChoiceField(
                        required=field.required,
                        choices=[
                            (c[0] if without_i else i, c[1]) if isinstance(c, tuple) else (c, c)
                            for i, c in enumerate(choices)
                        ],
                        label=field.label,
                    )
            # Save previous values of markdown fields and set label
            elif name.startswith('m_') and not isinstance(self, MagiFiltersForm):
                if not self.is_creating:
                    self.m_previous_values[name] = getattr(self.instance, name)
                self.fields[name].help_text = mark_safe(u'<br>'.join([
                    getattr(self.fields[name], 'help_text', ''),
                    unicode(markdownHelpText(request=self.request)),
                ]))

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
                        self.fields[name].form_group_classes = ['staff-only']
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
                    self.fields[name].form_group_classes = ['staff-only']


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

        # Has the form been opened in the context of a report?
        self.is_reported = (
            not self.is_creating
            and not isinstance(self, MagiFiltersForm)
            and self.request
            and 'is_reported' in self.request.GET
            and self.request.user.is_authenticated()
            and self.instance.owner != self.request.user
        )

        # Add buttons to add/edit sub items
        if (not self.is_reported
            and not getattr(self, 'is_translate_form', False)
            and self.collection
            and getattr(self.collection, 'sub_collections', None)
        ):
            self.sub_collections = []
            for sub_collection in getattr(self.collection, 'sub_collections', None).values():
                if sub_collection.main_many2many:
                    if sub_collection.main_related in self.fields:
                        self.fields[sub_collection.main_related].below_field = mark_safe(u"""
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
            and self.request and owner.is_authenticated()):
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

        # Save datetime times
        times = getattr(self.Meta, 'date_times', {})
        if times:
            for field_name in self.date_fields:
                if field_name in times and getattr(instance, field_name, None):
                    setattr(
                        instance, field_name,
                        getattr(instance, field_name).replace(
                            hour=times[field_name][0], minute=times[field_name][1]))
        # Save d_ dict choices
        for dfield, choices in self.d_choices.items():
            d = {}
            for field, key in choices:
                if (self.cleaned_data[field]
                    or key in getattr(self.Meta, 'd_save_falsy_values_for_keys', {}).get(dfield, [])):
                    d[key] = self.cleaned_data[field]
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
                            settings=getattr(instance._meta.model, 'tinypng_settings', {}).get(field, {}),
                        )

                    if image_data is not None:
                        image.name = instance._meta.model._meta.get_field(field).upload_to(instance, filename)
                        setattr(instance, field, image_data)
                    else:
                        # Remove any cached processed image
                        setattr(instance, u'_tthumbnail_{}'.format(field), None)
                        setattr(instance, u'_thumbnail_{}'.format(field), None)
                        setattr(instance, u'_original_{}'.format(field), None)
                        setattr(instance, u'_2x_{}'.format(field), None)

        # Save CSV values
        for field in self.c_choices:
            instance.save_c(field[2:], self.cleaned_data.get(field, getattr(instance, field)))
        if commit:
            instance.save()
        return instance

    def _transform_on_change_value(self, values):
        def _get_i(field_name, value):
            if not isinstance(value, int):
                try: return self.Meta.model.get_i(field_name[2:], value)
                except (FieldDoesNotExist, KeyError): pass
            return value
        return OrderedDict([
            (
                (field_name, fields)
                if not field_name.startswith('i_') or not isinstance(fields, dict)
                else (field_name, {
                        _get_i(field_name, value): value_fields
                        for value, value_fields in fields.items()
                })
            ) for field_name, fields in values.items()
        ])

    def get_on_change_value_show(self):
        on_change_value_show = getattr(self, 'on_change_value_show', None)
        if not on_change_value_show:
            return None
        return self._transform_on_change_value(on_change_value_show)

    def get_on_change_value_trigger(self):
        on_change_value_trigger = getattr(self, 'on_change_value_trigger', None)
        if not on_change_value_trigger:
            return None
        return self._transform_on_change_value(on_change_value_trigger)

    def reorder_fields(self, order):
        """
        Reorder form fields by order.
        Fields not in order will be placed at the end.

        >>> reorder_fields(
        ...     OrderedDict([('a', 1), ('b', 2), ('c', 3)]),
        ...     ['b', 'c', 'a'])
        OrderedDict([('b', 2), ('c', 3), ('a', 1)])
        """
        self.fields = OrderedDict(sorted(
            self.fields.items(),
            key=lambda k: order.index(k[0]) if k[0] in order else 9999999,
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

        def _get_verbose_language(self, language):
            return LANGUAGES_NAMES.get(language, language).replace('_', ' ').title()

        def _language_help_text(self, language, verbose_language, field_name, sources):
            formatted_sources = [
                u' <span class="label label-info">{language}</span> {value}'.format(
                    language=self._get_verbose_language(source_language),
                    value=(
                        u'<pre style="white-space: pre-line;">{}</pre>'.format(value)
                        if field_name.startswith('d_m_')
                        else value
                    ),
                ) for source_language, value in sources.items()
                if value and language != source_language
            ]
            original_help_text = self.fields[field_name].help_text.replace(unicode(verbose_language), '').strip()
            self.fields[field_name].help_text = mark_safe(
                u'{is_source}{no_value}{original}{sources}<img src="{img}" height="20" /> {lang}'.format(
                    is_source=(
                        u'<span class="label label-info pull-right">Source</span>'
                        if language in sources else ''
                    ),
                    no_value=(
                        u'<span class="label label-danger pull-right">No value</span>'
                        if not formatted_sources and language not in sources else ''
                    ),
                    original=(
                        u'{}<br>'.format(original_help_text)
                        if original_help_text
                        else ''
                    ),
                    img=staticImageURL(language, folder='language', extension='png'),
                    lang=verbose_language,
                    sources=(
                        u'<div class="alert alert-info">{}</div>'.format(
                            u'<br>'.join(formatted_sources)
                        ) if formatted_sources else ''
                    ),
                ))
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
                        field_name, language=language, fallback_to_english=False) or None)
                    for language in source_languages
                ])

                # Add a language help text on top of each field
                # with the list of sources + "Source" + "No value"
                self._language_help_text('en', t['English'], field_name, sources)
                for language, verbose_language in getattr(self.Meta.model, u'{name}S_CHOICES'.format(
                        name=field_name.upper()), []):
                    destination_field_name = u'd_{}s-{}'.format(field_name, language)
                    if destination_field_name in self.fields:
                        self._language_help_text(language, verbose_language, destination_field_name, sources)
                for language, fields in self.Meta.external_translation_fields.items():
                    if field_name in fields:
                        verbose_language = self._get_verbose_language(language)
                        self._language_help_text(language, verbose_language, fields[field_name], sources)

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
                    ) for language, verbose_language in django_settings.LANGUAGES
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

def filter_ids(queryset, request):
    if 'ids' in request.GET and request.GET['ids'] and request.GET['ids'].replace(',', '').isdigit():
        queryset = queryset.filter(pk__in=request.GET['ids'].split(','))
    return queryset

class MagiFiltersForm(AutoForm):
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
                        mode=FilterByMode.Contains,
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
                        mode=FilterByMode.Exact,
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
            return get_missing_translations(queryset, field_name, value.split(','))
        return _to_missing_translation

    presets = {}
    show_presets_in_navbar = True

    _internal_presets = {}
    @classmethod
    def get_presets(self):
        if not self._internal_presets and self.presets:
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
        return { k: unicode(v) for k, v in details['fields'].items() }

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

    def __init__(self, *args, **kwargs):
        self.preset = kwargs.pop('preset', None)
        super(MagiFiltersForm, self).__init__(*args, **kwargs)
        self.empty_permitted = True

        # Set action when using a preset

        if self.preset and self.collection:
            try:
                self.action_url = self.collection.get_list_url()
            except AttributeError:
                pass

        # Add/delete fields

        # Collectible
        if self.collection and self.request.user.is_authenticated():
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
                if collection.add_view.enabled:
                    # Add added_{} for fields that are collectible
                    field_name = u'added_{}'.format(collection_name)
                    if field_name in self.request.GET:
                        parent_item_name = self.collection.queryset.model.__name__.lower()
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
        if self.collection and self.request.user.is_authenticated() and self.allow_translate and self.collection.translated_fields:
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
            self.fields['owner'] = forms.CharField(widget=forms.HiddenInput)

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
                    if self.request.LANGUAGE_CODE not in type(self).search_field_help_text:
                        type(self).search_field_help_text[self.request.LANGUAGE_CODE] = getSearchFieldHelpText(
                            search_fields=(
                                list(getattr(self, 'search_fields', []))
                                + list(getattr(self, 'search_fields_exact', []))
                            ),
                            model_class=self.Meta.model,
                            labels=getattr(self, 'search_fields_labels', {}),
                            translated_fields=(self.collection.translated_fields if self.collection else []) or [],
                        )
                    if type(self).search_field_help_text[self.request.LANGUAGE_CODE]:
                        self.fields['search'].help_text = type(self).search_field_help_text[self.request.LANGUAGE_CODE]

        # Remove ordering form field if ordering_fields is not specified
        if not getattr(self, 'ordering_fields', None):
            if 'ordering' in self.fields:
                del(self.fields['ordering'])
            if 'reverse_order' in self.fields:
                del(self.fields['reverse_order'])

        fields_order = self.fields.keys()
        order_changed = False

        # Modify fields

        # Merge filters
        if getattr(self, 'merge_fields', None):
            def _get_merged_field_to_queryset(fields):
                def _merged_field_to_queryset(form, queryset, request, value):
                    for field_name, field_details in fields:
                        if value.startswith(field_name):
                            return self._filter_queryset_for_field(
                                field_name, queryset, request,
                                value=[value[len(field_name) + 1:]],
                                filter=field_details.get(
                                    'filter', getattr(self, u'{}_filter'.format(field_name), None)),
                            )
                    return queryset
                return _merged_field_to_queryset
            for new_field_name, fields in (
                    self.merge_fields.items()
                    if isinstance(self.merge_fields, dict)
                    else [('_'.join(fields.keys() if isinstance(fields, dict) else fields), fields)
                          for fields in self.merge_fields]
            ):
                if 'fields' in fields:
                    details = fields
                    fields = details['fields']
                else:
                    details = {}
                choices = BLANK_CHOICE_DASH[:]
                label_parts = []
                met_first_field = False
                for field_name, field_details in (
                        fields.items()
                        if isinstance(fields, dict)
                        else [(field, {}) for field in fields]
                ):
                    if field_name in self.fields:
                        self.fields[field_name].widget = self.fields[field_name].hidden_widget()
                        if not met_first_field:
                            fields_order = [
                                (new_field_name if key == field_name
                                 else key) for key in fields_order
                            ]
                            met_first_field = True
                            order_changed = True
                    field_choices = (
                        field_details.get('choices', None)
                        or getattr(self.fields.get(field_name, None), 'choices', None)
                        or self.Meta.model.get_choices(field_name)
                    )
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
                            field_label = self.Meta.model._meta.get_field(field_name).verbose_name
                        except FieldDoesNotExist:
                            field_label = toHumanReadable(field_name)
                    label_parts.append(unicode(field_label))
                self.fields[new_field_name] = forms.ChoiceField(
                    choices=choices,
                    label=details.get('label', u' / '.join(label_parts)),
                )
                setattr(self, u'{}_filter'.format(new_field_name), MagiFilter(
                    to_queryset=_get_merged_field_to_queryset(
                        fields.items()
                        if isinstance(fields, dict)
                        else [(field, {}) for field in fields]
                    )))

        # Set default ordering initial value
        if 'ordering' in self.fields:
            initial = ','.join(self.collection.list_view.plain_default_ordering_list)
            if initial not in dict(self.ordering_fields):
                self.ordering_fields = [(initial, _('Default'))] + self.ordering_fields
            self.fields['ordering'].choices = [
                (k, v() if callable(v) else v)
                for k, v in self.ordering_fields
            ]
            if self.collection:
                self.fields['ordering'].initial = initial
                self.fields['reverse_order'].initial = self.collection.list_view.default_ordering.startswith('-')

        # Set view selector
        if ('view' in self.fields
            and self.collection
            and self.collection.list_view.alt_views):
            if not self.collection.list_view._alt_view_choices:
                self.collection.list_view._alt_view_choices = [('', self.collection.plural_title)] + [
                    (view_name, view.get('verbose_name', view_name))
                    for view_name, view in self.collection.list_view.alt_views
                ]
            if not [_v for _v in self.collection.list_view.alt_views or []
                    if not _v[1].get('hide_in_filter', False) and _v[1].get('hide_in_navbar', False)]: # None visible
                self.fields['view'].widget = self.fields['view'].hidden_widget()
            self.fields['view'].choices = self.collection.list_view._alt_view_choices
        else:
            del(self.fields['view'])

        if getattr(self.Meta, 'all_optional', True):
            for field_name, field in self.fields.items():
                # Add blank choice to list of choices that don't have one
                if (isinstance(field, forms.fields.ChoiceField)
                    and not isinstance(field, forms.fields.MultipleChoiceField)
                    and field.choices
                    and field_name != 'ordering'
                    and not field_name.startswith('add_to_')):
                    choices = list(self.fields[field_name].choices)
                    if choices and choices[0][0] != '':
                        self.fields[field_name].choices = BLANK_CHOICE_DASH + choices
                        self.fields[field_name].initial = ''
                # Marks all fields as not required
                field.required = False

        # Set default values from GET form
        for field_name in GET_PARAMETERS_IN_FORM_HANDLED_OUTSIDE:
            if field_name in self.fields and self.request.GET.get(field_name, None):
                # Check for valid ordering choices, bypass when has permission
                if (field_name == 'ordering'
                    and not (self.request.user.is_authenticated()
                             and self.request.user.hasPermission('order_by_any_field'))
                    and self.request.GET[field_name] not in dict(self.fields[field_name].choices)):
                    continue
                self.fields[field_name].initial = self.request.GET[field_name]

        # Reorder if needed
        if order_changed:
            self.reorder_fields(fields_order)

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
                selectors = filter.selectors if filter.selectors else [field_name]
                condition = Q()
                filters, exclude = {}, {}
                for selector in selectors:
                    # NullBooleanField
                    if isinstance(field, forms.fields.NullBooleanField):
                        value = self._value_as_nullbool(filter, value)
                        if value is not None:
                            filters[selector] = value
                            # Special case for __isnull selectors
                            if selector.endswith('__isnull') and not filter.to_value:
                                filters[selector] = value = not value
                                original_selector = selector[:(-1 * len('__isnull'))]
                                # Get what corresponds to an empty value
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
                                    if value: # Also include empty values
                                        condition = condition | Q(**{ original_selector: empty_value })
                                    else: # Exclude empty values
                                        # need to check if int then 0 else ''
                                        exclude = { original_selector: empty_value }
                    # MultipleChoiceField
                    elif (isinstance(field, forms.fields.MultipleChoiceField)
                          or filter.multiple):
                        values = value if isinstance(value, list) else [value]
                        if field_name.startswith('c_'):
                            values = [u'"{}"'.format(value) for value in values]
                        if operator_for_multiple == MagiFilterOperator.OrContains:
                            for value in values:
                                condition = condition | Q(**{ u'{}__contains'.format(selector): value })
                        elif operator_for_multiple == MagiFilterOperator.OrExact:
                            filters = { u'{}__in'.format(selector): values }
                        elif operator_for_multiple == MagiFilterOperator.And:
                            for value in values:
                                condition = condition & Q(**{ u'{}__contains'.format(selector): value })
                        else:
                            raise NotImplementedError('Unknown operator for multiple condition')
                    # Generic
                    else:
                        filters = { selector: self._value_as_string(filter, value) }
                    # Add filters to condition based on operator for selectors
                    if operator_for_multiple_selectors == MagiFilterOperatorSelector.Or:
                        condition = condition | Q(**filters)
                    else:
                        condition = condition & Q(**filters)
                queryset = queryset.filter(condition).exclude(**exclude)
                if filter.distinct:
                    queryset = queryset.distinct()
        return queryset

    def filter_queryset(self, queryset, parameters, request):
        # Generic filter for ids
        queryset = filter_ids(queryset, request)
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
                if parameters[field_name] != '':
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
        if value == '2' or value == True:
            return True
        elif value == '3' or value == False:
            return False
        return None

    def _value_as_nullbool(self, filter, value):
        new_value = self.to_nullbool(value)
        return filter.to_value(new_value) if filter.to_value else new_value

    def _value_as_list(self, filter, parameters, field_name, allow_csv=True):
        if isinstance(parameters, QueryDict):
            value = parameters.getlist(field_name)
            if allow_csv and len(value) == 1:
                value = value[0].split(',')
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
    for field_name in list_view.collection.queryset.model._meta.get_all_field_names():
        if field_name.startswith('_'):
            continue
        try:
            field = list_view.collection.queryset.model._meta.get_field(field_name)
        except FieldDoesNotExist: # ManyToMany and reverse relations
            continue
        if (isinstance(field, django_models.CharField)
            or isinstance(field, django_models.TextField)):
            auto_search_fields.append(field_name)

        if (not field_name.startswith('i_')
              and (('name' in field_name and not field_name.startswith('d_'))
                   or isinstance(field, django_models.IntegerField)
                   or isinstance(field, django_models.FloatField)
                   or isinstance(field, django_models.AutoField)
                   or isinstance(field, django_models.DateField)
              )):
            auto_ordering_fields.append((field_name, field.verbose_name))

        if (field_name.startswith('i_')
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
            self.cuteform = {}
            for field_name in filter_fields:
                if field_name in self.fields and isinstance(self.fields[field_name], forms.BooleanField):
                    self.cuteform[field_name] = {
                        'type': CuteFormType.YesNo,
                    }
                    self.fields[field_name] = forms.NullBooleanField(
                        required=False, initial=None,
                        label=self.fields[field_name].label,
                    )

        class Meta(MagiFiltersForm.Meta):
            model = list_view.collection.queryset.model
            fields = ([
                'search'
            ] if auto_search_fields else []) + (
                filter_fields
            ) + ([
                'ordering', 'reverse_order'
            ] if auto_ordering_fields else [])

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
        if self.is_creating and 'nickname' in self.fields:
            if len(getAccountIdsFromSession(self.request)) == 0:
                self.fields['nickname'].widget = self.fields['nickname'].hidden_widget()
        if 'default_tab' in self.fields:
            if not self.collection or not hasattr(self.collection, 'get_profile_account_tabs'):
                del(self.fields['default_tab'])
            else:
                self.fields['default_tab'] = forms.ChoiceField(
                    required=False,
                    label=_('Default tab'),
                    initial=FIRST_COLLECTION,
                    choices=BLANK_CHOICE_DASH + [
                        (tab_name, tab['name'])
                        for tab_name, tab in
                        self.collection.get_profile_account_tabs(
                            self.request,
                            RAW_CONTEXT,
                            self.instance if not self.is_creating else None,
                        ).items()
                    ],
                )
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

    def clean_screenshot(self):
        new_level = self.cleaned_data.get('level')
        screenshot_image = self.cleaned_data.get('screenshot') or ''
        previous_level = 0
        if not self.is_creating:
            previous_level = getattr(self.instance, 'level_on_screenshot_upload', self.previous_level) or 0
        is_playground = self.instance.is_playground if not self.is_creating else False
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
        return screenshot_image

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
        'owner__username': t['Username'],
        'owner__links__value': _('Links'),
        'owner__email': _('Email'),
    }

    ordering_fields = [
        ('level', _('Level')),
        ('owner__username', t['Username']),
        ('creation', _('Join Date')),
        ('start_date', _('Start Date')),
        ('owner__preferences___cache_reputation', _('Most popular')),
    ]

    on_change_value_show = {
        'has_friend_id': {
            True: ['friend_id', 'accept_friend_requests'],
        },
    }
    show_more = FormShowMore(cutoff='i_os', including_cutoff=True, until='ordering')

    if has_field(models.Account, 'friend_id'):
        has_friend_id = forms.NullBooleanField(
            required=False, initial=None,
            label=models.Account._meta.get_field('friend_id').verbose_name,
        )
        has_friend_id_filter = MagiFilter(selector='friend_id__isnull')

    favorite_character = forms.ChoiceField(choices=BLANK_CHOICE_DASH + getFavoriteCharacterChoices(), required=False)
    favorite_character_filter = MagiFilter(selectors=[
        'owner__preferences__favorite_character{}'.format(i) for i in range(1, 4)])

    if USER_COLORS:
        color = forms.ChoiceField(label=_('Color'), choices=BLANK_CHOICE_DASH + [
            (_color_name, _color_verbose_name)
            for (_color_name, _color_verbose_name, _color_css, _color_hex) in USER_COLORS
        ])
        color_filter = MagiFilter(selector='owner__preferences__color')

    def __init__(self, *args, **kwargs):
        super(AccountFilterForm, self).__init__(*args, **kwargs)
        # Remove favorite character and color if users list is in navbar
        user_collection = getMagiCollection('user')
        if user_collection and user_collection.navbar_link:
            for field_name in ['favorite_character', 'color']:
                if field_name in self.fields:
                    del(self.fields[field_name])
        if 'favorite_character' in self.fields:
            self.fields['favorite_character'].choices = BLANK_CHOICE_DASH + getFavoriteCharacterChoices()
            self.fields['favorite_character'].label = models.UserPreferences.favorite_character_label()
        if 'friend_id' in self.fields:
            self.fields['friend_id'].widget.attrs['placeholder'] = _('Optional')

    class Meta(MagiFiltersForm.Meta):
        model = models.Account
        top_fields = ['search'] + (
            (['has_friend_id', 'friend_id']
             + ['accept_friend_requests'] if has_field(models.Account, 'accept_friend_requests') else [])
            if has_field(models.Account, 'friend_id') else []
        )
        middle_fields = ['favorite_character'] + (
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
        # If another user uses this email address
        if (models.User.objects.filter(email__iexact=email)
            .exclude(username=self.instance.username if not self.is_creating else None).count()):
            raise forms.ValidationError(
                message=t["%(model_name)s with this %(field_labels)s already exists."],
                code='unique_together',
                params={'model_name': t['User'], 'field_labels': t['Email']},
            )
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if re.search(r'^\d+$', username):
            raise forms.ValidationError(
                message=t["%(field_labels)s can\'t contain only digits."],
                code='unique_together',
                params={'field_labels': t['Username']},
            )
        if models.User.objects.filter(username__iexact=username).exclude(id=self.instance.id if not self.is_creating else None).count():
            raise forms.ValidationError(
                message=t["%(model_name)s with this %(field_labels)s already exists."],
                code='unique_together',
                params={'model_name': t['User'], 'field_labels': t['Username']},
            )
        return username

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
    captcha = ReCaptchaField()

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        if (getattr(django_settings, 'DEBUG', False)
            and not getattr(django_settings, 'RECAPTCHA_PUBLIC_KEY', None)):
            del(self.fields['captcha'])

class CreateUserForm(_UserCheckEmailUsernameForm):
    captcha = ReCaptchaField()
    submit_title = _('Sign Up')
    preferences_fields = ('birthdate', 'show_birthdate_year')
    password = forms.CharField(widget=forms.PasswordInput(), min_length=6, label=t['Password'])

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        preferences_initial = (
            model_to_dict(instance.preferences, self.preferences_fields)
            if instance is not None else {}
        )
        super(CreateUserForm, self).__init__(initial=preferences_initial, instance=instance, *args, **kwargs)
        self.fields.update(fields_for_model(models.UserPreferences, self.preferences_fields))
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
    form_title = string_concat(t['Username'], ' / ', t['Email'])
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
        new_d = self.instance.hidden_tags.copy()
        for default_hidden in models.ACTIVITIES_TAGS_HIDDEN_BY_DEFAULT:
            if default_hidden not in new_d:
                new_d[default_hidden] = True
        self.instance.save_d('hidden_tags', new_d)
        self.old_hidden_tags = self.instance.hidden_tags
        for field_name in self.fields.keys():
            if field_name.startswith('d_hidden_tags'):
                self.fields[field_name] = forms.BooleanField(
                    label=self.fields[field_name].label,
                    help_text=self.fields[field_name].help_text,
                    required=False,
                    initial=self.instance.hidden_tags.get(field_name.replace('d_hidden_tags-', ''), False),
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
                u'<a href="/help/Activities%20tabs" class="pull-right btn btn-main btn-sm" target="_blank">{}</a>'.format(
                    _('Learn more'),
                ))

    def clean(self):
        super(ActivitiesPreferencesForm, self).clean()
        # Check permission to show tags
        for field_name in self.fields.keys():
            if field_name.startswith('d_hidden_tags'):
                tag = field_name.replace('d_hidden_tags-', '')
                if (self.old_hidden_tags.get(tag, False)
                    and not self.cleaned_data.get(field_name, False)):
                    r = models.checkTagPermission(tag, self.request)
                    if r != True:
                        raise forms.ValidationError(u'{} {}'.format(
                            _(u'You are not allowed to see activities with the tag "{tag}".').format(
                                tag=self.fields[field_name].label,
                            ), r))

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = ('view_activities_language_only', 'i_default_activities_tab', 'i_activities_language', 'd_hidden_tags', )
        d_save_falsy_values_for_keys = {
            'hidden_tags': models.ACTIVITIES_TAGS_HIDDEN_BY_DEFAULT,
        }

class SecurityPreferencesForm(MagiForm):
    form_title = _('Security')
    form_icon = 'warning'

    def __init__(self, *args, **kwargs):
        super(SecurityPreferencesForm, self).__init__(*args, **kwargs)

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = ('i_private_message_settings', )

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

        # Favorite characters
        if not FAVORITE_CHARACTERS:
            for i in range(1, 4):
                self.fields.pop('favorite_character{}'.format(i))
        else:
            for i in range(1, 4):
                self.fields['favorite_character{}'.format(i)] = forms.ChoiceField(
                    required=False,
                    choices=BLANK_CHOICE_DASH + getFavoriteCharacterChoices(),
                    label=models.UserPreferences.favorite_character_label(i),
                )

        # Backgrounds
        if 'd_extra-background' in self.fields:
            if not PROFILE_BACKGROUNDS_NAMES:
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
            self.fields['m_description'].help_text = markdownHelpText(self.request)

    def clean_birthdate(self):
        if 'birthdate' in self.cleaned_data:
            if self.cleaned_data['birthdate'] and self.cleaned_data['birthdate'] > datetime.date.today():
                raise forms.ValidationError(_('This date cannot be in the future.'))
        return self.cleaned_data['birthdate']

    def clean(self):
        super(UserPreferencesForm, self).clean()
        favs = [v for (k, v) in self.cleaned_data.items() if k.startswith('favorite_character') and v]
        if favs and len(favs) != len(set(favs)):
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
        fields = ('m_description', 'location', 'favorite_character1', 'favorite_character2', 'favorite_character3', 'color', 'birthdate', 'show_birthdate_year', 'default_tab', 'd_extra')

class StaffEditUser(_UserCheckEmailUsernameForm):
    force_remove_avatar = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        preferences_fields = ('invalid_email', 'm_description', 'location', 'i_activities_language', 'i_status', 'donation_link', 'donation_link_title', 'c_groups')
        preferences_initial = model_to_dict(instance.preferences, preferences_fields) if instance is not None else {}
        super(StaffEditUser, self).__init__(initial=preferences_initial, instance=instance, *args, **kwargs)
        self.fields.update(fields_for_model(models.UserPreferences, preferences_fields))
        self.old_location = instance.preferences.location if instance else None

        # m_description
        if 'm_description' in self.fields:
            self.fields['m_description'].help_text = markdownHelpText(self.request)

        # invalid email
        if 'invalid_email' in self.fields:
            if not self.request.user.hasPermission('mark_email_addresses_invalid'):
                del(self.fields['invalid_email'])
            else:
                self.fields['invalid_email'].help_text = 'Mark as invalid if we keep receiving bounce emails from that email address. No email will ever be sent to that user again.'

        # i_activities_language
        if 'i_activities_language' in self.fields:
            if not self.request.user.hasPermission('edit_activities_post_language'):
                del(self.fields['i_activities_language'])
            else:
                self.fields['i_activities_language'] = forms.ChoiceField(
                    choices=models.Activity.LANGUAGE_CHOICES,
                    initial=self.fields['i_activities_language'].initial,
                    label=unicode(self.fields['i_activities_language'].label).format(language=''),
                    help_text='If you see that this user regularly posts with the wrong language, you can change the default language in which they post to avoid future mistakes.'
                )

        # edit_roles permission
        self.old_c_groups = self.instance.preferences.c_groups
        if 'c_groups' in self.fields:
            if hasPermission(self.request.user, 'edit_roles'):
                choices = [
                    (key, mark_safe(u'<img class="pull-right" height="60" alt="{name}" src="{img}"><b>{name}</b><br><p>{reqstaff}<small class="text-muted">{description}</small></p><ul>{perms}</ul>{operms}<br>'.format(
                        img=staticImageURL(key, folder='groups', extension='png'),
                        name=group['translation'],
                        reqstaff=u'<small class="text-danger">Requires staff status</small><br>' if group.get('requires_staff', False) else u'',
                        description=group['description'],
                        perms=u''.join([u'<li style="display: list-item"><small>{}</small></li>'.format(toHumanReadable(p)) for p in group.get('permissions', [])]),
                        operms=u'<br><div class="alert alert-danger"><small>Make sure you also grant/revoke {user} the following permissions <b>manually</b>:</small> <ul>{permissions}</ul></div>'.format(
                            user=instance.username,
                            permissions=u''.join([u'<li style="display: list-item"><small>{}</small></li>'.format(
                                p if not u
                                else u'<a href="{}" target="_blank">{} <i class="flaticon-link"></i></a>'.format(
                                        u['url'] if isinstance(u, dict) else u, p),
                            ) for p, u in group['outside_permissions'].items()]),
                        ) if group.get('outside_permissions', {}) else u'',
                    ))) for key, group in instance.preferences.GROUPS.items()
                ]
                self.fields['c_groups'] = forms.MultipleChoiceField(
                    required=False,
                    widget=forms.CheckboxSelectMultiple,
                    choices=choices,
                    label=self.fields['c_groups'].label,
                )
                # Add settings
                for key, group in instance.preferences.GROUPS.items():
                    settings = group.get('settings', [])
                    for setting in settings:
                        field_name = u'group_settings_{}_{}'.format(key, setting)
                        self.fields[field_name] = forms.CharField(
                            required=False, label=u'Settings for {}: {}'.format(
                                group['translation'],
                                toHumanReadable(setting)
                            ))
                # Set default checkboxes
                self.instance.preferences.c_groups = self.instance.preferences.groups
            else:
                del(self.fields['c_groups'])

        # edit_staff_status permission
        if 'is_staff' in self.fields:
            if hasPermission(self.request.user, 'edit_staff_status'):
                self.fields['is_staff'].help_text = 'Some roles require staff status, so you might need to remove the roles before being able to revoke staff status.'
            else:
                del(self.fields['is_staff'])

        # edit_donator_status permission
        if 'i_status' in self.fields:
            if hasPermission(self.request.user, 'edit_donator_status'):
                self.fields['i_status'].help_text = None
                self.fields['i_status'] = forms.ChoiceField(
                    required=False,
                    choices=(BLANK_CHOICE_DASH + [(c[0], c[1]) if isinstance(c, tuple) else (c, c) for c in instance.preferences.STATUS_CHOICES]),
                    label=self.fields['i_status'].label,
                )
            else:
                del(self.fields['i_status'])
        if 'donation_link' in self.fields:
            if not hasPermission(self.request.user, 'edit_donator_status'):
                del(self.fields['donation_link'])
        if 'donation_link_title' in self.fields:
            if hasPermission(self.request.user, 'edit_donator_status'):
                self.fields['donation_link_title'].help_text = 'If the donator is not interested in adding a link but are eligible for it, write "Not interested" and leave ""Donation link" empty'
            else:
                del(self.fields['donation_link_title'])

        # edit_reported_things
        if not hasPermission(self.request.user, 'edit_reported_things'):
            for field_name in ['username', 'email', 'm_description', 'location', 'force_remove_avatar']:
                if field_name in self.fields:
                    del(self.fields[field_name])
        else:
            self.fields['force_remove_avatar'].help_text = mark_safe('Check this box if the avatar is inappropriate. It will force the default avatar. <img src="{avatar_url}" alt="{username}" height="40" width="40">'.format(avatar_url=instance.image_url, username=instance.username))

        # If languages for translator is specified, use a choice field
        if 'group_settings_translator_languages' in self.fields:
            self.fields['group_settings_translator_languages'] = forms.MultipleChoiceField(
                required=False,
                label=self.fields['group_settings_translator_languages'].label,
                choices=django_settings.LANGUAGES,
                initial=(instance.preferences.settings_per_groups or {}).get('translator', {}).get('languages', [])
            )

    def save(self, commit=True):
        instance = super(StaffEditUser, self).save(commit=False)
        if 'force_remove_avatar' in self.fields and self.cleaned_data['force_remove_avatar'] and instance.email:
            splitEmail = instance.email.split('@')
            localPart = splitEmail.pop(0)
            instance.email = localPart.split('+')[0] + u'+' + randomString(4) + '@' + ''.join(splitEmail)
        if 'location' in self.fields and self.old_location != self.cleaned_data['location']:
            instance.preferences.location = self.cleaned_data['location']
            instance.preferences.location_changed = True
            instance.preferences.latitude = None
            instance.preferences.longitude = None
        for field_name in ['m_description', 'i_status', 'donation_link', 'donation_link_title', 'invalid_email', 'i_activities_language']:
            if field_name in self.fields and field_name in self.cleaned_data:
                setattr(instance.preferences, field_name, self.cleaned_data[field_name])
        if 'c_groups' in self.fields and 'c_groups' in self.cleaned_data:
            instance.preferences.save_c('groups', self.cleaned_data['c_groups'])
            settings_to_save = {}
            for group, details in instance.preferences.groups_and_details.items():
                # Mark as staff if added role requires staff
                if not instance.is_staff and instance.preferences.GROUPS[group].get('requires_staff', False):
                    instance.is_staff = True
                # Save settings for role
                settings = details.get('settings', [])
                if settings:
                    settings_to_save[group] = {
                        setting: self.cleaned_data.get(u'group_settings_{}_{}'.format(group, setting), None)
                        for setting in settings
                    }
            instance.preferences.save_j('settings_per_groups', settings_to_save)
        else:
            instance.preferences.c_groups = self.old_c_groups
        instance.preferences.save()
        if commit:
            instance.save()
        return instance

    class Meta(_UserCheckEmailUsernameForm.Meta):
        model = models.User
        fields = ('is_staff', 'username', 'email')

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
        ('username', t['Username']),
        ('preferences___cache_reputation', _('Most popular')),
        ('followed,id', _('Following')),
    )

    followers_of = HiddenModelChoiceField(queryset=models.User.objects.all())
    followers_of_filter = MagiFilter(selector='preferences__following')

    followed_by = HiddenModelChoiceField(queryset=models.User.objects.all())
    followed_by_filter = MagiFilter(selector='followers__user')

    liked_activity = HiddenModelChoiceField(queryset=models.Activity.objects.all())
    liked_activity_filter = MagiFilter(
        selectors=['activities', 'liked_activities'],
        distinct=True,
    )

    favorite_character = forms.ChoiceField(choices=BLANK_CHOICE_DASH + [
        (id, full_name)
        for (id, full_name, image) in getattr(django_settings, 'FAVORITE_CHARACTERS', [])
    ], required=False)
    favorite_character_filter = MagiFilter(selectors=[
        'preferences__favorite_character{}'.format(i) for i in range(1, 4)])

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

    def __init__(self, *args, **kwargs):
        super(UserFilterForm, self).__init__(*args, **kwargs)
        if 'favorite_character' in self.fields:
            self.fields['favorite_character'].label = models.UserPreferences.favorite_character_label()
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
        fields = [
            'search',
            'ordering', 'reverse_order',
            'favorite_character',
        ] + (
            ['color'] if USER_COLORS else []
        ) + [
            'location',
            'i_language',
        ]

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
            self.fields['i_type'].choices = [
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
        if self.request.user.is_superuser:
            return
        up_to = self.collection.edit_view.allow_cascade_delete_up_to(self.request)
        if not up_to:
            return
        collector = NestedObjects(using=self.instance._state.db)
        collector.collect([self.instance])
        total = self._get_total_deleted(collector.nested())
        if total >= up_to:
            raise forms.ValidationError(mark_safe(u'You are not allowed to delete this. {}'.format(
                'Ask an administrator.' if self.request.user.is_staff else '<a href="/help/Delete%20error/">Learn more</a>.',
            )))

class Confirm(forms.Form):
    confirm = forms.BooleanField(required=True, initial=False, label=_('Confirm'))

############################################################
# Staff configuration form

class StaffConfigurationForm(AutoForm):
    value = forms.NullBooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(StaffConfigurationForm, self).__init__(*args, **kwargs)
        if 'i_language' in self.fields:
            self.fields['i_language'].choices = BLANK_CHOICE_DASH + self.fields['i_language'].choices
        if 'value' in self.fields and (self.is_creating or not self.instance.is_boolean):
            self.fields['value'] = forms.CharField(required=False)
            if not self.is_creating and not self.instance.is_long:
                self.fields['value'].widget = forms.TextInput()
            else:
                self.fields['value'].widget = forms.Textarea()
        if not self.is_creating and self.instance.is_markdown and 'value' in self.fields:
            self.fields['value'].help_text = markdownHelpText(self.request)

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
    search_fields = ['key', 'verbose_key', 'value']

    has_value = forms.NullBooleanField()
    has_value_filter = MagiFilter(selector='value__isnull')

    with_translations = forms.NullBooleanField()
    with_translations_filter = MagiFilter(selector='i_language__isnull')

    i_language_filter = MagiFilter(to_queryset=lambda form, queryset, request, value: queryset.filter(
        Q(i_language=value) | Q(i_language__isnull=True) | Q(i_language='')))

    key = forms.CharField(widget=forms.HiddenInput)

    class Meta(MagiFiltersForm.Meta):
        model = models.StaffConfiguration
        fields = ('search', 'i_language', 'has_value', 'key')

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
        if self.is_creating and hasPermission(self.request.user, 'edit_staff_details'):
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
        'owner__username': t['Username'],
    }

    class Meta:
        model = models.StaffDetails
        fields = ['search']

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
            #self.fields['m_message'].help_text = markdownHelpText(self.request)
        # Only allow users to add tags they are allowed to add or already had before
        if 'c_tags' in self.fields:
            self.fields['c_tags'].choices = models.getAllowedTags(
                self.request, is_creating=True,
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

    show_more = FormShowMore(cutoff='is_popular', until='ordering')

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
        if 'c_tags' in self.fields:
            self.fields['c_tags'].choices = models.getAllowedTags(self.request)
        # Default selected language
        if 'i_language' in self.fields:
            self.default_to_current_language = False
            if ((self.request.user.is_authenticated()
                and self.request.user.preferences.view_activities_language_only)
                or (not self.request.user.is_authenticated()
                    and (ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT
                         or self.request.LANGUAGE_CODE in ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES)
                )):
                self.default_to_current_language = True
                self.fields['i_language'].initial = self.request.LANGUAGE_CODE
        if not self.request.user.is_authenticated():
            if 'is_following' in self.fields:
                del(self.fields['is_following'])
            if 'liked' in self.fields:
                del(self.fields['liked'])
        self.active_tab = None
        if self.request.user.is_authenticated():
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
        fields = ('search', 'c_tags', 'is_popular', 'is_following', 'liked', 'hide_archived', 'with_image', 'i_language')

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

############################################################
# Add/Edit reports

class ReportForm(MagiForm):
    reason = forms.ChoiceField(required=True, label=_('Reason'))
    images = MultiImageField(min_num=0, max_num=10, required=False, label=_('Images'))

    def __init__(self, *args, **kwargs):
        self.type = kwargs.pop('type', None)
        super(ReportForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.reported_thing_id = self.instance.reported_thing_id
            self.type = self.instance.reported_thing
        else:
            if 'id' not in self.request.GET:
                raise PermissionDenied()
            self.reported_thing_id = self.request.GET['id']
            # Check if the reported thing exists
            get_object_or_404(getMagiCollection(self.type).queryset, pk=self.reported_thing_id)
        reasons = OrderedDict()
        for reason in getMagiCollection(self.type).report_edit_templates.keys() + getMagiCollection(self.type).report_delete_templates.keys():
            reasons[reason] = _(reason)
        self.fields['reason'].choices = BLANK_CHOICE_DASH + reasons.items()

    def save(self, commit=True):
        instance = super(ReportForm, self).save(commit=False)
        instance.reported_thing = self.type
        instance.reported_thing_id = self.reported_thing_id
        old_lang = get_language()
        translation_activate('en')
        instance.reported_thing_title = unicode(getMagiCollection(self.type).title)
        translation_activate(old_lang)
        instance.save()
        for image in self.cleaned_data['images']:
            imageObject = models.UserImage.objects.create()
            imageObject.image.save(randomString(64), image)
            instance.images.add(imageObject)
        return instance

    class Meta(MagiForm.Meta):
        model = models.Report
        fields = ('reason', 'message', 'images')
        save_owner_on_creation = True

class FilterReports(MagiFiltersForm):
    search_fields = ['owner__username', 'message', 'staff_message', 'reason', 'reported_thing_title']
    search_fields_labels = {
        'owner__username': t['Username'],
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

    def __init__(self, *args, **kwargs):
        super(FilterReports, self).__init__(*args, **kwargs)
        self.fields['reported_thing'].choices = BLANK_CHOICE_DASH + [ (name, info['title']) for name, info in self.collection.types.items() ]
        self.fields['staff'].queryset = usersWithPermission(
            self.fields['staff'].queryset,
            self.request.user.preferences.GROUPS,
            'moderate_reports',
        )

    class Meta(MagiFiltersForm.Meta):
        model = models.Report
        fields = ('i_status', 'reported_thing', 'staff')

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
    username = forms.CharField(max_length=32, label=t['Username'])

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
        fields = ('username', 'name', 'description', 'image', 'url', 'rank')

class CopyBadgeForm(_BadgeForm):
    def __init__(self, *args, **kwargs):
        super(CopyBadgeForm, self).__init__(*args, **kwargs)
        badge_id = self.request.GET.get('id', None)
        self.badge = get_object_or_404(models.Badge, pk=badge_id)
        if not self.is_creating or self.badge.type == 'donator':
            raise PermissionDenied()
        self.fields['name'].initial = self.badge.name
        self.fields['description'].initial = self.badge.description
        self.fields['rank'].initial = self.badge.rank
        self.fields['url'].initial = self.badge.url
        if not self.badge.url:
            del(self.fields['url'])

    def save(self, commit=True):
        instance = super(CopyBadgeForm, self).save(commit=False)
        instance.show_on_profile = True
        instance.show_on_top_profile = False
        instance.image = self.badge.image
        if commit:
            instance.save()
        return instance

    class Meta(_BadgeForm.Meta):
        required_fields = ('name',)
        fields = ('username', 'name', 'description', 'url', 'rank')

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
        instance.description = self.cleaned_data['source']
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
    search_fields = ['user__username', 'name', 'description']
    search_fields_labels = {
        'user__username': t['Username'],
    }
    ordering_fields = [
        ('date', 'Date'),
        ('rank', 'Rank'),
    ]

    added_by = forms.ModelChoiceField(label=_('Staff'), queryset=models.User.objects.filter(is_staff=True), )

    of_user = forms.IntegerField(widget=forms.HiddenInput)
    of_user_filter = MagiFilter(to_queryset=lambda form, queryset, request, value: queryset.filter(user_id=value, show_on_profile=True))

    class Meta(MagiFiltersForm.Meta):
        model = models.Badge
        fields = ('search', 'rank', 'added_by', 'of_user')

############################################################
# Prizes form

class PrizeForm(AutoForm):
    class Meta(AutoForm.Meta):
        model = models.Prize
        fields = '__all__'
        save_owner_on_creation = True

class PrizeFilterForm(MagiFiltersForm):
    search_fields = ['name', 'm_details']
    ordering_fields = [
        ('id', 'Creation'),
        ('value', 'Value'),
    ]

    has_giveaway = forms.NullBooleanField(label='Assigned to a giveaway or already given away')
    has_giveaway_filter = MagiFilter(selector='giveaway_url__isnull')

    class Meta:
        model = models.Prize
        fields = ('search', 'has_giveaway', 'i_character', 'ordering', 'reverse_order')

class PrizeViewingFilterForm(MagiFiltersForm):
    max_value = forms.IntegerField(widget=forms.HiddenInput)
    max_value_filter = MagiFilter(selector='value__lte', multiple=False)

    min_value = forms.IntegerField(widget=forms.HiddenInput)
    min_value_filter = MagiFilter(selector='value__gt', multiple=False)

    presets = OrderedDict([
        ('tier1', { 'fields': { 'min_value': 0, 'max_value': 5 }, 'verbose_name': 'tier 1' }),
        ('tier2', { 'fields': { 'min_value': 5, 'max_value': 10 }, 'verbose_name': 'tier 2' }),
        ('tier3', { 'fields': { 'min_value': 10, 'max_value': 15 }, 'verbose_name': 'tier 3' }),
        ('tier4', { 'fields': { 'min_value': 10, 'max_value': 15 }, 'verbose_name': 'tier 4' }),
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
        self.fields['to_user'].initial = self.request.GET.get('to_user', None)
        self.fields['message'].validators.append(MinLengthValidator(2))

    class Meta(MagiForm.Meta):
        model = models.PrivateMessage
        fields = ('to_user', 'message', )
        hidden_foreign_keys = ('to_user', )
        save_owner_on_creation = True

class PrivateMessageFilterForm(MagiFiltersForm):
    search_fields = ['message', 'to_user__username', 'owner__username']
    search_fields_labels = {
        'to_user__username': t['Username'],
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
