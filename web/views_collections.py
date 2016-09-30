from __future__ import division
import math
import string
from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _, string_concat
from django.shortcuts import render
from web.middleware.httpredirect import HttpRedirectException
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from web.utils import getGlobalContext, redirectWhenNotAuthenticated
from web.forms import ConfirmDelete
from web.settings import SITE_IMAGE

############################################################
# Internal utils

def _get_filters(request_get, extra_filters={}):
    filters = request_get.copy()
    filters.update(extra_filters)
    return filters

def _authstaff_requirements(page, collection, request, context, default_for_auth=True):
    if collection[page].get('authentication_required', default_for_auth):
        redirectWhenNotAuthenticated(request, context)
    if collection[page].get('staff_required', False) and not request.user.is_staff:
        raise PermissionDenied()

def _get_share_image(context, collection, view, item=None):
    share_image = collection[view].get('share_image', None)
    if callable(share_image):
        share_image = share_image(context, collection, view, item)
    if not share_image:
        share_image = collection.get('share_image', collection.get('image', None))
    if share_image is not None:
        if '//' not in share_image:
            share_image = u'{}img/{}'.format(context['full_static_url'], share_image)
        if 'http' not in share_image:
            share_image = u'http:{}'.format(share_image)
    return share_image

def _modification_view(context, name, collection, view):
    mod_collection = collection[view]
    context['list_url'] = '/{}/'.format(collection['plural_name'])
    context['title'] = collection['title']
    context['name'] = name
    context['plural_name'] = collection['plural_name']
    context['plural_title'] = collection['plural_title']

    context['multipart'] = mod_collection.get('multipart', False)
    context['js_files'] = mod_collection.get('js_files', None)
    context['otherbuttons_template'] = mod_collection.get('otherbuttons_template', None)
    context['back_to_list_button'] = mod_collection.get('back_to_list_button', True)
    context['after_template'] = mod_collection.get('after_template', None)
    return context

def _type(a): return type(a)

############################################################
# Item view

def item_view(request, name, collection, pk, ajax=False, item=None, extra_filters={}, **kwargs):
    context = collection['item'].get('get_global_context', getGlobalContext)(request)
    _authstaff_requirements('item', collection, request, context, default_for_auth=False)
    queryset = collection['item']['filter_queryset'](collection['queryset'], _get_filters(request.GET, extra_filters), request) if 'filter_queryset' in collection['item'] else collection['queryset']
    context['item'] = get_object_or_404(queryset, pk=pk) if not item else item
    if collection['item'].get('owner_only', False) and not request.user.is_staff and context['item'].owner_id != request.user.id:
        raise PermissionDenied()
    context['ajax'] = ajax
    context['name'] = name
    context['title'] = collection['title']
    context['js_files'] = collection['item'].get('js_files', None)
    context['share_image'] = _get_share_image(context, collection, 'item', item=context['item'])
    context['comments_enabled'] = collection['item'].get('comments_enabled', True)
    context['item_template'] = collection['item']['template'] if 'template' in collection['item'] else '{}Item'.format(name)
    context['ajax_callback'] = collection['item'].get('ajax_callback', None)
    if 'extra_context' in collection['item']:
        collection['item']['extra_context'](context)
    if ajax:
        context['include_template'] = 'items/{}'.format(context['item_template'])
        return render(request, 'ajax.html', context)
    return render(request, 'collections/item_view.html', context)

############################################################
# List view

