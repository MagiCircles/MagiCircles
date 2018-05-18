from __future__ import division
import math
import string
from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _, string_concat
from django.shortcuts import render
from magi.middleware.httpredirect import HttpRedirectException
from django.shortcuts import render, redirect
from django.http import Http404
from django.core.exceptions import PermissionDenied

from magi.utils import getGlobalContext, cuteFormFieldsForContext, get_one_object_or_404
from magi.forms import ConfirmDelete, filter_ids
from magi.settings import SITE_IMAGE

############################################################
# Internal utils

def _get_filters(request_get, extra_filters={}):
    filters = request_get.copy()
    filters.update(extra_filters)
    return filters

def _get_share_image(context, collection_view, item=None):
    share_image = collection_view.share_image(context, item)
    if share_image is not None:
        if '//' not in share_image:
            share_image = u'{}img/{}'.format(context['full_static_url'], share_image)
        if 'http' not in share_image:
            share_image = u'http:{}'.format(share_image)
    return share_image

def _modification_view(context, name, view):
    context['list_url'] = '/{}/'.format(view.collection.plural_name)
    context['title'] = view.collection.title
    context['name'] = name
    context['plural_name'] = view.collection.plural_name
    context['plural_title'] = view.collection.plural_title

    context['multipart'] = view.multipart
    context['js_files'] = view.js_files
    context['otherbuttons_template'] = view.otherbuttons_template
    context['back_to_list_button'] = view.back_to_list_button
    context['after_template'] = view.after_template
    return context

def _modification_views_page_titles(action_sentence, context, after_title):
    context['page_title'] = u'{action_sentence}{after_title}'.format(
        action_sentence=action_sentence,
        after_title=u': {}'.format(after_title) if after_title else '',
    )

def _type(a): return type(a)

############################################################
# Item view

def item_view(request, name, collection, pk=None, reverse=None, ajax=False, item=None, extra_filters={}, shortcut_url=None, **kwargs):
    """
    Either pk or reverse required.
    """
    context = collection.item_view.get_global_context(request)
    collection.item_view.check_permissions(request, context)
    queryset = collection.item_view.get_queryset(collection.queryset, _get_filters(request.GET, extra_filters), request)
    if not pk and reverse:
        options = collection.item_view.reverse_url(reverse)
    else:
        options = collection.item_view.get_item(request, pk)
    context['item'] = get_one_object_or_404(queryset, **options) if not item else item
    collection.item_view.check_owner_permissions(request, context, context['item'])

    if request.user.is_authenticated() and collection.blockable:
        # Blocked
        if context['item'].owner_id in request.user.preferences.cached_blocked_ids:
            if ajax:
                try:
                    username = context['item'].owner.username
                except AttributeError:
                    username = _('this user')
                context['item'].blocked_message = _(u'You blocked {username}.').format(username=username)
                context['item'].unblock_button = _(u'Unblock {username}').format(username=username)
                return render(request, 'items/default_blocked_template_in_list.html', context)
            raise HttpRedirectException(u'/block/{id}/?next={next_url}'.format(
                id=context['item'].owner_id,
                next_url=context['current_url'],
            ))
        # Blocked by
        elif context['item'].owner_id in request.user.preferences.cached_blocked_by_ids:
            raise PermissionDenied()

    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url
    context['ajax'] = ajax
    context['name'] = name
    context['page_title'] = u'{item} - {title}'.format(title=collection.title, item=context['item'])
    context['js_files'] = collection.item_view.js_files
    context['reportable'] = collection.reportable
    context['share_image'] = _get_share_image(context, collection.item_view, item=context['item'])
    context['comments_enabled'] = collection.item_view.comments_enabled
    context['share_enabled'] = collection.item_view.share_enabled
    context['item_padding'] = collection.item_view.item_padding
    context['item_template'] = collection.item_view.template
    context['full_width'] = collection.item_view.full_width
    context['ajax_callback'] = collection.item_view.ajax_callback
    context['collection'] = collection
    if context['item_template'] == 'default':
        context['top_illustration'] = collection.item_view.top_illustration
        context['item_fields'] = collection.item_view.to_fields(context['item'])

    # Ajax items reloader
    if not ajax and collection.item_view.auto_reloader and collection.item_view.ajax:
        context['ajax_reload_url'] = context['item'].ajax_item_url
        context['reload_urls_start_with'] = [u'/{}/edit/'.format(collection.plural_name)];
        if collection.collectible_collections:
            context['reload_urls_start_with'] += [cc.get_add_url() for cc in collection.collectible_collections.values()]

    context['include_below_item'] = False
    context['show_item_buttons'] = collection.item_view.show_item_buttons
    context['item'].request = request
    context['item'].show_item_buttons_justified = collection.item_view.show_item_buttons_justified
    context['item'].show_item_buttons_as_icons = collection.item_view.show_item_buttons_as_icons
    context['item'].show_item_buttons_in_one_line = collection.item_view.show_item_buttons_in_one_line
    context['item'].buttons_to_show = collection.item_view.buttons_per_item(request, context, context['item'])
    if collection.item_view.show_item_buttons and [True for b in context['item'].buttons_to_show.values() if b['show'] and b['has_permissions']]:
        context['include_below_item'] = True

    collection.item_view.extra_context(context)
    if ajax:
        context['include_template'] = 'items/{}'.format(context['item_template'])
        return render(request, 'ajax.html', context)
    return render(request, 'collections/item_view.html', context)

