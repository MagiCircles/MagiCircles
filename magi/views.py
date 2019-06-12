from __future__ import division
import math, datetime, random
from collections import OrderedDict
from django.shortcuts import render, get_object_or_404, redirect
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
from django.db.models import Count, Prefetch
from magi.middleware.httpredirect import HttpRedirectException
from magi.forms import (
    CreateUserForm,
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
)
from magi import models
from magi.raw import donators_adjectives
from magi.utils import (
    getGlobalContext,
    ajaxContext,
    redirectToProfile,
    tourldash,
    toHumanReadable,
    redirectWhenNotAuthenticated,
    dumpModel,
    send_email,
    emailContext,
    getMagiCollection,
    getMagiCollections,
    cuteFormFieldsForContext,
    CuteFormType,
    FAVORITE_CHARACTERS_IMAGES,
    BACKGROUNDS_THUMBNAILS,
    groupsForAllPermissions,
    hasPermission,
    staticImageURL,
    find_all_translations,
    duplicate_translation,
    hasGoodReputation,
    getColSize,
)
from magi.notifications import pushNotification
from magi.settings import (
    SITE_NAME,
    SITE_NAME_PER_LANGUAGE,
    GAME_NAME,
    FAVORITE_CHARACTERS,
    BACKGROUNDS,
    TWITTER_HANDLE,
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
    SITE_LOGO_PER_LANGUAGE,
    GLOBAL_OUTSIDE_PERMISSIONS,
    CUSTOM_PREFERENCES_FORM,
    HOMEPAGE_BACKGROUND,
    HOMEPAGE_ARTS,
    RANDOM_ART_FOR_CHARACTER,
    HOMEPAGE_ART_POSITION,
    HOMEPAGE_ART_SIDE,
    HOMEPAGE_ART_GRADIENT,
    HOMEPAGE_RIBBON,
    LANGUAGES_CANT_SPEAK_ENGLISH,
)
from magi.views_collections import item_view

if CUSTOM_PREFERENCES_FORM:
    forms_module = __import__(django_settings.SITE + '.forms', fromlist=[''])

############################################################
# Login / Logout / Sign up

def login(request):
    context = getGlobalContext(request)
    context['next'] = request.GET['next'] if 'next' in request.GET else None
    context['next_title'] = request.GET['next_title'] if 'next_title' in request.GET else None
    del(context['form'])
    return login_view(request, template_name='pages/login.html', extra_context=context)

def logout(request):
    return logout_view(request, next_page='/')

