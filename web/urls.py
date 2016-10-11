import string
from django.conf.urls import include, patterns, url
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, string_concat
from django.db.models import Count, Q, Prefetch
from django.db import connection
#from web import bouncy # unused, only to force load the feedback process
from web import views as web_views
from web import views_collections, models, forms
from web.settings import ENABLED_PAGES, ENABLED_COLLECTIONS, ENABLED_NAVBAR_LISTS, SITE_NAME, EMAIL_IMAGE, GAME_NAME, SITE_DESCRIPTION, SITE_STATIC_URL, SITE_URL, GITHUB_REPOSITORY, SITE_LOGO, JAVASCRIPT_TRANSLATED_TERMS, ACCOUNT_MODEL, STATIC_UPLOADED_FILES_PREFIX, COLOR, SITE_IMAGE, TRANSLATION_HELP_URL, DISQUS_SHORTNAME, HASHTAGS, TWITTER_HANDLE, EMPTY_IMAGE, GOOGLE_ANALYTICS, STATIC_FILES_VERSION, DONATE_IMAGE
from web.default_settings import RAW_CONTEXT

views_module = __import__(settings.SITE + '.views', fromlist=[''])

############################################################
# Update enabled collections with default values that couldn't be added in default without models and other values

def _userListFilterQuerySet(queryset, parameters, request):
    if 'followers_of' in parameters:
        queryset = queryset.filter(preferences__following__username=parameters['followers_of'])
    if 'followed_by' in parameters:
        queryset = queryset.filter(followers__user__username=parameters['followed_by'])
    if 'liked_activity' in parameters:
        queryset = queryset.filter(Q(pk__in=(models.Activity.objects.get(pk=parameters['liked_activity']).likes.all())) | Q(activities__id=parameters['liked_activity']))
    return queryset

def _reportFilter(queryset, parameters, request):
    if 'staff' in parameters and parameters['staff']:
        queryset = queryset.filter(staff=parameters['staff'])
    if 'status' in parameters and parameters['status']:
        queryset = queryset.filter(status=parameters['status'])
    else:
        queryset = queryset.filter(status=models.REPORT_STATUS_PENDING)
    if 'reported_thing' in parameters and parameters['reported_thing']:
        queryset = queryset.filter(reported_thing=parameters['reported_thing'])
    return queryset

def _userItemFilterQuerySet(queryset, parameters, request):
    if request.user.is_authenticated():
        queryset = queryset.extra(select={
            'followed': 'SELECT COUNT(*) FROM web_userpreferences_following WHERE userpreferences_id = {} AND user_id = auth_user.id'.format(request.user.preferences.id),
        })
        queryset = queryset.extra(select={
            'is_followed_by': 'SELECT COUNT(*) FROM web_userpreferences_following WHERE userpreferences_id = (SELECT id FROM web_userpreferences WHERE user_id = auth_user.id) AND user_id = {}'.format(request.user.id),
        })
    queryset = queryset.extra(select={
        'total_following': 'SELECT COUNT(*) FROM web_userpreferences_following WHERE userpreferences_id = (SELECT id FROM web_userpreferences WHERE user_id = auth_user.id)',
        'total_followers': 'SELECT COUNT(*) FROM web_userpreferences_following WHERE user_id = auth_user.id',
    })
    queryset = queryset.select_related('preferences', 'favorite_character1', 'favorite_character2', 'favorite_character3')
    queryset = queryset.prefetch_related(Prefetch('accounts', to_attr='all_accounts'), Prefetch('links', to_attr='all_links'))
    return queryset

