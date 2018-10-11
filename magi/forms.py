import re, datetime
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from multiupload.fields import MultiFileField
from django import forms
from django.http.request import QueryDict
from django.db.models.fields import BLANK_CHOICE_DASH, FieldDoesNotExist, TextField, CharField
from django.db.models.fields.files import ImageField
from django.db.models import Q
from django.forms.models import model_to_dict, fields_for_model
from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login as login_action
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
from magi import models
from magi.default_settings import RAW_CONTEXT
from magi.settings import (
    FAVORITE_CHARACTER_NAME,
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
)
from magi.utils import (
    ordinalNumber,
    randomString,
    shrinkImageFromData,
    getMagiCollection,
    getAccountIdsFromSession,
    hasPermission,
    toHumanReadable,
    usersWithPermission,
    staticImageURL,
    markdownHelpText,
    hasGoodReputation,
    LANGUAGES_DICT,
    BACKGROUNDS_NAMES,
)

############################################################
# Internal utils

class MultiImageField(MultiFileField, forms.ImageField):
    pass

class DateInput(forms.DateInput):
    input_type = 'date'

def date_input(field, value=None):
    field.widget = DateInput()
    field.widget.attrs.update({
        'class': 'calendar-widget',
        'data-role': 'data',
    })
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
    error_css_class = ''

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.collection = kwargs.pop('collection', None)
        self.form_type = kwargs.pop('type', None)
        self.ajax = kwargs.pop('ajax', False)
        super(MagiForm, self).__init__(*args, **kwargs)
        self.is_creating = not hasattr(self, 'instance') or not self.instance.pk
        self.c_choices = []
        self.d_choices = {}
        self.m_previous_values = {}
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
        for name, field in self.fields.items():
            # Fix optional fields using null=True
            try:
                model_field = self.Meta.model._meta.get_field(name)
            except FieldDoesNotExist:
                model_field = None
            if model_field is not None and model_field.null:
                self.fields[name].required = False
            # Fix dates fields
            if isinstance(field, forms.DateField):
                self.fields[name], value = date_input(field, value=(getattr(self.instance, name, None) if not self.is_creating else None))
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
                    if not self.collection or not self.collection.translated_fields or name[2:-1] not in self.collection.translated_fields or getattr(self, 'is_translate_form', False):
                        self.d_choices[name[2:]] = []
                        for choice in (choices.items() if isinstance(choices, dict) else choices):
                            key = choice[0] if isinstance(choice, tuple) else choice
                            verbose_name = choice[1] if isinstance(choice, tuple) else choice
                            verbose_name = verbose_name() if callable(verbose_name) else verbose_name
                            field_name = u'{}-{}'.format(name, key)
                            self.d_choices[name[2:]].append((field_name, key))
                            widget = forms.TextInput
                            label = self.fields[name].label
                            if getattr(self, 'is_translate_form', False):
                                try: singular_field = self.Meta.model._meta.get_field(name[2:-1])
                                except FieldDoesNotExist: singular_field = None
                                if singular_field and isinstance(singular_field, TextField):
                                    widget = forms.Textarea
                                default = getattr(self.instance, name[2:-1], None)
                                if default and name[2:-1].startswith('m_'):
                                    default = mark_safe(u'<pre>{}</pre>'.format(default))
                                help_text = mark_safe(u'{original}<img src="{img}" height="20" /> {lang}{default}'.format(
                                    img=staticImageURL(key, folder='language', extension='png'),
                                    lang=verbose_name,
                                    default=u' <code>{}: {}</code>'.format(t['English'], default or 'no value'),
                                    original=u'{}<br>'.format(self.fields[name].help_text) if self.fields[name].help_text else '',
                                ))
                            else:
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
            # Save previous values of markdown fields
            elif name.startswith('m_') and not isinstance(self, MagiFiltersForm) and not self.is_creating:
                self.m_previous_values[name] = getattr(self.instance, name)
            # Show label "English" or "Japanese" to non-d fields kept in translation form
            elif getattr(self, 'is_translate_form', False):
                self.fields[name].help_text = mark_safe(u'{original}<img src="{img}" height="20" /> {lang}'.format(
                    original=u'{}<br>'.format(self.fields[name].help_text) if self.fields[name].help_text else '',
                    img=staticImageURL(
                        'ja' if name.startswith('japanese_') else 'en',
                        folder='language', extension='png',
                    ),
                    lang=t['Japanese'] if name.startswith('japanese_') else t['English'],
                ))

        # Fix force required fields
        if hasattr(self.Meta, 'required_fields'):
            for field in self.Meta.required_fields:
                if field in self.fields:
                    self.fields[field].required = True

        # Has the form been opened in the context of a report?
        self.is_reported = (
            not self.is_creating
            and not isinstance(self, MagiFiltersForm)
            and self.request
            and 'is_reported' in self.request.GET
            and self.request.user.is_authenticated()
            and self.instance.owner != self.request.user
        )

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
        # Save owner on creation if specified
        if hasattr(self.Meta, 'save_owner_on_creation') and self.Meta.save_owner_on_creation and self.is_creating:
            owner = getattr(self, 'to_owner', None)
            if owner:
                instance.owner = owner
            else:
                instance.owner = self.request.user if self.request.user.is_authenticated() else None
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
                and getattr(instance, field) == ''):
                setattr(instance, field, None)
            # Save CSV values
            if field.startswith('c_') and field in self.c_choices:
                instance.save_c(field[2:], self.cleaned_data[field])
            # Remove cached HTML for markdown fields
            if (field.startswith('m_') and field in self.m_previous_values
                and has_field(instance, field)
                and self.m_previous_values[field] != getattr(instance, field)
                and has_field(instance, u'_cache_{}'.format(field[2:]))):
                setattr(instance, u'_cache_{}'.format(field[2:]), None)
            # Shrink images
            if (hasattr(instance, field)
                and isinstance(self.fields[field], forms.Field)
                and has_field(instance, field)
                and type(self.Meta.model._meta.get_field(field)) == models.models.ImageField):
                image = self.cleaned_data[field]
                if image and (isinstance(image, InMemoryUploadedFile) or isinstance(image, TemporaryUploadedFile)):
                    if (hasattr(self.Meta, 'tinypng_on_save')
                        and field in self.Meta.tinypng_on_save):
                        filename = image.name
                        image = shrinkImageFromData(image.read(), filename, settings=getattr(instance._meta.model, 'tinypng_settings', {}).get(field, {}))
                        image.name = instance._meta.model._meta.get_field(field).upload_to(instance, filename)
                        setattr(instance, field, image)
                    else:
                        # Remove any cached processed image
                        setattr(instance, u'_tthumbnail_{}'.format(field), None)
                        setattr(instance, u'_thumbnail_{}'.format(field), None)
                        setattr(instance, u'_original_{}'.format(field), None)
                        setattr(instance, u'_2x_{}'.format(field), None)
        if commit:
            instance.save()
        return instance

    class Meta:
        pass