def list_view(request, name, collection, ajax=False, extra_filters={}, **kwargs):
    """
    View function for any page that lists data, such as cards. Handles pagination and context variables.
    name: The string that corresponds to the view (for instance 'cards' for the '/cards/' view)
    """
    context = collection['list'].get('get_global_context', getGlobalContext)(request)
    _authstaff_requirements('list', collection, request, context, default_for_auth=False)
    context['plural_name'] = collection['plural_name']
    page = 0
    page_size = collection['list'].get('page_size', 12)
    if 'page_size' in request.GET:
        try: page_size = int(request.GET['page_size'])
        except ValueError: pass
        if page_size > 500: page_size = 500
    filters = _get_filters(request.GET, extra_filters)
    queryset = collection['list']['filter_queryset'](collection['queryset'], filters, request) if 'filter_queryset' in collection['list'] else collection['queryset']

    if 'ordering' in request.GET and request.GET['ordering']:
        reverse = ('reverse_order' in request.GET and request.GET['reverse_order']) or not request.GET or len(request.GET) == 1
        prefix = '-' if reverse else ''
        ordering = [prefix + ordering for ordering in request.GET['ordering'].split(',')]
    else:
        ordering = collection['list'].get('default_ordering', '-creation').split(',')
    queryset = queryset.order_by(*ordering)

    context['total_results'] = queryset.count()
    context['total_results_sentence'] = _('1 {object} matches your search:').format(object=collection['title']) if context['total_results'] == 1 else _('{total} {objects} match your search:').format(total=context['total_results'], objects=collection['plural_title'])

    if 'page' in request.GET and request.GET['page']:
        page = int(request.GET['page']) - 1
        if page < 0:
            page = 0
    if collection['list'].get('distinct', True):
        queryset = queryset.distinct()
    queryset = queryset[(page * page_size):((page * page_size) + page_size)]

    if 'filter_form' in collection['list']:
        if len(request.GET) > 1 or (len(request.GET) == 1 and 'page' not in request.GET):
            context['filter_form'] = collection['list']['filter_form'](filters, request=request)
        else:
            context['filter_form'] = collection['list']['filter_form'](request=request)

    if 'add' in collection:
        show_add_button = collection['list'].get('show_add_button', True)
        if show_add_button and callable(show_add_button):
            show_add_button = show_add_button(request)
        if show_add_button:
            if not collection['add'].get('staff_required', False) or request.user.is_staff:
                if 'types' in collection['add']:
                    context['add_buttons'] = []
                    for (type, button) in collection['add']['types'].items():
                        context['add_buttons'].append({
                            'link': '/{}/add/{}/'.format(collection['plural_name'], type),
                            'image': button.get('image', None),
                            'title': button.get('title', type),
                            'subtitle': collection['add']['types'][type].get('title', button.get('title', type)),
                        })
                else:
                    context['add_buttons'] = [{
                        'link': '/{}/add/'.format(collection['plural_name']),
                        'image': collection.get('image', None),
                        'title': collection['title'],
                        'subtitle': collection['list'].get('add_button_subtitle', _('Become a contributor to help us fill the database')),
                    }]
                context['add_buttons_col_size'] = int(math.ceil(12 / len(context['add_buttons'])))

    if 'ajax_modal_only' in request.GET:
        # Will display a link to see the other results instead of the pagination button
        context['ajax_modal_only'] = True
        context['filters_string'] = '&'.join(['{}={}'.format(k, v) for k, v in filters.items() if k != 'ajax_modal_only'])
        context['remaining'] = context['total_results'] - page_size
    context['ordering'] = ordering
    context['total_pages'] = int(math.ceil(context['total_results'] / page_size))
    context['items'] = queryset
    context['page'] = page + 1
    context['is_last_page'] = context['page'] == context['total_pages']
    context['page_size'] = page_size
    context['show_no_result'] = not ajax
    context['show_search_results'] = bool(request.GET)
    context['name'] = name
    context['title'] = collection['title']
    context['before_template'] = collection['list'].get('before_template', None)
    context['no_result_template'] = collection['list'].get('no_result_template', None)
    context['after_template'] = collection['list'].get('after_template', None)
    context['show_title'] = collection['list'].get('show_title', False)
    context['plural_title'] = collection['plural_title']
    context['ajax_pagination'] = collection['list'].get('ajax', True)
    context['ajax_pagination_callback'] = collection['list'].get('ajax_pagination_callback', None)
    context['ajax'] = ajax

    context['js_files'] = collection['list'].get('js_files', None)
    context['share_image'] = _get_share_image(context, collection, 'list')
    context['full_width'] = collection['list'].get('full_width', False)
    context['col_break'] = collection['list'].get('col_break', 'md')
    context['per_line'] = collection['list'].get('per_line', 3)
    context['col_size'] = int(math.ceil(12 / context['per_line']))

    if 'extra_context' in collection['list']:
        collection['list']['extra_context'](context)

    if 'foreach_items' in collection['list']:
        for i, item in enumerate(queryset):
            collection['list']['foreach_items'](i, item, context)

    if ajax:
        return render(request, 'collections/list_page.html', context)
    return render(request, 'collections/list_view.html', context)

