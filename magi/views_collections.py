from __future__ import division
import math
import string
from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _, string_concat
from django.shortcuts import render
from magi.middleware.httpredirect import HttpRedirectException
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.core.exceptions import PermissionDenied

from magi.utils import getGlobalContext, cuteFormFieldsForContext
from magi.forms import ConfirmDelete, filter_ids
from magi.settings import SITE_IMAGE, ACCOUNT_MODEL

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

def _show_edit_button(collection, collection_view, request, context):
    if collection_view.show_edit_button and collection.edit_view.has_permissions(request, context):
        context['show_edit_button'] = True
        context['show_edit_ajax_enabled'] = collection.edit_view.ajax
        if collection.edit_view.owner_only:
            context['show_edit_button_owner_only'] = True
        if collection.edit_view.staff_required:
            context['edit_button_staff_only'] = True

def _show_collect_button(collection, collection_view, request, context):
    if collection.collectible and collection.collectible.add_view.enabled:
        context['collectible'] = True
        if collection.collectible.add_view.has_permissions(request, context):
            context['collectible_has_permissions'] = True
        if collection.collectible.add_view.ajax:
            context['collectible_ajax'] = True
        if collection_view.show_collect_button:
            context['show_collect_button'] = True
        if collection.collectible.add_view.staff_required:
            context['collectible_staff_only'] = True

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
    context['item'] = get_object_or_404(queryset, **options) if not item else item
    collection.item_view.check_owner_permissions(request, context, context['item'])

    _show_edit_button(collection, collection.item_view, request, context)
    _show_collect_button(collection, collection.item_view, request, context)

    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url
    context['ajax'] = ajax
    context['name'] = name
    context['page_title'] = u'{title}: {item}'.format(title=collection.title, item=context['item'])
    context['js_files'] = collection.item_view.js_files
    context['reportable'] = collection.reportable
    context['share_image'] = _get_share_image(context, collection.item_view, item=context['item'])
    context['comments_enabled'] = collection.item_view.comments_enabled
    context['item_template'] = collection.item_view.template
    if context['item_template'] == 'default':
        context['show_edit_button'] = False
        context['item_fields'] = collection.to_fields(context['item'])
        context['top_illustration'] = collection.item_view.top_illustration
        if context['show_collect_button']:
            context['show_collect_button'] = False
            if request.user.is_authenticated() and collection.collectible:
                if collection.collectible_with_accounts:
                    context['accounts'] = ACCOUNT_MODEL.filter(owner=request.user)

    context['include_below_item'] = context.get('show_edit_button', False) or context.get('show_collect_button', False)
    context['ajax_callback'] = collection.item_view.ajax_callback
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
        if collection.list_view.show_relevant_fields_on_ordering and prefix + request.GET['ordering'] != collection.list_view.default_ordering:
            context['show_relevant_fields_on_ordering'] = True
            context['plain_ordering'] = [o[1:] if o.startswith('-') else o for o in ordering]
    else:
        ordering = collection.list_view.default_ordering.split(',')
    queryset = queryset.order_by(*ordering)

    if collection.list_view.filter_form:
        if len(request.GET) > 1 or (len(request.GET) == 1 and 'page' not in request.GET):
            context['filter_form'] = collection.list_view.filter_form(filters, request=request, collection=collection)
            if hasattr(context['filter_form'], 'filter_queryset'):
                queryset = context['filter_form'].filter_queryset(queryset, filters, request)
            else:
                queryset = filter_ids(queryset, request)
        else:
            context['filter_form'] = collection.list_view.filter_form(request=request, collection=collection)

    context['total_results'] = queryset.count()
    context['total_results_sentence'] = _('1 {object} matches your search:').format(object=collection.title) if context['total_results'] == 1 else _('{total} {objects} match your search:').format(total=context['total_results'], objects=collection.plural_title)

    if 'page' in request.GET and request.GET['page']:
        page = int(request.GET['page']) - 1
        if page < 0:
            page = 0
    if collection.list_view.distinct:
        queryset = queryset.distinct()
    queryset = queryset[(page * page_size):((page * page_size) + page_size)]

    if 'filter_form' in context:
        cuteFormFieldsForContext(collection.list_view.filter_cuteform, context, form=context['filter_form'])

    if collection.add_view.enabled:
        if collection.list_view.show_add_button(request):
            if collection.add_view.has_permissions(request, context):
                if collection.types:
                    context['add_buttons'] = []
                    for (type, button) in collection.types.items():
                        if not button.get('show_button', True):
                            continue
                        context['add_buttons'].append({
                            'link': collection.get_add_url(type=type),
                            'image': button.get('image', None),
                            'title': button.get('title', type),
                            'subtitle': collection.types[type].get('title', button.get('title', type)),
                        })
                else:
                    context['add_buttons'] = [{
                        'link': collection.get_add_url(),
                        'image': collection.image,
                        'title': collection.title,
                        'subtitle': collection.list_view.add_button_subtitle,
                    }]
                context['add_buttons_staff_only'] = collection.add_view.staff_required
                context['add_buttons_col_size'] = int(math.ceil(12 / len(context['add_buttons'])))

    _show_edit_button(collection, collection.list_view, request, context)
    _show_collect_button(collection, collection.list_view, request, context)

    if 'ajax_modal_only' in request.GET:
        # Will display a link to see the other results instead of the pagination button
        context['ajax_modal_only'] = True
        context['filters_string'] = '&'.join(['{}={}'.format(k, v) for k, v in filters.items() if k != 'ajax_modal_only'])
        context['remaining'] = context['total_results'] - page_size

    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url
    context['ordering'] = ordering
    context['include_below_item'] = context.get('show_edit_button', False) or context.get('show_relevant_fields_on_ordering', False) or context.get('show_collect_button', False)
    context['page_title'] = collection.plural_title
    context['total_pages'] = int(math.ceil(context['total_results'] / page_size))
    context['items'] = queryset
    context['page'] = page + 1
    context['is_last_page'] = context['page'] == context['total_pages']
    context['page_size'] = page_size
    context['show_no_result'] = not ajax
    context['show_search_results'] = bool(request.GET)
    context['name'] = name
    context['title'] = collection.title
    context['reportable'] = collection.reportable
    context['hide_sidebar'] = collection.list_view.hide_sidebar
    context['before_template'] = collection.list_view.before_template
    context['no_result_template'] = collection.list_view.no_result_template
    context['after_template'] = collection.list_view.after_template
    context['item_template'] = collection.list_view.item_template
    if context['item_template'] == 'default':
        context['item_template'] = 'default_item_in_list'
    context['show_title'] = collection.list_view.show_title
    context['plural_title'] = collection.plural_title
    context['ajax_pagination'] = collection.list_view.ajax
    context['ajax_pagination_callback'] = collection.list_view.ajax_pagination_callback
    context['ajax'] = ajax
    context['ajax_callback'] = collection.list_view.ajax_callback

    context['js_files'] = collection.list_view.js_files
    context['share_image'] = _get_share_image(context, collection.list_view)
    context['full_width'] = collection.list_view.full_width
    context['col_break'] = collection.list_view.col_break
    context['per_line'] = collection.list_view.per_line
    context['col_size'] = int(math.ceil(12 / context['per_line']))
    context['item_view_enabled'] = collection.item_view.enabled
    context['ajax_item_view_enabled'] = context['item_view_enabled'] and collection.item_view.ajax

    collection.list_view.extra_context(context)

    if collection.list_view.foreach_items or context.get('show_relevant_fields_on_ordering', False):
        for i, item in enumerate(queryset):
            if collection.list_view.foreach_items:
                collection.list_view.foreach_items(i, item, context)
            if context.get('show_relevant_fields_on_ordering', False):
                item.relevant_fields_to_show = collection.to_fields(item, only_fields=context['plain_ordering'], in_list=True)

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
        form = formClass(request=request, collection=collection) if not with_types else formClass(request=request, collection=collection, type=type)
    elif request.method == 'POST':
        form = formClass(request.POST, request.FILES, request=request, collection=collection) if not with_types else formClass(request.POST, request.FILES, request=request, collection=collection, type=type)
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
    cuteFormFieldsForContext(collection.add_view.filter_cuteform, context, form=form)
    _modification_views_page_titles(collection.add_sentence, context, after_title)
    context['action_sentence'] = collection.add_sentence # Used in page title
    form.action_sentence = collection.add_sentence # Genericity when we have multiple forms
    context['share_image'] = _get_share_image(context, collection.add_view)
    context['forms'] = { 'add': form }
    context['ajax_callback'] = collection.add_view.ajax_callback
    if collection.add_view.alert_duplicate:
        context['alert_message'] = _('Make sure the {thing} you\'re about to add doesn\'t already exist.').format(thing=_(collection.title))
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
    collection.edit_view.check_permissions(request, context)
    context = _modification_view(context, name, collection.edit_view)
    queryset = collection.edit_view.get_queryset(collection.queryset, _get_filters(request.GET, extra_filters), request)
    instance = get_object_or_404(queryset, **collection.item_view.get_item(request, pk))
    context['type'] = None
    collection.edit_view.check_owner_permissions(request, context, instance)
    if collection.types:
        type = instance.type
        context['type'] = type
        formClass = collection.types[type].get('form_class', collection.edit_view.form_class)
        context['imagetitle'] = collection.types[type].get('image', collection.image)
        context['icontitle'] = collection.types[type].get('icon', collection.icon)
    else:
        formClass = collection.edit_view.form_class
        context['imagetitle'] = collection.image
        context['icontitle'] = collection.icon
    if str(_type(formClass)) == '<type \'instancemethod\'>':
        formClass = formClass(request, context)
    allowDelete = collection.edit_view.allow_delete and 'disable_delete' not in request.GET
    form = formClass(instance=instance, request=request, collection=collection)
    if allowDelete:
        formDelete = ConfirmDelete(initial={
            'thing_to_delete': instance.pk,
        })
    form = formClass(instance=instance, request=request, collection=collection)
    if allowDelete and request.method == 'POST' and 'delete' in request.POST:
        formDelete = ConfirmDelete(request.POST)
        if formDelete.is_valid():
            redirectURL = collection.edit_view.redirect_after_delete(request, instance, ajax)
            instance.delete()
            raise HttpRedirectException(redirectURL)
    elif request.method == 'POST':
        form = formClass(request.POST, request.FILES, instance=instance, request=request, collection=collection)
        if form.is_valid():
            instance = form.save(commit=False)
            instance = collection.edit_view.before_save(request, instance)
            instance.save()
            if collection.edit_view.savem2m:
                form.save_m2m()
            instance = collection.edit_view.after_save(request, instance)
            redirectURL = collection.edit_view.redirect_after_edit(request, instance, ajax)
            raise HttpRedirectException(redirectURL)
    cuteFormFieldsForContext(collection.edit_view.filter_cuteform, context, form=form)
    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url
    context['forms'] = OrderedDict()
    context['action_sentence'] = instance.edit_sentence # Used as the page title
    form.action_sentence = instance.edit_sentence
    context['item'] = instance
    context['share_image'] = _get_share_image(context, collection.edit_view, item=context['item'])
    _modification_views_page_titles(instance.edit_sentence, context, unicode(instance))
    context['ajax_callback'] = collection.edit_view.ajax_callback
    context['forms']['edit'] = form
    if allowDelete:
        formDelete.alert_message = _('You can\'t cancel this action afterwards.')
        formDelete.action_sentence = instance.delete_sentence
        context['forms']['delete'] = formDelete

    collection.edit_view.extra_context(context)
    if ajax:
        context['include_template'] = 'collections/modification_view'
        context['extends'] = 'ajax.html'
        context['ajax'] = True
    return render(request, 'collections/modification_view.html', context)
