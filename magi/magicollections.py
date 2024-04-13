# -*- coding: utf-8 -*-
from __future__ import division
import string, copy
from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _, string_concat, get_language
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.middleware import csrf
from django.http import Http404
from django.db.models import Q, Prefetch, FieldDoesNotExist
from django.shortcuts import get_object_or_404
from django.conf import settings as django_settings
from magi.views import indexExtraContext
from magi.utils import (
    mergeDicts,
    getCharacterNameFromPk,
    getCharacterImageFromPk,
    getCharacterURLFromPk,
    getCharacterLabel,
    getImageForPrefetched,
    getIndex,
    AttrDict,
    justReturn,
    propertyFromCollection,
    getMagiCollections,
    getMagiCollection,
    getMagiCollectionFromModel,
    CuteFormType,
    CuteFormTransform,
    redirectWhenNotAuthenticated,
    custom_item_template,
    getNavbarPrefix,
    getNavbarHeaderPrefixForCollection,
    getAccountIdsFromSession,
    getAccountTypesFromSession,
    setSubField,
    hasPermission,
    hasPermissions,
    hasOneOfPermissions,
    staticImageURL,
    ColorField,
    YouTubeVideoField,
    translationURL,
    modelHasField,
    modelFieldVerbose,
    isBirthdayToday,
    getSearchSingleFieldLabel,
    isTranslationField,
    addParametersToURL,
    tourldash,
    getEmojis,
    filterRealAccounts,
    filterRealCollectiblesPerAccount,
    failSafe,
    toHumanReadable,
    YouTubeVideoField,
    markSafeFormat,
    markSafeJoin,
    listUnique,
    getEnglish,
    newOrder,
    getModelOfRelatedItem,
    selectRelatedDictToStrings,
    displayQueryset,
    snakeToCamelCase,
    getListURL,
    getRelOptionsDict,
    getMaxShownForPrefetchedTogether,
    getQuerysetFromModel,
    getFilterFieldNameOfRelatedItem,
    articleJsonLdFromActivity,
    modelGetField,
    hasValue,
    getCharactersFavoriteFieldLabel,
    __,
    getCharactersTotalFavoritable,
    ordinalNumber,
    isValidCharacterPk,
    baseButton,
    getCharactersUsersFavorites,
    isCharactersUserFavorite,
    isRequestAjax,
    makeCollectionCommunity,
    getSiteName,
    notTranslatedWarning,
    mergedFieldCuteForm,
)
from magi.raw import please_understand_template_sentence, unrealistic_template_sentence
from magi.django_translated import t
from magi.notifications import pushNotification
from magi.middleware.httpredirect import HttpRedirectException
from magi.item_model import get_http_image_url_from_path
from magi.settings import (
    ACCOUNT_MODEL,
    ACTIVITY_TAGS,
    PROFILE_TABS,
    GET_GLOBAL_CONTEXT,
    DONATE_IMAGE,
    ON_USER_EDITED,
    ON_PREFERENCES_EDITED,
    ACCOUNT_TAB_ORDERING,
    FIRST_COLLECTION,
    FIRST_COLLECTION_PER_ACCOUNT_TYPE,
    GLOBAL_OUTSIDE_PERMISSIONS,
    HOME_ACTIVITY_TABS,
    LANGUAGES_CANT_SPEAK_ENGLISH,
    BACKGROUNDS_MODEL,
    FAVORITE_CHARACTERS_MODEL,
    OTHER_CHARACTERS_MODELS,
    BACKGROUNDS_FILTER,
    FAVORITE_CHARACTERS_FILTER,
)
from magi import models, forms, magifields

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
    show_title = False
    show_small_title = True
    ajax_callback = None
    enabled = True
    logout_required = False
    staff_required = property(propertyFromCollection('staff_required'))
    permissions_required = property(propertyFromCollection('permissions_required'))
    one_of_permissions_required = property(propertyFromCollection('one_of_permissions_required'))
    ajax = True
    disable_on_high_traffic = False

    def get_global_context(self, request):
        return GET_GLOBAL_CONTEXT(request)

    def share_image(self, context, item):
        return self.collection.share_image(context, item)

    def get_queryset(self, queryset=None, parameters={}, request=None):
        return self.collection.get_queryset(self, queryset, parameters, request)

    def check_permissions(self, request, context):
        # It's OK if context is empty, but request is required
        if not self.enabled:
            raise Http404
        if self.logout_required and request.user.is_authenticated():
            raise PermissionDenied()
        if self.authentication_required:
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
        if self.staff_required:
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
            if not request.user.is_staff and not request.user.is_superuser:
                raise PermissionDenied()
        if self.prelaunch_staff_required:
            redirectWhenNotAuthenticated(request, context, next_title=self.get_page_title())
            if not request.user.hasPermission('access_site_before_launch'):
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
        # It's OK if context is empty, but request is required
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

    def get_extra_fields(self, item):
        return []

    #######################
    # Tools - not meant to be overridden

    def has_permissions(self, request, context, item=None):
        # It's OK if context is empty, but request is required
        try:
            self.check_permissions(request, context)
            if item:
                self.check_owner_permissions(request, context, item)
        except (PermissionDenied, HttpRedirectException, Http404):
            return False
        return True

    def requires_permissions(self):
        """
        Does this view require specific permissions, or anyone authenticated has permissions?
        Can be useful to show/hide buttons that redirect to sign up to encourage people to click and sign up.
        Example: buttons to add to collection should show up when unauthenticated, but only
                 if requires_permissions is False.
        """
        return (
            self.staff_required
            or self.prelaunch_staff_required
            or self.permissions_required
            or self.one_of_permissions_required
            or getattr(self, 'owner_only', False)
            or getattr(self, 'owner_or_staff_only', False)
            or getattr(self, 'owner_only_or_permissions_required', [])
            or getattr(self, 'owner_only_or_one_of_permissions_required', [])
        )

    def view_title(self):
        return self.view.replace('_', ' ').capitalize()

    def has_method_been_overridden(self, method_name, check_collection_level=False):
        base_view = getattr(MagiCollection, snakeToCamelCase(self.view))
        base_method = getattr(base_view, method_name)
        for cls in type(self).__mro__:
            if hasattr(cls, method_name) and getattr(cls, method_name) != base_method:
                return True
        if check_collection_level:
            base_method = getattr(MagiCollection, method_name)
            for cls in type(self.collection).__mro__:
                if hasattr(cls, method_name) and getattr(cls, method_name) != base_method:
                    return True
        return False

    def uses_deprecated_to_fields(self):
        return (
            self.has_method_been_overridden('to_fields', check_collection_level=True)
            or self.has_method_been_overridden('get_extra_fields')
            or (self.view == 'list_view' and self.has_method_been_overridden('table_fields'))
            or (self.view == 'list_view' and self.has_method_been_overridden('ordering_fields'))
            or getattr(self, 'fields_extra', None)
        )

    def __unicode__(self):
        return u'{}: {}'.format(self.collection, self.view_title())