if 'user' in ENABLED_COLLECTIONS:
    if 'item' in ENABLED_COLLECTIONS['user'] and 'extra_context' not in ENABLED_COLLECTIONS['user']['item']:
        ENABLED_COLLECTIONS['user']['item']['extra_context'] = web_views.profileExtraContext
    if 'item' in ENABLED_COLLECTIONS['user'] and 'filter_queryset' not in ENABLED_COLLECTIONS['user']['item']:
        ENABLED_COLLECTIONS['user']['item']['filter_queryset'] = _userItemFilterQuerySet
    if 'list' in ENABLED_COLLECTIONS['user'] and 'filter_queryset' not in ENABLED_COLLECTIONS['user']['list']:
        ENABLED_COLLECTIONS['user']['list']['filter_queryset'] = _userListFilterQuerySet
    if 'edit' in ENABLED_COLLECTIONS['user'] and 'form_class' not in ENABLED_COLLECTIONS['user']['edit']:
        ENABLED_COLLECTIONS['user']['edit']['form_class'] = forms.StaffEditUser

if 'activity' in ENABLED_COLLECTIONS:
    if 'queryset' not in ENABLED_COLLECTIONS['activity']:
        ENABLED_COLLECTIONS['activity']['queryset'] = models.Activity.objects.all().annotate(total_likes=Count('likes'))
    if 'list' in ENABLED_COLLECTIONS['activity'] and 'filter_form' not in ENABLED_COLLECTIONS['activity']['list']:
        ENABLED_COLLECTIONS['activity']['list']['filter_form'] = forms.FilterActivities
    if 'add' in ENABLED_COLLECTIONS['activity'] and 'form_class' not in ENABLED_COLLECTIONS['activity']['add']:
        ENABLED_COLLECTIONS['activity']['add']['form_class'] = forms.Activity
    if 'edit' in ENABLED_COLLECTIONS['activity'] and 'form_class' not in ENABLED_COLLECTIONS['activity']['edit']:
        ENABLED_COLLECTIONS['activity']['edit']['form_class'] = forms.Activity

if 'account' in ENABLED_COLLECTIONS:
    if 'queryset' not in ENABLED_COLLECTIONS['account']:
        ENABLED_COLLECTIONS['account']['queryset'] = ACCOUNT_MODEL.objects.all().select_related('owner', 'owner__preferences')
    if 'list' in ENABLED_COLLECTIONS['account'] and hasattr(ACCOUNT_MODEL, 'level') and 'default_ordering' not in ENABLED_COLLECTIONS['account']['list']:
        ENABLED_COLLECTIONS['account']['list']['default_ordering'] = 'level'

if 'report' in ENABLED_COLLECTIONS:
    if 'queryset' not in ENABLED_COLLECTIONS['report']:
        ENABLED_COLLECTIONS['report']['queryset'] = models.Report.objects.all().select_related('owner', 'owner__preferences', 'staff', 'staff__preferences').prefetch_related(Prefetch('images', to_attr='all_images'))
    if 'list' in ENABLED_COLLECTIONS['report']:
        if 'filter_form' not in ENABLED_COLLECTIONS['report']['list']:
            ENABLED_COLLECTIONS['report']['list']['filter_form'] = forms.FilterReports
        if 'filter_queryset' not in ENABLED_COLLECTIONS['report']['list']:
            ENABLED_COLLECTIONS['report']['list']['filter_queryset'] = _reportFilter
    if 'add' in ENABLED_COLLECTIONS['report'] and 'types' in ENABLED_COLLECTIONS['report']['add']:
        for key in ENABLED_COLLECTIONS['report']['add']['types'].keys():
            ENABLED_COLLECTIONS['report']['add']['types'][key]['form_class'] = forms.ReportForm
        if 'edit' in ENABLED_COLLECTIONS['report']:
            ENABLED_COLLECTIONS['report']['edit']['form_class'] = forms.ReportForm

if 'badge' in ENABLED_COLLECTIONS:
    if 'queryset' not in ENABLED_COLLECTIONS['badge']:
        ENABLED_COLLECTIONS['badge']['queryset'] = models.Badge.objects.all()
    if 'add' in ENABLED_COLLECTIONS['badge'] and 'form_class' not in ENABLED_COLLECTIONS['badge']['add']:
        ENABLED_COLLECTIONS['badge']['add']['form_class'] = forms.BadgeForm
    if 'edit' in ENABLED_COLLECTIONS['badge'] and 'form_class' not in ENABLED_COLLECTIONS['badge']['edit']:
        ENABLED_COLLECTIONS['badge']['edit']['form_class'] = forms.BadgeForm