############################################################
# List view

def list_view(request, name, collection, ajax=False, extra_filters={}, shortcut_url=None, **kwargs):
    """
    View function for any page that lists data, such as cards. Handles pagination and context variables.
    name: The string that corresponds to the view (for instance 'cards' for the '/cards/' view)
    """
    context = collection.list_view.get_global_context(request)
    collection.list_view.check_permissions(request, context)
    context['plural_name'] = collection.plural_name
    page = 0
    page_size = collection.list_view.page_size
    if 'page_size' in request.GET:
        try: page_size = int(request.GET['page_size'])
        except ValueError: pass
        if page_size > 500: page_size = 500
    filters = _get_filters(request.GET, extra_filters)
    queryset = collection.list_view.get_queryset(collection.queryset, filters, request)

    if 'ordering' in request.GET and request.GET['ordering']:
        reverse = ('reverse_order' in request.GET and request.GET['reverse_order']) or not request.GET or len(request.GET) == 1
        prefix = '-' if reverse else ''
        ordering = [prefix + ordering for ordering in request.GET['ordering'].split(',')]
        if (collection.list_view.show_relevant_fields_on_ordering
            and request.GET['ordering'] != ','.join(collection.list_view.plain_default_ordering_list)):
            context['show_relevant_fields_on_ordering'] = True
            context['plain_ordering'] = [o[1:] if o.startswith('-') else o for o in ordering]
    else:
        ordering = collection.list_view.default_ordering.split(',')
    queryset = queryset.order_by(*ordering)

    if collection.list_view.filter_form:
        if len(request.GET) > 1 or (len(request.GET) == 1 and 'page' not in request.GET):
            context['filter_form'] = collection.list_view.filter_form(filters, request=request, ajax=ajax, collection=collection)
            if hasattr(context['filter_form'], 'filter_queryset'):
                queryset = context['filter_form'].filter_queryset(queryset, filters, request)
            else:
                queryset = filter_ids(queryset, request)
        else:
            context['filter_form'] = collection.list_view.filter_form(request=request, ajax=ajax, collection=collection)
    else:
        queryset = filter_ids(queryset, request)

    if collection.list_view.distinct:
        queryset = queryset.distinct()
    context['total_results'] = queryset.count()
    context['total_results_sentence'] = _('1 {object} matches your search:').format(object=collection.title) if context['total_results'] == 1 else _('{total} {objects} match your search:').format(total=context['total_results'], objects=collection.plural_title)

    if 'page' in request.GET and request.GET['page']:
        page = int(request.GET['page']) - 1
        if page < 0:
            page = 0
    queryset = queryset[(page * page_size):((page * page_size) + page_size)]

    if 'filter_form' in context:
        cuteFormFieldsForContext(
            collection.list_view.filter_cuteform,
            context, form=context['filter_form'],
            prefix='#sidebar-wrapper ',
            ajax=ajax,
        )

    if 'ajax_modal_only' in request.GET:
        # Will display a link to see the other results instead of the pagination button
        context['ajax_modal_only'] = True
        context['filters_string'] = '&'.join(['{}={}'.format(k, v) for k, v in filters.items() if k != 'ajax_modal_only'])
        context['remaining'] = context['total_results'] - page_size

    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url

    # Ajax items reloader
    if not ajax and collection.list_view.auto_reloader and collection.list_view.ajax:
        context['ajax_reload_url'] = collection.get_list_url(ajax=True)
        context['reload_urls_start_with'] = [u'/{}/edit/'.format(collection.plural_name)];
        if collection.collectible_collections:
            context['reload_urls_start_with'] += [cc.get_add_url() for cc in collection.collectible_collections.values()]

    # Alt views
    context['view'] = None
    context['alt_view'] = None
    alt_views = dict(collection.list_view.alt_views)
    if 'view' in request.GET and request.GET['view'] in alt_views:
        context['view'] = request.GET['view']
        context['alt_view'] = alt_views[context['view']]
    context['ordering'] = ordering
    context['page_title'] = _(u'{things} list').format(things=collection.plural_title)
    context['total_pages'] = int(math.ceil(context['total_results'] / page_size))
    context['items'] = queryset
    context['page'] = page + 1
    context['is_last_page'] = context['page'] == context['total_pages']
    context['page_size'] = page_size
    context['show_no_result'] = not ajax
    context['show_search_results'] = bool(request.GET)
    context['show_owner'] = 'show_owner' in request.GET
    context['get_started'] = 'get_started' in request.GET
    context['name'] = name
    context['title'] = collection.title
    context['reportable'] = collection.reportable
    context['hide_sidebar'] = collection.list_view.hide_sidebar
    context['before_template'] = collection.list_view.before_template
    context['no_result_template'] = collection.list_view.no_result_template
    context['after_template'] = collection.list_view.after_template
    context['item_template'] = collection.list_view.item_template
    context['item_blocked_template'] = collection.list_view.item_blocked_template
    if context['alt_view'] and 'template' in context['alt_view']:
        context['item_template'] = context['alt_view']['template']
    context['item_padding'] = collection.list_view.item_padding
    context['show_title'] = collection.list_view.show_title
    context['plural_title'] = collection.plural_title
    context['ajax_pagination'] = collection.list_view.ajax
    context['ajax_pagination_callback'] = collection.list_view.ajax_pagination_callback
    context['ajax_callback'] = collection.list_view.ajax_callback
    context['ajax'] = ajax
    context['js_files'] = collection.list_view.js_files
    context['share_image'] = _get_share_image(context, collection.list_view)
    context['full_width'] = collection.list_view.full_width
    if context['alt_view'] and 'full_width' in context['alt_view']:
        context['full_width'] = context['alt_view']['full_width']
    context['display_style'] = collection.list_view.display_style
    if context['alt_view'] and 'display_style' in context['alt_view']:
        context['display_style'] = context['alt_view']['display_style']
    context['display_style_table_classes'] = collection.list_view.display_style_table_classes
    context['display_style_table_fields'] = collection.list_view.display_style_table_fields
    if context['alt_view'] and 'display_style_table_fields' in context['alt_view']:
        context['display_style_table_fields'] = context['alt_view']['display_style_table_fields']
    context['col_break'] = collection.list_view.col_break
    context['per_line'] = int(request.GET['max_per_line']) if 'max_per_line' in request.GET and int(request.GET['max_per_line']) < collection.list_view.per_line else collection.list_view.per_line
    if context['alt_view'] and 'per_line' in context['alt_view']:
        context['per_line'] = context['alt_view']['per_line']
    context['col_size'] = int(math.ceil(12 / context['per_line']))
    context['ajax_item_popover'] = collection.list_view.ajax_item_popover
    context['item_view_enabled'] = collection.item_view.enabled
    context['ajax_item_view_enabled'] = context['item_view_enabled'] and collection.item_view.ajax and not context['ajax_item_popover']
    context['include_below_item'] = False # May be set to true below
    context['collection'] = collection

    if context['display_style'] == 'table':
        context['table_fields_headers'] = collection.list_view.table_fields_headers(context['display_style_table_fields'], view=context['view'])
        context['table_fields_headers_sections'] = collection.list_view.table_fields_headers_sections(view=context['view'])

    if not ajax:
        context['top_buttons'] = collection.list_view.top_buttons(request, context)
        context['top_buttons_total'] = len([True for b in context['top_buttons'].values() if b['show'] and b['has_permissions']])
        if context['top_buttons_total']:
            context['top_buttons_col_size'] = int(math.ceil(12 / context['top_buttons_total']))

    context['show_item_buttons'] = collection.list_view.show_item_buttons
    for i, item in enumerate(queryset):
        item.request = request
        if collection.list_view.foreach_items:
            collection.list_view.foreach_items(i, item, context)
        if context.get('show_relevant_fields_on_ordering', False):
            context['include_below_item'] = True
            item.relevant_fields_to_show = collection.list_view.ordering_fields(item, only_fields=context['plain_ordering'])
        if context['display_style'] == 'table':
            item.table_fields = collection.list_view.table_fields(item, only_fields=context['display_style_table_fields'], force_all_fields=True)
        item.buttons_to_show = collection.list_view.buttons_per_item(request, context, item)
        item.show_item_buttons_justified = collection.list_view.show_item_buttons_justified
        item.show_item_buttons_as_icons = collection.list_view.show_item_buttons_as_icons
        item.show_item_buttons_in_one_line = collection.list_view.show_item_buttons_in_one_line
        if collection.list_view.show_item_buttons and [True for b in item.buttons_to_show.values() if b['show'] and b['has_permissions']]:
            context['include_below_item'] = True
        if request.user.is_authenticated() and collection.blockable:
            if item.owner_id in request.user.preferences.cached_blocked_ids:
                item.blocked = True
                try:
                    username = item.owner.username
                except AttributeError:
                    username = _('this user')
                item.blocked_message = _(u'You blocked {username}.').format(username=username)
                item.unblock_button = _(u'Unblock {username}').format(username=username)
            elif item.owner_id in request.user.preferences.cached_blocked_by_ids:
                item.blocked_by_owner = True

    collection.list_view.extra_context(context)

    if ajax:
        return render(request, 'collections/list_page.html', context)
    return render(request, 'collections/list_view.html', context)

