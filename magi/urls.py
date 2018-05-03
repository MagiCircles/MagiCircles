import string, inspect
from collections import OrderedDict
from django.conf.urls import include, patterns, url
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _, string_concat
from django.utils import timezone
#from magi import bouncy # unused, only to force load the feedback process
from magi import views_collections, magicollections
from magi import views as magi_views
from magi import forms
from magi.settings import RAW_CONTEXT, ENABLED_PAGES, ENABLED_NAVBAR_LISTS, SITE_NAME, EMAIL_IMAGE, GAME_NAME, SITE_DESCRIPTION, SITE_STATIC_URL, SITE_URL, GITHUB_REPOSITORY, SITE_LOGO, SITE_NAV_LOGO, JAVASCRIPT_TRANSLATED_TERMS, STATIC_UPLOADED_FILES_PREFIX, COLOR, SITE_IMAGE, TRANSLATION_HELP_URL, DISQUS_SHORTNAME, HASHTAGS, TWITTER_HANDLE, EMPTY_IMAGE, GOOGLE_ANALYTICS, STATIC_FILES_VERSION, PROFILE_TABS, LAUNCH_DATE, PRELAUNCH_ENABLED_PAGES, NAVBAR_ORDERING, ACCOUNT_MODEL, STAFF_CONFIGURATIONS, FIRST_COLLECTION, GET_STARTED_VIDEO, GLOBAL_OUTSIDE_PERMISSIONS, GROUPS
from magi.models import UserPreferences
from magi.utils import redirectWhenNotAuthenticated, hasPermissions, hasOneOfPermissions, tourldash, groupsWithPermissions, groupsWithOneOfPermissions

############################################################
# Load dynamic module based on SITE

views_module = __import__(settings.SITE + '.views', fromlist=[''])
custom_magicollections_module = __import__(settings.SITE + '.magicollections', fromlist=['']).__dict__

############################################################
# Vatiables

navbar_links = OrderedDict()
now = timezone.now()
launched = not LAUNCH_DATE or LAUNCH_DATE < now
collections = OrderedDict()
enabled = {}
all_enabled = []
urls = []
collectible_collections = {}

############################################################
# Default enabled URLs (outside of collections + pages)

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

############################################################
# Navbar lists with dropdowns

def navbarAddLink(link_name, link, list_name=None):
    if list_name:
        if list_name not in navbar_links:
            navbar_links[list_name] = {
                'is_list': True,
                # show_link_callback gets added when links get ordered
            }
            navbar_links[list_name].update(ENABLED_NAVBAR_LISTS.get(list_name, OrderedDict()))
            if 'title' not in navbar_links[list_name]:
                navbar_links[list_name]['title'] = _(string.capwords(list_name))
            if 'links' not in navbar_links[list_name]:
                navbar_links[list_name]['links'] = OrderedDict()
        navbar_links[list_name]['links'][link_name] = link
    else:
        link['is_list'] = False
        navbar_links[link_name] = link

############################################################
# URLs for collections

def getURLLambda(name, lambdas):
    return (lambda context: u'/{}/{}/'.format(name, '/'.join([f(context) for f in lambdas])))

def getCollectionShowLinkLambda(collection):
    return (lambda context: collection.list_view.has_permissions(context['request'], context))

