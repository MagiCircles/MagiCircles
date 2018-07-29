import string, datetime, random
from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _, string_concat, get_language
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.formats import dateformat
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError
from django.middleware import csrf
from django.http import Http404
from django.db.models import Count, Q, Prefetch, FieldDoesNotExist
from magi.views import indexExtraContext
from magi.utils import AttrDict, ordinalNumber, justReturn, propertyFromCollection, getMagiCollections, getMagiCollection, CuteFormType, CuteFormTransform, redirectWhenNotAuthenticated, custom_item_template, getAccountIdsFromSession, setSubField, hasPermission, hasPermissions, hasOneOfPermissions, jsv, staticImageURL
from magi.raw import please_understand_template_sentence
from magi.django_translated import t
from magi.middleware.httpredirect import HttpRedirectException
from magi.settings import (
    ACCOUNT_MODEL,
    SHOW_TOTAL_ACCOUNTS,
    PROFILE_TABS,
    FAVORITE_CHARACTERS,
    FAVORITE_CHARACTER_NAME,
    FAVORITE_CHARACTER_TO_URL,
    GET_GLOBAL_CONTEXT,
    DONATE_IMAGE,
    ON_USER_EDITED,
    ON_PREFERENCES_EDITED,
    ACCOUNT_TAB_ORDERING,
    FIRST_COLLECTION,
    GLOBAL_OUTSIDE_PERMISSIONS,
    HOME_ACTIVITY_TABS,
    LANGUAGES_CANT_SPEAK_ENGLISH,
)
from magi import models, forms

############################################################
# MagiCollection interface

class _View(object):
    """
    Class used inside MagiCollection for common variables inside views
    """

    def __init__(self, collection):
        self.collection = collection

    # Optional variables without default
    js_files = []
    extra_context = None
    shortcut_urls = []
      # ListView/AddView: List of URLs
      # AddView with types: List or (url, type) or list of URLs
      # ItemView/EditView: List of (url, pk) or list of URLs

    # Optional variables with default values
    ajax_callback = None
    enabled = True
    logout_required = False
    staff_required = property(propertyFromCollection('staff_required'))
    permissions_required = property(propertyFromCollection('permissions_required'))
    one_of_permissions_required = property(propertyFromCollection('one_of_permissions_required'))
    ajax = True

    def get_global_context(self, request):
        return GET_GLOBAL_CONTEXT(request)

    def share_image(self, context, item):
        return self.collection.share_image(context, item)

    def get_queryset(self, queryset, parameters, request):
        return self.collection.get_queryset(queryset, parameters, request)

    def check_permissions(self, request, context):
        if not self.enabled:
            raise Http404
        if self.logout_required and request.user.is_authenticated():
            raise PermissionDenied()
        if self.authentication_required:
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
        if self.staff_required or self.prelaunch_staff_required:
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
            if not request.user.is_staff and not request.user.is_superuser:
                raise PermissionDenied()
        if self.permissions_required:
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
            if not hasPermissions(request.user, self.permissions_required):
                raise PermissionDenied()
        if self.one_of_permissions_required:
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
            if not hasOneOfPermissions(request.user, self.one_of_permissions_required):
                raise PermissionDenied()

    def check_owner_permissions(self, request, context, item):
        if item.owner_id:
            owner_only = getattr(self, 'owner_only', False)
            if owner_only:
                redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
                if item.owner_id != request.user.id and not request.user.is_superuser:
                    raise PermissionDenied()
            owner_or_staff_only = getattr(self, 'owner_or_staff_only', False)
            if owner_or_staff_only:
                redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
                if not request.user.is_staff and item.owner_id != request.user.id and not request.user.is_superuser:
                    raise PermissionDenied()
            owner_only_or_permissions_required = getattr(self, 'owner_only_or_permissions_required', [])
            if owner_only_or_permissions_required:
                redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
                if item.owner_id != request.user.id and not hasPermissions(request.user, owner_only_or_permissions_required):
                    raise PermissionDenied()
            owner_only_or_one_of_permissions_required = getattr(self, 'owner_only_or_one_of_permissions_required', [])
            if owner_only_or_one_of_permissions_required:
                redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
                if item.owner_id != request.user.id and not hasOneOfPermissions(request.user, owner_only_or_one_of_permissions_required):
                    raise PermissionDenied()

    #######################
    # Tools - not meant to be overriden

    def has_permissions(self, request, context, item=None):
        try:
            self.check_permissions(request, context)
            if item:
                self.check_owner_permissions(request, context, item)
        except (PermissionDenied, HttpRedirectException, Http404):
            return False
        return True

    def view_title(self):
        return self.view.replace('_', ' ').capitalize()

    def __unicode__(self):
        return u'{}: {}'.format(self.collection, self.view_title)

