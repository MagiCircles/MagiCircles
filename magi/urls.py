# -*- coding: utf-8 -*-
import string, inspect
from collections import OrderedDict
from django.conf import settings
from django.conf.urls import include, patterns, url
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import string_concat, ugettext_lazy as _
from django.views.generic.base import RedirectView
#from magi import bouncy # unused, only to force load the feedback process
from magi import views_collections, magicollections
from magi import views as magi_views
from magi.settings import (
    RAW_CONTEXT,
    ENABLED_PAGES,
    ENABLED_NAVBAR_LISTS,
    FAVORITE_CHARACTER_TO_URL,
    FAVORITE_CHARACTER_NAME,
    FAVORITE_CHARACTERS_MODEL,
    OTHER_CHARACTERS_MODELS,
    SITE_NAME,
    SITE_NAME_PER_LANGUAGE,
    EMAIL_IMAGE,
    EMAIL_IMAGE_PER_LANGUAGE,
    GAME_NAME,
    GAME_NAME_PER_LANGUAGE,
    SITE_DESCRIPTION,
    SITE_STATIC_URL,
    SITE_URL,
    GITHUB_REPOSITORY,
    SITE_LOGO,
    SITE_NAV_LOGO,
    JAVASCRIPT_TRANSLATED_TERMS,
    STATIC_UPLOADED_FILES_PREFIX,
    COLOR,
    SITE_IMAGE,
    SITE_IMAGE_PER_LANGUAGE,
    TRANSLATION_HELP_URL,
    COMMENTS_ENGINE,
    DISQUS_SHORTNAME,
    MAX_ACTIVITY_HEIGHT,
    HASHTAGS,
    TWITTER_HANDLE,
    EMPTY_IMAGE,
    GOOGLE_ANALYTICS,
    STATIC_FILES_VERSION,
    PROFILE_TABS,
    LAUNCH_DATE,
    PRELAUNCH_ENABLED_PAGES,
    NAVBAR_ORDERING,
    ACCOUNT_MODEL,
    STAFF_CONFIGURATIONS,
    FIRST_COLLECTION,
    GET_STARTED_VIDEO,
    GLOBAL_OUTSIDE_PERMISSIONS,
    GROUPS,
    JAVASCRIPT_COMMONS,
    LANGUAGES_CANT_SPEAK_ENGLISH,
    CORNER_POPUP_IMAGE,
    CORNER_POPUP_IMAGE_OVERFLOW,
    SITE_EMOJIS,
)
from magi.models import UserPreferences
from magi.utils import (
    getGlobalContext,
    getNavbarPrefix,
    pageTitleFromPrefixes,
    h1ToContext,
    redirectWhenNotAuthenticated,
    hasPermissions,
    hasOneOfPermissions,
    tourldash,
    groupsWithPermissions,
    groupsWithOneOfPermissions,
    staticImageURL,
)
from raw import other_sites

############################################################
# Load dynamic module based on SITE

views_module = __import__(settings.SITE + '.views', fromlist=[''])
custom_magicollections_module = __import__(settings.SITE + '.magicollections', fromlist=['']).__dict__

############################################################
# Vatiables

navbar_links = OrderedDict()
now = timezone.now()
launched = LAUNCH_DATE is None or (LAUNCH_DATE is not True and LAUNCH_DATE < now)
collections = OrderedDict()
enabled = {}
all_enabled = []
urls = []
collectible_collections = {}
collections_in_profile_tabs = []
main_collections = []
sub_collections = {}

_verbose_re = '[\w.@+\-_]+'

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
                navbar_links[list_name]['title'] = string.capwords(list_name)
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
    return (lambda context: collection.list_view.has_permissions_to_see_in_navbar(context['request'], context))

def _addToCollections(name, cls): # Class of the collection
    collection = cls()
    collection.list_view = collection.ListView(collection)
    collection.item_view = collection.ItemView(collection)
    collection.add_view = collection.AddView(collection)
    collection.edit_view = collection.EditView(collection)

    if issubclass(cls, magicollections.SubItemCollection):
        for main_collection in (collection.main_collections or [collection.main_collection]):
            if main_collection not in sub_collections:
                sub_collections[main_collection] = {}
            sub_collections[main_collection][collection.name] = collection
    elif issubclass(cls, magicollections.MainItemCollection):
        main_collections.append(collection)

    if collection.list_view.as_profile_tab:
        collections_in_profile_tabs.append(collection.name)

    collection.to_form_class()
    collection.list_view.to_filter_form_class()
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
    return collection

