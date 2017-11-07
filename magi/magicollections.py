import string, datetime, random
from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _, string_concat
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.formats import dateformat
from django.core.exceptions import PermissionDenied
from django.http import Http404
from dateutil.relativedelta import relativedelta
from django.db.models import Count, Q, Prefetch

from magi.views import indexExtraContext
from magi.utils import AttrDict, ordinalNumber, justReturn, getMagiCollections, getMagiCollection, CuteFormType, CuteFormTransform, redirectWhenNotAuthenticated, custom_item_template
from magi.raw import please_understand_template_sentence, donators_adjectives
from magi.django_translated import t
from magi.middleware.httpredirect import HttpRedirectException
from magi.settings import ACCOUNT_MODEL, SHOW_TOTAL_ACCOUNTS, PROFILE_TABS, FAVORITE_CHARACTERS, FAVORITE_CHARACTER_NAME, FAVORITE_CHARACTER_TO_URL, GET_GLOBAL_CONTEXT, DONATE_IMAGE, ON_USER_EDITED, ON_PREFERENCES_EDITED
from magi.item_model import AccountAsOwnerModel
from magi import models, forms

############################################################
# MagiCollection interface

class _View(object):
    """
    Class used inside MagiCollection for common variables inside views
    """

    def __init__(self, collection):
        self.collection = collection

    # Optional variables without default
    js_files = []
    extra_context = None
    shortcut_urls = []
      # ListView/AddView: List of URLs
      # AddView with types: List or (url, type) or list of URLs
      # ItemView/EditView: List of (url, pk) or list of URLs

    # Optional variables with default values
    ajax_callback = None
    enabled = True
    logout_required = False
    staff_required = False
    ajax = True

    def get_global_context(self, request):
        return GET_GLOBAL_CONTEXT(request)

    def share_image(self, context, item):
        return self.collection.share_image(context, item)

    def get_queryset(self, queryset, parameters, request):
        return self.collection.get_queryset(queryset, parameters, request)

    def check_permissions(self, request, context):
        if not self.enabled:
            raise Http404
        if self.logout_required and request.user.is_authenticated():
            raise PermissionDenied()
        if self.authentication_required:
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
        if self.staff_required:
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
            if not request.user.is_staff:
                raise PermissionDenied()

    def check_owner_permissions(self, request, context, item):
        if item.owner_id and getattr(self, 'owner_only', False):
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
            if not request.user.is_staff and item.owner_id != request.user.id:
                raise PermissionDenied()

    #######################
    # Tools - not meant to be overriden

    def has_permissions(self, request, context, item=None):
        try:
            self.check_permissions(request, context)
            if item:
                self.check_owner_permissions(request, context, item)
        except (PermissionDenied, HttpRedirectException, Http404):
            return False
        return True