def _addToCollections(name, cls): # Class of the collection
    collection = cls()
    collection.list_view = collection.ListView(collection)
    collection.item_view = collection.ItemView(collection)
    collection.add_view = collection.AddView(collection)
    collection.edit_view = collection.EditView(collection)
    collection.to_form_class()
    collection.edit_view.to_translate_form_class()
    for view in ['list', 'item', 'add', 'edit']:
        getattr(collection, view + '_view').prelaunch_staff_required = not launched and u'{}_{}'.format(collection.name, view) not in PRELAUNCH_ENABLED_PAGES
    all_enabled.append(collection.name)
    collections[collection.name] = collection
    if collection.collectible:
        collectible_model_classes = collection.collectible if isinstance(collection.collectible, list) else [collection.collectible]
        collection.collectible_collections = OrderedDict()
        for model_class in collectible_model_classes:
            collectible_collection_class = collection.collectible_to_class(model_class)
            if collectible_collection_class:
                collectible_collection = _addToCollections(model_class.collection_name, collectible_collection_class)
                if collectible_collection:
                    collection.collectible_collections[collectible_collection.name] = collectible_collection
                    fk_as_owner = collectible_collection.queryset.model.fk_as_owner or 'owner'
                    if fk_as_owner not in collectible_collections:
                        collectible_collections[fk_as_owner] = {}
                    collectible_collections[fk_as_owner][collectible_collection.name] = collectible_collection
                    if (collectible_collection.name == FIRST_COLLECTION and not collection.list_view.before_template
                        and 'get_started' in STAFF_CONFIGURATIONS):
                        collection.list_view.before_template = 'include/getstarted'
    return collection

def _addToEnabledCollections(name, cls, is_custom):
    if name != 'MagiCollection' and inspect.isclass(cls) and issubclass(cls, magicollections.MagiCollection) and not name.startswith('_'):
        if cls.enabled:
            cls.is_custom = is_custom
            enabled[name] = cls
        elif name in enabled:
            del(enabled[name])

# Determine the list of collections that should be enabled
for name, cls in magicollections.__dict__.items():
    _addToEnabledCollections(name, cls, False)
for name, cls in custom_magicollections_module.items():
    _addToEnabledCollections(name, cls, True)

# Instanciate collection objects
for name, cls in enabled.items():
    _addToCollections(name, cls)