class MagiCollection(object):
    # Required variables
    @property
    def queryset(self): raise NotImplementedError('Queryset is required in a MagiCollection')

    # Optional variables without default
    icon = None
    image = None
    navbar_link_list = None
    navbar_link_list_divider_before = False
    navbar_link_list_divider_after = False
    types = None
    filter_cuteform = None
    collectible = None
    collectible_collections = {}

    # Optional variables with default values
    @property
    def name(self):
        return self.__class__.__name__.lower().replace('collection', '')

    @property
    def navbar_link_title(self):
        return self.plural_title

    def get_queryset(self, queryset, parameters, request):
        return queryset

    def _collectibles_queryset(self, view, queryset, request):
        # Select related total collectible for authenticated user
        if request.user.is_authenticated() and self.collectible_collections:
            if not view.show_collect_button:
                return queryset
            account_ids = getAccountIdsFromSession(request)
            for name, collection in self.collectible_collections.items():
                if (not collection.add_view.enabled
                    or (isinstance(view.show_collect_button, dict)
                        and not view.show_collect_button.get(name, True))
                    or not collection.add_view.has_permissions(request, {})):
                    continue
                item_field_name = getattr(collection.queryset.model, 'selector_to_collected_item',
                                          self.queryset.model.__name__.lower())
                fk_owner = collection.queryset.model.fk_as_owner if collection.queryset.model.fk_as_owner else 'owner'
                if collection.add_view.enabled and collection.add_view.quick_add_to_collection(request):
                    # Quick add
                    if not collection.queryset.model.fk_as_owner:
                        # With owner
                        fk_owner_ids = request.user.id
                    else:
                        # With fk_as_owner
                        fk_owner_ids = request.GET.get(u'add_to_{}'.format(name))
                        if fk_owner_ids:
                            # Get from request
                            fk_owner_ids = int(fk_owner_ids)
                        else:
                            # Get the first one in the list
                            if collection.queryset.model.fk_as_owner == 'account':
                                all_fk_owner_ids = getAccountIdsFromSession(request)
                            else:
                                all_fk_owner_ids = collection.queryset.model.owner_ids(request.user)
                            try:
                                fk_owner_ids = all_fk_owner_ids[0]
                            except IndexError:
                                fk_owner_ids = None
                            setattr(request, u'total_fk_owner_ids_{}'.format(name), len(all_fk_owner_ids))
                    setattr(request, u'add_to_{}'.format(name), fk_owner_ids)
                else:
                    fk_owner_ids = ','.join(unicode(i) for i in (
                        getAccountIdsFromSession(request)
                        if fk_owner == 'account'
                        else collection.queryset.model.owner_ids(request.user)))
                if not fk_owner_ids:
                    continue
                # Only join the total if show_collect_total is on OR quick add is on
                if (not collection.add_view.quick_add_to_collection(request)
                    and (not view.show_collect_total
                         or (isinstance(view.show_collect_total, dict)
                             and not view.show_collect_total.get(name, True)))):
                    pass
                else:
                    a = {
                        u'total_{}'.format(collection.name):
                        'SELECT COUNT(*) FROM {db_table} WHERE {item_field_name}_id = {item_db_table}.id AND {fk_owner}_id IN ({fk_owner_ids})'.format(
                            db_table=collection.queryset.model._meta.db_table,
                            item_field_name=item_field_name,
                            item_db_table=self.queryset.model._meta.db_table,
                            fk_owner=fk_owner, fk_owner_ids=fk_owner_ids,
                        )
                    }
                    queryset = queryset.extra(select=a)
        return queryset

    def to_form_class(self):
        class _Form(forms.AutoForm):
            class Meta:
                model = self.queryset.model
                fields = '__all__'
        self._form_class = _Form

    def form_class(self, request, context):
        return self._form_class

    def collectible_to_class(self, model_class):
        """
        Return a collectible class based on this model.
        You may override this function, but you're not really supposed to call it yourself.
        """
        parent_collection = self
        item_field_name = parent_collection.queryset.model.__name__.lower()
        item_field_name_id = u'{}_id'.format(item_field_name)

        class _CollectibleForm(forms.AutoForm):
            def __init__(self, *args, **kwargs):
                super(_CollectibleForm, self).__init__(*args, **kwargs)
                redirectWhenNotAuthenticated(self.request, {})
                # Editing
                if not self.is_creating:
                    del(self.fields[item_field_name])
                    if model_class.fk_as_owner:
                        del(self.fields[model_class.fk_as_owner])
                # Creating
                else:
                    # Collected item field
                    self.item_id = self.request.GET.get(item_field_name_id, None)
                    if not self.item_id:
                        raise HttpRedirectException(parent_collection.get_list_url())
                    self.fields[item_field_name].initial = self.item_id
                    # Owner field
                    if model_class.fk_as_owner:
                        self.fields[model_class.fk_as_owner].empty_label = None
                        fq = filtered_queryset = self.fields[model_class.fk_as_owner].queryset.filter(**{
                            model_class.selector_to_owner()[len(model_class.fk_as_owner) + 2:]:
                            self.request.user
                        })
                        if self.collection and self.collection.add_view.unique_per_owner:
                            # Exclude fk_as_owner that already have it
                            filtered_queryset = filtered_queryset.exclude(**{
                                u'{}__{}'.format(
                                    getattr(model_class, model_class.fk_as_owner).field.related_query_name(),
                                    item_field_name,
                                ): self.item_id
                            })
                        self.fields[model_class.fk_as_owner].choices = [
                            (c.id, unicode(c)) for c in filtered_queryset
                        ]
                        total_choices = len(self.fields[model_class.fk_as_owner].choices)
                        if total_choices == 0:
                            if self.collection and self.collection.add_view.unique_per_owner:
                                # If user still has fk_as_owners but no more to add from, redirect to edit
                                total_owners = len(fq if model_class.fk_as_owner != 'account' else getAccountIdsFromSession(self.request))
                                if total_owners:
                                    if total_owners == 1:
                                        existing = self.collection.edit_view.get_queryset(self.collection.queryset, {}, self.request).filter(**{
                                            item_field_name: self.item_id,
                                            model_class.selector_to_owner(): self.request.user,
                                        })
                                        try: raise HttpRedirectException(existing[0].ajax_edit_url if self.ajax else existing[0].edit_url) # Redirect to edit
                                        except IndexError: pass
                                    raise HttpRedirectException(u'{}?owner={}&{}={}&view=quick_edit&ajax_modal_only'.format(
                                        self.collection.get_list_url(ajax=self.ajax),
                                        self.request.user.id,
                                        item_field_name,
                                        self.item_id,
                                    ))
                            collection = model_class.owner_collection()
                            if collection:
                                raise HttpRedirectException(u'{}?next={}'.format(
                                    collection.get_add_url(ajax=self.ajax),
                                    self.request.get_full_path(),
                                ))
                        if total_choices > 0:
                            self.fields[model_class.fk_as_owner].initial = self.fields[model_class.fk_as_owner].choices[0][0]
                        if total_choices == 1:
                            collection = model_class.owner_collection()
                            self.beforefields = mark_safe(u'<p class="col-sm-offset-4">{}</p><br>'.format(
                                _('Adding to your {thing} {name}').format(
                                    thing=unicode(collection.title).lower(),
                                    name=self.fields[model_class.fk_as_owner].choices[0][1],
                                )))
                            self.fields[model_class.fk_as_owner] = forms.HiddenModelChoiceField(
                                queryset=filtered_queryset,
                                initial=self.fields[model_class.fk_as_owner].initial,
                                widget=forms.forms.HiddenInput,
                            )
                # Collectible: retrieve passed data or get item
                if self.collection and self.collection.add_view.add_to_collection_variables and not isinstance(self, forms.MagiFiltersForm):
                    self.collectible_variables = {}
                    missing = False
                    # add variables from GET parameters
                    for variable in self.collection.add_view.add_to_collection_variables:
                        get = u'{}_{}'.format(parent_collection.name, variable)
                        if get not in self.request.GET:
                            missing = True
                            break
                        else:
                            self.collectible_variables[variable] = self.request.GET[get]
                    # add variables from item
                    if missing:
                        if self.is_creating:
                            item = self.fields[item_field_name].to_python(self.item_id)
                        else:
                            item = getattr(self.instance, item_field_name)
                        for variable in self.collection.add_view.add_to_collection_variables:
                            self.collectible_variables[variable] = unicode(getattr(item, variable))

            class Meta:
                model = model_class
                fields = '__all__'
                save_owner_on_creation = not model_class.fk_as_owner
                hidden_foreign_keys = [item_field_name]

        class _CollectibleFilterForm(forms.MagiFiltersForm):
            def __init__(self, *args, **kwargs):
                super(_CollectibleFilterForm, self).__init__(*args, **kwargs)
                self.fields['owner'] = forms.forms.IntegerField(required=False, widget=forms.forms.HiddenInput)
                self.owner_filter = forms.MagiFilter(selector=model_class.selector_to_owner())
                # fk_as_owner
                if model_class.fk_as_owner:
                    self.fields[model_class.fk_as_owner] = forms.forms.IntegerField(required=False, widget=forms.forms.HiddenInput)
                    setattr(self, u'{}_filter'.format(model_class.fk_as_owner), forms.MagiFilter(
                        selector=model_class.fk_as_owner
                    ))
                # Collected item field
                self.fields[item_field_name] = forms.forms.IntegerField(required=False, widget=forms.forms.HiddenInput)

            class Meta:
                model = model_class
                fields = []

        class _CollectibleCollection(MagiCollection):
            name = model_class.collection_name
            queryset = model_class.objects.all().select_related(self.name)
            icon = self.icon
            image = self.image
            navbar_link = False
            reportable = False
            form_class = _CollectibleForm
            collectible_tab_name = property(lambda _s: _s.plural_title)

            def __init__(self, *args, **kwargs):
                super(_CollectibleCollection, self).__init__(*args, **kwargs)
                self.parent_collection = parent_collection

            def get_list_url_for_authenticated_owner(self, request, ajax, item=None, fk_as_owner=None):
                url = u'{url}?{parameters}'.format(
                    url=self.get_list_url(ajax=ajax),
                    parameters=u'&'.join([p for p in [
                        u'owner={}'.format(request.user.id) if not fk_as_owner else None,
                        u'{}={}'.format(
                            item_field_name,
                            getattr(item, item_field_name_id),
                        ) if item else None,
                        u'{}={}'.format(model_class.fk_as_owner, fk_as_owner) if fk_as_owner else None,
                    ] if p is not None]),
                )
                return url

            @property
            def title(self):
                return _('Collected {thing}').format(thing=parent_collection.title)

            @property
            def plural_title(self):
                return _('Collected {things}').format(things=parent_collection.plural_title)

            @property
            def add_sentence(self):
                return _(u'Add to your {thing}').format(thing=self.plural_title.lower())

            class ListView(MagiCollection.ListView):
                filter_form = _CollectibleFilterForm
                item_padding = '7px 0'
                col_break = 'sm'
                per_line = 6
                page_size = 30
                show_item_buttons = False
                show_add_button = justReturn(False)
                ajax_item_popover = True

                alt_views = MagiCollection.ListView.alt_views + [
                    ('quick_edit', {
                        'verbose_name': _('Quick edit'),
                        'template': 'default_item_table_view',
                        'display_style': 'table',
                        'display_style_table_fields': ['image'] + ([model_class.fk_as_owner] if model_class.fk_as_owner else []) + ['edit_button'],
                    }),
                ]

                def table_fields(self, item, *args, **kwargs):
                    image = getattr(item, 'image_url')
                    fields = super(_CollectibleCollection.ListView, self).table_fields(item, *args, extra_fields=(
                        [(('image', { 'verbose_name': unicode(item), 'value': image, 'type': 'image' })
                          if image else ('name', {
                                  'verbose_name': unicode(item), 'value': unicode(item), 'type': 'text',
                          }))]), **kwargs)
                    if (model_class.fk_as_owner and model_class.fk_as_owner in fields
                        and 'ajax_link' in fields[model_class.fk_as_owner]):
                        del(fields[model_class.fk_as_owner]['ajax_link'])
                    return fields

                def table_fields_headers(self, fields, view=None):
                    return []

                def extra_context(self, context):
                    if context['view'] == 'quick_edit':
                        context['include_below_item'] = True
                        context['show_item_buttons'] = True

            class ItemView(MagiCollection.ItemView):
                comments_enabled = False
                share_enabled = False

                def extra_context(self, context):
                    context['item_parent'] = getattr(context['item'], item_field_name)

                def to_fields(self, item, extra_fields=None, force_all_fields=False, *args, **kwargs):
                    if extra_fields is None: extra_fields = []
                    item_parent = getattr(item, item_field_name)
                    extra_fields += [
                        (item_field_name, {
                            'type': 'text_with_link',
                            'verbose_name': parent_collection.title,
                            'value': unicode(item_parent),
                            'icon': parent_collection.icon,
                            'image': parent_collection.image,
                            'link': item_parent.item_url,
                            'ajax_link': item_parent.ajax_item_url,
                            'link_text': unicode(_(u'Open {thing}')).format(thing=unicode(parent_collection.title).lower()),
                        }),
                    ]
                    fields = super(_CollectibleCollection.ItemView, self).to_fields(
                        item, *args, extra_fields=extra_fields, force_all_fields=force_all_fields, **kwargs)
                    if not force_all_fields and model_class.fk_as_owner and model_class.fk_as_owner in fields:
                        del(fields[model_class.fk_as_owner])
                    return fields

            class AddView(MagiCollection.AddView):
                alert_duplicate = False
                back_to_list_button = False
                max_per_user = 3000

                def extra_context(self, context):
                    # Display which item is being added using the image
                    add_form = context['forms'][u'add_{}'.format(self.collection.name)]
                    if hasattr(add_form, 'collectible_variables'):
                        image = add_form.collectible_variables.get('image_url')
                        if image:
                            context['imagetitle'] = image
                            context['imagetitle_size'] = 100
                            context['icontitle'] = None

                def redirect_after_add(self, request, item, ajax):
                    if ajax:
                        return '/ajax/successadd/'
                    return parent_collection.get_list_url()

            class EditView(MagiCollection.EditView):
                back_to_list_button = False
                allow_delete = True
                show_cascade_before_delete = False

                def get_item(self, request, pk):
                    if pk == 'unique':
                        d = { item_field_name: request.GET.get(item_field_name_id) }
                        if model_class.fk_as_owner:
                            d[model_class.selector_to_owner()[:-7]] = request.GET.get(model_class.fk_as_owner)
                        else:
                            d['owner'] = request.user
                        return d
                    return super(_CollectibleCollection.EditView, self).get_item(request, pk)

                def redirect_after_edit(self, request, item, ajax):
                    if ajax:
                        return '/ajax/successedit/'
                    return parent_collection.get_list_url()

                def redirect_after_delete(self, request, item, ajax):
                    if ajax:
                        return '/ajax/successdelete/'
                    return parent_collection.get_list_url()

        return _CollectibleCollection

    enabled = True
    navbar_link = True
    multipart = False

    staff_required = False
    permissions_required = []
    one_of_permissions_required = []

    reportable = True
    blockable = True
    report_edit_templates = {}
    report_delete_templates = {}
    report_allow_edit = True
    report_allow_delete = True

    translated_fields = None

    @property
    def plural_name(self):
        return '{}s'.format(self.name)

    @property
    def title(self):
        return string.capwords(self.name)

    @property
    def plural_title(self):
        return string.capwords(self.plural_name)

    def share_image(self, context, item):
        return self.image

    def to_fields(self, view, item, to_dict=True, only_fields=None, icons=None, images=None, force_all_fields=False, order=None, extra_fields=None, exclude_fields=None, request=None):
        if extra_fields is None: extra_fields = []
        if exclude_fields is None: exclude_fields = []
        if only_fields is None: only_fields = []
        if order is None: order = []
        if icons is None: icons = {}
        if images is None: images = {}
        name_fields = []
        many_fields = []
        collectible_fields = []
        # Fields from reverse
        for (field_name, url, verbose_name) in getattr(item, 'reverse_related', []):
            if only_fields and field_name not in only_fields:
                continue
            if field_name in exclude_fields:
                continue
            try:
                total = getattr(item, 'cached_total_{}'.format(field_name))
            except AttributeError:
                continue
            if callable(verbose_name):
                verbose_name = verbose_name()
            if total:
                many_fields.append((field_name, {
                    'verbose_name': unicode(verbose_name).replace('{total}', ''),
                    'type': 'text_with_link' if url else 'text',
                    'value': (u'{total} {items}'.format(total=total, items=_(verbose_name).lower())
                              if '{total}' not in unicode(verbose_name)
                              else unicode(verbose_name).format(total=total)),
                    'ajax_link': u'/ajax/{}/?{}={}&ajax_modal_only'.format(url, item.collection_name, item.pk),
                    'link': u'/{}/?{}={}'.format(url, item.collection_name, item.pk),
                    'link_text': _('View all'),
                    'icon': icons.get(field_name, None),
                    'image': images.get(field_name, None),
                }))
        model_fields = []
        # Fields from model
        for field in item._meta.fields:
            field_name = field.name
            if field_name in exclude_fields:
                continue
            if (field_name.startswith('_')
                or field_name in ['id']
                or (field_name == 'image' and 'image' not in only_fields)):
                continue
            if only_fields and field_name not in only_fields:
                continue
            value = None
            if field_name.startswith('i_'):
                field_name = field_name[2:]
                value = getattr(item, u't_{}'.format(field_name))
            if field_name.startswith('m_'):
                field_name = field_name[2:]
            if field_name.startswith('c_'):
                field_name = field_name[2:]
                value = getattr(item, u't_{}'.format(field_name)).values()
                if not value:
                    continue
            if field_name.startswith('d_'):
                field_name = field_name[2:]
                # Skip translated strings
                if self.translated_fields and field_name.endswith('s') and field_name[:-1] in self.translated_fields:
                    continue
                # Show dictionary
                value = getattr(item, u't_{}'.format(field_name)).values()
                value = mark_safe(u'<dl>{}</dl>'.format(u''.join([u'<dt>{verbose}</dt><dd>{value}</dd>'.format(**dt) for dt in value])))
                if not value:
                    continue
            if self.translated_fields and field.name in self.translated_fields:
                value = getattr(item, u't_{}'.format(field.name), None)
                if not value:
                    continue
                choices = dict(getattr(item, u'{name}S_CHOICES'.format(name=field.name.upper()), [])).keys()
                if field.name.startswith('m_'):
                    value = (False, value)
                else:
                    if (get_language() in choices
                        and not getattr(item, u'{}s'.format(field_name), {}).get(get_language(), None)):
                        if get_language() in LANGUAGES_CANT_SPEAK_ENGLISH:
                            continue
                        else:
                            value = mark_safe(u'<a href="https://translate.google.com/#en/{to}/{value}" target="_blank">{value} <i class="flaticon-link"></i></a>'.format(to=get_language(), value=value))
            is_foreign_key = (isinstance(field, models.models.ForeignKey)
                              or isinstance(field, models.models.OneToOneField))
            if not value and not is_foreign_key:
                try:
                    value = getattr(item, field_name, None)
                except AttributeError:
                    continue
                if value is None:
                    continue
            d = {
                'verbose_name': getattr(field, 'verbose_name', _(field_name.capitalize())),
                'value': value,
                'icon': icons.get(field_name, None),
                'image': images.get(field_name, None),
            }
            if is_foreign_key:
                cache = getattr(item, 'cached_' + field_name, None)
                if not cache:
                    continue
                link = getattr(cache, 'item_url')
                if link:
                    d['type'] = 'text_with_link'
                    d['value'] = getattr(cache, 'unicode', field_name)
                    d['link'] = link
                    d['ajax_link'] = getattr(cache, 'ajax_item_url')
                    d['link_text'] = unicode(_(u'Open {thing}')).format(thing=d['verbose_name'])
                    d['image'] = getattr(cache, 'image_url', None)
                else:
                    d['type'] = 'text'
                    d['value'] = getattr(cache, 'unicode', field_name)
            elif field.name.startswith('c_'): # original field name
                d['type'] = 'list'
            elif field.name.startswith('m_'): # original field name
                d['type'] = 'markdown'
            elif isinstance(field, models.models.ManyToManyField):
                d['type'] = 'text_with_link'
                d['value'] = getattr(item, 'cached_total_' + field_name).unicode
                d['link'] = u'/{}/?{}={}'.format(field_name, item.collection_name, item.pk)
                d['link_text'] = _('View all')
            elif isinstance(field, models.models.ImageField):
                image_url = getattr(item, u'{}_url'.format(field_name, None))
                if not image_url:
                    continue
                d['type'] = 'image_link'
                d['value'] = getattr(item, u'{}_thumbnail_url'.format(field_name))
                d['link'] = getattr(item, u'{}_2x_url'.format(field_name), None) or getattr(item, u'{}_original_url'.format(field_name))
                d['link_text'] = d['verbose_name']

            elif (isinstance(field, models.models.BooleanField)
                  or isinstance(field, models.models.NullBooleanField)):
                d['type'] = 'bool'
            elif (isinstance(field, models.models.DateField)
                  or isinstance(field, models.models.DateTimeField)):
                d['type'] = 'timezone_datetime'
                d['timezones'] = ['Local time']
                d['ago'] = True
            elif isinstance(field, models.models.FileField):
                d['type'] = 'link'
                d['link_text'] = t['Download']
                d['value'] = getattr(item, field_name + '_url')
                if not d['value']:
                    continue
            elif field_name == 'itunes_id':
                d['type'] = 'itunes'
            else:
                d['type'] = 'text'
            if d['type'] == 'text_with_link':
                many_fields.append((field_name, d))
            elif field_name in ['name', 'japanese_name', 'romaji_name', 'english_name', 'translated_name']:
                name_fields.append((field_name, d))
            else:
                model_fields.append((field_name, d))
        fields = name_fields + many_fields + model_fields + extra_fields

       # Re-order fields
        if order or force_all_fields:
            dict_fields = dict(fields)
            sorted_fields = OrderedDict()
            for field_name in (order or []):
                if field_name.startswith('i_') or field_name.startswith('c_'):
                    field_name = field_name[2:]
                if only_fields and field_name not in only_fields:
                    continue
                if field_name in dict_fields:
                    sorted_fields[field_name] = dict_fields[field_name]
                elif force_all_fields:
                    sorted_fields[field_name] = { 'verbose_name': '', 'type': 'text', 'value': '' }
            for field_name in (only_fields if only_fields else dict_fields.keys()):
                if field_name.startswith('i_') or field_name.startswith('c_'):
                    field_name = field_name[2:]
                if field_name not in sorted_fields:
                    sorted_fields[field_name] = dict_fields[field_name] if field_name in dict_fields else { 'verbose_name': '', 'type': 'text', 'value': '' }
            if to_dict:
                fields = sorted_fields
            else:
                fields = sorted_fields.items()
        elif to_dict:
            fields = OrderedDict(fields)
        return fields

    #######################
    # Buttons
    # Only for item_view and list_view

    item_buttons_classes = ['btn', 'btn-secondary', 'btn-lines']
    show_item_buttons = True
    show_item_buttons_justified = True
    show_item_buttons_as_icons = False
    show_item_buttons_in_one_line = True
    show_edit_button = True
    show_edit_button_superuser_only = False
    show_edit_button_permissions_only = []
    show_translate_button = True
    show_report_button = True
    show_collect_button = True # Can also be a dictionary when multiple collectibles
    show_collect_total = True

    def buttons_per_item(self, view, request, context, item):
        """
        Used to display buttons below item, only for ItemView and ListView.
        You may override this function, but you're not really supposed to call it yourself.
        Can be overriden per view.
        """
        buttons = OrderedDict([
            (button_name, {
                'show': False,
                'has_permissions': False,
                'title': button_name,
                'icon': False,
                'image': False,
                'url': False,
                'open_in_new_window': False,
                'ajax_url': False,
                'ajax_title': False, # By default will use title
                'classes': (view.item_buttons_classes
                            + (['btn-block'] if not view.show_item_buttons_in_one_line else [])),
            }) for button_name in self.collectible_collections.keys() + ['edit', 'translate', 'report']
        ])
        # Collectible buttons
        for name, collectible_collection in self.collectible_collections.items():
            if (not view.show_collect_button
                or (isinstance(view.show_collect_button, dict) and not view.show_collect_button.get(name, True))
                or not collectible_collection.add_view.enabled):
                del(buttons[name])
                continue
            extra_attributes = {}
            quick_add_to_collection = collectible_collection.add_view.quick_add_to_collection(request) if request.user.is_authenticated() else False
            url_to_collectible_add_with_item = lambda url: u'{url}?{item_name}_id={item_id}&{variables}'.format(
                url=url, item_name=self.name, item_id=item.id,
                variables=u'&'.join([
                    u'{}_{}={}'.format(self.name, variable, getattr(item, variable))
                    for variable in collectible_collection.add_view.add_to_collection_variables
                    if hasattr(item, variable)]),
                )
            buttons[name]['show'] = view.show_collect_button[name] if isinstance(view.show_collect_button, dict) else view.show_collect_button
            buttons[name]['title'] = collectible_collection.add_sentence
            show_total = view.show_collect_total.get(name, True) if isinstance(view.show_collect_total, dict) else view.show_collect_total
            if quick_add_to_collection:
                show_total = True
            if show_total:
                buttons[name]['badge'] = getattr(item, u'total_{}'.format(name), 0)
            buttons[name]['icon'] = 'add'
            buttons[name]['image'] = collectible_collection.image
            buttons[name]['ajax_title'] = u'{}: {}'.format(collectible_collection.add_sentence, unicode(item))
            if collectible_collection.add_view.unique_per_owner:
                extra_attributes['unique-per-owner'] = 'true'
            if quick_add_to_collection:
                extra_attributes['quick-add-to-collection'] = 'true'
                extra_attributes['parent-item'] = self.name
                extra_attributes['parent-item-id'] = item.id
                if collectible_collection.queryset.model.fk_as_owner:
                    add_to_id_from_request = getattr(request, u'add_to_{}'.format(collectible_collection.name), None)
                    if not add_to_id_from_request:
                        quick_add_to_collection = False
                        del(extra_attributes['quick-add-to-collection'])
                        del(extra_attributes['parent-item'])
                        del(extra_attributes['parent-item-id'])
                    else:
                        extra_attributes['quick-add-to-id'] = add_to_id_from_request
                        extra_attributes['quick-add-to-fk-as-owner'] = collectible_collection.queryset.model.fk_as_owner or 'owner'
            if show_total and collectible_collection.add_view.unique_per_owner and not quick_add_to_collection:
                if collectible_collection.queryset.model.fk_as_owner == 'account' and buttons[name]['badge'] >= len(getAccountIdsFromSession(request)):
                    edit_sentence = unicode(_('Edit your {thing}')).format(
                        thing=unicode(collectible_collection.title
                                      if len(getAccountIdsFromSession(request)) == 1
                                      else collectible_collection.plural_title).lower())
                    if buttons[name]['badge'] > 0:
                        extra_attributes['alt-message'] = buttons[name]['title']
                        buttons[name]['title'] = edit_sentence
                    else:
                        extra_attributes['alt-message'] = edit_sentence
            if show_total and collectible_collection.add_view.unique_per_owner and quick_add_to_collection:
                delete_sentence = unicode(_('Delete {thing}')).format(thing=unicode(collectible_collection.title).lower())
                if buttons[name]['badge'] > 0:
                    extra_attributes['alt-message'] = buttons[name]['title']
                    buttons[name]['title'] = delete_sentence
                else:
                    extra_attributes['alt-message'] = delete_sentence
            if (collectible_collection.add_view.authentication_required
                and not collectible_collection.add_view.staff_required
                and not request.user.is_authenticated()):
                buttons[name]['has_permissions'] = True
                buttons[name]['url'] = u'/signup/?next={url}&next_title={title}'.format(
                    url=url_to_collectible_add_with_item(collectible_collection.get_add_url()),
                    title=item.edit_sentence,
                )
            else:
                buttons[name]['has_permissions'] = collectible_collection.add_view.has_permissions(request, context)
                buttons[name]['url'] = url_to_collectible_add_with_item(collectible_collection.get_add_url())
                buttons[name]['ajax_url'] = url_to_collectible_add_with_item(collectible_collection.get_add_url(ajax=True))
                if collectible_collection.add_view.staff_required and not view.staff_required:
                    buttons[name]['classes'].append('staff-only')
            buttons[name]['extra_attributes'] = extra_attributes
        # Edit button
        if self.edit_view.enabled:
            buttons['edit']['show'] = view.show_edit_button
            buttons['edit']['title'] = item.edit_sentence
            buttons['edit']['icon'] = 'edit'
            if (self.edit_view.authentication_required
                and not self.edit_view.owner_only
                and not self.edit_view.owner_or_staff_only
                and not self.edit_view.owner_only_or_permissions_required
                and not self.edit_view.owner_only_or_one_of_permissions_required
                and not self.edit_view.staff_required
                and not self.edit_view.permissions_required
                and not self.edit_view.one_of_permissions_required
                and not request.user.is_authenticated()):
                buttons['edit']['has_permissions'] = True
                buttons['edit']['url'] = u'/signup/?next={url}&next_title={title}'.format(
                    url=item.edit_url,
                    title=item.edit_sentence,
                )
            else:
                buttons['edit']['has_permissions'] = self.edit_view.has_permissions(request, context, item=item)
                if self.types:
                    buttons['edit']['has_permissions'] = buttons['edit']['has_permissions'] and self.edit_view.has_type_permissions(request, context, type=item.type, item=item)
                if (((view.show_edit_button_superuser_only
                      and not request.user.is_superuser)
                     or view.show_edit_button_permissions_only
                     and (not request.user.is_authenticated()
                          or not hasPermissions(request.user, view.show_edit_button_permissions_only)))
                    and buttons['edit']['has_permissions']
                    and not item.is_owner(request.user)):
                    buttons['edit']['show'] = False
                buttons['edit']['url'] = item.edit_url
                if self.edit_view.ajax:
                    buttons['edit']['ajax_url'] = item.ajax_edit_url
                if (request.user.is_staff
                    and self.edit_view.staff_required
                    and not view.staff_required):
                    buttons['edit']['classes'].append('staff-only')
        # Translation button
        if self.translated_fields:
            buttons['translate'] = buttons['edit'].copy()
            buttons['translate']['has_permissions'] = self.edit_view.has_translate_permissions(request, context)

            if buttons['translate']['has_permissions'] and request.user.is_staff:
                for field in self.translated_fields:
                    if request.GET.get(u'missing_{}_translations'.format(field), None):
                        buttons['translate']['classes'] = [c for c in buttons['translate']['classes'] if c != 'staff-only']
                        break

            buttons['translate']['title'] = unicode(_('Edit {thing}')).format(thing=unicode(_('Translations')).lower())
            buttons['translate']['icon'] = 'translate'
            buttons['translate']['url'] = u'{}{}translate'.format(buttons['translate']['url'], '&' if '?' in buttons['translate']['url'] else '?')
            buttons['translate']['ajax_url'] = u'{}{}translate'.format(buttons['translate']['ajax_url'], '&' if '?' in buttons['translate']['ajax_url'] else '?')
            if 'ajax_url' in buttons['translate']['url']:
                buttons['translate']['ajax_url'] = u'{}{}translate'.format(buttons['translate']['ajax_url'], '&' if '?' in buttons['translate']['ajax_url'] else '?')
        # Report buttons
        if self.reportable:
            buttons['report']['show'] = view.show_report_button
            buttons['report']['title'] = item.report_sentence
            buttons['report']['icon'] = 'warning'
            buttons['report']['has_permissions'] = (not request.user.is_authenticated()
                                                    or item.owner_id != request.user.id)
            buttons['report']['url'] = item.report_url
            buttons['report']['open_in_new_window'] = True
        return buttons

    #######################
    # Tools - not meant to be overriden

    def get_list_url(self, ajax=False):
        return u'{}/{}/'.format('' if not ajax else '/ajax', self.plural_name)

    def get_add_url(self, ajax=False, type=None):
        if self.types and not type:
            type = self.types.keys[0]
        return u'{}/{}/add/{}'.format(
            '' if not ajax else '/ajax',
            self.plural_name,
            u'{}/'.format(type) if type else '',
        )

    @property
    def add_sentence(self):
        return _(u'Add {thing}').format(thing=self.title.lower())

    @property
    def edit_sentence(self):
        return _(u'Edit {thing}').format(thing=self.title.lower())

    @property
    def is_first_collection(self):
        return self.name == FIRST_COLLECTION

    @property
    def is_first_collection_parent(self):
        return getMagiCollection(FIRST_COLLECTION).parent_collection.name == self.name

    @property
    def all_views(self):
        return [self.list_view, self.item_view, self.add_view, self.edit_view]

    def __unicode__(self):
        return u'MagiCollection {}'.format(self.name)

    #######################
    # Collection Views

    class ListView(_View):
        view = 'list_view'
        # Optional variables without default
        filter_form = None
        ajax_pagination_callback = None
        foreach_items = None
        #def foreach_items(self, index, item, context):
        before_template = None
        after_template = None
        no_result_template = None

        def extra_context(self, context):
            pass

        # Optional variables with default values
        display_style = 'rows'
        display_style_table_fields = ['image', 'name']
        display_style_table_classes = ['table']
        per_line = 3
        col_break = 'md'
        page_size = 12
        item_padding = 20 # Only used with default item template
        ajax_item_popover = False
        hide_icons = False

        item_buttons_classes = property(propertyFromCollection('item_buttons_classes'))
        show_item_buttons = property(propertyFromCollection('show_item_buttons'))
        show_item_buttons_justified = property(propertyFromCollection('show_item_buttons_justified'))
        show_item_buttons_as_icons = property(propertyFromCollection('show_item_buttons_as_icons'))
        show_item_buttons_in_one_line = property(propertyFromCollection('show_item_buttons_in_one_line'))
        show_edit_button = property(propertyFromCollection('show_edit_button'))
        show_edit_button_superuser_only = property(propertyFromCollection('show_edit_button_superuser_only'))
        show_edit_button_permissions_only = property(propertyFromCollection('show_edit_button_permissions_only'))
        show_translate_button = property(propertyFromCollection('show_translate_button'))
        show_report_button = property(propertyFromCollection('show_report_button'))
        show_collect_button = property(propertyFromCollection('show_collect_button'))
        show_collect_total = property(propertyFromCollection('show_collect_total'))

        top_buttons_classes = ['btn', 'btn-lg', 'btn-block', 'btn-main']
        show_add_button_superuser_only = False
        show_add_button_permission_only = False
        authentication_required = False
        distinct = False
        add_button_subtitle = _('Become a contributor to help us fill the database')
        show_title = False
        full_width = False
        show_relevant_fields_on_ordering = True
        hide_sidebar = False
        item_template = 'default_item_in_list'
        item_blocked_template = None
        auto_reloader = True
        _alt_view_choices = None # Cache
        alt_views = []

        def get_queryset(self, queryset, parameters, request):
            return super(MagiCollection.ListView, self).get_queryset(self.collection._collectibles_queryset(self, queryset, request), parameters, request)

        def buttons_per_item(self, *args, **kwargs):
            return self.collection.buttons_per_item(self, *args, **kwargs)

        def to_fields(self, *args, **kwargs):
            return self.collection.to_fields(self, *args, **kwargs)

        ordering_fields = to_fields

        def table_fields(self, *args, **kwargs):
            return self.collection.item_view.to_fields(*args, **kwargs)

        def table_fields_headers(self, fields, view=None):
            headers = []
            for field_name in fields:
                try:
                    headers.append((field_name, self.collection.queryset.model._meta.get_field(field_name).verbose_name))
                except FieldDoesNotExist:
                    try:
                        headers.append((field_name, self.collection.queryset.model._meta.get_field(u'i_{}'.format(field_name)).verbose_name))
                    except FieldDoesNotExist:
                        try:
                            headers.append((field_name, self.collection.queryset.model._meta.get_field(u'c_{}'.format(field_name)).verbose_name))
                        except FieldDoesNotExist:
                            headers.append((field_name, field_name.replace('_', ' ').title()))
            return headers

        def table_fields_headers_sections(self, view=None):
            return []

        def show_add_button(self, request):
            return True

        @property
        def filter_cuteform(self):
            return self.collection.filter_cuteform

        @property
        def default_ordering(self):
            if hasattr(self.collection.queryset.model, 'creation'):
                return '-creation'
            return '-id'

        def top_buttons(self, request, context):
            """
            Used to display buttons at the beginning of the list view.
            You may override this function, but you're not really supposed to call it yourself.
            """
            buttons = OrderedDict()
            # Add buttons
            if self.collection.add_view.enabled:
                for_all_buttons = {
                    'show': self.show_add_button(request),
                    'has_permissions': self.collection.add_view.has_permissions(request, context),
                    'ajax_url': False, # Top add buttons should always open a full page
                    'open_in_new_window': False,
                    'classes': (
                        self.collection.list_view.top_buttons_classes
                        + (['staff-only'] if self.collection.add_view.staff_required and not self.staff_required else [])
                    ),
                    'title': self.collection.add_sentence,
                }
                if (((self.show_add_button_superuser_only
                      and not request.user.is_superuser)
                     or (self.show_add_button_permission_only
                         and not hasPermission(request.user, self.show_add_button_permission_only)))
                    and for_all_buttons['has_permissions']
                    and request.user.is_staff):
                    for_all_buttons['show'] = False
                if self.collection.types:
                    for (type, button) in self.collection.types.items():
                        if not button.get('show_button', True):
                            continue
                        if not self.collection.add_view.has_type_permissions(request, context, type=type):
                            continue
                        buttons[u'add_{}'.format(type)] = dict({
                            'url': self.collection.get_add_url(type=type),
                            'icon': button.get('icon', None),
                            'image': button.get('image', None),
                            'subtitle': button.get('title', type),
                        }, **for_all_buttons)
                else:
                    buttons['add'] = dict({
                        'url': self.collection.get_add_url(),
                        'icon': self.collection.icon,
                        'image': self.collection.image,
                        'subtitle': self.collection.list_view.add_button_subtitle,
                    }, **for_all_buttons)
            return buttons

        #######################
        # Tools - not meant to be overriden

        def get_page_title(self):
            return self.collection.plural_title

        @property
        def plain_default_ordering_list(self):
            return [o[1:] if o.startswith('-') else o for o in self.default_ordering.split(',')]

        @property
        def plain_default_ordering(self):
            return self.plain_default_ordering_list[0]

    class ItemView(_View):
        view = 'item_view'

        # Optional variables without default
        top_illustration = None

        def extra_context(self, context):
            pass

        reverse_url = None
        #def reverse_url(self, text):
        # Returns a dictionary that will be used with the queryset to get a single item

        # Optional variables with default values
        authentication_required = False
        owner_only = False
        owner_or_staff_only = False
        owner_only_or_permissions_required = []
        owner_only_or_one_of_permissions_required = []
        comments_enabled = True
        share_enabled = True
        full_width = False
        auto_reloader = True
        template = 'default'
        item_padding = 20 # Only used with default item template
        hide_icons = False

        @property
        def show_item_buttons(self):
            return False if self.template == 'default' else self.collection.show_item_buttons
        @property
        def item_buttons_classes(self):
            return self.collection.item_buttons_classes + (['btn-lg'] if self.template == 'default' else [])
        @property
        def show_item_buttons_as_icons(self):
            return True if self.template == 'default' else self.collection.show_item_buttons_as_icons
        show_edit_button = property(propertyFromCollection('show_edit_button'))
        show_edit_button_superuser_only = property(propertyFromCollection('show_edit_button_superuser_only'))
        show_edit_button_permissions_only = property(propertyFromCollection('show_edit_button_permissions_only'))
        show_translate_button = property(propertyFromCollection('show_translate_button'))
        show_report_button = property(propertyFromCollection('show_report_button'))
        show_collect_button = property(propertyFromCollection('show_collect_button'))
        show_collect_total = property(propertyFromCollection('show_collect_total'))
        # Note: if you use the 'default' template, the following 2 will be ignored:
        show_item_buttons_justified = property(propertyFromCollection('show_item_buttons_justified'))
        show_item_buttons_in_one_line = property(propertyFromCollection('show_item_buttons_in_one_line'))

        def get_queryset(self, queryset, parameters, request):
            return super(MagiCollection.ItemView, self).get_queryset(self.collection._collectibles_queryset(self, queryset, request), parameters, request)

        def to_fields(self, *args, **kwargs):
            return self.collection.to_fields(self, *args, **kwargs)

        def buttons_per_item(self, *args, **kwargs):
            return self.collection.buttons_per_item(self, *args, **kwargs)

        def share_image(self, context, item):
            if hasattr(item, 'http_image_url'):
                return item.http_image_url
            return self.collection.share_image(context, item)

        def get_item(self, request, pk):
            return { 'pk': pk }

        #######################
        # Tools - not meant to be overriden

        def get_page_title(self, item=None):
            if item:
                return u'{}: {}'.format(self.collection.title, unicode(item))
            return self.collection.title

    class AddView(_View):
        view = 'add_view'

        # Optional variables without default
        otherbuttons_template = None
        after_template = None
        max_per_user = None
        max_per_user_per_day = None
        max_per_user_per_hour = None

        def before_save(self, request, instance, type=None):
            return instance

        def after_save(self, request, instance, type=None):
            return instance

        def extra_context(self, context):
            pass

        # Optional variables with default values
        authentication_required = True
        savem2m = False
        allow_next = True
        alert_duplicate = True
        back_to_list_button = True
        unique_per_owner = False

        def quick_add_to_collection(self, request):
            return False # for collectibles only

        add_to_collection_variables = ['image_url']

        @property
        def filter_cuteform(self):
            return self.collection.filter_cuteform

        @property
        def multipart(self):
            return self.collection.multipart

        def form_class(self, request, context):
            if str(type(self.collection.form_class)) == '<type \'instancemethod\'>':
                return self.collection.form_class(request, context)
            return self.collection.form_class

        def redirect_after_add(self, request, item, ajax):
            if self.collection.item_view.enabled:
                return item.item_url if not ajax else item.ajax_item_url
            return self.collection.get_list_url(ajax)

        def check_type_permissions(self, request, context, type=None):
            pass

        #######################
        # Tools - not meant to be overriden

        def get_page_title(self):
            return self.collection.add_sentence

        def has_type_permissions(self, request, context, type=None):
            try:
                self.check_type_permissions(request, context, type=type)
            except (PermissionDenied, HttpRedirectException, Http404):
                return False
            return True

    class EditView(_View):
        view = 'edit_view'

        # Optional variables without default
        otherbuttons_template = None
        after_template = None

        def before_save(self, request, instance, type=None):
            return instance

        def after_save(self, request, instance, type=None):
            return instance

        def extra_context(self, context):
            pass

        # Optional variables with default values
        authentication_required = True
        allow_delete = False
        @property
        def owner_only(self):
            return not self.collection.reportable and not self.staff_required
        owner_or_staff_only = False
        @property
        def owner_only_or_permissions_required(self):
            return ['edit_reported_things'] if self.collection.reportable and not self.staff_required else []
        owner_only_or_one_of_permissions_required = []
        savem2m = False
        back_to_list_button = True
        show_cascade_before_delete = True

        def allow_cascade_delete_up_to(self, request):
            return 10

        @property
        def filter_cuteform(self):
            return self.collection.filter_cuteform

        @property
        def multipart(self):
            return self.collection.multipart

        def form_class(self, request, context):
            if str(type(self.collection.form_class)) == '<type \'instancemethod\'>':
                return self.collection.form_class(request, context)
            return self.collection.form_class

        def to_translate_form_class(self):
            self._translate_form_class = forms.to_translate_form_class(self)

        def translate_form_class(self, request, context):
            return self._translate_form_class

        def redirect_after_edit(self, request, item, ajax):
            if self.collection.item_view.enabled:
                return item.item_url if not ajax else item.ajax_item_url
            return self.collection.get_list_url(ajax)

        def before_delete(self, request, item, ajax):
            pass

        def redirect_after_delete(self, request, item, ajax):
            return self.collection.get_list_url(ajax)

        def get_item(self, request, pk):
            if pk == 'unique':
                return { 'owner': request.user }
            return { 'pk': pk }

        def check_translate_permissions(self, request, context):
            if not request.user.is_authenticated():
                raise PermissionDenied()
            if not hasPermission(request.user, 'translate_items'):
                raise PermissionDenied()

        def check_type_permissions(self, request, context, type=None, item=None):
            pass

        #######################
        # Tools - not meant to be overriden

        def get_page_title(self, item=None):
            if item:
                return u'{}: {}'.format(item.edit_sentence, unicode(item))
            return self.collection.edit_sentence

        def has_translate_permissions(self, request, context):
            try:
                self.check_translate_permissions(request, context)
            except (PermissionDenied, HttpRedirectException, Http404):
                return False
            return True

        def has_type_permissions(self, request, context, type=None, item=None):
            try:
                self.check_type_permissions(request, context, type=type, item=item)
            except (PermissionDenied, HttpRedirectException, Http404):
                return False
            return True