class MagiCollection(object):
    # Required variables
    @property
    def queryset(self): raise NotImplementedError('Queryset is required in a MagiCollection')

    # Optional variables without default
    icon = None
    image = None
    larger_image = False
    navbar_link_list = None
    navbar_link_list_divider_before = False
    navbar_link_list_divider_after = False
    types = None
    filter_cuteform = {}
    fields_class = magifields.MagiFields
    fields_icons = {}
    fields_images = {}

    collectible = None
    collectible_collections = {}

    # Optional variables with default values
    auto_share_image = False
    show_items_names_in_source_languages = False # Can also be a list of languages

    @property
    def name(self):
        return self.__class__.__name__.lower().replace('collection', '')

    @property
    def navbar_link_title(self):
        return self.list_view.get_page_title()

    def get_queryset(self, view=None, queryset=None, parameters={}, request=None):
        """
        Will preselect/prefetch related items based on view settings.
        For each preselected/prefetched item, it will make sure to call get_queryset to keep all
          default preselected/prefetched items of those. It will however not use view settings for those.
        It doesn't support nested lookups, which means if you preselect "idol__song", it won't call
          get_queryset of idol nor song.
        It doesn't support generic `select_related(True)`.
        Example:
          - CardsSetCollection item view has fields_prefetched = 'cards'
          - CardCollection queryset = Card.objects.select_related('idol')
          => When displaying a cards set item view, will prefetch cards, and their idols too.
          => Result queryset: CardsSet.objects.prefetch_related(Prefetch('cards', models.Card.objects.select_related('idols'))
        Example:
          - CostumeCollection item view has fields_preselected = 'card'
          - CardCollection queryset = Card.objects.select_related('idol')
          => When displaying a costume item view, will preselect card, and its idol too.
          => Result queryset: Costume.objects.select_related('card', 'card__idol')
        Example:
          - IdolCollection item view has fields_preselected = 'unit'
          - UnitCollection queryset = Unit.objects.prefetch_related('idols')
          => When displaying an idol item view, will preselect unit, and its idols too.
          => Result queryset: Idol.objects.select_related('unit').prefetch_related('unit__idols')

        View is optional.
        It's used to figure out what to pre-select and prefetch from view settings.

        Queryset is optional.
        Defaults to self.queryset.

        Request is optional.
        It's used when called in the context of an item view to make a query with a limit
        instead of a prefetch whenever it's relevant. It will use previously set _item_view_pk (by item_view function)
        and store the results in _prefetched_with_max.
        """
        if queryset is None:
            queryset = self.queryset

        # Preselected
        fields_preselected = listUnique(
            getattr(view, 'fields_preselected', [])
            + selectRelatedDictToStrings(queryset.query.select_related)
        )
        if fields_preselected:
            new_fields_preselected = []
            for preselected in fields_preselected:
                model_of_preselected = getModelOfRelatedItem(queryset.model, preselected)
                queryset_of_preselected = getQuerysetFromModel(model_of_preselected, request=request)
                new_fields_preselected += [ preselected ]
                if queryset_of_preselected is not None:
                    new_fields_preselected += [
                        u'{}__{}'.format(preselected, other_preselected)
                        for other_preselected in selectRelatedDictToStrings(queryset_of_preselected.query.select_related)
                    ]
                    for other_prefetched in queryset_of_preselected._prefetch_related_lookups:
                        queryset_of_other_prefetched = None
                        if isinstance(other_prefetched, Prefetch):
                            queryset_of_other_prefetched = other_prefetched.queryset
                            other_prefetched = other_prefetched.prefetch_to
                        if queryset_of_other_prefetched is None:
                            model_of_other_prefetched = getModelOfRelatedItem(model_of_preselected, other_prefetched)
                            queryset_of_other_prefetched = getQuerysetFromModel(model_of_other_prefetched, request=request)
                        if queryset_of_other_prefetched is not None:
                            queryset = queryset.prefetch_related(Prefetch(
                                u'{}__{}'.format(preselected, other_prefetched),
                                queryset=queryset_of_other_prefetched.distinct(),
                            ))
                        else:
                            queryset = queryset.prefetch_related( u'{}__{}'.format(preselected, other_prefetched))
            # select_related modifies the queryset in place, so we need to make a copy
            queryset = copy.deepcopy(queryset)
            queryset.query.select_related = False
            queryset = queryset.select_related(*new_fields_preselected)

        # Prefetched

        already_prefetched = [ p.prefetch_to if isinstance(p, Prefetch) else p for p in queryset._prefetch_related_lookups ]
        fields_prefetched = listUnique( # may still get duplicates if queryset specified
            getattr(view, 'fields_prefetched', [])
            + getattr(view, 'fields_prefetched_together', [])
            + queryset._prefetch_related_lookups
        )
        prefetched_with_max_querysets = {}
        # Clear current prefetched because they'll be re-added here
        queryset = queryset.prefetch_related(None)
        for prefetched in fields_prefetched:
            queryset_of_prefetched = None
            to_attr = None
            if isinstance(prefetched, tuple):
                queryset_of_prefetched = prefetched[1]()
                prefetched = prefetched[0]
            elif isinstance(prefetched, Prefetch):
                queryset_of_prefetched = prefetched.queryset
                if prefetched.prefetch_to != prefetched.prefetch_through:
                    to_attr = prefetched.prefetch_to
                prefetched = prefetched.prefetch_through
            if queryset_of_prefetched is None:
                model_of_prefetched = getModelOfRelatedItem(queryset.model, prefetched)
                collection_of_prefetched, queryset_of_prefetched = getQuerysetFromModel(
                    model_of_prefetched, request=request, return_collection=True)
                # For item view, if the site is in high traffic mode and the current user
                # is not authenticated, don't prefetch at all.
                if (getattr(django_settings, 'HIGH_TRAFFIC', False)
                    and queryset_of_prefetched is not None
                    and view and view.view == 'item_view'
                    and request and getattr(request, '_item_view_pk', None)
                    and prefetched not in already_prefetched
                    and prefetched not in view.fields_prefetched_even_on_high_traffic
                    and not request.user.is_authenticated()
                    and not view.uses_deprecated_to_fields()):
                    if not hasattr(request, '_not_prefetched_for_high_traffic'):
                        request._not_prefetched_for_high_traffic = []
                    request._not_prefetched_for_high_traffic.append(prefetched)
                    continue
                # For item view, when a max is set, perform the query with a limit
                # to avoid loading all items. Doesn't support tuples, Prefetch and __.
                # If the prefetch key was already in the original queryset, it will also not use this.
                if (queryset_of_prefetched is not None
                    and view and view.view == 'item_view'
                    and request and getattr(request, '_item_view_pk', None)
                    and prefetched in getattr(view, 'fields_prefetched_together', [])
                    and prefetched not in already_prefetched
                    and not view.uses_deprecated_to_fields()):
                    max = getMaxShownForPrefetchedTogether(
                        model_class=queryset.model, field_name=prefetched, rel_collection=collection_of_prefetched
                    )
                    if max is not None:
                        filter_field_name = getFilterFieldNameOfRelatedItem(queryset.model, prefetched)
                        if filter_field_name:
                            queryset_of_prefetched = queryset_of_prefetched.filter(**{ filter_field_name: request._item_view_pk })
                            # Load 1 extra as a way to check if there's more or not
                            prefetched_items = failSafe(lambda: list(queryset_of_prefetched[:max + 1]), exceptions=[ TypeError ])
                            if prefetched_items is not None:
                                has_more = False
                                if len(prefetched_items) > max:
                                    has_more = True
                                    prefetched_items = prefetched_items[:-1]
                                prefetched_with_max_querysets[prefetched] = queryset_of_prefetched
                                if not hasattr(request, '_prefetched_with_max'):
                                    request._prefetched_with_max = {}
                                request._prefetched_with_max[prefetched] = (prefetched_items, max, has_more)
                                continue
                            else:
                                prefetched_with_max_querysets[prefetched] = None

            if queryset_of_prefetched is None:
                queryset = queryset.prefetch_related(prefetched)
            else:
                queryset = queryset.prefetch_related(Prefetch(prefetched, queryset=queryset_of_prefetched.distinct(), to_attr=to_attr))

        if django_settings.DEBUG and view and getattr(django_settings, 'DEBUG_SHOW_QUERYSET', True):
            print ''
            print 'Get queryset for', self.plural_name, view.view
            print displayQueryset(queryset, prefix=u'  ')
            if hasattr(request, '_prefetched_with_max'):
                print u'{}\n'.format('  Manual prefetch queries with limits:')
                for prefetched, queryset_of_prefetched in prefetched_with_max_querysets.items():
                    print '    ', prefetched
                    if queryset_of_prefetched is None:
                        print '      Failed to get queryset'
                    else:
                        print displayQueryset(queryset_of_prefetched, prefix=u'      ')
            if hasattr(request, '_not_prefetched_for_high_traffic'):
                print u'  Due to high traffic, the following have not been prefetched:'
                print u'    {}'.format(request._not_prefetched_for_high_traffic)
        return queryset

    def get_title_prefixes(self, request, context):
        prefixes = []
        navbar_prefix = getNavbarPrefix(self.navbar_link_list, request, context)
        if navbar_prefix:
            prefixes = [ navbar_prefix ]
            header_prefix = getNavbarHeaderPrefixForCollection(self, context)
            if header_prefix:
                prefixes.append(header_prefix)
        return prefixes

    def _collectibles_queryset(self, view, queryset, request=None):
        if queryset is None:
            queryset = self.queryset
        if not request:
            return queryset
        # Select related total collectible for authenticated user
        if request.user.is_authenticated() and self.collectible_collections:
            if not getattr(request, 'show_collect_button', False):
                return queryset
            for name, collection in self.collectible_collections.items():
                if (not collection.add_view.enabled
                    or (isinstance(request.show_collect_button, dict)
                        and not request.show_collect_button.get(name, True))
                    or not collection.add_view.has_permissions(request, {})):
                    continue
                item_field_name = getattr(collection.queryset.model, 'selector_to_collected_item',
                                          self.model_name)
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
                                if collection.collectible_limit_to_account_types is not None:
                                    all_fk_owner_ids = [
                                        account_id for account_id, type_ in getAccountTypesFromSession(request).items()
                                        if type_ in collection.collectible_limit_to_account_types
                                    ]
                                else:
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
                        'SELECT COUNT(*) FROM {db_table} WHERE {item_field_name}_id = {item_db_table}.{item_pk_name} AND {fk_owner}_id IN ({fk_owner_ids})'.format(
                            db_table=collection.queryset.model._meta.db_table,
                            item_field_name=item_field_name,
                            item_db_table=self.queryset.model._meta.db_table,
                            item_pk_name=self.queryset.model._meta.pk.column,
                            fk_owner=fk_owner, fk_owner_ids=fk_owner_ids,
                        )
                    }
                    queryset = queryset.extra(select=a)
        return queryset

    def to_form_class(self):
        """Used in urls.py"""
        class _Form(forms.AutoForm):
            class Meta(forms.AutoForm.Meta):
                model = self.queryset.model
        self._form_class = _Form

    def form_class(self, request, context):
        return self._form_class

    def collectible_to_class(self, model_class):
        """
        Return a collectible class based on this model.
        You may override this function, but you're not really supposed to call it yourself.
        """
        parent_collection = self
        item_field_name = parent_collection.model_name
        item_field_model_class = model_class._meta.get_field(item_field_name).rel.to
        item_field_name_id = u'{}_{}'.format(item_field_name, item_field_model_class._meta.pk.column)

        class _CollectibleForm(forms.AutoForm):
            def __init__(self, *args, **kwargs):
                super(_CollectibleForm, self).__init__(*args, **kwargs)
                self.collectible_variables = {}
                if not self.request:
                    return
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
                        # Choices
                        # Exclude limited account types
                        if self.collection and self.collection.collectible_limit_to_account_types is not None:
                            self.fields[model_class.fk_as_owner].choices = [
                                (c.pk, unicode(c)) for c in filtered_queryset
                                if c.type in self.collection.collectible_limit_to_account_types
                            ]
                        else:
                            self.fields[model_class.fk_as_owner].choices = [
                                (c.pk, unicode(c)) for c in filtered_queryset
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
                if (self.collection
                    and self.collection.add_view.add_to_collection_variables
                    and not isinstance(self, forms.MagiFiltersForm)):
                    missing = False
                    # add variables from GET parameters
                    for variable in self.collection.add_view.add_to_collection_variables:
                        get = u'{}_{}'.format(self.collection.item_field_name, variable)
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
                            if variable == 'unicode':
                                self.collectible_variables[variable] = unicode(item)
                            else:
                                self.collectible_variables[variable] = unicode(getattr(item, variable))

            class Meta:
                model = model_class
                fields = '__all__'
                save_owner_on_creation = not model_class.fk_as_owner
                hidden_foreign_keys = [item_field_name]

        class _CollectibleFilterForm(forms.MagiFiltersForm):
            if parent_collection.list_view.filter_form:
                search_fields = [
                    u'{}__{}'.format(item_field_name, _f)
                    for _f in getattr(parent_collection.list_view.filter_form, 'search_fields', [])
                ]
                search_fields_labels = { k: v for k, v in [
                    (u'{}__{}'.format(item_field_name, _f), getSearchSingleFieldLabel(
                        field_name=_f, model_class=parent_collection.queryset.model,
                        labels=getattr(parent_collection.list_view.filter_form, 'search_fields_labels', {}) or {},
                        translated_fields=parent_collection.translated_fields or [],
                    ))
                    for _f in getattr(parent_collection.list_view.filter_form, 'search_fields', [])
                ] if v is not None }
                ordering_fields = [
                    (u','.join([u'{}__{}'.format(
                        item_field_name, _os[1:] if _os.startswith('-') else _os,
                    ) for _os in _o.split(',')]), _t)
                    for _o, _t in getattr(parent_collection.list_view.filter_form, 'ordering_fields', [])
                ]

            def _to_cuteform_for_i_choices(self, to_cuteform, field_name):
                return lambda key, value: to_cuteform(key, parent_collection.queryset.model.get_reverse_i(field_name[2:], key), value)

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

                # Add filters from parent filters
                parent_filter_form = parent_collection.list_view.filter_form(request=self.request, ajax=self.ajax, collection=self.collection)
                self.parent_fields = []
                self.on_change_value_show = getattr(self, 'on_change_value_show', {})
                for field_name, field in parent_filter_form.fields.items():
                    new_field_name = '{}_{}'.format(item_field_name, field_name)
                    if (field_name in ['search', 'ordering', 'reverse_order', 'view', item_field_name, model_class.fk_as_owner, 'owner']
                        or field_name in self.fields or new_field_name in self.fields):
                        continue
                    filter = getattr(parent_filter_form, u'{}_filter'.format(field_name), None)
                    if filter:
                        filter = copy.deepcopy(filter)
                    else:
                        filter = forms.MagiFilter()
                    if filter.to_queryset or filter.noop:
                        continue
                    self.fields[new_field_name] = field
                    self.parent_fields.append(new_field_name)
                    if not filter.selectors:
                        filter.selectors = ['{}__{}'.format(item_field_name, field_name)]
                    else:
                        filter.selectors = [
                            u'{}__{}'.format(item_field_name, selector)
                            for selector in filter.selectors
                        ]
                    setattr(self, u'{}_filter'.format(new_field_name), filter)
                    cuteform = (
                        parent_filter_form.cuteform.get(field_name, None)
                        or parent_collection.list_view.filter_cuteform.get(field_name, None)
                        or parent_collection.filter_cuteform.get(field_name, None)
                    )
                    if cuteform is not None:
                        cuteform = cuteform.copy()
                        if ('to_cuteform' in cuteform and field_name.startswith('i_')
                            and failSafe(lambda: cuteform['to_cuteform'].func_code.co_argcount, exceptions=[ AttributeError ]) == 3):
                            cuteform['to_cuteform'] = self._to_cuteform_for_i_choices(cuteform['to_cuteform'], field_name)
                        if not cuteform.get('image_folder', None):
                            cuteform['image_folder'] = field_name
                        self.cuteform[new_field_name] = cuteform
                    parent_on_change_value_show = getattr(parent_filter_form, 'on_change_value_show', {}).get(field_name, None)
                    if parent_on_change_value_show:
                        if isinstance(parent_on_change_value_show, dict):
                            self.on_change_value_show[new_field_name] = {
                                key: [u'{}_{}'.format(item_field_name, sub_field_name) for sub_field_name in sub_field_names]
                                for key, sub_field_names in parent_on_change_value_show.items()
                            }
                        else:
                            self.on_change_value_show[new_field_name] = [
                                u'{}_{}'.format(item_field_name, sub_field_name) for sub_field_name in parent_on_change_value_show
                            ]

                if self.parent_fields and not getattr(self, 'show_more', None):
                    self.show_more = forms.FormShowMore(cutoff=self.parent_fields[0], including_cutoff=True, message_more=parent_collection.title)

            class Meta(forms.MagiFiltersForm.Meta):
                model = model_class
                fields = []

        class _CollectibleCollection(MagiCollection):
            name = model_class.collection_name
            queryset = model_class.objects.all().select_related(item_field_name)
            icon = self.icon
            image = self.image
            navbar_link = False
            reportable = False
            form_class = _CollectibleForm
            collectible_tab_name = property(lambda _s: _s.plural_title)
            collectible_limit_to_account_types = None # If accounts have types, list of types that are allowed to collect this

            def __init__(self, *args, **kwargs):
                super(_CollectibleCollection, self).__init__(*args, **kwargs)
                self.parent_collection = parent_collection
                self.item_field_name = item_field_name
                self.item_field_model_class = item_field_model_class
                self.item_field_name_id = item_field_name_id

            def get_list_url_for_authenticated_owner(
                    self, request, ajax=False, item=None, fk_as_owner=None, parameters=None, full=False):
                new_parameters = {
                    k: v for k, v in {
                        'owner': request.user.id if not fk_as_owner else None,
                        item_field_name: getattr(item, item_field_name_id) if item else None,
                        model_class.fk_as_owner: fk_as_owner if fk_as_owner else None,
                    }.items() if v
                }
                new_parameters.update(parameters or {})
                return self.get_list_url(ajax=ajax, parameters=new_parameters, full=full)

            @property
            def title(self):
                return _('Collected {thing}').format(thing=parent_collection.title.lower())

            @property
            def plural_title(self):
                return _('Collected {things}').format(things=parent_collection.plural_title.lower())

            @property
            def add_sentence(self):
                return _(u'Add to your {thing}').format(thing=self.plural_title.lower())

            def get_parent_prefix(self, request, context):
                user = getattr(request, 'user_for_parent_prefix', None)
                owner = getattr(request, 'owner_for_parent_prefix', None)
                item = getattr(request, 'item_for_parent_prefix', None)
                fk_as_owner = model_class.fk_as_owner or 'owner'
                return {
                    'title': self.list_view.get_page_title(),
                    'url': (
                        # Link to profile tab within profile
                        addParametersToURL(user.item_url, anchor='profiletabs', parameters={
                            'open': self.name,
                        })
                        if fk_as_owner == 'owner' and user
                        else
                        # Link to regular list view with set item and/or owner
                        self.get_list_url(
                            parameters={ k: v for k, v in {
                                fk_as_owner: owner.pk if owner else None,
                                item_field_name: item.pk if item else None,
                            }.items() if v })
                    ),
                }

            def get_title_prefixes(self, request, context):
                title_prefixes = super(_CollectibleCollection, self).get_title_prefixes(request, context)

                fk_as_owner = model_class.fk_as_owner or 'owner'
                request = context['request']

                # List view + Item view
                # Show profile of user in prefixes

                if 'item' in context or request.GET.get(fk_as_owner, None):

                    # User profile

                    if fk_as_owner == 'owner':
                        if 'item' in context:
                            owner = getattr(context['item'], fk_as_owner) # Preselected
                        else:
                            try:
                                owner = (
                                    request.user
                                    if unicode(request.user.id) == unicode(request.GET[fk_as_owner])
                                    else model_class.get_owner_from_pk(request.GET[fk_as_owner])
                                )
                            except ObjectDoesNotExist:
                                raise Http404

                        title_prefixes.append({
                            'title': unicode(owner),
                            'url': owner.item_url,
                        })

                        # Hack for get_parent_prefix
                        request.user_for_parent_prefix = owner
                        request.owner_for_parent_prefix = owner

                    # Account

                    elif fk_as_owner == 'account':
                        if 'item' in context:
                            account = getattr(context['item'], fk_as_owner) # Preselected
                        else:
                            try:
                                account = model_class.get_owner_from_pk(request.GET[fk_as_owner])
                            except ObjectDoesNotExist:
                                raise Http404
                        title_prefixes += [
                            {
                                'title': unicode(account.cached_owner.username),
                                'url': account.cached_owner.item_url,
                            },
                            {
                                'title': unicode(account),
                                'url': addParametersToURL(account.cached_owner.item_url, {
                                    'open': 'account',
                                    u'account{}'.format(account.pk): self.name,
                                }, anchor=account.id),
                            },
                        ]
                        # Hack for get_parent_prefix
                        request.user_for_parent_prefix = account.cached_owner
                        request.owner_for_parent_prefix = account

                    # Other
                    else:
                        pass # No prefix

                # List view only
                # Show item view in prefixes

                elif request.GET.get(item_field_name, None):
                    try:
                        item = item_field_model_class.objects.get(
                            pk=request.GET[item_field_name])
                    except ObjectDoesNotExist:
                        raise Http404
                    item_title_prefixes, item_h1 = self.parent_collection.item_view.get_h1_title(
                        request, context, item)
                    title_prefixes += item_title_prefixes + [
                        {
                            'title': (
                                item_h1.get('title', None)
                                or self.parent_collection.item_view.get_page_title(item=item)
                            ),
                            'url': item.item_url,
                        },
                    ]
                    # Hack for get_parent_prefix
                    request.item_for_parent_prefix = item

                return title_prefixes

            class ListView(MagiCollection.ListView):
                add_button_use_collection_icon = False

                filter_form = _CollectibleFilterForm
                item_padding = (7, 0)
                col_break = 'sm'
                per_line = 6
                page_size = 30
                show_item_buttons = False
                show_add_button = justReturn(False)
                ajax_item_popover = True
                allow_random = False
                show_open_button = False
                display_style_table_show_open_button = False

                alt_views = MagiCollection.ListView.alt_views + [
                    ('quick_edit', {
                        'hide_in_filter': True,
                        'verbose_name': _('Quick edit'),
                        'template': 'default_item_table_view',
                        'display_style': 'table',
                        'display_style_table_fields': [ 'image' ] + ([
                            model_class.fk_as_owner] if model_class.fk_as_owner else []),
                    }),
                ]

                def check_permissions(self, request, context):
                    super(_CollectibleCollection.ListView, self).check_permissions(request, context)
                    if context['current'].startswith(u'{}_list'.format(self.collection.name)):
                        # At least owner filter or item filter required
                        if (not request.GET.get(model_class.fk_as_owner or 'owner', None)
                            and not request.GET.get(item_field_name, None)
                            and not request.GET.get('owner', None)):
                            raise PermissionDenied()

                def get_queryset(self, queryset=None, parameters={}, request=None):
                    queryset = super(_CollectibleCollection.ListView, self).get_queryset(
                        queryset, parameters, request)
                    # For collectibles per account:
                    # If we're listing per item and not per account or owner, hide collected from fake accounts
                    if (model_class.fk_as_owner == 'account'
                        and request
                        and request.GET.get(item_field_name, None)
                        and not request.GET.get('account', None)
                        and not request.GET.get('owner', None)):
                        queryset = filterRealCollectiblesPerAccount(queryset)
                    return queryset

                def top_buttons(self, request, context):
                    buttons = super(_CollectibleCollection.ListView, self).top_buttons(request, context)
                    if (context['ajax']
                        and (('account' in request.GET
                              and int(request.GET['account']) in getAccountIdsFromSession(request))
                             or ('owner' in request.GET and request.user.is_authenticated()
                                 and int(request.GET['owner']) == request.user.id))):
                        if 'account' in request.GET:
                            account_id = int(request.GET['account'])
                            owner_id = None
                        else:
                            owner_id = int(request.GET['owner'])
                            account_id = None
                        classes = self.get_top_buttons_classes(request, context)
                        if context['total_results']:
                            buttons['search_and_filter'] = {
                                'show': True, 'has_permissions': True,
                                'url': self.collection.get_list_url_for_authenticated_owner(
                                    request, fk_as_owner=account_id),
                                'classes': classes,
                                'title': _('Search and filter'),
                                'icon': 'search',
                            }
                        parameters = {}
                        if account_id:
                            parameters[u'add_to_{}'.format(self.collection.name)] = account_id
                        if parent_collection.list_view.quick_add_view:
                            parameters['view'] = parent_collection.list_view.quick_add_view
                        buttons['add_to_collected'] = {
                            'show': True, 'has_permissions': True,
                            'url': parent_collection.get_list_url(parameters=parameters),
                            'classes': classes,
                            'title': self.collection.add_sentence,
                            'icon': self.collection.add_view.view_icon,
                        }
                        if context['total_results']:
                            parameters = {
                                'view': parent_collection.list_view.quick_add_view,
                                u'added_{}'.format(self.collection.name): account_id or owner_id,
                            }
                            if account_id:
                                parameters[u'add_to_{}'.format(self.collection.name)] = account_id
                            buttons['delete_collected'] = {
                                'show': True, 'has_permissions': True,
                                'url': (
                                    parent_collection.get_list_url(parameters=parameters)
                                    if parent_collection.list_view.quick_add_view
                                    else self.collection.get_list_url_for_authenticated_owner(
                                            request, fk_as_owner=account_id, parameters={
                                                'view': 'quick_edit',
                                            })
                                ),
                                'classes': classes,
                                'title': _('Delete {thing}').format(thing=self.collection.plural_title.lower()),
                                'icon': 'delete',
                            }
                    return buttons

                hide_table_fields_headers = True

                def table_fields_headers(self, fields, view=None): # Deprecated
                    return []

                def extra_context(self, context):
                    super(_CollectibleCollection.ListView, self).extra_context(context)
                    if context['view'] == 'quick_edit':
                        context['include_below_item'] = True
                        context['show_item_buttons'] = True

            class ItemView(MagiCollection.ItemView):
                comments_enabled = False
                share_enabled = False

                fields_preselected = [
                    model_class.fk_as_owner or 'owner',
                    item_field_name,
                ]

                def extra_context(self, context):
                    super(_CollectibleCollection.ItemView, self).extra_context(context)
                    context['item_parent'] = getattr(context['item'], item_field_name)

            class AddView(MagiCollection.AddView):
                alert_duplicate = False
                back_to_list_button = False
                max_per_user = 3000

                def get_h1_title(self, request, context, *args, **kwargs):
                    title_prefixes, h1 = super(_CollectibleCollection.AddView, self).get_h1_title(
                        request, context, *args, **kwargs)

                    add_form = context['forms'][u'add_{}'.format(self.collection.name)]
                    if hasattr(add_form, 'collectible_variables'):

                        # Add item to title prefixes
                        title_prefixes.append({
                            'title': add_form.collectible_variables['unicode'],
                            'url': add_form.collectible_variables['item_url'],
                        })

                        # Display which item is being added using the image
                        image = add_form.collectible_variables.get('image_url')
                        if image and image != 'None':
                            h1['image'] = image
                            h1['image_size'] = 100
                            h1['icon'] = None

                    return title_prefixes, h1

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
    multipart = True

    staff_required = False
    permissions_required = []
    one_of_permissions_required = []

    reportable = True
    blockable = True
    allow_suggest_edit = False

    report_edit_templates = {
        'Inappropriate content': 'Something you wrote or uploaded was inappropriate. ' + please_understand_template_sentence,
    }
    report_delete_templates = OrderedDict([
        ('Inappropriate content', 'Something you wrote or uploaded was inappropriate. ' + please_understand_template_sentence),
        ('Troll', 'This content has been detected as being deliberately provocative with the intention of causing disruption or argument and therefore has been deleted. We kindly ask you not to re-iterate your actions and be respectful towards our community.'),
        ('Spam', 'This content has been detected as spam. We do not tolerate such behavior and kindly ask you not to re-iterate your actions or your entire profile might get deleted next time.'),
        ('Wrong details', 'The following details seemed to be wrong: XXXXXXXXX'),
    ])
    report_allow_edit = True
    report_allow_edit_with_permission = None
    report_allow_delete = True
    report_allow_delete_with_permission = None

    def to_form_details(self):
        """
        Used in urls.py
        Dict of field_name -> {
          'label': label,
          'form_field_class': class of the form field,
          'model_field_class': class of the model field,
        }
        """
        formClass = self.form_class
        if str(type(formClass)) == '<type \'instancemethod\'>':
            formClass = formClass(request=None, context={})
        if formClass:
            form = formClass(request=None, collection=self)
            self.form_details = OrderedDict()
            for field_name, field in form.fields.items():
                model_field = modelGetField(self.queryset.model, field_name)
                self.form_details[field_name] = {
                    'label': field.label,
                    'form_field_class': type(field),
                    'model_field_class': model_field,
                    'validators': field.validators,
                }
        else:
            self.form_details = {}

    def to_suggest_edit_choices(self):
        """Used in urls.py"""
        self.suggest_edit_choices = OrderedDict([
            (field_name, (getEnglish(field_details['label']), field_details['label']))
            for field_name, field_details in self.form_details.items()
            if field_name not in (getattr(self.item_view, 'fields_exclude', None) or [])
        ])

    @property
    def translated_fields(self):
        return getattr(self.queryset.model, 'TRANSLATED_FIELDS', [])

    allow_html_in_markdown = False

    @property
    def plural_name(self):
        return '{}s'.format(self.name)

    @property
    def title(self):
        return notTranslatedWarning(string.capwords(self.name))

    @property
    def plural_title(self):
        return notTranslatedWarning(string.capwords(self.plural_name))

    def share_image(self, context, item=None):
        return (
            (get_http_image_url_from_path(getattr(django_settings, 'GENERATED_SHARE_IMAGES', {}).get(
                self.name, None)) if self.auto_share_image else None)
            or self.image
        )

    def before_save(self, request, instance, type=None):
        return instance

    def after_save(self, request, instance, type=None):
        instance.update_all_related_caches(reload_m2m=True, previous_related_caches=getattr(
            request, '_reverse_related_caches_previous_values', {}))
        return instance

    def _get_more_url(self, url, filter_field_name, item, to_preset, ajax=False):
        preset = to_preset(item) if to_preset else None
        return u'{}/{}/{}{}{}'.format(
            '/ajax' if ajax else '',
            url, (
                u'{}/'.format(tourldash(preset))
                if preset
                else u'?{}={}'.format(filter_field_name, item.pk)
            ),
            ('?' if preset else '&') if ajax else '',
            'ajax_modal_only' if ajax else '',
        )

    def to_magifields(self, view, item, context, **kwargs):
        return view.fields_class(view, item, context, **kwargs)

    def _get_value_from_display_property(self, view, item, field_name):
        value = None
        retrieved_display_from_view = False
        if view.view == 'item_view':
            try:
                value = getattr(item, u'display_{}_item'.format(field_name))
                retrieved_display_from_view = True
            except AttributeError:
                pass
        elif view.view == 'list_view':
            try:
                value = getattr(item, u'display_{}_in_list'.format(field_name))
                retrieved_display_from_view = True
            except AttributeError:
                pass
        if not retrieved_display_from_view:
            try:
                value = getattr(item, u'display_{}'.format(field_name))
            except AttributeError:
                pass
        return value

    def to_fields(self, view, item, to_dict=True, only_fields=None, icons=None, images=None, force_all_fields=False, order=None, extra_fields=None, exclude_fields=None, request=None, preselected=None, prefetched_together=None, prefetched=None, images_as_gallery=None):
        """
        Deprecated, in favor of to_magifields (see magifields.py).
        Will still be used when uses_deprecated_to_fields returns True.
        This includes when to_fields, get_extra_fields or fields_extra have been set.
        All sites should stop using these ASAP in order to fully remove this code
        and migrate to magifields.
        """
        if extra_fields is None: extra_fields = []
        if exclude_fields is None: exclude_fields = []
        if only_fields is None: only_fields = []
        if order is None: order = []
        if icons is None: icons = {}
        if images is None: images = {}
        if preselected is None: preselected = []
        if prefetched_together is None: prefetched_together = []
        if prefetched is None: prefetched = []
        name_fields = []
        many_fields = []
        collectible_fields = []
        many_fields_galleries = []

        if hasattr(view, 'fields_exclude'):
            exclude_fields = exclude_fields + view.fields_exclude

        icons = mergeDicts(icons, self.fields_icons, view.fields_icons)

        images = mergeDicts(images, self.fields_images, view.fields_images)

        extra_fields += (view.get_extra_fields(item) or [])
        if hasattr(view, 'fields_extra'):
            extra_fields += view.fields_extra

        if hasattr(view, 'fields_order'):
            order += view.fields_order

        order_settings = {}
        if hasattr(view, 'fields_order_settings'):
            order_settings = view.fields_order_settings

        if hasattr(view, 'get_fields_order'):
            order += view.get_fields_order(item)

        if hasattr(view, 'fields_preselected'):
            preselected += view.fields_preselected

        if hasattr(view, 'fields_prefetched'):
            prefetched += view.fields_prefetched
        prefetched_field_names = [p[0] if isinstance(p, tuple) else p for p in prefetched]

        if hasattr(view, 'fields_prefetched_together'):
            prefetched_together += view.fields_prefetched_together
        prefetched_together_field_names = [p[0] if isinstance(p, tuple) else p for p in prefetched_together]

        language = get_language()

        # Related fields
        #   from reverse_related setting
        related_fields = OrderedDict([
            (details['field_name'] if isinstance(details, dict) else details[0],
             details if isinstance(details, dict) else { # old style with tuples
                 'url': getIndex(details, 1),
                 'verbose_name': getIndex(details, 2),
                 'filter_field_name': getIndex(details, 3),
             }) for details in getattr(item, 'reverse_related', [])
        ])
        #   from many to many
        for m in item._meta.many_to_many:
            if m.name not in related_fields:
                related_fields[m.name] = {}
            if 'verbose_name' not in related_fields[m.name]:
                related_fields[m.name]['verbose_name'] = modelFieldVerbose(type(item), m.name)
            if 'collection_name' not in related_fields[m.name]:
                related_fields[m.name]['collection_name'] = getattr(m.rel.to, 'collection_name', None)
            if 'filter_field_name' not in related_fields[m.name]:
                related_fields[m.name]['filter_field_name'] = m.related.get_accessor_name()

        #   from related objects
        #   + from many to many related objects
        for r in item._meta.get_all_related_objects() + item._meta.get_all_related_many_to_many_objects():
            field_name = r.get_accessor_name()
            if field_name not in related_fields:
                related_fields[field_name] = {}
            if 'collection_name' not in related_fields[field_name]:
                related_fields[field_name]['collection_name'] = getattr(r.model, 'collection_name', None)
            if 'filter_field_name' not in related_fields[field_name]:
                related_fields[field_name]['filter_field_name'] = r.field.name

        for field_name, details in related_fields.items():
            # Exclude field if needed
            if only_fields and field_name not in only_fields:
                continue
            if field_name in exclude_fields:
                continue

            # Get collection if specified
            collection = getMagiCollection(details['collection_name']) if details.get('collection_name', None) else None

            # Set defaults from dict
            url = details.get('url', collection.plural_name if collection else field_name)
            verbose_name = (
                details.get('verbose_name', None)
                or (
                    (collection.title if field_name in prefetched_field_names else collection.plural_title)
                    if collection else None
                ) or toHumanReadable(field_name)
            )
            if callable(verbose_name):
                verbose_name = verbose_name()
            filter_field_name = details.get('filter_field_name', item.collection_name)
            plural_verbose_name = details.get('plural_verbose_name', verbose_name)

            # Max and show per line
            max = 5 if collection else None
            show_per_line = 5
            if details.get('max_per_line', None):
                max = details['max_per_line']
                if max:
                    show_per_line = max
            if details.get('show_per_line', None):
                show_per_line = details['show_per_line']
            if details.get('max', None):
                max = details['max']

            allow_ajax_per_item = details.get('allow_ajax_per_item', True) and (not collection or collection.item_view.ajax)
            allow_ajax_for_more = details.get('allow_ajax_for_more', True) and (not collection or collection.list_view.ajax)
            to_preset = details.get('to_preset', None)
            show_first = details.get('show_first', False)
            show_last = details.get('show_last', False)
            icon = details.get('icon', None) or (collection.icon if collection else None)
            image = details.get('image', None) or (collection.image if collection else None)

            if field_name in prefetched_field_names:
                # Ensure cached total gets updated
                try: getattr(item, 'cached_total_{}'.format(field_name))
                except AttributeError: pass
                for related_item in getattr(item, field_name).all():
                    related_item.request = request
                    d = {
                        'verbose_name': verbose_name,
                        'value': unicode(related_item),
                        'icon': icons.get(field_name, icon),
                        'image': images.get(field_name, image),
                    }
                    template = getattr(related_item, 'template_for_prefetched', None)
                    item_url = getattr(related_item, 'item_url', None)
                    item_view_has_permissions = bool(item_url)
                    if (collection and request
                        and collection.item_view.enabled
                        and not collection.item_view.has_permissions(request, {}, related_item)):
                        item_view_has_permissions = False
                    used_image_field_name, item_image = getImageForPrefetched(related_item, return_field_name=True)
                    if template:
                        d['type'] = 'template'
                        d['template'] = template
                        d['item'] = related_item
                    elif item_url and item_view_has_permissions:
                        d['type'] = 'text_with_link'
                        d['link'] = item_url
                        if allow_ajax_per_item:
                            d['ajax_link'] = getattr(related_item, 'ajax_item_url')
                        d['link_text'] = unicode(_(u'Open {thing}')).format(thing=d['verbose_name'].lower())
                        d['image_for_link'] = getImageForPrefetched(related_item)
                        d['image_for_link'] = item_image
                    elif item_image:
                        d['type'] = 'image_link'
                        d['value'] = item_image
                        d['link_text'] = d['verbose_name']
                        if used_image_field_name == 'image_thumbnail_url':
                            d['link'] = getattr(related_item, 'image_url', item_image)
                        else:
                            d['link'] = item_image
                    d['icon'] = getattr(related_item, 'flaticon', d['icon'])
                    if callable(d['icon']):
                        d['icon'] = d['icon'](item)
                    if 'image' in d:
                        if callable(d['image']):
                            d['image'] = d['image'](item)
                        d['image'] = staticImageURL(d['image'])
                    (many_fields if show_first else many_fields_galleries).append(
                        (u'{}{}'.format(field_name, related_item.pk), d))
            elif field_name in prefetched_together_field_names:
                # Ensure cached total gets updated
                try: getattr(item, 'cached_total_{}'.format(field_name))
                except AttributeError: pass
                d = {
                    'verbose_name': verbose_name,
                    'icon': icons.get(field_name, icon),
                    'image': images.get(field_name, image),
                    'images': [],
                    'links': [],
                    'template': None,
                    'items': [],
                }
                and_more = False
                all_have_images = True
                l_images = []
                l_links = []
                with_template = False
                for i, related_item in enumerate(getattr(item, field_name).all()):
                    related_item.request = request
                    if max and i >= max:
                        and_more = getattr(item, field_name).count() - max
                        break
                    template = getattr(related_item, 'template_for_prefetched', None)
                    item_url = getattr(related_item, 'item_url', None)
                    item_view_has_permissions = True
                    if (collection and request
                        and collection.item_view.enabled
                        and not collection.item_view.has_permissions(request, {}, related_item)):
                        item_view_has_permissions = False
                    to_append = {
                        'link': item_url if item_view_has_permissions else None,
                        'link_text': unicode(related_item),
                    }
                    if item_view_has_permissions and allow_ajax_per_item:
                        to_append['ajax_link'] = getattr(related_item, 'ajax_item_url', None)
                    if template:
                        with_template = True
                        d['type'] = 'templates'
                        d['template'] = template
                        d['items'].append(related_item)
                        d['spread_across'] = True
                    else:
                        link_to_append = to_append.copy()
                        link_to_append['value'] = unicode(related_item)
                        l_links.append(link_to_append)
                        used_image_field_name, item_image = getImageForPrefetched(related_item, return_field_name=True)
                        if item_image:
                            image_to_append = to_append.copy()
                            if not image_to_append['link']:
                                if used_image_field_name == 'image_thumbnail_url':
                                    image_to_append['link'] = getattr(related_item, 'image_url', item_image)
                                else:
                                    image_to_append['link'] = item_image
                            image_to_append['value'] = item_image
                            image_to_append['tooltip'] = unicode(related_item)
                            l_images.append(image_to_append)
                        else:
                            all_have_images = False
                if not with_template:
                    if all_have_images:
                        d['type'] = 'images_links'
                        d['images'] = l_images
                        d['spread_across'] = True
                        d['images_width'] = u'{}%'.format(100 / show_per_line)
                        d['per_line'] = show_per_line
                    else:
                        d['type'] = 'list_links' if item_url else 'list'
                        d['links'] = l_links
                if url:
                    verbose_name = (
                        u'{total} {items}'.format(total=and_more or 0, items=plural_verbose_name.lower())
                        if '{total}' not in unicode(plural_verbose_name)
                        else unicode(plural_verbose_name).format(total=and_more or 0))
                    d['and_more'] = {
                        'hide': not and_more,
                        'link': self._get_more_url(url, filter_field_name, item, to_preset=to_preset),
                        'verbose_name': u'+ {} - {}'.format(verbose_name, _('View all')),
                    }
                    if allow_ajax_for_more:
                        d['and_more']['ajax_link'] = self._get_more_url(
                            url, filter_field_name, item, to_preset=to_preset, ajax=True)
                if d['images'] or d['links'] or d['items']:
                    if 'icon' in d:
                        if callable(d['icon']):
                            d['icon'] = d['icon'](item)
                    if 'image' in d:
                        if callable(d['image']):
                            d['image'] = d['image'](item)
                        d['image'] = staticImageURL(d['image'])
                    (many_fields if show_first else many_fields_galleries).append((field_name, d))
            else:
                try:
                    total = getattr(item, 'cached_total_{}'.format(field_name))
                except AttributeError:
                    continue
                value = (
                    u'{total} {items}'.format(total=total, items=plural_verbose_name.lower())
                    if '{total}' not in unicode(plural_verbose_name)
                    else unicode(plural_verbose_name).format(total=total))
                if total:
                    icon = icons.get(field_name, icon)
                    if callable(icon):
                        icon = icon(item)
                    image = images.get(field_name, image)
                    if callable(image):
                        image = image(item)
                    if image:
                        image = staticImageURL(image)
                    (many_fields_galleries if show_last else many_fields).append((field_name, {
                        'verbose_name': unicode(verbose_name).replace('{total}', ''),
                        'type': 'text_with_link' if url else 'text',
                        'value': value,
                        'ajax_link': (
                            u'/ajax/{}/?{}={}&ajax_modal_only'.format(url, filter_field_name, item.pk)
                        ) if allow_ajax_for_more else None,
                        'link': u'/{}/?{}={}'.format(url, filter_field_name, item.pk),
                        'link_text': _('View all'),
                        'icon': icon,
                        'image': image,
                    }))
        model_fields = []
        # Fields from model
        for field in item._meta.fields:
            field_name = field.name
            if field_name in exclude_fields:
                continue
            if (field_name.startswith('_')
                or field_name in ['id']
                or (field_name == 'image'
                    and 'image' not in only_fields
                    and not getattr(item, u'{}_2x_url'.format(field_name), None))):
                continue
            if only_fields and field_name not in only_fields:
                continue
            # Skip translated strings
            if isTranslationField(field_name, self.translated_fields or []):
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
                # Show dictionary
                value = getattr(item, u't_{}'.format(field_name)).values()
                value = mark_safe(u'<dl>{}</dl>'.format(u''.join([
                    u'<dt>{verbose}</dt><dd>{value}</dd>'.format(**dt)
                    for dt in value if dict(dt)['value'] is not None
                ])))
                if not value or value == '<dl></dl>':
                    continue
            if self.translated_fields and field.name in self.translated_fields:
                language = request.LANGUAGE_CODE if request else get_language()
                # When display_{} is specified, resulting value will be assumed to be in the right language
                value = self._get_value_from_display_property(view, item, field_name)
                if value is not None:
                    result_language = language
                else:
                    result_language, value = item.get_translation_from_dict(
                        field.name, language=language, return_language=True)
                if not value:
                    continue
                if language != result_language:
                    if (language in LANGUAGES_CANT_SPEAK_ENGLISH
                        and not force_all_fields):
                        continue
                    elif not isinstance(field, YouTubeVideoField):
                        value = mark_safe(translationURL(
                            value,
                            from_language=result_language,
                            to_language=language,
                            with_wrapper=True,
                            markdown=field.name.startswith('m_'),
                        ))
                if field.name.startswith('m_'):
                    cache = None
                    if language == 'en':
                        cache = getattr(item, u'cached_{}'.format(field.name[2:]), None)
                    if cache:
                        value = (True, cache)
                    else:
                        value = (False, value)
            is_foreign_key = (isinstance(field, models.models.ForeignKey)
                              or isinstance(field, models.models.OneToOneField))
            if not value and not is_foreign_key:
                try:
                    value = getattr(item, field_name, None)
                except AttributeError:
                    continue
                if value is None or field.name.startswith('m_') and not value[1]:
                    continue

            # HIDE_WHEN_DEFAULT option
            if (getattr(item, u'{}_HIDE_WHEN_DEFAULT'.format(field_name.upper()), False)
                and getattr(item, field.name, None) == field.default):
                continue

            d = {
                'verbose_name': getattr(field, 'verbose_name', field_name.capitalize()),
                'value': value,
                'icon': icons.get(field_name, None),
                'image': images.get(field_name, None),
            }
            # Auto image if exists
            if (not d['image'] and getattr(item, '{}_AUTO_IMAGES'.format(field_name.upper()), False)
                and not field.name.startswith('c_')):
                d['image'] = staticImageURL(getattr(item, field_name), folder=field.name)
            if is_foreign_key:
                if field_name in preselected:
                    cache = getattr(item, field_name, None)
                    if cache:
                        cache.request = request
                else:
                    cache = getattr(item, 'cached_' + field_name, None)
                if not cache:
                    continue
                collection_name = getattr(field.rel.to, 'collection_name', None)
                collection = getMagiCollection(collection_name) if collection_name else None
                allow_ajax = not collection or collection.item_view.ajax
                if collection:
                    d['icon'] = collection.icon or d['icon']
                    d['image'] = collection.image or d['image']
                link = getattr(cache, 'item_url')
                if link:
                    d['type'] = 'text_with_link'
                    d['value'] = getattr(cache, 'unicode', unicode(cache))
                    d['link'] = link
                    if allow_ajax:
                        d['ajax_link'] = getattr(cache, 'ajax_item_url')
                    d['link_text'] = unicode(_(u'Open {thing}')).format(thing=d['verbose_name'].lower())
                    d['image_for_link'] = getImageForPrefetched(cache)
                    d['icon'] = getattr(cache, 'flaticon', d['icon'])
                else:
                    d['type'] = 'text'
                    d['value'] = getattr(cache, 'unicode', field_name)
            elif field.name.startswith('c_'): # original field name
                d['type'] = 'list'
                if (getattr(item, '{}_AUTO_IMAGES'.format(field_name.upper()), False)):
                    d['value'] = [
                        failSafe(lambda: markSafeFormat(
                            u'<img src="{url}" alt="{v}" height="30"> {v}',
                            url=staticImageURL(_value, folder=field.name),
                            v=item.get_verbose_i(field_name, item.get_i(field_name, _value))),
                                 exceptions=[ KeyError ], default=u'')
                        for _value in getattr(item, field_name)
                    ]
            elif field.name.startswith('m_'): # original field name
                d['type'] = 'markdown'
                d['allow_html'] = self.allow_html_in_markdown
            elif isinstance(field, models.models.ManyToManyField):
                d['type'] = 'text_with_link'
                d['value'] = getattr(item, 'cached_total_' + field_name).unicode
                d['link'] = u'/{}/?{}={}'.format(field_name, item.collection_name, item.pk)
                d['link_text'] = _('View all')
            elif isinstance(field, models.models.ImageField):
                image_url = getattr(item, u'{}_url'.format(field_name, None))
                if not image_url:
                    continue
                d['value'] = getattr(item, u'{}_thumbnail_url'.format(field_name))
                hd = getattr(item, u'{}_2x_url'.format(field_name), None)
                if hd:
                    d['type'] = 'image_with_multiple_links'
                    d['popover_title'] = _('Download')
                    d['links'] = [
                        {
                            'verbose': _('Original'),
                            'value': getattr(item, u'{}_original_url'.format(field_name)),
                        },
                        {
                            'verbose': _('High quality'),
                            'value': hd,
                        },
                    ]
                else:
                    d['link_text'] = d['verbose_name']
                    d['type'] = 'image_link'
                    d['link'] = getattr(item, u'{}_original_url'.format(field_name))
                    d['link_text'] = d['verbose_name']

            elif (isinstance(field, models.models.BooleanField)
                  or isinstance(field, models.models.NullBooleanField)):
                d['type'] = 'bool'
            elif isinstance(field, models.models.DateTimeField):
                d['type'] = 'timezone_datetime'
                d['timezones'] = item.get_displayed_timezones(field_name)
                d['ago'] = True
            elif isinstance(field, models.models.DateField):
                d['type'] = 'text'
            elif isinstance(field, models.models.FileField):
                d['type'] = 'link'
                d['link_text'] = t['Download']
                d['value'] = getattr(item, field_name + '_url')
                if not d['value']:
                    continue
            elif isinstance(field, models.models.TextField):
                d['type'] = 'long_text'
            elif field_name == 'itunes_id':
                d['type'] = 'itunes'
            elif isinstance(field, ColorField):
                d['type'] = 'color'
            elif isinstance(field, YouTubeVideoField):
                d['type'] = 'youtube_video'
                d['value'] = YouTubeVideoField.embed_url(d['value'])
                d['spread_across'] = True
            elif isinstance(field, models.models.URLField):
                d['type'] = 'button'
                d['link_text'] = d['verbose_name']
            else:
                d['type'] = 'text'

            value = self._get_value_from_display_property(view, item, field_name)
            if value:
                d['value'] = value

            if callable(d.get('icon', None)):
                d['icon'] = d['icon'](item)
            if callable(d.get('image', None)):
                d['image'] = d['image'](item)
            d['image'] = staticImageURL(d['image'])

            # Fix types
            if d['type'] == 'timezone_datetime' and not hasattr(d['value'], 'strftime'):
                d['type'] = 'text'

            if d['type'] == 'text_with_link':
                many_fields.append((field_name, d))
            elif 'name' in field_name:
                name_fields.append((field_name, d))
            else:
                model_fields.append((field_name, d))
        fields = name_fields + many_fields + model_fields + extra_fields + many_fields_galleries

        # Re-order fields
        if order or force_all_fields:
            dict_fields = dict(fields)
            sorted_fields = OrderedDict()
            for field_name in (order or []):
                for prefix in ['i_', 'c_', 'm_', 'j_']:
                    if field_name.startswith(prefix):
                        field_name = field_name[2:]
                        break
                if only_fields and field_name not in only_fields:
                    continue
                if field_name in dict_fields:
                    sorted_fields[field_name] = dict_fields[field_name]
                elif force_all_fields:
                    sorted_fields[field_name] = {
                        'verbose_name': '',
                        'type': 'text',
                        'value': unicode(item) if field_name == 'unicode' else '',
                    }
            for field_name in (only_fields if only_fields else dict_fields.keys()):
                for prefix in ['i_', 'c_', 'm_', 'j_']:
                    if field_name.startswith(prefix):
                        field_name = field_name[2:]
                        break
                if field_name not in sorted_fields:
                    sorted_fields[field_name] = dict_fields[field_name] if field_name in dict_fields else {
                        'verbose_name': '',
                        'type': 'text',
                        'value': unicode(item) if field_name == 'unicode' else '',
                    }
            if order_settings:
                sorted_fields = newOrder(sorted_fields, **order_settings)
            if to_dict:
                fields = sorted_fields
            else:
                fields = sorted_fields.items()
        elif to_dict and order_settings:
            fields = newOrder(OrderedDict(fields), **order_settings)
        elif to_dict:
            fields = OrderedDict(fields)
        elif order_settings:
            fields = newOrder(OrderedDict(fields), **order_settings).items()
        return fields

    #######################
    # Buttons
    # Only for item_view and list_view

    item_buttons_classes = ['btn', 'btn-secondary', 'btn-lines']
    show_item_buttons = True
    show_item_buttons_justified = True
    show_item_buttons_as_icons = False
    show_item_buttons_in_one_line = True
    show_open_button = 'auto' # can be changed to True/False
    show_edit_button = True
    show_edit_button_permissions_only = []
    show_translate_button = True
    show_report_button = True
    show_suggest_edit_button = True
    show_comments_button = False
    show_share_buttons = False
    show_collect_button = True # Can also be a dictionary when multiple collectibles
    show_collect_total = True

    def buttons_per_item(self, view, request, context, item):
        """
        Used to display buttons below item, only for ItemView and ListView.
        You may override this function, but you're not really supposed to call it yourself.
        Can be overridden per view.
        """
        buttons = OrderedDict()
        def set_base_button(button_name):
            baseButton(
                button_name=button_name, buttons=buttons, view=view, request=request,
                context=context, item=item)
        # Open button
        if self.item_view.enabled and view.view == 'list_view':
            set_base_button('open')
            if context.get('alt_view', None) and 'show_open_button' in context['alt_view']:
                buttons['open']['show'] = context['alt_view']['show_open_button']
            elif (context.get('alt_view', {}) or {}).get('display_style', view.display_style) == 'table':
                buttons['open']['show'] = view.display_style_table_show_open_button
            else:
                buttons['open']['show'] = view.show_open_button
            buttons['open']['title'] = item.open_sentence
            buttons['open']['icon'] = self.icon
            buttons['open']['image'] = self.image
            buttons['open']['has_permissions'] = self.item_view.has_permissions(request, context, item=item)
            buttons['open']['url'] = item.item_url
            if self.item_view.ajax:
                buttons['open']['ajax_url'] = item.ajax_item_url
            if (request.user.is_staff
                and self.item_view.staff_required
                and not view.staff_required):
                buttons['open']['classes'].append('staff-only')
        # Collectible buttons
        for name, collectible_collection in self.collectible_collections.items():
            if (not request.show_collect_button
                or (isinstance(request.show_collect_button, dict)
                    and not request.show_collect_button.get(name, True))
                or not collectible_collection.add_view.enabled):
                continue
            extra_attributes = {}
            quick_add_to_collection = collectible_collection.add_view.quick_add_to_collection(request) if request.user.is_authenticated() else False
            url_to_collectible_add_with_item = lambda url: (
                u'{url}?{item_field_name_id}={item_pk}&{variables}'.format(
                    url=url, item_field_name_id=collectible_collection.item_field_name_id,
                    item_pk=item.pk,
                    variables=u'&'.join([
                        u'{}_{}={}'.format(
                            collectible_collection.item_field_name, variable,
                            unicode(item) if variable == 'unicode' else getattr(item, variable),
                        ) for variable in collectible_collection.add_view.add_to_collection_variables
                        if hasattr(item, variable) or variable == 'unicode']),
                ))
            set_base_button(name)
            buttons[name]['has_permissions'] = False
            buttons[name]['show'] = (
                request.show_collect_button[name]
                if isinstance(request.show_collect_button, dict) else request.show_collect_button)
            buttons[name]['title'] = collectible_collection.add_sentence
            show_total = view.show_collect_total.get(name, True) if isinstance(view.show_collect_total, dict) else view.show_collect_total
            if quick_add_to_collection:
                show_total = True
            if show_total:
                buttons[name]['badge'] = getattr(item, u'total_{}'.format(name), 0)
            buttons[name]['icon'] = (
                collectible_collection.icon
                if collectible_collection.list_view.add_button_use_collection_icon
                else collectible_collection.add_view.view_icon
            )
            buttons[name]['image'] = collectible_collection.image
            buttons[name]['ajax_title'] = u'{}: {}'.format(collectible_collection.add_sentence, unicode(item))
            if collectible_collection.add_view.unique_per_owner:
                extra_attributes['unique-per-owner'] = 'true'
            if quick_add_to_collection:
                extra_attributes['quick-add-to-collection'] = 'true'
                extra_attributes['parent-item-field-name-id'] = collectible_collection.item_field_name_id
                extra_attributes['parent-item-id'] = item.pk
                if collectible_collection.queryset.model.fk_as_owner:
                    add_to_id_from_request = getattr(request, u'add_to_{}'.format(collectible_collection.name), None)
                    if not add_to_id_from_request:
                        quick_add_to_collection = False
                        del(extra_attributes['quick-add-to-collection'])
                        del(extra_attributes['parent-item-field-name-id'])
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
                and not collectible_collection.add_view.requires_permissions()
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
        # Set as background button
        if (view.view == 'list_view'
            and self.list_view.is_backgrounds_model
            and context.get('view', None) == 'set_background'):
            set_base_button('set_background')
            buttons['set_background'].update({
                'has_permissions': request.user.is_authenticated(),
                'title': _('Select {}').format(_('Background').lower()),
                'icon': 'checked',
                'url': u'/set_background/{}/'.format(item.pk),
                'extra_attributes': {
                    'set-background': 'true',
                    'csrf-token': csrf.get_token(request),
                },
            })
        # Set favorite character / other character buttons
        key = None
        if self.list_view.is_favorite_characters_model:
            key = 'FAVORITE_CHARACTERS'
        elif self.list_view.is_other_characters_model:
            key = self.list_view.is_other_characters_model
        if (request and key
            and ((view.view == 'list_view' and context.get('view', None) == 'set_favorite_character')
                 or (view.view == 'item_view' and isValidCharacterPk(item.pk, key=key)))):
            current_favorites = getCharactersUsersFavorites(request.user)
            label = getCharactersFavoriteFieldLabel(key=key)
            total_favoritable = getCharactersTotalFavoritable(key=key)
            # If this character has already been set as favorite, show unset button
            current_nth = isCharactersUserFavorite(
                item.pk, key=key, favorite_characters=current_favorites)
            if current_nth:
                set_base_button('unset_favorite_character')
                buttons['unset_favorite_character'].update({
                    'has_permissions': request.user.is_authenticated(),
                    'title': (
                        _('Clear')
                        if total_favoritable == 1
                        else string_concat(_('Clear'), u' - ', _(ordinalNumber(current_nth)))
                    ),
                    'icon': 'delete',
                    'url': u'/unset_favorite_character/{}/{}/'.format(key, current_nth),
                    'extra_attributes': {
                        'unset-favorite-character': 'true',
                        'csrf-token': csrf.get_token(request),
                    },
                })
            else:
                if view.view == 'item_view':
                    icon = 'profile'
                    title = lambda label: string_concat(_('Customize profile'), u' - ', label)
                    button_icon = 'star'
                    button_title = lambda label: _('Select {}').format(label.lower())
                else:
                    icon = 'checked'
                    title = lambda label: _('Select {}').format(label.lower())
                    button_icon = None
                    button_title = lambda label: _('Select {}').format(label.lower())
                # Show only 1 button
                if total_favoritable == 1 or view.show_item_buttons_as_icons:
                    set_base_button('set_favorite_character')
                    nth = request.GET.get('nth', None) if total_favoritable != 1 else None
                    if nth:
                        url = u'/set_favorite_character/{}/{}/{}/'.format(key, item.pk, request.GET['nth'])
                        label = _(ordinalNumber(int(nth)))
                    else:
                        url = u'/set_favorite_character/{}/{}/'.format(key, item.pk)
                    buttons['set_favorite_character'].update({
                        'has_permissions': request.user.is_authenticated(),
                        'title': title(label),
                        'button_title': button_title(label),
                        'icon': icon,
                        'button_icon': button_icon,
                        'url': url,
                    })
                    if total_favoritable == 1 or nth:
                        buttons['set_favorite_character']['extra_attributes'] = {
                            'set-favorite-character': 'true',
                            'csrf-token': csrf.get_token(request),
                        }
                        if total_favoritable == 1:
                            current_favorite_pk = failSafe(
                                lambda: current_favorites[key][1]['pk'], exceptions=[ KeyError ])
                            if current_favorite_pk:
                                buttons['set_favorite_character']['annotation'] = string_concat(
                                    _('Current'), u' - ', getCharacterNameFromPk(current_favorite_pk))
                    else:
                        buttons['set_favorite_character']['ajax_url'] = u'/ajax' + url
                        buttons['set_favorite_character']['ajax_title'] = buttons['set_favorite_character']['title']
                # Show 1 button per nth
                else:
                    for nth in range(1, total_favoritable + 1):
                        if request.GET.get('nth', None) and request.GET['nth'] != unicode(nth):
                            continue
                        button_name = u'set_favorite_character-{}'.format(nth)
                        set_base_button(button_name)
                        buttons[button_name].update({
                            'has_permissions': request.user.is_authenticated(),
                            'title': title(label),
                            'button_title': button_title(_(ordinalNumber(nth))),
                            'icon': icon,
                            'button_icon': button_icon,
                            'url': u'/set_favorite_character/{}/{}/{}/'.format(key, item.pk, nth),
                            'extra_attributes': {
                                'set-favorite-character': 'true',
                                'csrf-token': csrf.get_token(request),
                            },
                        })
                        current_favorite_pk = failSafe(lambda: current_favorites[key][nth]['pk'],
                                                    exceptions=[ KeyError ])
                        if current_favorite_pk:
                            buttons[button_name]['annotation'] = string_concat(
                                _('Current'), u' - ', getCharacterNameFromPk(current_favorite_pk))

        # Edit button
        if self.edit_view.enabled:
            set_base_button('edit')
            buttons['edit']['show'] = (context.get('alt_view', {}) or {}).get(
                'show_edit_button', view.show_edit_button)
            buttons['edit']['title'] = item.edit_sentence
            buttons['edit']['icon'] = self.edit_view.view_icon
            if (self.edit_view.authentication_required
                and not self.edit_view.requires_permissions()
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
                if ((view.show_edit_button_permissions_only
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
            buttons['translate']['has_permissions'] = self.edit_view.has_translate_permissions(
                request, context)
            if buttons['translate']['has_permissions'] and request.user.is_staff:
                for field in self.translated_fields:
                    if request.GET.get(u'missing_{}_translations'.format(field), None):
                        buttons['translate']['classes'] = [
                            c for c in buttons['translate']['classes'] if c != 'staff-only']
                        parameters = {
                            'language': request.GET.get(u'missing_{}_translations'.format(field)),
                        }
                        buttons['translate']['url'] = addParametersToURL(
                            buttons['translate']['url'], parameters)
                        if buttons['translate']['ajax_url']:
                            buttons['translate']['ajax_url'] = addParametersToURL(
                                buttons['translate']['ajax_url'], parameters)
                        break

            buttons['translate']['title'] = unicode(_('Edit {thing}')).format(thing=unicode(_('Translations')).lower())
            buttons['translate']['icon'] = 'translate'
            buttons['translate']['url'] = u'{}{}translate'.format(buttons['translate']['url'], '&' if '?' in buttons['translate']['url'] else '?')
            if buttons['translate']['ajax_url']:
                buttons['translate']['ajax_url'] = u'{}{}translate'.format(buttons['translate']['ajax_url'], '&' if '?' in buttons['translate']['ajax_url'] else '?')
        # Report buttons: don't show in list view unless there's no item view
        if self.reportable:
            set_base_button('report')
            buttons['report']['show'] = view.show_report_button
            buttons['report']['title'] = item.report_sentence
            buttons['report']['icon'] = 'warning'
            buttons['report']['has_permissions'] = (not request.user.is_authenticated()
                                                    or item.owner_id != request.user.id)
            buttons['report']['url'] = item.report_url
            buttons['report']['open_in_new_window'] = True
        # Suggest edit buttons: don't show in list view unless there's no item view
        if self.allow_suggest_edit:
            set_base_button('suggest_edit')
            buttons['suggest_edit']['show'] = view.show_suggest_edit_button
            buttons['suggest_edit']['title'] = item.suggest_edit_sentence
            buttons['suggest_edit']['icon'] = 'edit'
            buttons['suggest_edit']['has_permissions'] = (
                not request.user.is_authenticated()
                or (item.owner_id != request.user.id and not buttons.get('edit', {}).get('has_permissions', False))
            )
            buttons['suggest_edit']['url'] = item.suggest_edit_url
            buttons['suggest_edit']['open_in_new_window'] = True
        if not context['uses_deprecated_to_fields']:
            # Comments button: shows up on List view + Item view only if ajax
            if self.item_view.comments_enabled:
                set_base_button('comments')
                buttons['comments']['show'] = (
                    view.show_comments_button and (view.view != 'item_view' or context['ajax'])
                )
                buttons['comments']['title'] = _('Comments')
                buttons['comments']['icon'] = 'comments'
                buttons['comments']['has_permissions'] = True
                buttons['comments']['url'] = addParametersToURL(item.http_item_url, anchor='disqus_thread')
                buttons['comments']['open_in_new_window'] = True
            # Share buttons
            if self.item_view.share_enabled:
                set_base_button('share')
                buttons['share']['show'] = view.show_share_buttons
                buttons['share']['title'] = _('Share')
                buttons['share']['icon'] = 'link'
                buttons['share']['has_permissions'] = True
                buttons['share']['url'] = item.share_url
                buttons['share']['template'] = 'include/share'
        return buttons

    def get_parent_prefix(self, request, context):
        """
        Called by item/add/edit views (always) and list view (when a view or preset is set)
        """
        if not self.list_view.enabled or not self.list_view.has_permissions(request, context):
            return None
        return {
            'title': self.list_view.get_page_title(),
            'url': self.get_list_url(),
        }

    #######################
    # Tools - not meant to be overridden

    def get_list_url(self, ajax=False, modal_only=False, parameters=None, preset=None, random=False, full=False):
        return getListURL(
            self.plural_name, ajax=ajax, modal_only=modal_only, parameters=parameters,
            preset=preset, random=random, full=full,
        )

    @property
    def list_url(self):
        return self.get_list_url()

    @property
    def random_url(self):
        return self.get_list_url(random=True)

    def get_add_url(self, ajax=False, type=None):
        return u'{}/{}/add/{}'.format(
            '' if not ajax else '/ajax',
            self.plural_name,
            u'{}/'.format(type) if type else '',
        )

    @property
    def add_url(self):
        return self.get_add_url()

    @property
    def add_sentence(self):
        return _(u'Add {thing}').format(thing=self.title.lower())

    @property
    def edit_sentence(self):
        return _(u'Edit {thing}').format(thing=self.title.lower())

    @property
    def all_views(self):
        return [self.list_view, self.item_view, self.add_view, self.edit_view]

    @property
    def model_name(self):
        return self.queryset.model.__name__.lower()

    def get_buttons_classes(self, buttons_classes, request, context, item=None, size=None, block=None, color=None):
        new_buttons_classes = []
        color = color or (request.GET.get('buttons_color', None) if request else None)
        has_size = False
        for cls in buttons_classes:
            if color:
                if '-main' in cls:
                    cls = cls.replace('-main', u'-{}'.format(color))
                elif '-secondary' in cls:
                    cls = cls.replace('-secondary', u'-{}'.format(color))
                elif cls == 'btn-link':
                    cls = u'btn-link-{}'.format(color)
            if size:
                if cls in ['btn-xs', 'btn-sm', 'btn-md', 'btn-lg', 'btn-xl']:
                    cls = u'btn-{}'.format(size)
                    has_size = True
            new_buttons_classes.append(cls)
        if block:
            new_buttons_classes.append('btn-block')
        if size and not has_size:
            new_buttons_classes.append(u'btn-{}'.format(size))
        return new_buttons_classes

    def set_buttons_auto_open(self, buttons):
        """
        Should only be called by list view, not item view
        When open show is auto, will display open button when there are other visible buttons
        """
        if 'open' in buttons and buttons['open']['show'] == 'auto':
            buttons['open']['show'] = False
            for button_name, button in buttons.items():
                if (button_name != 'open'
                    and button['show'] and button['has_permissions']
                    and 'staff-only' not in button['classes']):
                    buttons['open']['show'] = True
                    break

    def __unicode__(self):
        return u'MagiCollection {}'.format(self.name)

    #######################
    # Collection Views

    class ListView(_View):
        view = 'list_view'
        view_icon = 'icons-list'

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
        display_style_table_fields = ['image', 'unicode']
        display_style_table_classes = ['table']
        display_style_table_show_open_button = True
        display_style_table_item_buttons_classes = [ 'btn', 'btn-secondary-link', 'btn-lines' ]
        per_line = 3
        col_break = 'md'
        page_size = 12
        item_padding = 20 # Only used with default item template
        item_max_height = 300

        prefetched_per_line = property(lambda _s: _s.per_line)
        prefetched_page_size = property(lambda _s: _s.page_size)

        ajax_item_popover = False
        hide_icons = False
        allow_random = True
        as_profile_tab = False
        profile_tab_name = property(lambda _s: _s.get_page_title())

        auto_filter_form = False

        fields_class = property(propertyFromCollection('fields_class'))
        fields_icons = {}
        fields_images = {}
        fields_preselected_subfields = property(propertyFromCollection('fields_preselected_subfields'))
        item_buttons_classes = property(propertyFromCollection('item_buttons_classes'))
        show_item_buttons = property(propertyFromCollection('show_item_buttons'))
        show_item_buttons_justified = property(propertyFromCollection('show_item_buttons_justified'))
        show_item_buttons_as_icons = property(propertyFromCollection('show_item_buttons_as_icons'))
        show_item_buttons_in_one_line = property(propertyFromCollection('show_item_buttons_in_one_line'))
        show_open_button = property(propertyFromCollection('show_open_button'))
        show_edit_button = property(propertyFromCollection('show_edit_button'))
        show_edit_button_permissions_only = property(propertyFromCollection('show_edit_button_permissions_only'))
        show_translate_button = property(propertyFromCollection('show_translate_button'))
        # Show report/suggest_edit buttons only if not in item view
        show_report_button = property(lambda _s: not _s.collection.item_view.enabled or not _s.collection.item_view.show_report_button)
        show_suggest_edit_button = property(lambda _s: not _s.collection.item_view.enabled or not _s.collection.item_view.show_suggest_edit_button)
        show_comments_button = False
        show_share_buttons = False
        show_collect_button = property(propertyFromCollection('show_collect_button'))
        show_collect_total = property(propertyFromCollection('show_collect_total'))

        top_buttons_classes = ['btn', 'btn-lg', 'btn-block', 'btn-main']
        top_buttons_per_line = None
        show_search_results = True
        show_items_names = False
        show_items_names_in_source_languages = property(propertyFromCollection('show_items_names_in_source_languages'))
        authentication_required = False
        distinct = False
        add_button_subtitle = None
        full_width = False
        show_relevant_fields_on_ordering = True
        hide_sidebar = False

        item_template = 'default_item_in_list'
        item_blocked_template = None
        auto_reloader = True
        alt_views = []
        quick_add_view = None
        show_section_header_on_change = None

        ordering_fields_class = property(lambda _s: _s.collection.fields_class)
        table_fields_class = property(lambda _s: _s.collection.fields_class)

        def check_random_permissions(self, request, context):
            return self.allow_random and self.check_permissions(request, context)

        def has_permissions_to_see_in_navbar(self, request, context):
            return self.has_permissions(request, context)

        def get_queryset(self, queryset=None, parameters={}, request=None):
            return super(MagiCollection.ListView, self).get_queryset(
                queryset=self.collection._collectibles_queryset(self, queryset=queryset, request=request),
                parameters=parameters, request=request)

        def buttons_per_item(self, *args, **kwargs):
            return self.collection.buttons_per_item(self, *args, **kwargs)

        def to_magifields(self, item, context, **kwargs):
            return self.collection.to_magifields(self, item, context, **kwargs)

        def to_magi_ordering_fields(self, item, context, ordering_fields=[], **kwargs):
            return self.ordering_fields_class(
                self, item, context, ordering_fields=ordering_fields, **kwargs)

        def to_magi_table_fields(self, item, context, table_fields=[], **kwargs):
            return self.table_fields_class(
                self, item, context, table_fields=table_fields, **kwargs
            )

        # Deprecated
        def to_fields(self, *args, **kwargs):
            return self.collection.to_fields(self, *args, **kwargs)

        # Deprecated
        ordering_fields = to_fields

        # Deprecated
        def table_fields(self, *args, **kwargs):
            return self.collection.item_view.to_fields(*args, **kwargs)

        # Deprecated
        def table_fields_headers(self, fields, view=None):
            headers = []
            for field_name in fields:
                if field_name == 'unicode':
                    field_name = 'name'
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

        hide_table_fields_headers = False

        def show_add_button(self, request):
            return True

        @property
        def filter_cuteform(self):
            return self.collection.filter_cuteform

        @property
        def default_ordering(self):
            if self.collection.queryset.model._meta.ordering:
                return u','.join(self.collection.queryset.model._meta.ordering)
            if hasattr(self.collection.queryset.model, 'creation'):
                return '-creation'
            return '-id'

        def top_buttons(self, request, context):
            """
            Used to display buttons at the beginning of the list view.
            You may override this function, but you're not really supposed to call it yourself.
            """
            buttons = OrderedDict()
            top_buttons_classes = self.get_top_buttons_classes(request, context)
            # Alt view buttons
            for alt_view_name, alt_view_details in self.alt_views.items():
                buttons[alt_view_name] = {
                    'has_permissions': True, # if you have permissions for the list view, alt view should work too
                    'ajax_url': False,
                    'open_in_new_window': False,
                    'classes': top_buttons_classes,
                    'show': alt_view_details.get('show_as_top_button', False) and not (
                        # Don't show table alt views when getting started because they don't have add buttons
                        'get_started' in request.GET and alt_view_details.get('display_style', None) == 'table'
                    ),
                }
                if context.get('view', None) == alt_view_name:
                    buttons[alt_view_name].update({
                        'title': u'{} ({})'.format(self.get_page_title(), _('Default')),
                        'url': self.collection.get_list_url(),
                        'icon': self.collection.icon,
                        'image': self.collection.image,
                    })
                else:
                    buttons[alt_view_name].update({
                        'url': self.collection.get_list_url(parameters={ 'view': alt_view_name }),
                        'icon': alt_view_details.get('icon', self.collection.icon if not alt_view_details.get('image', None) else None),
                        'image': alt_view_details.get('image', self.collection.image),
                        'title': alt_view_details['verbose_name'],
                    })
            # Add buttons
            if self.collection.add_view.enabled:
                for_all_buttons = {
                    'show': self.show_add_button(request) and 'get_started' not in request.GET,
                    'has_permissions': self.collection.add_view.has_permissions(request, context),
                    'ajax_url': False, # Top add buttons should always open a full page
                    'open_in_new_window': False,
                    'classes': (
                        top_buttons_classes
                        + (['staff-only'] if self.collection.add_view.staff_required and not self.staff_required else [])
                    ),
                    'title': self.collection.add_sentence,
                }
                if (self.collection.add_view.authentication_required
                    and not self.collection.add_view.requires_permissions()
                    and not request.user.is_authenticated()):
                    for_all_buttons['has_permissions'] = True
                if self.collection.types:
                    for (type, button) in self.collection.types.items():
                        if not button.get('show_button', True):
                            continue
                        if (not self.collection.add_view.has_permissions(request, context)
                            or not self.collection.add_view.has_type_permissions(request, context, type=type)):
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
                        'icon': self.collection.add_view.view_icon,
                        'image': self.collection.image,
                        'subtitle': self.collection.list_view.add_button_subtitle,
                    }, **for_all_buttons)
            return buttons

        def get_page_title(self):
            if self.collection.navbar_link and not self.collection.navbar_link_list:
                return self.collection.plural_title
            return _(u'{things} list').format(things=self.collection.plural_title)

        def get_h1_title(self, request, context, view=None, preset=None):
            """
            title_prefixes = list of dict with { title, url, include_in_title }
            h1 = dict with { title, icon, image, classes, attributes, image_size }, none required
            """
            h1 = {
                'classes': 'list-page-title list-page-title-{}'.format(self.collection.name),
            }

            # Navbar prefix

            title_prefixes = self.collection.get_title_prefixes(request, context)

            # Preset and view prefixes

            if view:
                # Don't show view details if view is not visible anywhere
                if (('show_view_title' not in self.alt_views[view]
                     and (self.alt_views[view].get('hide_in_filter', False)
                          and self.alt_views[view].get('hide_in_navbar', False)))
                    or ('show_view_title' in self.alt_views[view]
                        and not self.alt_views[view]['show_view_title'])):
                    view = None

            def _preset_title():
                h1['title'] = self.collection.list_view.filter_form.get_preset_label(
                    preset, self.collection.plural_title)
                h1['icon'] = self.collection.list_view.filter_form.get_preset_icon(preset)
                h1['image'] = self.collection.list_view.filter_form.get_preset_image(preset)
            def _list_title():
                h1['title'] = self.get_page_title()
                h1['icon'] = self.collection.icon
                h1['image'] = self.collection.image
            def _view_title():
                h1['title'] = self.alt_views[view]['verbose_name']
                h1['icon'] = self.alt_views[view].get('icon')
                h1['image'] = self.alt_views[view].get('image')
            def _parent_prefix():
                parent_prefix = self.collection.get_parent_prefix(request, context)
                if parent_prefix:
                    title_prefixes.append(parent_prefix)
            def _view_prefix():
                title_prefixes.append({
                    'title': self.alt_views[view]['verbose_name'],
                    'url': self.collection.get_list_url(parameters={ 'view': view }),
                })

            if preset and view:
                # Ex: Cards / Statistics / [ All R cards ]
                _parent_prefix()
                _view_prefix()
                _preset_title()
            elif view:
                # Ex: Cards / [ Statistics ]
                _parent_prefix()
                _view_title()
            elif preset:
                # Ex: Cards / [ All R cards ]
                _parent_prefix()
                _preset_title()
            else:
                # Ex: [ Cards ]
                _list_title()

            return title_prefixes, h1

        def to_filter_form_class(self):
            """Used in urls.py"""
            if self.auto_filter_form:
                self.filter_form = forms.to_auto_filter_form(self)

        def to_filters_details(self):
            """
            Used in urls.py
            Dict of field_name -> {
              'form_field_class': class of the form field,
              'model_field_class': class of the model field,
              'form_default': default value when initializing the form,
            }
            Will also automatically add cuteform for merged fields.
            """
            formClass = self.filter_form
            if str(type(formClass)) == '<type \'instancemethod\'>':
                formClass = formClass(request=None, context={})
            if formClass:
                form = formClass(request=None, collection=self.collection)
                self.filters_details = OrderedDict()
                self.filters_with_default_form_values = []
                for field_name, field in form.fields.items():
                    model_field = modelGetField(self.collection.queryset.model, field_name)
                    self.filters_details[field_name] = {
                        'form_field_class': type(field),
                        'model_field_class': model_field,
                        'form_default': getattr(field, 'initial', None),
                        # 'model_default': getattr(model_field, 'default', None),
                    }
                    if hasValue(self.filters_details[field_name]['form_default']):
                        self.filters_with_default_form_values.append(field_name)
            else:
                self.filters_details = {}

        def auto_cuteform_for_filter_forms(self):
            if str(type(self.filter_form)) == '<type \'instancemethod\'>':
                return
            if not getattr(self.filter_form, 'merge_fields', None):
                return
            if not hasattr(self.filter_form, 'cuteform'):
                self.filter_form.cuteform = {}
            all_cuteforms_for_filter_form = mergeDicts(
                self.collection.filter_cuteform,
                self.filter_form.cuteform,
            )
            if not all_cuteforms_for_filter_form:
                return
            def _autoCuteFormForMergedFields_foreachMergeFields(new_field_name, details, fields):
                if new_field_name in all_cuteforms_for_filter_form:
                    return
                for field_name in fields:
                    if (field_name not in all_cuteforms_for_filter_form
                        or not all_cuteforms_for_filter_form[field_name].get('to_cuteform', None)):
                        return
                cuteform_name, cuteform = mergedFieldCuteForm(
                    all_cuteforms_for_filter_form, merged_fields=fields,
                    model=self.collection.queryset.model, as_modal=True, add_to_cuteform=False,
                )
                self.filter_form.cuteform[cuteform_name] = cuteform
            self.filter_form.foreach_merge_fields(_autoCuteFormForMergedFields_foreachMergeFields)

        def get_clear_url(self, request):
            return self.collection.get_list_url(
                parameters={
                    'view': request.GET['view'],
                } if request and request.GET.get('view', None) else None,
            )

        #######################
        # Tools - not meant to be overridden

        def get_top_buttons_classes(self, request, context, size=None, block=None, color=None):
            return self.collection.get_buttons_classes(
                self.top_buttons_classes, request, context, size=size, block=block, color=color)

        def get_item_buttons_classes(self, request, context, item=None, size=None, block=None, color=None):
            return self.collection.get_buttons_classes(
                (context.get('alt_view', {}) or {}).get('item_buttons_classes', (
                    self.display_style_table_item_buttons_classes
                    if context.get('display_style', None) == 'table'
                    else self.item_buttons_classes)),
                request, context,
                item=item,
                size=size,
                block=block,
                color=color,
            )

        # Caches

        is_backgrounds_model = False
        is_favorite_characters_model = False
        is_other_characters_model = False

        _alt_view_choices = None
        _alt_view_visible_choices = None

        def to_alt_views(self):
            """Used in urls.py"""
            if not self.alt_views:
                self.alt_views = []

            # Set background
            if self.collection.queryset.model == BACKGROUNDS_MODEL:
                self.is_backgrounds_model = True
                self.alt_views.append(('set_background', {
                    'verbose_name': __(u'{} - {}', _('Customize profile'), _('Background')),
                    'icon': 'pictures',
                    'filter_queryset': BACKGROUNDS_FILTER,
                    'hide_in_navbar': True,
                    'hide_in_filter': True,
                    'show_title': True,
                    'show_open_button': False,
                }))

            # Set favorite character(s)
            # It's OK to call getCharactersFavoriteFieldLabel because
            # favorite_character_name has been set at this point.
            if self.collection.queryset.model == FAVORITE_CHARACTERS_MODEL:
                self.is_favorite_characters_model = True
                self.alt_views.append(('set_favorite_character', {
                    'verbose_name': __(u'{} - {}', _('Customize profile'), getCharactersFavoriteFieldLabel()),
                    'icon': 'star',
                    'filter_queryset': FAVORITE_CHARACTERS_FILTER,
                    'hide_in_navbar': True,
                    'hide_in_filter': True,
                    'show_title': True,
                    'show_open_button': False,
                }))
            else:
                for key, other_characters_model in OTHER_CHARACTERS_MODELS.items():
                    if (self.collection.queryset.model == other_characters_model['model']
                        and other_characters_model.get('allow_set_as_favorite_on_profile', False)):
                        self.is_other_characters_model = key
                        self.alt_views.append((u'set_favorite_character', {
                            'verbose_name': __(
                                u'{} - {}', _('Customize profile'),
                                getCharactersFavoriteFieldLabel(key=key),
                            ),
                            'icon': 'star',
                            'filter_queryset': other_characters_model.get('filter', lambda q: q),
                            'hide_in_navbar': True,
                            'hide_in_filter': True,
                            'show_title': True,
                            'show_open_button': False,
                        }))
                        break

            # Make alt views into an ordered dict
            self.alt_views = OrderedDict(self.alt_views)

            # Cache: Form choices
            self._alt_view_choices = [('', self.collection.plural_title)] + [
                (view_name, view.get('verbose_name', view_name))
                for view_name, view in self.alt_views.items()
            ]

            # Cache: Visible form choices
            self._alt_view_visible_choices = [
                view_name for view_name, view in self.alt_views.items()
                if (not view.get('hide_in_filter', False)
                    and view.get('hide_in_navbar', False)
                    and not view.get('show_as_top_button', False))
            ]

    class ItemView(_View):
        view = 'item_view'

        @property
        def view_icon(self):
            return self.collection.icon or 'deck'

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
        share_templates = False
        full_width = False
        auto_reloader = True
        template = 'default'
        item_padding = 20 # Only used with default item template
        item_max_height = 600
        ajax_item_max_height = 400

        hide_icons = False
        fields_class = property(propertyFromCollection('fields_class'))
        fields_icons = {}
        fields_images = {}
        fields_preselected = []
        fields_preselected_subfields = property(propertyFromCollection('fields_preselected_subfields'))
        fields_prefetched = []
        fields_prefetched_together = []
        fields_suggest_edit = []
        fields_prefetched_even_on_high_traffic = []

        show_item_name_in_source_languages = property(propertyFromCollection('show_items_names_in_source_languages'))
        show_item_buttons = property(propertyFromCollection('show_item_buttons'))
        item_buttons_classes = property(propertyFromCollection('item_buttons_classes'))
        show_item_buttons_as_icons = property(propertyFromCollection('show_item_buttons_as_icons'))
        show_open_button = property(propertyFromCollection('show_open_button'))
        show_edit_button = property(propertyFromCollection('show_edit_button'))
        show_edit_button_permissions_only = property(propertyFromCollection('show_edit_button_permissions_only'))
        show_translate_button = property(propertyFromCollection('show_translate_button'))
        show_report_button = property(propertyFromCollection('show_report_button'))
        show_suggest_edit_button = property(propertyFromCollection('show_suggest_edit_button'))
        show_comments_button = True
        show_share_buttons = True
        show_collect_button = property(propertyFromCollection('show_collect_button'))
        show_collect_total = property(propertyFromCollection('show_collect_total'))
        # Note: if you use the 'default' template, the following 2 will be ignored:
        show_item_buttons_justified = property(propertyFromCollection('show_item_buttons_justified'))

        @property
        def show_item_buttons_in_one_line(self):
            if self.template == 'default':
                return False
            return self.collection.show_item_buttons_in_one_line

        show_owner = False
        show_faq = False
        show_article_ld = False

        def _preselect_owner(self, queryset, request=None):
            if isRequestAjax(request) or (not self.show_article_ld and not self.show_owner):
                return queryset
            if (modelHasField(queryset.model, '_cache_owner_username')
                or modelHasField(queryset.model, '_cache_owner')):
                return queryset
            return queryset.select_related('owner')

        def get_queryset(self, queryset=None, parameters={}, request=None):
            """
            Will call self.collection._collectibles_queryset to pre-select total collectible for authenticated user
            Will call self._preselect_owner to pre-select the owner in case we show the
            article Ld for SEO or we show the owner.
            """
            return super(MagiCollection.ItemView, self).get_queryset(
                queryset=self._preselect_owner(self.collection._collectibles_queryset(
                    self, queryset=queryset, request=request), request=request),
                parameters=parameters, request=request)

        def to_magifields(self, item, context, **kwargs):
            return self.collection.to_magifields(self, item, context, **kwargs)

        # Deprecated
        def to_fields(self, *args, **kwargs):
            return self.collection.to_fields(self, *args, **kwargs)

        def buttons_per_item(self, *args, **kwargs):
            return self.collection.buttons_per_item(self, *args, **kwargs)

        def share_image(self, context, item):
            for field_name in ['http_share_image_url', 'http_top_image_item_url',
                               'http_top_image_url', 'http_image_url', 'DEFAULT_IMAGE']:
                if hasattr(item, field_name):
                    return staticImageURL(getattr(item, field_name))
            return self.collection.share_image(context, item)

        def get_item(self, request, pk):
            return { 'pk': pk }

        def get_h1_title(self, request, context, item):
            """
            title_prefixes = list of dict with { title, url, include_in_title }
            h1 = dict with { title, icon, image, classes, attributes, image_size }, none required
            """
            title_prefixes = self.collection.get_title_prefixes(request, context)

            parent_prefix = self.collection.get_parent_prefix(request, context)
            if parent_prefix:
                title_prefixes.append(parent_prefix)

            type = item.type if self.collection.types else None

            h1 = {
                'title': self.get_page_title(item=item),
                'icon': (
                    getattr(item, 'flaticon', None)
                    or (self.collection.types[type].get('icon', None) if type else None)
                    or self.collection.icon
                ),
                'image': (
                    (self.collection.types[type].get('image', None) if type else None)
                    or self.collection.image
                ),
                'classes': 'item-page-title item-page-title-{}'.format(self.collection.name),
            }

            return title_prefixes, h1

        def get_page_title(self, item=None):
            return unicode(item) if item else self.collection.title

        #######################
        # Tools - not meant to be overridden

        def get_item_buttons_classes(self, request, context, item=None, size=None, block=None, color=None):
            return self.collection.get_buttons_classes(
                self.item_buttons_classes, request, context,
                item=item,
                size=(size or ('lg' if self.template == 'default' else None)),
                block=block,
                color=color,
            )

    class AddView(_View):
        view = 'add_view'
        view_icon = 'add'

        # Optional variables without default
        otherbuttons_template = None
        after_template = None
        max_per_user = None
        max_per_user_per_day = None
        max_per_user_per_hour = None
        max_per_user_per_minute = None

        def before_save(self, request, instance, type=None):
            return self.collection.before_save(request, instance, type=type)

        def after_save(self, request, instance, type=None):
            return self.collection.after_save(request, instance, type=type)

        def extra_context(self, context):
            pass

        # Optional variables with default values
        show_title = True
        authentication_required = True
        allow_next = True
        alert_duplicate = True
        back_to_list_button = True
        unique_per_owner = False

        @property
        def savem2m(self):
            return bool(self.collection.queryset.model._meta.many_to_many)

        def quick_add_to_collection(self, request):
            return False # for collectibles only

        add_to_collection_variables = [
            'unicode',
            'item_url',
            'image_url',
        ]

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
            return self.collection.get_list_url(ajax, modal_only=ajax)

        def check_type_permissions(self, request, context, type=None):
            pass

        def get_h1_title(self, request, context, type=None):
            """
            title_prefixes = list of dict with { title, url, include_in_title }
            h1 = dict with { title, icon, image, classes, attributes, image_size }, none required
            """
            title_prefixes = self.collection.get_title_prefixes(request, context)

            parent_prefix = self.collection.get_parent_prefix(request, context)
            if parent_prefix:
                title_prefixes.append(parent_prefix)

            if type:
                title_prefixes.append({
                    'title': self.collection.types[type].get('title', type),
                })

            h1 = {
                'title': self.get_page_title(type=type),
                'icon': (
                    (self.collection.types[type].get('icon', None) if type else None)
                    or self.collection.icon
                ),
                'image': (
                    (self.collection.types[type].get('image', None) if type else None)
                    or self.collection.image
                ),
                'classes': 'form-title add-view-title add-view-title-{}'.format(self.collection.name),
            }

            return title_prefixes, h1

        def get_page_title(self, type=None):
            return self.collection.add_sentence

        #######################
        # Tools - not meant to be overridden

        def has_type_permissions(self, request, context, type=None):
            try:
                self.check_type_permissions(request, context, type=type)
            except (PermissionDenied, HttpRedirectException, Http404):
                return False
            return True

    class EditView(_View):
        view = 'edit_view'
        view_icon = 'edit'

        # Optional variables without default
        otherbuttons_template = None
        after_template = None

        def before_save(self, request, instance, type=None):
            return self.collection.before_save(request, instance, type=type)

        def after_save(self, request, instance, type=None):
            return self.collection.after_save(request, instance, type=type)

        def extra_context(self, context):
            pass

        # Optional variables with default values
        show_title = True
        authentication_required = True
        allow_delete = False
        @property
        def owner_only(self):
            return (
                not self.collection.reportable
                and not self.collection.allow_suggest_edit
                and not self.staff_required
            )
        owner_or_staff_only = False
        owner_only_or_permissions_required = []
        @property
        def owner_only_or_one_of_permissions_required(self):
            if self.staff_required:
                return []
            permissions = []
            if self.collection.reportable:
                permissions += ['edit_reported_things']
            if self.collection.allow_suggest_edit:
                permissions += ['edit_suggested_edits']
            return permissions
        allow_next = True

        @property
        def savem2m(self):
            return bool(self.collection.queryset.model._meta.many_to_many)

        back_to_list_button = True
        show_cascade_before_delete = True

        def allow_cascade_delete_up_to(self, request):
            return 10

        @property
        def fields_preselected(self):
            """Defaults to all the fields known to be in the edit form that are ForeignKey or OneToOneField"""
            return [
                field_name
                for field_name, field_details in self.collection.form_details.items()
                if (isinstance(field_details['model_field_class'], models.models.ForeignKey)
                    or isinstance(field_details['model_field_class'], models.models.OneToOneField))
            ]

        @property
        def fields_prefetched(self):
            """Defaults to all the fields known to be in the edit form that are ManyToManyField"""
            return [
                field_name
                for field_name, field_details in self.collection.form_details.items()
                if isinstance(field_details['model_field_class'], models.models.ManyToManyField)
            ]

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
            """Used in urls.py"""
            self._translate_form_class = forms.to_translate_form_class(self)

        def translate_form_class(self, request, context):
            return self._translate_form_class

        def redirect_after_edit(self, request, item, ajax):
            if self.collection.item_view.enabled:
                return item.item_url if not ajax else item.ajax_item_url
            return self.collection.get_list_url(ajax, modal_only=ajax)

        def before_delete(self, request, item, ajax):
            pass

        def after_delete(self, request):
            pass

        def redirect_after_delete(self, request, item, ajax):
            return self.collection.get_list_url(ajax, modal_only=ajax)

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

        def get_h1_title(self, request, context, item, type=None, is_translate=False):
            """
            title_prefixes = list of dict with { title, url, include_in_title }
            h1 = dict with { title, icon, image, classes, attributes, image_size }, none required
            """
            title_prefixes = self.collection.get_title_prefixes(request, context)

            parent_prefix = self.collection.get_parent_prefix(request, context)
            if parent_prefix:
                title_prefixes.append(parent_prefix)

            title_prefixes.append({
                'title': unicode(item),
                'url': item.item_url if self.collection.item_view.enabled else None,
            })

            h1 = {
                'title': self.collection.edit_sentence if not is_translate else _('Translations'),
                'icon': (
                    getattr(item, 'flaticon', None)
                    or (self.collection.types[type].get('icon', None) if type else None)
                    or self.collection.icon
                ),
                'image': (
                    (self.collection.types[type].get('image', None) if type else None)
                    or self.collection.image
                ),
                'classes': 'form-title edit-view-title edit-view-title-{}'.format(self.collection.name),
            }

            return title_prefixes, h1

        def get_page_title(self, item=None, type=None, is_translate=False):
            if item and is_translate:
                return u'{}: {}'.format(_('Translations'), unicode(item))
            elif item:
                return u'{}: {}'.format(item.edit_sentence, unicode(item))
            return self.collection.edit_sentence

        #######################
        # Tools - not meant to be overridden

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
# Abstract collections

class MainItemCollection(MagiCollection):
    blockable = False
    reportable = False
    allow_suggest_edit = True
    allow_html_in_markdown = True
    auto_share_image = True

    class ItemView(MagiCollection.ItemView):
        show_suggest_edit_button = True
        share_templates = True

        @property
        def show_owner(self):
            return self.template == 'default'

        @property
        def show_faq(self):
            return self.template == 'default'

        @property
        def show_article_ld(self):
            return self.template == 'default'

    class AddView(MagiCollection.AddView):
        staff_required = True
        permissions_required = ['manage_main_items']

    class EditView(MagiCollection.EditView):
        staff_required = True
        permissions_required = ['manage_main_items']
        allow_delete = True

CommunityMainItemCollection = makeCollectionCommunity(MainItemCollection)

class SubItemCollection(MainItemCollection):
    """
    The list view is visible to all users, but only in the navbar for translators and database maintainers.
    The item view doesn't have comments.
    The add/edit view are only for translators and database maintainers.
    The form to edit the main item has direct links to add/edit sub items.
    """
    # Required variable (either)
    @property
    def main_collection(self):
        if self.main_collections:
            return self.main_collections[0]
        raise NotImplementedError('Main collection is required in a SubItemCollection')
    main_collections = []

    # Overridable variable
    main_fk = property(lambda _s: _s.main_collection)
    main_related = property(lambda _s: _s.plural_name)
    main_many2many = False

    # Defaults
    navbar_link_list = 'staff'
    auto_share_image = False

    def get_add_url(self, ajax=False, type=None, item=None):
        return addParametersToURL(
            super(SubItemCollection, self).get_add_url(ajax=ajax, type=type),
            { self.main_fk: item.pk } if item else {},
        )

    def to_form_class(self):
        class _Form(forms.AutoForm):
            def __init__(self, *args, **kwargs):
                super(_Form, self).__init__(*args, **kwargs)
                if not self.is_creating and self.collection.main_fk in self.fields:
                    del(self.fields[self.collection.main_fk])
            class Meta(forms.AutoForm.Meta):
                model = self.queryset.model
                allow_initial_in_get = (self.main_fk, )
        self._form_class = _Form

    def to_main_item_url(self, item):
        return getattr(item, self.main_fk).item_url

    class ListView(MainItemCollection.ListView):
        def has_permissions_to_see_in_navbar(self, request, context):
            return (
                super(SubItemCollection.ListView, self).has_permissions_to_see_in_navbar(request, context)
                and request.user.is_authenticated()
                and (request.user.hasOneOfPermissions([
                    'manage_main_items',
                    'translate_items',
                ]))
            )

    class ItemView(MainItemCollection.ItemView):
        comments_enabled = False

    class AddView(MainItemCollection.AddView):
        back_to_list_button = False

        def redirect_after_add(self, request, item, ajax):
            if self.collection.main_many2many:
                return super(SubItemCollection.AddView, self).redirect_after_add(request, item, ajax)
            return self.collection.to_main_item_url(item) if not ajax else '/ajax/successadd/'

    class EditView(MainItemCollection.EditView):
        back_to_list_button = False

        def redirect_after_edit(self, request, item, ajax):
            if self.collection.main_many2many:
                return super(SubItemCollection.EditView, self).redirect_after_edit(request, item, ajax)
            return self.collection.to_main_item_url(item) if not ajax else '/ajax/successedit/'

_base_CommunitySubItemCollection = makeCollectionCommunity(SubItemCollection)
class CommunitySubItemCollection(_base_CommunitySubItemCollection):
    navbar_link_list = 'more'
    auto_share_image = False

    class ListView(_base_CommunitySubItemCollection.ListView):
        def has_permissions_to_see_in_navbar(self, request, context):
            return (
                super(CommunitySubItemCollection.ListView, self).has_permissions_to_see_in_navbar(request, context)
                and request.user.is_authenticated()
            )

############################################################
############################################################
############################################################

############################################################
# Account Collection

class AccountCollection(MagiCollection):
    title = _('Account')
    plural_title = _('Accounts')
    icon = 'leaderboard'
    queryset = ACCOUNT_MODEL.objects.all()
    report_allow_delete = False
    form_class = forms.AccountForm
    fields_class = magifields.AccountFields
    navbar_link_list = 'community'
    show_open_button = False

    filter_cuteform = {
        'has_friend_id': {
            'type': CuteFormType.YesNo,
        },
        'accept_friend_requests': {
            'type': CuteFormType.YesNo,
        },
        'color': {
            'type': CuteFormType.Images,
        },
        'i_os': {
            'to_cuteform': lambda k, v: ACCOUNT_MODEL.get_reverse_i('os', k),
            'transform': CuteFormTransform.FlaticonWithText,
        },
        'i_play_with': {
            'to_cuteform': lambda k, v: ACCOUNT_MODEL.PLAY_WITH[ACCOUNT_MODEL.get_reverse_i('play_with', k)]['icon'],
            'transform': CuteFormTransform.FlaticonWithText,
        },
        'center': {
            'to_cuteform': lambda _k, _v: _v.image_url,
            'title': _('Center'),
            'extra_settings': {
                'modal': 'true',
                'modal-text': 'true',
            },
        },
    }

    fields_icons = {
        'creation': 'date',
        'start_date': 'date',
        'level': 'max-level',
        'friend_id': 'id',
        'screenshot': 'screenshot',
        'is_playground': 'hobbies',
        'os': lambda _i: _i.os,
        'play_with': lambda _i: _i.play_with_icon,
        'center': 'center',
        'accept_friend_requests': 'users',
        'device': lambda _i: _i.os,
    }

    def get_buttons_classes(self, buttons_classes, request, context, item=None, size=None, block=None, color=None):
        if item:
            if getattr(item, 'center', None) and item.center.color:
                color = item.center.color
            else:
                color = item.cached_owner.preferences.css_color
        return super(AccountCollection, self).get_buttons_classes(
            buttons_classes, request, context, item=item, color=color, size=size, block=block)

    def get_profile_account_tabs(self, request, context, account=None, account_type=None):
        """
        Ordered dict that:
        - MUST contain name, callback (except for about)
        - May contain icon, image, callback
        When account is not provided, callback will always be 'undefined'
        """
        tabs = {}
        if context['collectible_collections'] and 'account' in context['collectible_collections']:
            for collection_name, collection in context['collectible_collections']['account'].items():
                if (collection.collectible_limit_to_account_types is not None
                    and (getattr(account, 'type', None) or account_type) not in collection.collectible_limit_to_account_types):
                    continue
                tabs[collection_name] = {
                    'name': collection.collectible_tab_name,
                    'icon': collection.icon,
                    'image': collection.image,
                    'callback': mark_safe(u'loadCollectionForAccount(\'{load_url}\', {callback})'.format(
                        load_url=collection.get_list_url_for_authenticated_owner(
                            request, ajax=True, item=None, fk_as_owner=account.id),
                        callback=collection.list_view.ajax_pagination_callback or 'undefined',
                    )) if account else 'undefined',
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
            ('Unrealistic Level', unrealistic_template_sentence.format(thing='level')),
            ('Unrealistic Level (recidivist)', 'After multiple warnings, you have failed to provide a valid screenshot proving your level, so you have been removed from the leaderboard completely. You may still use this account normally and it is still accessible from your profile, with a visual indication that it cannot be trusted. If this was a mistake, you may contact us with a valid screenshot and we will change it back. Thank you for your understanding.'),
            ] + [
                ('Fake screenshot', 'The screenshot you uploaded does feature a valid, existing in-game account. Please upload a screenshot of your account in-game that features your level{} clearly.'.format(' and friend ID' if modelHasField(models.Account, 'friend_id') else '')),
                ] if modelHasField(models.Account, 'screenshot') else []
        )
        for field in self.queryset.model._meta.fields:
            if not field.name.startswith('_') and field.name not in [
                    'id', 'owner', 'creation', 'level', 'default_tab', 'level_on_screenshot_upload',
            ]:
                name = field.name
                if name.startswith('i_'):
                    name = name[2:]
                name = name.replace('_', ' ').title()
                if (isinstance(field, models.models.fields.CharField)
                    or isinstance(field, models.models.ImageField)):
                    templates[u'Inappropriate {}'.format(name)] = (
                        u'Your account\'s {} was inappropriate. {}'.format(
                            name.lower(), please_understand_template_sentence))
                elif field.name == 'friend_id':
                    templates['Invalid friend id'] = 'Your friend ID doesn\'t seem to exist in the game. It may have been a typo, so please check again and re-enter your friend ID.'
                elif (not field.name.startswith('i_')
                    and isinstance(field, models.models.fields.PositiveIntegerField)):
                    templates[u'Unrealistic {}'.format(name)] = unrealistic_template_sentence.format(
                        thing=name)
        return templates

    class ListView(MagiCollection.ListView):
        item_template = 'defaultAccountItem'
        show_report_button = True
        show_title = True
        per_line = 1
        add_button_subtitle = _('Create your account to join the community and be in the leaderboard!')
        filter_form = forms.AccountFilterForm
        allow_random = False
        disable_on_high_traffic = True

        show_item_buttons = False # displayed manually by template
        show_item_buttons_justified = False

        show_item_buttons_as_icons = True
        item_buttons_classes = ['btn', 'btn-link']

        def show_add_button(self, request):
            return not getAccountIdsFromSession(request)

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(AccountCollection.ListView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)
            queryset = filterRealAccounts(queryset)
            return queryset

        @property
        def profile_default_ordering(self):
            if (modelHasField(self.collection.queryset.model, 'level')
                and modelHasField(self.collection.queryset.model, 'is_playground')
                and modelHasField(self.collection.queryset.model, 'is_hidden_from_leaderboard')):
                return 'is_playground,is_hidden_from_leaderboard,-level'
            return self.default_ordering

        @property
        def default_ordering(self):
            if modelHasField(self.collection.queryset.model, 'level'):
                return '-level'
            return MagiCollection.ListView.default_ordering.__get__(self)

        def get_page_title(self):
            return _('Leaderboard')

    class ItemView(MagiCollection.ItemView):
        # When loading the actual view (/account/x/.../)
        template = 'defaultAccountItem'
        comments_enabled = False

        # When loading within User ItemView

        show_item_buttons = True
        show_item_buttons_as_icons = False
        show_item_buttons_in_one_line = False
        show_item_buttons_justified = False

        if modelHasField(ACCOUNT_MODEL, 'center'):
            fields_preselected = [ 'center' ]

        fields_exclude = [
            'owner',
            'nickname',
            'default_tab',
        ]

        fields_permissions_required = {
            'level_on_screenshot_upload': [ 'see_account_verification_details' ],
            'is_hidden_from_leaderboard': [ 'see_account_verification_details' ],
            'show_friend_id': [ 'see_account_verification_details' ],
            # friend_id is hidden/displayed in AccountFields / AccountFriendId
        }

    class AddView(MagiCollection.AddView):
        alert_duplicate = False
        allow_next = True
        max_per_user = 10
        simpler_form = None
        back_to_list_button = False

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
            first_collection = getMagiCollection(
                FIRST_COLLECTION_PER_ACCOUNT_TYPE.get(getattr(instance, 'type', None), None)
                or FIRST_COLLECTION
            )
            if first_collection:
                return first_collection.parent_collection.get_list_url(
                    ajax=ajax, modal_only=ajax, parameters={
                        'get_started': '',
                        'add_to_{}'.format(first_collection.name): instance.pk,
                    },
                )
            if ajax: # Ajax is not allowed for profile url
                return '/ajax/successadd/'
            return '{}#{}'.format(request.user.item_url, instance.pk)

        def before_save(self, request, instance, type=None):
            super(AccountCollection.AddView, self).before_save(request, instance, type=type)
            if 'account_ids' in request.session:
                del request.session['account_ids']
            if 'account_versions' in request.session:
                del request.session['account_versions']
            if 'account_types' in request.session:
                del request.session['account_types']
            return instance

        def after_save(self, request, instance, type=None):
            instance = super(AccountCollection.AddView, self).after_save(request, instance, type=type)
            # If the user had no account before, update cache to say that they have accounts now
            if not instance.owner.preferences.cached_tabs_with_content.get('account', {}).get('has_content', False):
                instance.owner.preferences.force_update_cache('tabs_with_content')
            return instance

    class EditView(MagiCollection.EditView):
        allow_delete = True

        def allow_cascade_delete_up_to(self, request):
            return 25

        def redirect_after_edit(self, request, instance, ajax=False):
            if ajax:
                return '/ajax/successedit/'
            return '{}#{}'.format(request.user.item_url, instance.pk)

        def before_save(self, request, instance, type=None):
            super(AccountCollection.EditView, self).before_save(request, instance, type=type)
            if 'account_versions' in request.session:
                del request.session['account_versions']
            return instance

        def before_delete(self, request, item, ajax):
            super(AccountCollection.EditView, self).before_delete(request, item, ajax)
            if 'account_ids' in request.session:
                del request.session['account_ids']
            if 'account_versions' in request.session:
                del request.session['account_versions']
            if 'account_types' in request.session:
                del request.session['account_types']
            request._account_owner = item.owner

        def after_delete(self, request):
            super(AccountCollection.EditView, self).after_delete(request)
            request._account_owner.preferences.force_update_cache('tabs_with_content')

        def redirect_after_delete(self, request, item, ajax=False):
            if ajax:
                return '/ajax/successdelete/'
            return request.user.item_url

############################################################
# User Collection

class UserCollection(MagiCollection):
    title = _('Profile')
    plural_title = _('Players')
    icon = 'users'
    navbar_link = False
    navbar_link_list = 'community'
    fields_class = magifields.UserFields
    queryset = models.User.objects.all().select_related('preferences')
    report_allow_delete_with_permission = 'allow_delete_reported_profiles'
    report_edit_templates = OrderedDict([
        ('Inappropriate profile picture', 'Your profile picture is inappropriate. ' + please_understand_template_sentence + ' To change your avatar, go to gravatar and upload a new image, then go to your settings on our web app to re-enter your email address.'),
        ('Inappropriate image in profile description', 'An image on your profile description was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate link', 'A link on your profile description was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate profile description', 'Something you wrote on your profile was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate username', 'Your username was inappropriate. ' + please_understand_template_sentence),
        ('Inappropriate location', 'Your location was inappropriate. ' + please_understand_template_sentence),
        ('Received an inappropriate private message from this user', 'You sent private message(s) to user(s) and they found the content inappropriate. ' + please_understand_template_sentence + ' We kindly ask you to not re-iterate your actions. If it happens again, we will delete your profile, accounts, activities and everything else you own on our web app permanently.'),
    ])
    report_delete_templates = {
        'Inappropriate behavior towards other user(s)': 'We noticed that you\'ve been acting in an inappropriate manner towards other user(s), which doesn\'t correspond to what we expect from our community members. Your profile, accounts, activities and everything else you owned on our web app has been permanently deleted, and we kindly ask you not to re-iterate your actions.',
        'Spam': 'We detected spam activities from your user profile. Your profile, accounts, activities and everything else you owned on our web app has been permanently deleted, and we kindly ask you not to re-iterate your actions.',
        'Troll profile': 'This profile was deliberately made to be provocative with the intention of causing disruption or argument and therefore has been deleted. Activities, accounts, and everything else that was created using this profile have also been deleted. We kindly ask you not to re-iterate your actions and be respectful towards our community.',
    }

    filter_cuteform = {
        'color': {
            'type': CuteFormType.Images,
        },
        'i_language': {
            'image_folder': 'language',
        },
    }

    def get_buttons_classes(self, buttons_classes, request, context, item=None, size=None, block=None, color=None):
        if item:
            color = item.preferences.css_color
        return super(UserCollection, self).get_buttons_classes(
            buttons_classes, request, context, item=item, color=color, size=size, block=block)

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        filter_form = forms.UserFilterForm
        default_ordering = '-id'
        fields_preselected = [ 'preferences' ]
        show_report_button = False
        show_item_buttons = False
        show_item_buttons_as_icons = True
        show_item_buttons_in_one_line = True
        show_item_buttons_justified = False
        item_buttons_classes = ['btn', 'btn-link-secondary', 'btn-lg']
        show_edit_button = False
        disable_on_high_traffic = True
        page_size = 30
        per_line = 1

        alt_views = MagiCollection.ListView.alt_views + [
            ('send_private_message', {
                'hide_in_filter': True,
                'hide_in_navbar': True,
                'verbose_name': _('Send a message'),
                'template': 'userSendMessageItem',
            }),
        ]

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(UserCollection.ListView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)
            # When ordering is followed first, add follow
            if request and request.GET.get('ordering', None) == 'followed,id':
                queryset = queryset.extra(select={
                    'followed': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = {id} AND user_id = auth_user.id'.format(
                        table=models.UserPreferences._meta.db_table,
                        id=request.user.preferences.id,
                    ),
                })
            return queryset

        def extra_context(self, context):
            super(UserCollection.ListView, self).extra_context(context)
            # Send private message view
            if context['view'] == 'send_private_message':
                # Show warning youre not following anyone when settings is following only
                if context['request'].GET.get('followed_by', None):
                    context['no_result_template'] = 'include/alert'
                    context['alert_title'] = _('Your inbox is only open to people you follow, and you\'re not following anyone.')
                    context['alert_button_string'] = _('Settings')
                    context['alert_button_link'] = u'/settings/#security'
                    context['alert_flaticon'] = 'about'
                    context['alert_type'] = 'info'

    class ItemView(MagiCollection.ItemView):
        template = 'profile'
        js_files = ['profile']
        fields_preselected = [ 'preferences' ]
        comments_enabled = False
        follow_enabled = True
        show_item_buttons = False
        show_item_buttons_justified = False
        item_buttons_classes = ['btn', 'btn-link']
        ajax = False
        accounts_template = 'include/defaultAccountsForProfile'
        profile_accounts_top_template = None
        show_small_title = False
        show_edit_button = False

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(UserCollection.ItemView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)

            # Shown under "Follow" button
            queryset = queryset.extra(select={
                'total_following': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = (SELECT id FROM {table} WHERE user_id = auth_user.id)'.format(
                    table=models.UserPreferences._meta.db_table,
                ),
                'total_followers': 'SELECT COUNT(*) FROM {table}_following WHERE user_id = auth_user.id'.format(
                    table=models.UserPreferences._meta.db_table,
                ),
            })

            # Prefetch accounts
            account_collection = getMagiCollection('account')
            if account_collection:
                account_queryset = account_collection.item_view.get_queryset().order_by(
                    *account_collection.list_view.profile_default_ordering.split(',')
                )
                queryset = queryset.prefetch_related(
                    Prefetch('accounts', queryset=account_queryset, to_attr='all_accounts'),
                )

            # Prefetch links
            queryset = queryset.prefetch_related(
                Prefetch('links', queryset=models.UserLink.objects.order_by('-i_relevance'), to_attr='all_links'),
            )

            if request and request.user.is_authenticated():
                queryset = queryset.extra(select={
                    # Used by "follow" button + "private message" button
                    'followed': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = {id} AND user_id = auth_user.id'.format(
                        table=models.UserPreferences._meta.db_table,
                        id=request.user.preferences.id,
                    ),
                    # Used by "follows you" message + "private message" button
                    'is_followed_by': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = (SELECT id FROM {table} WHERE user_id = auth_user.id) AND user_id = {id}'.format(
                        table=models.UserPreferences._meta.db_table,
                        id=request.user.id,
                    ),
                })
            return queryset

        def buttons_per_item(self, request, context, item):
            buttons = super(UserCollection.ItemView, self).buttons_per_item(request, context, item)
            classes = self.get_item_buttons_classes(request, context, item=item)
            user = item

            # Make sure reputation is calculated every day for all users
            reputation = user.preferences.cached_reputation

            # Private message button (should always be first + not a 'btn-link')
            if 'privatemessage' in context['all_enabled'] and request.user.is_authenticated():
                buttons = OrderedDict([
                    ('privatemessage', {
                        'classes': [cls.replace('-link', '') for cls in classes],
                        'show': True,
                        'url': '/privatemessages/?to_user={id}'.format(id=user.id),
                        'ajax_url': '/ajax/privatemessages/?to_user={id}&ajax_modal_only&ajax_show_top_buttons&buttons_color={color}'.format(
                            id=user.id,
                            color=user.preferences.css_color,
                        ),
                        'icon': 'contact',
                        'title': _('Private messages'),
                        'has_permissions': request.user.hasPermissionToMessage(user),
                    }),
                ] + buttons.items())

            # Block button
            if request.user.is_authenticated() and user.id != request.user.id:
                buttons['block'] = {
                    'show': True,
                    'classes': classes,
                    'url': u'/block/{}/'.format(user.id),
                    'icon': 'block',
                    'title': _(u'Block {username}').format(username=user.username),
                    'has_permissions': True,
                }

            # Mark email address as invalid button
            if (request.user.is_authenticated() and user.id != request.user.id
                and request.user.hasPermission('mark_email_addresses_invalid')):
                baseButton(
                    button_name='mark_email_addresses_invalid',
                    buttons=buttons, classes=classes + [ 'staff-only' ], extras={
                        'title': 'Mark e-mail address invalid',
                        'url': addParametersToURL(
                            user.preferences.edit_url, parameters={ 'mark_email_addresses_invalid': u'' }),
                        'ajax_url': addParametersToURL(
                            user.preferences.ajax_edit_url, parameters={ 'mark_email_addresses_invalid': u'' }),
                        'icon': 'warning',
                    })

            # Edit roles button
            if (request.user.is_authenticated() and request.user.hasPermission('edit_roles')):
                baseButton(
                    button_name='edit_roles', buttons=buttons, classes=classes + [ 'staff-only' ], extras={
                        'title': 'Edit roles',
                        'url': addParametersToURL(
                            user.preferences.edit_url, parameters={ 'edit_roles': u'' }),
                        'ajax_url': addParametersToURL(
                            user.preferences.ajax_edit_url, parameters={ 'edit_roles': u'' }),
                        'icon': 'staff',
                    })

            # Edit donator status button
            if (request.user.is_authenticated() and request.user.hasPermission('edit_donator_status')):
                baseButton(
                    button_name='edit_donator_status', buttons=buttons, classes=classes + [ 'staff-only' ], extras={
                        'title': 'Edit donator status',
                        'url': addParametersToURL(
                            user.preferences.edit_url, parameters={ 'edit_donator_status': u'' }),
                        'ajax_url': addParametersToURL(
                            user.preferences.ajax_edit_url, parameters={ 'edit_donator_status': u'' }),
                        'icon': 'heart',
                    })

            # Reputation info button
            if request.user.is_authenticated() and request.user.hasPermission('see_reputation'):
                buttons['reputation'] = {
                    'classes': classes + ['staff-only', 'disabled'],
                    'show': True,
                    'url': '#',
                    'icon': 'leaderboard',
                    'title': u'Reputation: {} points'.format(reputation),
                    'has_permissions': True,
                }

            return buttons

        def reverse_url(self, text):
            return {
                'username': text,
            }

        def get_meta_links(self, user, context):
            meta_links = []
            first_links = []
            already_linked = None

            # Donation link
            if user.preferences.donation_link:
                for link in context['item'].all_links:
                    if link.url == user.preferences.donation_link:
                        link = {
                            'name': link.type,
                            'verbose_name': link.t_type,
                            'value': link.value,
                            'pk': link.pk,
                            'url': link.url,
                            'image': link.image_url,
                        }
                        already_linked = link
                        first_links.append(link)
                        break
                if not already_linked:
                    first_links.append(AttrDict({
                        'name': 'website',
                        'verbose_name': _('Website'),
                        'value': user.preferences.donation_link_title,
                        'url': user.preferences.donation_link,
                        'flaticon': 'url',
                    }))

            # Favorite characters
            for key, user_favorites in getCharactersUsersFavorites(user).items():
                for nth, favorite_character in user_favorites.items():
                    pk = favorite_character['pk']
                    if pk:
                        meta_links.append(AttrDict({
                            'name': favorite_character['field_name'],
                            'verbose_name': favorite_character['field_label'],
                            'raw_value': pk,
                            'value': getCharacterNameFromPk(pk, key=key),
                            'image': getCharacterImageFromPk(pk, key=key),
                            'url': getCharacterURLFromPk(pk, key=key),
                        }))

            # Location
            if user.preferences.location:
                latlong = '{},{}'.format(user.preferences.latitude, user.preferences.longitude) if user.preferences.latitude else None
                link = AttrDict({
                    'name': 'location',
                    'verbose_name': _('Location'),
                    'value': user.preferences.location,
                    'url': user.preferences.location_url,
                    'flaticon': 'pinpoint',
                })
                meta_links.append(link)

            # Language
            if context['is_me'] or user.preferences.language != context['request'].LANGUAGE_CODE:
                meta_links.append(AttrDict({
                    'name': 'language',
                    'verbose_name': _('Language'),
                    'value': user.preferences.t_language,
                    'raw_value': user.preferences.language,
                    'url': u'/users/{}/'.format(user.preferences.language),
                    'image': staticImageURL(user.preferences.language, folder='language', extension='png'),
                }))

            # Birthday
            if user.preferences.birthdate:
                meta_links.append(AttrDict({
                    'name': 'birthdate',
                    'verbose_name': _('Birthdate'),
                    'value': user.preferences.formatted_birthday,
                    'url': user.birthday_url,
                    'flaticon': 'birthday',
                }))

            return (
                first_links, meta_links,
                [link for link in [{
                    'name': link.type,
                    'verbose_name': link.t_type,
                    'value': link.value,
                    'pk': link.pk,
                    'url': link.url,
                    'image': link.image_url,
                } for link in context['item'].all_links
                ] if link != already_linked],
            )

        def extra_context(self, context):
            user = context['item']
            request = context['request']
            context['is_me'] = user.id == request.user.id
            context['profile_tabs'] = PROFILE_TABS.copy()
            context['accounts_template'] = self.accounts_template
            context['profile_accounts_top_template'] = self.profile_accounts_top_template
            account_collection = getMagiCollection('account')
            if 'js_variables' not in context:
                context['js_variables'] = {}
            afterjs = u'<script>'

            # Retrieve cached tabs with content
            tabs_with_content = user.preferences.cached_tabs_with_content

            # Account fields, buttons and tabs
            afterjs += u'var account_tab_callbacks = {'
            if not account_collection or not account_collection.list_view.has_permissions(request, context):
                if 'account' in context['profile_tabs']:
                    del(context['profile_tabs']['account'])
            else:
                context['uses_deprecated_to_fields'] = account_collection.item_view.uses_deprecated_to_fields()
                for account in user.all_accounts:
                    account.request = request

                    # Fields
                    if context['uses_deprecated_to_fields']:
                        # Call deprecated to_fields if to_fields has been overrided
                        account.fields = account_collection.item_view.to_fields(account, request=request)
                    else:
                        account.fields = account_collection.item_view.to_magifields(account, context)

                    # Buttons
                    account.show_item_buttons_in_one_line = account_collection.item_view.show_item_buttons_in_one_line
                    if (context['uses_deprecated_to_fields']
                        or account.show_item_buttons_in_one_line):
                        account.include_below_item = False
                        account.show_item_buttons_as_icons = account_collection.show_item_buttons_as_icons
                        account.show_item_buttons_justified = account_collection.show_item_buttons_justified
                        account.buttons_to_show = account_collection.item_view.buttons_per_item(request, context, account)
                        if ((account.show_item_buttons_in_one_line
                             or not context['uses_deprecated_to_fields'])
                            and account_collection.item_view.show_item_buttons
                            and [True for b in account.buttons_to_show.values() if b['show'] and b['has_permissions']]):
                            account.include_below_item = True

                    # Tabs
                    account.tabs = account_collection.get_profile_account_tabs(request, context, account)
                    account.tabs_size = 100 / len(account.tabs) if account.tabs else 100
                    account.opened_tab = account.tabs.keys()[0] if account.tabs else None
                    open_tab_key = u'account{}'.format(account.id)
                    if account.default_tab and account.default_tab in account.tabs:
                        account.opened_tab = account.default_tab
                    if open_tab_key in request.GET and request.GET[open_tab_key] in account.tabs:
                        account.opened_tab = request.GET[open_tab_key]
                    # Hide tabs with no values
                    if not context['is_me']:
                        for collection_name in context['collectible_collections'].get('account', {}):
                            if (collection_name not in [account.opened_tab, account.default_tab]
                                and not tabs_with_content.get('account', {}).get(
                                    'tabs_per_account', {}).get(str(account.id), {}).get(collection_name, False)):
                                if collection_name in account.tabs:
                                    del(account.tabs[collection_name])
                    afterjs += u'\'{account_id}\': {{'.format(account_id=account.id)
                    for tab_name, tab in account.tabs.items():
                        if 'callback' in tab and tab['callback']:
                            afterjs += u'\'{tab_name}\': {{\'callback\': {callback}, \'called\': false}},'.format(
                                tab_name=tab_name, callback=tab['callback'],
                            )
                    afterjs += u'},'
            afterjs += u'};'

            # Badges
            if 'badge' in context['all_enabled'] and tabs_with_content.get('badge_top_profile'):
                context['item'].latest_badges = list(context['item'].badges.filter(
                    show_on_top_profile=True).order_by('-date', '-id')[:6])
                if len(context['item'].latest_badges) == 6:
                    context['more_badges'] = True
                context['item'].latest_badges = context['item'].latest_badges[:5]

            # Profile tabs
            parameters = {
                'ajax_show_no_result': '',
                'buttons_color': user.preferences.css_color,
            }
            if context['is_me']:
                parameters['ajax_show_top_buttons'] = ''

            for collection_name in context['collections_in_profile_tabs']:
                collection = getMagiCollection(collection_name)
                if not collection.list_view.has_permissions(request, context):
                    continue
                context['profile_tabs'][collection_name] = {
                    'name': collection.list_view.profile_tab_name,
                    'icon': collection.icon,
                    'image': collection.image,
                    'callback': mark_safe(u'loadCollectionForOwner(\'{load_url}\', {callback})'.format(
                        load_url=collection.get_list_url(ajax=True, parameters=parameters),
                        callback=collection.list_view.ajax_pagination_callback or 'undefined',
                    )),
                }

            if context['collectible_collections'] and 'owner' in context['collectible_collections']:
                for collection_name, collection in context['collectible_collections']['owner'].items():
                    if not collection.list_view.has_permissions(request, context):
                        continue
                    if collection_name in context['profile_tabs']:
                        continue
                    context['profile_tabs'][collection_name] = {
                        'name': collection.collectible_tab_name,
                        'icon': collection.icon,
                        'image': collection.image,
                        'callback': mark_safe(u'loadCollectionForOwner(\'{load_url}\', {callback})'.format(
                            load_url=collection.get_list_url(ajax=True, parameters=parameters),
                            callback=collection.list_view.ajax_pagination_callback or 'undefined',
                        )),
                    }

            # Update profile account tabs using collection setings
            if 'account' in context['profile_tabs']:
                context['profile_tabs']['account']['name'] = (
                    account_collection.title
                    if len(user.all_accounts) <= 1
                    else account_collection.plural_title
                )
                context['profile_tabs']['account']['icon'] = account_collection.icon

            # Set opened tab
            context['opened_tab'] = context['profile_tabs'].keys()[0] if context['profile_tabs'] else None
            if user.preferences.default_tab and user.preferences.default_tab in context['profile_tabs']:
                context['opened_tab'] = user.preferences.default_tab
            if 'open' in request.GET and request.GET['open'] in context['profile_tabs']:
                context['opened_tab'] = request.GET['open']

            # Hide tabs with no values
            if not context['is_me']:
                def must_stay(collection_name):
                    return collection_name in [context['opened_tab'], user.preferences.default_tab]
                for collection_name in (
                        context['collections_in_profile_tabs']
                        + context['collectible_collections'].get('owner', {}).keys()):
                    if (collection_name in context['profile_tabs']
                        and not must_stay(collection_name) and not tabs_with_content.get(collection_name, False)):
                        del(context['profile_tabs'][collection_name])
                if ('account' in context['profile_tabs'] and not must_stay('account')
                    and not tabs_with_content.get('account', {}).get('has_content', False)):
                    del(context['profile_tabs']['account'])
                if ('badge' in context['profile_tabs'] and not must_stay('badge')
                    and not tabs_with_content.get('badge', False)):
                    del(context['profile_tabs']['badge'])

            # Tab size
            context['profile_tabs_size'] = 100 / len(context['profile_tabs']) if context['profile_tabs'] else 100

            afterjs += u'var tab_callbacks = {'
            for tab_name, tab in context['profile_tabs'].items():
                if 'callback' in tab and tab['callback']:
                    afterjs += u'\'{tab_name}\': {{\'callback\': {callback}, \'called\': false}},'.format(
                        tab_name=tab_name, callback=tab['callback'],
                    )
            afterjs += u'};'

            # Links
            context['item'].all_links = [link for links in self.get_meta_links(user, context) for link in links]
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
            if account_collection and account_collection.add_view.has_permissions(request, context):
                context['can_add_account'] = True
                context['add_account_sentence'] = account_collection.add_sentence
                context['add_account_subtitle'] = account_collection.list_view.add_button_subtitle
                context['add_account_icon'] = account_collection.icon
                context['add_account_buttons_classes'] = u' '.join(
                    account_collection.list_view.get_top_buttons_classes(request, context, color=user.preferences.css_color))
            if context['is_me']:
                emojis = getEmojis(2)
                context['share_sentence'] = _(u'Hey, look! I\'m on {site}! Follow me ♥︎').format(
                    site=u'{}{}{}'.format(emojis[0], context['t_site_name'], emojis[1]))
                context['hashtags'] = context['hashtags'] + ['My{}Collection'.format(
                    context['site_name'].replace(' ', ''))]
            else:
                context['share_sentence'] = _('Check out {username}\'s awesome collection!').format(
                    username=context['item'].username)
            context['share_url'] = context['item'].http_item_url

            # Show birthday popup
            if not context['is_me'] and isBirthdayToday(user.preferences.birthdate):
                context['corner_popups']['profile_birthday'] = {
                    'title': u'{}, {} 🎉'.format(
                        _('Happy Birthday'),
                        user.username,
                    ),
                    'content': mark_safe(u'<p>🗓 {}{}</p>'.format(
                        user.preferences.formatted_birthday_date,
                        u'<br>🎂 {}'.format(user.preferences.formatted_age)
                        if user.preferences.show_birthdate_year else '',
                    )),
                    'buttons': {
                        'privatemessages': {
                            'title': _('Send a message'),
                            'url': '/privatemessages/?to_user={id}'.format(id=user.id),
                            'ajax_url': '/ajax/privatemessages/?to_user={id}&ajax_modal_only&ajax_show_top_buttons'.format(
                                id=user.id,
                            ),
                        },
                    } if 'privatemessage' in context['all_enabled'] else None,
                    'image': context['corner_popup_image'],
                    'image_overflow': context['corner_popup_image_overflow'],
                    'allow_close_once': True,
                }

            # Afterjs
            afterjs += u'</script>'
            context['afterjs'] = afterjs

    class AddView(MagiCollection.AddView):
        enabled = False

    class EditView(MagiCollection.EditView):
        staff_required = True
        one_of_permissions_required = [
            'edit_roles',
            'edit_reported_things',
            'edit_donator_status',
            'mark_email_addresses_invalid',
        ]
        form_class = forms.StaffEditUser

        def check_owner_permissions(self, request, context, item):
            # Edit view is for staff only, but staff can't edit their own
            if item.owner_id == request.user.id:
                raise PermissionDenied()

        def extra_context(self, context):
            # Redirects to preference form most of the time, unless it's being linked from
            # preference form itself with ?edit_reported_user
            # The view still needs to exist in order to be linked from reports.
            if context.get('request', None) and 'edit_reported_user' in context['request'].GET:
                return
            raise HttpRedirectException(addParametersToURL((
                context['item'].preferences.ajax_edit_url
                if context['ajax']
                else context['item'].preferences.edit_url
            ), parameters={
                key: context['request'].GET[key]
                for key in [ 'is_reported', 'disable_delete' ]
                if key in context['request'].GET
            }))

        def redirect_after_edit(self, request, item, ajax):
            if ajax:
                return u'/ajax/successedit/'
            return item.item_url