def _notificationMarkAsRead(context):
    to_update = [item.pk for item in context['items'] if not item.seen]
    if to_update:
        updated = models.Notification.objects.filter(pk__in=to_update).update(seen=True)
        if updated:
            context['request'].user.preferences.unread_notifications -= updated
            if context['request'].user.preferences.unread_notifications < 0:
                context['request'].user.preferences.unread_notifications = 0
            context['request'].user.preferences.save()
    return context

if 'notification' in ENABLED_COLLECTIONS:
    if 'queryset' not in ENABLED_COLLECTIONS['notification']:
        ENABLED_COLLECTIONS['notification']['queryset'] = models.Notification.objects.all()
    if 'list' in ENABLED_COLLECTIONS['notification'] and 'extra_context' not in ENABLED_COLLECTIONS['notification']['list']:
        ENABLED_COLLECTIONS['notification']['list']['extra_context'] = _notificationMarkAsRead

def _donateExtraContext(context):
    request = context['request']
    context['show_paypal'] = 'show_paypal' in request.GET
    context['donate_image'] = DONATE_IMAGE

if 'donate' in ENABLED_COLLECTIONS:
    if 'queryset' not in ENABLED_COLLECTIONS['donate']:
        ENABLED_COLLECTIONS['donate']['queryset'] = models.DonationMonth.objects.all().prefetch_related(Prefetch('badges', queryset=models.Badge.objects.select_related('user', 'user__preferences').order_by('-show_on_profile'), to_attr='all_badges'))
    if 'list' in ENABLED_COLLECTIONS['donate'] and 'extra_context' not in ENABLED_COLLECTIONS['donate']['list']:
        ENABLED_COLLECTIONS['donate']['list']['extra_context'] = _donateExtraContext

############################################################
# Navbar lists with dropdowns

RAW_CONTEXT['navbar_links'] = []
RAW_CONTEXT['navbar_links_lists'] = ENABLED_NAVBAR_LISTS.copy()
urls = [
    #url(r'^bouncy/', include('django_bouncy.urls', app_name='django_bouncy')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^password_reset[/]+$', 'django.contrib.auth.views.password_reset', {
        'template_name': 'password/password_reset_form.html',
        'html_email_template_name': 'password/password_reset_email_html.html',
        'from_email': settings.PASSWORD_EMAIL,

    }, name='password_reset'),
    url(r'^password_reset/done[/]+$', 'django.contrib.auth.views.password_reset_done', {
        'template_name': 'password/password_reset_done.html'
    }, name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 'django.contrib.auth.views.password_reset_confirm', {
        'template_name': 'password/password_reset_confirm.html'
    }, name='password_reset_confirm'),
    url(r'^reset/done[/]+$', 'django.contrib.auth.views.password_reset_complete', {
        'template_name': 'password/password_reset_complete.html'
    }, name='password_reset_complete'),
]

def navbarAddLink(link, list_name):
    if list_name:
        if list_name not in RAW_CONTEXT['navbar_links_lists']:
            RAW_CONTEXT['navbar_links_lists'][list_name] = {
                'title': _(string.capwords(list_name)),
                'links': [],
            }
        if 'links' not in RAW_CONTEXT['navbar_links_lists'][list_name]:
            RAW_CONTEXT['navbar_links_lists'][list_name]['links'] = []
        RAW_CONTEXT['navbar_links_lists'][list_name]['links'].append(link)
    else:
        RAW_CONTEXT['navbar_links'].append(link)

RAW_CONTEXT['all_enabled'] = []

############################################################
# URLs for collections

