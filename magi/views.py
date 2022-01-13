from __future__ import division
import math, datetime, random, string, simplejson
from collections import OrderedDict
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.conf import settings as django_settings
from django.contrib.auth.views import login as login_view
from django.contrib.auth.views import logout as logout_view
from django.contrib.auth import authenticate, login as login_action
from django.contrib.admin.utils import NestedObjects
from django.utils.translation import ugettext_lazy as _, get_language, activate as translation_activate
from django_translated import t
from django.utils.safestring import mark_safe
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.http import urlquote
from django.utils import timezone
from django.db.models import Count, Prefetch, Q
from magi.middleware.httpredirect import HttpRedirectException
from magi.forms import (
    CreateUserForm,
    LoginForm,
    UserForm,
    UserPreferencesForm,
    AddLinkForm,
    DonationLinkForm,
    ChangePasswordForm,
    EmailsPreferencesForm,
    LanguagePreferencesForm,
    ActivitiesPreferencesForm,
    SecurityPreferencesForm,
    Confirm,
    TranslationCheckForm,
    get_total_translations,
    get_missing_translations,
)
from magi import models
from magi.raw import donators_adjectives
from magi.utils import (
    addParametersToURL,
    artSettingsToGetParameters,
    getGlobalContext,
    getNavbarPrefix,
    getRandomValueInCurrentSeasons,
    getRandomVariableInCurrentSeasons,
    HTMLAlert,
    isValueInAnyCurrentSeason,
    isVariableInAnyCurrentSeason,
    redirectToProfile,
    tourldash,
    toHumanReadable,
    redirectWhenNotAuthenticated,
    dumpModel,
    send_email,
    emailContext,
    getMagiCollection,
    getMagiCollections,
    getMagiCollectionFromModelName,
    cuteFormFieldsForContext,
    CuteFormType,
    getCharactersBirthdayToday,
    getCharactersFavoriteCuteForm,
    groupsForAllPermissions,
    hasPermission,
    staticImageURL,
    find_all_translations,
    duplicate_translation,
    getColSize,
    LANGUAGES_NAMES,
    h1ToContext,
    get_default_owner,
    getEventStatus,
    listUnique,
    markSafeFormat,
)
from magi.notifications import pushNotification
from magi.settings import (
    ACTIVITY_TAGS,
    ENABLED_PAGES,
    SITE_NAME,
    SITE_NAME_PER_LANGUAGE,
    GAME_NAME,
    TWITTER_HANDLE,
    INSTAGRAM_HANDLE,
    BUG_TRACKER_URL,
    GITHUB_REPOSITORY,
    CONTRIBUTE_URL,
    CONTACT_EMAIL,
    CONTACT_REDDIT,
    CONTACT_FACEBOOK,
    CONTACT_DISCORD,
    FEEDBACK_FORM,
    ABOUT_PHOTO,
    WIKI,
    HELP_WIKI,
    LATEST_NEWS,
    SITE_LONG_DESCRIPTION,
    CALL_TO_ACTION,
    TOTAL_DONATORS,
    GAME_DESCRIPTION,
    GAME_URL,
    ON_USER_EDITED,
    ON_PREFERENCES_EDITED,
    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT,
    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES,
    REDIRECT_AFTER_SIGNUP,
    SITE_LOGO_PER_LANGUAGE,
    SITE_LOGO_WHEN_LOGGED_IN,
    SITE_LOGO_WHEN_LOGGED_IN_PER_LANGUAGE,
    GLOBAL_OUTSIDE_PERMISSIONS,
    CUSTOM_PREFERENCES_FORM,
    HOMEPAGE_ARTS,
    RANDOM_ART_FOR_CHARACTER,
    HOMEPAGE_ART_POSITION,
    HOMEPAGE_ART_SIDE,
    HOMEPAGE_ART_GRADIENT,
    HOMEPAGE_RIBBON,
    HOMEPAGE_BACKGROUNDS,
    HOMEPAGE_BACKGROUND,
    PROFILE_BACKGROUNDS_THUMBNAILS,
    LANGUAGES_CANT_SPEAK_ENGLISH,
)
from magi.views_collections import item_view

if CUSTOM_PREFERENCES_FORM:
    forms_module = __import__(django_settings.SITE + '.forms', fromlist=[''])

try:
    CUSTOM_SEASONAL_MODULE = __import__(django_settings.SITE + '.seasons', fromlist=[''])
except ImportError:
    CUSTOM_SEASONAL_MODULE = None

############################################################
# Sitemap

def sitemap(request, context):
    context['page_definers'] = ['sitemap']
    navbar = request.path_info.replace('/', '')
    if navbar == 'sitemap':
        context['sitemap'] = OrderedDict(context['navbar_links'].items())
    else:
        if navbar not in context['navbar_links']:
            raise Http404
        navbar_details = context['navbar_links'][navbar]
        context['h1_page_title'] = (
            _('More')
            if navbar == 'more'
            else (
                    navbar_details['title'](context)
                    if callable(navbar_details['title'])
                    else navbar_details['title']
            )
        )
        context['sitemap'] = OrderedDict([
            (link_name, link)
            for link_name, link in navbar_details['links'].items()
            if link['show_link_callback'](context)
        ])

############################################################
# Login / Logout / Sign up

def login(request):
    context = getGlobalContext(request)
    h1ToContext({}, context)
    context['next'] = request.GET['next'] if 'next' in request.GET else None
    context['next_title'] = request.GET['next_title'] if 'next_title' in request.GET else None
    context['page_title'] = _('Login')
    del(context['form'])
    if 'login' in context['navbar_links'].get('you', {}).get('links', {}):
        title = context['navbar_links']['you'].get('title', _('You'))
        context['title_prefixes'] = [{
            'title': title(context) if callable(title) else title,
            'url': u'/you/',
        }]
    return login_view(
        request,
        authentication_form=LoginForm,
        template_name='pages/login.html',
        extra_context=context,
    )

def logout(request):
    return logout_view(request, next_page='/')

def signup(request, context):
    if request.user.is_authenticated():
        redirectToProfile(request)
    if request.method == "POST":
        form = CreateUserForm(request.POST, request=request)
        if form.is_valid():
            new_user = models.User.objects.create_user(**{
                k: v for k, v in form.cleaned_data.items()
                if k in form.Meta.fields
            })
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            preferences = models.UserPreferences(
                user=user,
                i_language=request.LANGUAGE_CODE,
                view_activities_language_only= (
                    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT
                    if ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT
                    else (get_language() in ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES)),
            )
            for field_name in form.preferences_fields:
                if field_name in form.fields and field_name in form.cleaned_data:
                    setattr(preferences, field_name, form.cleaned_data[field_name])
            age = preferences.age
            if age is None: # unknown
                if 'hot' in models.UserPreferences.DEFAULT_ACTIVITIES_TABS:
                    preferences.i_default_activities_tab = models.UserPreferences.get_i(
                        'default_activities_tab', 'hot')
                # hidden tags default to hiding only nsfw
                # private message settings defaults to anyone
            elif age < 18: # minor
                if 'popular' in models.UserPreferences.DEFAULT_ACTIVITIES_TABS:
                    preferences.i_default_activities_tab = models.UserPreferences.get_i(
                        'default_activities_tab', 'popular')
                preferences.d_hidden_tags = '{"swearing": true, "questionable": true, "nsfw": true}'
                preferences.i_private_message_settings = models.UserPreferences.get_i(
                    'private_message_settings', 'follow')
            else: # adult
                if 'hot' in models.UserPreferences.DEFAULT_ACTIVITIES_TABS:
                    preferences.i_default_activities_tab = models.UserPreferences.get_i(
                        'default_activities_tab', 'hot')
                # hidden tags default to hiding only nsfw
                # private message settings defaults to anyone
            preferences.save()
            login_action(request, user)
            if context.get('launch_date', None):
                raise HttpRedirectException('/prelaunch/')
            if REDIRECT_AFTER_SIGNUP:
                raise HttpRedirectException(REDIRECT_AFTER_SIGNUP(user))
            account_collection = getMagiCollection('account')
            if account_collection and account_collection.add_view.has_permissions(request, context):
                url = u'/accounts/add/{}{}'.format(
                    (u'?next={}'.format(urlquote(request.GET['next'])) if 'next' in request.GET else ''),
                    (u'&next_title={}'.format(request.GET['next_title'])
                     if 'next' in request.GET and 'next_title' in request.GET
                     else ''))
            else:
                url = '/'
            raise HttpRedirectException(url)
    else:
        form = CreateUserForm(request=request)
    context['form'] = form
    context['next'] = request.GET.get('next', None)
    context['next_title'] = request.GET.get('next_title', None)
    context['js_files'] = ['signup']