class UserPreferencesCollection(MagiCollection):
    queryset = models.UserPreferences.objects.all()
    title = _('Preferences')
    plural_title = _('Preferences')
    reportable = False

    class ItemView(MagiCollection.ItemView):
        enabled = False
    class ListView(MagiCollection.ListView):
        enabled = False
    class AddView(MagiCollection.AddView):
        enabled = False

    class EditView(MagiCollection.EditView):
        staff_required = True
        one_of_permissions_required = [
            'edit_roles',
            'edit_reported_things',
            'edit_donator_status',
            'mark_email_addresses_invalid',
        ]
        form_class = forms.StaffEditUserPreferences
        fields_preselected = [ 'owner' ]
        ajax_callback = 'updateStaffEditUserPreferencesForm'

        def check_owner_permissions(self, request, context, item):
            # Edit view is for staff only, but staff can't edit their own (unless they can edit their roles)
            if item.owner_id == request.user.id and not request.user.hasPermission('edit_roles'):
                raise PermissionDenied()

        def after_save(self, request, instance, type=None):
            instance = super(UserPreferencesCollection.EditView, self).after_save(request, instance, type=type)
            models.onUserEdited(instance)
            if ON_USER_EDITED:
                ON_USER_EDITED(instance)
            models.onPreferencesEdited(instance)
            if ON_PREFERENCES_EDITED:
                ON_PREFERENCES_EDITED(instance)
            return instance

        def redirect_after_edit(self, request, item, ajax):
            if 'edit_roles' in request.GET:
                return '{}/addrevokeoutsidepermissions/{}/?previous_is_staff={}&previous_groups={}'.format(
                    '/ajax' if ajax else '', item.owner.username,
                    'true' if request._previous_is_staff else '',
                    u','.join(request._previous_groups),
                )
            if ajax:
                return u'/ajax/successedit/'
            return item.owner.item_url

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
    fields_class = magifields.StaffConfigurationFields
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
        page_size = len(django_settings.LANGUAGES) if len(django_settings.LANGUAGES) > 12 else 12
        display_style = 'table'
        display_style_table_fields = ['verbose_key', 'i_language', 'value', 'owner']
        display_style_table_classes = MagiCollection.ListView.display_style_table_classes + ['table-striped']
        before_template = 'include/beforeStaffConfigurations'
        filter_form = forms.StaffConfigurationFilters
        allow_random = False
        fields_preselected = [ 'owner' ]

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(StaffConfigurationCollection.ListView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)
            # Translators can only see translatable configurations
            if request and not hasOneOfPermissions(request.user, [
                    'edit_staff_configurations', 'advanced_staff_configurations' ]):
                queryset = queryset.exclude(Q(i_language__isnull=True) | Q(i_language=''))
            elif not parameters.get('i_language', None) and not parameters.get('key', None):
                # Hide other languages (unless you're filtering by language or by specific key)
                queryset = queryset.filter(
                    Q(Q(i_language__isnull=True) | Q(i_language=''))
                    | Q(i_language=(request.LANGUAGE_CODE if request else get_language()))
                )
            return queryset

        def buttons_per_item(self, request, context, item):
            buttons = super(StaffConfigurationCollection.ListView, self).buttons_per_item(request, context, item)
            if item.i_language and not request.GET.get('key', None):
                baseButton(
                    button_name='see_other_languages', buttons=buttons,
                    view=self, request=request, context=context, item=item, extras={
                        'title': 'See all languages',
                        'icon': 'translate',
                        'url': self.collection.get_list_url(parameters={ 'key': item.key }),
                        'ajax_url': self.collection.get_list_url(
                            ajax=True, modal_only=True, parameters={ 'key': item.key },
                        ),
                    })
            return buttons

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
    reportable = False
    blockable = False
    form_class = forms.StaffDetailsForm

    class ListView(MagiCollection.ListView):
        one_of_permissions_required = ['edit_own_staff_profile', 'translate_items', 'edit_staff_details']
        add_button_subtitle = None
        filter_form = forms.StaffDetailsFilterForm
        hide_sidebar = True
        allow_random = False
        show_items_names = True
        display_style = 'table'
        fields_preselected_subfields = { 'owner': [ 'username' ] }
        display_style_table_fields = [ 'image', 'owner__username' ]

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(StaffDetailsCollection.ListView, self).get_queryset(queryset, parameters, request)
            if request and not hasOneOfPermissions(request.user, ['translate_items', 'edit_staff_details']):
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

    class EditView(MagiCollection.EditView):
        one_of_permissions_required = ['edit_own_staff_profile', 'translate_items', 'edit_staff_details']
        owner_only = False
        owner_only_or_permissions_required = ['edit_staff_details']

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
    title = _('Post')
    plural_title = _('Posts')
    plural_name = 'activities'
    queryset = models.Activity.objects.all()
    navbar_link_list = 'community'
    icon = 'comments'
    show_open_button = False

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

    def _get_queryset_for_list_and_item(self, queryset, request=None):
        if request and request.user.is_authenticated():
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
        classes = view.get_item_buttons_classes(request, context, item=item)
        js_buttons = []
        if request.user.is_authenticated():

            # Edit button
            if ('edit' in buttons
                and buttons['edit']['has_permissions']
                and item.owner_id != request.user.id
                and not request.user.is_superuser):
                buttons['edit']['has_permissions'] = False

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
                        'classes': classes + (['staff-only'] if staff_only else []),
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
                        'classes': classes + (['staff-only'] if staff_only else []),
                    }))

            if request.user.hasPermission('edit_activities_post_language'):
                # Fix activity's language
                js_buttons.append(('fix_language', {
                    'has_permissions': True,
                    'title': u'Not in {}? → Fix'.format(item.t_language),
                    'url': u'{}?fix_language'.format(item.edit_url),
                    'ajax_url': u'{}?fix_language'.format(item.ajax_edit_url),
                    'image': item.language_image_url,
                    'classes': classes + (
                        ['staff-only'] if 'fix_language' not in request.GET else []
                    ),
                }))

            if request.user.hasPermission('manipulate_activities'):
                # Bump
                js_buttons.append(('bump', {
                    'has_permissions': True,
                    'title': 'Bump',
                    'url': u'/ajax/bumpactivity/{}/'.format(item.id),
                    'icon': 'sort-up',
                    'classes': classes + ['staff-only'],
                }))
                # Drown
                js_buttons.append(('drown', {
                    'has_permissions': True,
                    'title': 'Drown',
                    'url': u'/ajax/drownactivity/{}/'.format(item.id),
                    'icon': 'sort-down',
                    'classes': classes + ['staff-only'],
                }))
            if ('staff' in ACTIVITY_TAGS.keys()
                and request.user.hasPermission('mark_activities_as_staff_pick')):
                if 'staff' in item.tags:
                    # Remove from staff picks
                    js_buttons.append(('remove-from-staff-pick', {
                        'has_permissions': True, 'title': 'Remove from staff picks',
                        'url': u'/ajax/removeactivitystaffpick/{}/'.format(item.id),
                        'icon': 'staff',
                        'classes': classes + ['staff-only'],
                    }))
                else:
                    # Mark as staff pick
                    js_buttons.append(('mark-staff-pick', {
                        'has_permissions': True, 'title': 'Mark as staff pick',
                        'url': u'/ajax/markactivitystaffpick/{}/'.format(item.id),
                        'icon': 'staff',
                        'classes': classes + ['staff-only'],
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

    def _item_and_list_extra_context(self, request, context, view, item=None):
        if 'js_variables' not in context:
            context['js_variables'] = {}
        context['js_variables']['main_collections'] = {
            collection_name: getMagiCollection(collection_name).item_view.ajax_callback
            for collection_name in context['main_collections']
        }
        context['js_variables']['site_url'] = context['site_url']
        context['buttons_classes'] = u' '.join(view.get_item_buttons_classes(request, context, item=item))

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        header_template = None
        per_line = 1
        distinct = False
        add_button_subtitle = _('Share your adventures!')
        ajax_pagination_callback = 'updateActivities'
        before_template = 'include/homePage'
        filter_form = forms.FilterActivities
        show_relevant_fields_on_ordering = False
        show_item_buttons = False
        show_item_buttons_justified = False
        show_report_button = True
        ajax_callback = 'loadIndex'
        as_profile_tab = True
        profile_tab_name = property(lambda _s: _s.collection.plural_title)

        def get_page_title(self):
            return _('Feed')

        @property
        def item_buttons_classes(self):
            return [cls for cls in super(ActivityCollection.ListView, self).item_buttons_classes if cls != 'btn-secondary'] + ['btn-link']

        show_edit_button_permissions_only = [ 'edit_activities_from_the_feed' ]
        shortcut_urls = [''] + [u'activities/{}'.format(_tab) for _tab in HOME_ACTIVITY_TABS.keys()]

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(ActivityCollection.ListView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)
            queryset = self.collection._get_queryset_for_list_and_item(queryset, request=request)
            # Exclude hidden tags
            if request and request.user.is_authenticated() and request.user.preferences.hidden_tags:
                for tag, hidden in request.user.preferences.hidden_tags.items():
                    if hidden:
                        queryset = queryset.exclude(c_tags__contains=u'"{}"'.format(tag))
            else:
                queryset = queryset.exclude(_cache_hidden_by_default=True)
            # Get who archived if staff
            if request and request.user.is_authenticated() and request.user.is_staff:
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
                    'ajax_url': '/ajax/help/Report/',
                    'open_in_new_window': True,
                    'icon': 'about',
                }
            return buttons

        def show_homepage(self, context):
            return context.get('shortcut_url', None) is not None

        def show_sidebar_on_homepage(self, context):
            return context.get('shortcut_url', None) is None

        def extra_context(self, context):
            super(ActivityCollection.ListView, self).extra_context(context)

            # Header template (if any)
            context['header_template'] = self.header_template

            # Show homepage / hide sidebar

            if self.show_homepage(context):
                indexExtraContext(context)
                if not self.show_sidebar_on_homepage(context):
                    context['hide_sidebar'] = True

            # Activities tabs

            if context['request'].user.is_authenticated():
                context['activity_tabs'] = HOME_ACTIVITY_TABS
                context['active_activity_tab_name'] = context['filter_form'].active_tab
                if context['active_activity_tab_name']:
                    context['active_activity_tab'] = context['activity_tabs'][
                        context['active_activity_tab_name']]
                context['show_about_button'] = (
                    'help' in context['all_enabled']
                    and context['request'].LANGUAGE_CODE not in LANGUAGES_CANT_SPEAK_ENGLISH
                )
                # Context based on tab
                if context['filter_form'].active_tab == 'following':
                    context['no_result_template'] = 'include/activityFollowMessage'
            else:
                context['show_bump'] = True

            # Dyanmic loaded content in activities

            self.collection._item_and_list_extra_context(context['request'], context, self, item=None)

    class ItemView(MagiCollection.ItemView):
        template = custom_item_template
        ajax_callback = 'updateActivities'
        show_item_buttons = False
        show_item_buttons_justified = False
        show_edit_button_permissions_only = [ 'edit_activities_from_the_feed' ]

        @property
        def item_buttons_classes(self):
            return [cls for cls in super(ActivityCollection.ItemView, self).item_buttons_classes if cls != 'btn-secondary'] + ['btn-link']

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(ActivityCollection.ItemView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)
            return self.collection._get_queryset_for_list_and_item(queryset=queryset, request=request)

        def get_h1_title(self, *args, **kwargs):
            title_prefixes, h1 = super(ActivityCollection.ItemView, self).get_h1_title(*args, **kwargs)
            h1['title'] = _('Activity')
            return title_prefixes, h1

        def extra_context(self, context):
            super(ActivityCollection.ItemView, self).extra_context(context)

            # Dyanmic loaded content in activities

            self.collection._item_and_list_extra_context(context['request'], context, self, item=context['item'])

            # Show warning on hidden tags

            tags = context['item'].tags
            context['item'].hidden_reasons = [
                verbose_reason
                for tag_name, (_tag, verbose_reason, _reason) in models.getForbiddenTags(
                        context['request']).items()
                if tag_name in tags
            ]
            if context['item'].hidden_reasons:
                context['page_title'] = None
                context['h1_page_title'] = None
                context['comments_enabled'] = False

            # JSON-LD

            articleJsonLdFromActivity(context['item'], context=context)

    class AddView(MagiCollection.AddView):
        alert_duplicate = False
        form_class = forms.ActivityForm
        max_per_user_per_hour = 3
        ajax_callback = 'updateActivityForm'

    class EditView(MagiCollection.EditView):
        form_class = forms.ActivityForm
        ajax_callback = 'updateActivityForm'
        owner_only_or_permissions_required = []
        owner_only_or_one_of_permissions_required = [
            'edit_reported_things',
            'edit_activities_post_language',
        ]

        def allow_delete(self, item, request, context):
            return (
                'fix_language' not in request.GET
                and (
                    item.owner_id == request.user.id
                    or request.user.hasPermission('edit_reported_things')
                )
            )

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
        authentication_required = True
        allow_random = False

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(NotificationCollection.ListView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)
            if 'ajax_modal_only' in parameters:
                queryset = queryset.filter(seen=False)
            if request:
                queryset = queryset.filter(owner=request.user)
            return queryset

        def top_buttons(self, request, context):
            buttons = super(NotificationCollection.ListView, self).top_buttons(request, context)
            buttons['mark_all_read'] = {
                'show': bool(request.user.preferences.cached_unread_notifications),
                'has_permissions': True,
                'url': '/markallnotificationsread/',
                'classes': ['btn', 'btn-link-muted', 'pull-right'],
                'title': _('Mark all as read'),
                'icon': 'checked',
            }
            return buttons

        def extra_context(self, context):
            # Don't show total search results when opening from navbar popup
            if len(context['request'].GET) == 1 and 'page_size' in context['request'].GET:
                context['show_search_results'] = False
            # Mark notification as read when they show up
            to_update = [item.pk for item in context['items'] if not item.seen]
            if to_update:
                updated = models.Notification.objects.filter(pk__in=to_update).update(seen=True)
                if updated:
                    context['request'].user.preferences.force_update_cache('unread_notifications')
            # Show alert when notifications have been marked as read
            if (not context.get('before_template', None)
                and context['request'].GET.get('marked_read', None)):
                context['show_search_results'] = False
                context['before_template'] = 'include/alert'
                context['alert_message'] = _('{total} notifications were marked as read.').format(
                    total=int(context['request'].GET['marked_read']),
                )
                context['alert_type'] = 'success'
                context['alert_flaticon'] = 'checked'
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
                'classes': view.get_item_buttons_classes(request, context, item=item, block=True) + (
                    ['staff-only'] if self.add_view.staff_required else []
                ),
            }
        if not context['ajax']:
            for button in buttons.values():
                button['classes'] = [cls for cls in button['classes'] if cls != 'staff-only']
        return buttons

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        filter_form = forms.FilterBadges
        allow_random = False

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(BadgeCollection.ListView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)
            if request:
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
            of_user = request.GET.get('of_user', None)
            if of_user:
                if (context['request'].LANGUAGE_CODE not in LANGUAGES_CANT_SPEAK_ENGLISH
                    and 'help' in context['all_enabled']
                    and request.user.is_authenticated()
                    and unicode(request.user.id) == of_user):
                    buttons['get_badges'] = {
                        'show': True, 'has_permissions': True,
                        'url': '/help/Badges',
                        'ajax_url': '/ajax/help/Badges',
                        'icon': self.collection.icon,
                        'classes': self.get_top_buttons_classes(request, context),
                        'title': _('How to get badges?'),
                        'subtitle': _('Collect them all!'),
                        'open_in_new_window': True,
                    }
            else:
                for button in buttons.values():
                    button['classes'] = [cls for cls in button['classes'] if cls != 'staff-only']
            return buttons

        def check_permissions(self, request, context):
            super(BadgeCollection.ListView, self).check_permissions(request, context)
            if context['current'].startswith(u'{}_list'.format(self.collection.name)):
                if (hasattr(request, 'GET') and 'of_user' not in request.GET
                    and (not request.user.is_authenticated()
                         or not hasOneOfPermissions(
                             request.user, self.collection.AddView.one_of_permissions_required))):
                    raise PermissionDenied()

    class ItemView(MagiCollection.ItemView):
        template = 'badgeInfo'
        comments_enabled = False
        fields_preselected = [ 'owner' ]

        def get_h1_title(self, request, context, item):
            _unused_title_prefixes, h1 = super(BadgeCollection.ItemView, self).get_h1_title(request, context, item)
            title_prefixes = [
                {
                    'title': unicode(item.owner),
                    'url': item.owner.item_url,
                },
                {
                    'title': _('{things} list').format(things=_('Badges')),
                    'url': addParametersToURL(item.owner.item_url, parameters={
                        'open': 'badge',
                    }, anchor='profiletabs'),
                }
            ]
            return title_prefixes, h1

    class AddView(MagiCollection.AddView):
        staff_required = True
        one_of_permissions_required = ['add_donation_badges', 'add_badges']
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

        def after_save(self, request, instance, type=None):
            instance = super(BadgeCollection.AddView, self).after_save(request, instance, type=type)
            # If the user had no badge before, update cache to say that they have badges now
            if (not instance.user.preferences.cached_tabs_with_content.get('badge', False)
                or (instance.show_on_profile
                    and not instance.user.preferences.cached_tabs_with_content.get('badge_top_profile', False))):
                instance.user.preferences.force_update_cache('tabs_with_content')
            return instance

    class EditView(MagiCollection.EditView):
        staff_required = True
        one_of_permissions_required = ['add_donation_badges', 'add_badges']
        allow_delete = True

        def check_type_permissions(self, request, context, type=None, item=None):
            if type == 'donator' and not hasPermission(request.user, 'add_donation_badges'):
                raise PermissionDenied()

        # If the badge wasn't shown on top profile and is now shown, update cache

        def after_save(self, request, instance):
            instance = super(BadgeCollection.EditView, self).after_save(request, instance)
            # _previous_show_on_top_profile is set in form init
            if (instance.show_on_profile != request._previous_show_on_top_profile):
                instance.user.preferences.force_update_cache('tabs_with_content')
            return instance

        # After deleting, update cache

        def before_delete(self, request, instance, ajax=False):
            super(BadgeCollection.EditView, self).before_delete(request, instance, ajax=ajax)
            request._badge_user = instance.user
            return instance

        def after_delete(self, request):
            super(BadgeCollection.EditView, self).after_delete(request)
            request._badge_user.preferences.force_update_cache('tabs_with_content')

############################################################
# Report Collection / Suggestion Collection

class _BaseReportCollection(MagiCollection):
    navbar_link_list = 'staff'
    queryset = models.Report.objects.select_related(
        'owner', 'owner__preferences', 'staff', 'staff__preferences',
    ).prefetch_related(Prefetch('images', to_attr='all_images'))

    reportable = False
    blockable = False

    def get_collections(self):
        return {
            name: collection
            for name, collection in getMagiCollections().items()
            if (collection.allow_suggest_edit if self.name == 'suggestededit' else collection.reportable)
        }

    @property
    def types(self):
        if not getMagiCollections():
            return True
        if not self._cached_types:
            self._cached_types = {
                collection.model_name: {
                    'title': collection.title,
                    'plural_title': collection.plural_title,
                    'image': collection.image,
                    'icon': collection.icon,
                }
                for collection in self.get_collections().values()
            }
        return self._cached_types
    _cached_types = None

    class ListView(MagiCollection.ListView):
        item_template = 'reportItem'
        show_title = True
        staff_required = True
        show_edit_button = False
        per_line = 1
        js_files = ['reports']
        ajax_pagination_callback = 'updateReport'
        filter_form = forms.FilterReports
        show_add_button = justReturn(False)
        allow_random = False

        def extra_context(self, context):
            context['can_moderate_own_reports'] = context['request'].user.hasPermission('moderate_own_reports')

    class ItemView(MagiCollection.ItemView):
        template = 'reportItem'
        comments_enabled = False
        show_edit_button = False
        js_files = ['reports']
        ajax_callback = 'updateReport'

        def extra_context(self, context):
            context['can_moderate_own_reports'] = context['request'].user.hasPermission('moderate_own_reports')

    class AddView(MagiCollection.AddView):
        authentication_required = True
        alert_duplicate = False
        back_to_list_button = False

    class EditView(MagiCollection.EditView):
        allow_delete = True
        redirect_after_delete = justReturn('/')
        back_to_list_button = False

class ReportCollection(_BaseReportCollection):
    title = _('Report')
    plural_title = _('Reports')
    icon = 'warning'
    queryset = _BaseReportCollection.queryset.filter(is_suggestededit=False)
    form_class = forms.ReportForm

    @property
    def add_sentence(self):
        return _('Report')

    def before_save(self, request, instance, type=None):
        super(ReportCollection, self).before_save(request, instance, type=type)
        if (instance.reason == 'Wrong details'
            and instance.reported_thing_collection
            and instance.reported_thing_collection.allow_suggest_edit):
            instance.is_suggestededit = True
        return instance

    class ListView(_BaseReportCollection.ListView):
        permissions_required = ['moderate_reports']

    class ItemView(_BaseReportCollection.ItemView):
        owner_only_or_permissions_required = ['moderate_reports']

class SuggestedEditCollection(_BaseReportCollection):
    name = 'suggestededit'
    plural_name = 'suggestededits'
    title = _('Suggested edit')
    plural_title = _('Suggested edits')
    icon = 'edit'
    queryset = _BaseReportCollection.queryset.filter(is_suggestededit=True)
    form_class = forms.SuggestedEditForm

    @property
    def add_sentence(self):
        return _('Suggest edit')

    class ListView(_BaseReportCollection.ListView):
        permissions_required = ['moderate_suggested_edits']

    class ItemView(_BaseReportCollection.ItemView):
        owner_only_or_permissions_required = ['moderate_suggested_edits']

############################################################
# Donate Collection

class DonateCollection(MagiCollection):
    enabled = False
    title = 'Donation Month'
    plural_title = _('Donators')
    plural_name = 'donate'
    icon = 'heart'
    navbar_link_list = 'more'
    queryset =  models.DonationMonth.objects.all()
    reportable = False
    blockable = False
    form_class = forms.DonateForm

    class ListView(MagiCollection.ListView):
        item_template = custom_item_template
        page_size = 1
        per_line = 1
        show_title = False
        before_template = 'include/donate'
        add_button_subtitle = ''
        allow_random = False

        def share_image(self, context, item=None):
            return DONATE_IMAGE

        def get_page_title(self):
            return _('Donate')

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(DonateCollection.ListView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)
            extra_select = {
                u'user_is_{}'.format(status): 'CASE WHEN i_status = \'{}\' THEN 1 ELSE 0 END'.format(status)
                for status, verbose in models.UserPreferences.STATUS_CHOICES
            }
            extra_select['has_rank'] = 'CASE WHEN rank IS NULL THEN 0 ELSE 1 END'
            extra_select['user_has_status'] = 'CASE WHEN i_status IS NULL THEN 0 WHEN i_status = \'\' THEN 0 ELSE 1 END'
            order = [
                u'-user_is_{}'.format(status)
                for status, verbose in reversed(models.UserPreferences.STATUS_CHOICES)
            ]
            queryset = queryset.prefetch_related(
                Prefetch('badges',
                         queryset=models.Badge.objects.select_related(
                             'user', 'user__preferences',
                         ).prefetch_related(
                             Prefetch('user__links', to_attr='all_links'),
                         ).extra(select=extra_select).order_by(*[
                             '-show_on_top_profile',
                             '-has_rank',
                             '-rank',
                             '-user_has_status',
                         ] + order + [
                             '-user__preferences__donation_link',
                         ]),
                         to_attr='all_badges'),
            )
            queryset = queryset.filter(date__lte=timezone.now())
            return queryset

        def extra_context(self, context):
            request = context['request']
            context['show_paypal'] = 'show_paypal' in request.GET
            context['donate_image'] = DONATE_IMAGE
            if request.user.is_authenticated() and request.user.hasPermission('manage_donation_months'):
                context['show_donator_details'] = True
            context['consider_donating_sentence'] = _('If you like {site_name}, please consider donating').format(
                site_name=getSiteName())

    class ItemView(MagiCollection.ItemView):
        enabled = False

    class AddView(MagiCollection.AddView):
        staff_required = True
        permissions_required = ['manage_donation_months']

    class EditView(MagiCollection.EditView):
        staff_required = True
        permissions_required = ['manage_donation_months']
        allow_delete = True

############################################################
# Prize Collection

PRIZE_CUTEFORM = {
    'i_character': {
        'to_cuteform': lambda k, v: getCharacterImageFromPk(k),
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
    fields_class = magifields.PrizeFields
    navbar_link_list = 'staff'
    filter_cuteform = PRIZE_CUTEFORM
    reportable = False
    icon = 'present'

    class ListView(MagiCollection.ListView):
        staff_required = True
        one_of_permissions_required = ['add_prizes', 'manage_prizes']
        filter_form = forms.PrizeFilterForm
        show_items_names = True

    class ItemView(MagiCollection.ItemView):
        staff_required = True
        hide_icons = True

    class AddView(MagiCollection.AddView):
        staff_required = True
        one_of_permissions_required = ['add_prizes', 'manage_prizes']

    class EditView(MagiCollection.EditView):
        staff_required = True
        owner_only_or_permissions_required = ['manage_prizes']
        allow_delete = True

class PrizeViewingCollection(PrizeCollection):
    enabled = True
    navbar_link = False
    navbar_link_list = False
    queryset = models.Prize.objects.filter(Q(giveaway_url__isnull=True) | Q(giveaway_url=''))
    plural_title = _('Prizes')

    filter_cuteform = PrizeCollection.filter_cuteform.copy()
    filter_cuteform['i_character']['extra_settings'] = {}

    class ListView(PrizeCollection.ListView):
        staff_required = False
        one_of_permissions_required = []
        filter_form = forms.PrizeViewingFilterForm
        default_ordering = 'value,-id'

    class ItemView(PrizeCollection.ItemView):
        enabled = False

    class AddView(PrizeCollection.AddView):
        enabled = False

    class EditView(PrizeCollection.EditView):
        enabled = False

############################################################
# Private Message Collection

class PrivateMessageCollection(MagiCollection):
    title = _('Private message')
    plural_title = _('Private messages')
    queryset = models.PrivateMessage.objects.select_related(
        'owner', 'owner__preferences',
        'to_user', 'to_user__preferences',
    )
    icon = 'contact'
    form_class = forms.PrivateMessageForm
    navbar_link_list = 'you'
    reportable = False

    add_sentence = _('Send a message')

    @classmethod
    def _get_user_for_thread_with(self, request):
        request.thread_with = get_object_or_404(models.User.objects.select_related('preferences').extra(select={
            'is_followed_by': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = (SELECT id FROM {table} WHERE user_id = auth_user.id) AND user_id = {id}'.format(
                table=models.UserPreferences._meta.db_table,
                id=request.user.id,
            ),
            'followed': 'SELECT COUNT(*) FROM {table}_following WHERE userpreferences_id = {id} AND user_id = auth_user.id'.format(
                table=models.UserPreferences._meta.db_table,
                id=request.user.preferences.id,
            ),
        }), pk=request.GET['to_user'])

    def get_queryset(self, view=None, queryset=None, parameters={}, request=None):
        queryset = super(PrivateMessageCollection, self).get_queryset(
            view=view, queryset=queryset, parameters=parameters, request=request)
        if request:
            # Only return messages sent from or to me
            queryset = queryset.filter(Q(to_user=request.user) | Q(owner=request.user))
        return queryset

    class ListView(MagiCollection.ListView):
        filter_form = forms.PrivateMessageFilterForm
        per_line = 1
        authentication_required = True
        item_template = custom_item_template
        add_button_subtitle = None
        show_search_results = False
        hide_sidebar = True
        ajax_pagination_callback = 'loadPrivateMessages'
        item_blocked_template = 'default_blocked_template_in_list'
        allow_random = False

        def get_page_title(self):
            return _('Inbox')

        def get_queryset(self, queryset=None, parameters={}, request=None):
            queryset = super(PrivateMessageCollection.ListView, self).get_queryset(
                queryset=queryset, parameters=parameters, request=request)
            if not request:
                return queryset
            # Thread view (including search)
            if request.GET.get('to_user', None):
                # Get user thread with
                self.collection._get_user_for_thread_with(request)
            # Inbox view
            else:
                if not request.GET.get('search', None):
                    queryset = queryset.extra(
                        where=['{db_table}.id IN (SELECT MAX(threads.id) \
                        FROM (SELECT id, \
                        (CASE WHEN to_user_id = {user_id} THEN owner_id ELSE to_user_id END) AS thread_id \
                        FROM {db_table} \
                        WHERE to_user_id = {user_id} OR owner_id = {user_id} \
                        ORDER BY creation DESC \
                        ) threads \
                        GROUP BY thread_id \
                        )'.format(
                            db_table=queryset.model._meta.db_table,
                            user_id=request.user.id,
                        )],
                    ).select_related('to_user', 'owner')
            return queryset

        def top_buttons(self, request, context):
            buttons = super(PrivateMessageCollection.ListView, self).top_buttons(request, context)
            if 'add' in buttons:
                # Thread view
                if request.GET.get('to_user', None):

                    # Note: hasPermissionToMessage is already called when add button is added

                    # Link to form to send a message to to_user
                    buttons['add']['url'] = addParametersToURL(buttons['add']['url'], parameters={
                        'to_user': request.thread_with.id,
                    })
                    # Ajax popup allow to add message from same popup
                    if context['ajax']:
                        buttons['add']['ajax_url'] = u'/ajax{}'.format(buttons['add']['url'])

                    if not context['ajax'] and buttons['add']['has_permissions']:

                        # Report button
                        buttons['report'] = {
                            'classes': ['btn', 'btn-block', 'btn-link-secondary', 'btn-lg'],
                            'show': True,
                            'title': request.thread_with.report_sentence,
                            'icon': 'warning',
                            'has_permissions': True,
                            'url': request.thread_with.report_url,
                        }

                        # Block button
                        buttons['block'] = {
                            'classes': ['btn', 'btn-block', 'btn-link-secondary', 'btn-lg'],
                            'show': True,
                            'url': u'/block/{}/'.format(request.thread_with.id),
                            'icon': 'block',
                            'title': _(u'Block {username}').format(username=request.thread_with.username),
                            'has_permissions': True,
                        }

                # Inbox view
                else:
                    # No add button when searching
                    if request.GET.get('search', None):
                        del(buttons['add'])
                    else:
                        # Check if the user will be able to message anyone
                        buttons['add']['has_permissions'] = (
                            request.user.preferences.has_good_reputation
                            and request.user.preferences.private_message_settings != 'nobody'
                        )
                        # Add button lists users that could be messaged
                        parameters = {
                            'view': 'send_private_message',
                            'reverse_oder': 'on',
                        }
                        if request.user.preferences.private_message_settings == 'follow':
                            parameters['ordering'] = 'preferences___cache_reputation'
                            parameters['followed_by'] = request.user.id
                        else:
                            parameters['ordering'] = 'followed,id'
                        buttons['add']['url'] = addParametersToURL('/users/', parameters)
                        buttons['add']['ajax_url'] = u'/ajax{}&ajax_modal_only'.format(buttons['add']['url'])
            return buttons

        def foreach_items(self, index, item, context):
            _super = super(PrivateMessageCollection.ListView, self).foreach_items
            if _super: _super(index, item, context)

            item.sent_by_me = item.owner == context['request'].user
            item.is_new_message = not item.sent_by_me and not item.seen
            item.thread_with = item.owner if item.to_user == context['request'].user else item.to_user

            # Thread view (including search)
            if context['request'].GET.get('to_user', None):
                # Mark messages received as seen
                if not item.sent_by_me and not item.seen:
                    item.seen = True
                    item.save()
            # Inbox view
            else:
                # Check for blocked threads for owner as well
                if item.to_user_id in context['request'].user.preferences.cached_blocked_ids:
                    item.blocked = True
                    item.blocked_message = _(u'You blocked {username}.').format(username=item.to_user.username)
                    item.unblock_button = _(u'Unblock {username}').format(username=item.to_user.username)
                    item.blocked_owner_id = item.to_user.id

        def get_h1_title(self, request, context, *args, **kwargs):
            title_prefixes, h1 = super(PrivateMessageCollection.ListView, self).get_h1_title(
                request, context, *args, **kwargs)
            # Thread view
            if request.GET.get('to_user', None):
                title_prefixes.append({
                    'title': _('Inbox'),
                    'url': self.collection.get_list_url(),
                })
                h1 = {
                    'title': request.thread_with.username,
                    'image': models.avatar(request.thread_with, size=39),
                }
            # Inbox view
            else:
                pass
            return title_prefixes, h1

        def extra_context(self, context):
            super(PrivateMessageCollection.ListView, self).extra_context(context)

            if (not context['ajax']
                and ('add' not in context['top_buttons']
                     or not context['top_buttons']['add']['has_permissions'])):
                # Show reputation not allowed warning
                if not context['request'].user.preferences.has_good_reputation:
                    context['before_template'] = 'include/alert'
                    context['alert_title'] = _('You are not allowed to send private messages.')
                    context['alert_message'] = _('Take some time to play around {site_name} to unlock this feature!').format(site_name=context['t_site_name'])
                    context['alert_flaticon'] = 'about'
                    context['alert_type'] = 'info'

                # If inbox setting is "nobody", show link to settings to open
                elif context['request'].user.preferences.private_message_settings == 'nobody':
                    context['alert_title'] = _('Your inbox is closed.')
                    context['alert_button_string'] = _('Settings')
                    context['alert_button_link'] = u'/settings/#security'
                    context['alert_flaticon'] = 'about'
                    context['alert_type'] = 'info'

            # Thread view
            if context['request'].GET.get('to_user', None):
                context['pm_view'] = 'thread'
                context['thread_with'] = context['request'].thread_with
                context['show_search_results'] = 'search' in context['request'].GET
                context['hide_sidebar'] = not bool(context['request'].GET.get('search', None))
                context['top_buttons_col_size'] = 12
            # Inbox view
            else:
                context['pm_view'] = 'inbox'
                # Search
                if context['request'].GET.get('search', None):
                    context['hide_sidebar'] = False
                    context['show_search_results'] = True
                # Normal, without search
                else:
                    pass

    class ItemView(MagiCollection.ItemView):
        enabled = False

    class AddView(MagiCollection.AddView):
        alert_duplicate = False
        max_per_user_per_day = 100
        max_per_user_per_hour = 30
        max_per_user_per_minute = 2

        def check_permissions(self, request, context):
            super(PrivateMessageCollection.AddView, self).check_permissions(request, context)
            if not request.GET.get('to_user', None):
                raise PermissionDenied()
            self.collection._get_user_for_thread_with(request)
            if not request.user.hasPermissionToMessage(request.thread_with):
                raise PermissionDenied()

        def get_h1_title(self, request, context, *args, **kwargs):
            title_prefixes, h1 = super(PrivateMessageCollection.AddView, self).get_h1_title(
                request, context, *args, **kwargs)
            title_prefixes.append({
                'title': request.thread_with.username,
                'url': self.collection.get_list_url(parameters={
                    'to_user': request.thread_with.pk,
                }),
            })
            return title_prefixes, h1

        def redirect_after_add(self, request, instance, ajax=False):
            return self.collection.get_list_url(ajax=ajax, modal_only=ajax, parameters={
                'to_user': request.thread_with.pk,
                'ajax_show_top_buttons': True if ajax else None,
            })

        def after_save(self, request, instance, type=None):
            instance = super(PrivateMessageCollection.AddView, self).after_save(request, instance)
            pushNotification(
                request.thread_with,
                'private-message',
                [request.user.username],
                url_values=[request.user.id],
                image=request.user.image_url,
            )
            return instance

        def extra_context(self, context):
            super(PrivateMessageCollection.AddView, self).extra_context(context)
            context['back_to_list_url'] = self.collection.get_list_url(
                ajax=context['ajax'], modal_only=context['ajax'], parameters={
                    'to_user': context['request'].GET['to_user'],
                    'ajax_show_top_buttons': True if context['ajax'] else None,
                })

    class EditView(MagiCollection.EditView):
        enabled = False