for (name, collection) in ENABLED_COLLECTIONS.items():
    if 'plural_name' not in collection:
        collection['plural_name'] = '{}s'.format(name)
    if 'title' not in collection:
        collection['title'] = string.capwords(name)
    if 'plural_title' not in collection:
        collection['plural_title'] = string.capwords(collection['plural_name'])
    if not collection.get('enabled', True):
        continue
    parameters = {
        'name': name,
        'collection': collection,
    }
    ajax_parameters = parameters.copy()
    ajax_parameters['ajax'] = True
    if collection.get('list', None) is not None:
        if name not in RAW_CONTEXT['all_enabled']:
            RAW_CONTEXT['all_enabled'].append(name)
        url_name = '{}_list'.format(name)
        urls.append(url(r'^{}[/]+$'.format(collection['plural_name']), views_collections.list_view, parameters, name=url_name))
        if collection['list'].get('ajax', True):
            urls.append(url(r'^ajax/{}/$'.format(collection['plural_name']), views_collections.list_view, ajax_parameters, name='{}_ajax'.format(url_name)))
        navbar_link = collection.get('navbar_link', True)
        if navbar_link:
            link = {
                'url_name': url_name,
                'url': '/{}/'.format(collection['plural_name']),
                'title': collection['plural_title'],
                'icon': collection.get('icon', None),
                'image': collection.get('image', None),
                'auth': (True, False) if collection['list'].get('authentication_required', False) else (True, True),
                'get_url': None,
                'staff_required': collection['list'].get('staff_required', False),
            }
            navbarAddLink(link, collection.get('navbar_link_list', None))
    if collection.get('item', None) is not None:
        url_name = '{}_item'.format(name)
        urls.append(url(r'^{}/(?P<pk>\d+)[/]+$'.format(name), views_collections.item_view, parameters, name=url_name))
        urls.append(url(r'^{}/(?P<pk>\d+)[/]+$'.format(collection['plural_name'], name), views_collections.item_view, parameters, name=url_name))
        urls.append(url(r'^{}/(?P<pk>\d+)/[\w-]+[/]+$'.format(name, name), views_collections.item_view, parameters, name=url_name))
        urls.append(url(r'^{}/(?P<pk>\d+)/[\w-]+[/]+$'.format(collection['plural_name'], name), views_collections.item_view, parameters, name=url_name))
        if collection['item'].get('ajax', True):
            urls.append(url(r'^ajax/{}/(?P<pk>\d+)/$'.format(name), views_collections.item_view, ajax_parameters, name='{}_ajax'.format(url_name)))
    if collection.get('add', None) is not None:
        url_name = '{}_add'.format(name)
        if 'types' in collection['add']:
            urls.append(url(r'^{}/add/(?P<type>[\w_]+)[/]+$'.format(collection['plural_name']), views_collections.add_view, parameters, name=url_name))
            if collection['add'].get('ajax', True):
                urls.append(url(r'^ajax/{}/add/(?P<type>[\w_]+)[/]+$'.format(collection['plural_name']), views_collections.add_view, ajax_parameters, name='{}_ajax'.format(url_name)))
        else:
            urls.append(url(r'^{}/add[/]+$'.format(collection['plural_name']), views_collections.add_view, parameters, name=url_name))
            if collection['add'].get('ajax', True):
                urls.append(url(r'^ajax/{}/add[/]+$'.format(collection['plural_name']), views_collections.add_view, ajax_parameters, name='{}_ajax'.format(url_name)))
    if collection.get('edit', None) is not None:
        url_name = '{}_edit'.format(name)
        urls.append(url(r'^{}/edit/(?P<pk>\d+)/$'.format(collection['plural_name']), views_collections.edit_view, parameters, name=url_name))
        if collection['edit'].get('ajax', True):
            urls.append(url(r'^ajax/{}/edit/(?P<pk>\d+)/$'.format(collection['plural_name']), views_collections.edit_view, ajax_parameters, name='{}_ajax'.format(url_name)))

############################################################
# URLs for pages

def getURLLambda(name, lambdas):
    return (lambda context: '/{}/{}/'.format(name, '/'.join([f(context) for f in lambdas])))