############################################################
# AutoForm will guess which fields to use in a model

class AutoForm(MagiForm):
    """
    This form can be used to include all the fields but ignore the _cache data or anything that starts with '_'
    """
    def __init__(self, *args, **kwargs):
        super(AutoForm, self).__init__(*args, **kwargs)
        for field in self.fields.keys():
            if (field.startswith('_')
                or field == 'owner'):
                del(self.fields[field])

############################################################
# Translate form

def to_translate_form_class(view):
    if not view.collection.translated_fields:
        return None

    class _TranslateForm(MagiForm):

        def _addHelpTextReverseTranslation(self, field_name, reverse_value, language):
            self.fields[field_name].help_text = mark_safe(
                u'{original} <code>{language}: {value}</code>'.format(
                    original=self.fields[field_name].help_text,
                    language=LANGUAGES_DICT.get(language, language.upper()),
                    value=reverse_value or 'no value',
                ))

        def _needsVisibleEnglishFields(self, spoken_languages):
            """
            Check if English should be added to languages because value exists in field but not in English
            -> ie needs reverse translation
            """
            needs_english = False
            for language in spoken_languages:
                for field in view.collection.translated_fields:
                    if (field in self.fields
                        and not getattr(self.instance, field, None)):
                        if u'd_{}s-{}'.format(field, language) in self.fields:
                            reverse_value = getattr(
                                self.instance, u'{}s'.format(field, language), {}).get(language, None)
                            if reverse_value:
                                needs_english = True
                                self._addHelpTextReverseTranslation(
                                    field, reverse_value, language)
                        if language == 'ja' and u'japanese_{}'.format(field) in self.fields:
                            reverse_value = getattr(self.instance, u'japanese_{}'.format(field), None)
                            if reverse_value:
                                needs_english = True
                                self._addHelpTextReverseTranslation(
                                    field, reverse_value, language)
            return needs_english

        def __init__(self, *args, **kwargs):
            self.is_translate_form = True
            super(_TranslateForm, self).__init__(*args, **kwargs)
            spoken_languages = (self.request.user.preferences.settings_per_groups or {}).get('translator', {}).get('languages', [])
            if spoken_languages:
                if self._needsVisibleEnglishFields(spoken_languages):
                    spoken_languages.append('en')
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
            fields = [
                f(field)
                for field in (view.collection.translated_fields or [])
                for f in (lambda field: field, lambda field: u'd_{}s'.format(field))
            ]
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
                condition |= Q(**{ '{}__icontains'.format(field_name): term })
            for field_name in getattr(self, 'search_fields_exact', []):
                condition |= Q(**{ '{}__iexact'.format(field_name): term })
            queryset = queryset.filter(condition)
        return queryset

    search_filter = MagiFilter(to_queryset=_search_to_queryset)

    ordering = forms.ChoiceField(label=_('Ordering'))
    ordering_filter = MagiFilter(multiple=False)
    reverse_order = forms.BooleanField(label=_('Reverse order'))

    view = forms.ChoiceField(label=_('View'))
    view_filter = MagiFilter(noop=True)

    def _to_missing_translation_lambda(self, field_name):
        def _to_missing_translation(form, queryset, request, value=None):
            return queryset.exclude(**{
                u'{}__isnull'.format(field_name): True,
            }).exclude(**{
                field_name: '',
            }).exclude(**{
                u'd_{}s__contains'.format(field_name): u'"{}"'.format(value),
            })
        return _to_missing_translation

    def __init__(self, *args, **kwargs):
        super(MagiFiltersForm, self).__init__(*args, **kwargs)
        self.empty_permitted = True
        # Add add_to_{} to fields that are collectible and have a quick add option
        if self.collection and self.request.user.is_authenticated():
            for collection_name, collection in self.collection.collectible_collections.items():
                if collection.queryset.model.fk_as_owner and collection.add_view.enabled and collection.add_view.quick_add_to_collection(self.request):
                    setattr(self, u'add_to_{}_filter'.format(collection_name), MagiFilter(noop=True))
                    queryset = collection.queryset.model.owners_queryset(self.request.user)
                    initial = getattr(self.request, u'add_to_{}'.format(collection_name), None)
                    # Check if only one option, hide picker
                    total_fk_owner_ids = getattr(self.request, u'total_fk_owner_ids_{}'.format(collection_name), None)
                    if total_fk_owner_ids is None:
                        if collection.queryset.model.fk_as_owner == 'account':
                            total_fk_owner_ids = len(getAccountIdsFromSession(self.request))
                        else:
                            total_fk_owner_ids = len(queryset)
                    if total_fk_owner_ids <= 1:
                        self.fields[u'add_to_{}'.format(collection_name)] = forms.IntegerField(
                            initial=initial, widget=forms.HiddenInput(attrs=({'value': initial} if initial else {})),
                        )
                    else:
                        self.fields = OrderedDict(
                            [(u'add_to_{}'.format(collection_name), forms.ModelChoiceField(
                                queryset=queryset, label=collection.add_sentence, required=True,
                                initial=initial,
                            ))] + self.fields.items())
        # Add missing_{}_translations for all translatable fields if the current user has permission
        if self.collection and self.request.user.is_authenticated() and self.request.user.hasPermission('translate_items') and self.collection.translated_fields:
            for field_name in self.collection.translated_fields:
                filter_field_name = u'missing_{}_translations'.format(field_name)
                setattr(self, u'{}_filter'.format(filter_field_name), MagiFilter(
                    to_queryset=self._to_missing_translation_lambda(field_name),
                ))
                self.fields[filter_field_name] = forms.CharField(
                    widget=forms.HiddenInput
                )
        # Remove search from field if search_fields is not specified
        if not hasattr(self, 'search_fields') and not hasattr(self, 'search_fields_exact'):
            del(self.fields['search'])
        # Remove ordering form field if ordering_fields is not specified
        if not hasattr(self, 'ordering_fields'):
            del(self.fields['ordering'])
            del(self.fields['reverse_order'])
        # Set default ordering initial value
        if 'ordering' in self.fields:
            self.fields['ordering'].choices = [
                (k, v() if callable(v) else v)
                for k, v in self.ordering_fields
            ]
            if self.collection:
                self.fields['ordering'].initial = self.collection.list_view.plain_default_ordering
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
                 if not _v[1].get('hide_in_filter', False)]: # None visible
                self.fields['view'].widget = self.fields['view'].hidden_widget()
            self.fields['view'].choices = self.collection.list_view._alt_view_choices
        else:
            del(self.fields['view'])
        if getattr(self.Meta, 'all_optional', True):
            for field_name, field in self.fields.items():
                # Add blank choice to list of choices that don't have one
                if (isinstance(field, forms.fields.ChoiceField)
                    and not isinstance(field, forms.fields.MultipleChoiceField)
                    and field.choices and not field.initial):
                    choices = list(self.fields[field_name].choices)
                    if choices and choices[0][0] != '':
                        self.fields[field_name].choices = BLANK_CHOICE_DASH + choices
                        self.fields[field_name].initial = ''
                # Marks all fields as not required
                field.required = False

    def filter_queryset(self, queryset, parameters, request):
        # Generic filter for ids
        queryset = filter_ids(queryset, request)
        # Go through form fields
        for field_name in self.fields.keys():
            # ordering fields are Handled in views collection, used by pagination
            if field_name in ['ordering', 'page', 'reverse_order']:
                continue
            filter = getattr(self, '{}_filter'.format(field_name), None)
            if not filter:
                filter = MagiFilter()
            if filter.noop:
                continue
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
            if value is None or value == '':
                continue
            # Filtering is provided by to_queryset
            if filter.to_queryset:
                queryset = filter.to_queryset(self, queryset, request,
                                              value=self._value_as_string(filter, value))
            # Automatic filtering
            else:
                operator_for_multiple = filter.operator_for_multiple or MagiFilterOperator.default_for_field(self.fields[field_name])
                operator_for_multiple_selectors = filter.operator_for_multiple_selectors or MagiFilterOperatorSelector.default
                selectors = filter.selectors if filter.selectors else [field_name]
                condition = Q()
                filters, exclude = {}, {}
                for selector in selectors:
                    # NullBooleanField
                    if isinstance(self.fields[field_name], forms.fields.NullBooleanField):
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
                    elif (isinstance(self.fields[field_name], forms.fields.MultipleChoiceField)
                          or filter.multiple):
                        values = value if isinstance(value, list) else [value]
                        if operator_for_multiple == MagiFilterOperator.OrContains:
                            for value in values:
                                condition = condition | Q(**{ u'{}__icontains'.format(selector): value })
                        elif operator_for_multiple == MagiFilterOperator.OrExact:
                            filters = { u'{}__in'.format(selector): values }
                        elif operator_for_multiple == MagiFilterOperator.And:
                            for value in values:
                                condition = condition & Q(**{ u'{}__icontains'.format(selector): value })
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
        if 'level' in self.fields and not self.is_creating:
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
            if not self.data.get('screenshot') and 'screenshot' in self.fields and int(self.data.get('level', 0) or 0) < 200:
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