class MagiCollection(object):
    # Required variables
    @property
    def queryset(self): raise NotImplementedError('Queryset is required in a MagiCollection')

    # Optional variables without default
    icon = None
    image = None
    navbar_link_list = None
    navbar_link_list_divider_before = False
    navbar_link_list_divider_after = False
    types = None
    filter_cuteform = None
    collectible = None

    # Optional variables with default values
    @property
    def name(self):
        return self.__class__.__name__.lower().replace('collection', '')

    @property
    def navbar_link_title(self):
        return self.plural_title

    def get_queryset(self, queryset, parameters, request):
        return queryset

    def form_class(self, request, context):
        class AutoForm(forms.AutoForm):
            class Meta:
                model = self.queryset.model
        return AutoForm

    def collectible_to_class(self, cls):
        return cls

    enabled = True
    navbar_link = True
    multipart = False

    reportable = True
    report_edit_templates = {}
    report_delete_templates = {}
    report_allow_edit = True
    report_allow_delete = True

    @property
    def plural_name(self):
        return '{}s'.format(self.name)

    @property
    def title(self):
        return string.capwords(self.name)

    @property
    def plural_title(self):
        return string.capwords(self.plural_name)

    def share_image(self, context, item):
        return self.image

    def to_fields(self, item, to_dict=True, only_fields=None, in_list=False, icons={}, images={}):
        """
        Used only when template = 'default' or when 'ordering' is specified in a list
        Returns a dictionary of dictinaries with:
        - verbose_name
        - value
        - type
        - optional: icon, image, link, link_text, ajax_link
        Takes an object that inherits from MagiModel and returns a dictionary of field name -> value
        Available types:
        - text
        - title_text (needs 'title')
        - image
        - bool
        - link (needs 'link_text')
        - image_link (needs 'link', 'link_text')
        - button (needs 'link_text')
        - text_with_link (needs 'link' and 'link_text', will show a 'View all' button)
        - timezone_datetime (useful when showing another timezone, otherwise use text. needs 'timezones' list. can be 'local')
        - long_text
        - html
        Optional parameters:
        - to_dict will return a dict by default, otherwise a list or pair. Useful if you plan to change the order or insert items at certain positions.
        - only_fields if specified will ignore any other field
        - icons is a dictionary of the icons associated with the fields
        - images is a dictionary of the images associated with the fields
        """
        name_fields = []
        many_fields = []
        # Fields from reverse
        for (field_name, url, verbose_name) in getattr(item, 'reverse_related', []):
            if only_fields and field_name not in only_fields:
                continue
            try:
                total = getattr(item, 'cached_total_{}'.format(field_name))
            except AttributeError:
                continue
            if total:
                many_fields.append((field_name, {
                    'verbose_name': verbose_name,
                    'type': 'text_with_link',
                    'value': u'{total} {items}'.format(total=total, items=_(verbose_name).lower()),
                    'ajax_link': u'/ajax/{}/?{}_id={}&ajax_modal_only'.format(url, item.collection_name, item.pk),
                    'link': u'/{}/?{}_id={}'.format(url, item.collection_name, item.pk),
                    'link_text': _('View all'),
                    'icon': icons.get(field_name, None),
                    'image': images.get(field_name, None),
                }))
        model_fields = []
        # Fields from model
        for field in item._meta.fields:
            field_name = field.name
            if (field_name.startswith('_')
                or field_name in ['id', 'owner', 'owner_id']
                or field_name == 'image'):
                continue
            if only_fields and field_name not in only_fields:
                continue
            if field_name.startswith('i_'):
                field_name = field_name[2:]
            is_foreign_key = (isinstance(field, models.models.ForeignKey)
                              or isinstance(field, models.models.OneToOneField))
            value = None
            if not is_foreign_key:
                try:
                    value = getattr(item, field_name, None)
                except AttributeError:
                    continue
                if value is None:
                    continue
            d = {
                'verbose_name': getattr(field, 'verbose_name', _(field_name.capitalize())),
                'value': value,
                'icon': icons.get(field_name, None),
                'image': images.get(field_name, None),
            }
            if is_foreign_key:
                try:
                    d['type'] = 'text_with_link'
                    d['value'] = getattr(item, 'cached_' + field_name).unicode
                    d['link'] = getattr(item, 'cached_' + field_name).item_url
                    d['ajax_link'] = getattr(item, 'cached_' + field_name).ajax_item_url
                    d['link_text'] = unicode(_(u'Open {thing}')).format(thing=d['verbose_name'])
                except AttributeError:
                    continue
            elif isinstance(field, models.models.ManyToManyField):
                d['type'] = 'text_with_link'
                d['value'] = getattr(item, 'cached_total_' + field_name).unicode
                d['link'] = u'/{}/?{}={}'.format(field_name, item.collection_name, item.pk)
                d['link_text'] = _('View all')
            elif isinstance(field, models.models.ImageField):
                d['type'] = 'image'
                d['value'] = getattr(item, field_name + '_url')
                if not d['value']:
                    continue
            elif (isinstance(field, models.models.BooleanField)
                  or isinstance(field, models.models.NullBooleanField)):
                d['type'] = 'bool'
            elif isinstance(field, models.models.FileField):
                d['type'] = 'link'
                d['link_text'] = t['Download']
            else:
                d['type'] = 'text'
            if d['type'] == 'text_with_link':
                many_fields.append((field_name, d))
            elif field_name in ['name', 'japanese_name', 'romaji_name', 'english_name', 'translated_name']:
                name_fields.append((field_name, d))
            else:
                model_fields.append((field_name, d))
        fields = name_fields + many_fields + model_fields
        return OrderedDict(fields) if to_dict else fields

    #######################
    # Tools - not meant to be overriden

    def get_list_url(self, ajax=False):
        return u'{}/{}/'.format('' if not ajax else '/ajax', self.plural_name)

    def get_add_url(self, ajax=False, type=None):
        return u'{}/{}/add/{}'.format(
            '' if not ajax else '/ajax',
            self.plural_name,
            u'{}/'.format(type) if type else '',
        )

    @property
    def collectible_with_accounts(self):
        return issubclass(self.collectible.__class__, AccountAsOwnerModel) # todo: test, not sure which one works
        return issubclass(self.collectible, AccountAsOwnerModel)

    @property
    def add_sentence(self):
        return _(u'Add {thing}').format(thing=self.title.lower())

    @property
    def edit_sentence(self):
        return _(u'Edit {thing}').format(thing=self.title.lower())

    #######################
    # Collection Views

    class ListView(_View):
        # Optional variables without default
        filter_form = None
        ajax_pagination_callback = None
        foreach_items = None
        #def foreach_items(self, index, item, context):
        before_template = None
        after_template = None
        no_result_template = None

        def extra_context(self, context):
            pass

        # Optional variables with default values
        per_line = 3
        col_break = 'md'
        page_size = 12
        show_edit_button = True
        show_collect_button = True
        authentication_required = False
        distinct = True
        add_button_subtitle = _('Become a contributor to help us fill the database')
        show_title = False
        full_width = False
        show_relevant_fields_on_ordering = True
        hide_sidebar = False
        item_template = 'default_item_in_list'

        def show_add_button(self, request):
            return True

        @property
        def filter_cuteform(self):
            return self.collection.filter_cuteform

        @property
        def default_ordering(self):
            if hasattr(self.collection.queryset.model, 'creation'):
                return '-creation'
            return '-id'

        #######################
        # Tools - not meant to be overriden

        def get_page_title(self):
            return self.collection.plural_title

        @property
        def plain_default_ordering(self):
            default_ordering = self.default_ordering.split(',')[0]
            return default_ordering[1:] if default_ordering.startswith('-') else default_ordering

    class ItemView(_View):
        # Optional variables without default
        top_illustration = None

        def extra_context(self, context):
            pass

        reverse_url = None
        #def reverse_url(self, text):
        # Returns a dictionary that will be used with the queryset to get a single item

        # Optional variables with default values
        authentication_required = False
        owner_only = False
        show_edit_button = True
        show_collect_button = True
        comments_enabled = True
        template = 'default'

        def share_image(self, context, item):
            if hasattr(item, 'http_image_url'):
                return item.http_image_url
            return self.collection.share_image(context, item)

        def get_item(self, request, pk):
            return { 'pk': pk }

        #######################
        # Tools - not meant to be overriden

        def get_page_title(self, item=None):
            if item:
                return u'{}: {}'.format(self.collection.title, unicode(item))
            return self.collection.title

    class AddView(_View):
        # Optional variables without default
        otherbuttons_template = None
        after_template = None

        def before_save(self, request, instance, type=None):
            return instance

        def after_save(self, request, instance, type=None):
            return instance

        def extra_context(self, context):
            pass

        # Optional variables with default values
        authentication_required = True
        savem2m = False
        allow_next = True
        alert_duplicate = True
        back_to_list_button = True

        @property
        def filter_cuteform(self):
            return self.collection.filter_cuteform

        @property
        def multipart(self):
            return self.collection.multipart

        def form_class(self, request, context):
            if str(type(self.collection.form_class)) == '<type \'instancemethod\'>':
                return self.collection.form_class(request, context)
            return self.collection.form_class

        def redirect_after_add(self, request, item, ajax):
            if self.collection.item_view.enabled:
                return item.item_url if not ajax else item.ajax_item_url
            return self.collection.get_list_url(ajax)

        #######################
        # Tools - not meant to be overriden

        def get_page_title(self):
            return self.collection.add_sentence

    class EditView(_View):
        # Optional variables without default
        otherbuttons_template = None
        after_template = None

        def before_save(self, request, instance, type=None):
            return instance

        def after_save(self, request, instance, type=None):
            return instance

        def extra_context(self, context):
            pass

        # Optional variables with default values
        authentication_required = True
        allow_delete = False
        owner_only = True
        savem2m = False
        back_to_list_button = True

        @property
        def filter_cuteform(self):
            return self.collection.filter_cuteform

        @property
        def multipart(self):
            return self.collection.multipart

        def form_class(self, request, context):
            if str(type(self.collection.form_class)) == '<type \'instancemethod\'>':
                return self.collection.form_class(request, context)
            return self.collection.form_class

        def redirect_after_edit(self, request, item, ajax):
            if self.collection.item_view.enabled:
                return item.item_url if not ajax else item.ajax_item_url
            return self.collection.get_list_url(ajax)

        def redirect_after_delete(self, request, item, ajax):
            return self.collection.get_list_url(ajax)

        def get_item(self, request, pk):
            return { 'pk': pk }

        #######################
        # Tools - not meant to be overriden

        def get_page_title(self, item=None):
            if item:
                return u'{}: {}'.format(item.edit_sentence, unicode(item))
            return self.collection.edit_sentence