############################################################
# Add view

def add_view(request, name, collection, type=None, ajax=False, shortcut_url=None, **kwargs):
    context = collection.add_view.get_global_context(request)
    collection.add_view.check_permissions(request, context)
    context = _modification_view(context, name, collection.add_view)
    with_types = False
    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url
    context['next'] = request.GET.get('next', None)
    context['next_title'] = request.GET.get('next_title', None)
    context['type'] = None
    after_title = None
    if type is not None and collection.types:
        if type not in collection.types:
            raise Http404
        with_types = True
        context['type'] = type
        collection.add_view.check_type_permissions(request, context, type=type)
        formClass = collection.types[type].get('form_class', collection.add_view.form_class)
        context['imagetitle'] = collection.types[type].get('image', collection.image)
        context['icontitle'] = collection.types[type].get('icon', collection.icon)
        after_title = collection.types[type].get('title', type)
    else:
        formClass = collection.add_view.form_class
        context['imagetitle'] = collection.image
        context['icontitle'] = collection.icon
    if str(_type(formClass)) == '<type \'instancemethod\'>':
        formClass = formClass(request, context)
    if request.method == 'GET':
        form = formClass(request=request, ajax=ajax, collection=collection) if not with_types else formClass(request=request, ajax=ajax, collection=collection, type=type)
    elif request.method == 'POST':
        form = formClass(request.POST, request.FILES, request=request, ajax=ajax, collection=collection) if not with_types else formClass(request.POST, request.FILES, request=request, ajax=ajax, collection=collection, type=type)
        if form.is_valid():
            instance = form.save(commit=False)
            instance = collection.add_view.before_save(request, instance, type=type)
            instance.save()
            if collection.add_view.savem2m:
                form.save_m2m()
            instance = collection.add_view.after_save(request, instance, type=type)
            if collection.add_view.allow_next and context['next']:
                raise HttpRedirectException(context['next'])
            redirectURL = collection.add_view.redirect_after_add(request, instance, ajax)
            if context['next']:
                redirectURL += '{}next={}&next_title={}'.format(
                    '&' if '?' in redirectURL else '?',
                    context['next'],
                    context['next_title'] if context['next_title'] else '',
                )
            raise HttpRedirectException(redirectURL)
    cuteFormFieldsForContext(
        collection.add_view.filter_cuteform,
        context, form=form,
        prefix=u'[data-form-name="add_{}"] '.format(collection.name),
        ajax=ajax,
    )
    _modification_views_page_titles(collection.add_sentence, context, after_title)
    context['action_sentence'] = collection.add_sentence # Used in page title
    form.action_sentence = collection.add_sentence # Genericity when we have multiple forms
    context['share_image'] = _get_share_image(context, collection.add_view)
    context['forms'] = { u'add_{}'.format(collection.name): form }
    context['ajax_callback'] = collection.add_view.ajax_callback
    context['collection'] = collection
    if collection.add_view.alert_duplicate:
        context['alert_message'] = _('Make sure the {thing} you\'re about to add doesn\'t already exist.').format(thing=_(collection.title.lower()))
        context['alert_button_link'] = context['list_url']
        context['alert_button_string'] = _(collection.plural_title)

    collection.add_view.extra_context(context)
    if ajax:
        context['include_template'] = 'collections/modification_view'
        context['extends'] = 'ajax.html'
        context['ajax'] = True
    return render(request, 'collections/modification_view.html', context)

