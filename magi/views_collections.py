from __future__ import division
import math, string
from collections import OrderedDict
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from magi.middleware.httpredirect import HttpRedirectException
from django.shortcuts import render
from django.http import Http404
from django.conf import settings as django_settings
from django.core.exceptions import PermissionDenied
from django.forms import HiddenInput, ChoiceField
from magi.utils import (
    cuteFormFieldsForContext,
    get_one_object_or_404,
    listUnique,
    staticImageURL,
    getColSize,
    getSearchFieldHelpText,
    pageTitleFromPrefixes,
    h1ToContext,
    simplifyMarkdown,
    summarize,
    matchesTemplate,
    HTMLAlert,
    addParametersToURL,
    modelGetField,
    setJavascriptFormContext,
)
from magi.raw import (
    GET_PARAMETERS_NOT_IN_FORM,
    GET_PARAMETERS_IN_FORM_HANDLED_OUTSIDE,
)
from magi.forms import ConfirmDelete, filter_ids

############################################################
# Internal utils

def _redirect_on_high_traffic(view, request, ajax=False):
    if (getattr(django_settings, 'HIGH_TRAFFIC', False)
        and view.disable_on_high_traffic
        and not request.user.is_authenticated()):
        raise HttpRedirectException(u'{}/hightraffic/'.format('/ajax' if ajax else ''))

def _get_filters(request_get, extra_filters={}):
    filters = request_get.copy()
    filters.update(extra_filters)
    return filters

def _get_share_image(context, collection_view, item=None):
    return staticImageURL(collection_view.share_image(context, item), full=True)

def _modification_view(context, name, view, ajax):
    context['list_url'] = '/{}/'.format(view.collection.plural_name)
    context['title'] = view.collection.title
    context['name'] = name
    context['plural_name'] = view.collection.plural_name
    context['plural_title'] = view.collection.plural_title

    context['multipart'] = view.multipart
    context['js_files'] = view.js_files
    context['otherbuttons_template'] = view.otherbuttons_template
    context['back_to_list_button'] = view.back_to_list_button
    context['back_to_list_url'] = view.collection.get_list_url()
    if ajax:
        context['back_to_list_ajax_url'] = view.collection.get_list_url(ajax=True, modal_only=True)
    context['back_to_list_title'] = _('Back to {page_name}').format(
        page_name=view.collection.plural_title.lower(),
    )
    context['after_template'] = view.after_template
    return context