############################################################
############################################################
############################################################

############################################################
# Account Collection

class AccountCollection(MagiCollection):
    title = _('Account')
    plural_title = _('Accounts')
    navbar_link_title = _('Leaderboard')
    icon = 'users'
    queryset = ACCOUNT_MODEL.objects.all().select_related('owner', 'owner__preferences')
    report_allow_delete = False
    form_class = forms.AccountForm

    @property
    def report_edit_templates(self):
        templates = OrderedDict([
            ('Unrealistic Level', 'Your level is unrealistic, so we edited it. Please provide screenshots of your game to prove it and we\'ll change it back. Thank you for your understanding.'),
        ])
        for field in self.queryset.model._meta.fields:
            if not field.name.startswith('_') and field.name not in ['id', 'owner', 'creation', 'level']:
                name = field.name
                if name.startswith('i_'):
                    name = name[2:]
                name = name.replace('_', ' ').title()
                if isinstance(field, models.models.fields.CharField):
                    templates[u'Inappropriate {}'.format(name)] = 'Your account\'s {} was inappropriate. ' + please_understand_template_sentence.format(name)
        return templates

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        show_title = True
        per_line = 1
        add_button_subtitle = _('Create your account to join the community and be in the leaderboard!')

        def show_add_button(self, request):
            return not request.user.is_authenticated()

        @property
        def default_ordering(self):
            if hasattr(self.collection.queryset.model, 'level'):
                return '-level'
            return MagiCollection.ListView.default_ordering.__get__(self)

    class ItemView(MagiCollection.ItemView):
        template = custom_item_template
        comments_enabled = False

    class AddView(MagiCollection.AddView):
        alert_duplicate = False
        allow_next = False

        def redirect_after_edit(self, request, instance, ajax=False):
            return '{}#{}'.format(request.user.item_url, instance.id)

        def before_save(self, request, instance, type=None):
            instance.owner = request.user
            return instance

    class EditView(MagiCollection.EditView):
        allow_delete = True

        def redirect_after_edit(self, request, instance, ajax=False):
            if ajax:
                return instance.ajax_item_url
            return '{}#{}'.format(request.user.item_url, instance.id)

        def redirect_after_delete(self, request, item, ajax=False):
            return request.user.item_url