############################################################
# Edit view

def edit_view(request, name, collection, pk, extra_filters={}, ajax=False, shortcut_url=None, **kwargs):
    context = collection.edit_view.get_global_context(request)
    context['is_translate'] = 'translate' in request.GET
    if context['is_translate']:
        collection.edit_view.check_translate_permissions(request, context)
    else:
        collection.edit_view.check_permissions(request, context)
    context = _modification_view(context, name, collection.edit_view)
    queryset = collection.edit_view.get_queryset(collection.queryset, _get_filters(request.GET, extra_filters), request)
    instance = get_one_object_or_404(queryset, **collection.edit_view.get_item(request, pk))
    context['type'] = None
    collection.edit_view.check_owner_permissions(request, context, instance)
    if context['is_translate']:
        formClass = collection.edit_view.translate_form_class
        context['icontitle'] = 'world'
    elif collection.types:
        type = instance.type
        context['type'] = type
        collection.edit_view.check_type_permissions(request, context, type=type, item=instance)
        formClass = collection.types[type].get('form_class', collection.edit_view.form_class)
        context['imagetitle'] = collection.types[type].get('image', collection.image)
        context['icontitle'] = collection.types[type].get('icon', collection.icon)
    else:
        formClass = collection.edit_view.form_class
        context['imagetitle'] = collection.image
        context['icontitle'] = collection.icon
    if str(_type(formClass)) == '<type \'instancemethod\'>':
        formClass = formClass(request, context)
    allowDelete = not context['is_translate'] and collection.edit_view.allow_delete and 'disable_delete' not in request.GET
    form = formClass(instance=instance, request=request, ajax=ajax, collection=collection)
    if allowDelete:
        formDelete = ConfirmDelete(initial={
            'thing_to_delete': instance.pk,
        })
    form = formClass(instance=instance, request=request, ajax=ajax, collection=collection)
    if allowDelete and request.method == 'POST' and u'delete_{}'.format(collection.name) in request.POST:
        formDelete = ConfirmDelete(request.POST)
        if formDelete.is_valid():
            collection.edit_view.before_delete(request, instance, ajax)
            redirectURL = collection.edit_view.redirect_after_delete(request, instance, ajax)
            instance.delete()
            raise HttpRedirectException(redirectURL)
    elif request.method == 'POST':
        form = formClass(request.POST, request.FILES, instance=instance, request=request, ajax=ajax, collection=collection)
        if form.is_valid():
            instance = form.save(commit=False)
            instance = collection.edit_view.before_save(request, instance)
            instance.save()
            if collection.edit_view.savem2m and not context['is_translate']:
                form.save_m2m()
            instance = collection.edit_view.after_save(request, instance)
            redirectURL = collection.edit_view.redirect_after_edit(request, instance, ajax)
            raise HttpRedirectException(redirectURL)
    cuteFormFieldsForContext(
        collection.edit_view.filter_cuteform,
        context, form=form,
        prefix=u'[data-form-name="edit_{}"] '.format(collection.name),
        ajax=ajax,
    )
    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url
    context['forms'] = OrderedDict()
    context['action_sentence'] = instance.edit_sentence # Used as the page title
    form.action_sentence = instance.edit_sentence
    context['item'] = instance
    context['item'].request = request
    context['share_image'] = _get_share_image(context, collection.edit_view, item=context['item'])
    _modification_views_page_titles(instance.edit_sentence, context, unicode(instance))
    context['ajax_callback'] = collection.edit_view.ajax_callback
    context['forms'][u'edit_{}'.format(collection.name)] = form
    context['collection'] = collection
    if allowDelete:
        formDelete.alert_message = _('You can\'t cancel this action afterwards.')
        formDelete.action_sentence = instance.delete_sentence
        formDelete.form_title = u'{}: {}'.format(instance.delete_sentence, unicode(instance))
        context['forms'][u'delete_{}'.format(collection.name)] = formDelete

    collection.edit_view.extra_context(context)
    if ajax:
        context['include_template'] = 'collections/modification_view'
        context['extends'] = 'ajax.html'
        context['ajax'] = True
    return render(request, 'collections/modification_view.html', context)