############################################################
############################################################
############################################################

############################################################
# Account Collection

class AccountCollection(MagiCollection):
    title = _('Account')
    plural_title = _('Accounts')
    navbar_link_title = _('Leaderboard')
    icon = 'leaderboard'
    queryset = ACCOUNT_MODEL.objects.all()
    report_allow_delete = False
    form_class = forms.AccountForm

    show_item_buttons = False
    show_item_buttons_justified = False

    def get_profile_account_tabs(self, request, context, account):
        """
        Ordered dict that:
        - MUST contain name, callback (except for about)
        - May contain icon, image, callback
        """
        tabs = {}
        if context['collectible_collections'] and 'account' in context['collectible_collections']:
            for collection_name, collection in context['collectible_collections']['account'].items():
                tabs[collection_name] = {
                    'name': collection.collectible_tab_name,
                    'icon': collection.icon,
                    'image': collection.image,
                    'callback': mark_safe(u'loadCollectionForAccount(\'{load_url}\', {callback})'.format(
                        load_url=collection.get_list_url_for_authenticated_owner(
                            request, ajax=True, item=None, fk_as_owner=account.id),
                        callback=collection.list_view.ajax_pagination_callback or 'undefined',
                    )),
                }
        tabs['about'] = {
            'name': _('About'),
            'icon': 'about',
        }
        ordered_tabs = OrderedDict()
        for name in ACCOUNT_TAB_ORDERING:
            if name in tabs:
                ordered_tabs[name] = tabs[name]
                del(tabs[name])
        for name, tab in tabs.items():
            ordered_tabs[name] = tab
        return ordered_tabs

    @property
    def report_edit_templates(self):
        templates = OrderedDict([
            ('Unrealistic Level', 'Your level is unrealistic, so we edited it. If this was a mistake, please upload a screenshot of your game to the details of your account to prove your level and change it back. Thank you for your understanding.'),
        ])
        for field in self.queryset.model._meta.fields:
            if not field.name.startswith('_') and field.name not in ['id', 'owner', 'creation', 'level', 'default_tab']:
                name = field.name
                if name.startswith('i_'):
                    name = name[2:]
                name = name.replace('_', ' ').title()
                if isinstance(field, models.models.fields.CharField):
                    templates[u'Inappropriate {}'.format(name)] = u'Your account\'s {} was inappropriate. {}'.format(name.lower(), please_understand_template_sentence)
        return templates

    def to_fields(self, view, item, icons=None, *args, **kwargs):
        if icons is None: icons = {}
        icons.update({
            'creation': 'date',
            'start_date': 'date',
            'level': 'max-level',
            'friend_id': 'id',
            'screenshot': 'screenshot',
        })
        return super(AccountCollection, self).to_fields(view, item, *args, icons=icons, **kwargs)

    class ListView(MagiCollection.ListView):
        item_template = 'defaultAccountItem'
        show_edit_button_superuser_only = True
        show_title = True
        per_line = 1
        add_button_subtitle = _('Create your account to join the community and be in the leaderboard!')

        show_item_buttons_as_icons = True
        item_buttons_classes = ['btn', 'btn-link']

        def show_add_button(self, request):
            return not getAccountIdsFromSession(request)

        @property
        def default_ordering(self):
            try:
                self.collection.queryset.model._meta.get_field('level')
                return '-level'
            except FieldDoesNotExist:
                return MagiCollection.ListView.default_ordering.__get__(self)

    class ItemView(MagiCollection.ItemView):
        template = 'defaultAccountItem'
        comments_enabled = False
        show_edit_button_superuser_only = True

        def to_fields(self, item, exclude_fields=None, *args, **kwargs):
            if not exclude_fields: exclude_fields = []
            exclude_fields += ['owner', 'level_on_screenshot_upload']
            fields = super(AccountCollection.ItemView, self).to_fields(item, *args, exclude_fields=exclude_fields, **kwargs)
            if hasattr(item, 'cached_leaderboard') and item.cached_leaderboard:
                fields['leaderboard'] = {
                    'verbose_name': _('Leaderboard position'),
                    'icon': 'trophy',
                }
                if item.cached_leaderboard > 3:
                    fields['leaderboard']['type'] = 'html'
                    fields['leaderboard']['value'] = u'<h4>#{}</h4>'.format(item.cached_leaderboard)
                else:
                    fields['leaderboard']['type'] = 'image_link'
                    fields['leaderboard']['link'] = '/accounts/'
                    fields['leaderboard']['link_text'] = u'#{}'.format(item.cached_leaderboard)
                    fields['leaderboard']['value'] = item.leaderboard_image_url
            if 'nickname' in fields:
                del(fields['nickname'])
            if 'default_tab' in fields:
                del(fields['default_tab'])
            return fields

    class AddView(MagiCollection.AddView):
        alert_duplicate = False
        allow_next = True
        max_per_user = 10
        simpler_form = None

        def form_class(self, request, context):
            form_class = super(AccountCollection.AddView, self).form_class(request, context)
            if self.simpler_form and 'advanced' not in request.GET:
                form_class = self.simpler_form
            return form_class

        def extra_context(self, context):
            super(AccountCollection.AddView, self).extra_context(context)
            if self.simpler_form:
                form_name = u'add_{}'.format(self.collection.name)
                if 'otherbuttons' not in context:
                    context['otherbuttons'] = {}
                if 'advanced' in context['request'].GET:
                    context['advanced'] = True
                    context['otherbuttons'][form_name] = mark_safe(u'<a href="?simple" class="btn btn-link">{}</a>'.format(_('Simple')))
                else:
                    context['otherbuttons'][form_name] = mark_safe(u'<a href="?advanced" class="btn btn-link">{}</a>'.format(_('Advanced')))

        def redirect_after_add(self, request, instance, ajax=False):
            if ajax: # Ajax is not allowed for profile url
                return '/ajax/successadd/'
            if FIRST_COLLECTION:
                collection = getMagiCollection(FIRST_COLLECTION)
                if collection:
                    return u'{}?get_started&add_to_{}={}'.format(collection.parent_collection.get_list_url(), collection.name, instance.id)
            return '{}#{}'.format(request.user.item_url, instance.id)

        def before_save(self, request, instance, type=None):
            if 'account_ids' in request.session:
                del request.session['account_ids']
            return instance

    class EditView(MagiCollection.EditView):
        allow_delete = True

        def allow_cascade_delete_up_to(self, request):
            return 25

        def redirect_after_edit(self, request, instance, ajax=False):
            if ajax:
                return '/ajax/successedit/'
            return '{}#{}'.format(request.user.item_url, instance.id)

        def before_delete(self, request, item, ajax):
            if 'account_ids' in request.session:
                del request.session['account_ids']

        def redirect_after_delete(self, request, item, ajax=False):
            if ajax:
                return '/ajax/successdelete/'
            return request.user.item_url