############################################################
# User Collection

class UserCollection(MagiCollection):
    title = _('Profile')
    plural_title = _('Players')
    navbar_link = False
    queryset = models.User.objects.all().select_related('preferences')
    report_allow_delete = False
    report_edit_templates = OrderedDict([
        ('Inappropriate profile picture', 'Your profile picture is inappropriate. ' + please_understand_template_sentence + ' To change your avatar, go to gravatar and upload a new image, then go to your settings on our website to re-enter your email address.'),
        ('Inappropriate image in profile description', 'An image on your profile description was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate link', 'A link on your profile description was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate profile description', 'Something you wrote on your profile was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate location', 'Your location was inappropriate. ' + please_understand_template_sentence),
    ])
    report_delete_templates = {
        'Inappropriate behavior towards other user(s)': 'We noticed that you\'ve been acting in an inappropriate manner towards other user(s), which doesn\'t correspond to what we expect from our community members. Your profile, accounts, activities and everything else you owned on our website has been permanently deleted, and we kindly ask you not to re-iterate your actions.',
        'Spam': 'We detected spam activities from your user profile. Your profile, accounts, activities and everything else you owned on our website has been permanently deleted, and we kindly ask you not to re-iterate your actions.',
    }

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        default_ordering = 'username'
        per_line = 6
        page_size = 30

        def get_queryset(self, queryset, parameters, request):
            if 'followers_of' in parameters:
                queryset = queryset.filter(preferences__following__username=parameters['followers_of'])
            if 'followed_by' in parameters:
                queryset = queryset.filter(followers__user__username=parameters['followed_by'])
            if 'liked_activity' in parameters:
                queryset = queryset.filter(Q(pk__in=(models.Activity.objects.get(pk=parameters['liked_activity']).likes.all())) | Q(activities__id=parameters['liked_activity']))
            return queryset

        def extra_context(self, context):
            return context

    class ItemView(MagiCollection.ItemView):
        template = 'profile'
        js_files = ['profile']
        comments_enabled = False
        show_edit_button = False
        ajax = False
        shortcut_urls = [
            ('me', 'me'),
        ]

        def get_item(self, request, pk):
            if pk == 'me':
                if request.user.is_authenticated():
                    pk = request.user.id
                else:
                    raise HttpRedirectException('/signup/')
            return { 'pk': pk }

        def reverse_url(self, text):
            return {
                'username': text,
            }

        def get_queryset(self, queryset, parameters, request):
            if request.user.is_authenticated():
                queryset = queryset.extra(select={
                    'followed': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = {id} AND user_id = auth_user.id'.format(
                        table=models.UserPreferences._meta.db_table,
                        id=request.user.preferences.id,
                    ),
                })
                queryset = queryset.extra(select={
                    'is_followed_by': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = (SELECT id FROM {table} WHERE user_id = auth_user.id) AND user_id = {id}'.format(
                        table=models.UserPreferences._meta.db_table,
                        id=request.user.id,
                    ),
                })
            queryset = queryset.extra(select={
                'total_following': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = (SELECT id FROM {table} WHERE user_id = auth_user.id)'.format(
                    table=models.UserPreferences._meta.db_table,
                ),
                'total_followers': 'SELECT COUNT(*) FROM {table}_following WHERE user_id = auth_user.id'.format(
                    table=models.UserPreferences._meta.db_table,
                ),
            })
            queryset = queryset.select_related('preferences', 'favorite_character1', 'favorite_character2', 'favorite_character3')
            queryset = queryset.prefetch_related(Prefetch('accounts', to_attr='all_accounts'), Prefetch('links', queryset=models.UserLink.objects.order_by('-i_relevance'), to_attr='all_links'))
            return queryset

        def extra_context(self, context):
            user = context['item']
            request = context['request']
            context['is_me'] = user.id == request.user.id

            # Badges
            if 'badge' in context['all_enabled']:
                context['item'].latest_badges = list(context['item'].badges.filter(show_on_top_profile=True).order_by('-date', '-id')[:6])
                if len(context['item'].latest_badges) == 6:
                    context['more_badges'] = True
                context['item'].latest_badges = context['item'].latest_badges[:5]

            # Profile tabs
            context['show_total_accounts'] = SHOW_TOTAL_ACCOUNTS
            context['profile_tabs'] = PROFILE_TABS
            context['profile_tabs_size'] = 100 / len(context['profile_tabs']) if context['profile_tabs'] else 100
            context['opened_tab'] = context['profile_tabs'].keys()[0] if context['profile_tabs'] else None
            if 'open' in request.GET and request.GET['open'] in context['profile_tabs']:
                context['opened_tab'] = request.GET['open']

            # Links
            context['item'].all_links = list(context['item'].all_links)
            meta_links = []
            if FAVORITE_CHARACTERS:
                for i in range(1, 4):
                    if getattr(user.preferences, 'favorite_character{}'.format(i)):
                        link = AttrDict({
                            'type': (_(FAVORITE_CHARACTER_NAME) if FAVORITE_CHARACTER_NAME else _('{nth} Favorite Character')).format(nth=_(ordinalNumber(i))),
                            # May be used by FAVORITE_CHARACTER_TO_URL
                            'raw_value': getattr(user.preferences, 'favorite_character{}'.format(i)),
                            'value': user.preferences.localized_favorite_character(i),
                            'translate_type': False,
                            'image_url': user.preferences.favorite_character_image(i),
                        })
                        link.url = FAVORITE_CHARACTER_TO_URL(link)
                        meta_links.append(AttrDict(link))
            if user.preferences.location:
                latlong = '{},{}'.format(user.preferences.latitude, user.preferences.longitude) if user.preferences.latitude else None
                link = AttrDict({
                    'type': 'Location',
                    'value': user.preferences.location,
                    'translate_type': True,
                    'flaticon': 'world',
                    'url': u'/map/?center={}&zoom=10'.format(latlong) if 'map' in context['all_enabled'] and latlong else u'https://www.google.com/maps?q={}'.format(user.preferences.location),
                })
                meta_links.append(link)
            if user.preferences.birthdate:
                today = datetime.date.today()
                birthday = user.preferences.birthdate.replace(year=today.year)
                if birthday < today:
                    birthday = birthday.replace(year=today.year + 1)
                meta_links.append(AttrDict({
                    'type': 'Birthdate',
                    'value': u'{} ({})'.format(user.preferences.birthdate, _(u'{age} years old').format(age=user.preferences.age)),
                    'translate_type': True,
                    'flaticon': 'event',
                    'url': 'https://www.timeanddate.com/countdown/birthday?iso={date}T00&msg={username}%27s+birthday'.format(date=dateformat.format(birthday, "Ymd"), username=user.username),
                }))
            context['item'].all_links = meta_links + context['item'].all_links
            num_links = len(context['item'].all_links)
            best_links_on_last_line = 0
            for i in range(4, 7):
                links_on_last_line = num_links % i
                if links_on_last_line == 0:
                    context['per_line'] = i
                    break
                if links_on_last_line > best_links_on_last_line:
                    best_links_on_last_line = links_on_last_line
                    context['per_line'] = i

            # Sentences
            activity_collection = getMagiCollection('activity')
            if activity_collection and activity_collection.add_view.has_permissions(request, context):
                context['can_add_activity'] = True
                context['add_activity_sentence'] = activity_collection.add_sentence
                context['add_activity_subtitle'] = activity_collection.list_view.add_button_subtitle
            account_collection = getMagiCollection('account')
            if account_collection and account_collection.add_view.has_permissions(request, context):
                context['can_add_account'] = True
                context['add_account_sentence'] = account_collection.add_sentence
            context['share_sentence'] = _('Check out {username}\'s awesome collection!').format(username=context['item'].username)
            context['share_url'] = context['item'].http_item_url

    class AddView(MagiCollection.AddView):
        enabled = False

    class EditView(MagiCollection.EditView):
        staff_required = True
        form_class = forms.StaffEditUser

        def after_save(self, request, instance):
            models.updateCachedActivities(instance.id)
            if ON_USER_EDITED:
                ON_USER_EDITED(request)
            if ON_PREFERENCES_EDITED:
                ON_PREFERENCES_EDITED(request)
            return instance

        def redirect_after_edit(self, request, item, ajax):
            if ajax: # Ajax is not allowed
                return '/ajax/successedit/'
            return super(UserCollection.EditView, self).redirect_after_edit(request, item, ajax)