def signup(request):
    if request.user.is_authenticated():
        redirectToProfile(request)
    context = getGlobalContext(request)
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
            if preferences.age > 18:
                if 'hot' in models.UserPreferences.DEFAULT_ACTIVITIES_TABS:
                    preferences.i_default_activities_tab = models.UserPreferences.get_i(
                        'default_activities_tab', 'hot')
            else:
                preferences.d_hidden_tags = '{"swearing": true, "questionable": true, "nsfw": true}'
                preferences.i_private_message_settings = models.UserPreferences.get_i('private_message_settings', 'follow')
            preferences.save()
            login_action(request, user)
            if context.get('launch_date', None):
                return redirect('/prelaunch/')
            url = u'/accounts/add/{}{}'.format(
                (u'?next={}'.format(urlquote(request.GET['next'])) if 'next' in request.GET else ''),
                (u'&next_title={}'.format(request.GET['next_title']) if 'next' in request.GET and 'next_title' in request.GET else ''))
            return redirect(url)
    else:
        form = CreateUserForm(request=request)
    context['form'] = form
    context['next'] = request.GET.get('next', None)
    context['next_title'] = request.GET.get('next_title', None)
    context['js_files'] = ['signup']
    return render(request, 'pages/signup.html', context)

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

    # Homepage arts
    if HOMEPAGE_ARTS:
        context['full_width'] = True

        # Staff can preview art and/or foreground
        if (context['request'].user.is_authenticated()
            and context['request'].user.hasPermission('manage_main_items')
            and (context['request'].GET.get('preview', None)
                 or context['request'].GET.get('foreground_preview', None))):
            context['art'] = {
                k: v for k, v in (
                    ('url', context['request'].GET.get('preview', None)),
                    ('foreground_url', context['request'].GET.get('foreground_preview', None)),
                ) if v
            }
        # Staff can preview foreground
        elif (context['request'].user.is_authenticated()
            and context['request'].user.hasPermission('manage_main_items')
            and 'foreground_preview' in context['request'].GET):
            context['art']['foreground_url'] = context['request'].GET['foreground_preview']
        # 1 chance out of 5 to get a random art of 1 of your favorite characters
        elif (RANDOM_ART_FOR_CHARACTER
              and context['request'].user.is_authenticated()
              and context['request'].user.preferences.favorite_characters
              and random.randint(0, 5) == 5):
            character_id = random.choice(context['request'].user.preferences.favorite_characters)
            context['art'] = RANDOM_ART_FOR_CHARACTER(character_id)
            if not context['art']:
                context['art'] = random.choice(HOMEPAGE_ARTS).copy()
        else:
            context['art'] = random.choice(HOMEPAGE_ARTS).copy()

        # Position of art with CSS
        context['art_position'] = context['art'].get('position', None)
        if not context['art_position']:
            context['art_position'] = HOMEPAGE_ART_POSITION
        else:
            for key, value in HOMEPAGE_ART_POSITION.items():
                if key not in context['art_position']:
                    context['art_position'][key] = value

        # When a foreground is provided but no background, use a random background in BACKGROUNDS
        if context['art'].has_key('foreground_url') and not context['art'].has_key('url') and BACKGROUNDS:
            background = random.choice(BACKGROUNDS)
            if background.has_key('thumbnail'):
                context['art']['url'] = background['thumbnail']
                context['art']['hd_url'] = background['image']
            else:
                context['art']['url'] = background['image']

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
        return redirect('/prelaunch/')
    indexExtraContext(context)
    context['ajax_callback'] = 'loadIndex'
    return render(request, 'pages/index.html', context)

############################################################
# Prelaunch

def prelaunch(request, *args, **kwargs):
    context = getGlobalContext(request)
    context['page_definers'] = context.get('page_definers', []) + ['homepage']
    context['about_site_sentence'] = _('About {thing}').format(thing=context['t_site_name'])
    context['about_game_sentence'] = _('About {thing}').format(thing=context['t_game_name'])
    context['homepage_background'] = HOMEPAGE_BACKGROUND
    if SITE_LOGO_PER_LANGUAGE:
        logo_per_language = SITE_LOGO_PER_LANGUAGE.get(get_language(), None)
        if logo_per_language:
            context['site_logo'] = staticImageURL(logo_per_language)
    if not context.get('launch_date', None):
        return redirect('signup')
    context['twitter'] = TWITTER_HANDLE
    return render(request, 'pages/prelaunch.html', context)

############################################################
# Profile

def user(request, pk=None, username=None):
    return item_view(request, 'user', getMagiCollection('user'), pk=pk, ajax=False)

############################################################
# About