############################################################
# Index

def indexExtraContext(context):
    context['show_homepage'] = True
    context['page_definers'] = context.get('page_definers', []) + ['homepage']
    context['page_title'] = None
    context['latest_news'] = LATEST_NEWS
    context['call_to_action'] = CALL_TO_ACTION
    context['about_site_sentence'] = _('About {thing}').format(thing=context['t_site_name'])
    context['about_game_sentence'] = _('About {thing}').format(thing=context['t_game_name'])
    context['total_donators'] = TOTAL_DONATORS
    context['homepage_background'] = HOMEPAGE_BACKGROUND
    context['adjective'] = random.choice(donators_adjectives)
    now = timezone.now()
    if 'donate' in context['all_enabled']:
        context['this_month'] = datetime.datetime(year=now.year, month=now.month, day=1)
        if hasattr(django_settings, 'DONATION_MONTH'):
            if django_settings.DONATION_MONTH:
                context['donation_month'] = django_settings.DONATION_MONTH
        else:
            try: context['donation_month'] = models.DonationMonth.objects.get(date=context['this_month'])
            except ObjectDoesNotExist: pass
    if SITE_LOGO_PER_LANGUAGE:
        logo_per_language = SITE_LOGO_PER_LANGUAGE.get(get_language(), None)
        if logo_per_language:
            context['site_logo'] = staticImageURL(logo_per_language)

    if context['request'].user.is_authenticated():
        # 'Tis the season
        if isValueInAnyCurrentSeason('site_logo_when_logged_in'):
            context['site_logo'] = staticImageURL(getRandomValueInCurrentSeasons(
                'site_logo_when_logged_in'))
        elif SITE_LOGO_WHEN_LOGGED_IN:
            context['site_logo'] = staticImageURL(SITE_LOGO_WHEN_LOGGED_IN)
            if SITE_LOGO_WHEN_LOGGED_IN_PER_LANGUAGE:
                logo_per_language = SITE_LOGO_WHEN_LOGGED_IN_PER_LANGUAGE.get(get_language(), None)
                if logo_per_language:
                    context['site_logo'] = staticImageURL(logo_per_language)

    # Homepage arts
    if HOMEPAGE_ARTS:
        context['full_width'] = True

        can_preview = (django_settings.DEBUG
                       or (context['request'].user.is_authenticated()
                           and context['request'].user.hasPermission('manage_main_items')))

        if can_preview:
            preview = {}
            for get_parameter, art_key in [
                    ('preview', 'url'),
                    ('foreground_preview', 'foreground_url'),
                    ('position_x_preview', 'position_x'),
                    ('position_y_preview', 'position_y'),
                    ('position_size_preview', 'position_size'),
                    ('side_preview', 'side'),
                    ('ribbon_preview', 'ribbon'),
                    ('gradient_preview', 'gradient'),
                    ('hd_url_preview', 'hd_url'),
            ]:
                value = context['request'].GET.get(get_parameter, None)
                if value:
                    if art_key.startswith('position_'):
                        if 'position' not in preview:
                            preview['position'] = {}
                        preview['position'][art_key[9:]] = value
                    else:
                        preview[art_key] = value
            if not preview.get('url', None) and not preview.get('foreground_url', None):
                preview = None

        # Staff preview
        if (can_preview and preview):
            context['art'] = preview

        # It's a character's birthday
        elif (RANDOM_ART_FOR_CHARACTER
              and getCharactersBirthdayToday()):
            context['art'] = RANDOM_ART_FOR_CHARACTER(
                random.choice(getCharactersBirthdayToday()),
            )

        # 1 chance out of 5 to get a random art of 1 of your favorite characters
        elif (RANDOM_ART_FOR_CHARACTER
            and context['request'].user.is_authenticated()
            and context['request'].user.preferences.favorite_characters
            and random.randint(0, 5) == 5):
            character_id = random.choice(context['request'].user.preferences.favorite_characters)
            context['art'] = RANDOM_ART_FOR_CHARACTER(character_id)
            if not context['art']:
                context['art'] = random.choice(HOMEPAGE_ARTS).copy()

        # 'Tis the season
        elif isVariableInAnyCurrentSeason('to_random_homepage_art'):
            context['art'] = getRandomVariableInCurrentSeasons(
                'to_random_homepage_art', CUSTOM_SEASONAL_MODULE)()

        # Random from the list
        if not context.get('art', None):
            context['art'] = random.choice(HOMEPAGE_ARTS).copy()

        # Position of art with CSS
        context['art_position'] = context['art'].get('position', None)
        if not context['art_position']:
            context['art_position'] = HOMEPAGE_ART_POSITION
        else:
            for key, value in HOMEPAGE_ART_POSITION.items():
                if key not in context['art_position']:
                    context['art_position'][key] = value

        # When a foreground is provided but no background,
        # use a random background in HOMEPAGE_BACKGROUNDS
        if (context['art'].has_key('foreground_url')
            and not context['art'].has_key('url')
            and HOMEPAGE_BACKGROUNDS):

            background = None

            # 'Tis the season
            if isVariableInAnyCurrentSeason('to_random_homepage_background'):
                background = getRandomVariableInCurrentSeasons(
                    'to_random_homepage_background', CUSTOM_SEASONAL_MODULE)()

            if not background:
                background = random.choice(HOMEPAGE_BACKGROUNDS)

            context['art']['url'] = background['image']
            if background.has_key('hd_image'):
                context['art']['hd_url'] = background['hd_image']

        # Side of art
        context['homepage_art_side'] = context['art'].get('side', HOMEPAGE_ART_SIDE)
        if isinstance(context['homepage_art_side'], list):
            context['homepage_art_side'] = random.choice(context['homepage_art_side'])

        # With gradient
        context['homepage_art_gradient'] = context['art'].get('gradient', HOMEPAGE_ART_GRADIENT)

    context['homepage_ribbon'] = HOMEPAGE_RIBBON

def index(request):
    context = getGlobalContext(request)
    if (context.get('launch_date', None)
        and not request.user.is_authenticated()
        or not request.user.hasPermission('access_site_before_launch')):
        raise HttpRedirectException('/prelaunch/')
    indexExtraContext(context)
    context['ajax_callback'] = 'loadIndex'
    return render(request, 'pages/index.html', context)

############################################################
# Prelaunch

def prelaunch(request, context, *args, **kwargs):
    context['show_small_title'] = False
    context['page_definers'] = context.get('page_definers', []) + ['homepage']
    context['about_site_sentence'] = _('About {thing}').format(thing=context['t_site_name'])
    context['about_game_sentence'] = _('About {thing}').format(thing=context['t_game_name'])
    context['homepage_background'] = HOMEPAGE_BACKGROUND
    if SITE_LOGO_PER_LANGUAGE:
        logo_per_language = SITE_LOGO_PER_LANGUAGE.get(get_language(), None)
        if logo_per_language:
            context['site_logo'] = staticImageURL(logo_per_language)
    if not context.get('launch_date', None):
        raise Http404()
    context['twitter'] = TWITTER_HANDLE

############################################################
# Profile

def user(request, pk=None, username=None):
    return item_view(request, 'user', getMagiCollection('user'), pk=pk, ajax=False)

############################################################
# About