############################################################
# Activities Collection

class ActivityCollection(MagiCollection):
    title = _('Activity')
    plural_title = _('Activities')
    plural_name = 'activities'
    queryset = models.Activity.objects.all().annotate(total_likes=Count('likes'))
    navbar_link = False
    icon = 'comments'

    report_edit_templates = OrderedDict([
        ('Incorrect/missing tag', 'Your activity\'s tags have been changed. One or more of the activity\'s tags didn\'t reflect its content, or one or more tags were missing.'),
        ('Wrong language', 'The language you specified for this activity didn\'t reflect its content so it has been changed.'),
        ('Inappropriate image', 'An image in this activity you posted was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate content', 'Something you wrote in this activity was inappropriate. ' + please_understand_template_sentence),
        ('False information', 'Something you wrote in this activity is invalid or doesn\'t have enough available proof to be considered true.'),
        ('Illegal content', 'Something you shared in this activity was illegal so it has been edited.'),
        ('Uncredited fanart', 'You shared an image without the artist\'s permission, so it has been edited. Make sure you only post official art, or ask for permission to the artist and credit them.'),
    ])

    report_delete_templates = OrderedDict([
        ('Troll activity', 'This activity has been detected as being deliberately provocative with the intention of causing disruption or argument and therefore has been deleted. We kindly ask you not to re-iterate your actions and be respectful towards our community.'),
        ('Illegal content', 'Something you shared in this activity was illegal so it has been deleted.'),
        ('Uncredited fanart', 'You shared an image without the artist\'s permission, so your activity has been deleted. Make sure you only post official art, or ask for permission to the artist and credit them.'),
        ('Inappropriate activity', 'This activity was inappropriate. ' + please_understand_template_sentence),
        ('False information', 'Something you wrote in this activity is invalid or doesn\'t have enough available proof to be considered true.'),
        ('Spam activity', 'This activity has been detected as spam. We do not tolerate such behavior and kindly ask you not to re-iterate your actions or your entire profile might get deleted next time.'),
    ])

    def _get_queryset_for_list_and_item(self, queryset, parameters, request):
        if request.user.is_authenticated():
            queryset = queryset.extra(select={
                'liked': 'SELECT COUNT(*) FROM {activity_table_name}_likes WHERE activity_id = {activity_table_name}.id AND user_id = {user_id}'.format(
                    activity_table_name=models.Activity._meta.db_table,
                    user_id=request.user.id,
                ),
            })
        queryset = queryset.annotate(total_likes=Count('likes'))
        return queryset

    filter_cuteform = {
        'i_language': {
            'image_folder': 'language',
        },
        'with_image': {
            'type': CuteFormType.OnlyNone,
        },
    }

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        per_line = 1
        distinct = False
        add_button_subtitle = _('Share your adventures!')
        ajax_pagination_callback = 'updateActivities'
        no_result_template = 'include/activityFollowMessage'
        before_template = 'include/homePage'
        default_ordering = '-modification'
        filter_form = forms.FilterActivities
        hide_sidebar = True
        show_relevant_fields_on_ordering = False
        show_edit_button = False
        shortcut_urls = ['']

        def get_queryset(self, queryset, parameters, request):
            return self.collection._get_queryset_for_list_and_item(queryset, parameters, request)

        def extra_context(self, context):
            super(ActivityCollection.ListView, self).extra_context(context)
            if context.get('shortcut_url', None) == '': # Homepage of the site
                indexExtraContext(context)

    class ItemView(MagiCollection.ItemView):
        template = custom_item_template
        ajax_callback = 'updateActivities'
        show_edit_button = False

        def get_queryset(self, queryset, parameters, request):
            return self.collection._get_queryset_for_list_and_item(queryset, parameters, request)

    class AddView(MagiCollection.AddView):
        multipart = True
        alert_duplicate = False
        form_class = forms.ActivityForm

    class EditView(MagiCollection.EditView):
        multipart = True
        allow_delete = True
        form_class = forms.ActivityForm