def aboutDefaultContext(request):
    context = getGlobalContext(request)
    context['about_description_template'] = 'include/about_description'
    context['about_photo'] = ABOUT_PHOTO
    context['site_long_description'] = SITE_LONG_DESCRIPTION
    context['about_site_sentence'] = _('About {thing}').format(thing=context['t_site_name'])
    context['feedback_form'] = FEEDBACK_FORM
    context['contact_email'] = CONTACT_EMAIL
    context['contact_methods'] = [
        ('Discord', 'discord', CONTACT_DISCORD),
        ('Twitter', 'twitter', u'https://twitter.com/{}/'.format(TWITTER_HANDLE) if TWITTER_HANDLE else None),
        ('Reddit', 'reddit', u'https://www.reddit.com/user/{}/'.format(CONTACT_REDDIT) if CONTACT_REDDIT else None),
        ('Facebook', 'facebook', u'https://facebook.com/{}/'.format(CONTACT_FACEBOOK) if CONTACT_FACEBOOK else None),
        (_('Email'), 'flaticon-contact', u'mailto:{}'.format(CONTACT_EMAIL if CONTACT_EMAIL else None)),
        ('GitHub', 'github', u'https://github.com/{}/{}/'.format(GITHUB_REPOSITORY[0], GITHUB_REPOSITORY[1]) if GITHUB_REPOSITORY else None),
        ('Bug tracker', 'flaticon-album', BUG_TRACKER_URL if BUG_TRACKER_URL and not FEEDBACK_FORM else None),
    ]
    context['franchise'] = _('{site} is not a representative and is not associated with {game}. Its logos and images are Trademarks of {company}.').format(
        site=SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME),
        game=GAME_NAME, company=_('the company that owns {game}').format(game=GAME_NAME))
    context['staff'] = list(models.User.objects.filter(is_staff=True).select_related('preferences', 'staff_details').prefetch_related(
        Prefetch('links', queryset=models.UserLink.objects.order_by('-i_relevance'), to_attr='all_links'),
    ).extra(select={
        'length_of_groups': 'Length(c_groups)',
        'is_manager': 'CASE WHEN c_groups LIKE \'%%\"manager\"%%\' THEN 1 ELSE 0 END',
        'is_management': 'CASE WHEN c_groups LIKE "%%manager%%" THEN 1 ELSE 0 END',
    }).order_by('-is_manager', '-is_management', '-length_of_groups'))
    context['contributors'] = [
        user for user in models.User.objects.filter(
            is_staff=False, preferences__c_groups__isnull=False).exclude(
                preferences__c_groups='').select_related(
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
                    model = getattr(models, stat['model'])
                    total = model.objects.filter(**{ stat.get('selector_to_owner', model.selector_to_owner()): staff_member }).filter(**(stat.get('filters', {}))).count()
                    if total:
                        staff_member.stats[group].append(mark_safe(unicode(stat['template']).format(total=u'<strong>{}</strong>'.format(total))))
            settings = staff_member.preferences.t_settings_per_groups.get(group, None)
            if settings:
                for setting, value in settings.items():
                    staff_member.stats[group].append(u'<strong>{}</strong>: {}'.format(
                        setting, value))

        if not staff_member.is_staff:
            continue

        # Availability calendar
        try:
            staff_member.has_staff_details = bool(staff_member.staff_details.id) if staff_member.is_staff else None
        except models.StaffDetails.DoesNotExist:
            staff_member.has_staff_details = False
            staff_member.staff_details = models.StaffDetails()
        if request.user.is_staff and staff_member.has_staff_details and (staff_member.staff_details.d_availability or staff_member.staff_details.d_weekend_availability):
            staff_member.show_calendar = True
            if my_timezone and staff_member.staff_details.timezone:
                staff_member.availability_calendar = staff_member.staff_details.availability_calendar_timezone(my_timezone)
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

    context['extends'] = 'base.html' if not context['ajax'] else 'ajax.html'
    return context

def about(request):
    return render(request, 'pages/about.html', aboutDefaultContext(request))

def about_game(request):
    context = getGlobalContext(request)
    context['game_description'] = GAME_DESCRIPTION
    context['game_url'] = GAME_URL
    return render(request, 'ajax/about_game.html', context)

############################################################
# Settings

def _settingsOnSuccess(form, added=False):
    if not hasattr(form, 'beforefields') or not form.beforefields:
        form.beforefields = u''
    form.beforefields += u'<p class="alert alert-info"><i class="flaticon-about"></i> {}</p>'.format(
        _('Successfully edited!') if not added else _('Successfully added!'),
    )
    form.beforefields = mark_safe(form.beforefields)

def settingsContext(request):
    context = getGlobalContext(request)
    redirectWhenNotAuthenticated(request, context, next_title=_('Settings'))
    context['preferences'] = request.user.preferences
    context['accounts'] = request.user.accounts.all()
    context['page_title'] = _('Settings')

    preferences_form_class = (
        forms_module.UserPreferencesForm
        if CUSTOM_PREFERENCES_FORM
        else UserPreferencesForm
    )

    account_collection = getMagiCollection('account')
    context['add_account_sentence'] = account_collection.add_sentence
    context['add_link_sentence'] = _(u'Add {thing}').format(thing=_('Link'))
    context['delete_link_sentence'] = _(u'Delete {thing}').format(thing=_('Link'))
    context['accounts_title_sentence'] = account_collection.plural_title
    context['back_to_profile_sentence'] = _('Back to {page_name}').format(page_name=_('Profile').lower())

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
    a_month_ago = now - datetime.timedelta(days=30)
    context['reports'] = list(models.Report.objects.filter(
        reported_thing_owner_id=request.user.id,
        i_status__in=[
            models.Report.get_i('status', 'Deleted'),
            models.Report.get_i('status', 'Edited'),
        ],
        modification__gte=a_month_ago,
    ).order_by('-modification'))
    for report in context['reports']:
        report.introduction_sentence = mark_safe(
            _(u'Your {thing} has been reported, and a moderator confirmed it should be {verb}.').format(**{
                'thing': u'<a href="/{thing}/{id}/">{title}</a>'.format(
                    thing=report.reported_thing,
                    id=report.reported_thing_id,
                    title=unicode(report).lower(),
                ),
                'verb': _(u'edited'),
            } if report.status == 'Edited' else {
                'thing': unicode(report).lower(),
                'verb': _(u'deleted'),
            }))

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
            'to_cuteform': lambda k, v: BACKGROUNDS_THUMBNAILS[k],
            'title': _('Background'),
            'extra_settings': {
                'modal': 'true',
	        'modal-text': 'true',
            },
        },
    }
    if FAVORITE_CHARACTERS:
        for i in range(1, 4):
            filter_cuteform['favorite_character{}'.format(i)] = {
                'to_cuteform': lambda k, v: FAVORITE_CHARACTERS_IMAGES[k],
                'extra_settings': {
	            'modal': 'true',
	            'modal-text': 'true',
                },
            }
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
    return context