def _addToEnabledCollections(name, cls, is_custom):
    if (name != 'MagiCollection'
        and name != 'MainItemCollection'
        and name != 'SubItemCollection'
        and inspect.isclass(cls)
        and issubclass(cls, magicollections.MagiCollection)
        and not name.startswith('_')):
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

# Link main collections and their sub collections
for collection in main_collections:
    collection.sub_collections = sub_collections.get(collection.name, {})

def _get_navbar_title_lambda(collection):
    return lambda _c: collection.navbar_link_title

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
        urls.append(url(u'^{}[/]*$'.format(collection.plural_name), views_collections.list_view, parameters, name=url_name))
        if collection.list_view.ajax:
            urls.append(url(u'^ajax/{}/$'.format(collection.plural_name), views_collections.list_view, ajax_parameters, name='{}_ajax'.format(url_name)))
        for shortcut_url in collection.list_view.shortcut_urls:
            shortcut_parameters = parameters.copy()
            shortcut_parameters['shortcut_url'] = shortcut_url
            shortcut_ajax_parameters = ajax_parameters.copy()
            shortcut_ajax_parameters['shortcut_url'] = shortcut_url
            urls.append(url(u'^{}[/]*$'.format(shortcut_url), views_collections.list_view, shortcut_parameters, name=url_name))
            if collection.list_view.ajax:
                urls.append(url(u'^ajax/{}/$'.format(shortcut_url), views_collections.list_view, shortcut_ajax_parameters, name='{}_ajax'.format(url_name)))
        if collection.list_view.allow_random and collection.list_view.filter_form:
            urls.append(url(u'^{}/random[/]*$'.format(collection.plural_name), views_collections.random_view, parameters, name=u'{}_random'.format(url_name)))
        if collection.list_view.filter_form and getattr(collection.list_view.filter_form, 'presets', None):
            for preset in collection.list_view.filter_form.get_presets().keys():
                urls.append(url(u'^{}/{}[/]*$'.format(collection.plural_name, preset), views_collections.list_view, parameters, name=url_name))
                if collection.list_view.ajax:
                    urls.append(url(u'^ajax/{}/{}/$'.format(collection.plural_name, preset), views_collections.list_view, ajax_parameters, name='{}_ajax'.format(url_name)))
        if collection.navbar_link:
            link = {
                'url_name': url_name,
                'url': '/{}/'.format(collection.plural_name),
                'title': _get_navbar_title_lambda(collection),
                'icon': collection.icon,
                'image': collection.image,
                'larger_image': collection.larger_image,
                'auth': (True, False) if collection.list_view.authentication_required else (True, True),
                'show_link_callback': getCollectionShowLinkLambda(collection),
                'divider_before': collection.navbar_link_list_divider_before,
            }
            navbarAddLink(url_name, link, collection.navbar_link_list)
            added_links = [link]
            for view, details in collection.list_view.alt_views:
                if not details.get('hide_in_navbar', False):
                    view_link = link.copy()
                    view_link['url_name'] = u'{}_list_{}'.format(collection.name, view)
                    view_link['url'] = u'/{}/?view={}'.format(collection.plural_name, view)
                    view_link['icon'] = view_link['image'] = None
                    view_link['title'] = details.get('navbar_link_title', details['verbose_name'])
                    if 'icon' in details:
                        view_link['icon'] = details['icon']
                    elif 'image' in details:
                        view_link['image'] = details['image']
                    else:
                        view_link['title'] = string_concat(u'↳ ', view_link['title'])
                    navbarAddLink(view_link['url_name'], view_link, collection.navbar_link_list)
                    added_links.append(view_link)
            added_links[-1]['divider_after'] = collection.navbar_link_list_divider_after
            if len(added_links) > 1:
                current_ordering = (
                    navbar_links[collection.navbar_link_list].get('order', [])
                    if collection.navbar_link_list
                    else NAVBAR_ORDERING
                )
                if url_name in current_ordering:
                    new_ordering = []
                    for no in current_ordering:
                        if no == url_name:
                            new_ordering += [l['url_name'] for l in added_links]
                        else:
                            new_ordering.append(no)
                    if collection.navbar_link_list:
                        navbar_links[collection.navbar_link_list]['order'] = new_ordering
                    else:
                        NAVBAR_ORDERING = new_ordering
    if collection.item_view.enabled:
        url_name = '{}_item'.format(collection.name)
        urls.append(url(u'^{}/(?P<pk>\d+)[/]*$'.format(collection.name), views_collections.item_view, parameters, name=url_name))
        urls.append(url(u'^{}/(?P<pk>\d+)[/]*$'.format(collection.plural_name), views_collections.item_view, parameters, name=url_name))
        urls.append(url(u'^{}/(?P<pk>\d+)/{}[/]*$'.format(collection.name, _verbose_re), views_collections.item_view, parameters, name=url_name))
        urls.append(url(u'^{}/(?P<pk>\d+)/{}[/]*$'.format(collection.plural_name, _verbose_re), views_collections.item_view, parameters, name=url_name))
        if collection.item_view.ajax:
            urls.append(url(u'^ajax/{}/(?P<pk>\d+)/$'.format(collection.name), views_collections.item_view, ajax_parameters, name='{}_ajax'.format(url_name)))
        if collection.item_view.reverse_url:
            urls.append(url(u'^{}/(?P<reverse>{})[/]*$'.format(collection.name, _verbose_re), views_collections.item_view, parameters, name=url_name))
            urls.append(url(u'^{}/(?P<reverse>{})[/]*$'.format(collection.plural_name, _verbose_re), views_collections.item_view, parameters, name=url_name))
        for shortcut_url in collection.item_view.shortcut_urls:
            if isinstance(shortcut_url, tuple):
                shortcut_url, pk = shortcut_url
                shortcut_parameters = parameters.copy()
                shortcut_parameters['shortcut_url'] = shortcut_url
                shortcut_parameters['pk'] = pk
                urls.append(url(u'^{}[/]*$'.format(shortcut_url), views_collections.item_view, shortcut_parameters, name=url_name))
            else:
                urls.append(url(u'^{}/(?P<pk>\d+)[/]*$'.format(shortcut_url), views_collections.item_view, parameters, name=url_name))
                urls.append(url(u'^{}/(?P<pk>\d+)/{}[/]*$'.format(shortcut_url, _verbose_re), views_collections.item_view, parameters, name=url_name))
    if collection.add_view.enabled:
        url_name = '{}_add'.format(collection.name)
        if collection.types:
            urls.append(url(u'^{}/add/(?P<type>{})[/]*$'.format(collection.name, _verbose_re), views_collections.add_view, parameters, name=url_name))
            urls.append(url(u'^{}/add/(?P<type>{})[/]*$'.format(collection.plural_name, _verbose_re), views_collections.add_view, parameters, name=url_name))
            if collection.add_view.ajax:
                urls.append(url(u'^ajax/{}/add/(?P<type>{})[/]*$'.format(collection.name, _verbose_re), views_collections.add_view, ajax_parameters, name='{}_ajax'.format(url_name)))
                urls.append(url(u'^ajax/{}/add/(?P<type>{})[/]*$'.format(collection.plural_name, _verbose_re), views_collections.add_view, ajax_parameters, name='{}_ajax'.format(url_name)))
            for shortcut_url, _type in collection.add_view.shortcut_urls:
                shortcut_parameters = parameters.copy()
                shortcut_parameters['shortcut_url'] = shortcut_url
                shortcut_parameters['type'] = _type
                urls.append(url(u'^{}[/]*$'.format(shortcut_url), views_collections.add_view, shortcut_parameters, name=url_name))
        else:
            urls.append(url(u'^{}/add[/]*$'.format(collection.name), views_collections.add_view, parameters, name=url_name))
            urls.append(url(u'^{}/add[/]*$'.format(collection.plural_name), views_collections.add_view, parameters, name=url_name))
            if collection.AddView.ajax:
                urls.append(url(u'^ajax/{}/add[/]*$'.format(collection.plural_name), views_collections.add_view, ajax_parameters, name='{}_ajax'.format(url_name)))
            for shortcut_url in collection.add_view.shortcut_urls:
                shortcut_parameters = parameters.copy()
                shortcut_parameters['shortcut_url'] = shortcut_url
                urls.append(url(u'^{}[/]*$'.format(shortcut_url), views_collections.add_view, shortcut_parameters, name=url_name))
    if collection.edit_view.enabled:
        url_name = '{}_edit'.format(collection.name)
        urls.append(url(u'^{}/edit/(?P<pk>\d+|unique)/$'.format(collection.name), views_collections.edit_view, parameters, name=url_name))
        urls.append(url(u'^{}/edit/(?P<pk>\d+|unique)/$'.format(collection.plural_name), views_collections.edit_view, parameters, name=url_name))
        if collection.edit_view.ajax:
            urls.append(url(u'^ajax/{}/edit/(?P<pk>\d+|unique)/$'.format(collection.name), views_collections.edit_view, ajax_parameters, name='{}_ajax'.format(url_name)))
            urls.append(url(u'^ajax/{}/edit/(?P<pk>\d+|unique)/$'.format(collection.plural_name), views_collections.edit_view, ajax_parameters, name='{}_ajax'.format(url_name)))
        for shortcut_url, pk in collection.edit_view.shortcut_urls:
            shortcut_parameters = parameters.copy()
            shortcut_parameters['shortcut_url'] = shortcut_url
            shortcut_parameters['pk'] = pk
            urls.append(url(u'^{}[/]*$'.format(shortcut_url), views_collections.item_view, shortcut_parameters, name=url_name))

