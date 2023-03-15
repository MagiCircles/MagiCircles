from __future__ import division
import math, string
from collections import OrderedDict
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
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
    getDescriptionFromItem,
    isPreset,
    MagiQueryDict,
    unifyMergedFields,
    reverseOrdering,
    plainOrdering,
    getOwnerFromItem,
    markSafeFormat,
)
from magi.forms import ConfirmDelete, filter_ids

############################################################
# Internal utils

def _redirect_on_high_traffic(view, request, ajax=False):
    if (getattr(django_settings, 'HIGH_TRAFFIC', False)
        and view.disable_on_high_traffic
        and not request.user.is_authenticated()):
        raise HttpRedirectException(u'{}/hightraffic/'.format('/ajax' if ajax else ''))

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
    if context.get('preset', None):
        context['show_title'] = True
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
    request._item_view_pk = pk
    request.show_collect_button = collection.item_view.show_collect_button
    filters = MagiQueryDict(request.GET)
    filters.update(extra_filters)
    queryset = collection.item_view.get_queryset(collection.queryset, filters, request)
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
    context['page_description'] = getDescriptionFromItem(context['item'])

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
    context['uses_deprecated_to_fields'] = collection.item_view.uses_deprecated_to_fields()

    if context['item_template'] == 'default':
        context['top_illustration'] = collection.item_view.top_illustration

        if context['uses_deprecated_to_fields']:
            # Call deprecated to_fields if to_fields has been overrided
            context['item_fields'] = collection.item_view.to_fields(context['item'], request=request)
        else:
            context['item_fields'] = collection.item_view.to_magifields(context['item'], context)

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
    # Buttons are displayed by magifields (deprecated or magifields) or when buttons are displayed
    # in one line. They're also loaded if a user uses a custom template, so they can be displayed as they want
    # within their template.
    if (context['uses_deprecated_to_fields']
        or collection.item_view.show_item_buttons_in_one_line
        or context['item_template'] != 'default'):
        context['item'].show_item_buttons_as_icons = collection.item_view.show_item_buttons_as_icons
        context['item'].show_item_buttons_in_one_line = collection.item_view.show_item_buttons_in_one_line
        context['item'].show_item_buttons_justified = collection.item_view.show_item_buttons_justified
        context['item'].buttons_to_show = collection.item_view.buttons_per_item(request, context, context['item'])
        if ((collection.item_view.show_item_buttons_in_one_line or not context['uses_deprecated_to_fields'])
            and collection.item_view.show_item_buttons
            and [True for b in context['item'].buttons_to_show.values() if b['show'] and b['has_permissions']]):
            context['include_below_item'] = True # only used by 'default' template (deprecated or magifields)

    # Show owner
    context['annotations_below_template'] = []
    if not ajax and collection.item_view.show_owner:
        owner = getOwnerFromItem(context['item'])
        if owner:
            context['annotations_below_template'].append(
                markSafeFormat(_('Added by {username}'), username=markSafeFormat(
                    u'<a href="{}" target="_blank">{}</a>', owner.http_item_url, owner.username)))

    collection.item_view.extra_context(context)
    if ajax:
        context['ajax_include_title'] = True
        context['include_template'] = 'items/{}'.format(context['item_template'])
        return render(request, 'ajax.html', context)
    return render(request, 'collections/item_view.html', context)

############################################################
# Random view