# Add collection URLs to router
for collection in collections.values():
    parameters = {
        'name': collection.name,
        'collection': collection,
    }
    ajax_parameters = parameters.copy()
    ajax_parameters['ajax'] = True
    if collection.list_view.enabled:
        url_name = '{}_list'.format(collection.name)
        urls.append(url(r'^{}[/]*$'.format(collection.plural_name), views_collections.list_view, parameters, name=url_name))
        if collection.list_view.ajax:
            urls.append(url(r'^ajax/{}/$'.format(collection.plural_name), views_collections.list_view, ajax_parameters, name='{}_ajax'.format(url_name)))
        for shortcut_url in collection.list_view.shortcut_urls:
            shortcut_parameters = parameters.copy()
            shortcut_parameters['shortcut_url'] = shortcut_url
            urls.append(url(r'^{}[/]*$'.format(shortcut_url), views_collections.list_view, shortcut_parameters, name=url_name))
        if collection.navbar_link:
            link = {
                'url_name': url_name,
                'url': '/{}/'.format(collection.plural_name),
                'title': collection.navbar_link_title,
                'icon': collection.icon,
                'image': collection.image,
                'auth': (True, False) if collection.list_view.authentication_required else (True, True),
                'show_link_callback': getCollectionShowLinkLambda(collection),
                'divider_before': collection.navbar_link_list_divider_before,
                'divider_after': collection.navbar_link_list_divider_after,
            }
            navbarAddLink(url_name, link, collection.navbar_link_list)
    if collection.item_view.enabled:
        url_name = '{}_item'.format(collection.name)
        urls.append(url(r'^{}/(?P<pk>\d+)[/]*$'.format(collection.name), views_collections.item_view, parameters, name=url_name))
        urls.append(url(r'^{}/(?P<pk>\d+)[/]*$'.format(collection.plural_name), views_collections.item_view, parameters, name=url_name))
        urls.append(url(r'^{}/(?P<pk>\d+)/[\w-]+[/]*$'.format(collection.name), views_collections.item_view, parameters, name=url_name))
        urls.append(url(r'^{}/(?P<pk>\d+)/[\w-]+[/]*$'.format(collection.plural_name), views_collections.item_view, parameters, name=url_name))
        if collection.item_view.ajax:
            urls.append(url(r'^ajax/{}/(?P<pk>\d+)/$'.format(collection.name), views_collections.item_view, ajax_parameters, name='{}_ajax'.format(url_name)))
        if collection.item_view.reverse_url:
            urls.append(url(r'^{}/(?P<reverse>[\w-]+)[/]*$'.format(collection.name), views_collections.item_view, parameters, name=url_name))
            urls.append(url(r'^{}/(?P<reverse>[\w-]+)[/]*$'.format(collection.plural_name), views_collections.item_view, parameters, name=url_name))
        for shortcut_url, pk in collection.item_view.shortcut_urls:
            shortcut_parameters = parameters.copy()
            shortcut_parameters['shortcut_url'] = shortcut_url
            shortcut_parameters['pk'] = pk
            urls.append(url(r'^{}[/]*$'.format(shortcut_url), views_collections.item_view, shortcut_parameters, name=url_name))
    if collection.add_view.enabled:
        url_name = '{}_add'.format(collection.name)
        if collection.types:
            urls.append(url(r'^{}/add/(?P<type>[\w_]+)[/]*$'.format(collection.name), views_collections.add_view, parameters, name=url_name))
            urls.append(url(r'^{}/add/(?P<type>[\w_]+)[/]*$'.format(collection.plural_name), views_collections.add_view, parameters, name=url_name))
            if collection.add_view.ajax:
                urls.append(url(r'^ajax/{}/add/(?P<type>[\w_]+)[/]*$'.format(collection.name), views_collections.add_view, ajax_parameters, name='{}_ajax'.format(url_name)))
                urls.append(url(r'^ajax/{}/add/(?P<type>[\w_]+)[/]*$'.format(collection.plural_name), views_collections.add_view, ajax_parameters, name='{}_ajax'.format(url_name)))
            for shortcut_url, _type in collection.add_view.shortcut_urls:
                shortcut_parameters = parameters.copy()
                shortcut_parameters['shortcut_url'] = shortcut_url
                shortcut_parameters['type'] = _type
                urls.append(url(r'^{}[/]*$'.format(shortcut_url), views_collections.add_view, shortcut_parameters, name=url_name))
        else:
            urls.append(url(r'^{}/add[/]*$'.format(collection.name), views_collections.add_view, parameters, name=url_name))
            urls.append(url(r'^{}/add[/]*$'.format(collection.plural_name), views_collections.add_view, parameters, name=url_name))
            if collection.AddView.ajax:
                urls.append(url(r'^ajax/{}/add[/]*$'.format(collection.plural_name), views_collections.add_view, ajax_parameters, name='{}_ajax'.format(url_name)))
            for shortcut_url in collection.add_view.shortcut_urls:
                shortcut_parameters = parameters.copy()
                shortcut_parameters['shortcut_url'] = shortcut_url
                urls.append(url(r'^{}[/]*$'.format(shortcut_url), views_collections.add_view, shortcut_parameters, name=url_name))
    if collection.edit_view.enabled:
        url_name = '{}_edit'.format(collection.name)
        urls.append(url(r'^{}/edit/(?P<pk>\d+|unique)/$'.format(collection.name), views_collections.edit_view, parameters, name=url_name))
        urls.append(url(r'^{}/edit/(?P<pk>\d+|unique)/$'.format(collection.plural_name), views_collections.edit_view, parameters, name=url_name))
        if collection.edit_view.ajax:
            urls.append(url(r'^ajax/{}/edit/(?P<pk>\d+|unique)/$'.format(collection.name), views_collections.edit_view, ajax_parameters, name='{}_ajax'.format(url_name)))
            urls.append(url(r'^ajax/{}/edit/(?P<pk>\d+|unique)/$'.format(collection.plural_name), views_collections.edit_view, ajax_parameters, name='{}_ajax'.format(url_name)))
        for shortcut_url, pk in collection.item_view.shortcut_urls:
            shortcut_parameters = parameters.copy()
            shortcut_parameters['shortcut_url'] = shortcut_url
            shortcut_parameters['pk'] = pk
            urls.append(url(r'^{}[/]*$'.format(shortcut_url), views_collections.item_view, shortcut_parameters, name=url_name))