############################################################
# URLs for pages

def getPageShowLinkLambda(page):
    def _showLink(context):
        permissions_required = page.get('permissions_required', [])
        one_of_permissions_required = page.get('one_of_permissions_required', [])
        check_permissions = page.get('check_permissions', None)
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
            or (check_permissions
                and not check_permissions(context))
        )
    return _showLink

def page_view(name, page):
    function_name = page.get('function_name', name)
    try:
        function = (
            getattr(views_module, function_name)
            if page.get('custom', True)
            else getattr(magi_views, function_name)
        )
    except AttributeError:
        function = None
    boilerplate = page.get('boilerplate', True)
    if not boilerplate and not function:
        raise NotImplementedError(u'Function of enabled page {} not found.'.format(name))

    def _view(request, *args, **kwargs):
        # Check permissions
        permissions_context = { 'current_url': request.get_full_path() }
        if page.get('logout_required', False) and request.user.is_authenticated():
            raise PermissionDenied()
        if page.get('authentication_required'):
            redirectWhenNotAuthenticated(request, permissions_context, next_title=page.get('title', ''))
        if page.get('staff_required', False):
            redirectWhenNotAuthenticated(request, permissions_context, next_title=page.get('title', ''))
            if not request.user.is_staff and not request.user.is_superuser:
                raise PermissionDenied()
        if page.get('prelaunch_staff_required', False):
            redirectWhenNotAuthenticated(request, permissions_context, next_title=page.get('title', ''))
            if not request.user.hasPermission('access_site_before_launch'):
                raise PermissionDenied()
        if page.get('permissions_required', []):
            redirectWhenNotAuthenticated(request, permissions_context, next_title=page.get('title', ''))
            if not hasPermissions(request.user, page['permissions_required']):
                raise PermissionDenied()
        if page.get('one_of_permissions_required', []):
            redirectWhenNotAuthenticated(request, permissions_context, next_title=page.get('title', ''))
            if not hasOneOfPermissions(request.user, page['one_of_permissions_required']):
                raise PermissionDenied()

        if boilerplate:
            # Context
            context = getGlobalContext(request=request)
            context['extends'] = 'base.html' if not context['ajax'] else 'ajax.html'
            context['disqus_identifier'] = context['current']
            # Settings from page
            context['show_small_title'] = page.get('show_small_title', True)
            context['show_title'] = page.get('show_title', False)
            context['share_image'] = staticImageURL(page.get('share_image', None))
            context['page_description'] = page.get('page_description', None)
            context['comments_enabled'] = page.get('comments_enabled', False)
            context['template'] = page.get('template', name)
            # Set title and prefixes
            context['title_prefixes'] = []
            if 'navbar_link_list' in page:
                getNavbarPrefix(page['navbar_link_list'], request, context, append_to=context['title_prefixes'])
            default_page_title = page.get('title', None)
            if callable(default_page_title):
                default_page_title = default_page_title(context)
            h1 = {
                'title': default_page_title,
                'icon': page.get('icon', None),
                'image': page.get('image', None),
            }
            h1ToContext(h1, context)
            context['page_title'] = pageTitleFromPrefixes(context['title_prefixes'], default_page_title)
            # Call function
            if function:
                result = function(request, context, *args, **kwargs)
            # Render with full template
            if page.get('full_template', False):
                return render(request, u'pages/{}.html'.format(
                    name if page['full_template'] == True else page['full_template']), context)
            # Render with boilerplate
            if page.get('as_json', False):
                if result is None:
                    return HttpResponse('')
                return JsonResponse(result)
            elif page.get('as_form', False):
                return render(request, 'form.html', context)
            elif page.get('as_sidebar', False):
                context['sidebar_show_title'] = True
                context['sidebar_template'] = 'include/{}.html'.format(
                    page.get('sidebar_template', '{}_sidebar'.format(name)))
                context['template'] = 'pages/{}.html'.format(context['template'])
                return render(request, 'sidebar.html', context)
            return render(request, 'pages/boilerplate.html', context)
        else:
            # Render expected to be called by function
            return function(request, *args, **kwargs)
    return _view

