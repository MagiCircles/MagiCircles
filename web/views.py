from __future__ import division
import math, datetime
from django.utils import timezone
from collections import OrderedDict
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib.auth.views import login as login_view
from django.contrib.auth.views import logout as logout_view
from django.contrib.auth import authenticate, login as login_action
from django.utils.translation import ugettext_lazy as _, string_concat, get_language, activate as translation_activate
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.http import urlquote
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
from web.forms import CreateUserForm, UserForm, UserPreferencesForm, AddLinkForm, ChangePasswordForm, EmailsPreferencesForm, LanguagePreferencesForm
from web import models
from web.donations import donations
from web.utils import getGlobalContext, ajaxContext, redirectToProfile, AttrDict, ordinalNumber, tourldash, redirectWhenNotAuthenticated, dumpModel, send_email, emailContext
from web.notifications import pushNotification
from web.settings import SITE_NAME, GAME_NAME, ENABLED_COLLECTIONS, ENABLED_PAGES, FAVORITE_CHARACTERS, FAVORITE_CHARACTER_NAME, TWITTER_HANDLE, BUG_TRACKER_URL, GITHUB_REPOSITORY, CONTRIBUTE_URL, CONTACT_EMAIL, CONTACT_REDDIT, CONTACT_FACEBOOK, ABOUT_PHOTO, WIKI, LATEST_NEWS, SITE_LONG_DESCRIPTION, CALL_TO_ACTION, TOTAL_DONATORS, GAME_DESCRIPTION, GAME_URL, SHOW_TOTAL_ACCOUNTS, ON_USER_EDITED, ON_PREFERENCES_EDITED, PROFILE_EXTRA_TABS
from web.views_collections import item_view, list_view
from raw import other_sites

############################################################
# Index

def _index_extraContext(context):
    context['latest_news'] = LATEST_NEWS
    context['call_to_action'] = CALL_TO_ACTION
    context['total_donators'] = TOTAL_DONATORS
    context['is_feed'] = 'feed' in context['request'].GET
    now = timezone.now()
    context['this_month'] = datetime.datetime(year=now.year, month=now.month, day=1)
    try: context['donation_month'] = models.DonationMonth.objects.get(date=context['this_month'])
    except ObjectDoesNotExist: pass

def index(request):
    collection = ENABLED_COLLECTIONS['activity'].copy()
    collection['list'] = collection['list'].copy()
    collection['list']['before_template'] = 'include/homePage'
    collection['list']['extra_context'] = _index_extraContext
    if 'filter_form' in collection['list']:
        del(collection['list']['filter_form'])
    return list_view(request, 'activity', collection)

############################################################
# Login / Logout / Sign up

def login(request):
    context = getGlobalContext(request)
    context['next'] = request.GET['next'] if 'next' in request.GET else None
    context['next_title'] = request.GET['next_title'] if 'next_title' in request.GET else None
    return login_view(request, template_name='pages/login.html', extra_context=context)

def logout(request):
    return logout_view(request, next_page='index')

def signup(request):
    if request.user.is_authenticated():
        redirectToProfile(request)
    if request.method == "POST":
        form = CreateUserForm(request.POST, request=request)
        if form.is_valid():
            new_user = models.User.objects.create_user(**form.cleaned_data)
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            preferences = models.UserPreferences.objects.create(user=user, language=request.LANGUAGE_CODE)
            login_action(request, user)
            url = '/accounts/add/{}{}'.format(
                ('?next={}'.format(urlquote(request.GET['next'])) if 'next' in request.GET else ''),
                ('&next_title={}'.format(request.GET['next_title']) if 'next' in request.GET and 'next_title' in request.GET else ''))
            return redirect(url)
    else:
        form = CreateUserForm(request=request)
    context = getGlobalContext(request)
    context['form'] = form
    context['next'] = request.GET.get('next', None)
    context['next_title'] = request.GET.get('next_title', None)
    return render(request, 'pages/signup.html', context)

############################################################
# Profile