def about(request, context):
    context['disqus_identifier'] = 'contact'
    context['about_description_template'] = 'include/about_description'
    context['about_photo'] = ABOUT_PHOTO
    context['share_image'] = staticImageURL(context.get('staff_configurations', {}).get(
        'about_image', None) or ABOUT_PHOTO)
    context['site_long_description'] = SITE_LONG_DESCRIPTION
    context['about_site_sentence'] = _('About {thing}').format(thing=context['t_site_name'])
    context['call_to_action'] = _('Pre-register') if context.get('launch_date', None)  else CALL_TO_ACTION

    if not context['ajax']:
        context['feedback_form'] = FEEDBACK_FORM
        context['contact_email'] = CONTACT_EMAIL
        context['bug_tracker_url'] = BUG_TRACKER_URL
        context['contact_methods'] = [
            ('Discord', 'discord', CONTACT_DISCORD),
            ('Twitter', 'twitter', u'https://twitter.com/{}/'.format(
                TWITTER_HANDLE) if TWITTER_HANDLE else None),
            ('Instagram', 'instagram', u'https://instagram.com/{}/'.format(
                INSTAGRAM_HANDLE) if INSTAGRAM_HANDLE else None),
            ('Reddit', 'reddit', u'https://www.reddit.com/user/{}/'.format(
                CONTACT_REDDIT) if CONTACT_REDDIT else None),
            ('Facebook', 'facebook', u'https://facebook.com/{}/'.format(
                CONTACT_FACEBOOK) if CONTACT_FACEBOOK else None),
            (_('Email'), 'flaticon-contact', u'mailto:{}'.format(
                CONTACT_EMAIL if CONTACT_EMAIL else None)),
            ('GitHub', 'github', u'https://github.com/{}/{}/'.format(
                GITHUB_REPOSITORY[0], GITHUB_REPOSITORY[1]) if GITHUB_REPOSITORY else None),
            ('Bug tracker', 'flaticon-album', BUG_TRACKER_URL if BUG_TRACKER_URL and not FEEDBACK_FORM else None),
        ]
        context['franchise'] = _('{site} is not a representative and is not associated with {game}. Its logos and images are Trademarks of {company}.').format(
            site=SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME),
            game=GAME_NAME, company=_('the company that owns {game}').format(game=GAME_NAME))
        context['staff'] = list(models.User.objects.filter(is_staff=True).select_related(
            'preferences', 'staff_details').prefetch_related(
            Prefetch('links', queryset=models.UserLink.objects.order_by('-i_relevance'), to_attr='all_links'),
        ).extra(select={
            'length_of_groups': 'Length(c_groups)',
            'is_manager': 'CASE WHEN c_groups LIKE \'%%\"manager\"%%\' THEN 1 ELSE 0 END',
            'is_management': 'CASE WHEN c_groups LIKE "%%manager%%" THEN 1 ELSE 0 END',
        }).order_by('-is_manager', '-is_management', '-length_of_groups'))
        context['contributors'] = [
            user for user in models.User.objects.filter(
                is_staff=False, preferences__c_groups__isnull=False).exclude(
                    preferences__c_groups='').exclude(
                        preferences__c_groups='"betatester_donator"').select_related(
                            'preferences').prefetch_related(
                                Prefetch('links', queryset=models.UserLink.objects.order_by(
                                    '-i_relevance'), to_attr='all_links'),
                            ).extra(select={
                                'length_of_groups': 'Length(c_groups)',
                            })
        ]

        try:
            my_timezone = request.user.staff_details.timezone if request.user.is_staff else None
        except ObjectDoesNotExist:
            my_timezone = None
        for staff_member in context['staff'] + context['contributors']:

            # Stats & Details
            staff_member.stats = {}
            for group, details in staff_member.preferences.groups_and_details.items():
                stats = details.get('stats', [])
                staff_member.stats[group] = []
                if stats:
                    for stat in stats:
                        if isinstance(stat['model'], basestring):
                            model = getattr(models, stat['model'])
                        else:
                            model = stat['model']
                        if stat.get('selectors_to_owner', None):
                            owner_filter = Q()
                            for selector in stat['selectors_to_owner']:
                                owner_filter |= Q(**{ selector: staff_member })
                        else:
                            owner_filter = Q(**{
                                stat.get('selector_to_owner', model.selector_to_owner()):
                                staff_member
                            })
                        total = model.objects.filter(owner_filter).filter(**(stat.get('filters', {}))).count()
                        if total:
                            staff_member.stats[group].append(mark_safe(
                                unicode(stat['template']).format(total=u'<strong>{}</strong>'.format(total))))
                settings = staff_member.preferences.t_settings_per_groups.get(group, None)
                if settings:
                    for setting, value in settings.items():
                        staff_member.stats[group].append(u'<strong>{}</strong>: {}'.format(
                            setting, value))

            if not staff_member.is_staff:
                continue

            # Availability calendar
            try:
                staff_member.has_staff_details = (
                    bool(staff_member.staff_details.id)
                    if staff_member.is_staff else None
                )
            except models.StaffDetails.DoesNotExist:
                staff_member.has_staff_details = False
                staff_member.staff_details = models.StaffDetails()
            if (request.user.is_staff
                and staff_member.has_staff_details
                and (staff_member.staff_details.d_availability
                     or staff_member.staff_details.d_weekend_availability)):
                staff_member.show_calendar = True
                if my_timezone and staff_member.staff_details.timezone:
                    staff_member.availability_calendar = staff_member.staff_details.availability_calendar_timezone(
                        my_timezone)
                    staff_member.calendar_with_timezone = True
                else:
                    staff_member.availability_calendar = staff_member.staff_details.availability_calendar
                    staff_member.calendar_with_timezone = False

        context['now'] = timezone.now()
        context['api_enabled'] = False
        context['contribute_url'] = CONTRIBUTE_URL
        total = len(context['other_sites'])
        if total <= 4:
            context['other_sites_per_line'] = total
        elif (total % 4) == 1:
            context['other_sites_per_line'] = 3
        else:
            context['other_sites_per_line'] = 4
        context['other_sites_col_size'] = getColSize(context['other_sites_per_line'])

def about_game(request, context):
    context['game_description'] = GAME_DESCRIPTION
    context['game_url'] = GAME_URL
    context['button_sentence'] = _('Learn more')
    context['extends'] = 'ajax.html' if context['ajax'] else 'base.html'

############################################################
# Settings

def _settingsOnSuccess(form, added=False):
    if not hasattr(form, 'beforefields') or not form.beforefields:
        form.beforefields = u''
    form.beforefields += u'<p class="alert alert-info"><i class="flaticon-about"></i> {}</p>'.format(
        _('Successfully edited!') if not added else _('Successfully added!'),
    )
    form.beforefields = mark_safe(form.beforefields)