############################################################
# User Collection

class UserCollection(MagiCollection):
    title = _('Profile')
    plural_title = _('Players')
    navbar_link = False
    queryset = models.User.objects.all().select_related('preferences')
    report_allow_delete = False
    report_edit_templates = OrderedDict([
        ('Inappropriate profile picture', 'Your profile picture is inappropriate. ' + please_understand_template_sentence + ' To change your avatar, go to gravatar and upload a new image, then go to your settings on our website to re-enter your email address.'),
        ('Inappropriate image in profile description', 'An image on your profile description was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate link', 'A link on your profile description was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate profile description', 'Something you wrote on your profile was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate username', 'Your username was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate location', 'Your location was inappropriate. ' + please_understand_template_sentence),
    ])
    report_delete_templates = {
        'Inappropriate behavior towards other user(s)': 'We noticed that you\'ve been acting in an inappropriate manner towards other user(s), which doesn\'t correspond to what we expect from our community members. Your profile, accounts, activities and everything else you owned on our website has been permanently deleted, and we kindly ask you not to re-iterate your actions.',
        'Spam': 'We detected spam activities from your user profile. Your profile, accounts, activities and everything else you owned on our website has been permanently deleted, and we kindly ask you not to re-iterate your actions.',
    }

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        default_ordering = 'username'
        show_item_buttons = False
        show_edit_button_permissions_only = ['see_profile_edit_button']
        per_line = 6
        page_size = 30

        def get_queryset(self, queryset, parameters, request):
            queryset = super(UserCollection.ListView, self).get_queryset(queryset, parameters, request)
            if 'followers_of' in parameters:
                queryset = queryset.filter(preferences__following__username=parameters['followers_of']).distinct()
            if 'followed_by' in parameters:
                queryset = queryset.filter(followers__user__username=parameters['followed_by']).distinct()
            if 'liked_activity' in parameters:
                queryset = queryset.filter(Q(pk__in=(models.Activity.objects.get(pk=parameters['liked_activity']).likes.all())) | Q(activities__id=parameters['liked_activity'])).distinct()
            return queryset

        def extra_context(self, context):
            return context

    class ItemView(MagiCollection.ItemView):
        template = 'profile'
        js_files = ['profile']
        comments_enabled = False
        follow_enabled = True
        show_item_buttons = False
        show_item_buttons_justified = False
        item_buttons_classes = ['btn', 'btn-link']
        show_edit_button_permissions_only = ['see_profile_edit_button']
        ajax = False
        shortcut_urls = [
            ('me', 'me'),
        ]
        accounts_template = 'include/defaultAccountsForProfile'

        def buttons_per_item(self, request, context, item):
            buttons = super(UserCollection.ItemView, self).buttons_per_item(request, context, item)
            user = context['item']
            if request.user.is_authenticated() and user.id != request.user.id:
                buttons['block'] = {
                    'classes': self.item_buttons_classes,
                    'show': True,
                    'url': u'/block/{}/'.format(user.id),
                    'icon': 'block',
                    'title': _(u'Block {username}').format(username=user.username),
                    'has_permissions': True,
                }
            return buttons

        def get_item(self, request, pk):
            if pk == 'me':
                if request.user.is_authenticated():
                    pk = request.user.id
                else:
                    raise HttpRedirectException('/signup/')
            return { 'pk': pk }

        def reverse_url(self, text):
            return {
                'username': text,
            }

        def get_queryset(self, queryset, parameters, request):
            queryset = super(UserCollection.ItemView, self).get_queryset(queryset, parameters, request)
            if request.user.is_authenticated():
                queryset = queryset.extra(select={
                    'followed': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = {id} AND user_id = auth_user.id'.format(
                        table=models.UserPreferences._meta.db_table,
                        id=request.user.preferences.id,
                    ),
                })
                queryset = queryset.extra(select={
                    'is_followed_by': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = (SELECT id FROM {table} WHERE user_id = auth_user.id) AND user_id = {id}'.format(
                        table=models.UserPreferences._meta.db_table,
                        id=request.user.id,
                    ),
                })
            queryset = queryset.extra(select={
                'total_following': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = (SELECT id FROM {table} WHERE user_id = auth_user.id)'.format(
                    table=models.UserPreferences._meta.db_table,
                ),
                'total_followers': 'SELECT COUNT(*) FROM {table}_following WHERE user_id = auth_user.id'.format(
                    table=models.UserPreferences._meta.db_table,
                ),
            })
            queryset = queryset.select_related('preferences', 'favorite_character1', 'favorite_character2', 'favorite_character3')
            try:
                models.Account._meta.get_field('level')
                has_level = True
            except FieldDoesNotExist:
                has_level = False
            account_queryset = models.Account.objects.order_by('-level' if has_level else '-id')
            try:
                models.Account._meta.get_field('center')
                account_queryset = account_queryset.select_related('center')
            except FieldDoesNotExist: pass
            queryset = queryset.prefetch_related(Prefetch('accounts', queryset=account_queryset, to_attr='all_accounts'), Prefetch('links', queryset=models.UserLink.objects.order_by('-i_relevance'), to_attr='all_links'))
            return queryset

        def extra_context(self, context):
            user = context['item']
            request = context['request']
            context['is_me'] = user.id == request.user.id
            context['accounts_template'] = self.accounts_template
            account_collection = getMagiCollection('account')
            if 'js_variables' not in context:
                context['js_variables'] = {}
            afterjs = u'<script>'

            # Account fields, buttons and tabs
            afterjs += u'var account_tab_callbacks = {'
            if account_collection:
                for account in user.all_accounts:
                    # Fields
                    account.fields = account_collection.item_view.to_fields(account)
                    # Buttons
                    account.buttons_to_show = account_collection.item_view.buttons_per_item(request, context, account)
                    account.show_item_buttons_justified = account_collection.item_view.show_item_buttons_justified
                    account.show_item_buttons_as_icons = account_collection.item_view.show_item_buttons_as_icons
                    account.show_item_buttons_in_one_line = account_collection.item_view.show_item_buttons_in_one_line
                    # Tabs
                    account.tabs = account_collection.get_profile_account_tabs(request, context, account)
                    account.tabs_size = 100 / len(account.tabs) if account.tabs else 100
                    account.opened_tab = account.tabs.keys()[0] if account.tabs else None
                    open_tab_key = u'account{}'.format(account.id)
                    if account.default_tab and account.default_tab in account.tabs:
                        account.opened_tab = account.default_tab
                    if open_tab_key in request.GET and request.GET[open_tab_key] in account.tabs:
                        account.opened_tab = request.GET[open_tab_key]
                    afterjs += u'\'{account_id}\': {{'.format(account_id=account.id)
                    for tab_name, tab in account.tabs.items():
                        if 'callback' in tab and tab['callback']:
                            afterjs += u'\'{tab_name}\': {{\'callback\': {callback}, \'called\': false}},'.format(
                                tab_name=tab_name, callback=tab['callback'],
                            )
                    afterjs += u'},'
            afterjs += u'};'

            # Badges
            if 'badge' in context['all_enabled']:
                context['item'].latest_badges = list(context['item'].badges.filter(show_on_top_profile=True).order_by('-date', '-id')[:6])
                if len(context['item'].latest_badges) == 6:
                    context['more_badges'] = True
                context['item'].latest_badges = context['item'].latest_badges[:5]

            # Profile tabs
            context['show_total_accounts'] = SHOW_TOTAL_ACCOUNTS
            context['profile_tabs'] = PROFILE_TABS
            if context['collectible_collections'] and 'owner' in context['collectible_collections']:
                for collection_name, collection in context['collectible_collections']['owner'].items():
                    context['profile_tabs'][collection_name] = {
                        'name': collection.plural_title,
                        'icon': collection.icon,
                        'image': collection.image,
                        'callback': mark_safe(u'loadCollectionForOwner(\'{load_url}\', {callback})'.format(
                            load_url=collection.get_list_url(ajax=True),
                            callback=collection.list_view.ajax_pagination_callback or 'undefined',
                        )),
                    }

            context['profile_tabs_size'] = 100 / len(context['profile_tabs']) if context['profile_tabs'] else 100
            context['opened_tab'] = context['profile_tabs'].keys()[0] if context['profile_tabs'] else None
            if user.preferences.default_tab and user.preferences.default_tab in context['profile_tabs']:
                context['opened_tab'] = user.preferences.default_tab
            if 'open' in request.GET and request.GET['open'] in context['profile_tabs']:
                context['opened_tab'] = request.GET['open']
            afterjs += u'var tab_callbacks = {'
            for tab_name, tab in context['profile_tabs'].items():
                if 'callback' in tab and tab['callback']:
                    afterjs += u'\'{tab_name}\': {{\'callback\': {callback}, \'called\': false}},'.format(
                        tab_name=tab_name, callback=tab['callback'],
                    )
            afterjs += u'};'

            # Links
            context['item'].all_links = list(context['item'].all_links)
            meta_links = []
            already_linked = None
            if user.preferences.donation_link:
                for link in context['item'].all_links:
                    if link.url == user.preferences.donation_link:
                        already_linked = link
                        meta_links.append(link)
                        break
                if not already_linked:
                    meta_links.append(AttrDict({
                        'type': 'Website',
                        'value': user.preferences.donation_link_title,
                        'translate_type': True,
                        'flaticon': 'url',
                        'url': user.preferences.donation_link,
                    }))
            if FAVORITE_CHARACTERS:
                for i in range(1, 4):
                    if getattr(user.preferences, 'favorite_character{}'.format(i)):
                        name = (_(FAVORITE_CHARACTER_NAME) if FAVORITE_CHARACTER_NAME else _('{nth} Favorite Character')).format(nth=_(ordinalNumber(i)))
                        link = AttrDict({
                            'type': name,
                            't_type': name,
                            # May be used by FAVORITE_CHARACTER_TO_URL
                            'raw_value': getattr(user.preferences, 'favorite_character{}'.format(i)),
                            'value': user.preferences.localized_favorite_character(i),
                            'translate_type': False,
                            'image_url': user.preferences.favorite_character_image(i),
                        })
                        link.url = FAVORITE_CHARACTER_TO_URL(link)
                        meta_links.append(AttrDict(link))
            if user.preferences.location:
                latlong = '{},{}'.format(user.preferences.latitude, user.preferences.longitude) if user.preferences.latitude else None
                link = AttrDict({
                    'type': 'Location',
                    'value': user.preferences.location,
                    'translate_type': True,
                    'flaticon': 'pinpoint',
                    'url': u'/map/?center={}&zoom=10'.format(latlong) if 'map' in context['all_enabled'] and latlong else u'https://www.google.com/maps?q={}'.format(user.preferences.location),
                })
                meta_links.append(link)
            if context['is_me'] or user.preferences.language != request.LANGUAGE_CODE:
                meta_links.append(AttrDict({
                    'type': 'Language',
                    'value': user.preferences.t_language,
                    'translate_type': True,
                    'image_url': staticImageURL(user.preferences.language, folder='language', extension='png'),
                }))
            if user.preferences.birthdate:
                today = datetime.date.today()
                birthday = user.preferences.birthdate.replace(year=today.year)
                if birthday < today:
                    birthday = birthday.replace(year=today.year + 1)
                if user.preferences.show_birthdate_year:
                    value = u'{} ({})'.format(
                        user.preferences.birthdate,
                        _(u'{age} years old').format(age=user.preferences.age),
                    )
                else:
                    value = dateformat.format(user.preferences.birthdate, "F d")
                meta_links.append(AttrDict({
                    'type': 'Birthdate',
                    'value': value,
                    'translate_type': True,
                    'flaticon': 'birthday',
                    'url': 'https://www.timeanddate.com/countdown/birthday?iso={date}T00&msg={username}%27s+birthday'.format(date=dateformat.format(birthday, "Ymd"), username=user.username),
                }))
            context['item'].all_links = meta_links + [link for link in context['item'].all_links if link != already_linked]
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

            # Sentences
            activity_collection = getMagiCollection('activity')
            if activity_collection:
                if activity_collection.add_view.has_permissions(request, context):
                    context['js_variables']['show_add_activity_button'] = jsv(context['is_me'])
                    context['js_variables']['add_activity_sentence'] = jsv(activity_collection.add_sentence)
                    context['js_variables']['add_activity_subtitle'] = jsv(unicode(activity_collection.list_view.add_button_subtitle))
                else:
                    context['js_variables']['show_add_activity_button'] = jsv(False)
            if account_collection and account_collection.add_view.has_permissions(request, context):
                context['can_add_account'] = True
                context['add_account_sentence'] = account_collection.add_sentence
            context['share_sentence'] = _('Check out {username}\'s awesome collection!').format(username=context['item'].username)
            context['share_url'] = context['item'].http_item_url

            context['single_account_sentence'] = account_collection.title

            # Afterjs
            afterjs += u'</script>'
            context['afterjs'] = afterjs

    class AddView(MagiCollection.AddView):
        enabled = False

    class EditView(MagiCollection.EditView):
        staff_required = True
        one_of_permissions_required = [
            'edit_staff_status',
            'edit_roles',
            'edit_reported_things',
            'edit_donator_status',
            'mark_email_addresses_invalid',
            'edit_activities_post_language',
        ]
        form_class = forms.StaffEditUser
        ajax_callback = 'updateStaffEditUserForm'

        filter_cuteform = {
            'i_activities_language': {
                'image_folder': 'language',
            },
        }

        def check_owner_permissions(self, request, context, item):
            super(UserCollection.EditView, self).check_permissions(request, context)
            # Edit view is for staff only, but staff can't edit their own
            if item.is_owner(request.user) and not request.user.hasPermission('edit_roles'):
                raise PermissionDenied()

        def extra_context(self, context):
            if hasPermission(context['request'].user, 'edit_roles') and GLOBAL_OUTSIDE_PERMISSIONS:
                if 'afterfields' not in context:
                    context['afterfields'] = {}
                context['afterfields']['edit_user'] = mark_safe(u'<div class="alert alert-danger">If you are making {user} a new staff, or if you are revoking the staff status of {user}, make sure you also <b>manually grant or revoke</b> the following permissions: <ul>{permissions}</ul></div>'.format(
                    user=context['item'].username,
                    permissions=u''.join([u'<li>{}</li>'.format(
                        p if not u else u'<a href="{}" target="_blank">{} <i class="flaticon-link"></i></a>'.format(u, p),
                    ) for p, u in GLOBAL_OUTSIDE_PERMISSIONS.items()]),
                ))

        def after_save(self, request, instance):
            models.onUserEdited(instance)
            if ON_USER_EDITED:
                ON_USER_EDITED(instance)
            models.onPreferencesEdited(instance)
            if ON_PREFERENCES_EDITED:
                ON_PREFERENCES_EDITED(instance)
            return instance

        def redirect_after_edit(self, request, item, ajax):
            if ajax: # Ajax is not allowed
                return '/ajax/successedit/'
            return super(UserCollection.EditView, self).redirect_after_edit(request, item, ajax)