for (name, pages) in ENABLED_PAGES.items():
    if not isinstance(pages, list):
        pages = [pages]
    for page in pages:
        if 'title' not in page:
            page['title'] = string.capwords(name)
        if not page.get('enabled', True):
            continue
        if name not in RAW_CONTEXT['all_enabled']:
            RAW_CONTEXT['all_enabled'].append(name)
        function = (getattr(views_module, name)
                    if page.get('custom', True)
                    else getattr(web_views, name))
        ajax = page.get('ajax', False)
        if name == 'index':
            urls.append(url(r'^$', function, name=name))
        else:
            url_variables = '/'.join(['(?P<{}>{})'.format(v[0], v[1]) for v in page.get('url_variables', [])])
            urls.append(url(r'^{}{}{}[/]+$'.format('ajax/' if ajax else '', name, '/' + url_variables if url_variables else ''),
                            function, name=name if not ajax else '{}_ajax'.format(name)))
        if not ajax:
            navbar_link = page.get('navbar_link', True)
            if navbar_link:
                lambdas = [(v[2] if len(v) >= 3 else (lambda x: x)) for v in page.get('url_variables', [])]
                link = {
                    'url_name': name,
                    'url': '/{}/'.format(name),
                    'title': page['title'],
                    'icon': page.get('icon', None),
                    'image': page.get('image', None),
                    'auth': page.get('navbar_link_auth', (True, True)),
                    'get_url': None if not page.get('url_variables', None) else (getURLLambda(name, lambdas)),
                    'staff_required': page.get('staff_required', False),
                }
                navbarAddLink(link, page.get('navbar_link_list', None))

urlpatterns = patterns('', *urls)

############################################################
# Set data in RAW_CONTEXT

RAW_CONTEXT['site_name'] = SITE_NAME
RAW_CONTEXT['site_url'] = SITE_URL
RAW_CONTEXT['github_repository'] = GITHUB_REPOSITORY
RAW_CONTEXT['site_description'] = SITE_DESCRIPTION
RAW_CONTEXT['game_name'] = GAME_NAME
RAW_CONTEXT['static_url'] = SITE_STATIC_URL + 'static/'
RAW_CONTEXT['full_static_url'] = u'http:{}'.format(RAW_CONTEXT['static_url']) if 'http' not in RAW_CONTEXT['static_url'] else RAW_CONTEXT['static_url']
RAW_CONTEXT['site_logo'] = SITE_LOGO
RAW_CONTEXT['disqus_shortname'] = DISQUS_SHORTNAME
RAW_CONTEXT['javascript_translated_terms'] = JAVASCRIPT_TRANSLATED_TERMS
RAW_CONTEXT['site_color'] = COLOR
RAW_CONTEXT['site_image'] = RAW_CONTEXT['static_url'] + 'img/' + SITE_IMAGE if '//' not in SITE_IMAGE else SITE_IMAGE
RAW_CONTEXT['full_site_image'] = u'http:{}'.format(RAW_CONTEXT['site_image']) if 'http' not in RAW_CONTEXT['site_image'] else RAW_CONTEXT['site_image']
RAW_CONTEXT['email_image'] = RAW_CONTEXT['static_url'] + 'img/' + EMAIL_IMAGE if '//' not in EMAIL_IMAGE else EMAIL_IMAGE
RAW_CONTEXT['full_email_image'] = u'http:{}'.format(RAW_CONTEXT['email_image']) if 'http' not in RAW_CONTEXT['email_image'] else RAW_CONTEXT['email_image']
RAW_CONTEXT['translation_help_url'] = TRANSLATION_HELP_URL
RAW_CONTEXT['hashtags'] = HASHTAGS
RAW_CONTEXT['twitter_handle'] = TWITTER_HANDLE
RAW_CONTEXT['empty_image'] = EMPTY_IMAGE
RAW_CONTEXT['google_analytics'] = GOOGLE_ANALYTICS
RAW_CONTEXT['static_files_version'] = STATIC_FILES_VERSION