def settings(request, context):
    context['preferences'] = request.user.preferences
    context['accounts'] = request.user.accounts.all()
    context['hide_prefixes'] = True

    preferences_form_class = (
        forms_module.UserPreferencesForm
        if CUSTOM_PREFERENCES_FORM
        else UserPreferencesForm
    )

    account_collection = getMagiCollection('account')
    if account_collection:
        context['add_account_sentence'] = account_collection.add_sentence
        context['accounts_title_sentence'] = account_collection.plural_title
    else:
        context['no_accounts'] = True
    context['add_link_sentence'] = _(u'Add {thing}').format(thing=_('Link'))
    context['delete_link_sentence'] = _(u'Delete {thing}').format(thing=_('Link'))
    context['back_to_profile_sentence'] = _('Back to {page_name}').format(page_name=_('Profile').lower())
    context['alert_reputation_title'] = _('You are not allowed to send private messages.')
    context['alert_reputation_message'] = _('Take some time to play around {site_name} to unlock this feature!').format(site_name=context['t_site_name'])
    context['blocked_users_sentence'] = _('Block {username}').format(username=_('Users').lower())

    context['t_english'] = t['English']
    context['global_outside_permissions'] = GLOBAL_OUTSIDE_PERMISSIONS
    context['forms'] = OrderedDict([
        ('preferences', preferences_form_class(instance=context['preferences'], request=request)),
        ('addLink', AddLinkForm(request=request)),
    ])
    if request.user.preferences.is_premium:
        context['forms']['donationLink'] = DonationLinkForm(instance=context['preferences'], request=request)
    context['forms'].update([
        ('form', UserForm(instance=request.user, request=request)),
        ('language', LanguagePreferencesForm(instance=context['preferences'], request=request)),
        ('changePassword', ChangePasswordForm(request=request)),
        ('emails', EmailsPreferencesForm(request=request)),
        ('activities', ActivitiesPreferencesForm(instance=context['preferences'], request=request)),
        ('security', SecurityPreferencesForm(instance=context['preferences'], request=request)),
    ])
    if request.method == 'POST':
        for (form_name, form) in context['forms'].items():
            if form_name in request.POST:
                if form_name == 'form':
                    form = UserForm(request.POST, instance=request.user, request=request)
                    if form.is_valid():
                        form.save()
                        models.onUserEdited(request.user)
                        if ON_USER_EDITED:
                            ON_USER_EDITED(request.user)
                        _settingsOnSuccess(form)
                elif form_name == 'preferences':
                    form = preferences_form_class(request.POST, instance=context['preferences'], request=request)
                    if form.is_valid():
                        form.save()
                        models.onPreferencesEdited(request.user)
                        if ON_PREFERENCES_EDITED:
                            ON_PREFERENCES_EDITED(request.user)
                        redirectToProfile(request)
                elif form_name == 'addLink':
                    form = AddLinkForm(request.POST, request=request)
                    if form.is_valid():
                        form.save()
                        _settingsOnSuccess(form, added=True)
                elif form_name == 'changePassword':
                    form = ChangePasswordForm(request.POST, request=request)
                    if form.is_valid():
                        form.save()
                        _settingsOnSuccess(form)
                elif form_name == 'language':
                    form = LanguagePreferencesForm(request.POST, instance=context['preferences'], request=request)
                    if form.is_valid():
                        form.save()
                        redirectToProfile(request)
                elif form_name == 'emails':
                    form = EmailsPreferencesForm(request.POST, request=request)
                    if form.is_valid():
                        form.save()
                        _settingsOnSuccess(form)
                elif form_name == 'activities':
                    form = ActivitiesPreferencesForm(request.POST, instance=context['preferences'], request=request)
                    if form.is_valid():
                        form.save()
                        models.onPreferencesEdited(request.user)
                        if ON_PREFERENCES_EDITED:
                            ON_PREFERENCES_EDITED(request.user)
                        _settingsOnSuccess(form)
                elif form_name == 'security':
                    form = SecurityPreferencesForm(request.POST, instance=context['preferences'], request=request)
                    if form.is_valid():
                        form.save()
                        models.onPreferencesEdited(request.user)
                        if ON_PREFERENCES_EDITED:
                            ON_PREFERENCES_EDITED(request.user)
                        _settingsOnSuccess(form)
                elif (request.user.preferences.is_premium
                      and form_name == 'donationLink'):
                    form = DonationLinkForm(request.POST, instance=context['preferences'], request=request)
                    if form.is_valid():
                        form.save()
                        models.onPreferencesEdited(request.user)
                        if ON_PREFERENCES_EDITED:
                            ON_PREFERENCES_EDITED(request.user)
                        _settingsOnSuccess(form)
                context['forms'][form_name] = form

    context['add_custom_link_sentence'] = _(u'Add {thing}').format(thing=unicode(_('Custom link')).lower())
    if 'donationLink' in context['forms']:
        context['forms']['donationLink'].form_title = context['add_custom_link_sentence']

    # Links
    context['links'] = [{
        'name': link.type,
        'verbose_name': link.t_type,
        'value': link.value,
        'pk': link.pk,
        'url': link.url,
        'image': link.image_url,
    } for link in request.user.links.all()]

    # Blocked users
    context['blocked'] = list(request.user.preferences.blocked.all())
    for blocked_user in context['blocked']:
        blocked_user.block_message = _(u'You blocked {username}.').format(username=blocked_user.username)
        blocked_user.unblock_message = _(u'Unblock {username}').format(username=blocked_user.username)

    # Recent reports
    now = timezone.now()
    six_months_ago = now - datetime.timedelta(days=30 * 6)
    reports = list(models.Report.objects.filter(
        Q(
            Q(modification__gte=six_months_ago)
            & Q(
                i_status__in=[
                    models.Report.get_i('status', 'Deleted'),
                    models.Report.get_i('status', 'Edited'),
                ])
            & Q(
                Q(reported_thing_owner_id=request.user.id)
                | Q(owner_id=request.user.id)
            )
        )
        | Q(
            Q(
                i_status__in=[
                    models.Report.get_i('status', 'Pending'),
                ])
            & Q(owner_id=request.user.id)
        )
    ).order_by('-modification', '-creation'))
    context['reports'] = []
    context['pending_reports'] = []
    context['suggested_edits'] = []
    context['pending_suggested_edits'] = []
    for report in reports:
        if report.status == 'Pending':
            if report.is_suggestededit:
                context['pending_suggested_edits'].append(report)
            else:
                context['pending_reports'].append(report)
            continue
        if report.status == 'Edited':
            thing = markSafeFormat(
                u'<a href="/{thing}/{id}/">{title}</a>',
                thing=report.reported_thing,
                id=report.reported_thing_id,
                title=unicode(report).lower(),
            )
        else:
            thing = unicode(report).lower()
        if report.is_suggestededit:
            if report.status == 'Deleted':
                continue
            if report.reported_thing_owner_id == request.user.id:
                report.introduction_sentence = markSafeFormat(
                    _('An edit has been suggested on your {thing}, and a database maintainer confirmed and applied it.'),
                    thing=thing,
                )
            else:
                report.introduction_sentence = markSafeFormat(
                    _('The edit you suggested has been reviewed by a database maintainer and the {thing} has been edited accordingly. Thank you so much for your help!'),
                    thing=thing,
                )
            context['suggested_edits'].append(report)
        else:
            verb = _(u'edited') if report.status == 'Edited' else _(u'deleted')
            if report.reported_thing_owner_id == request.user.id:
                report.introduction_sentence = markSafeFormat(
                    _(u'Your {thing} has been reported, and a moderator confirmed it should be {verb}.'),
                    thing=thing, verb=verb)
            else:
                report.introduction_sentence = markSafeFormat(
                    _(u'This {thing} you reported has been reviewed by a moderator and {verb}. Thank you so much for your help!'),
                    thing=thing, verb=verb)
            context['reports'].append(report)

    context['js_files'] = ['settings']

    filter_cuteform = {
        'i_language': {
            'type': CuteFormType.Images,
            'image_folder': 'language',
        },
        'color': {
            'type': CuteFormType.Images,
        },
        'd_extra-background': {
            'to_cuteform': lambda k, v: staticImageURL(PROFILE_BACKGROUNDS_THUMBNAILS[k]),
            'title': _('Background'),
            'extra_settings': {
                'modal': 'true',
	        'modal-text': 'true',
            },
        },
    }

    # Favorite characters fields
    filter_cuteform.update(getCharactersFavoriteCuteForm(only_one=False))

    cuteFormFieldsForContext(filter_cuteform, context, context['forms']['preferences'])
    cuteFormFieldsForContext({
        'i_type': {
            'image_folder': 'links',
        },
        'relevance': {
            'type': CuteFormType.HTML,
        },
    }, context, context['forms']['addLink'])
    cuteFormFieldsForContext({
        'i_activities_language': {
            'type': CuteFormType.Images,
            'image_folder': 'language',
        },
        'i_default_activities_tab': {
            'type': CuteFormType.HTML,
        },
    }, context, context['forms']['activities'])
    cuteFormFieldsForContext({
        'i_language': {
            'type': CuteFormType.Images,
            'image_folder': 'language',
        },
    }, context, context['forms']['language'])
    cuteFormFieldsForContext({
        'i_private_message_settings': {
            'type': CuteFormType.HTML,
        },
    }, context, context['forms']['security'])

############################################################
# Help / Wiki

def custom_wiki(wiki, wiki_base_url, wiki_name, request, context, wiki_url):
    context['wiki_url'] = wiki_url
    if wiki_url not in ['Home', '_Sidebar']:
        if 'title_prefixes' not in context:
            context['title_prefixes'] = []
        if (wiki_base_url in ENABLED_PAGES
            and isinstance(ENABLED_PAGES[wiki_base_url], list)):
            navbar_link_list = ENABLED_PAGES[wiki_base_url][0].get('navbar_link_list', None)
            navbar_prefix = getNavbarPrefix(navbar_link_list, request, context, append_to=context['title_prefixes'])
        context['title_prefixes'].append({
            'title': wiki_name,
            'url': u'/{}/'.format(wiki_base_url),
        })
        verbose_wiki_url = wiki_url.replace('_', ' ').replace('-', ' ')
        context['page_title'] = u'{} - {}'.format(verbose_wiki_url, wiki_name)
        context['h1_page_title'] = verbose_wiki_url
    else:
        context['page_title'] = wiki_name

    context['h1_page_title_attributes'] = { 'data-url': wiki_url, 'id': 'wiki-title' }
    context['hide_side_bar'] = wiki_url == '_Sidebar'
    context['small_container'] = True
    context['wiki'] = wiki
    context['full_wiki_url'] = 'https://github.com/{}/{}/wiki/'.format(wiki[0], wiki[1])
    context['js_files'] = ['bower/marked/lib/marked', 'bower/github-wiki/js/githubwiki', 'wiki']
    context['ajax_callback'] = 'loadWikiPage'
    context['back_to_home_sentence'] = _('Back to {page_name}').format(
        page_name=_('Wiki home').lower(),
    )
    if 'js_variables' not in context:
        context['js_variables'] = {}
    context['js_variables'].update({
        'wiki_url': wiki_url,
        'site_url': context['site_url'],
        'current': context['current'],
        'github_repository_username': wiki[0],
        'github_repository_name': wiki[1],
    })

