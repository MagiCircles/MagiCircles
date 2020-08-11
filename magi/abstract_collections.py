import operator
from django.utils.translation import ugettext_lazy as _
from magi.magicollections import MainItemCollection
from magi.utils import (
    eventToCountDownField,
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

    def get_fields_icons_for_version(self, version_name, version):
        return {
            u'{}image'.format(version['prefix']): version.get('icon', None),
            u'{}start_date'.format(version['prefix']): 'date',
            u'{}end_date'.format(version['prefix']): 'date',
        }

    @property
    def fields_icons(self):
        fields_icons = self.base_fields_icons.copy()
        for version_name, version in self.versions.items():
            fields_icons.update(self.get_fields_icons_for_version(version_name, version))
        return fields_icons

    ############################################################
    # Fields images

    base_fields_images = {}

    def get_fields_images_for_version(self, version_name, version):
        return {
            u'{}image'.format(version['prefix']): version.get('image', None),
        }

    @property
    def fields_images(self):
        fields_images = self.base_fields_images.copy()
        for version_name, version in self.versions.items():
            fields_images.update(self.get_fields_images_for_version(version_name, version))
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
        auto_filter_form = True # todo

    ############################################################
    # Item view

    class ItemView(MainItemCollection.ItemView):
        ajax_callback = 'loadBaseEvent'

        # Fields order

        fields_order_before = [
            'name',
            'c_versions',
        ]

        @property
        def fields_order(self):
            return self.fields_order_before + [
                # Fields per version
                field_name.format(version['prefix'])
                for version_name, version in self.collection.versions.items()
                for field_name in [
                        version_name,
                        '{}countdown',
                ] + self.collection.queryset.model.FIELDS_PER_VERSION
            ]

        # Fields exclude

        fields_exclude_per_version = [
            'image'
        ]

        @property
        def fields_exclude(self):
            # todo
            print '----'
            try:
                print [
                    self.collection.queryset.model.get_field_names_all_versions(field_name)
                    for field_name in self.fields_exclude_per_version
                ]
            except:
                import traceback
                traceback.print_exc()
                print '/////'
            return reduce(operator.add, [
                self.collection.queryset.model.get_field_names_all_versions(field_name)
                for field_name in self.fields_exclude_per_version
            ])

        # Extra fields

        def get_extra_fields(self, item):
            extra_fields = super(BaseEventCollection.ItemView, self).get_extra_fields(item)

            if self.collection.with_versions:

                for version_name in item.versions:

                    # Add title for each version
                    title_field = {
                        'image': item.get_version_image(version_name),
                        'icon': item.get_version_icon(version_name),
                        'verbose_name': item.get_name_for_version(version_name),
                        'verbose_name_subtitle': item.get_version_name(version_name),
                    }
                    image = item.get_field_for_version('image_url', version_name)
                    if image:
                        title_field.update({
                            'type': 'image_link',
                            'value': image,
                            'link_text': item.get_name_for_version(version_name),
                            'link': item.get_field_for_version('image_original_url', version_name),
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

            else:
                pass
            # todo

            return extra_fields
