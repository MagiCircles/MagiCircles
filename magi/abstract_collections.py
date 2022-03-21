import operator
from django.utils.translation import ugettext_lazy as _
from magi.magicollections import MainItemCollection
from magi.utils import (
    addParametersToURL,
    eventToCountDownField,
    listUnique,
    modelFieldVerbose,
    modelHasField,
    staticImageURL,
)
from magi import forms

def to_EventParticipationCollection(cls):
    class _EventParticipationCollection(cls):
        title = _('Event participation')
        plural_title = _('Event participations')
    return _EventParticipationCollection

class BaseEventCollection(MainItemCollection):
    title = _('Event')
    plural_title = _('Events')
    translated_fields = ['name', 'm_description']
    icon = 'event'

    def __init__(self, *args, **kwargs):
        super(BaseEventCollection, self).__init__(*args, **kwargs)
        self.with_versions = modelHasField(self.queryset.model, 'c_versions')
        self.versions = self.queryset.model.VERSIONS if self.with_versions else {}

    ############################################################
    # Fields icons

    base_fields_icons = {
        'name': 'event',
        'description': 'about',
        'versions': 'world',
        'start_date': 'date',
        'end_date': 'date',
    }

    fields_icons_per_version = {
        u'{}start_date': 'date',
        u'{}end_date': 'date',
    }

    fields_icons_per_version_and_language = {
    }

    def get_fields_icons_per_version(self, version_name, version):
        return {
            u'{}image': version.get('icon', None),
        }

    def get_fields_icons_per_version_and_language(self, version_name, version, language):
        return {
            u'{}image': version.get('icon', None),
        }

    @property
    def fields_icons(self):
        fields_icons = self.base_fields_icons.copy()
        if self.with_versions:
            # Static fields_icons_per_version + fields_icons_per_version_and_language
            for template_field_name, icon in self.fields_icons_per_version.items() + self.fields_icons_per_version_and_language.items():
                fields_icons.update({ field_name: icon for field_name in self.queryset.model.get_all_versions_field_names(template_field_name) })
            # Dynamic get_fields_icons_per_version
            for version_name, version in self.versions.items():
                for template_field_name, icon in self.get_fields_icons_per_version(version_name, version).items():
                    fields_icons[self.queryset.model.get_field_name_for_version(template_field_name, version_name)] = icon
                for language in self.queryset.model.get_version_languages(version_name):
                    for template_field_name, icon in self.get_fields_icons_per_version_and_language(version_name, version, language).items():
                        fields_icons[self.queryset.model.get_field_name_for_version_and_language(template_field_name, version_name, language)] = icon
        return fields_icons

    ############################################################
    # Fields images

    base_fields_images = {}

    fields_images_per_version = {
    }

    fields_images_per_version_and_language = {
    }

    def get_fields_images_per_version(self, version_name, version):
        return {
            u'{}image': version.get('image', None),
        }

    def get_fields_images_per_version_and_language(self, version_name, version, language):
        return {
            u'{}image': version.get('image', None),
        }

    @property
    def fields_images(self):
        fields_images = self.base_fields_images.copy()
        if self.with_versions:
            # Static fields_images_per_version + fields_images_per_version_and_language
            for template_field_name, image in self.fields_images_per_version.items() + self.fields_images_per_version_and_language.items():
                fields_images.update({ field_name: image for field_name in self.queryset.model.get_all_versions_field_names(template_field_name) })
            # Dynamic get_fields_images_per_version
            for version_name, version in self.versions.items():
                for template_field_name, image in self.get_fields_images_per_version(version_name, version).items():
                    fields_images[self.queryset.model.get_field_name_for_version(template_field_name, version_name)] = image
                for language in self.queryset.model.get_version_languages(version_name):
                    for template_field_name, image in self.get_fields_images_per_version_and_language(version_name, version, language).items():
                        fields_images[self.queryset.model.get_field_name_for_version_and_language(template_field_name, version_name, language)] = image
        return fields_images

    ############################################################
    # Form class

    def to_form_class(self):
        self._form_class = forms.to_EventForm(self)

    ############################################################
    # Participations (collectible, only when specified)

    def collectible_to_class(self, model_class):
        cls = super(BaseEventCollection, self).collectible_to_class(model_class)
        if model_class.collection_name == 'eventparticipation':
            return to_EventParticipationCollection(cls)
        return cls

    ############################################################
    # List view

    class ListView(MainItemCollection.ListView):

        @property
        def default_ordering(self):
            return u','.join(getattr(self.collection.queryset.model._meta, 'ordering', [])) or '-start_date'

        def to_filter_form_class(self):
            self.filter_form = forms.to_EventFilterForm(self)

    ############################################################
    # Item view

    class ItemView(MainItemCollection.ItemView):
        ajax_callback = 'loadBaseEvent'

        # Fields order

        fields_order_before = [
            'name',
            'c_versions',
        ]

        def get_fields_order(self, item):
            if self.collection.with_versions:
                order = self.fields_order_before
                for version_name in item.versions_display_order:
                    order.append(version_name)
                    order += [
                        self.collection.queryset.model.get_field_name_for_version('{}countdown', version_name)
                    ] + self.collection.queryset.model.ALL_FIELDS_BY_VERSION[version_name]
                return order
            return []

        def extra_context(self, context):
            super(BaseEventCollection.ItemView, self).extra_context(context)
            if 'js_variables' not in context:
                context['js_variables'] = {}
            context['js_variables']['event_collection_name'] = self.collection.name
            context['js_variables']['with_versions'] = self.collection.with_versions
            if self.collection.with_versions:
                context['js_variables']['versions'] = self.collection.versions
                context['js_variables']['opened_versions'] = context['item'].opened_versions

        # Fields exclude
        fields_exclude_before = []
        fields_exclude_per_version = []
        fields_exclude_per_version_and_language = []

        @property
        def fields_exclude(self):
            try:
                fields_excluded = MainItemCollection.ItemView.fields_exclude.fget(self) + self.fields_exclude_before
            except AttributeError:
                fields_excluded = self.fields_exclude_before
            if self.collection.with_versions:
                return reduce(operator.add, [
                    self.collection.queryset.model.get_all_versions_field_names(field_name)
                    for field_name in self.fields_exclude_per_version + self.fields_exclude_per_version_and_language
                ], fields_excluded)
            return fields_excluded

        # Extra fields

        def get_extra_fields(self, item):
            extra_fields = super(BaseEventCollection.ItemView, self).get_extra_fields(item)

            if self.collection.with_versions:

                for version_name in item.versions:

                    anchor = u'version{}'.format(version_name)

                    # Add title for each version
                    title_field = {
                        'image': item.get_version_image(version_name),
                        'icon': item.get_version_icon(version_name),
                        'verbose_name': item.get_name_for_version(version_name) or unicode(item),
                        'verbose_name_subtitle': item.get_version_name(version_name),
                        'attributes': { 'id': anchor },
                    }
                    if '{}image' in self.collection.queryset.model.FIELDS_PER_VERSION_AND_LANGUAGE:
                        image = item.get_value_of_relevant_language_for_version('image_url', version_name)
                    else:
                        image = item.get_field_for_version('image_url', version_name)
                    if image:
                        title_field.update({
                            'type': 'image_link',
                            'value': image,
                            'link_text': item.get_name_for_version(version_name),
                            'link': addParametersToURL(item.item_url, anchor=anchor),
                            'not_new_window': True,
                        })
                    else:
                        title_field.update({
                            'type': 'text',
                            'value': '',
                        })
                    extra_fields.append((version_name, title_field))

                    # Add countdown

                    status = item.get_status_for_version(version_name)
                    if status and status not in ['ended', 'invalid']:
                        extra_fields.append(eventToCountDownField(
                            start_date=item.get_start_date_for_version(version_name),
                            end_date=item.get_end_date_for_version(version_name),
                            field_name=item.get_field_name_for_version('{}countdown', version_name),
                        ))

                    # Add participations(?) todo

            return extra_fields

        def to_fields(self, item, *args, **kwargs):
            fields = super(BaseEventCollection.ItemView, self).to_fields(item, *args, **kwargs)
            if self.collection.with_versions:
                # Links to versions with smooth page scroll
                if getattr(item, 'request', None) and not item.request.path_info.startswith('/ajax/'):
                    if 'versions' in fields:
                        fields['versions'].update({
                            'type': 'list_links',
                            'links': [{
                                'link': u'#version{}'.format(version_name),
                                'value': item.get_version_name(version_name),
                                'not_new_window': True,
                                'attributes': { 'class': 'page-scroll' },
                            } for version_name in item.versions_display_order
                            ],
                        })
            return fields