def random_view(request, name, collection, ajax=False, extra_filters={}, shortcut_url=None, **kwargs):
    collection.list_view.check_random_permissions(request, {})
    filters = MagiQueryDict(request.GET)
    request.GET = filters
    filters.update(extra_filters)

    unifyMergedFields(collection, filters)
    collection.list_view.filter_form.set_filters_defaults_when_missing(collection, filters)

    queryset = collection.list_view.get_queryset(collection.queryset, filters, request)

    alt_view = collection.list_view.alt_views.get(filters.get('view', None), None)
    if alt_view and alt_view.get('filter_queryset', None):
        queryset = alt_view['filter_queryset'](queryset)

    filter_form = collection.list_view.filter_form(
        filters, request=request, ajax=ajax, collection=collection, preset=None, allow_next=False)
    if hasattr(filter_form, 'filter_queryset'):
        queryset = filter_form.filter_queryset(queryset, filters, request)

    try:
        random_item = queryset.order_by('?')[0]
    except IndexError:
        raise HttpRedirectException(collection.get_list_url(
            ajax=ajax, modal_only=ajax, parameters=filters,
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

    ######################
    # Permissions

    if (shortcut_url == ''
        and context.get('launch_date', None)
        and (not request.user.is_authenticated()
             or not request.user.hasPermission('access_site_before_launch'))):
        raise HttpRedirectException('/prelaunch/')

    collection.list_view.check_permissions(request, context)
    _redirect_on_high_traffic(collection.list_view, request, ajax=ajax)

    ######################
    # Filters

    filters = MagiQueryDict(request.GET)
    request.GET = filters
    filters.update(extra_filters)

    preset = None
    filled_filter_form = False
    filled_filter_form_before_preset = False
    filled_filter_form_excluding_view = False

    if collection.list_view.filter_form:

        # Find preset path, if any
        url = request.path[5:] if request.path.startswith('/ajax') else request.path
        template = u'/{}/{}/'.format(collection.plural_name, '{preset}')
        matches = matchesTemplate(template, url)
        preset_path = matches.get('preset', None) if matches else None

        # Confirm that the preset matches an existing preset
        if preset_path:
            if getattr(collection.list_view.filter_form, 'presets'):
                presets = collection.list_view.filter_form.get_presets()
                if preset_path in presets:
                    preset = preset_path
                    context['preset'] = preset

        # When there's a preset
        if preset:

            # 1. Is filled (before presets)?
            filled_filter_form_before_preset = filters.is_form_filled(collection, include_view=False)
            # 2. Add preset filters to filters
            collection.list_view.filter_form.update_filters_with_preset(preset, filters)
            # 3. Unify merged fields with their original fields
            unifyMergedFields(collection, filters)
            # 4. Is filled?
            filled_filter_form = filters.is_form_filled(collection)
            filled_filter_form_excluding_view = filters.is_form_filled(collection, include_view=False)

        # When there's no preset
        else:

            # 1. Unify merged fields with their original fields
            unifyMergedFields(collection, filters)
            # 2. Is filled?
            filled_filter_form = filters.is_form_filled(collection)
            # 3. Detect if filters match a preset, and redirect to preset if so
            if not ajax and filled_filter_form:
                preset = isPreset(collection, filters)
                if preset:
                    raise HttpRedirectException(collection.get_list_url(
                        preset=preset))
            filled_filter_form_excluding_view = filters.is_form_filled(collection, include_view=False)
            filled_filter_form_before_preset = filled_filter_form_excluding_view

        # Set default filters

        if filled_filter_form:
            collection.list_view.filter_form.set_filters_defaults_when_missing(collection, filters)

    ######################
    # Alt views

    context['view'] = None
    context['alt_view'] = None
    alt_views = collection.list_view.alt_views
    view = filters.get('view', None)
    if view in alt_views:
        context['view'] = view
        context['alt_view'] = alt_views[view]

    request.show_collect_button = collection.list_view.show_collect_button
    if context['alt_view'] and 'show_collect_button' in context['alt_view']:
        request.show_collect_button = context['alt_view']['show_collect_button']

    ######################
    # Display style (table/row)

    context['display_style'] = collection.list_view.display_style
    if context['alt_view'] and 'display_style' in context['alt_view']:
        context['display_style'] = context['alt_view']['display_style']
    context['display_style_table_classes'] = collection.list_view.display_style_table_classes
    context['display_style_table_fields'] = collection.list_view.display_style_table_fields
    if context['alt_view'] and 'display_style_table_fields' in context['alt_view']:
        context['display_style_table_fields'] = context['alt_view']['display_style_table_fields']

    ######################
    # Queryset

    queryset = collection.list_view.get_queryset(collection.queryset, filters, request)

    if context['alt_view'] and context['alt_view'].get('filter_queryset', None):
        queryset = context['alt_view']['filter_queryset'](queryset)

    ######################
    # Form

    if collection.list_view.filter_form:

        # Initialize form
        if filled_filter_form:
            context['filter_form'] = collection.list_view.filter_form(
                filters, request=request, ajax=ajax, collection=collection, preset=preset, allow_next=False)
        else:
            context['filter_form'] = collection.list_view.filter_form(
                request=request, ajax=ajax, collection=collection, preset=preset, allow_next=False)

        # Apply filters
        if hasattr(context['filter_form'], 'filter_queryset'):
            queryset = context['filter_form'].filter_queryset(queryset, filters, request)
        else:
            queryset = filter_ids(queryset, filters.get('ids', None))

    else:
        queryset = filter_ids(queryset, filters.get('ids', None))

    if preset and 'filter_form' in context:
        try:
            context['filter_form'].action_url = collection.list_view.get_clear_url(request)
        except AttributeError:
            pass

    ######################
    # Ordering

    ordering_fields = []
    is_reverse = True
    filtered_relevant_fields_to_show = None

    # Get default ordering fields + is_reverse
    if ('filter_form' in context
        and 'ordering' in context['filter_form'].fields
        and context['filter_form'].fields['ordering'].initial):
        default_ordering_fields = context['filter_form'].fields['ordering'].initial.split(',')
        if 'reverse_order' in context['filter_form'].fields:
            default_is_reverse = bool(context['filter_form'].fields['reverse_order'].initial)
        else:
            default_is_reverse = True
    else:
        default_ordering_fields = collection.list_view.default_ordering.split(',')
        default_is_reverse = False # dashes are assumed to already be in ordering fields

    # Specified in filters (with or without form)
    # + Check if it's allowed to order by that field
    if (filters.get('ordering', None)
        and ((collection.list_view.filter_form
              and filters['ordering'] in dict(
                  getattr(collection.list_view.filter_form, 'ordering_fields', [])))
             or (request.user.is_authenticated()
                 and request.user.hasPermission('order_by_any_field')))):
        ordering_fields = filters['ordering'].split(',')
        is_reverse = bool(filters.get('reverse_order', True)) # defaults have been added to filters earlier
        filtered_relevant_fields_to_show = getattr(
            collection.list_view.filter_form, 'ordering_show_relevant_fields', {}).get(filters['ordering'], None)

    # Default ordering
    else:
        ordering_fields = default_ordering_fields
        is_reverse = default_is_reverse

    # Check if it's the default ordering
    is_default_ordering = (
        (ordering_fields == default_ordering_fields and is_reverse == default_is_reverse)
        or (is_reverse != default_is_reverse and reverseOrdering(ordering_fields) == default_ordering_fields)
    )

    # Apply is_reverse
    if is_reverse:
        ordering = [
            field_name[1:] if field_name.startswith('-') else u'-' + field_name
            for field_name in ordering_fields
        ]
    else:
        ordering = ordering_fields

    # Apply order_by
    queryset = queryset.order_by(*ordering)

    context['ordering'] = ordering

    # Show relevant fields on ordering
    if filtered_relevant_fields_to_show is not None:
        ordering_fields_to_show = filtered_relevant_fields_to_show
    else:
        ordering_fields_to_show = plainOrdering(ordering)

    show_relevant_fields_on_ordering = collection.list_view.show_relevant_fields_on_ordering
    if context['alt_view'] and 'show_relevant_fields_on_ordering' in context['alt_view']:
        show_relevant_fields_on_ordering = context['alt_view']['show_relevant_fields_on_ordering']
    if 'hide_relevant_fields_on_ordering' in filters:
        show_relevant_fields_on_ordering = False
    if (show_relevant_fields_on_ordering and (not filled_filter_form_excluding_view or is_default_ordering)):
        show_relevant_fields_on_ordering = False
    # Hide fields already in the table
    if context['display_style'] == 'table':
        ordering_fields_to_show = [
            field_name for field_name in ordering_fields_to_show
            if field_name not in context['display_style_table_fields']
        ]

    if not ordering_fields_to_show:
        show_relevant_fields_on_ordering = False

    context['show_relevant_fields_on_ordering'] = show_relevant_fields_on_ordering
    context['uses_deprecated_to_fields'] = collection.list_view.uses_deprecated_to_fields()

    ######################
    # Finalize queryset

    # Hide items without value when order is not reversed (lower values first)
    # because it would otherwise show them first which can be confusing
    if len(ordering) == 1 and filled_filter_form_excluding_view:
        field_name = ordering[0][1:] if ordering[0].startswith('-') else ordering[0]
        field = modelGetField(collection.queryset.model, field_name)
        if (field and field.null
            and not ordering[0].startswith('-')):
            queryset = queryset.exclude(**{ u'{}__isnull'.format(field_name): True })

    # Distinct
    if collection.list_view.distinct:
        queryset = queryset.distinct()

    ######################
    # Total

    context['total_results'] = queryset.count()

    if context['total_results'] == 1:
        context['total_results_sentence'] = _('1 {object} matches your search:').format(
            object=collection.title.lower())
    else:
        context['total_results_sentence'] = _('{total} {objects} match your search:').format(
            total=context['total_results'], objects=collection.plural_title.lower(),
        )

    ######################
    # Pagination

    # Per line
    context['per_line'] = int(filters['max_per_line']) if 'max_per_line' in filters and int(filters['max_per_line']) < collection.list_view.per_line else collection.list_view.per_line
    if context['alt_view'] and 'per_line' in context['alt_view']:
        context['per_line'] = context['alt_view']['per_line']
    context['col_size'] = getColSize(context['per_line'])

    # Page size
    page_size = collection.list_view.page_size
    if context['alt_view'] and 'page_size' in context['alt_view']:
        page_size = context['alt_view']['page_size']
    # Make sure the page_size is aligned with per_line, unless headers are shown
    if filled_filter_form_excluding_view or not collection.list_view.show_section_header_on_change:
        page_size += (page_size % context['per_line'])
    # Page size specified in filters
    if 'page_size' in filters:
        try: page_size = int(filters.get('page_size'))
        except ValueError: pass
        if page_size > 500: page_size = 500
    context['page_size'] = page_size

    page = 0

    if filters.get('page', None):
        try:
            page = int(filters['page']) - 1
        except ValueError:
            page = 0
        if page < 0:
            page = 0

    unpaginated_queryset = queryset
    queryset = queryset[(page * page_size):((page * page_size) + page_size)]

    context['page'] = page + 1
    context['total_pages'] = int(math.ceil(context['total_results'] / page_size))
    context['is_last_page'] = context['page'] == context['total_pages']

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

    ######################
    # Set settings in context

    context['plural_name'] = collection.plural_name

    if 'filter_form' in context and not ajax:
        setJavascriptFormContext(
            form=context['filter_form'],
            form_selector='[id=\\"filter-form-{}\\"]'.format(collection.name),
            context=context,
            cuteforms=[collection.list_view.filter_cuteform],
            ajax=ajax,
        )

    # ajax_modal_only will display a link to see the other results instead of the pagination button
    context['ajax_modal_only'] = False
    if 'ajax_modal_only' in filters:
        context['ajax_modal_only'] = True
        context['filters_string'] = '&'.join([
            u'&'.join([ u'{}={}'.format(key, value) for value in values ])
            for key, values in filters.items_as_lists()
            if key != 'ajax_modal_only'
        ])
        context['remaining'] = context['total_results'] - page_size

    # ajax_show_top_buttons will still show top buttons at the top, first page only
    context['ajax_show_top_buttons'] = ajax and 'ajax_show_top_buttons' in filters and page == 0

    if shortcut_url is not None:
        context['shortcut_url'] = shortcut_url

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

    # Ajax items reloader
    if not ajax and collection.list_view.auto_reloader and collection.list_view.ajax:
        context['ajax_reload_url'] = context['next_page_url']
        context['reload_urls_start_with'] = [u'/{}/edit/'.format(collection.plural_name)];
        if collection.collectible_collections:
            context['reload_urls_start_with'] += [cc.get_add_url() for cc in collection.collectible_collections.values()]

    context['show_no_result'] = not ajax or context['ajax_modal_only'] or 'ajax_show_no_result' in filters
    context['show_search_results'] = collection.list_view.show_search_results and filled_filter_form_before_preset
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
    if context['display_style'] == 'table' and context['item_template'] == 'default_item_in_list':
        context['item_template'] = 'default_item_table_view'
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
    context['col_break'] = collection.list_view.col_break
    if context['alt_view'] and 'col_break' in context['alt_view']:
        context['col_break'] = context['alt_view']['col_break']
    context['ajax_item_popover'] = collection.list_view.ajax_item_popover
    context['item_view_enabled'] = collection.item_view.enabled
    context['ajax_item_view_enabled'] = context['item_view_enabled'] and collection.item_view.ajax and not context['ajax_item_popover']
    context['staff_only_view'] = collection.list_view.staff_required
    context['collection'] = collection

    # May be set to true below (go through each item)
    context['include_below_item'] = False
    context['include_below_item_as_row'] = False

    # Title and prefixes
    title_prefixes, h1 = collection.list_view.get_h1_title(
        request, context, view=context['view'], preset=preset)
    _add_h1_and_prefixes_to_context(collection.list_view, context, title_prefixes, h1)

    # Get started
    context['get_started'] = 'get_started' in filters
    if context['get_started']:
        context['show_small_title'] = False
        context['show_search_results'] = False
        context['before_template'] = 'include/getstarted'
        context['share_collection_sentence'] = _('Share your {things}!').format(
            things=unicode(collection.plural_title).lower())
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

    # Show item buttons
    context['show_item_buttons'] = collection.list_view.show_item_buttons
    if context['alt_view'] and 'show_item_buttons' in context['alt_view']:
        context['show_item_buttons'] = context['alt_view']['show_item_buttons']

    # Retrieve section header from previous page, if any, to avoid showing the
    # header multiple times when loading pages
    if not filled_filter_form_excluding_view and collection.list_view.show_section_header_on_change:
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

    ######################
    # Go through each item

    context['items'] = list(queryset)
    previous_item = None

    for i, item in enumerate(context['items']):

        # Add request to item (sometimes accessed in properties)
        item.request = request

        # Apply foreach_items (if any specified in collection)
        if collection.list_view.foreach_items:
            collection.list_view.foreach_items(i, item, context)

        # Retrieve relevant fields on ordering
        if show_relevant_fields_on_ordering:
            context['include_below_item'] = True
            context['include_below_item_as_row'] = True
            if context['uses_deprecated_to_fields']:
                item.relevant_fields_to_show = collection.list_view.ordering_fields(
                    item, only_fields=ordering_fields_to_show, request=request)
            else:
                item.relevant_fields_to_show = collection.list_view.to_magi_ordering_fields(
                    item, context, ordering_fields=ordering_fields_to_show)

        # Buttons per item
        item.buttons_to_show = collection.list_view.buttons_per_item(request, context, item)
        collection.set_buttons_auto_open(item.buttons_to_show)
        item.show_item_buttons_in_one_line = collection.list_view.show_item_buttons_in_one_line
        item.show_item_buttons_justified = collection.list_view.show_item_buttons_justified
        item.show_item_buttons_as_icons = collection.list_view.show_item_buttons_as_icons
        if context['alt_view'] and 'show_item_buttons_as_icons' in context['alt_view']:
            item.show_item_buttons_as_icons = context['alt_view']['show_item_buttons_as_icons']
        total_shown_buttons = len([True for b in item.buttons_to_show.values() if b['show'] and b['has_permissions']])
        if context['show_item_buttons'] and total_shown_buttons > 0:
            context['include_below_item'] = True
            if total_shown_buttons > 1 and len(context['display_style_table_fields']) > 4:
                context['include_below_item_as_row'] = True

        # Retrieve relevant fields for table display style
        if context['display_style'] == 'table':
            if context['uses_deprecated_to_fields']:
                item.table_fields = collection.list_view.table_fields(
                    item, only_fields=context['display_style_table_fields'],
                    force_all_fields=True, request=request)
            else:
                item.table_fields = collection.list_view.to_magi_table_fields(
                    item, context, table_fields=context['display_style_table_fields'])

        # If the user blocked whoever owns this item, it will be hidden with a button to unblock
        # If the user was blocked by whoever owns this item, it will be hidden and the user won't know
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

        # Calculate column
        item.new_row = False
        if not previous_item:
            item.column = 0
        else:
            item.column = previous_item.column + 1
            if item.column == (context['per_line'] - 1):
                item.new_row = True
            elif item.column == context['per_line']:
                item.column = 0

        # Show section headers
        if not filled_filter_form_excluding_view and collection.list_view.show_section_header_on_change:
            section_header = getattr(item, collection.list_view.show_section_header_on_change)
            if section_header != previous_section_header:
                item.show_section_header = section_header
                previous_section_header = section_header
                context['showing_section_headers'] = True
                if previous_item:
                    item.new_row = False
                    previous_item.new_row = True
                    item.column = 0
            else:
                item.show_section_header = False

        previous_item = item

    ######################
    # Table headers (only if there are items, otherwise no result will show)

    if context['display_style'] == 'table' and context['items']:
        if context['uses_deprecated_to_fields']:
            context['table_fields_headers'] = collection.list_view.table_fields_headers(
                context['display_style_table_fields'], view=context['view'])
            context['table_fields_headers_sections'] = collection.list_view.table_fields_headers_sections(
                view=context['view'])
        else:
            context['table_fields_headers'] = context['items'][0].table_fields.get_table_headers()
            context['table_fields_headers_sections'] = context['items'][0].table_fields.get_table_headers_sections()

    ######################
    # Extra context (from collection)

    collection.list_view.extra_context(context)

    ######################
    # Render template

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
    filters = MagiQueryDict(request.GET)
    filters.update(extra_filters)
    queryset = collection.edit_view.get_queryset(collection.queryset, filters, request)
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