############################################################
# Notification Collection

class NotificationCollection(MagiCollection):
    title = _('Notification')
    plural_title = _('Notifications')
    queryset = models.Notification.objects.all()
    navbar_link = False
    reportable = False

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        show_title = True
        per_line = 1
        page_size = 5
        default_ordering = 'seen,-creation,-id'

        def get_queryset(self, queryset, parameters, request):
            if not request.user.is_authenticated():
                raise HttpRedirectException(u'/signup/?next=/notifications/&next_title={}'.format(unicode(_('Notifications'))))
            if 'ajax_modal_only' in parameters:
                queryset = queryset.filter(seen=False)
            return queryset.filter(owner=request.user)

        def extra_context(self, context):
            # Mark notification as read
            to_update = [item.pk for item in context['items'] if not item.seen]
            if to_update:
                updated = models.Notification.objects.filter(pk__in=to_update).update(seen=True)
                if updated:
                    context['request'].user.preferences.unread_notifications -= updated
                    if context['request'].user.preferences.unread_notifications < 0:
                        context['request'].user.preferences.unread_notifications = 0
                    context['request'].user.preferences.save()
            return context

    class ItemView(MagiCollection.ItemView):
        enabled = False

    class AddView(MagiCollection.AddView):
        enabled = False

    class EditView(MagiCollection.EditView):
        enabled = False