############################################################
# Add view

def add_view(request, name, collection, type=None, ajax=False, **kwargs):
    context = collection['add'].get('get_global_context', getGlobalContext)(request)
    _authstaff_requirements('add', collection, request, context)
    context = _modification_view(context, name, collection, 'add')
    with_types = False
    context['next'] = request.GET.get('next', None)
    context['next_title'] = request.GET.get('next_title', None)
    if type is not None and 'types' in collection['add']:
        if type not in collection['add']['types']:
            raise Http404
        with_types = True
        formClass = collection['add']['types'][type].get('form_class', collection['add'].get('form_class', None))
        context['imagetitle'] = collection['add']['types'][type].get('image', collection.get('image', None))
        context['after_title'] = collection['add']['types'][type].get('title', type)
    else:
        formClass = collection['add']['form_class']
        context['imagetitle'] = collection.get('image', None)
    if str(_type(formClass)) == '<type \'function\'>':
        formClass = formClass(request, context, collection)
    if request.method == 'GET':
        form = formClass(request=request) if not with_types else formClass(request=request, type=type)
    elif request.method == 'POST':
        form = formClass(request.POST, request.FILES, request=request) if not with_types else formClass(request.POST, request.FILES, request=request, type=type)
        if form.is_valid():
            instance = form.save(commit=False)
            beforeSave = collection['add'].get('before_save', None)
            if beforeSave:
                instance = beforeSave(request, instance, type=type)
            instance.save()
            if collection['add'].get('savem2m', False):
                form.save_m2m()
            afterSave = collection['add'].get('after_save', None)
            if afterSave:
                instance = afterSave(request, instance)
            if collection['add'].get('allow_next', True) and context['next']:
                raise HttpRedirectException(context['next'])
            nextParameters = '?next={}&next_title={}'.format(context['next'], context['next_title'] if context['next_title'] else '') if context['next'] else ''
            redirectAfterAdd = collection['add'].get('redirect_after_add', None)
            if redirectAfterAdd:
                if callable(redirectAfterAdd):
                    redirectAfterAdd = redirectAfterAdd(request, instance, ajax)
                    redirectAfterAdd += nextParameters.replace('?', '&' if '?' in redirectAfterAdd else nextParameters)
                    raise HttpRedirectException(redirectAfterAdd)
                raise HttpRedirectException((redirectAfterAdd if not ajax else '/ajax' + redirectAfterAdd) + (nextParameters.replace('?', '&' if '?' in redirectAfterAdd else nextParameters)))
            raise HttpRedirectException((instance.item_url if not ajax else instance.ajax_item_url) + nextParameters)
    form.verb = 'Add'
    context['share_image'] = _get_share_image(context, collection, 'add')
    context['forms'] = { 'add': form }
    if collection['add'].get('alert_duplicate', True):
        context['alert_message'] = _('Make sure the {thing} you\'re about to add doesn\'t already exist.').format(thing=_(collection['title']))
        context['alert_button_link'] = context['list_url']
        context['alert_button_string'] = _(collection['plural_title'])

    if 'extra_context' in collection['add']:
        collection['add']['extra_context'](context)
    if ajax:
        context['include_template'] = 'collections/modification_view'
        context['extends'] = 'ajax.html'
        context['ajax'] = True
    return render(request, 'collections/modification_view.html', context)