############################################################
# URLs for pages

def getPageShowLinkLambda(page):
    def _showLink(context):
        permissions_required = page.get('permissions_required', [])
        one_of_permissions_required = page.get('one_of_permissions_required', [])
        return not (
            (page.get('authentication_required', False) and not context['request'].user.is_authenticated())
            or (page.get('logout_required', False) and context['request'].user.is_authenticated())
            or (page.get('staff_required', False) and not context['request'].user.is_staff)
            or (permissions_required and (
                not context['request'].user.is_authenticated()
                or not hasPermissions(context['request'].user, permissions_required)
            ))
            or (one_of_permissions_required and (
                not context['request'].user.is_authenticated()
                or not hasOneOfPermissions(context['request'].user, one_of_permissions_required)
            ))
        )
    return _showLink

def page_view(name, page):
    function = (
        getattr(views_module, name)
        if page.get('custom', True)
        else getattr(magi_views, name)
    )
    def _f(request, *args, **kwargs):
        if request.user.is_authenticated():
            if (page.get('logout_required', False)
                or (page.get('staff_required', False) and not request.user.is_staff)):
                raise PermissionDenied()
        elif page.get('authentication_required', False) or page.get('staff_required', False):
            redirectWhenNotAuthenticated(request, {
                'current_url': request.get_full_path() + ('?' if request.get_full_path()[-1] == '/' else '&'),
            }, next_title=page.get('title', ''))
        return function(request, *args, **kwargs)
    return _f

for (name, pages) in ENABLED_PAGES.items():
    if not isinstance(pages, list):
        pages = [pages]
    for page in pages:
        if not launched:
            if name not in PRELAUNCH_ENABLED_PAGES:
                page['staff_required'] = True
        if 'title' not in page:
            page['title'] = string.capwords(name)
        if not page.get('enabled', True):
            continue
        if name not in all_enabled:
            all_enabled.append(name)
        ajax = page.get('ajax', False)
        redirect = page.get('redirect', None)
        if not redirect:
            if name == 'index':
                urls.append(url(r'^$', page_view(name, page), name=name))
            else:
                url_variables = '/'.join(['(?P<{}>{})'.format(v[0], v[1]) for v in page.get('url_variables', [])])
                urls.append(url(r'^{}{}{}[/]*$'.format('ajax/' if ajax else '', name, '/' + url_variables if url_variables else ''),
                                page_view(name, page), name=name if not ajax else '{}_ajax'.format(name)))
        if not ajax:
            navbar_link = page.get('navbar_link', True)
            if navbar_link:
                lambdas = [(v[2] if len(v) >= 3 else (lambda x: x)) for v in page.get('url_variables', [])]
                link = {
                    'url_name': name,
                    'url': redirect or '/{}/'.format(name),
                    'title': page['title'],
                    'icon': page.get('icon', None),
                    'image': page.get('image', None),
                    'new_tab': page.get('new_tab', False),
                    'auth': page.get('navbar_link_auth', (True, True)),
                    'get_url': None if not page.get('url_variables', None) else (getURLLambda(name, lambdas)),
                    'show_link_callback': getPageShowLinkLambda(page),
                    'divider_before': page.get('divider_before', False),
                    'divider_after': page.get('divider_after', False),
                }
                navbarAddLink(name, link, page.get('navbar_link_list', None))

############################################################
# Add staff links to navbar

for permission, url in GLOBAL_OUTSIDE_PERMISSIONS.items():
    if url:
        url_name = u'staff-global-{}'.format(tourldash(permission).lower())
        navbarAddLink(url_name, {
            'url_name': url_name,
            'url': url,
            'title': permission,
            'show_link_callback': lambda context: context['request'].user.is_staff,
            'new_tab': True,
        }, 'staff')

def _getPageShowLinkForGroupsLambda(group):
    def _show_link_callback(context):
        return context['request'].user.is_authenticated() and context['request'].user.hasGroup(group)
    return _show_link_callback