def help(request, context, wiki_url='_Sidebar'):
    return custom_wiki(HELP_WIKI, 'help', _('Help'), request, context, wiki_url)

def wiki(request, context, wiki_url='Home'):
    return custom_wiki(WIKI, 'wiki', _('Wiki'), request, context, wiki_url)

############################################################
# Map

def map(request, context):
    context['js_files'] = [
        'https://maps.googleapis.com/maps/api/js?key=AIzaSyDHtAPFTmOCQZrKSjZlIeoZrZYLJjKLupE',
        'oms.min',
    ]
    if request.user.is_authenticated() and request.user.preferences.latitude:
        context['center'] = {
            'latitude': request.user.preferences.latitude,
            'longitude': request.user.preferences.longitude,
        }
        context['zoom'] = 10
    if 'center' in request.GET:
        center = request.GET['center'].split(',')
        try:
            context['center'] = {
                'latitude': center[0],
                'longitude': center[1],
            }
        except IndexError: pass
    if 'zoom' in request.GET:
        context['zoom'] = request.GET['zoom']

############################################################
# Block

def block(request, context, pk, unblock=False):
    user = get_object_or_404(models.User.objects.select_related('preferences'), pk=pk)
    if user == request.user:
        raise PermissionDenied()
    block = True
    if request.user.preferences.blocked.filter(pk=user.pk).exists():
        block = False
    title = _(u'Block {username}').format(username=user.username) if block else _(u'Unblock {username}').format(username=user.username)
    context['page_title'] = title
    context['extends'] = 'base.html'
    context['form'] = Confirm()
    if request.method == 'POST':
        context['form'] = Confirm(request.POST)
        if context['form'].is_valid():
            if block:
                request.user.preferences.blocked.add(user)
                request.user.preferences.following.remove(user)
                user.preferences.following.remove(request.user)
                redirect_url = context['current_url']
            else:
                request.user.preferences.blocked.remove(user)
                redirect_url = user.item_url
            if 'next' in request.GET:
                redirect_url = request.GET['next']
            request.user.preferences.update_cache('blocked_ids')
            request.user.preferences.save()
            user.preferences.update_cache('blocked_by_ids')
            user.preferences.save()
            raise HttpRedirectException(redirect_url)
    context['form'].submit_title = title
    if not block:
        context['form'].beforeform = mark_safe(
            """
            <div class=\"blocked-info\">
            <h1><i class=\"flaticon-block\"></i></h1>
            <p>{}</p>
            </div>
            """.format(_(u'You blocked {username}.').format(username=user.username)))
    context['form'].beforefields = mark_safe(HTMLAlert(
        type='danger', flaticon='block',
        message=(_(u'Are you sure you want to block {username}? You will not be able to see any content created by {username}.')
                 if block
                 else _(u'Are you sure you want to unblock {username}?')).format(username=user.username)
    ))

############################################################
# Avatar redirection for gravatar + twitter

def twitter_avatar(request, twitter):
    raise HttpRedirectException('https://twitter.com/{}/profile_image?size=original'.format(twitter))

############################################################
# Ajax

def deletelink(request, context, pk):
    models.UserLink.objects.filter(owner=request.user, pk=pk).delete()
    return None

def _getInstanceFromThingId(thing, thing_id, collection=None):
    if not collection:
        collection = getMagiCollection(thing)
    queryset = collection.queryset
    return get_object_or_404(queryset, pk=thing_id)

def _cascadeDeleteInstances(instance):
    collector = NestedObjects(using=instance._state.db)
    collector.collect([instance])
    return collector.nested()

def _deleteCascadeWarnings(thing, instance):
    return (
        _('If you delete this {thing} ({instance}), the following will automatically be deleted as well:').format(thing=thing, instance=instance),
        _('Are you sure you want to delete this {thing} ({instance})?').format(thing=thing, instance=instance),
        _('You can\'t cancel this action afterwards.'),
    )

def whatwillbedeleted(request, context, thing, thing_id):
    collection = getMagiCollection(thing)
    instance = _getInstanceFromThingId(thing, thing_id, collection=collection)
    context['to_delete'] = _cascadeDeleteInstances(instance)
    context['warnings'] = _deleteCascadeWarnings(thing=collection.title.lower(), instance=instance)
    context['show_small_title'] = False

def moderatereport(request, report, action):
    if request.method != 'POST':
        raise PermissionDenied()
    queryset = models.Report.objects.select_related('owner', 'owner__preferences')
    if not request.user.is_superuser:
        queryset = queryset.exclude(owner=request.user)
    report = get_object_or_404(queryset, pk=report, i_status=models.Report.get_i('status', 'Pending'))

    if (not request.user.is_superuser
        and ((action == 'Edited' and not report.allow_edit)
             or (action == 'Deleted' and not report.allow_delete))):
        raise PermissionDenied()

    report.staff = request.user
    old_language = get_language()
    moderated_reports = []
    context = emailContext()
    context['report'] = report

    if action == 'Edited' or action == 'Deleted':

        # Get the reported thing
        queryset = report.reported_thing_collection.queryset
        thing = get_object_or_404(queryset, pk=report.reported_thing_id)

        # Make sure there's an owner
        if not hasattr(thing, 'owner') and isinstance(thing, models.User):
            thing.owner = thing

        # Get staff message
        if 'staff_message' not in request.POST or not request.POST['staff_message']:
            raise PermissionDenied()
        report.staff_message = request.POST['staff_message']

        # Get reason
        if not report.is_suggestededit:
            reason = request.POST.get('reason', None)
            if reason and reason != '_other':
                report.reason = reason

    # Action: Ignore
    if action == 'Ignored':
        report.i_status = models.Report.get_i('status', 'Ignored')
        report.save()
        moderated_reports = [report.pk]

    # Action: Edit
    elif action == 'Edited':
        if report.reported_thing_collection.item_view.enabled:
            context['item_url'] = thing.http_item_url
            context['item_open_sentence'] = thing.open_sentence
        else:
            context['item_url'] = None
            context['item_open_sentence'] = None
        report.i_status = models.Report.get_i('status', 'Edited')
        report.reported_thing_owner_id = thing.owner.id
        # Notify reporter
        if report.owner:
            translation_activate(report.owner.preferences.language if report.owner.preferences.language else 'en')
            if report.is_suggestededit:
                context['sentence'] = unicode(_('The edit you suggested has been reviewed by a database maintainer and the {thing} has been edited accordingly. Thank you so much for your help!')).format(thing=_(report.reported_thing_title))
                subject = _(u'Thank you for suggesting this edit!')
            else:
                context['sentence'] = _(u'This {thing} you reported has been reviewed by a moderator and {verb}. Thank you so much for your help!').format(thing=_(report.reported_thing_title), verb=_(u'edited'))
                subject = _(u'Thank you for reporting this {thing}')
            context['user'] = report.owner
            context['show_donation'] = True
            context['subject'] = u'{} {}'.format(
                SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME),
                unicode(subject.format(thing=_(report.reported_thing_title))),
            )
            send_email(context['subject'], template_name='report', to=[context['user'].email], context=context)
        # Notify owner
        if thing.owner:
            translation_activate(thing.real_owner.preferences.language if thing.real_owner.preferences.language else 'en')
            if report.is_suggestededit:
                context['sentence'] = _('An edit has been suggested on your {thing}, and a database maintainer confirmed and applied it.').format(thing=report.reported_thing_title)
            else:
                context['sentence'] = _(u'Your {thing} has been reported, and a moderator confirmed it should be {verb}.').format(thing=_(report.reported_thing_title), verb=_(u'edited'))
            context['user'] = thing.real_owner
            context['show_donation'] = False
            context['subject'] = u'{} {}'.format(
                SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME),
                unicode(_(u'Your {thing} has been {verb}').format(thing=_(report.reported_thing_title), verb=_(u'edited'))),
            )
            send_email(context['subject'], template_name='report', to=[context['user'].email], context=context)
        report.save()
        moderated_reports = [report.pk]

    # Delete is not an option for suggested edits
    elif action == 'Deleted' and not report.is_suggestededit:
        report.i_status = models.Report.get_i('status', 'Deleted')
        report.reported_thing_owner_id = thing.real_owner.id
        report.saved_data = dumpModel(thing)
        # Notify all reporters
        all_reports = models.Report.objects.filter(
            reported_thing=report.reported_thing,
            reported_thing_id=report.reported_thing_id,
            i_status=models.Report.get_i('status', 'Pending'),
        ).select_related('owner', 'owner__preferences')
        for a_report in all_reports:
            if a_report.owner:
                translation_activate(a_report.owner.preferences.language if a_report.owner.preferences.language else 'en')
                context['sentence'] = _(u'This {thing} you reported has been reviewed by a moderator and {verb}. Thank you so much for your help!').format(thing=_(report.reported_thing_title), verb=_(u'deleted'))
                context['user'] = a_report.owner
                context['show_donation'] = True
                context['subject'] = u'{} {}'.format(
                    SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME),
                    unicode(_(u'Thank you for reporting this {thing}').format(thing=_(report.reported_thing_title))),
                )
                send_email(context['subject'], template_name='report', to=[context['user'].email], context=context)
        # Notify owner
        if thing.owner:
            translation_activate(thing.real_owner.preferences.language if thing.real_owner.preferences.language else 'en')
            context['sentence'] = _(u'Your {thing} has been reported, and a moderator confirmed it should be {verb}.').format(thing=_(report.reported_thing_title), verb=_(u'edited'))
            context['user'] = thing.real_owner
            context['show_donation'] = False
            context['subject'] = u'{} {}'.format(
                SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME),
                unicode(_(u'Your {thing} has been {verb}').format(thing=_(report.reported_thing_title), verb=_(u'deleted'))),
            )
            send_email(context['subject'], template_name='report', to=[context['user'].email], context=context)
        moderated_reports = [a_report.pk for a_report in all_reports]
        all_reports.update(
            staff=request.user,
            staff_message=report.staff_message,
            saved_data=report.saved_data,
            i_status=models.Report.get_i('status', 'Deleted'),
            reported_thing_owner_id=report.reported_thing_owner_id,
        )
        thing.delete()

    translation_activate(old_language)
    return JsonResponse({
        'moderated_reports': moderated_reports,
        'action': action,
    })

