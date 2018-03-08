import re, datetime
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from multiupload.fields import MultiFileField
from django import forms
from django.http.request import QueryDict
from django.db.models.fields import BLANK_CHOICE_DASH, FieldDoesNotExist, TextField, CharField
from django.db.models import Q
from django.forms.models import model_to_dict, fields_for_model
from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login as login_action
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, string_concat, get_language, activate as translation_activate
from django.utils.safestring import mark_safe
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.core.validators import MinValueValidator
from django.shortcuts import get_object_or_404
from magi.middleware.httpredirect import HttpRedirectException
from magi.django_translated import t
from magi import models
from magi.default_settings import RAW_CONTEXT
from magi.settings import FAVORITE_CHARACTER_NAME, FAVORITE_CHARACTERS, USER_COLORS, GAME_NAME, ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT, ON_PREFERENCES_EDITED, PROFILE_TABS
from magi.utils import ordinalNumber, randomString, shrinkImageFromData, getMagiCollection, getAccountIdsFromSession

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
# - Will use tinypng to optimize images and will use settings specified in models
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
        self.hidden_foreign_keys_querysets = {}
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
                    self.d_choices[name] = []
                    for choice in choices:
                        key = choice[0] if isinstance(choice, tuple) else choice
                        field_name = u'{}-{}'.format(name, key)
                        self.d_choices[name].append((field_name, key))
                        self.fields[field_name] = forms.CharField(
                            required=False,
                            label=u'{}: {}'.format(self.fields[name].label, choice[1] if isinstance(choice, tuple) else choice),
                            initial=getattr(self.instance, name[2:]).get(key, None) if not self.is_creating else None,
                        )
                    del(self.fields[name])
            # Make fields with soft choices use a ChoiceField
            elif getattr(self.Meta.model, u'{name}_SOFT_CHOICES'.format(name=name[2:].upper()), False):
                choices = getattr(self.Meta.model, '{name}_CHOICES'.format(name=name[2:].upper()), None)
                if choices is not None:
                    self.fields[name] = forms.ChoiceField(
                        required=field.required,
                        choices=[(c[0], c[1]) if isinstance(c, tuple) else (c, c) for c in choices],
                        label=field.label,
                    )
        # Fix force required fields
        if hasattr(self.Meta, 'required_fields'):
            for field in self.Meta.required_fields:
                if field in self.fields:
                    self.fields[field].required = True

    def clean(self):
        # Check max_per_user
        if (self.collection
            and self.request and self.request.user.is_authenticated()):
            if self.collection.add_view.max_per_user_per_hour:
                already_added = self.Meta.model.objects.filter(**{
                    self.Meta.model.selector_to_owner(): self.request.user,
                    'creation__gte': timezone.now() - relativedelta(hours=1),
                }).count()
                if already_added >= self.collection.add_view.max_per_user_per_hour:
                    raise forms.ValidationError(
                        unicode(_('You\'ve added a lot of {things}, lately. Try to wait a little bit before adding more.'))
                        .format(things=unicode(self.collection.plural_title).lower()))
            if self.collection.add_view.max_per_user_per_day:
                already_added = self.Meta.model.objects.filter(**{
                    self.Meta.model.selector_to_owner(): self.request.user,
                    'creation__gte': timezone.now() - relativedelta(days=1),
                }).count()
                if already_added >= self.collection.add_view.max_per_user_per_day:
                    raise forms.ValidationError(
                        unicode(_('You\'ve added a lot of {things}, lately. Try to wait a little bit before adding more.'))
                        .format(things=unicode(self.collection.plural_title).lower()))
            if self.collection.add_view.max_per_user:
                already_added = self.Meta.model.objects.filter(**{
                    self.Meta.model.selector_to_owner(): self.request.user
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
            instance.owner = self.request.user if self.request.user.is_authenticated() else None
        # Save d_ dict choices
        for dfield, choices in self.d_choices.items():
            d = {}
            for field, key in choices:
                if self.cleaned_data[field]:
                    d[key] = self.cleaned_data[field]
            instance.save_d(dfield[2:], d)
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
            # Shrink images
            if (hasattr(instance, field)
                and isinstance(self.fields[field], forms.Field)
                and has_field(instance, field)
                and type(self.Meta.model._meta.get_field(field)) == models.models.ImageField):
                image = self.cleaned_data[field]
                if image and (isinstance(image, InMemoryUploadedFile) or isinstance(image, TemporaryUploadedFile)):
                    filename = image.name
                    image = shrinkImageFromData(image.read(), filename, settings=getattr(instance._meta.model, 'tinypng_settings', {}).get(field, {}))
                    image.name = instance._meta.model._meta.get_field(field).upload_to(instance, filename)
                    setattr(instance, field, image)
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
# MagiFiltersForm

class MagiFilter(object):
    """
    to_queryset: lambda that takes form, queryset, request, value and returns a queryset.
                 Optional, will filter automatically.
                 selector and to_value are ignored when specified.
    selector: will be the name of the field by default. example: owner__username.
    selectors: same as selector but works with multiple values.
    to_value: lambda that takes the value and transforms the value if needed.
    multiple: allow multiple values separated by commas. Set to False if your value may contain commas.
    noop: when set to true, will not affect result
    """
    def __init__(self,
                 to_queryset=None,
                 selector=None,
                 selectors=None,
                 to_value=None,
                 multiple=True,
                 operator_for_multiple=None,
                 allow_csv=True,
                 noop=False,
    ):
        self.to_queryset = to_queryset
        self.selectors = selectors
        if not self.selectors and selector:
            self.selectors = [selector]
        self.to_value = to_value
        self.multiple = multiple
        self.operator_for_multiple = operator_for_multiple
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

    def __init__(self, *args, **kwargs):
        super(MagiFiltersForm, self).__init__(*args, **kwargs)
        self.empty_permitted = True
        # Add add_to_{} to fields that are collectible and have a quick add option
        if self.collection and self.request.user.is_authenticated():
            for collection_name, collection in self.collection.collectible_collections.items():
                if collection.queryset.model.fk_as_owner and collection.add_view.enabled and collection.add_view.quick_add_to_collection(self.request):
                    setattr(self, u'add_to_{}_filter'.format(collection_name), MagiFilter(noop=True))
                    queryset = collection.queryset.model.owners_queryset(self.request.user)
                    initial = getattr(self.request, u'add_to_{}'.format(collection_name))
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
            # Remove search from field if search_fields is not specified
        if not hasattr(self, 'search_fields') and not hasattr(self, 'search_fields_exact'):
            del(self.fields['search'])
        # Remove ordering form field if ordering_fields is not specified
        if not hasattr(self, 'ordering_fields'):
            del(self.fields['ordering'])
            del(self.fields['reverse_order'])
        # Set default ordering initial value
        if 'ordering' in self.fields:
            self.fields['ordering'].choices = self.ordering_fields
            if self.collection:
                self.fields['ordering'].initial = self.collection.list_view.plain_default_ordering
                self.fields['reverse_order'].initial = self.collection.list_view.default_ordering.startswith('-')
        # Set view selector
        if 'view' in self.fields and self.collection and self.collection.list_view.alt_views:
            if not self.collection.list_view._alt_view_choices:
                self.collection.list_view._alt_view_choices = [('', self.collection.plural_title)] + [
                    (view_name, view.get('verbose_name', view_name))
                    for view_name, view in self.collection.list_view.alt_views
                ]
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
            if field_name in parameters and parameters[field_name] != '':
                filter = getattr(self, '{}_filter'.format(field_name), None)
                if not filter:
                    filter = MagiFilter()
                if filter.noop:
                    continue
                # Filtering is provided by to_queryset
                if filter.to_queryset:
                    queryset = filter.to_queryset(self, queryset, request,
                                                  value=self._value_as_string(filter, parameters, field_name))
                else: # Automatic filtering
                    operator_for_multiple = filter.operator_for_multiple or MagiFilterOperator.default_for_field(self.fields[field_name])
                    selectors = filter.selectors if filter.selectors else [field_name]
                    condition = Q()
                    filters, exclude = {}, {}
                    for selector in selectors:
                        # NullBooleanField
                        if isinstance(self.fields[field_name], forms.fields.NullBooleanField):
                            value = self._value_as_nullbool(filter, parameters, field_name)
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
                                        if isinstance(model_field, TextField) or isinstance(model_field, CharField):
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
                            values = self._value_as_list(filter, parameters, field_name, filter.allow_csv)
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
                            filters = { selector: self._value_as_string(filter, parameters, field_name) }
                        condition = condition | Q(**filters)
                    queryset = queryset.filter(condition).exclude(**exclude)
        return queryset

    def _value_as_string(self, filter, parameters, field_name):
        return filter.to_value(parameters[field_name]) if filter.to_value else parameters[field_name]

    def _value_as_nullbool(self, filter, parameters, field_name):
        value = None
        if parameters[field_name] == '2':
            value = True
        elif parameters[field_name] == '3':
            value = False
        return filter.to_value(value) if filter.to_value else value

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
        if 'center' in self.fields:
            if self.is_creating:
                del(self.fields['center'])
            else:
                self.fields['center'].queryset = self.fields['center'].queryset.filter(account=self.instance.id)
        if self.is_creating and 'nickname' in self.fields:
            if len(getAccountIdsFromSession(self.request)) == 0:
                self.fields['nickname'].widget = self.fields['nickname'].hidden_widget()
        if 'default_tab' in self.fields:
            if self.is_creating or not self.collection or not hasattr(self.collection, 'get_profile_account_tabs'):
                del(self.fields['default_tab'])
            else:
                self.fields['default_tab'] = forms.ChoiceField(
                    required=False,
                    choices=BLANK_CHOICE_DASH + [
                        (tab_name, tab['name'])
                        for tab_name, tab in
                        self.collection.get_profile_account_tabs(self.request, RAW_CONTEXT, self.instance).items()
                    ],
                )
        self.previous_level = None
        if 'level' in self.fields and not self.is_creating:
            self.previous_level = self.instance.level
        self.previous_screenshot = None
        if 'screenshot' in self.fields and not self.is_creating:
            self.previous_screenshot = unicode(self.instance.screenshot)

    def clean_screenshot(self):
        new_level = self.cleaned_data.get('level')
        screenshot_image = self.cleaned_data.get('screenshot')
        if (new_level
            and new_level != self.previous_level
            and has_field(self.Meta.model, 'screenshot')
            and new_level >= 200
            and (new_level - (self.previous_level or 0)) >= 10
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
        if commit:
            instance.save()
        return instance

    class Meta(AutoForm.Meta):
        model = models.Account
        fields = '__all__'
        save_owner_on_creation = True

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
    password = forms.CharField(widget=forms.PasswordInput(), min_length=6, label=t['Password'])

    class Meta(_UserCheckEmailUsernameForm.Meta):
        model = models.User
        fields = ('username', 'email', 'password')

class UserForm(_UserCheckEmailUsernameForm):
    class Meta(_UserCheckEmailUsernameForm.Meta):
        model = models.User
        fields = ('username', 'email',)

class EmailsPreferencesForm(MagiForm):
    def __init__(self, *args, **kwargs):
        super(EmailsPreferencesForm, self).__init__(*args, **kwargs)
        turned_off = self.request.user.preferences.email_notifications_turned_off
        for (type, message) in models.Notification.MESSAGES:
            value = True
            if type in turned_off:
                value = False
            self.fields['email{}'.format(type)] = forms.BooleanField(required=False, label=_(message['title']), initial=value)

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

class UserPreferencesForm(MagiForm):
    color = forms.ChoiceField(required=False, choices=[], label=_('Color'))
    default_tab = forms.ChoiceField(
        required=False,
        choices=BLANK_CHOICE_DASH + [
            (tab_name, tab['name'])
            for tab_name, tab in PROFILE_TABS.items()
        ],
    )

    def __init__(self, *args, **kwargs):
        super(UserPreferencesForm, self).__init__(*args, **kwargs)
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
        self.fields['location'].help_text = mark_safe(u'{} <a href="/map/" target="_blank">{}</a>'.format(
            unicode(self.fields['location'].help_text),
            unicode(_(u'Open {thing}')).format(thing=_('Map')))
        )
        if USER_COLORS:
            self.fields['color'].choices = BLANK_CHOICE_DASH + [(name, localized_name) for (name, localized_name, css_color, hex_color) in USER_COLORS]
            if self.instance:
                self.fields['color'].initial = self.instance.color
        else:
            self.fields.pop('color')
        self.old_location = self.instance.location if self.instance else None
        if not getMagiCollection('activity'):
            del(self.fields['view_activities_language_only'])

    def clean_birthdate(self):
        if 'birthdate' in self.cleaned_data:
            if self.cleaned_data['birthdate'] and self.cleaned_data['birthdate'] > datetime.date.today():
                raise forms.ValidationError(_('This date cannot be in the future.'))
        return self.cleaned_data['birthdate']

    def clean(self):
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
        fields = ('description', 'location', 'favorite_character1', 'favorite_character2', 'favorite_character3', 'color', 'birthdate','i_language', 'view_activities_language_only', 'default_tab')

class StaffEditUser(_UserCheckEmailUsernameForm):
    force_remove_avatar = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        preferences_fields = ('description', 'location', 'i_status', 'donation_link', 'donation_link_title')
        preferences_initial = model_to_dict(instance.preferences, preferences_fields) if instance is not None else {}
        super(StaffEditUser, self).__init__(initial=preferences_initial, instance=instance, *args, **kwargs)
        self.fields.update(fields_for_model(models.UserPreferences, preferences_fields))
        self.fields['i_status'] = forms.ChoiceField(
            required=False,
            choices=(BLANK_CHOICE_DASH + [(c[0], c[1]) if isinstance(c, tuple) else (c, c) for c in instance.preferences.STATUS_SOFT_CHOICES]),
            label=self.fields['i_status'].label,
        )
        self.fields['donation_link_title'].help_text = 'If the donator is not interested in adding a link but are eligible for it, write "Not interested" and leave ""Donation link" empty'
        self.old_location = instance.preferences.location if instance else None
        if not self.is_creating:
            self.fields['force_remove_avatar'].help_text = mark_safe('Check this box if the avatar is inappropriate. It will force the default avatar. <img src="{avatar_url}" alt="{username}" height="40" width="40">'.format(avatar_url=instance.image_url, username=instance.username))

    def save(self, commit=True):
        instance = super(StaffEditUser, self).save(commit=False)
        if self.cleaned_data['force_remove_avatar'] and instance.email:
            splitEmail = instance.email.split('@')
            localPart = splitEmail.pop(0)
            instance.email = localPart.split('+')[0] + u'+' + randomString(4) + '@' + ''.join(splitEmail)
        if self.old_location != self.cleaned_data['location']:
            instance.preferences.location = self.cleaned_data['location']
            instance.preferences.location_changed = True
            instance.preferences.latitude = None
            instance.preferences.longitude = None
        instance.preferences.description = self.cleaned_data['description']
        instance.preferences.i_status = self.cleaned_data['i_status']
        instance.preferences.donation_link = self.cleaned_data['donation_link']
        instance.preferences.donation_link_title = self.cleaned_data['donation_link_title']
        instance.preferences.save()
        if commit:
            instance.save()
        return instance

    class Meta(_UserCheckEmailUsernameForm.Meta):
        model = models.User
        fields = ('username', 'email')

class ChangePasswordForm(MagiForm):
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

############################################################
# User links

class AddLinkForm(MagiForm):
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

############################################################
# Change language (on top bar)

class LanguagePreferencesForm(MagiForm):
    class Meta(MagiForm.Meta):
        model = models.UserPreferences
        fields = ('i_language',)

############################################################
# Confirm delete - works with everything

class ConfirmDelete(forms.Form):
    confirm = forms.BooleanField(required=True, initial=False, label=_('Confirm'))
    thing_to_delete = forms.IntegerField(widget=forms.HiddenInput, required=True)

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
            if 'help' in RAW_CONTEXT['all_enabled']:
                self.fields['value'].help_text = mark_safe(u'{} <a href="/help/Markdown" target="_blank">{}.</a>'.format(_(u'You may use Markdown formatting.'), _(u'Learn more')))
            else:
                self.fields['value'].help_text = _(u'You may use Markdown formatting.')

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

class StaffConfigurationSimpleEditForm(StaffConfigurationForm):
    class Meta(StaffConfigurationForm.Meta):
        fields = ('verbose_key', 'value')

class StaffConfigurationFilters(MagiFiltersForm):
    search_fields = ['verbose_key', 'value']

    has_value = forms.NullBooleanField()
    has_value_filter = MagiFilter(selector='value__isnull')

    i_language_filter = MagiFilter(to_queryset=lambda form, queryset, request, value: queryset.filter(
        Q(i_language=value) | Q(i_language__isnull=True) | Q(i_language='')))

    class Meta(MagiFiltersForm.Meta):
        model = models.StaffConfiguration
        fields = ('search', 'i_language', 'has_value')

############################################################
# Activity form

class ActivityForm(MagiForm):
    def __init__(self, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
        self.fields['i_language'].initial = self.request.user.preferences.language if self.request.user.is_authenticated() and self.request.user.preferences.language else django_settings.LANGUAGE_CODE
        if 'message' in self.fields:
            if 'help' in RAW_CONTEXT['all_enabled']:
                self.fields['message'].help_text = mark_safe(u'{} <a href="/help/Markdown" target="_blank">{}.</a>'.format(_(u'You may use Markdown formatting.'), _(u'Learn more')))
            else:
                self.fields['message'].help_text = _(u'You may use Markdown formatting.')

    class Meta(MagiForm.Meta):
        model = models.Activity
        fields = ('message', 'c_tags', 'i_language', 'image')
        save_owner_on_creation = True

class FilterActivities(MagiFiltersForm):
    search_fields = ['message', 'c_tags']
    ordering_fields = [
        ('modification', _('Last Update')),
        ('creation', _('Creation')),
        ('total_likes,creation', string_concat(_('Most Popular'), ' (', _('All time'), ')')),
        ('total_likes,id', string_concat(_('Most Popular'), ' (', _('This week'), ')')),
    ]

    with_image = forms.NullBooleanField(label=_('Image'))
    with_image_filter = MagiFilter(selector='image__isnull')

    owner_id = forms.IntegerField(widget=forms.HiddenInput)

    def filter_queryset(self, queryset, parameters, request):
        queryset = super(FilterActivities, self).filter_queryset(queryset, parameters, request)
        if 'feed' in parameters and request.user.is_authenticated():
            queryset = queryset.filter(Q(owner__in=request.user.preferences.following.all()) | Q(owner_id=request.user.id))
        elif request.user.is_authenticated() and request.user.preferences.view_activities_language_only:
            queryset = queryset.filter(language=request.LANGUAGE_CODE)
        elif ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT:
            queryset = queryset.filter(language=request.LANGUAGE_CODE)
        if 'ordering' in parameters and parameters['ordering'] == 'total_likes,id':
            queryset = queryset.filter(modification__gte=timezone.now() - relativedelta(weeks=1))
        return queryset

    class Meta(MagiFiltersForm.Meta):
        model = models.Activity
        fields = ('search', 'c_tags', 'with_image', 'i_language')

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
        self.fields['staff'].queryset = self.fields['staff'].queryset.filter(is_staff=True)

    class Meta(MagiFiltersForm.Meta):
        model = models.Report
        fields = ('i_status', 'reported_thing', 'staff')

############################################################
# Donation Months forms

class DonateForm(AutoForm):
    class Meta(AutoForm.Meta):
        model = models.DonationMonth
        fields = '__all__'
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