############################################################
# Badge Collection

class BadgeCollection(MagiCollection):
    enabled = False
    icon = 'achievement'
    title = _('Badge')
    plural_title = _('Badges')
    navbar_link_list = 'more'
    navbar_link_list_divider_after = True
    queryset = models.Badge.objects.all()
    reportable = False

    types = OrderedDict([
        ('exclusive', {
            'title': 'Create a new exclusive badge',
            'form_class': forms.ExclusiveBadgeForm,
        }),
        ('copy', {
            'title': 'Make a copy from an existing badge',
            'form_class': forms.CopyBadgeForm,
            'show_button': False,
        }),
        ('donator', {
            'title': 'Montly donator badge',
            'form_class': forms.DonatorBadgeForm,
        }),
    ])

    filter_cuteform = {
        'show_on_profile': {
            'type': CuteFormType.YesNo,
            'to_cuteform': lambda k, v: 'checked' if k == 'True' else 'delete',
        },
        'rank': {
            'image_folder': 'badges',
            'to_cuteform': lambda k, v: u'medal{}'.format(k),
            'transform': CuteFormTransform.ImagePath,
        }
    }

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        default_ordering = '-date'
        filter_form = forms.FilterBadges

        def get_queryset(self, queryset, parameters, request):
            if 'of_user' in parameters and parameters['of_user']:
                request.context_show_user = False
            else:
                queryset = queryset.select_related('user', 'user__preferences')
                request.context_show_user = True
            return queryset

        def extra_context(self, context):
            request = context['request']
            context['show_user'] = request.context_show_user

        def check_permissions(self, request, context):
            super(BadgeCollection.ListView, self).check_permissions(request, context)
            if hasattr(request, 'GET') and 'of_user' not in request.GET and not request.user.is_staff:
                raise PermissionDenied()

    class ItemView(MagiCollection.ItemView):
        template = 'badgeInfo'
        comments_enabled = False

        def get_queryset(self, queryset, parameters, request):
            return queryset.select_related('owner')

    class AddView(MagiCollection.AddView):
        staff_required = True
        multipart = True
        alert_duplicate = False

        def extra_context(self, context):
            if hasattr(context['forms']['add'], 'badge'):
                context['alert_message'] = string_concat(_('Badge'), ': ', unicode(context['forms']['add'].badge))
                context['alert_type'] = 'info'
                context['alert_flaticon'] = 'about'
                context['alert_button_string'] = context['forms']['add'].badge.open_sentence
                context['alert_button_link'] = context['forms']['add'].badge.item_url

    class EditView(MagiCollection.EditView):
        staff_required = True
        multipart = True
        allow_delete = True