def settings(request):
    context = settingsContext(request)
    return render(request, 'pages/settings.html', context)

############################################################
# Help / Wiki

def custom_wiki(wiki, wiki_name, request, wiki_url):
    context = getGlobalContext(request)
    context['wiki_url'] = wiki_url
    context['page_title'] = wiki_name if wiki_url in ['Home', '_Sidebar'] else u'{} - {}'.format(wiki_url.replace('_', ' ').replace('-', ' '), wiki_name)
    context['hide_side_bar'] = wiki_url == '_Sidebar'
    context['small_container'] = True
    context['wiki'] = wiki
    context['full_wiki_url'] = 'https://github.com/{}/{}/wiki/'.format(wiki[0], wiki[1])
    context['js_files'] = ['bower/marked/lib/marked', 'bower/github-wiki/js/githubwiki', 'wiki']
    context['back_to_home_sentence'] = _('Back to {page_name}').format(
        page_name=_('Wiki home').lower(),
    )
    return render(request, 'pages/wiki.html', context)

def help(request, wiki_url='_Sidebar'):
    return custom_wiki(HELP_WIKI, _('Help'), request, wiki_url)

def wiki(request, wiki_url='Home'):
    return custom_wiki(WIKI, _('Wiki'), request, wiki_url)

############################################################
# Map

def mapDefaultContext(request):
    context = getGlobalContext(request)
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
    return context

def map(request):
    return render(request, 'pages/map.html', mapDefaultContext(request))

############################################################
# Block

def block(request, pk, unblock=False):
    context = getGlobalContext(request)
    redirectWhenNotAuthenticated(request, context, next_title=_('Settings'))
    user = get_object_or_404(models.User.objects.select_related('preferences'), pk=pk)
    block = True
    if request.user.preferences.blocked.filter(pk=user.pk).exists():
        block = False
        context['info_message'] = _(u'You blocked {username}.').format(username=user.username)
    context['blocking'] = block
    title = _(u'Block {username}').format(username=user.username) if block else _(u'Unblock {username}').format(username=user.username)
    context['page_title'] = title
    context['extends'] = 'base.html'
    context['form'] = Confirm()
    context['alert_message'] = (_(u'Are you sure you want to block {username}? You will not be able to see any content created by {username}.') if block else _(u'Are you sure you want to unblock {username}?')).format(username=user.username)
    context['alert_type'] = 'danger'
    context['alert_flaticon'] = 'block'
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
    return render(request, 'pages/block.html', context)