def reportwhatwillbedeleted(request, context, report):
    # Get the report
    report = get_object_or_404(models.Report, pk=report, i_status=models.Report.get_i('status', 'Pending'))
    # Get the reported thing
    instance = _getInstanceFromThingId(report.reported_thing, report.reported_thing_id)

    context['to_delete'] = _cascadeDeleteInstances(instance)
    context['warnings'] = _deleteCascadeWarnings(thing=report.reported_thing, instance=instance)
    context['show_small_title'] = False

def changelanguage(request):
    form = LanguagePreferencesForm(request.POST, instance=request.user.preferences, request=request)
    if form.is_valid():
        form.save()
    raise HttpRedirectException(request.POST.get('next', '/'))

def markallnotificationsread(request):
    read = request.user.notifications.filter(seen=False).update(seen=True)
    request.user.preferences.force_update_cache('unread_notifications')
    raise HttpRedirectException(u'/notifications/?marked_read={}'.format(read))

def me(request):
    if request.user.is_authenticated():
        raise HttpRedirectException(request.user.http_item_url)
    raise HttpRedirectException('/signup/')

def _shouldBumpActivity(activity, request):
    # Archived activities can't be bumped
    if activity.archived:
        return False

    now = timezone.now()
    one_hour_ago = now - datetime.timedelta(hours=1)
    one_day_ago = now - datetime.timedelta(days=1)

    # Activities can only be bumped once per hour
    if activity.last_bump and activity.last_bump >= one_hour_ago:
        return False

    # Only users with enough "reputation" can bump
    if not request.user.preferences.has_good_reputation:
        return False

    # A given user can only bump up to 5 activities older than 1 day per hour
    if activity.creation > one_day_ago:
        return True
    elif (not request.user.preferences.last_bump_date
          or request.user.preferences.last_bump_date < one_hour_ago):
        request.user.preferences.last_bump_date = now
        request.user.preferences.last_bump_counter = 0
        request.user.preferences.save()
        return True
    elif request.user.preferences.last_bump_counter < 5:
        request.user.preferences.last_bump_counter += 1
        request.user.preferences.save()
        return True
    return False

def likeactivity(request, context, pk):
    if request.method != 'POST':
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity.objects.extra(select={
        'liked': 'SELECT COUNT(*) FROM magi_activity_likes WHERE activity_id = magi_activity.id AND user_id={}'.format(request.user.id),
    }).annotate(total_likes=Count('likes')).select_related('owner', 'owner__preferences'), pk=pk)
    # If the owner of the liked activity blocked the authenticated user
    if activity.cached_owner.id in request.user.preferences.cached_blocked_by_ids:
        raise PermissionDenied()
    if activity.cached_owner.username == request.user.username:
        raise PermissionDenied()
    if 'like' in request.POST and not activity.liked:
        if _shouldBumpActivity(activity, request):
            activity.last_bump = timezone.now()
        activity.likes.add(request.user)
        activity.update_cache('total_likes')
        activity.save()
        pushNotification(activity.owner, 'like-archive' if activity.archived_by_owner else 'like', [unicode(request.user), unicode(activity)], url_values=[str(activity.id), tourldash(unicode(activity))], image=activity.image)
        return {
            'total_likes': activity.total_likes + 2,
            'result': 'liked',
        }
    if 'unlike' in request.POST and activity.liked:
        activity.likes.remove(request.user)
        activity.update_cache('total_likes')
        activity.save()
        return {
            'total_likes': activity.total_likes,
            'result': 'unliked',
        }
    return {
        'total_likes': activity.total_likes + 1,
    }

def archiveactivity(request, context, pk):
    if request.method != 'POST':
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity.objects.select_related('archived_by_staff'), pk=pk)
    if activity.is_owner(request.user):
        if not activity.has_permissions_to_archive(request.user)[0]:
            raise PermissionDenied()
        activity.archived_by_owner = True
    else:
        if not activity.has_permissions_to_ghost_archive(request.user):
            raise PermissionDenied()
        activity.archived_by_staff = request.user
    activity.save()
    if activity.archived_by_staff:
        return {
            'result': {
                'archived': activity.archived_by_owner,
                'archived_by_staff': activity.archived_by_staff.username if activity.archived_by_staff else None,
            },
        }
    # We don't want to reveal users if the activity is ghost archived if they check the request
    return {
        'result': {
            'archived': activity.archived_by_owner,
        },
    }

def unarchiveactivity(request, context, pk):
    by_staff = False
    if not request.user.is_authenticated() or request.method != 'POST':
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity.objects.select_related('archived_by_staf'), pk=pk)
    if activity.is_owner(request.user):
        if not activity.has_permissions_to_archive(request.user)[0]:
            raise PermissionDenied()
        activity.archived_by_owner = False
    else:
        if not activity.has_permissions_to_ghost_archive(request.user):
            raise PermissionDenied()
        activity.archived_by_staff = None
        by_staff = True
    activity.save()
    if by_staff:
        return {
            'result': {
                'archived': activity.archived_by_owner,
                'archived_by_staff': activity.archived_by_staff.username if activity.archived_by_staff else None,
            },
        }
    # We don't want to reveal users if the activity is ghost archived if they check the request
    return {
        'result': {
            'archived': activity.archived_by_owner,
        },
    }