############################################################
# Staff Configuration Collection

class StaffConfigurationCollection(MagiCollection):
    enabled = False
    title = 'Configuration'
    plural_title = 'Configurations'
    queryset = models.StaffConfiguration.objects.all().select_related('owner')
    navbar_link_list = 'staff'
    icon = 'settings'
    form_class = forms.StaffConfigurationForm
    reportable = False
    blockable = False
    one_of_permissions_required = [
        'advanced_staff_configurations',
        'edit_staff_configurations',
        'translate_staff_configurations',
    ]

    filter_cuteform = {
        'has_value': {
            'type': CuteFormType.YesNo,
        },
        'with_translations': {
            'type': CuteFormType.YesNo,
        },
        'i_language': {
            'image_folder': 'language',
        },
    }

    class ListView(MagiCollection.ListView):
        add_button_subtitle = None
        item_template = 'default_item_table_view'
        display_style = 'table'
        display_style_table_fields = ['verbose_key', 'i_language', 'value', 'owner']
        display_style_table_classes = MagiCollection.ListView.display_style_table_classes + ['table-striped']
        before_template = 'include/beforeStaffConfigurations'
        filter_form = forms.StaffConfigurationFilters
        default_ordering = 'id'

        def get_queryset(self, queryset, parameters, request):
            queryset = super(StaffConfigurationCollection.ListView, self).get_queryset(queryset, parameters, request)
            # Translators can only see translatable configurations
            if not hasOneOfPermissions(request.user, ['edit_staff_configurations', 'advanced_staff_configurations']):
                queryset = queryset.exclude(Q(i_language__isnull=True) | Q(i_language=''))
            return queryset

        def table_fields_headers(self, fields, view=None):
            return []

        def table_fields(self, item, *args, **kwargs):
            fields = super(StaffConfigurationCollection.ListView, self).table_fields(item, *args, **kwargs)
            setSubField(fields, 'owner', key='value', value='Last updated by:')
            setSubField(fields, 'owner', key='link_text', value=item.cached_owner.unicode)
            setSubField(fields, 'value', key='type', value=item.field_type)
            setSubField(fields, 'value', key='value', value=item.representation_value)
            return fields

    class ItemView(MagiCollection.ItemView):
        enabled = False

    class AddView(MagiCollection.AddView):
        alert_duplicate = False
        permissions_required = ['advanced_staff_configurations']
        one_of_permissions_required = []

    class EditView(MagiCollection.EditView):
        owner_only = False

        def check_owner_permissions(self, request, context, item):
            super(StaffConfigurationCollection.EditView, self).check_owner_permissions(request, context, item)
            # Translators don't have permissions to edit non translatable configurations
            if (not hasOneOfPermissions(request.user, ['edit_staff_configurations', 'advanced_staff_configurations'])
                and not item.i_language):
                raise PermissionDenied()

        def form_class(self, request, context):
            if hasPermission(request.user, 'advanced_staff_configurations'):
                return forms.StaffConfigurationForm
            return forms.StaffConfigurationSimpleEditForm

        def redirect_after_edit(self, request, item, ajax):
            if ajax:
                return '/ajax/successedit/'
            return super(StaffConfigurationCollection.EditView, self).redirect_after_edit(request, item, ajax)