for (name, pages) in ENABLED_PAGES.items():
    if not isinstance(pages, list):
        pages = [pages]
    for page in pages:
        if not launched:
            if name not in PRELAUNCH_ENABLED_PAGES:
                page['permissions_required'] = page.get('permissions_required', []) + ['access_site_before_launch']
        if 'title' not in page:
            page['title'] = string.capwords(name)
        if not page.get('enabled', True):
            continue
        if name not in all_enabled:
            all_enabled.append(name)
        ajax = page.get('ajax', False)
        redirect = page.get('redirect', None)
        if redirect:
            urls.append(url(u'^{}{}{}[/]*$'.format(
                'ajax/' if ajax else '', name, '/' + url_variables if url_variables else '',
            ), RedirectView.as_view(url=redirect, permanent=True)))
        else:
            if name == 'index':
                urls.append(url(u'^$', page_view(name, page), name=name))
            else:
                url_variables = '/'.join(['(?P<{}>{})'.format(v[0], v[1]) for v in page.get('url_variables', [])])
                urls.append(url(u'^{}{}{}[/]*$'.format('ajax/' if ajax else '', name, '/' + url_variables if url_variables else ''),
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
                    'larger_image': page.get('larger_image', False),
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

for permission, details in GLOBAL_OUTSIDE_PERMISSIONS.items():
    if not isinstance(details, dict):
        details = { 'url': url }
    if details.get('url', None):
        url_name = u'staff-global-{}'.format(tourldash(permission).lower())
        navbarAddLink(url_name, {
            'url_name': url_name,
            'url': details['url'],
            'image': details.get('image', None),
            'icon': details.get('icon', None),
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
                    'icon': collection.icon,
                    'image': collection.image,
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
                        'icon': page.get('icon', None),
                        'image': page.get('image', None),
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
    for permission, details in group_details.get('outside_permissions', {}).items():
        if not isinstance(details, dict):
            details = { 'url': url }
        if details.get('url', None):
            url_name = u'staff-{}-{}'.format(group, tourldash(permission).lower())
            links_to_add.append((url_name, {
                'url_name': url_name,
                'url': details['url'],
                'image': details.get('image', None),
                'icon': details.get('icon', None),
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
        if 'url' not in link:
            link['url'] = u'/{}/'.format(link_name)
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
RAW_CONTEXT['collections_in_profile_tabs'] = collections_in_profile_tabs
RAW_CONTEXT['main_collections'] = [ _c.name for _c in main_collections ]
RAW_CONTEXT['account_model'] = ACCOUNT_MODEL
RAW_CONTEXT['site_name'] = SITE_NAME
RAW_CONTEXT['site_name_per_language'] = SITE_NAME_PER_LANGUAGE
RAW_CONTEXT['site_url'] = SITE_URL
RAW_CONTEXT['github_repository'] = GITHUB_REPOSITORY
RAW_CONTEXT['site_description'] = SITE_DESCRIPTION
RAW_CONTEXT['staff_configurations'] = STAFF_CONFIGURATIONS
RAW_CONTEXT['get_started_video'] = GET_STARTED_VIDEO
RAW_CONTEXT['game_name'] = GAME_NAME
RAW_CONTEXT['game_name_per_language'] = GAME_NAME_PER_LANGUAGE
RAW_CONTEXT['static_uploaded_files_prefix'] = STATIC_UPLOADED_FILES_PREFIX
RAW_CONTEXT['static_url'] = SITE_STATIC_URL + 'static/'
RAW_CONTEXT['static_files_version'] = STATIC_FILES_VERSION
RAW_CONTEXT['empty_image'] = EMPTY_IMAGE
RAW_CONTEXT['full_static_url'] = u'http{}:{}'.format('' if settings.DEBUG else 's', RAW_CONTEXT['static_url']) if 'http' not in RAW_CONTEXT['static_url'] else RAW_CONTEXT['static_url']
RAW_CONTEXT['site_logo'] = staticImageURL(SITE_LOGO)
RAW_CONTEXT['full_site_logo'] = u'http{}:{}'.format('' if settings.DEBUG else 's',RAW_CONTEXT['site_logo']) if 'http' not in RAW_CONTEXT['site_logo'] else RAW_CONTEXT['site_logo']
RAW_CONTEXT['site_nav_logo'] = SITE_NAV_LOGO
RAW_CONTEXT['comments_engine'] = COMMENTS_ENGINE
if RAW_CONTEXT['comments_engine'] == 'disqus':
    RAW_CONTEXT['disqus_shortname'] = DISQUS_SHORTNAME
RAW_CONTEXT['max_activity_height'] = MAX_ACTIVITY_HEIGHT
RAW_CONTEXT['javascript_translated_terms'] = JAVASCRIPT_TRANSLATED_TERMS
RAW_CONTEXT['javascript_commons'] = JAVASCRIPT_COMMONS
RAW_CONTEXT['site_color'] = COLOR
RAW_CONTEXT['site_image'] = staticImageURL(SITE_IMAGE)
RAW_CONTEXT['site_image_per_language'] = { _l: staticImageURL(_url) for _l, _url in SITE_IMAGE_PER_LANGUAGE.items() }
RAW_CONTEXT['full_site_image'] = u'http{}:{}'.format('' if settings.DEBUG else 's',RAW_CONTEXT['site_image']) if 'http' not in RAW_CONTEXT['site_image'] else RAW_CONTEXT['site_image']
RAW_CONTEXT['full_site_image_per_language'] = { _l: (u'http:{}'.format(_url) if 'http' not in _url else _url) for _l, _url in RAW_CONTEXT['site_image_per_language'].items() }
RAW_CONTEXT['email_image'] = staticImageURL(EMAIL_IMAGE if EMAIL_IMAGE else SITE_IMAGE)
RAW_CONTEXT['email_image_per_language'] = { _l: staticImageURL(_url) for _l, _url in EMAIL_IMAGE_PER_LANGUAGE.items() }
RAW_CONTEXT['full_email_image'] = u'http{}:{}'.format('' if settings.DEBUG else 's',RAW_CONTEXT['email_image']) if 'http' not in RAW_CONTEXT['email_image'] else RAW_CONTEXT['email_image']
RAW_CONTEXT['full_email_image_per_language'] = { _l: (u'http:{}'.format(_url) if 'http' not in _url else _url) for _l, _url in RAW_CONTEXT['email_image_per_language'].items() }
RAW_CONTEXT['translation_help_url'] = TRANSLATION_HELP_URL
RAW_CONTEXT['hashtags'] = HASHTAGS
RAW_CONTEXT['twitter_handle'] = TWITTER_HANDLE
RAW_CONTEXT['full_empty_image'] = staticImageURL(RAW_CONTEXT['empty_image'])
RAW_CONTEXT['google_analytics'] = GOOGLE_ANALYTICS
RAW_CONTEXT['preferences_model'] = UserPreferences
RAW_CONTEXT['languages_cant_speak_english'] = LANGUAGES_CANT_SPEAK_ENGLISH
RAW_CONTEXT['other_sites'] = [s for s in other_sites if s['name'] != SITE_NAME]
RAW_CONTEXT['corner_popup_image'] = staticImageURL(CORNER_POPUP_IMAGE)
RAW_CONTEXT['corner_popup_image_overflow'] = CORNER_POPUP_IMAGE_OVERFLOW
RAW_CONTEXT['site_emojis'] = SITE_EMOJIS
RAW_CONTEXT['favorite_character_to_url'] = FAVORITE_CHARACTER_TO_URL
RAW_CONTEXT['favorite_character_name'] = FAVORITE_CHARACTER_NAME
RAW_CONTEXT['favorite_characters_model'] = FAVORITE_CHARACTERS_MODEL
RAW_CONTEXT['other_characters_models'] = OTHER_CHARACTERS_MODELS

if not launched:
    RAW_CONTEXT['launch_date'] = LAUNCH_DATE