############################################################
# Edit view

def edit_view(request, name, collection, pk, extra_filters={}, ajax=False, **kwargs):
    context = collection['edit'].get('get_global_context', getGlobalContext)(request)
    _authstaff_requirements('edit', collection, request, context)
    context = _modification_view(context, name, collection, 'edit')
    queryset = collection['edit']['filter_queryset'](collection['queryset'], _get_filters(request.GET, extra_filters), request) if 'filter_queryset' in collection['edit'] else collection['queryset']
    instance = get_object_or_404(queryset, pk=pk)
    if collection['edit'].get('owner_only', True) and not request.user.is_staff and instance.owner_id != request.user.id:
        raise PermissionDenied()
    if 'types' in collection['edit']:
        type = instance.type
        formClass = collection['edit']['types'][type].get('form_class', collection['edit'].get('form_class', None))
        context['imagetitle'] = collection['edit']['types'][type].get('image', collection.get('image', None))
        context['after_title'] = collection['edit']['types'][type].get('title', type)
    else:
        formClass = collection['edit']['form_class']
        context['imagetitle'] = collection.get('image', None)
    if _type(formClass) == 'function':
        formClass = formClass(request, context, collection)
    allowDelete = collection['edit'].get('allow_delete', False) and 'disable_delete' not in request.GET
    form = formClass(instance=instance, request=request)
    if allowDelete:
        formDelete = ConfirmDelete(initial={
            'thing_to_delete': instance.pk,
        })
    form = formClass(instance=instance, request=request)
    if allowDelete and request.method == 'POST' and 'delete' in request.POST:
        formDelete = ConfirmDelete(request.POST)
        if formDelete.is_valid():
            redirectAfterDelete = collection['edit'].get('redirect_after_delete', None)
            if redirectAfterDelete:
                if callable(redirectAfterDelete):
                    redirectAfterDelete = redirectAfterDelete(request, instance, ajax)
                else:
                    redirectAfterDelete = redirectAfterDelete if not ajax else '/ajax' + redirectAfterDelete
            else:
                redirectAfterDelete = '{}/{}/'.format('' if not ajax else '/ajax', collection['plural_name'])
            instance.delete()
            raise HttpRedirectException(redirectAfterDelete)
    elif request.method == 'POST':
        form = formClass(request.POST, request.FILES, instance=instance, request=request)
        if form.is_valid():
            instance = form.save(commit=False)
            beforeSave = collection['edit'].get('before_save', None)
            if beforeSave:
                instance = beforeSave(request, instance)
            instance.save()
            if collection['edit'].get('savem2m', False):
                form.save_m2m()
            afterSave = collection['edit'].get('after_save', None)
            if afterSave:
                instance = afterSave(request, instance)
            redirectAfterEdit = collection['edit'].get('redirect_after_edit', None)
            if redirectAfterEdit:
                if callable(redirectAfterEdit):
                    raise HttpRedirectException(redirectAfterEdit(request, instance, ajax))
                raise HttpRedirectException(redirectAfterEdit if not ajax else '/ajax' + redirectAfterEdit)
            raise HttpRedirectException(instance.item_url if not ajax else instance.ajax_item_url)
    context['forms'] = OrderedDict()
    form.verb = 'Edit'
    context['item'] = instance
    context['share_image'] = _get_share_image(context, collection, 'edit', item=context['item'])
    context['forms']['edit'] = form
    if allowDelete:
        formDelete.alert_message = _('You can\'t cancel this action afterwards.')
        formDelete.verb = _('Delete')
        context['forms']['delete'] = formDelete
    context['after_title'] = instance

    if 'extra_context' in collection['edit']:
        collection['edit']['extra_context'](context)
    if ajax:
        context['include_template'] = 'collections/modification_view'
        context['extends'] = 'ajax.html'
        context['ajax'] = True
    return render(request, 'collections/modification_view.html', context)