############################################################
# Staff Details Collections

class StaffDetailsCollection(MagiCollection):
    title = 'Staff profile'
    plural_title = 'Staff profiles'
    queryset = models.StaffDetails.objects.all().select_related('owner')
    navbar_link_list = 'staff'
    icon = 'id'
    translated_fields = ('hobbies', 'favorite_food')
    reportable = False
    blockable = False
    form_class = forms.StaffDetailsForm
    multipart = True

    class ListView(MagiCollection.ListView):
        one_of_permissions_required = ['edit_own_staff_profile', 'translate_items', 'edit_staff_details']
        add_button_subtitle = None
        filter_form = forms.StaffDetailsFilterForm
        hide_sidebar = True

        def get_queryset(self, queryset, parameters, request):
            queryset = super(StaffDetailsCollection.ListView, self).get_queryset(queryset, parameters, request)
            if not hasOneOfPermissions(request.user, ['translate_items', 'edit_staff_details']):
                try:
                    sd = models.StaffDetails.objects.get(owner=request.user)
                    raise HttpRedirectException(sd.edit_url)
                except ObjectDoesNotExist:
                    raise HttpRedirectException(self.collection.get_add_url())
            return queryset

    class ItemView(MagiCollection.ItemView):
        enabled = False

    class AddView(MagiCollection.AddView):
        alert_duplicate = False
        max_per_user = 1
        one_of_permissions_required = ['edit_own_staff_profile']
        js_files = ['staffdetails']
        ajax_callback = 'updateStaffDetailsForm'

    class EditView(MagiCollection.EditView):
        one_of_permissions_required = ['edit_own_staff_profile', 'translate_items', 'edit_staff_details']
        owner_only = False
        owner_only_or_permissions_required = ['edit_staff_details']
        js_files = ['staffdetails']
        ajax_callback = 'updateStaffDetailsForm'

        def redirect_after_edit(self, request, item, ajax):
            if ajax:
                return '/ajax/successedit/'
            if not hasOneOfPermissions(request.user, ['translate_items', 'edit_staff_details']):
                return '/successedit/'
            return super(StaffDetailsCollection.EditView, self).redirect_after_edit(request, item, ajax)

        def check_owner_permissions(self, request, context, item):
            if not context.get('is_translate', False):
                super(StaffDetailsCollection.EditView, self).check_owner_permissions(request, context, item)