############################################################
# Report Collection

class ReportCollection(MagiCollection):
    navbar_link_list = 'more'
    navbar_link_list_divider_before = True
    icon = 'fingers'
    queryset = models.Report.objects.all().select_related('owner', 'owner__preferences', 'staff', 'staff__preferences').prefetch_related(Prefetch('images', to_attr='all_images'))
    reportable = False

    @property
    def types(self):
        if not getMagiCollections():
            return True
        if not self._cached_types:
            self._cached_types = {
                name: {
                    'title': c.title,
                    'plural_title': c.plural_title,
                    'image': c.image,
                    'icon': c.icon,
                }
                for name, c in getMagiCollections().items()
                if c.reportable
            }
        return self._cached_types
    _cached_types = None

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        show_title = True
        staff_required = True
        show_edit_button = False
        per_line = 1
        js_files = ['reports']
        ajax_pagination_callback = 'updateReport'
        filter_form = forms.FilterReports
        show_add_button = justReturn(False)
        default_ordering = 'i_status'

    class ItemView(MagiCollection.ItemView):
        template = custom_item_template
        comments_enabled = False
        owner_only = True
        show_edit_button = False
        js_files = ['reports']
        ajax_callback = 'updateReport'

    class AddView(MagiCollection.AddView):
        authentication_required = False
        alert_duplicate = False
        back_to_list_button = False
        form_class = forms.ReportForm
        multipart = True

        def extra_context(self, context):
            context['alert_message'] = mark_safe(u'{message}<ul>{list}</ul>'.format(
                message=_(u'Only submit a report if there is a problem with this specific {thing}. If it\'s about something else, your report will be ignored. For example, don\'t report an account or a profile if there is a problem with an activity. Look for "Report" buttons on the following to report individually:').format(thing=context['type']),
                list=''.join([u'<li>{}</li>'.format(unicode(type['plural_title'])) for name, type in self.collection.types.items() if name != context['type']]),
            ))
            return context

    class EditView(MagiCollection.EditView):
        multipart = True
        allow_delete = True
        redirect_after_delete = justReturn('/')
        back_to_list_button = False
        form_class = forms.ReportForm

############################################################
# Donate Collection

class DonateCollection(MagiCollection):
    enabled = False
    title = 'Donation Month'
    plural_title = _('Donate')
    plural_name = 'donate'
    icon = 'heart'
    navbar_link_list = 'more'
    queryset =  models.DonationMonth.objects.all().prefetch_related(Prefetch('badges', queryset=models.Badge.objects.select_related('user', 'user__preferences').order_by('-show_on_profile'), to_attr='all_badges'))
    reportable = False

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        page_size = 1
        per_line = 1
        default_ordering = '-date'
        show_title = True
        before_template = 'include/donate'
        add_button_subtitle = ''

        def get_queryset(self, queryset, parameters, request):
            return queryset.filter(date__lte=timezone.now())

        def extra_context(self, context):
            request = context['request']
            context['show_paypal'] = 'show_paypal' in request.GET
            context['donate_image'] = DONATE_IMAGE

    class ItemView(MagiCollection.ItemView):
        enabled = False

    class AddView(MagiCollection.AddView):
        staff_required = True
        multipart = True

    class EditView(MagiCollection.EditView):
        staff_required = True
        multipart = True