def profileExtraContext(context):
    user = context['item']
    request = context['request']
    context['is_me'] = user.id == request.user.id
    context['item'].all_links = list(context['item'].all_links)
    context['item'].latest_badges = list(context['item'].badges.filter(show_on_top_profile=True).order_by('id')[:6])
    if len(context['item'].latest_badges) == 6:
        context['more_badges'] = True
    context['item'].latest_badges = context['item'].latest_badges[:5]
    context['show_total_accounts'] = SHOW_TOTAL_ACCOUNTS
    context['profile_extra_tabs'] = PROFILE_EXTRA_TABS
    context['profile_tabs_size'] = 100 / ((2 if 'activity' in context['all_enabled'] else 1) + (len(PROFILE_EXTRA_TABS) if PROFILE_EXTRA_TABS else 0))
    meta_links = []
    if FAVORITE_CHARACTERS:
        for i in range(1, 4):
            if getattr(user.preferences, 'favorite_character{}'.format(i)):
                meta_links.append(AttrDict({
                    'type': (_(FAVORITE_CHARACTER_NAME) if FAVORITE_CHARACTER_NAME else _('{nth} Favorite Character')).format(nth=_(ordinalNumber(i))),
                    'raw_value': getattr(user.preferences, 'favorite_character{}'.format(i)),
                    'value': user.preferences.localized_favorite_character(i),
                    'translate_type': False,
                    'image': user.preferences.favorite_character_image(i),
                }))
    if user.preferences.location:
        meta_links.append(AttrDict({
            'type': 'Location',
            'value': user.preferences.location,
            'latlong': '{},{}'.format(user.preferences.latitude, user.preferences.longitude) if user.preferences.latitude else None,
            'translate_type': True,
            'flaticon': 'world',
        }))
    if user.preferences.birthdate:
        meta_links.append(AttrDict({
            'type': 'Birthdate',
            'value': u'{} ({})'.format(user.preferences.birthdate, _(u'{age} years old').format(age=user.preferences.age)),
            'translate_type': True,
            'flaticon': 'event',
            'raw_value': None,
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
    context['add_activity_sentence'] = _('Share your adventures!')
    if 'activity' in ENABLED_COLLECTIONS and 'list' in ENABLED_COLLECTIONS['activity'] and 'add_button_subtitle' in ENABLED_COLLECTIONS['activity']['list']:
        context['add_activity_sentence'] = ENABLED_COLLECTIONS['activity']['list']['add_button_subtitle']
    context['share_sentence'] = _('Check out {username}\'s awesome collection!').format(username=context['item'].username)
    context['share_url'] = context['item'].http_item_url

def user(request, pk=None, username=None):
    collection = ENABLED_COLLECTIONS['user']
    user = None
    if pk is None:
        queryset = collection['item']['filter_queryset'](collection['queryset'], {}, request) if 'filter_queryset' in collection['item'] else collection['queryset']
        user = get_object_or_404(queryset, username__iexact=username)
    return item_view(request, 'user', collection, pk=pk, ajax=False, item=user)

############################################################
# About

def aboutDefaultContext(request):
    context = getGlobalContext(request)
    context['about_description_template'] = 'include/about_description'
    context['about_photo'] = ABOUT_PHOTO
    context['site_long_description'] = SITE_LONG_DESCRIPTION
    context['twitter'] = TWITTER_HANDLE
    context['email'] = CONTACT_EMAIL
    context['reddit_user'] = CONTACT_REDDIT
    context['facebook'] = CONTACT_FACEBOOK
    context['bug_tracker_url'] = BUG_TRACKER_URL
    context['github_repository'] = GITHUB_REPOSITORY
    context['franchise'] = _('{site} is not a representative and is not associated with {game}. Its logos and images are Trademarks of {company}.').format(site=_(SITE_NAME), game=_(GAME_NAME), company=_('the company that owns {game}').format(game=GAME_NAME))
    context['staff'] = models.User.objects.filter(is_staff=True).select_related('preferences')
    context['api_enabled'] = False
    context['contribute_url'] = CONTRIBUTE_URL
    context['other_sites'] = other_sites
    context['other_sites_colsize'] = int(math.ceil(12 / (len(context['other_sites']) - 1)))
    context['ajax'] = context['current_url'].startswith('/ajax/')
    context['extends'] = 'base.html' if not context['ajax'] else 'ajax.html'
    return context

def about(request):
    return render(request, 'pages/about.html', aboutDefaultContext(request))

def about_game(request):
    context = getGlobalContext(request)
    context['game_description'] = GAME_DESCRIPTION
    context['game_url'] = GAME_URL
    return render(request, 'pages/about_game.html', context)

############################################################
# Settings

def settings(request):
    context = getGlobalContext(request)
    redirectWhenNotAuthenticated(request, context, next_title=_('Settings'))
    context['preferences'] = request.user.preferences
    context['accounts'] = request.user.accounts.all()
    context['forms'] = OrderedDict([
        ('preferences', UserPreferencesForm(instance=context['preferences'], request=request)),
        ('form', UserForm(instance=request.user, request=request)),
        ('changePassword', ChangePasswordForm(request=request)),
        ('emails', EmailsPreferencesForm(request=request)),
        ('addLink', AddLinkForm(request=request)),
    ])
    if request.method == 'POST':
        for (form_name, form) in context['forms'].items():
            if form_name in request.POST:
                if form_name == 'form':
                    form = UserForm(request.POST, instance=request.user, request=request)
                    if form.is_valid():
                        form.save()
                        models.updateCachedActivities(request.user.id)
                        if ON_USER_EDITED:
                            ON_USER_EDITED(request)
                        redirectToProfile(request)
                elif form_name == 'preferences':
                    form = UserPreferencesForm(request.POST, instance=context['preferences'], request=request)
                    if form.is_valid():
                        form.save()
                        if ON_PREFERENCES_EDITED:
                            ON_PREFERENCES_EDITED(request)
                        redirectToProfile(request)
                elif form_name == 'addLink':
                    form = AddLinkForm(request.POST, request=request)
                    if form.is_valid():
                        form.save()
                elif form_name == 'changePassword':
                    form = ChangePasswordForm(request.POST, request=request)
                    if form.is_valid():
                        form.save()
                        redirectToProfile(request)
                elif form_name == 'emails':
                    form = EmailsPreferencesForm(request.POST, request=request)
                    if form.is_valid():
                        form.save()
                        redirectToProfile(request)
                context['forms'][form_name] = form
    context['links'] = list(request.user.links.all())
    context['js_files'] = ['settings']
    context['favorite_characters'] = FAVORITE_CHARACTERS
    return render(request, 'pages/settings.html', context)

############################################################
# Help / Wiki

def help(request, wiki_url='Home'):
    context = getGlobalContext(request)
    context['wiki_url'] = wiki_url
    context['wiki'] = WIKI
    context['full_wiki_url'] = 'https://github.com/{}/{}/wiki/'.format(WIKI[0], WIKI[1])
    context['js_files'] = ['bower/marked/lib/marked', 'bower/github-wiki/js/githubwiki', 'wiki']
    return render(request, 'pages/wiki.html', context)

wiki = help

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

def moderatereport(request, report, action):
    if not request.user.is_authenticated() or not request.user.is_staff or request.method != 'POST':
        raise PermissionDenied()
    report = get_object_or_404(models.Report.objects.exclude(owner=request.user).select_related('owner', 'owner__preferences'), pk=report, status=models.REPORT_STATUS_PENDING)
    report.staff = request.user
    old_language = get_language()
    moderated_reports = []
    context = emailContext()
    context['report'] = report

    if action == 'Edited' or action == 'Deleted':

        # Get the reported thing
        queryset = ENABLED_COLLECTIONS[report.reported_thing]['queryset']
        thing = get_object_or_404(queryset, pk=report.reported_thing_id)

        # Make sure there's an owner
        if not hasattr(thing, 'owner'):
            if isinstance(thing, models.User):
                thing.owner = thing
            else:
                thing.owner = thing.user

        # Get staff message
        if 'staff_message' not in request.POST or not request.POST['staff_message']:
            raise PermissionDenied()
        report.staff_message = request.POST['staff_message']

    # Action: Ignore
    if action == 'Ignored':
        report.status = models.REPORT_STATUS_IGNORED
        report.save()
        moderated_reports = [report.pk]

    # Action: Edit
    elif action == 'Edited':
        context['item_url'] = thing.http_item_url if 'item' in ENABLED_COLLECTIONS[report.reported_thing] else None
        report.status = models.REPORT_STATUS_EDITED
        # Notify reporter
        if report.owner:
            translation_activate(report.owner.preferences.language if report.owner.preferences.language else 'en')
            context['sentence'] = _(u'This {thing} you reported has been reviewed by a moderator and {verb}. Thank you so much for your help!').format(thing=_(report.reported_thing_title), verb=_(u'edited'))
            context['user'] = report.owner
            context['show_donation'] = True
            context['subject'] = u'{} {}'.format(SITE_NAME, unicode(_(u'Thank you for reporting this {thing}').format(thing=_(report.reported_thing_title))))
            send_email(context['subject'], template_name='report', to=[context['user'].email], context=context)
        # Notify owner
        if thing.owner:
            translation_activate(thing.owner.preferences.language if thing.owner.preferences.language else 'en')
            context['sentence'] = _(u'Your {thing} has been reported, and a moderator confirmed it should be {verb}.').format(thing=_(report.reported_thing_title), verb=_(u'edited'))
            context['user'] = thing.owner
            context['show_donation'] = False
            context['subject'] = u'{} {}'.format(SITE_NAME, unicode(_(u'Your {thing} has been {verb}').format(thing=_(report.reported_thing_title), verb=_(u'edited'))))
            send_email(context['subject'], template_name='report', to=[context['user'].email], context=context)
        report.save()
        moderated_reports = [report.pk]

    elif action == 'Deleted':
        report.status = models.REPORT_STATUS_DELETED
        report.saved_data = dumpModel(thing)
        # Notify all reporters
        all_reports = models.Report.objects.filter(
            reported_thing=report.reported_thing,
            reported_thing_id=report.reported_thing_id,
            status=models.REPORT_STATUS_PENDING,
        ).select_related('owner', 'owner__preferences')
        for a_report in all_reports:
            if a_report.owner:
                translation_activate(a_report.owner.preferences.language if a_report.owner.preferences.language else 'en')
                context['sentence'] = _(u'This {thing} you reported has been reviewed by a moderator and {verb}. Thank you so much for your help!').format(thing=_(report.reported_thing_title), verb=_(u'deleted'))
                context['user'] = a_report.owner
                context['show_donation'] = True
                context['subject'] = u'{} {}'.format(SITE_NAME, unicode(_(u'Thank you for reporting this {thing}').format(thing=_(report.reported_thing_title))))
                send_email(context['subject'], template_name='report', to=[context['user'].email], context=context)
        # Notify owner
        if thing.owner:
            translation_activate(thing.owner.preferences.language if thing.owner.preferences.language else 'en')
            context['sentence'] = _(u'Your {thing} has been reported, and a moderator confirmed it should be {verb}.').format(thing=_(report.reported_thing_title), verb=_(u'edited'))
            context['user'] = thing.owner
            context['show_donation'] = False
            context['subject'] = u'{} {}'.format(SITE_NAME, unicode(_(u'Your {thing} has been {verb}').format(thing=_(report.reported_thing_title), verb=_(u'deleted'))))
            send_email(context['subject'], template_name='report', to=[context['user'].email], context=context)
        moderated_reports = [a_report.pk for a_report in all_reports]
        all_reports.update(
            staff=request.user,
            staff_message=report.staff_message,
            saved_data=report.saved_data,
            status=models.REPORT_STATUS_DELETED,
        )
        thing.delete()

    translation_activate(old_language)
    return JsonResponse({
        'moderated_reports': moderated_reports,
        'action': action,
    })

def changelanguage(request):
    if not request.user.is_authenticated():
        raise PermissionDenied()
    form = LanguagePreferencesForm(request.POST, instance=request.user.preferences, request=request)
    if form.is_valid():
        form.save()
    return redirect(request.POST.get('next', '/'))

@csrf_exempt
def likeactivity(request, pk):
    context = ajaxContext(request)
    if not request.user.is_authenticated() or request.method != 'POST':
        raise PermissionDenied()
    activity = get_object_or_404(models.Activity.objects.extra(select={
        'liked': 'SELECT COUNT(*) FROM web_activity_likes WHERE activity_id = web_activity.id AND user_id={}'.format(request.user.id),
    }).annotate(total_likes=Count('likes')).select_related('owner', 'owner__preferences'), pk=pk)
    if activity.cached_owner.username == request.user.username:
        raise PermissionDenied()
    if 'like' in request.POST and not activity.liked:
        activity.likes.add(request.user)
        activity.save()
        pushNotification(activity.owner, models.NOTIFICATION_LIKE, [unicode(request.user), unicode(activity)], url_values=[str(activity.id), tourldash(unicode(activity))], image=activity.image)
        return JsonResponse({
            'total_likes': activity.total_likes + 2,
            'result': 'liked',
        })
    if 'unlike' in request.POST and activity.liked:
        activity.likes.remove(request.user)
        activity.save()
        return JsonResponse({
            'total_likes': activity.total_likes,
            'result': 'unliked',
        })
    return JsonResponse({
        'total_likes': activity.total_likes + 1,
    })

@csrf_exempt
def follow(request, username):
    context = ajaxContext(request)
    if not request.user.is_authenticated() or request.method != 'POST' or request.user.username == username:
        raise PermissionDenied()
    user = get_object_or_404(models.User.objects.extra(select={
        'followed': 'SELECT COUNT(*) FROM web_userpreferences_following WHERE userpreferences_id = {} AND user_id = auth_user.id'.format(request.user.preferences.id),
    }).annotate(total_followers=Count('followers')).select_related('preferences'), username=username)
    if 'follow' in request.POST and not user.followed:
        request.user.preferences.following.add(user)
        request.user.preferences.save()
        pushNotification(user, models.NOTIFICATION_FOLLOW, [unicode(request.user)], url_values=[str(request.user.id), unicode(request.user)], image=models.avatar(request.user, size=100))
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