_groups_dict = dict(GROUPS)
_links_for_groups = {}
_links_to_show_first = []

# Retrieve collections and pages that will be in staff dropdown to put them at the right place in order
for collection in collections.values():
    if (collection.navbar_link_list == 'staff'
        and collection.list_view.enabled):
        view_with_permissions = collection.list_view if collection.name != 'badge' else collection.add_view
        if (collection.name != 'staffdetails'
            and (view_with_permissions.permissions_required
                 or view_with_permissions.one_of_permissions_required)):
            groups = []
            if view_with_permissions.permissions_required:
                groups += groupsWithPermissions(_groups_dict, view_with_permissions.permissions_required).keys()
            if view_with_permissions.one_of_permissions_required:
                groups += groupsWithOneOfPermissions(_groups_dict, view_with_permissions.one_of_permissions_required).keys()
            for group in groups:
                if group not in _links_for_groups:
                    _links_for_groups[group] = []
                name = u'{}-{}_list'.format(group, collection.name)
                _links_for_groups[group].append(name)
                navbarAddLink(name, {
                    'title': collection.plural_title,
                    'url': collection.get_list_url(),
                    'show_link_callback': _getPageShowLinkForGroupsLambda(group),
                }, 'staff')
                if u'{}_list'.format(collection.name) in navbar_links['staff']['links']:
                    del(navbar_links['staff']['links'][u'{}_list'.format(collection.name)])
        else:
            _links_to_show_first.append(u'{}_list'.format(collection.name))
for name, pages in ENABLED_PAGES.items():
    if not isinstance(pages, list):
        pages = [pages]
    for page in pages:
        if page.get('navbar_link_list') == 'staff':
            if (page.get('permissions_required', [])
                or page.get('one_of_permissions_required', [])):
                groups = []
                if page.get('permissions_required', []):
                    groups += groupsWithPermissions(_groups_dict, page['permissions_required']).keys()
                if page.get('one_of_permissions_required', []):
                    groups += groupsWithOneOfPermissions(_groups_dict, page['one_of_permissions_required']).keys()
                for group in groups:
                    if group not in _links_for_groups:
                        _links_for_groups[group] = []
                    url_name = u'{}-{}'.format(group, name)
                    navbarAddLink(url_name, {
                        'title': page['title'],
                        'url': page.get('redirect', None) or '/{}/'.format(name),
                        'get_url': None if not page.get('url_variables', None) else (getURLLambda(name, lambdas)),
                        'show_link_callback': _getPageShowLinkForGroupsLambda(group),
                    }, 'staff')
                    if name in navbar_links['staff']['links']:
                        del(navbar_links['staff']['links'][name])
                    _links_for_groups[group].append(url_name)
            else:
                _links_to_show_first.append(name)

# Add outside permissions links to the navbar dropdowns
_staff_order = _links_to_show_first
for group, group_details in GROUPS:
    links_to_add = []
    for permission, url in group_details.get('outside_permissions', {}).items():
        if url:
            url_name = u'staff-{}-{}'.format(group, tourldash(permission).lower())
            links_to_add.append((url_name, {
                'url_name': url_name,
                'url': url,
                'title': permission,
                'show_link_callback': _getPageShowLinkForGroupsLambda(group),
                'new_tab': True,
            }))
    if links_to_add or _links_for_groups.get(group, []):
        header_name = u'staff-header-{}'.format(group)
        navbarAddLink(header_name, {
            'title': group_details['translation'],
            'image': 'groups/{}'.format(group),
            'is_header': True,
            'show_link_callback': _getPageShowLinkForGroupsLambda(group),
         }, 'staff')
        _staff_order.append(header_name)
        _staff_order += _links_for_groups.get(group, [])
        for url_name, link in links_to_add:
            navbarAddLink(url_name, link, 'staff')
            _staff_order.append(url_name)

# Specify the order of the staff navbar
navbar_links['staff']['order'] = _staff_order

############################################################

urlpatterns = patterns('', *urls)

