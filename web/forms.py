import re, datetime
from collections import OrderedDict
from multiupload.fields import MultiFileField
from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH, FieldDoesNotExist
from django.db.models import Q
from django.forms.models import model_to_dict, fields_for_model
from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login as login_action
from django.utils.translation import ugettext_lazy as _, string_concat, get_language, activate as translation_activate
from django.utils.safestring import mark_safe
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.shortcuts import get_object_or_404
from web.django_translated import t
from web import models
from web.settings import FAVORITE_CHARACTER_NAME, FAVORITE_CHARACTERS, ACTIVITY_TAGS, USER_COLORS, GAME_NAME, ON_PREFERENCES_EDITED
from web.utils import ordinalNumber, randomString, shrinkImageFromData, getMagiCollection

############################################################
# Internal utils

class MultiImageField(MultiFileField, forms.ImageField):
    pass

class DateInput(forms.DateInput):
    input_type = 'date'

def date_input(field):
    field.widget = DateInput()
    field.widget.attrs.update({
        'class': 'calendar-widget',
        'data-role': 'data',
    })
    field.help_text = 'mm-dd-yyyy'
    return field

def has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False

############################################################
# Recommended form for any MagiCollection item
# - Will make fields in `optional_fields` optional, regardless of db field
# - Will show the correct date picker for date fields
# - Will replace any empty string with None for better database consistency
# - Will use tinypng to optimize images and will use settings specified in models
# - When `save_owner_on_creation` is True in Meta form object, will save the field `owner` using the current user

class MagiForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.collection = kwargs.pop('collection', None)
        self.form_type = kwargs.pop('type', None)
        super(MagiForm, self).__init__(*args, **kwargs)
        self.is_creating = not hasattr(self, 'instance') or not self.instance.pk
        # Fix optional fields
        if hasattr(self.Meta, 'optional_fields'):
            for field in self.Meta.optional_fields:
                if field in self.fields:
                    self.fields[field].required = False
        # Fix dates fields
        for name, field in self.fields.items():
            if isinstance(field, forms.DateField):
                self.fields[name] = date_input(field)

    def save(self, commit=True):
        instance = super(MagiForm, self).save(commit=False)
        # Save owner on creation if specified
        if hasattr(self.Meta, 'save_owner_on_creation') and self.Meta.save_owner_on_creation and self.is_creating:
            instance.owner = self.request.user if self.request.user.is_authenticated() else None
        for field in self.fields.keys():
            # Fix empty strings to None
            if (hasattr(instance, field)
                and isinstance(self.fields[field], forms.Field)
                and has_field(instance, field)
                and (isinstance(getattr(instance, field), unicode) or isinstance(getattr(instance, field), str))
                and getattr(instance, field) == ''):
                setattr(instance, field, None)
            # Shrink images
            if (hasattr(instance, field)
                and isinstance(self.fields[field], forms.Field)
                and has_field(instance, field)
                and type(self.Meta.model._meta.get_field(field)) == models.models.ImageField):
                image = self.cleaned_data[field]
                if image and (isinstance(image, InMemoryUploadedFile) or isinstance(image, TemporaryUploadedFile)):
                    filename = image.name
                    image = shrinkImageFromData(image.read(), filename, settings=getattr(instance._meta.model, 'tinypng_settings', {}).get(field, {}))
                    image.name = instance._meta.model._meta.get_field('image').upload_to(instance, filename)
                    setattr(instance, field, image)
        if commit:
            instance.save()
        return instance

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
    """
    def __init__(self,
                 to_queryset=None,
                 selector=None,
                 selectors=None,
                 to_value=None,
                 multiple=True,
    ):
        self.to_queryset = to_queryset
        self.selectors = selectors
        if not self.selectors and selector:
            self.selectors = [selector]
        self.to_value = to_value
        self.multiple = multiple

def filter_ids(queryset, request):
    if 'ids' in request.GET and request.GET['ids'] and request.GET['ids'].replace(',', '').isdigit():
        queryset = queryset.filter(pk__in=request.GET['ids'].split(','))
    return queryset

class MagiFiltersForm(MagiForm):

    def __init__(self, *args, **kwargs):
        super(MagiFiltersForm, self).__init__(*args, **kwargs)
        # Remove search from form if search_fields is not specified
        if not hasattr(self, 'search_fields') and not hasattr(self, 'search_fields_exact'):
            del(self.fields['search'])
        # Mark all fields as not required
        for field in self.fields.values():
            field.required = False

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

    search = forms.CharField(required=False, label=t['Search'])
    search_filter = MagiFilter(to_queryset=_search_to_queryset)

    def filter_queryset(self, queryset, parameters, request):
        # Generic filter for ids
        queryset = filter_ids(queryset, request)
        # Go through form fields
        hidden_filters = getattr(self, 'hidden_filters', {})
        for field_name in self.fields.keys() + hidden_filters.keys():
            if field_name in ['ordering', 'page', 'reverse_order']:
                continue
            if field_name in parameters and parameters[field_name] != '':
                if field_name in hidden_filters:
                    hidden = True
                    filter = hidden_filters[field_name]
                else:
                    hidden = False
                    filter = getattr(self, '{}_filter'.format(field_name), None)
                if not filter:
                    filter = MagiFilter()
                if filter.to_queryset:
                    queryset = filter.to_queryset(self, queryset, request, value=parameters[field_name])
                else:
                    value = filter.to_value(parameters[field_name]) if filter.to_value else parameters[field_name]
                    selectors = filter.selectors if filter.selectors else [field_name]
                    condition = Q()
                    for selector in selectors:
                        if not hidden and isinstance(self.fields[field_name], forms.fields.NullBooleanField):
                            if value == '2':
                                filters = { selector: True }
                            elif value == '3':
                                filters = { selector: False }
                            else:
                                filters = {}
                        else:
                            if filter.multiple:
                                filters = { '{}__in'.format(selector): value.split(',') }
                            else:
                                filters = { selector: value }
                        condition = condition | Q(**filters)
                    queryset = queryset.filter(condition)
        return queryset

############################################################
############################################################

############################################################
# Accounts forms

class AccountForm(AutoForm):
    class Meta:
        model = models.Account
        fields = '__all__'
        save_owner_on_creation = True

############################################################
# Users forms

class _UserCheckEmailUsernameForm(MagiForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and models.User.objects.filter(email__iexact=email).exclude(username=self.request.user.username).count():
            raise forms.ValidationError(
                message=t["%(model_name)s with this %(field_labels)s already exists."],
                code='unique_together',
                params={'model_name': t['User'], 'field_labels': t['Email']},
            )
        return email.lower()

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if re.search(r'^\d+$', username):
            raise forms.ValidationError(
                message=t["%(field_labels)s can\'t contain only digits."],
                code='unique_together',
                params={'field_labels': t['Username']},
            )
        if models.User.objects.filter(username__iexact=username).exclude(username__exact=username).count():
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

    class Meta:
        model = models.User
        fields = ('username', 'email', 'password')

class UserForm(_UserCheckEmailUsernameForm):
    class Meta:
        model = models.User
        fields = ('username', 'email',)

class EmailsPreferencesForm(MagiForm):
    def __init__(self, *args, **kwargs):
        super(EmailsPreferencesForm, self).__init__(*args, **kwargs)
        turned_off = self.request.user.preferences.email_notifications_turned_off
        for (type, sentence) in models.NOTIFICATION_TITLES.items():
            value = True
            if type in turned_off:
                value = False
            self.fields['email{}'.format(type)] = forms.BooleanField(required=False, label=_(sentence), initial=value)

    def save(self, commit=True):
        new_emails_settings = []
        for type in models.NOTIFICATION_TITLES.keys():
            if not self.cleaned_data.get('email{}'.format(type), False):
                new_emails_settings.append(type)
        self.request.user.preferences.save_email_notifications_turned_off(new_emails_settings)
        if commit:
            self.request.user.preferences.save()
        return self.request.user.preferences

    class Meta:
        model = models.UserPreferences
        fields = []

class UserPreferencesForm(MagiForm):
    color = forms.ChoiceField(required=False, choices=[], label=_('Color'))

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
        self.fields['language'].choices = [l for l in self.fields['language'].choices if l[0]]
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

    class Meta:
        model = models.UserPreferences
        fields = ('description', 'location', 'favorite_character1', 'favorite_character2', 'favorite_character3', 'color', 'birthdate','language', 'view_activities_language_only')

class StaffEditUser(MagiForm):
    force_remove_avatar = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        preferences_fields = ('description', 'location', 'i_status', 'donation_link', 'donation_link_title')
        preferences_initial = model_to_dict(instance.preferences, preferences_fields) if instance is not None else {}
        super(StaffEditUser, self).__init__(initial=preferences_initial, instance=instance, *args, **kwargs)
        self.fields.update(fields_for_model(models.UserPreferences, preferences_fields))
        self.fields['i_status'].required = False
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

    class Meta:
        model = models.User
        fields = ('username', )

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

    class Meta:
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
            models.updateCachedActivities(self.request.user.id)
            if ON_PREFERENCES_EDITED:
                ON_PREFERENCES_EDITED(self.request)
        return instance

    class Meta:
        model = models.UserLink
        fields = ('i_type', 'value', 'i_relevance')
        save_owner_on_creation = True

############################################################
# Change language (on top bar)

class LanguagePreferencesForm(MagiForm):
    class Meta:
        model = models.UserPreferences
        fields = ('language',)

############################################################
# Confirm delete - works with everything

class ConfirmDelete(forms.Form):
    confirm = forms.BooleanField(required=True, initial=False, label=_('Confirm'))
    thing_to_delete = forms.IntegerField(widget=forms.HiddenInput, required=True)

############################################################
# Activity form

class ActivityForm(MagiForm):
    tags = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[],
        label=_('Tags'),
    )

    def __init__(self, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
        self.fields['language'].initial = self.request.user.preferences.language if self.request.user.is_authenticated() and self.request.user.preferences.language else django_settings.LANGUAGE_CODE
        if ACTIVITY_TAGS:
            self.fields['tags'].choices = ACTIVITY_TAGS
            if self.instance:
                self.fields['tags'].initial = self.instance.tags
        else:
            self.fields.pop('tags')

    def save(self, commit=True):
        instance = super(ActivityForm, self).save(commit=False)
        if 'tags' in self.cleaned_data:
            instance.save_tags(self.cleaned_data['tags'])
        if commit:
            instance.save()
        return instance

    class Meta:
        model = models.Activity
        fields = ('message', 'tags', 'language', 'image')
        save_owner_on_creation = True

class FilterActivities(MagiForm):
    tags = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[],
        label=_('Tags'),
    )
    search = forms.CharField(required=False, label=t['Search'])
    with_image = forms.NullBooleanField(required=False, initial=None, label=_('Image'))
    ordering = forms.ChoiceField(choices=[
        ('modification', _('Last Update')),
        ('creation', _('Creation')),
        ('total_likes,creation', string_concat(_('Most Popular'), ' (', _('All time'), ')')),
        ('total_likes,id', string_concat(_('Most Popular'), ' (', _('This week'), ')')),
    ], initial='modification', required=False, label=_('Ordering'))
    reverse_order = forms.BooleanField(initial=True, required=False, label=_('Reverse order'))

    def __init__(self, *args, **kwargs):
        super(FilterActivities, self).__init__(*args, **kwargs)
        self.fields['language'].required = False
        if ACTIVITY_TAGS:
            self.fields['tags'].choices = ACTIVITY_TAGS
            if self.instance:
                self.fields['tags'].initial = self.instance.tags
        else:
            self.fields.pop('tags')

    class Meta:
        model = models.Activity
        fields = ('search', 'tags', 'with_image', 'language', 'ordering', 'reverse_order')

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

    class Meta:
        model = models.Report
        fields = ('reason', 'message', 'images')
        save_owner_on_creation = True

class FilterReports(MagiForm):
    reported_thing = forms.ChoiceField(
        required=False,
        choices=[],
    )

    def __init__(self, *args, **kwargs):
        super(FilterReports, self).__init__(*args, **kwargs)
        self.fields['i_status'].required = False
        self.fields['i_status'].initial = models.REPORT_STATUS_PENDING
        self.fields['staff'].required = False
        self.fields['staff'].queryset = self.fields['staff'].queryset.filter(is_staff=True)
        self.fields['reported_thing'].choices = BLANK_CHOICE_DASH + [ (name, info['title']) for name, info in self.collection.types.items() ]

    class Meta:
        model = models.Report
        fields = ('i_status', 'reported_thing', 'staff')

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

    class Meta:
        model = models.Badge
        optional_fields = ('donation_month', 'url')
        save_owner_on_creation = True

class ExclusiveBadgeForm(_BadgeForm):
    class Meta(_BadgeForm.Meta):
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
        instance.image = self.badge.image
        if commit:
            instance.save()
        return instance

    class Meta(_BadgeForm.Meta):
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