############################################################
# Avatar redirection for gravatar + twitter

def twitter_avatar(request, twitter):
    return redirect('https://twitter.com/{}/profile_image?size=original'.format(twitter))

############################################################
# Ajax

def deletelink(request, pk):
    if not request.user.is_authenticated():
        raise PermissionDenied()
    models.UserLink.objects.filter(owner=request.user, pk=pk).delete()
    return HttpResponse('')

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

def whatwillbedeleted(request, thing, thing_id):
    context = ajaxContext(request)
    collection = getMagiCollection(thing)
    instance = _getInstanceFromThingId(thing, thing_id, collection=collection)
    context['to_delete'] = _cascadeDeleteInstances(instance)
    context['warnings'] = _deleteCascadeWarnings(thing=collection.title.lower(), instance=instance)
    return render(request, 'ajax/whatwillbedeleted.html', context)

def moderatereport(request, report, action):
    if not request.user.is_authenticated() or not hasPermission(request.user, 'moderate_reports') or request.method != 'POST':
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
            context['sentence'] = _(u'This {thing} you reported has been reviewed by a moderator and {verb}. Thank you so much for your help!').format(thing=_(report.reported_thing_title), verb=_(u'edited'))
            context['user'] = report.owner
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
                unicode(_(u'Your {thing} has been {verb}').format(thing=_(report.reported_thing_title), verb=_(u'edited'))),
            )
            send_email(context['subject'], template_name='report', to=[context['user'].email], context=context)
        report.save()
        moderated_reports = [report.pk]

    elif action == 'Deleted':
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

def reportwhatwillbedeleted(request, report):
    if not request.user.is_authenticated() or not hasPermission(request.user, 'moderate_reports'):
        raise PermissionDenied()
    context = ajaxContext(request)
    # Get the report
    report = get_object_or_404(models.Report, pk=report, i_status=models.Report.get_i('status', 'Pending'))
    # Get the reported thing
    instance = _getInstanceFromThingId(report.reported_thing, report.reported_thing_id)

    context['to_delete'] = _cascadeDeleteInstances(instance)
    context['warnings'] = _deleteCascadeWarnings(thing=report.reported_thing, instance=instance)
    return render(request, 'ajax/whatwillbedeleted.html', context)

def changelanguage(request):
    if not request.user.is_authenticated():
        raise PermissionDenied()
    form = LanguagePreferencesForm(request.POST, instance=request.user.preferences, request=request)
    if form.is_valid():
        form.save()
    return redirect(request.POST.get('next', '/'))

def markallnotificationsread(request):
    if not request.user.is_authenticated():
        raise PermissionDenied()
    read = request.user.notifications.filter(seen=False).update(seen=True)
    request.user.preferences.force_update_cache('unread_notifications')
    return redirect(u'/notifications/?marked_read={}'.format(read))

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
    if not hasGoodReputation(request):
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

def likeactivity(request, pk):
    context = ajaxContext(request)
    if not request.user.is_authenticated() or request.method != 'POST':
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
        return JsonResponse({
            'total_likes': activity.total_likes + 2,
            'result': 'liked',
        })
    if 'unlike' in request.POST and activity.liked:
        activity.likes.remove(request.user)
        activity.update_cache('total_likes')
        activity.save()
        return JsonResponse({
            'total_likes': activity.total_likes,
            'result': 'unliked',
        })
    return JsonResponse({
        'total_likes': activity.total_likes + 1,
    })

def archiveactivity(request, pk):
    context = ajaxContext(request)
    if not request.user.is_authenticated() or request.method != 'POST':
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
        return JsonResponse({
            'result': {
                'archived': activity.archived_by_owner,
                'archived_by_staff': activity.archived_by_staff.username if activity.archived_by_staff else None,
            },
        })
    # We don't want to reveal users if the activity is ghost archived if they check the request
    return JsonResponse({
        'result': {
            'archived': activity.archived_by_owner,
        },
    })