def bumpactivity(request, context, pk):
    if (not request.user.is_authenticated() or request.method != 'POST'
        or not request.user.hasPermission('manipulate_activities')):
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity, pk=pk)
    activity.last_bump = timezone.now()
    activity.save()
    return {
        'result': 'bumped',
    }

def drownactivity(request, context, pk):
    if (not request.user.is_authenticated() or request.method != 'POST'
        or not request.user.hasPermission('manipulate_activities')):
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity, pk=pk)
    now = timezone.now()
    a_month_ago = now - datetime.timedelta(days=30)
    activity.last_bump = a_month_ago
    activity.save()
    return {
        'result': 'drowned',
    }

def markactivitystaffpick(request, context, pk):
    if (not request.user.is_authenticated() or request.method != 'POST'
        or 'staff' not in ACTIVITY_TAGS.keys()
        or not request.user.hasPermission('mark_activities_as_staff_pick')):
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity, pk=pk)
    activity.add_c('tags', ['staff'])
    activity.save()
    return {
        'result': {
            'staff-picks': True,
            'tags': {
                k: unicode(v)
                for k, v in activity.t_tags.items()
            },
        },
    }

def removeactivitystaffpick(request, context, pk):
    if (not request.user.is_authenticated() or request.method != 'POST'
        or 'staff' not in ACTIVITY_TAGS.keys()
        or not request.user.hasPermission('mark_activities_as_staff_pick')):
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity, pk=pk)
    activity.remove_c('tags', ['staff'])
    activity.save()
    return {
        'result': {
            'staff-picks': False,
            'tags': {
                k: unicode(v)
                for k, v in activity.t_tags.items()
            },
        },
    }

def follow(request, context, username):
    if not request.user.is_authenticated() or request.method != 'POST' or request.user.username == username:
        raise PermissionDenied()
    user = get_object_or_404(models.User.objects.extra(select={
        'followed': 'SELECT COUNT(*) FROM magi_userpreferences_following WHERE userpreferences_id = {} AND user_id = auth_user.id'.format(request.user.preferences.id),
    }).annotate(total_followers=Count('followers')).select_related('preferences'), username=username)
    # If the user being followed blocked the authenticated user
    if user.id in request.user.preferences.cached_blocked_by_ids:
        raise PermissionDenied()
    if 'follow' in request.POST and not user.followed:
        request.user.preferences.following.add(user)
        request.user.preferences.save()
        pushNotification(
            user,
            'follow',
            [unicode(request.user)],
            url_values=[str(request.user.id), unicode(request.user)],
            image=request.user.image_url,
        )
        return {
            'total_followers': user.total_followers + 1,
            'result': 'followed',
        }
    if 'unfollow' in request.POST and user.followed:
        request.user.preferences.following.remove(user)
        request.user.preferences.save()
        return {
            'total_followers': user.total_followers - 1,
            'result': 'unfollowed',
        }
    return {
        'total_followers': user.total_followers,
    }

############################################################
# Staff / Contributors

def translations(request, context):
    context['collections'] = []
    context['guide'] = models.UserPreferences.GROUPS.get('translator', {}).get('guide', None)
    context['poeditor'] = models.UserPreferences.GROUPS.get('translator', {}).get('outside_permissions', {}).get('POEditor', None)
    context['total_per_languages'] = {}
    context['total'] = 0
    context['total_need_translations'] = 0
    context['see_all'] = 'see_all' in request.GET
    speaks_languages = listUnique((request.user.preferences.settings_per_groups or {}).get(
        'translator', {}).get('languages', []) + ['en'])
    only_languages = speaks_languages[:]
    if context['see_all']:
        only_languages = {}
    if 'language' in request.GET:
        only_languages = request.GET['language'].split(u',')
    for collection in getMagiCollections().values():
        if collection.translated_fields:
            c = {
                'name': collection.name,
                'model_name': collection.model_name,
                'title': collection.title,
                'icon': collection.icon,
                'image': collection.image,
                'list_url': collection.get_list_url(),
                'translated_fields_per_languages': {},
            }
            for field in collection.translated_fields:
                languages = getattr(
                    collection.queryset.model,
                    u'{name}S_CHOICES'.format(name=field.upper()),
                    django_settings.LANGUAGES,
                )

                source_languages = getattr(
                    collection.queryset.model, u'{}_SOURCE_LANGUAGES'.format(field.upper()),
                    ['en']) or ['en']

                limit_sources_to = dict(languages).keys()

                if source_languages != ['en']:
                    languages = [('en', t['English'])] + languages

                for language, verbose_name in languages:
                    if only_languages:
                        if language == 'en':
                            if not set(source_languages).intersection(set(only_languages)):
                                continue
                        elif language not in only_languages:
                            continue
                    if language not in c['translated_fields_per_languages']:
                        c['translated_fields_per_languages'][language] = {
                            'verbose_name': verbose_name,
                            'fields': [],
                            'image': staticImageURL(language, folder='language', extension='png')
                        }

                    _limit_sources_to = [
                        l for l in limit_sources_to if l != language
                    ] if language == 'en' else speaks_languages
                    items_with_something_to_translate = get_total_translations(
                        collection.queryset, field, limit_sources_to=_limit_sources_to)
                    count_total = items_with_something_to_translate.count()
                    count_need_translations = get_missing_translations(
                        collection.queryset, field, [language], limit_sources_to=_limit_sources_to,
                    ).count()
                    if not count_total:
                        continue
                    c['translated_fields_per_languages'][language]['fields'].append({
                        'name': field,
                        'verbose_name': collection.queryset.model._meta.get_field_by_name(field)[0].verbose_name or toHumanReadable(field),
                        'total': count_total,
                        'total_need_translations': count_need_translations,
                        'total_translated': count_total - count_need_translations,
                        'source_languages': {
                            source_language: LANGUAGES_NAMES.get(source_language, source_language).replace(
                                '_', ' ').title()
                            for source_language in source_languages
                            if source_language != 'en'
                        } if language == 'en' else None,
                    })
                    context['total'] += count_total
                    context['total_need_translations'] += count_need_translations
                    if language not in context['total_per_languages']:
                        context['total_per_languages'][language] = {
                            'verbose_name': verbose_name,
                            'total_need_translations': 0,
                            'total': 0,
                            'image': staticImageURL(language, folder='language', extension='png')
                        }
                    context['total_per_languages'][language]['total'] += count_total
                    context['total_per_languages'][language]['total_need_translations'] += count_need_translations
            context['collections'].append(c)

    if 'staffconfiguration' in context['all_enabled']:
        context['staff_configurations_per_languages'] = {}
        keys_of_staff_configurations_with_english = models.StaffConfiguration.objects.filter(
            i_language='en', value__isnull=False).exclude(value='').values_list('key', flat=True)
        staff_configurations = models.StaffConfiguration.objects.filter(
            key__in=keys_of_staff_configurations_with_english).exclude(i_language='en')
        if only_languages:
            staff_configurations = staff_configurations.filter(i_language__in=only_languages)
        context['staff_configurations_per_languages'] = {}
        for staff_configuration in staff_configurations:
            if staff_configuration.language not in context['staff_configurations_per_languages']:
                context['staff_configurations_per_languages'][staff_configuration.language] = {
                    'verbose_name': staff_configuration.t_language,
                    'image': staff_configuration.language_image_url,
                    'fields': [],
                }
            staff_configuration.need_translation = not staff_configuration.value
            context['staff_configurations_per_languages'][staff_configuration.language]['fields'].append(staff_configuration)
            if staff_configuration.need_translation:
                context['total_need_translations'] += 1
                context['total_per_languages'][staff_configuration.language]['total_need_translations'] += 1
            context['total'] += 1
            context['total_per_languages'][staff_configuration.language]['total'] += 1

    context['total_translated'] = context['total'] - context['total_need_translations']
    try:
        context['percent_translated'] = int(context['total_translated'] / context['total'] * 100)
    except ZeroDivisionError:
        context['percent_translated'] = 0
    for language, details in context['total_per_languages'].items():
        details['total_translated'] = details['total'] - details['total_need_translations']
        details['percent_translated'] = int(details['total_translated'] / details['total'] * 100)

