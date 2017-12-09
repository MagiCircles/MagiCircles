from __future__ import division
import math, datetime
from collections import OrderedDict
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.views import login as login_view
from django.contrib.auth.views import logout as logout_view
from django.contrib.auth import authenticate, login as login_action
from django.contrib.admin.utils import get_deleted_objects
from django.utils.translation import ugettext_lazy as _, string_concat, get_language, activate as translation_activate
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.http import urlquote
from django.utils import timezone
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
from magi.forms import CreateUserForm, UserForm, UserPreferencesForm, AddLinkForm, ChangePasswordForm, EmailsPreferencesForm, LanguagePreferencesForm
from magi import models
from magi.utils import getGlobalContext, ajaxContext, redirectToProfile, tourldash, redirectWhenNotAuthenticated, dumpModel, send_email, emailContext, getMagiCollection, cuteFormFieldsForContext, CuteFormType, FAVORITE_CHARACTERS_IMAGES
from magi.notifications import pushNotification
from magi.settings import SITE_NAME, GAME_NAME, ENABLED_PAGES, FAVORITE_CHARACTERS, TWITTER_HANDLE, BUG_TRACKER_URL, GITHUB_REPOSITORY, CONTRIBUTE_URL, CONTACT_EMAIL, CONTACT_REDDIT, CONTACT_FACEBOOK, ABOUT_PHOTO, WIKI, LATEST_NEWS, SITE_LONG_DESCRIPTION, CALL_TO_ACTION, TOTAL_DONATORS, GAME_DESCRIPTION, GAME_URL, ON_USER_EDITED, ON_PREFERENCES_EDITED, ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT, SITE_LOGO_PER_LANGUAGE
from magi.views_collections import item_view, list_view
from raw import other_sites

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
    if context.get('launch_date', None):
        return redirect('/prelaunch/')
    if request.method == "POST":
        form = CreateUserForm(request.POST, request=request)
        if form.is_valid():
            new_user = models.User.objects.create_user(**form.cleaned_data)
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            preferences = models.UserPreferences.objects.create(
                user=user,
                i_language=request.LANGUAGE_CODE,
                view_activities_language_only=ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT,
            )
            login_action(request, user)
            url = '/accounts/add/{}{}'.format(
                ('?next={}'.format(urlquote(request.GET['next'])) if 'next' in request.GET else ''),
                ('&next_title={}'.format(request.GET['next_title']) if 'next' in request.GET and 'next_title' in request.GET else ''))
            return redirect(url)
    else:
        form = CreateUserForm(request=request)
    context['form'] = form
    context['next'] = request.GET.get('next', None)
    context['next_title'] = request.GET.get('next_title', None)
    return render(request, 'pages/signup.html', context)

############################################################
# Index

def indexExtraContext(context):
    context['latest_news'] = LATEST_NEWS
    context['call_to_action'] = CALL_TO_ACTION
    context['total_donators'] = TOTAL_DONATORS
    context['is_feed'] = 'feed' in context['request'].GET
    now = timezone.now()
    if 'donate' in context['all_enabled']:
        context['this_month'] = datetime.datetime(year=now.year, month=now.month, day=1)
        try: context['donation_month'] = models.DonationMonth.objects.get(date=context['this_month'])
        except ObjectDoesNotExist: pass
    if SITE_LOGO_PER_LANGUAGE:
        logo_per_language = SITE_LOGO_PER_LANGUAGE.get(get_language(), None)
        if logo_per_language:
            context['site_logo'] = context['static_url'] + 'img/' + logo_per_language if '//' not in logo_per_language else logo_per_language

def index(request):
    context = getGlobalContext(request)
    indexExtraContext(context)
    return render(request, 'pages/index.html', context)

############################################################
# Prelaunch

def prelaunch(request, *args, **kwargs):
    context = getGlobalContext(request)
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
    return render(request, 'ajax/about_game.html', context)

############################################################
# Settings

def settings(request):
    context = getGlobalContext(request)
    redirectWhenNotAuthenticated(request, context, next_title=_('Settings'))
    context['preferences'] = request.user.preferences
    context['accounts'] = request.user.accounts.all()
    context['add_account_sentence'] = _(u'Add {thing}').format(thing=_('Account'))
    context['add_link_sentence'] = _(u'Add {thing}').format(thing=_('Link'))
    context['delete_link_sentence'] = _(u'Delete {thing}').format(thing=_('Link'))
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
    filter_cuteform = {
        'i_language': {
            'type': CuteFormType.Images,
            'image_folder': 'language',
        },
        'color': {
            'type': CuteFormType.Images,
        },
    }
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
        'type': {
            'image_folder': 'links',
        },
        'relevance': {
            'type': CuteFormType.HTML,
        },
    }, context, context['forms']['addLink'])
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
    report = get_object_or_404(models.Report.objects.exclude(owner=request.user).select_related('owner', 'owner__preferences'), pk=report, i_status=models.Report.get_i('status', 'Pending'))

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
        report.i_status = models.Report.get_i('status', 'Deleted')
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
            i_status=models.Report.get_i('status', 'Deleted'),
        )
        thing.delete()

    translation_activate(old_language)
    return JsonResponse({
        'moderated_reports': moderated_reports,
        'action': action,
    })

def reportwhatwillbedeleted(request, report):
    if not request.user.is_authenticated() or not request.user.is_staff:
        raise PermissionDenied()
    context = ajaxContext(request)
    # Get the report
    report = get_object_or_404(models.Report, pk=report, i_status=models.Report.get_i('status', 'Pending'))
    # Get the reported thing
    queryset = report.reported_thing_collection.queryset
    thing = get_object_or_404(queryset, pk=report.reported_thing_id)

    from django.contrib.admin.util import NestedObjects

    collector = NestedObjects(using='default') # or specific database
    collector.collect([thing])
    context['report'] = report
    context['to_delete'] = collector.nested()
    return render(request, 'ajax/reportwhatwillbedeleted.html', context)

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
        'liked': 'SELECT COUNT(*) FROM magi_activity_likes WHERE activity_id = magi_activity.id AND user_id={}'.format(request.user.id),
    }).annotate(total_likes=Count('likes')).select_related('owner', 'owner__preferences'), pk=pk)
    if activity.cached_owner.username == request.user.username:
        raise PermissionDenied()
    if 'like' in request.POST and not activity.liked:
        activity.likes.add(request.user)
        activity.save()
        pushNotification(activity.owner, 'like', [unicode(request.user), unicode(activity)], url_values=[str(activity.id), tourldash(unicode(activity))], image=activity.image)
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
        'followed': 'SELECT COUNT(*) FROM magi_userpreferences_following WHERE userpreferences_id = {} AND user_id = auth_user.id'.format(request.user.preferences.id),
    }).annotate(total_followers=Count('followers')).select_related('preferences'), username=username)
    if 'follow' in request.POST and not user.followed:
        request.user.preferences.following.add(user)
        request.user.preferences.save()
        pushNotification(user, 'follow', [unicode(request.user)], url_values=[str(request.user.id), unicode(request.user)], image=models.avatar(request.user, size=100))
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
    context = ajaxContext(request)
    return render(request, 'pages/ajax/successedit.html')

def successadd(request):
    context = ajaxContext(request)
    return render(request, 'pages/ajax/successadd.html')