def unarchiveactivity(request, pk):
    context = ajaxContext(request)
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
        return JsonResponse({
            'result': {
                'archived': activity.archived_by_owner,
                'archived_by_staff': activity.archived_by_staff.username if activity.archived_by_staff else None,
            },
        })
    # We don't want to reveal users if the activity is ghost archived if they check the request
    return JsonResponse({
        'result': {
            'archived': activity.archived_by_owner,
        },
    })

def bumpactivity(request, pk):
    context = ajaxContext(request)
    if (not request.user.is_authenticated() or request.method != 'POST'
        or not request.user.hasPermission('manipulate_activities')):
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity, pk=pk)
    activity.last_bump = timezone.now()
    activity.save()
    return JsonResponse({
        'result': 'bumped',
    })

def drownactivity(request, pk):
    context = ajaxContext(request)
    if (not request.user.is_authenticated() or request.method != 'POST'
        or not request.user.hasPermission('manipulate_activities')):
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity, pk=pk)
    now = timezone.now()
    a_month_ago = now - datetime.timedelta(days=30)
    activity.last_bump = a_month_ago
    activity.save()
    return JsonResponse({
        'result': 'drowned',
    })

def markactivitystaffpick(request, pk):
    context = ajaxContext(request)
    if (not request.user.is_authenticated() or request.method != 'POST'
        or 'staff' not in models.ACTIVITY_TAGS_DICT.keys()
        or not request.user.hasPermission('mark_activities_as_staff_pick')):
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity, pk=pk)
    activity.add_c('tags', ['staff'])
    activity.save()
    return JsonResponse({
        'result': {
            'staff-picks': True,
            'tags': {
                k: unicode(v)
                for k, v in activity.t_tags.items()
            },
        },
    })

def removeactivitystaffpick(request, pk):
    context = ajaxContext(request)
    if (not request.user.is_authenticated() or request.method != 'POST'
        or 'staff' not in models.ACTIVITY_TAGS_DICT.keys()
        or not request.user.hasPermission('mark_activities_as_staff_pick')):
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity, pk=pk)
    activity.remove_c('tags', ['staff'])
    activity.save()
    return JsonResponse({
        'result': {
            'staff-picks': False,
            'tags': {
                k: unicode(v)
                for k, v in activity.t_tags.items()
            },
        },
    })

def follow(request, username):
    context = ajaxContext(request)
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
        return JsonResponse({
            'total_followers': user.total_followers + 1,
            'result': 'followed',
        })
    if 'unfollow' in request.POST and user.followed:
        request.user.preferences.following.remove(user)
        request.user.preferences.save()
        return JsonResponse({
            'total_followers': user.total_followers - 1,
            'result': 'unfollowed',
        })
    return JsonResponse({
        'total_followers': user.total_followers,
    })

def successedit(request):
    ajax = request.path_info.startswith('/ajax/')
    context = ajaxContext(request) if ajax else getGlobalContext(request)
    context['success_sentence'] = _('Successfully edited!')
    return render(request, 'pages/ajax/success.html' if ajax else 'pages/success.html', context)

def successadd(request):
    ajax = request.path_info.startswith('/ajax/')
    context = ajaxContext(request) if ajax else getGlobalContext(request)
    context['success_sentence'] = _('Successfully added!')
    return render(request, 'pages/ajax/success.html' if ajax else 'pages/success.html', context)

def successdelete(request):
    ajax = request.path_info.startswith('/ajax/')
    context = ajaxContext(request) if ajax else getGlobalContext(request)
    context['success_sentence'] = _('Successfully deleted!')
    return render(request, 'pages/ajax/success.html' if ajax else 'pages/success.html', context)

############################################################
# Staff / Contributors