def translations_duplicator(request, context, model_name, field_name, language=None):
    collection = getMagiCollectionFromModelName(model_name)
    if not collection or not collection.translated_fields or field_name not in collection.translated_fields:
        raise Http404
    context['collection'] = collection
    context['field_name'] = field_name
    context['language'] = language
    context['verbose_field_name'] = collection.queryset.model._meta.get_field_by_name(field_name)[0].verbose_name
    context['see_all'] = 'see_all' in request.GET
    context['page_title'] = u'Translations duplicator: {} {}'.format(
        collection.plural_title,
        context['verbose_field_name'],
    )
    if language:
        context['h1_page_title_icon'] = None
        context['h1_page_title_image'] = staticImageURL(language, folder='language')
    if request.method == 'POST' and 'term' in request.POST:
        context['logs'] = duplicate_translation(
            collection.queryset.model, field_name, request.POST['term'],
            only_for_language=language, print_log=False, html_log=True,
        )

    context['terms'] = find_all_translations(collection.queryset.model, field_name, only_for_language=language)

def collections(request, context):
    context['collections'] = getMagiCollections()
    context['groups_per_permissions'] = groupsForAllPermissions(request.user.preferences.GROUPS)

def translations_check(request, context):
    terms = []
    if request.method == 'POST':
        form = TranslationCheckForm(request.POST)
        if form.is_valid():
            old_lang = get_language()
            for lang, verbose in django_settings.LANGUAGES:
                translation_activate(lang)
                terms.append((lang, verbose, unicode(_(form.cleaned_data['term']))))
                translation_activate(old_lang)
    else:
        form = TranslationCheckForm()
    context['form'] = form
    if terms:
        context['form'].belowform = mark_safe(u'<br><br><ul class="list-group list-group-striped">{}</ul>'.format(
            u''.join([
                u"""
                <li class="list-group-item">
                <img src="{image}" height="30" />
                &nbsp;&nbsp;&nbsp;
                {term}
                <span class="pull-right text-muted">{verbose}</span>
                </li>
                """.format(
                    image=staticImageURL(language, folder='language'),
                    term=term,
                    verbose=verbose,
                )
                for language, verbose, term in terms
            ])
        ))

def homepage_arts(request, context):
    context['tabs'] = OrderedDict()
    context['art_position'] = HOMEPAGE_ART_POSITION
    context['homepage_art_gradient'] = HOMEPAGE_ART_GRADIENT
    if HOMEPAGE_BACKGROUNDS:
        available_backgrounds = []
        # Seasonal backgrounds
        if isVariableInAnyCurrentSeason('to_random_homepage_background'):
            available_backgrounds = [b for b in [
                getRandomVariableInCurrentSeasons(
                    'to_random_homepage_background', CUSTOM_SEASONAL_MODULE)()
                for _i in range(10)
            ] if b]
        if not available_backgrounds:
            available_backgrounds = HOMEPAGE_BACKGROUNDS
        context['backgrounds'] = [
            background.get('thumbnail', background['image'])
            for background in available_backgrounds
        ]
    elif HOMEPAGE_BACKGROUND:
        context['background'] = staticImageURL(HOMEPAGE_BACKGROUND)
    else:
        context['backgrounds'] = []

    def transform_homepage_arts(arts_to_transform):
        new_arts = []
        for art in arts_to_transform:
            if not art:
                continue
            sides = art.get('side', HOMEPAGE_ART_SIDE)
            for side in ([sides] if not isinstance(sides, list) else sides):
                new_arts.append(
                    (side, art, addParametersToURL(u'/', artSettingsToGetParameters(art)))
                )
        return new_arts

    context['can_show_random_for_character'] = bool(RANDOM_ART_FOR_CHARACTER)
    arts = transform_homepage_arts(HOMEPAGE_ARTS)

    # Show character's birthday examples
    if (RANDOM_ART_FOR_CHARACTER
        and getCharactersBirthdayToday()):
        context['tabs']['birthday_arts'] = {
            'name': 'Current birthday(s)',
            'arts': transform_homepage_arts([
                RANDOM_ART_FOR_CHARACTER(
                    random.choice(getCharactersBirthdayToday()))
                for _i in range(50)
            ]),
        }

    # 'Tis the season
    if isVariableInAnyCurrentSeason('to_random_homepage_art'):
        context['tabs']['seasonal_arts'] = {
            'name': 'Current season(s)',
            'arts': transform_homepage_arts([
                getRandomVariableInCurrentSeasons(
                    'to_random_homepage_art', CUSTOM_SEASONAL_MODULE)()
                for _i in range(50)
            ]),
        }

    context['tabs']['homepage_arts'] = {
        'name': 'Regular',
        'arts': arts,
    }

############################################################
# Errors

def handler500(request):
    return render(request, 'pages/error.html', {
        'error_code': 500,
        'page_title': 'Server error',
        'error_details': mark_safe('If the problem persists, please <a href="/about/#contact">contact us</a>.'),
    })

def handler403(request):
    return render(request, 'pages/error.html', {
        'error_code': 403,
        'page_title': 'Permission denied',
        'error_details': 'You are not allowed to access this page.',
    })

############################################################
# Seasonal

def adventcalendar(request, context, day=None):
    today = datetime.date.today()
    days_opened = request.user.preferences.extra.get('advent_calendar{}'.format(today.year), '').split(',')
    context['calendar'] = OrderedDict([
        (unicode(i_day), unicode(i_day) in days_opened)
        for i_day in range(1, 25)
    ])
    if day and day in context['calendar']:
        if day not in days_opened:

            # Open day
            if today.month != 12 or int(day) not in [today.day - 1, today.day, today.day + 1]:
                raise PermissionDenied()
            days_opened.append(day)
            context['calendar'][day] = True
            request.user.preferences.add_d('extra', 'advent_calendar{}'.format(today.year), u','.join(days_opened))
            request.user.preferences.save()

            # Add badge when all opened
            if day == '24' and 'badge' in context['all_enabled']:
                badge = django_settings.STAFF_CONFIGURATIONS.get('season_advent_calendar_badge_image', None)
                if badge:
                    total_opened = 0
                    for _day, opened in context['calendar'].items():
                        if opened:
                            total_opened += 1
                    if total_opened >= 21:
                        name = u'{} {}'.format(_('Merry Christmas!'), today.year)
                        try:
                            models.Badge.objects.filter(user=request.user, name=name)[0]
                        except IndexError:
                            description = 'Opened {} days of the advent calendar {}'.format(total_opened, today.year)
                            try:
                                badge_with_same_description = models.Badge.objects.filter(m_description=description)[0]
                            except IndexError:
                                badge_with_same_description = None
                            badge = models.Badge.objects.create(
                                date=today,
                                owner=get_default_owner(models.User),
                                user=request.user,
                                name=name,
                                m_description=description,
                                _cache_description=(
                                    badge_with_same_description._cache_description
                                    if badge_with_same_description else None
                                ),
                                image=staticImageURL(badge),
                                url='/adventcalendar/',
                                show_on_top_profile=False,
                                show_on_profile=True,
                            )
                            request.user.preferences.force_update_cache('tabs_with_content')
                            context['badge'] = badge

        context['day'] = day
        try:
            context['image'] = staticImageURL(
                simplejson.loads(django_settings.STAFF_CONFIGURATIONS.get(
                    'season_advent_calendar_images', {})).get(day, None)
            )
        except simplejson.JSONDecodeError:
            context['image'] = None

def endaprilfool(request, context):
    if getEventStatus((03, 31), (04, 03)) != 'current':
        raise PermissionDenied()
    badge_image = getattr(django_settings, 'SEASONAL_SETTINGS', {}).get('aprilfools', {}).get('extra', {}).get('badge_image', None)
    if not badge_image:
        return {}
    today = datetime.date.today()
    name = u'Happy April Fool\'s Day! {}'.format(today.year)
    description = 'Congratulations! You finished the event.'
    existing_badge = models.Badge.objects.filter(name=name, user=request.user).count()
    rank = None
    already_got = models.Badge.objects.filter(name=name).count()
    if existing_badge:
        return {
            'already_got': already_got,
        }
    if already_got < 3:
        rank = 3 - already_got
    models.Badge.objects.create(
        owner=get_default_owner(models.User),
        user=request.user,
        name=name, m_description=description, _cache_description=description,
        image=badge_image,
        rank=rank,
        show_on_profile=True,
        show_on_top_profile=False,
    )
    request.user.preferences.force_update_cache('tabs_with_content')
    return {
        'already_got': already_got,
        'added': True,
    }