############################################################
# Re-order navbar

def _getPageShowLinkForListsLambda(link):
    """
    In base template, when the link is a list, this lambda is expected to return the dict of links.
    """
    show_link_callback = link.get('show_link_callback', None)
    if not link['links']:
        return show_link_callback or (lambda c: {})
    if show_link_callback:
        return show_link_callback
    def _show_link_callback(context):
        return OrderedDict([
            (sub_link_name, sub_link)
            for sub_link_name, sub_link in link['links'].items()
            if sub_link.get('show_link_callback', lambda c: True)(context)
        ])
    return _show_link_callback

order = [link_name for link_name in navbar_links.keys() if link_name not in NAVBAR_ORDERING] + NAVBAR_ORDERING

RAW_CONTEXT['navbar_links'] = OrderedDict((key, navbar_links[key]) for key in order if key in navbar_links)

for link_name, link in RAW_CONTEXT['navbar_links'].items():
    if link['is_list']:
        if link['links'] and 'order' in link:
            if 'headers' in link:
                for header_name, header in link['headers']:
                    header['is_header'] = True
                link['links'].update(link['headers'])
            order = [link_name for link_name in link['links'].keys() if link_name not in link['order']] + link['order']
            link['links'] = OrderedDict((key, link['links'][key]) for key in order if key in link['links'])
        link['show_link_callback'] = _getPageShowLinkForListsLambda(link)

############################################################
# Remove profile tabs when some collections are disabled

for collection_name in ['activity', 'badge', 'account']:
    if collection_name not in all_enabled and collection_name in PROFILE_TABS:
        del(PROFILE_TABS[collection_name])

############################################################
# Mark as non-reportable if the report collection is disabled

if 'report' not in all_enabled:
    for collection in collections.values():
        collection.reportable = False

############################################################
# Set data in RAW_CONTEXT

RAW_CONTEXT['all_enabled'] = all_enabled
RAW_CONTEXT['magicollections'] = collections
RAW_CONTEXT['collectible_collections'] = collectible_collections
RAW_CONTEXT['account_model'] = ACCOUNT_MODEL
RAW_CONTEXT['site_name'] = SITE_NAME
RAW_CONTEXT['site_url'] = SITE_URL
RAW_CONTEXT['github_repository'] = GITHUB_REPOSITORY
RAW_CONTEXT['site_description'] = SITE_DESCRIPTION
RAW_CONTEXT['staff_configurations'] = STAFF_CONFIGURATIONS
RAW_CONTEXT['get_started_video'] = GET_STARTED_VIDEO
RAW_CONTEXT['game_name'] = GAME_NAME
RAW_CONTEXT['static_uploaded_files_prefix'] = STATIC_UPLOADED_FILES_PREFIX
RAW_CONTEXT['static_url'] = SITE_STATIC_URL + 'static/'
RAW_CONTEXT['full_static_url'] = u'http:{}'.format(RAW_CONTEXT['static_url']) if 'http' not in RAW_CONTEXT['static_url'] else RAW_CONTEXT['static_url']
RAW_CONTEXT['site_logo'] = RAW_CONTEXT['static_url'] + 'img/' + SITE_LOGO if '//' not in SITE_LOGO else SITE_LOGO
RAW_CONTEXT['full_site_logo'] = u'http:{}'.format(RAW_CONTEXT['site_logo']) if 'http' not in RAW_CONTEXT['site_logo'] else RAW_CONTEXT['site_logo']
RAW_CONTEXT['site_nav_logo'] = SITE_NAV_LOGO
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
RAW_CONTEXT['full_empty_image'] = RAW_CONTEXT['static_url'] + 'img/' + RAW_CONTEXT['empty_image']
RAW_CONTEXT['google_analytics'] = GOOGLE_ANALYTICS
RAW_CONTEXT['static_files_version'] = STATIC_FILES_VERSION
RAW_CONTEXT['preferences_model'] = UserPreferences

if not launched:
    RAW_CONTEXT['launch_date'] = LAUNCH_DATE