def _add_h1_and_prefixes_to_context(view, context, title_prefixes, h1, item=None, get_page_title_parameters={}):
    context['show_title'] = view.show_title
    if context.get('alt_view', None) and 'show_title' in context['alt_view']:
        context['show_title'] = context['alt_view']['show_title']
    context['show_small_title'] = view.show_small_title
    if context.get('alt_view', None) and 'show_small_title' in context['alt_view']:
        context['show_small_title'] = context['alt_view']['show_small_title']
    context['title_prefixes'] = title_prefixes
    h1ToContext(h1, context)
    context['page_title'] = pageTitleFromPrefixes(
        title_prefixes, view.get_page_title(**get_page_title_parameters),
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
    _redirect_on_high_traffic(collection.item_view, request, ajax=ajax)
    request.show_collect_button = collection.item_view.show_collect_button
    queryset = collection.item_view.get_queryset(collection.queryset, _get_filters(request.GET, extra_filters), request)
    if not pk and reverse:
        options = collection.item_view.reverse_url(reverse)
    else:
        options = collection.item_view.get_item(request, pk)
    context['item'] = get_one_object_or_404(queryset, **options) if not item else item
    context['item'].request = request
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

    # Page description
    description = unicode(context['item'])
    for field_name, is_markdown in [
            ('t_m_description', True),
            ('t_description', False),
            ('m_description', True),
            ('description', False),
    ]:
        description = getattr(context['item'], field_name, None)
        if description:
            if isinstance(description, tuple):
                description = description[1]
            description = (simplifyMarkdown if is_markdown else summarize)(description, max_length=158)
            break
    context['page_description'] = description

    context['js_files'] = collection.item_view.js_files
    context['reportable'] = collection.reportable
    context['allow_suggest_edit'] = collection.allow_suggest_edit
    context['share_image'] = _get_share_image(context, collection.item_view, item=context['item'])
    context['comments_enabled'] = collection.item_view.comments_enabled
    context['share_enabled'] = collection.item_view.share_enabled
    context['item_padding'] = collection.item_view.item_padding
    if ajax:
        context['item_max_height'] = collection.item_view.ajax_item_max_height
    else:
        context['item_max_height'] = collection.item_view.item_max_height
    context['item_template'] = collection.item_view.template
    context['full_width'] = collection.item_view.full_width
    context['ajax_callback'] = collection.item_view.ajax_callback
    context['hide_icons'] = collection.item_view.hide_icons
    context['staff_only_view'] = collection.item_view.staff_required
    context['collection'] = collection
    if context['item_template'] == 'default':
        context['top_illustration'] = collection.item_view.top_illustration
        context['item_fields'] = collection.item_view.to_fields(context['item'], request=request)

    # Ajax items reloader
    if not ajax and collection.item_view.auto_reloader and collection.item_view.ajax:
        context['ajax_reload_url'] = context['item'].ajax_item_url
        context['reload_urls_start_with'] = [u'/{}/edit/'.format(collection.plural_name)];
        if collection.collectible_collections:
            context['reload_urls_start_with'] += [cc.get_add_url() for cc in collection.collectible_collections.values()]

    # Title and prefixes
    title_prefixes, h1 = collection.item_view.get_h1_title(request, context, context['item'])
    _add_h1_and_prefixes_to_context(
        collection.item_view, context, title_prefixes, h1, context['item'], get_page_title_parameters={
            'item': context['item'], })

    context['include_below_item'] = False
    context['show_item_buttons'] = collection.item_view.show_item_buttons
    context['item'].show_item_buttons_justified = collection.item_view.show_item_buttons_justified
    context['item'].show_item_buttons_as_icons = collection.item_view.show_item_buttons_as_icons
    context['item'].show_item_buttons_in_one_line = collection.item_view.show_item_buttons_in_one_line
    context['item'].buttons_to_show = collection.item_view.buttons_per_item(request, context, context['item'])
    if 'only_show_buttons' in request.GET:
        only_show_buttons = request.GET['only_show_buttons'].split(',')
        for button_name, button in context['item'].buttons_to_show.items():
            if button_name not in only_show_buttons:
                button['show'] = False
    if collection.item_view.show_item_buttons and [True for b in context['item'].buttons_to_show.values() if b['show'] and b['has_permissions']]:
        context['include_below_item'] = True

    collection.item_view.extra_context(context)
    if ajax:
        context['ajax_include_title'] = True
        context['include_template'] = 'items/{}'.format(context['item_template'])
        return render(request, 'ajax.html', context)
    return render(request, 'collections/item_view.html', context)

############################################################
# Random view

def random_view(request, name, collection, ajax=False, extra_filters={}, shortcut_url=None, **kwargs):
    collection.list_view.check_permissions(request, {})
    filters = _get_filters(request.GET, extra_filters)
    queryset = collection.list_view.get_queryset(collection.queryset, filters, request)

    filter_form = collection.list_view.filter_form(
        filters, request=request, ajax=ajax, collection=collection, preset=None, allow_next=False)
    if hasattr(filter_form, 'filter_queryset'):
        queryset = filter_form.filter_queryset(queryset, filters, request)

    try:
        random_item = queryset.order_by('?')[0]
    except IndexError:
        raise HttpRedirectException(collection.get_list_url(
            ajax=ajax, modal_only=ajax,
        ))
    raise HttpRedirectException(random_item.ajax_item_url if ajax else random_item.item_url)

############################################################
# List view

def list_view(request, name, collection, ajax=False, extra_filters={}, shortcut_url=None, **kwargs):
    """
    View function for any page that lists data, such as cards. Handles pagination and context variables.
    name: The string that corresponds to the view (for instance 'cards' for the '/cards/' view)
    """

    context = collection.list_view.get_global_context(request)

    if (shortcut_url == ''
        and context.get('launch_date', None)
        and (not request.user.is_authenticated()
             or not request.user.hasPermission('access_site_before_launch'))):
        raise HttpRedirectException('/prelaunch/')

    collection.list_view.check_permissions(request, context)
    _redirect_on_high_traffic(collection.list_view, request, ajax=ajax)

    context['plural_name'] = collection.plural_name
    page = 0

    # Alt views
    context['view'] = None
    context['alt_view'] = None
    alt_views = dict(collection.list_view.alt_views)
    page_size = collection.list_view.page_size
    request.show_collect_button = collection.list_view.show_collect_button
    if 'view' in request.GET and request.GET['view'] in alt_views:
        context['view'] = request.GET['view']
        context['alt_view'] = alt_views[context['view']]
    if context['alt_view'] and 'page_size' in context['alt_view']:
        page_size = context['alt_view']['page_size']
    if context['alt_view'] and 'show_collect_button' in context['alt_view']:
        request.show_collect_button = context['alt_view']['show_collect_button']

    if 'page_size' in request.GET:
        try: page_size = int(request.GET['page_size'])
        except ValueError: pass
        if page_size > 500: page_size = 500
    filters = _get_filters(request.GET, extra_filters)

    queryset = collection.list_view.get_queryset(collection.queryset, filters, request)

    show_relevant_fields_on_ordering = collection.list_view.show_relevant_fields_on_ordering
    if context['alt_view'] and 'show_relevant_fields_on_ordering' in context['alt_view']:
        show_relevant_fields_on_ordering = context['alt_view']['show_relevant_fields_on_ordering']
    if 'hide_relevant_fields_on_ordering' in request.GET:
        show_relevant_fields_on_ordering = False

    ordering = None
    if (request.GET.get('ordering', None)
        and ((request.user.is_authenticated()
              and request.user.hasPermission('order_by_any_field'))
             or (collection.list_view.filter_form
                 and request.GET['ordering'] in dict(
                     getattr(collection.list_view.filter_form, 'ordering_fields', []))))):
        reverse = ('reverse_order' in request.GET and request.GET['reverse_order']) or not request.GET or len(request.GET) == 1
        prefix = '-' if reverse else ''
        ordering = [prefix + ordering for ordering in request.GET['ordering'].split(',')]
        ordering = [order[2:] if order.startswith('--') else order for order in ordering]

        if (show_relevant_fields_on_ordering
            and request.GET['ordering'] != ','.join(collection.list_view.plain_default_ordering_list)):
            context['show_relevant_fields_on_ordering'] = True
            context['plain_ordering'] = [o[1:] if o.startswith('-') else o for o in ordering]

    filled_filter_form = False
    preset = None
    if collection.list_view.filter_form:
        # Set default values from presets
        if getattr(collection.list_view.filter_form, 'presets'):
            url = request.path[5:] if request.path.startswith('/ajax') else request.path
            template = u'/{}/{}/'.format(collection.plural_name, '{preset}')
            matches = matchesTemplate(template, url)
            presets = collection.list_view.filter_form.get_presets()
            if matches and matches['preset'] in presets:
                preset = matches['preset']
                context['preset'] = preset
                filters.update(collection.list_view.filter_form.get_presets_fields(preset))

        if len([
                k for k in filters.keys()
                if k not in GET_PARAMETERS_NOT_IN_FORM + GET_PARAMETERS_IN_FORM_HANDLED_OUTSIDE
        ]) > 0:
            context['filter_form'] = collection.list_view.filter_form(filters, request=request, ajax=ajax, collection=collection, preset=preset, allow_next=False)
            filled_filter_form = len(request.GET) > 0
        else:
            context['filter_form'] = collection.list_view.filter_form(request=request, ajax=ajax, collection=collection, preset=preset, allow_next=False)
        if hasattr(context['filter_form'], 'filter_queryset'):
            queryset = context['filter_form'].filter_queryset(queryset, filters, request)
        else:
            queryset = filter_ids(queryset, request)
    else:
        queryset = filter_ids(queryset, request)

    if preset and 'filter_form' in context:
        try:
            context['filter_form'].action_url = collection.list_view.get_clear_url(request)
        except AttributeError:
            pass

    if not ordering:
        if ('filter_form' in context
            and 'ordering' in context['filter_form'].fields
            and context['filter_form'].fields['ordering'].initial):
            reverse = True
            if 'reverse_order' in context['filter_form'].fields:
                reverse = context['filter_form'].fields['reverse_order'].initial
            ordering = [
                u'{}{}'.format(
                    '-' if reverse else '',
                    ordering_field,
                ) for ordering_field in context['filter_form'].fields['ordering'].initial.split(',')
            ]
        else:
            ordering = collection.list_view.default_ordering.split(',')

    # Hide items without value when order is not reversed (lower values first)
    # because it would otherwise show them first which can be confusing
    if len(ordering) == 1 and filled_filter_form:
        field_name = ordering[0][1:] if ordering[0].startswith('-') else ordering[0]
        field = modelGetField(collection.queryset.model, field_name)
        if (field and field.null
            and not ordering[0].startswith('-')):
            queryset = queryset.exclude(**{ u'{}__isnull'.format(field_name): True })

    queryset = queryset.order_by(*ordering)

    if collection.list_view.distinct:
        queryset = queryset.distinct()
    context['total_results'] = queryset.count()
    context['total_results_sentence'] = _('1 {object} matches your search:').format(object=collection.title.lower()) if context['total_results'] == 1 else _('{total} {objects} match your search:').format(total=context['total_results'], objects=collection.plural_title.lower())

    if 'page' in request.GET and request.GET['page']:
        try:
            page = int(request.GET['page']) - 1
        except ValueError:
            page = 0
        if page < 0:
            page = 0
    unpaginated_queryset = queryset
    queryset = queryset[(page * page_size):((page * page_size) + page_size)]

    if 'filter_form' in context and not ajax:
        setJavascriptFormContext(
            form=context['filter_form'],
            form_selector='[id=\\"filter-form-{}\\"]'.format(collection.name),
            context=context,
            cuteforms=[collection.list_view.filter_cuteform],
            ajax=ajax,
        )

    # Will display a link to see the other results instead of the pagination button
    context['ajax_modal_only'] = False
    if 'ajax_modal_only' in request.GET:
        context['ajax_modal_only'] = True
        context['filters_string'] = '&'.join(['{}={}'.format(k, v) for k, v in filters.items() if k != 'ajax_modal_only'])
        context['remaining'] = context['total_results'] - page_size

    # Will still show top buttons at the top, first page only
    context['ajax_show_top_buttons'] = ajax and 'ajax_show_top_buttons' in request.GET and page == 0

    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url

    context['ordering'] = ordering

    # Page description
    if shortcut_url != '':
        if 'filter_form' in context:
            filters_labels = [
                unicode(field.label).lower()
                for field_name, field in context['filter_form'].fields.items()
                if (field.label and field_name not in [
                        'search', 'ordering', 'reverse_order',
                ] and not isinstance(field.widget, HiddenInput)
                    and (isinstance(field, ChoiceField)))
            ]
            search_fields = (
                list(getattr(context['filter_form'], 'search_fields', []))
                + list(getattr(context['filter_form'], 'search_fields_exact', []))
            )
            search_label = None
            if search_fields:
                search_label = getSearchFieldHelpText(
                    search_fields, collection.queryset.model, {},
                    collection.translated_fields or [], all_lower=True,
                )
        else:
            filters_labels = []
            search_label = []
        context['page_description'] = _(u'All the {things}! Search by {search_terms} and filter by {filters} to find all the details you need about the {things} from {game}.').format(
                things=collection.plural_title.lower(),
                search_terms=search_label or _('Name').lower(),
                filters=u', '.join(filters_labels) or _('Type').lower(),
                game=context['game_name'],
            )

    context['total_pages'] = int(math.ceil(context['total_results'] / page_size))
    context['items'] = queryset
    context['page'] = page + 1

    page_buttons = [(0, 'active' if page == 0 else None)]
    if page > 2:
        page_buttons.append((-1, 'disabled'))
    if (page - 1) > 0:
        page_buttons.append((page - 1, None))
    page_buttons.append((page, 'active'))
    if (page + 1) < (context['total_pages'] - 1):
        page_buttons.append((page + 1, None))
    if page < (context['total_pages'] - 3):
        page_buttons.append((-2, 'disabled'))
    page_buttons.append((context['total_pages'] - 1, 'active' if page == (context['total_pages'] - 1) else None))
    context['displayed_page_buttons'] = listUnique(page_buttons)
    if request.path and request.path != '/':
        context['next_page_url'] = u'/ajax{}'.format(request.path)
    else:
        context['next_page_url'] = u'/ajax/{}/'.format(collection.plural_name)

    # Ajax items reloader
    if not ajax and collection.list_view.auto_reloader and collection.list_view.ajax:
        context['ajax_reload_url'] = context['next_page_url']
        context['reload_urls_start_with'] = [u'/{}/edit/'.format(collection.plural_name)];
        if collection.collectible_collections:
            context['reload_urls_start_with'] += [cc.get_add_url() for cc in collection.collectible_collections.values()]

    context['is_last_page'] = context['page'] == context['total_pages']
    context['page_size'] = page_size
    context['show_no_result'] = not ajax or context['ajax_modal_only'] or 'ajax_show_no_result' in request.GET
    context['show_search_results'] = collection.list_view.show_search_results and filled_filter_form
    context['show_owner'] = 'show_owner' in request.GET
    context['get_started'] = 'get_started' in request.GET
    context['name'] = name
    context['title'] = collection.title
    context['reportable'] = collection.reportable
    context['allow_suggest_edit'] = collection.allow_suggest_edit
    context['hide_sidebar'] = collection.list_view.hide_sidebar
    context['before_template'] = collection.list_view.before_template
    context['no_result_template'] = collection.list_view.no_result_template
    context['after_template'] = collection.list_view.after_template
    context['item_template'] = collection.list_view.item_template
    context['hide_icons'] = collection.list_view.hide_icons
    context['item_blocked_template'] = collection.list_view.item_blocked_template
    if context['alt_view'] and 'template' in context['alt_view']:
        context['item_template'] = context['alt_view']['template']
    context['item_padding'] = collection.list_view.item_padding
    if context['alt_view'] and 'item_padding' in context['alt_view']:
        context['item_padding'] = context['alt_view']['item_padding']
    context['item_max_height'] = collection.list_view.item_max_height
    context['plural_title'] = collection.plural_title
    context['show_items_names'] = collection.list_view.show_items_names
    if context['alt_view'] and 'show_items_names' in context['alt_view']:
        context['show_items_names'] = context['alt_view']['show_items_names']
    context['lowercase_plural_title'] = collection.plural_title.lower()
    context['ajax_pagination'] = collection.list_view.ajax
    context['ajax_pagination_callback'] = collection.list_view.ajax_pagination_callback
    if not ajax or context['ajax_modal_only']:
        # Should only be called once
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
    if context['display_style'] == 'table' and context['item_template'] == 'default_item_in_list':
        context['item_template'] = 'default_item_table_view'
    context['display_style_table_classes'] = collection.list_view.display_style_table_classes
    context['display_style_table_fields'] = collection.list_view.display_style_table_fields
    if context['alt_view'] and 'display_style_table_fields' in context['alt_view']:
        context['display_style_table_fields'] = context['alt_view']['display_style_table_fields']
    context['col_break'] = collection.list_view.col_break
    if context['alt_view'] and 'col_break' in context['alt_view']:
        context['col_break'] = context['alt_view']['col_break']
    context['per_line'] = int(request.GET['max_per_line']) if 'max_per_line' in request.GET and int(request.GET['max_per_line']) < collection.list_view.per_line else collection.list_view.per_line
    if context['alt_view'] and 'per_line' in context['alt_view']:
        context['per_line'] = context['alt_view']['per_line']
    context['col_size'] = getColSize(context['per_line'])
    context['ajax_item_popover'] = collection.list_view.ajax_item_popover
    context['item_view_enabled'] = collection.item_view.enabled
    context['ajax_item_view_enabled'] = context['item_view_enabled'] and collection.item_view.ajax and not context['ajax_item_popover']
    context['include_below_item'] = False # May be set to true below
    context['staff_only_view'] = collection.list_view.staff_required
    context['collection'] = collection

    if context['display_style'] == 'table':
        context['table_fields_headers'] = collection.list_view.table_fields_headers(context['display_style_table_fields'], view=context['view'])
        context['table_fields_headers_sections'] = collection.list_view.table_fields_headers_sections(view=context['view'])

    # Title and prefixes
    title_prefixes, h1 = collection.list_view.get_h1_title(
        request, context, view=context['view'], preset=preset)
    _add_h1_and_prefixes_to_context(collection.list_view, context, title_prefixes, h1)

    context['get_started'] = 'get_started' in request.GET
    if context['get_started']:
        context['show_small_title'] = False
        context['show_search_results'] = False
        context['before_template'] = 'include/getstarted'
        context['share_collection_sentence'] = _('Share your {things}!').format(things=unicode(collection.plural_title).lower())
        context['after_template'] = 'include/afterGetStarted'

    # Top buttons

    if not ajax or context['ajax_show_top_buttons']:
        context['top_buttons'] = collection.list_view.top_buttons(request, context)
        context['filtered_top_buttons'] = OrderedDict([
            (button_name, button) for button_name, button in context['top_buttons'].items()
            if button['show'] and button['has_permissions']
        ])
        context['top_buttons_total'] = len(context['filtered_top_buttons'])
        if context['top_buttons_total']:
            context['top_buttons_per_line'] = (
                collection.list_view.top_buttons_per_line or context['top_buttons_total'])
            if context['top_buttons_total'] < context['top_buttons_per_line']:
                context['top_buttons_per_line'] = context['top_buttons_total']
            context['top_buttons_col_size'] = getColSize(context['top_buttons_per_line'])

    context['show_item_buttons'] = collection.list_view.show_item_buttons
    if context['alt_view'] and 'show_item_buttons' in context['alt_view']:
        context['show_item_buttons'] = context['alt_view']['show_item_buttons']

    if not filled_filter_form and not preset and collection.list_view.show_section_header_on_change:
        if page > 0:
            try:
                previous_section_header = getattr(
                    unpaginated_queryset[(page * page_size) - 1],
                    collection.list_view.show_section_header_on_change,
                )
            except IndexError:
                previous_section_header = None
        else:
            previous_section_header = None

    for i, item in enumerate(queryset):
        item.request = request
        if collection.list_view.foreach_items:
            collection.list_view.foreach_items(i, item, context)
        if context.get('show_relevant_fields_on_ordering', False):
            context['include_below_item'] = True
            item.relevant_fields_to_show = collection.list_view.ordering_fields(item, only_fields=context['plain_ordering'], request=request)
        if context['display_style'] == 'table':
            item.table_fields = collection.list_view.table_fields(item, only_fields=context['display_style_table_fields'], force_all_fields=True, request=request)
        item.buttons_to_show = collection.list_view.buttons_per_item(request, context, item)
        if 'only_show_buttons' in request.GET:
            only_show_buttons = request.GET['only_show_buttons'].split(',')
            for button_name, button in item.buttons_to_show.items():
                if button_name not in only_show_buttons:
                    button['show'] = False
        item.show_item_buttons_justified = collection.list_view.show_item_buttons_justified
        item.show_item_buttons_as_icons = collection.list_view.show_item_buttons_as_icons
        if context['alt_view'] and 'show_item_buttons_as_icons' in context['alt_view']:
            item.show_item_buttons_as_icons = context['alt_view']['show_item_buttons_as_icons']
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
        if not filled_filter_form and not preset and collection.list_view.show_section_header_on_change:
            if getattr(item, collection.list_view.show_section_header_on_change) != previous_section_header:
                item.show_section_header = getattr(item, collection.list_view.show_section_header_on_change)
                previous_section_header = item.show_section_header
                context['showing_section_headers'] = True
            else:
                item.show_section_header = False

    collection.list_view.extra_context(context)

    if ajax:
        context['include_template'] = 'collections/list_page'
        context['ajax_include_title'] = True
        if context['ajax_modal_only'] and context['ajax_pagination_callback']:
            context['ajax_callback'] = context['ajax_pagination_callback']
        return render(request, 'ajax.html', context)
    return render(request, 'collections/list_view.html', context)

############################################################
# Add view

def add_view(request, name, collection, type=None, ajax=False, shortcut_url=None, **kwargs):
    context = collection.add_view.get_global_context(request)
    collection.add_view.check_permissions(request, context)
    _redirect_on_high_traffic(collection.add_view, request, ajax=ajax)

    context = _modification_view(context, name, collection.add_view, ajax)
    with_types = False
    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url
    context['type'] = None
    if type is not None and collection.types:
        if type not in collection.types:
            raise Http404
        with_types = True
        context['type'] = type
        collection.add_view.check_type_permissions(request, context, type=type)
        formClass = collection.types[type].get('form_class', collection.add_view.form_class)
    else:
        formClass = collection.add_view.form_class
    if str(_type(formClass)) == '<type \'instancemethod\'>':
        formClass = formClass(request, context)
    if request.method in ['GET', 'HEAD']:
        form = formClass(request=request, ajax=ajax, collection=collection, allow_next=collection.add_view.allow_next) if not with_types else formClass(request=request, ajax=ajax, collection=collection, type=type, allow_next=collection.add_view.allow_next)
    elif request.method == 'POST':
        form = formClass(request.POST, request.FILES, request=request, ajax=ajax, collection=collection, allow_next=collection.add_view.allow_next) if not with_types else formClass(request.POST, request.FILES, request=request, ajax=ajax, collection=collection, type=type, allow_next=collection.add_view.allow_next)
        if form.is_valid():
            instance = form.save(commit=False)
            instance = collection.add_view.before_save(request, instance, type=type)
            instance.save()
            if collection.add_view.savem2m:
                form.save_m2m()

            # For collectibles per owner or account + as_profile_tabs, update cache
            if (collection.name != 'account'
                and (((collection.name in context['collectible_collections'].get('owner', {})
                       or collection.name in context['collections_in_profile_tabs'])
                      and not instance.real_owner.preferences.cached_tabs_with_content.get(collection.name, False))
                     or (collection.name in context['collectible_collections'].get('account', {})
                         and not instance.real_owner.preferences.cached_tabs_with_content.get(
                             'account', {}).get('tabs_per_account', {}).get(collection.name, False)))):
                instance.real_owner.preferences.force_update_cache('tabs_with_content')

            instance = collection.add_view.after_save(request, instance, type=type)
            next_value = form.cleaned_data.get('next', None)
            if collection.add_view.allow_next and next_value:
                raise HttpRedirectException(next_value)
            raise HttpRedirectException(addParametersToURL(
                collection.add_view.redirect_after_add(request, instance, ajax),
                parameters={
                    'next': next_value,
                    'next_title': form.cleaned_data.get('next_title', ''),
                } if next_value else {}))

    context['forms'] = { u'add_{}'.format(collection.name): form }
    context['share_image'] = _get_share_image(context, collection.add_view)
    context['ajax_callback'] = collection.add_view.ajax_callback
    context['collection'] = collection

    setJavascriptFormContext(
        form=form,
        form_selector=u'[data-form-name=\\"add_{}\\"]'.format(collection.name),
        context=context,
        cuteforms=[collection.add_view.filter_cuteform],
        ajax=ajax,
    )

    # Alert
    if collection.add_view.alert_duplicate:
        form.beforefields = mark_safe(u'{}{}'.format(
            getattr(form, 'beforefield', ''), HTMLAlert(
                message=_('Make sure the {thing} you\'re about to add doesn\'t already exist.').format(
                    thing=_(collection.title.lower())),
                button={ 'url': context['list_url'], 'verbose': unicode(collection.plural_title) },
            )))

    # Title and prefixes
    title_prefixes, h1 = collection.add_view.get_h1_title(request, context, type=type)
    _add_h1_and_prefixes_to_context(collection.add_view, context, title_prefixes, h1, get_page_title_parameters={
        'type': type, })

    if not getattr(form, 'submit_title', None):
        form.submit_title = collection.add_sentence

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

    _redirect_on_high_traffic(collection.edit_view, request, ajax=ajax)

    context['is_reported'] = 'is_reported' in request.GET
    context['is_suggestededit'] = 'is_suggestededit' in request.GET
    context = _modification_view(context, name, collection.edit_view, ajax)
    queryset = collection.edit_view.get_queryset(collection.queryset, _get_filters(request.GET, extra_filters), request)
    instance = get_one_object_or_404(queryset, **collection.edit_view.get_item(request, pk))
    context['type'] = None
    collection.edit_view.check_owner_permissions(request, context, instance)
    if context['is_translate']:
        formClass = collection.edit_view.translate_form_class
        context['icontitle'] = 'translate'
    elif collection.types:
        type = instance.type
        context['type'] = type
        collection.edit_view.check_type_permissions(request, context, type=type, item=instance)
        formClass = collection.types[type].get('form_class', collection.edit_view.form_class)
    else:
        formClass = collection.edit_view.form_class
    if str(_type(formClass)) == '<type \'instancemethod\'>':
        formClass = formClass(request, context)
    allowDelete = collection.edit_view.allow_delete
    if str(_type(allowDelete)) == '<type \'instancemethod\'>':
        allowDelete = allowDelete(instance, request, context)
    allowDelete = not context['is_translate'] and allowDelete and 'disable_delete' not in request.GET
    # Delete form
    if allowDelete and request.method == 'POST' and u'delete_{}'.format(collection.name) in request.POST:
        formDelete = ConfirmDelete(request.POST, request=request, instance=instance, collection=collection)
        if formDelete.is_valid():
            collection.edit_view.before_delete(request, instance, ajax)
            redirectURL = collection.edit_view.redirect_after_delete(request, instance, ajax)
            instance_owner = request.user if instance.owner_id == request.user.id else instance.real_owner
            instance.delete()

            # For collectibles per owner or account + as_profile_tabs, update cache
            if (collection.name != 'account'
                and (collection.name in context['collectible_collections'].get('owner', {})
                     or collection.name in context['collectible_collections'].get('account', {})
                     or collection.name in context['collections_in_profile_tabs'])):
                instance_owner.preferences.force_update_cache('tabs_with_content')

            collection.edit_view.after_delete(request)
            raise HttpRedirectException(redirectURL)
        else:
            form = formClass(instance=instance, request=request, ajax=ajax, collection=collection, allow_next=collection.edit_view.allow_next)
    # Edit form
    elif request.method == 'POST':
        form = formClass(request.POST, request.FILES, instance=instance, request=request, ajax=ajax, collection=collection, allow_next=collection.edit_view.allow_next)
        if form.is_valid():
            instance = form.save(commit=False)
            instance = collection.edit_view.before_save(request, instance)
            instance.save()
            if collection.edit_view.savem2m and not context['is_translate']:
                form.save_m2m()
            instance = collection.edit_view.after_save(request, instance)
            next_value = form.cleaned_data.get('next', None)
            if collection.edit_view.allow_next and next_value:
                raise HttpRedirectException(next_value)
            raise HttpRedirectException(addParametersToURL(
                collection.edit_view.redirect_after_edit(request, instance, ajax),
                parameters={
                    'next': next_value,
                    'next_title': form.cleaned_data.get('next_title', ''),
                } if next_value else {}))
        elif allowDelete:
            formDelete = ConfirmDelete(initial={
                'thing_to_delete': instance.pk,
            }, request=request, instance=instance, collection=collection)
    else:
        form = formClass(instance=instance, request=request, ajax=ajax, collection=collection, allow_next=collection.edit_view.allow_next)
        if allowDelete:
            formDelete = ConfirmDelete(initial={
                'thing_to_delete': instance.pk,
            }, request=request, instance=instance, collection=collection)

    setJavascriptFormContext(
        form=form,
        form_selector=u'[data-form-name=\\"edit_{}\\"]'.format(collection.name),
        context=context,
        cuteforms=[collection.edit_view.filter_cuteform],
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
    context['collection'] = collection
    context['ajax_callback'] = collection.edit_view.ajax_callback
    context['forms'][u'edit_{}'.format(collection.name)] = form

    if allowDelete:
        formDelete.submit_title = instance.delete_sentence
        formDelete.form_title = u'{}: {}'.format(instance.delete_sentence, unicode(instance))

        # Alert
        formDelete.beforefields = mark_safe(u'{}{}'.format(
            getattr(form, 'beforefield', ''), HTMLAlert(
                type='danger',
                message=unicode(_('You can\'t cancel this action afterwards.')),
            )))

        if 'js_variables' not in context or not context['js_variables']:
            context['js_variables'] = OrderedDict()
        context['js_variables']['show_cascade_before_delete'] = collection.edit_view.show_cascade_before_delete
        context['forms'][u'delete_{}'.format(collection.name)] = formDelete

    # Title and prefixes
    title_prefixes, h1 = collection.edit_view.get_h1_title(
        request, context, context['item'], type=context['type'], is_translate=context['is_translate'])
    _add_h1_and_prefixes_to_context(collection.edit_view, context, title_prefixes, h1, get_page_title_parameters={
        'item': context['item'], 'type': context['type'], 'is_translate': context['is_translate'] })

    if not getattr(form, 'submit_title', None):
        form.submit_title = collection.edit_sentence

    collection.edit_view.extra_context(context)
    if ajax:
        context['include_template'] = 'collections/modification_view'
        context['extends'] = 'ajax.html'
        context['ajax'] = True
    return render(request, 'collections/modification_view.html', context)