############################################################
# Activities Collection

class ActivityCollection(MagiCollection):
    title = _('Activity')
    plural_title = _('Activities')
    plural_name = 'activities'
    queryset = models.Activity.objects.all()
    navbar_link = False
    icon = 'comments'

    report_edit_templates = OrderedDict([
        ('Incorrect/missing tag', 'Your activity\'s tags have been changed. One or more of the activity\'s tags didn\'t reflect its content, or one or more tags were missing.'),
        ('Wrong language', 'The language you specified for this activity didn\'t reflect its content so it has been changed.'),
        ('Inappropriate image', 'An image in this activity you posted was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate content', 'Something you wrote in this activity was inappropriate. ' + please_understand_template_sentence),
        ('False information', 'Something you wrote in this activity is invalid or doesn\'t have enough available proof to be considered true.'),
        ('Illegal content', 'Something you shared in this activity was illegal so it has been edited.'),
        ('Uncredited fanart', 'You shared an image without the artist\'s permission, so it has been edited. Make sure you only post official art, or ask for permission to the artist and credit them.'),
    ])

    report_delete_templates = OrderedDict([
        ('Troll activity', 'This activity has been detected as being deliberately provocative with the intention of causing disruption or argument and therefore has been deleted. We kindly ask you not to re-iterate your actions and be respectful towards our community.'),
        ('Illegal content', 'Something you shared in this activity was illegal so it has been deleted.'),
        ('Uncredited fanart', 'You shared an image without the artist\'s permission, so your activity has been deleted. Make sure you only post official art, or ask for permission to the artist and credit them.'),
        ('Inappropriate activity', 'This activity was inappropriate. ' + please_understand_template_sentence),
        ('False information', 'Something you wrote in this activity is invalid or doesn\'t have enough available proof to be considered true.'),
        ('Spam activity', 'This activity has been detected as spam. We do not tolerate such behavior and kindly ask you not to re-iterate your actions or your entire profile might get deleted next time.'),
    ])

    def _get_queryset_for_list_and_item(self, queryset, parameters, request):
        if request.user.is_authenticated():
            queryset = queryset.extra(select={
                'liked': 'SELECT COUNT(*) FROM {activity_table_name}_likes WHERE activity_id = {activity_table_name}.id AND user_id = {user_id}'.format(
                    activity_table_name=models.Activity._meta.db_table,
                    user_id=request.user.id,
                ),
            })
        return queryset

    filter_cuteform = {
        'i_language': {
            'image_folder': 'language',
        },
        'with_image': {
            'type': CuteFormType.OnlyNone,
        },
        'is_popular': {
            'type': CuteFormType.OnlyNone,
        },
    }

    def buttons_per_item(self, view, request, context, item):
        buttons = super(ActivityCollection, self).buttons_per_item(view, request, context, item)
        js_buttons = []
        if request.user.is_authenticated():

            # Archive buttons
            for prefix, is_archived, (has_permissions, because_premium), icon, staff_only in [
                ('', item.archived_by_owner,
                 item.has_permissions_to_archive(request.user), 'archive', False),
                ('ghost-', item.archived_by_staff,
                 (item.has_permissions_to_ghost_archive(request.user), False), 'ghost', True),
            ]:
                if is_archived:
                    # Unarchive
                    js_buttons.append((u'{}unarchive'.format(prefix), {
                        'has_permissions': has_permissions,
                        'title': _('Unarchive'),
                        'url': u'/ajax/unarchiveactivity/{}/'.format(item.id),
                        'icon': icon,
                        'classes': view.item_buttons_classes + (['staff-only'] if staff_only else []),
                    }))
                else:
                    # Archive
                    js_buttons.append((u'{}archive'.format(prefix), {
                        'has_permissions': has_permissions,
                        'alt_title': _('Archive'),
                        'title': mark_safe(u'{}{}'.format(
                            _('Archive'),
                            '' if not because_premium else
                            u' <i class="flaticon-promo text-gold" data-toggle="tooltip" data-title="{}" data-placement="top" data-trigger="hover"></i>'.format(
                                _('Premium feature'),
                            ),
                        )),
                        'url': u'/ajax/archiveactivity/{}/'.format(item.id),
                        'icon': icon,
                        'classes': view.item_buttons_classes + (['staff-only'] if staff_only else []),
                    }))

            if request.user.hasPermission('manipulate_activities'):
                # Bump
                js_buttons.append(('bump', {
                    'has_permissions': True,
                    'title': 'Bump',
                    'url': u'/ajax/bumpactivity/{}/'.format(item.id),
                    'icon': 'sort-up',
                    'classes': view.item_buttons_classes + ['staff-only'],
                }))
                # Drown
                js_buttons.append(('drown', {
                    'has_permissions': True,
                    'title': 'Drown',
                    'url': u'/ajax/drownactivity/{}/'.format(item.id),
                    'icon': 'sort-down',
                    'classes': view.item_buttons_classes + ['staff-only'],
                }))
            if ('staff' in models.ACTIVITY_TAGS_DICT.keys()
                and request.user.hasPermission('mark_activities_as_staff_pick')):
                if 'staff' in item.tags:
                    # Remove from staff picks
                    js_buttons.append(('remove-from-staff-pick', {
                        'has_permissions': True, 'title': 'Remove from staff picks',
                        'url': u'/ajax/removeactivitystaffpick/{}/'.format(item.id),
                        'icon': 'staff',
                        'classes': view.item_buttons_classes + ['staff-only'],
                    }))
                else:
                    # Mark as staff pick
                    js_buttons.append(('mark-staff-pick', {
                        'has_permissions': True, 'title': 'Mark as staff pick',
                        'url': u'/ajax/markactivitystaffpick/{}/'.format(item.id),
                        'icon': 'staff',
                        'classes': view.item_buttons_classes + ['staff-only'],
                    }))
        # Add show, csrf token to Js buttons
        for button_name, button in js_buttons:
            button['show'] = True
            if button['has_permissions']:
                button['extra_attributes'] = {
                    'csrf-token': csrf.get_token(request),
                }
        # Add Js buttons to buttons
        buttons.update(js_buttons)
        return buttons

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        per_line = 1
        distinct = False
        add_button_subtitle = _('Share your adventures!')
        ajax_pagination_callback = 'updateActivities'
        before_template = 'include/homePage'
        default_ordering = '-last_bump'
        filter_form = forms.FilterActivities
        show_relevant_fields_on_ordering = False
        show_item_buttons = False
        show_item_buttons_justified = False

        @property
        def item_buttons_classes(self):
            return [cls for cls in super(ActivityCollection.ListView, self).item_buttons_classes if cls != 'btn-secondary'] + ['btn-link']

        show_edit_button_superuser_only = True
        shortcut_urls = [''] + [u'activities/{}'.format(_tab) for _tab in HOME_ACTIVITY_TABS.keys()]

        def get_queryset(self, queryset, parameters, request):
            queryset = super(ActivityCollection.ListView, self).get_queryset(queryset, parameters, request)
            queryset = self.collection._get_queryset_for_list_and_item(queryset, parameters, request)
            # Exclude hidden tags
            if request.user.is_authenticated() and request.user.preferences.hidden_tags:
                for tag in models.getHiddenTags(request):
                    queryset = queryset.exclude(c_tags__contains=u'"{}"'.format(tag))
            else:
                queryset = queryset.exclude(_cache_hidden_by_default=True)
            # Get who archived if staff
            if request.user.is_authenticated() and request.user.is_staff:
                queryset = queryset.select_related('archived_by_staff')
            return queryset

        def top_buttons(self, request, context):
            buttons = super(ActivityCollection.ListView, self).top_buttons(request, context)
            if request.user.is_authenticated() and context['filter_form'].active_tab in ['new', 'hot']:
                buttons['warn'] = {
                    'show': True,
                    'has_permissions': True,
                    'classes': ['btn', 'btn-block', 'alert', 'alert-info'],
                    'title': _('You might be the first person who sees these activities!'),
                    'subtitle': _('If you see anything that doesn\'t follow our rules, please help us by reporting it.'),
                    'url': '/help/Report/',
                    'open_in_new_window': True,
                    'icon': 'about',
                }
            return buttons

        def extra_context(self, context):
            super(ActivityCollection.ListView, self).extra_context(context)
            if context.get('shortcut_url', None) is not None: # Homepage of the site
                indexExtraContext(context)
                context['hide_sidebar'] = True
            if context['request'].user.is_authenticated():
                context['activity_tabs'] = HOME_ACTIVITY_TABS
                context['active_activity_tab'] = context['filter_form'].active_tab
                # Context based on tab
                if context['filter_form'].active_tab == 'following':
                    context['no_result_template'] = 'include/activityFollowMessage'

    class ItemView(MagiCollection.ItemView):
        template = custom_item_template
        ajax_callback = 'updateActivities'
        show_item_buttons = False
        show_item_buttons_justified = False
        show_edit_button_superuser_only = True

        @property
        def item_buttons_classes(self):
            return [cls for cls in super(ActivityCollection.ItemView, self).item_buttons_classes if cls != 'btn-secondary'] + ['btn-link']

        def get_queryset(self, queryset, parameters, request):
            queryset = super(ActivityCollection.ItemView, self).get_queryset(queryset, parameters, request)
            return self.collection._get_queryset_for_list_and_item(queryset, parameters, request)

        def extra_context(self, context):
            super(ActivityCollection.ItemView, self).extra_context(context)

            # Show warning on hidden tags
            context['item'].hidden_reasons = []
            tags = context['item'].tags
            error_message = _(u'You are not allowed to see activities with the tag "{tag}".')

            for tag in models.getHiddenTags(context['request']):
                if tag in tags:
                    details = models.ACTIVITY_TAGS_DICT.get(tag, {})
                    if not isinstance(details, dict):
                        details = {}
                    has_permission = details.get('has_permission_to_show', lambda r: True)(context['request'])
                    if has_permission != True:
                        context['item'].hidden_reasons.append(u'{} {}'.format(
                            error_message.format(tag=details.get('translation', tag)),
                            has_permission,
                        ))
                    else:
                        context['item'].hidden_reasons.append(u'{} {}'.format(
                            error_message.format(tag=details.get('translation', tag)),
                            _('You can change which tags you would like to see or hide in your settings.'),
                        ))
            if context['item'].hidden_reasons:
                context['page_title'] = None
                context['comments_enabled'] = False

    class AddView(MagiCollection.AddView):
        multipart = True
        alert_duplicate = False
        form_class = forms.ActivityForm
        max_per_user_per_hour = 3

    class EditView(MagiCollection.EditView):
        multipart = True
        allow_delete = True
        form_class = forms.ActivityForm

        def allow_cascade_delete_up_to(self, request):
            return 25

        def redirect_after_delete(self, request, item, ajax):
            if ajax:
                return '/ajax/successdelete/'
            return super(ActivityCollection.EditView, self).redirect_after_delete(request, item, ajax)