class CreateUserForm(_UserCheckEmailUsernameForm):
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

    class Meta(_UserCheckEmailUsernameForm.Meta):
        model = models.User
        fields = ('username', 'email', 'password')

class UserForm(_UserCheckEmailUsernameForm):
    form_title = string_concat(t['Username'], ' / ', t['Email'])
    icon = 'profile'

    class Meta(_UserCheckEmailUsernameForm.Meta):
        model = models.User
        fields = ('username', 'email',)

class EmailsPreferencesForm(MagiForm):
    form_title = _('Emails')
    icon = 'contact'

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
    icon = 'comments'

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
                    label=self.fields[field_name].help_text,
                    help_text=self.fields[field_name].label,
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
            self.fields['i_default_activities_tab'].help_text = mark_safe(
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
    icon = 'warning'

    def __init__(self, *args, **kwargs):
        super(SecurityPreferencesForm, self).__init__(*args, **kwargs)

    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = ('i_private_message_settings', )

class UserPreferencesForm(MagiForm):
    form_title = _('Customize profile')
    icon = 'id'

    color = forms.ChoiceField(required=False, choices=[], label=_('Color'))
    default_tab = forms.ChoiceField(
        label=_('Default tab'),
        required=False,
        choices=BLANK_CHOICE_DASH + [
            (tab_name, tab['name'])
            for tab_name, tab in PROFILE_TABS.items()
        ],
    )

    def __init__(self, *args, **kwargs):
        super(UserPreferencesForm, self).__init__(*args, **kwargs)

        # Favorite characters
        if not FAVORITE_CHARACTERS:
            for i in range(1, 4):
                self.fields.pop('favorite_character{}'.format(i))
        else:
            for i in range(1, 4):
                self.fields['favorite_character{}'.format(i)] = forms.ChoiceField(
                    required=False,
                    choices=BLANK_CHOICE_DASH + [(name, localized) for (name, localized, image) in FAVORITE_CHARACTERS],
                    label=(_(FAVORITE_CHARACTER_NAME) if FAVORITE_CHARACTER_NAME
                           else _('{nth} Favorite Character')).format(nth=_(ordinalNumber(i))))

        # Backgrounds
        if 'd_extra-background' in self.fields:
            if not BACKGROUNDS_NAMES:
                del(self.fields['d_extra-background'])
            else:
                self.fields['d_extra-background'] = forms.ChoiceField(
                    required=False,
                    label=self.fields['d_extra-background'].label,
                    initial=self.fields['d_extra-background'].initial,
                    choices=BLANK_CHOICE_DASH + [(k, v()) for k, v in BACKGROUNDS_NAMES.items()],
                )

        # Location
        if 'location' in self.fields:
            self.fields['location'].help_text = mark_safe(
                u'{} <a href="/map/" target="_blank">{} <i class="flaticon-link"></i></a>'.format(
                    unicode(self.fields['location'].help_text),
                    unicode(_(u'Open {thing}')).format(thing=unicode(_('Map')).lower()),
                ))

        # Color
        if 'color' in self.fields:
            if USER_COLORS:
                self.fields['color'].choices = BLANK_CHOICE_DASH + [(name, localized_name) for (name, localized_name, css_color, hex_color) in USER_COLORS]
                if self.instance:
                    self.fields['color'].initial = self.instance.color
            else:
                self.fields.pop('color')
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
                            permissions=''.join([u'<li style="display: list-item"><small>{}</small></li>'.format(
                                p if not u else u'<a href="{}" target="_blank">{} <i class="flaticon-link"></i></a>'.format(u, p),
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
    icon = 'lock'

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
    search_fields = ('username', )
    ordering_fields = (
        ('username', t['Username']),
        ('date_joined', _('Join Date')),
        ('followed,id', _('Follow')),
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

    def filter_queryset(self, queryset, parameters, request):
        queryset = super(UserFilterForm, self).filter_queryset(queryset, parameters, request)

        # Filter by who the user can private messages to
        if (request.GET.get('view', None) == 'send_private_message'
            and request.user.is_authenticated()):
            # If setting is nobody, don't return any result
            if request.user.preferences.private_message_settings == 'nobody':
                return queryset.filter(id=-1)
            # If follow, restrict to followers
            if request.user.preferences.private_message_settings == 'follow':
                queryset = queryset.filter(followers__user=request.user)
            # Filter out users who allow nobody to message them
            queryset = queryset.exclude(
                preferences__i_private_message_settings=models.UserPreferences.get_i(
                    'private_message_settings', 'nobody'),
            )
            # Filter out users who allow only followers and don't follow user
            queryset = queryset.exclude(
                Q(preferences__i_private_message_settings=models.UserPreferences.get_i(
                    'private_message_settings', 'follow'))
                & ~Q(preferences__following=request.user),
            )

        return queryset

    class Meta(MagiFiltersForm.Meta):
        model = models.User
        fields = ('search', 'ordering', 'reverse_order')

############################################################
# User links

class AddLinkForm(MagiForm):
    action = '#links'

    @property
    def form_title(self):
        return _(u'Add {thing}').format(thing=unicode(_('Link')).lower())
    icon = 'add'

    def __init__(self, *args, **kwargs):
        super(AddLinkForm, self).__init__(*args, **kwargs)
        self.fields['i_relevance'].label = _('How often do you tweet/stream/post about {}?').format(GAME_NAME)
        self.fields['i_type'].choices = [(name, localized) for (name, localized) in self.fields['i_type'].choices if name != django_settings.SITE]

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
    icon = 'promo'

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
    icon = 'translate'

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
    search_fields = ['verbose_key', 'value']

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
            if field_name == 'for_user':
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
                    label=self.fields[field_name].help_text,
                    help_text=self.fields[field_name].label,
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

    class Meta:
        model = models.StaffDetails
        fields = ['search']

############################################################
# Activity form

class ActivityForm(MagiForm):
    def __init__(self, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
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

        if 'm_message' in self.fields:
            self.fields['m_message'].help_text = markdownHelpText(self.request)
        # Only allow users to add tags they are allowed to see
        if 'c_tags' in self.fields:
            self.fields['c_tags'].choices = models.getAllowedTags(self.request, is_creating=True)
        self.previous_m_message = None
        if 'm_message' in self.fields and not self.is_creating:
            self.previous_m_message = self.instance.m_message

    def save(self, commit=False):
        instance = super(ActivityForm, self).save(commit=False)
        instance.update_cache('hidden_by_default')
        if not self.is_creating and instance.m_message != self.previous_m_message:
            instance.last_bump = timezone.now()
        if commit:
            instance.save()
        return instance

    class Meta(MagiForm.Meta):
        model = models.Activity
        fields = ('m_message', 'c_tags', 'i_language', 'image')
        save_owner_on_creation = True

class FilterActivities(MagiFiltersForm):
    search_fields = ['m_message', 'c_tags']
    ordering_fields = [
        ('last_bump', _('Hot')),
        ('creation', _('Creation')),
        ('_cache_total_likes,creation', string_concat(_('Most Popular'), ' (', _('All time'), ')')),
        ('_cache_total_likes,id', string_concat(_('Most Popular'), ' (', _('This week'), ')')),
    ]

    with_image = forms.NullBooleanField(label=_('Image'))
    with_image_filter = MagiFilter(selector='image__isnull')

    owner_id = forms.IntegerField(widget=forms.HiddenInput)

    def _is_popular_to_queryset(self, queryset, request, value):
        # Skil the filter if owner_id is selected
        if 'owner_id' in self.data and self.data['owner_id']:
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
    ) if value else queryset)

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
        if 'ordering' in parameters and parameters['ordering'] == '_cache_total_likes,id':
            queryset = queryset.filter(creation__gte=timezone.now() - relativedelta(weeks=1))
        return queryset

    @property
    def action(self):
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
        if commit:
            instance.save()
        return instance

    class Meta(_BadgeForm.Meta):
        fields = ('username', 'donation_month', 'source', 'show_on_profile', 'rank')

class FilterBadges(MagiFiltersForm):
    search_fields = ['user__username', 'name', 'description']
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

############################################################
# Private Message form

class PrivateMessageForm(MagiForm):
    def __init__(self, *args, **kwargs):
        super(PrivateMessageForm, self).__init__(*args, **kwargs)
        self.fields['to_user'].initial = self.request.GET.get('to_user', None)

        # For permissions checking
        self.fields['to_user'].queryset = self.fields['to_user'].queryset.select_related(
            'preferences').extra(select={
                'is_followed_by': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = (SELECT id FROM {table} WHERE user_id = auth_user.id) AND user_id = {id}'.format(
                    table=models.UserPreferences._meta.db_table,
                    id=self.request.user.id,
                ),
                'followed': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = {id} AND user_id = auth_user.id'.format(
                    table=models.UserPreferences._meta.db_table,
                    id=self.request.user.preferences.id,
                ),
            })
        self.fields['message'].validators.append(MinLengthValidator(2))

    def clean(self):
        super(PrivateMessageForm, self).clean()
        if (not self.request.user.hasPermissionToMessage(self.cleaned_data['to_user'])
            or not hasGoodReputation(self.request)):
            raise forms.ValidationError('Permission denied')

    def save(self, commit=True):
        instance = super(PrivateMessageForm, self).save(commit=False)
        if commit:
            instance.save()
        return instance

    class Meta(MagiForm.Meta):
        model = models.PrivateMessage
        fields = ('to_user', 'message', )
        hidden_foreign_keys = ('to_user', )
        save_owner_on_creation = True

class PrivateMessageFilterForm(MagiFiltersForm):
    search_fields = ('message', 'to_user__username', 'owner__username')

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