def translations(request):
    context = getGlobalContext(request)
    redirectWhenNotAuthenticated(request, context, next_title='Translations')
    if not hasPermission(request.user, 'translate_items'):
        raise PermissionDenied()
    context['page_title'] = 'Translations'
    context['collections'] = []
    context['guide'] = models.UserPreferences.GROUPS.get('translator', {}).get('guide', None)
    context['poeditor'] = models.UserPreferences.GROUPS.get('translator', {}).get('outside_permissions', {}).get('POEditor', None)
    context['total_per_languages'] = {}
    context['total'] = 0
    context['total_need_translations'] = 0
    context['see_all'] = 'see_all' in request.GET
    only_languages = (request.user.preferences.settings_per_groups or {}).get('translator', {}).get('languages', {})
    if context['see_all']:
        only_languages = {}
    if 'language' in request.GET:
        only_languages = request.GET['language'].split(u',')
    for collection in getMagiCollections().values():
        if collection.translated_fields:
            c = {
                'name': collection.name,
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

                for language, verbose_name in languages:
                    if only_languages and language not in only_languages:
                        continue
                    if language not in c['translated_fields_per_languages']:
                        c['translated_fields_per_languages'][language] = {
                            'verbose_name': verbose_name,
                            'fields': [],
                            'image': staticImageURL(language, folder='language', extension='png')
                        }
                    items_with_something_to_translate = collection.queryset.exclude(**{
                        u'{}__isnull'.format(field): True,
                    }).exclude(**{
                        field: '',
                    })
                    count_total = items_with_something_to_translate.count()
                    count_need_translations = items_with_something_to_translate.exclude(**{
                        u'd_{}s__contains'.format(field): u'"{}"'.format(language),
                    }).count()
                    if not count_total:
                        continue
                    c['translated_fields_per_languages'][language]['fields'].append({
                        'name': field,
                        'verbose_name': collection.queryset.model._meta.get_field_by_name(field)[0].verbose_name or toHumanReadable(field),
                        'total': count_total,
                        'total_need_translations': count_need_translations,
                        'total_translated': count_total - count_need_translations,
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
    context['percent_translated'] = int(context['total_translated'] / context['total'] * 100)
    for language, details in context['total_per_languages'].items():
        details['total_translated'] = details['total'] - details['total_need_translations']
        details['percent_translated'] = int(details['total_translated'] / details['total'] * 100)
    return render(request, 'pages/staff/translations.html', context)

def translations_duplicator(request, collection_name, field_name, language=None):
    context = getGlobalContext(request)
    redirectWhenNotAuthenticated(request, context, next_title='Translations duplicator')
    if not hasPermission(request.user, 'translate_items'):
        raise PermissionDenied()
    collection = getMagiCollection(collection_name)
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
    if request.method == 'POST' and 'term' in request.POST:
        context['logs'] = duplicate_translation(
            collection.queryset.model, field_name, request.POST['term'],
            only_for_language=language, print_log=False, html_log=True,
        )

    context['terms'] = find_all_translations(collection.queryset.model, field_name, only_for_language=language)
    return render(request, 'pages/staff/translations_duplicator.html', context)

def collections(request):
    context = getGlobalContext(request)
    redirectWhenNotAuthenticated(request, context, next_title='Collections details')
    if not hasPermission(request.user, 'see_collections_details'):
        raise PermissionDenied()
    context['page_title'] = 'Collections'
    context['collections'] = getMagiCollections()
    context['groups_per_permissions'] = groupsForAllPermissions(request.user.preferences.GROUPS)
    return render(request, 'pages/staff/collections.html', context)

def translations_check(request):
    context = getGlobalContext(request)
    if request.method == 'POST':
        form = TranslationCheckForm(request.POST)
        if form.is_valid():
            context['terms'] = []
            old_lang = get_language()
            for lang, verbose in django_settings.LANGUAGES:
                translation_activate(lang)
                context['terms'].append((lang, verbose, unicode(_(form.cleaned_data['term']))))
                translation_activate(old_lang)
    else:
        form = TranslationCheckForm()
    context['form'] = form
    context['page_title'] = 'POEditor translations term checker'
    return render(request, 'pages/staff/translations_check.html', context)


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