############################################################
# Notification Collection

class NotificationCollection(MagiCollection):
    title = _('Notification')
    plural_title = _('Notifications')
    queryset = models.Notification.objects.all()
    navbar_link = False
    reportable = False

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        filter_form = forms.FilterNotification
        hide_sidebar = True
        show_title = True
        per_line = 1
        page_size = 5
        default_ordering = 'seen,-creation,-id'
        authentication_required = True

        def get_queryset(self, queryset, parameters, request):
            queryset = super(NotificationCollection.ListView, self).get_queryset(queryset, parameters, request)
            if 'ajax_modal_only' in parameters:
                queryset = queryset.filter(seen=False)
            return queryset.filter(owner=request.user)

        def extra_context(self, context):
            # Mark notification as read
            to_update = [item.pk for item in context['items'] if not item.seen]
            if to_update:
                updated = models.Notification.objects.filter(pk__in=to_update).update(seen=True)
                if updated:
                    context['request'].user.preferences.unread_notifications -= updated
                    if context['request'].user.preferences.unread_notifications < 0:
                        context['request'].user.preferences.unread_notifications = 0
                    context['request'].user.preferences.save()
            return context

    class ItemView(MagiCollection.ItemView):
        enabled = False

    class AddView(MagiCollection.AddView):
        enabled = False

    class EditView(MagiCollection.EditView):
        enabled = False

############################################################
# Badge Collection

class BadgeCollection(MagiCollection):
    enabled = False
    icon = 'badge'
    title = _('Badge')
    plural_title = _('Badges')
    navbar_link_list = 'staff'
    queryset = models.Badge.objects.all()
    reportable = False
    blockable = False

    types = OrderedDict([
        ('exclusive', {
            'title': 'Create a new exclusive badge',
            'form_class': forms.ExclusiveBadgeForm,
        }),
        ('copy', {
            'title': 'Make a copy from an existing badge',
            'form_class': forms.CopyBadgeForm,
            'show_button': False,
        }),
        ('donator', {
            'title': 'Montly donator badge',
            'form_class': forms.DonatorBadgeForm,
        }),
    ])

    filter_cuteform = {
        'show_on_profile': {
            'type': CuteFormType.YesNo,
            'to_cuteform': lambda k, v: 'checked' if k == 'True' else 'delete',
        },
        'rank': {
            'image_folder': 'badges',
            'to_cuteform': lambda k, v: u'medal{}'.format(k),
            'transform': CuteFormTransform.ImagePath,
        }
    }

    def buttons_per_item(self, view, request, context, item):
        buttons = super(BadgeCollection, self).buttons_per_item(view, request, context, item)
        if item.type == 'exclusive':
            buttons['copy'] = {
                'show': True,
                'has_permissions': self.add_view.has_permissions(request, context, item=item),
                'title': u'Make a copy',
                'icon': 'deck',
                'url': u'{url}?id={badge_id}'.format(
                    url=self.get_add_url(type='copy'),
                    badge_id=item.id,
                ),
                'classes': (
                    view.item_buttons_classes
                    + (['btn-block'] if not view.show_item_buttons_in_one_line else [])
                    + (['staff-only'] if self.add_view.staff_required else [])
                ),
            }
        if not context['ajax']:
            for button in buttons.values():
                button['classes'] = [cls for cls in button['classes'] if cls != 'staff-only']
        return buttons

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        default_ordering = '-date'
        filter_form = forms.FilterBadges

        def get_queryset(self, queryset, parameters, request):
            queryset = super(BadgeCollection.ListView, self).get_queryset(queryset, parameters, request)
            if 'of_user' in parameters and parameters['of_user']:
                request.context_show_user = False
            else:
                queryset = queryset.select_related('user', 'user__preferences')
                request.context_show_user = True
            return queryset

        def extra_context(self, context):
            request = context['request']
            context['show_user'] = request.context_show_user

        def top_buttons(self, request, context):
            buttons = super(BadgeCollection.ListView, self).top_buttons(request, context)
            for button in buttons.values():
                button['classes'] = [cls for cls in button['classes'] if cls != 'staff-only']
            return buttons

        def check_permissions(self, request, context):
            super(BadgeCollection.ListView, self).check_permissions(request, context)
            if (hasattr(request, 'GET') and 'of_user' not in request.GET
                and (not request.user.is_authenticated()
                     or not hasOneOfPermissions(request.user, self.collection.AddView.one_of_permissions_required))):
                raise PermissionDenied()

    class ItemView(MagiCollection.ItemView):
        template = 'badgeInfo'
        comments_enabled = False

        def get_queryset(self, queryset, parameters, request):
            queryset = super(BadgeCollection.ItemView, self).get_queryset(queryset, parameters, request)
            return queryset.select_related('owner')

    class AddView(MagiCollection.AddView):
        staff_required = True
        one_of_permissions_required = ['add_donation_badges', 'add_badges']
        multipart = True
        alert_duplicate = False

        def check_type_permissions(self, request, context, type=None):
            if type == 'donator' and not hasPermission(request.user, 'add_donation_badges'):
                raise PermissionDenied()

        def extra_context(self, context):
            form_name = u'add_{}'.format(self.collection.name)
            if hasattr(context['forms'][form_name], 'badge'):
                context['alert_message'] = string_concat(_('Badge'), ': ', unicode(context['forms'][form_name].badge))
                context['alert_type'] = 'info'
                context['alert_flaticon'] = 'about'
                context['alert_button_string'] = context['forms'][form_name].badge.open_sentence
                context['alert_button_link'] = context['forms'][form_name].badge.item_url

    class EditView(MagiCollection.EditView):
        staff_required = True
        one_of_permissions_required = ['add_donation_badges', 'add_badges']
        multipart = True
        allow_delete = True

        def check_type_permissions(self, request, context, type=None, item=None):
            if type == 'donator' and not hasPermission(request.user, 'add_donation_badges'):
                raise PermissionDenied()

############################################################
# Report Collection

class ReportCollection(MagiCollection):
    navbar_link_list = 'staff'
    icon = 'warning'
    queryset = models.Report.objects.all().select_related('owner', 'owner__preferences', 'staff', 'staff__preferences').prefetch_related(Prefetch('images', to_attr='all_images'))
    reportable = False
    blockable = False

    @property
    def types(self):
        if not getMagiCollections():
            return True
        if not self._cached_types:
            self._cached_types = {
                name: {
                    'title': c.title,
                    'plural_title': c.plural_title,
                    'image': c.image,
                    'icon': c.icon,
                }
                for name, c in getMagiCollections().items()
                if c.reportable
            }
        return self._cached_types
    _cached_types = None

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        show_title = True
        staff_required = True
        permissions_required = ['moderate_reports']
        show_edit_button = False
        per_line = 1
        js_files = ['reports']
        ajax_pagination_callback = 'updateReport'
        filter_form = forms.FilterReports
        show_add_button = justReturn(False)
        default_ordering = 'i_status'

    class ItemView(MagiCollection.ItemView):
        template = custom_item_template
        comments_enabled = False
        owner_only_or_permissions_required = ['moderate_reports']
        show_edit_button = False
        js_files = ['reports']
        ajax_callback = 'updateReport'

    class AddView(MagiCollection.AddView):
        authentication_required = False
        alert_duplicate = False
        back_to_list_button = False
        form_class = forms.ReportForm
        multipart = True

        def extra_context(self, context):
            context['alert_message'] = mark_safe(u'{message}<ul>{list}</ul>{learn_more}'.format(
                message=_(u'Only submit a report if there is a problem with this specific {thing}. If it\'s about something else, your report will be ignored. For example, don\'t report an account or a profile if there is a problem with an activity. Look for "Report" buttons on the following to report individually:').format(thing=self.collection.types[context['type']]['title'].lower()),
                list=''.join([u'<li>{}</li>'.format(unicode(type['plural_title'])) for name, type in self.collection.types.items() if name != context['type']]),
                learn_more=(
                    '' if context['request'].LANGUAGE_CODE in LANGUAGES_CANT_SPEAK_ENGLISH else
                    u'<div class="text-right"><a href="/help/Report" target="_blank" class="btn btn-warning">{}</a></div>'.format(_('Learn more'))),
            ))
            return context

    class EditView(MagiCollection.EditView):
        multipart = True
        allow_delete = True
        redirect_after_delete = justReturn('/')
        back_to_list_button = False
        form_class = forms.ReportForm

############################################################
# Donate Collection

class DonateCollection(MagiCollection):
    enabled = False
    title = 'Donation Month'
    plural_title = _('Donators')
    navbar_link_title = _('Donate')
    plural_name = 'donate'
    icon = 'heart'
    navbar_link_list = 'more'
    queryset =  models.DonationMonth.objects.all().prefetch_related(Prefetch('badges', queryset=models.Badge.objects.select_related('user', 'user__preferences').order_by('-show_on_profile'), to_attr='all_badges'))
    reportable = False
    blockable = False
    form_class = forms.DonateForm

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        page_size = 1
        per_line = 1
        default_ordering = '-date'
        show_title = False
        show_edit_button_superuser_only = True
        show_add_button_superuser_only = True
        before_template = 'include/donate'
        add_button_subtitle = ''

        def get_queryset(self, queryset, parameters, request):
            queryset = super(DonateCollection.ListView, self).get_queryset(queryset, parameters, request)
            return queryset.filter(date__lte=timezone.now())

        def extra_context(self, context):
            request = context['request']
            context['show_paypal'] = 'show_paypal' in request.GET
            context['donate_image'] = DONATE_IMAGE
            if request.user.is_authenticated() and request.user.hasPermission('manage_donation_months'):
                context['show_donator_details'] = True

    class ItemView(MagiCollection.ItemView):
        enabled = False

    class AddView(MagiCollection.AddView):
        staff_required = True
        permissions_required = ['manage_donation_months']
        multipart = True

    class EditView(MagiCollection.EditView):
        staff_required = True
        permissions_required = ['manage_donation_months']
        multipart = True
        allow_delete = True

############################################################
# Prize Collection

PRIZE_CUTEFORM = {
    'i_character': {
        'to_cuteform': lambda k, v: models.Prize.CHARACTERS[k][2],
        'extra_settings': {
	    'modal': 'true',
	    'modal-text': 'true',
        },
    },
    'has_giveaway': {
        'type': CuteFormType.YesNo,
    },
}

class PrizeCollection(MagiCollection):
    enabled = False
    queryset = models.Prize.objects.all()
    form_class = forms.PrizeForm
    navbar_link_list = 'staff'
    filter_cuteform = PRIZE_CUTEFORM
    reportable = False
    icon = 'present'

    def to_fields(self, view, item, *args, **kwargs):
        fields = super(PrizeCollection, self).to_fields(view, item, *args, **kwargs)
        setSubField(fields, 'value', key='value', value=u'US ${}'.format(item.value))
        setSubField(fields, 'character', key='type', value='text_with_link')
        setSubField(fields, 'character', key='link', value=lambda f: item.character_url)
        setSubField(fields, 'character', key='link_text', value=lambda f: item.character)
        setSubField(fields, 'character', key='image', value=lambda f: item.character_image)
        return fields

    class ListView(MagiCollection.ListView):
        staff_required = True
        one_of_permissions_required = ['add_prizes', 'manage_prizes']
        filter_form = forms.PrizeFilterForm

    class ItemView(MagiCollection.ItemView):
        staff_required = True
        hide_icons = True

    class AddView(MagiCollection.AddView):
        staff_required = True
        one_of_permissions_required = ['add_prizes', 'manage_prizes']
        multipart = True

    class EditView(MagiCollection.EditView):
        staff_required = True
        owner_only_or_permissions_required = ['manage_prizes']
        multipart = True
        allow_delete = True
