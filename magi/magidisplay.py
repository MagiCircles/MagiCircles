# -*- coding: utf-8 -*-
import datetime, string
from collections import OrderedDict
from django.conf import settings as django_settings
from django.utils.translation import ugettext_lazy as _
from magi.utils import (
    ALERT_TEMPLATE,
    ALERT_BUTTON_TEMPLATE,
    AttrDict,
    failSafe,
    getColOffset,
    getColSize,
    hasValue,
    isMarkedSafe,
    justReturn,
    markSafe,
    markSafeFormat,
    markSafeJoin,
    markUnsafe,
    mergeDicts,
    templateVariables,
    torfc2822,
)

__all__ = [
    'MagiDisplay',
    'MagiDisplayMultiple',

    'MagiDisplayText',
    'MagiDisplayLongText',
    'MagiDisplayTextWithLink',
    'MagiDisplayMarkdown',
    'MagiDisplayLink',
    'MagiDisplayButton',
    'MagiDisplayImage',
    'MagiDisplayFigure',
    'MagiDisplayDateTimeWithTimezones',
    'MagiDisplayCountdown',
    'MagiDisplayITunes',
    'MagiDisplayColor',
    'MagiDisplayYouTubeVideo',
    'MagiDisplayMultiple',
    'MagiDisplayList',
    'MagiDisplayDict',
    'MagiDisplayOrderedList',
    'MagiDisplayDescriptionList',
    'MagiDisplayGrid',
    'MagiDisplayGallery',
    'MagiDisplayTextarea',
    'MagiDisplayAlert',

    'MagiDisplayButtons',
]

############################################################
# Utils

class MagiDisplayWithTooltipMixin(object):
    """
    This class should only be used as a mixin, with your class still inheriting from one of the display classes below.
    To use it, simply add `{tooltip}` anywhere in your template. Don't forget to call super if you have your
    own __init__ or to_parameters_extra.
    You can also override `to_default_tooltip`.
    """
    TOOLTIP_PARAMETERS = {
        'tooltip': False, # defaults to verbose name
        'tooltip_trigger': 'hover',
        'tooltip_placement': 'top',
        'tooltip_container': 'body',
        'tooltip_html': 'false', # defaults to auto detects based on tooltip value
    }
    template_tooltip = u"""
    data-toggle="tooltip" title="{tooltip}"
    data-trigger="{tooltip_trigger}" data-html="{tooltip_html}"
    data-placement="{tooltip_placement}" data-container="{tooltip_container}"
    """

    def __init__(self, *args, **kwargs):
        self.OPTIONAL_PARAMETERS = mergeDicts(self.OPTIONAL_PARAMETERS, self.TOOLTIP_PARAMETERS)

    def to_default_tooltip(self, parameters):
        return parameters.verbose_name

    def to_parameters_extra(self, parameters):
        if parameters.tooltip:
            if parameters.tooltip == True:
                parameters.tooltip = self.to_default_tooltip(parameters)
            elif isMarkedSafe(parameters.tooltip):
                parameters.tooltip_html = 'true'

############################################################
# MagiDisplay

class MagiDisplay(object):

    ############################################################
    # Variables and methods that can be changed per subclass
    # "Parameters" are both details you can use within the logic
    # of your display field, and template variables.

    OPTIONAL_PARAMETERS = {}
    REQUIRED_PARAMETERS = []
    AUTO_REQUIRED_PARAMETERS = False
    DONT_CALL_CALLABLE_PARAMETERS_FOR = []

    def to_display_value(self, value, parameters):
        return value

    def to_parameters_extra(self, parameters):
        pass

    # Use parameters.original_value to check if it's the correct type
    # ⚠️ Will not have called .to_display_value and .to_parameters_extra yet
    def is_valid_display_value(self, parameters):
        return True

    template = None

    # In addition to what's in valid_parameters, parameters contain auto-set parameters,
    # See AUTO_SET_PARAMETERS

    # template can be a callable that takes parameters.
    # You can set template_{} for any parameter, including display_value.
    # Templates can also be methods that take parameters.

    # If display_value is a dict, template can contain its keys which will be replaces by the values:
    # Example: '<a href="{url}">{verbose}</a>' with display_value { 'url': '...', 'verbose': '...' }

    # If a parameter's value (including display_value) is a list or a dict,
    # you can also set template_{}_foreach and template_{}_separator.
    # In addition to regular parameters, template variables will then contain 'i', 'value' and 'key' (dict only).
    # template_{}_foreach can also be a callable that takes parameters_per_item (= parameters + i/key/value).
    # For dicts, list_item is a tuple (key, value).

    # If a parameter's value is a dict and you don't use template_{}_foreach,
    # the template for that parameter can contain its keys which will be replaced by the values.

    # If you use a foreach template, you can also set to_{}_foreach_value
    # to define how the list/dict value is displayed. Takes parameters_per_item (= parameters + i/key/value).
    # If your value is a dict, the foreach template can contain its keys which will be replaced by the values.

    # Default templates:

    template_icon = u'<i class="flaticon-{icon}"></i>'
    template_image = u'<img src="{image}" alt="{verbose_name}" height="39">'

    ############################################################
    # Utils

    PARAMETERS = {
        'field_name': None,
        'verbose_name': None,
        'verbose_name_subtitle': None,
        'icon': None,
        'image': None,

        'classes': [],
        'attributes': {},
        'spread_across': False,
        'text_align': None,
        'annotation': None,
    }
    # It's not possible to set default values for PARAMETERS in MagiDisplay.
    # Defaults can be set in MagiField classes.
    AUTO_SET_PARAMETERS = [
        'item', 'original_value', 'display_value',
    ]

    @property
    def valid_parameters(self):
        return (
            self.PARAMETERS.keys()
            + self.REQUIRED_PARAMETERS
            + self.OPTIONAL_PARAMETERS.keys()
            + self.INTERNAL_PARAMETERS.keys()
        )

    ############################################################
    # To HTML is called within templates

    def to_html(self, item, value, **kwargs):
        kwargs_parameters = self.to_kwargs_parameters(item, value, **kwargs)
        is_valid_display_value, parameters = self.to_parameters(item, value, kwargs_parameters)
        if not is_valid_display_value:
            if django_settings.DEBUG:
                print '[Warning] Invalid value was given to display class {} for field {}'.format(
                    self.__class__.__name__, parameters.field_name)
            return parameters.original_value
        if not getattr(self, 'template', None):
            return parameters.display_value
        return self.apply_template_parameters(self.template, parameters)

    ############################################################
    # Internals

    INTERNAL_PARAMETERS = {}
    WILL_USE_PARAMETERS_FROM = [] # List of parameter names that contain display classes

    def __init__(self):
        # Shortcuts for list/dict for display value
        if hasattr(self, 'template_foreach'):
            self.template_display_value_foreach = self.template_foreach
        if hasattr(self, 'to_foreach_value'):
            self.to_display_value_foreach_value = self.to_foreach_value
        if hasattr(self, 'to_foreach_parameters_extra'):
            self.to_display_value_foreach_parameters_extra = self.to_foreach_parameters_extra
        # Auto-add parameters
        if self.AUTO_REQUIRED_PARAMETERS and not callable(self.template):
            self.REQUIRED_PARAMETERS = self.REQUIRED_PARAMETERS[:]
            valid_parameters = self.valid_parameters + self.AUTO_SET_PARAMETERS
            for variable in templateVariables(self.template):
                if variable not in valid_parameters:
                    self.REQUIRED_PARAMETERS.append(variable)

    def get_default_kwargs_parameter(self, parameter_name):
        return (
            self.OPTIONAL_PARAMETERS.get(parameter_name, None)
            or self.PARAMETERS.get(parameter_name, None)
            or self.INTERNAL_PARAMETERS.get(parameter_name, None)
        )

    def to_kwargs_parameters(self, item, value, strict_parameters=True, **kwargs):
        valid_parameters = self.valid_parameters + self.to_kwargs_parameters_from_parameters_display_classes(kwargs)
        kwargs_parameters = {}
        for parameter_name, parameter_value in kwargs.items():
            if strict_parameters and parameter_name not in valid_parameters:
                raise ValueError('Unknown parameter {} for display {}'.format(parameter_name, type(self)))
            kwargs_parameters[parameter_name] = parameter_value
        for parameter_name in valid_parameters:
            if parameter_name not in kwargs_parameters:
                if parameter_name in self.REQUIRED_PARAMETERS:
                    raise ValueError('Parameter {} is required for display {}'.format(parameter_name, type(self)))
                else:
                    kwargs_parameters[parameter_name] = self.get_default_kwargs_parameter(parameter_name)
        return kwargs_parameters

    def to_kwargs_parameters_from_parameters_display_classes(self, kwargs):
        extra_valid_parameters = []
        for display_class_parameter_name in self.WILL_USE_PARAMETERS_FROM:
            extra_valid_parameters.append(
                self.to_kwargs_parameters_from_parameters_display_class(display_class_parameter_name, kwargs),
            )
        return extra_valid_parameters

    def to_kwargs_parameters_from_parameters_display_class(self, display_class_name, kwargs):
        display_class = kwargs.get(display_class_name, self.OPTIONAL_PARAMETERS[display_class_name])
        kwargs_name = '_parameters_{}'.format(display_class_name)
        kwargs[kwargs_name] = {}
        for parameter_name in display_class.valid_parameters:
            if parameter_name in kwargs:
                if parameter_name in self.valid_parameters:
                    kwargs[kwargs_name][parameter_name] = kwargs.get(parameter_name)
                else:
                    kwargs[kwargs_name][parameter_name] = kwargs.pop(parameter_name)
        return kwargs_name

    @property
    def get_dont_call_callable_parameters_for(self):
        return self.DONT_CALL_CALLABLE_PARAMETERS_FOR + sum([ [
            display_class_name.replace('_display_class', '_to_parameters'),
            display_class_name.replace('_display_class', '_to_value'),
        ] for display_class_name in self.WILL_USE_PARAMETERS_FROM ], [])

    def to_parameters(self, item, value, kwargs_parameters):
        parameters = AttrDict()
        for parameter_name, kwargs_value in kwargs_parameters.items():
            if (parameter_name not in self.get_dont_call_callable_parameters_for
                and callable(kwargs_value)
                and not failSafe(lambda: issubclass(kwargs_value, object), exceptions=[TypeError])):
                setattr(parameters, parameter_name, kwargs_value(item))
            else:
                setattr(parameters, parameter_name, kwargs_value)
            if not hasValue(parameters[parameter_name], false_bool_is_value=False):
                setattr(parameters, parameter_name, u'')
        parameters.item = item
        parameters.original_value = value
        if not self.is_valid_display_value(parameters):
            return False, parameters
        parameters.display_value = self.to_display_value(value, parameters)
        self.to_parameters_extra(parameters)
        return True, parameters

    def prepare_template(self, template, parameters, parameters_templates, value, sub_item_name=None):
        if callable(template):
            template = template(parameters)
        template = template.replace('{{', '{{{{').replace('}}', '}}}}')
        if isinstance(value, dict):
            for key in templateVariables(template):
                if key in value:
                    parameters_templates[key] = self.get_parameter_template(
                        key, value[key], parameters, parameters_templates,
                        template_name=(
                            u'template_{}_{{}}'.format(sub_item_name) if sub_item_name else u'template_{}'),
                    )
                    parameters[key] = value[key]
        return template

    def get_parameter_template(self, parameter_name, parameter_value, parameters, parameters_templates, template_name=u'template_{}'):
        if not hasValue(parameter_value, false_bool_is_value=False):
            parameter_template = u''
        elif getattr(self, template_name.format(parameter_name), None):
            parameter_template = getattr(self, template_name.format(parameter_name))
        else:
            parameter_template = u'{{{}}}'.format(parameter_name)
        if callable(parameter_template):
            parameter_template = parameter_template(parameters)
        if (isinstance(parameter_value, dict)
            and not getattr(self, u'template_{}_foreach'.format(parameter_name), None)):
            for key in templateVariables(parameter_template):
                if key in parameter_value:
                    parameters_templates[key] = u'{{{}}}'.format(key)
                    parameters[key] = parameter_value[key]
        return parameter_template

    def apply_template_parameters(self, template, parameters):
        # Step 1: Parameters
        # Retrieve templates for each parameter:
        # parameters_templates = {
        #     'icon': '<i class="flaticon-{icon}">',
        #     'link': '{link}',
        #     'ajax_link': '',
        # }
        list_or_dict_parameters_keys = []
        parameters_templates = {}
        for parameter_name, parameter_value in parameters.items():
            parameters_templates[parameter_name] = self.get_parameter_template(
                parameter_name, parameter_value, parameters, parameters_templates)
            if (hasValue(parameter_value, false_bool_is_value=False)
                and (isinstance(parameter_value, list) or isinstance(parameter_value, dict))
                and getattr(self, u'template_{}_foreach'.format(parameter_name), None)):
                list_or_dict_parameters_keys.append(parameter_name)

        # Step 2: retrieve templates for each parameter
        # For lists, if there's a template_{}_foreach specified,
        # the value of the parameter gets changed to the already rendered parameter
        # parameter_templates = { 'items': u'<ul>{items}</ul>' }
        # Before: parameters = { 'items': [ _('Dance'), _('Fly') ] }
        # After:  parameters = { 'items': u'<li>Fly</li><li>Dance</li>' }
        # Which means when it will be applied it will be: u'<ul><li>Fly</li><li>Dance</li></ul>'
        for parameter_name in list_or_dict_parameters_keys:
            html = self.html_for_list_or_dict(
                parameter_name, parameters[parameter_name],
                parameters_templates, parameters,
            )
            setattr(parameters, parameter_name, html)

        # Step 3: For lists, if there's a template_{}_foreach specified, the value of
        # the parameter gets changed to the already rendered parameter
        template = self.prepare_template(self.template, parameters, parameters_templates, parameters.display_value)

        # Step 4: Get template
        # Apply parameters_templates:
        # Before: template = '<span>{icon} {display_value}</span>'
        # After:  template = '<span><i class="flaticon-{icon}"> {display_value}</span>'
        template = template.format(**parameters_templates)

        # Step 5: Apply parameters_templates
        # Apply parameters to template:
        # Before: '<span><i class="flaticon-{icon}"> {display_value}</span>'
        # After:  '<span><i class="flaticon-idol"> Kousaka Honoka</span>'

        html = markSafeFormat(template, **parameters)
        # Step 6: apply parameters to template
        return html

    def html_for_list_or_dict(self, parameter_name, parameter_value, parameters_templates, parameters):
        separator = getattr(self, u'template_{}_separator'.format(parameter_name), u' ')
        foreach_template = getattr(self, u'template_{}_foreach'.format(parameter_name))
        html_items = []
        for i, list_item in enumerate(parameter_value.items() if isinstance(parameter_value, dict) else parameter_value):
            # Prepare parameters per item:
            parameters_per_item = AttrDict(parameters.copy())
            parameters_per_item.i = i
            if isinstance(list_item, tuple):
                parameters_per_item.key = list_item[0]
                parameters_per_item.value = list_item[1]
            else:
                parameters_per_item.key = None
                parameters_per_item.value = list_item
            # If there's a to_{}_foreach_value set, apply to value
            if getattr(self, u'to_{}_foreach_value'.format(parameter_name), None):
                parameters_per_item['value'] = getattr(self, u'to_{}_foreach_value'.format(parameter_name))(parameters_per_item)
            # If there's a to_{}_foreach_parameters_extra set
            extra_parameters_per_item = {}
            if getattr(self, u'to_{}_foreach_parameters_extra'.format(parameter_name), None):
                extra_parameters_per_item = getattr(
                    self, u'to_{}_foreach_parameters_extra'.format(parameter_name))(parameters_per_item)
                parameters_per_item.update(extra_parameters_per_item)
            # Prepare parameters templates
            parameters_templates_per_item = parameters_templates.copy()
            for added_parameter_name in [ 'i', 'key', 'value' ] + extra_parameters_per_item.keys():
                parameters_templates_per_item[added_parameter_name] = self.get_parameter_template(
                    added_parameter_name, parameters_per_item[added_parameter_name],
                    parameters_per_item, parameters_templates_per_item,
                    template_name=u'template_{}_{{}}'.format(parameter_name) if parameter_name != 'display_value' else u'template_{}',
                )
            # Prepare template
            template_per_item = self.prepare_template(
                foreach_template, parameters_per_item, parameters_templates_per_item, list_item,
                sub_item_name=parameter_name)
            # Apply parameters_templates:
            template_per_item = template_per_item.format(**parameters_templates_per_item)
            # Apply parameters to template:
            html_per_item = markSafeFormat(template_per_item, **parameters_per_item)
            html_items.append(html_per_item)
        # Join all rendered HTML into 1
        return markSafeJoin(html_items, separator=separator)

    ############################################################
    # Tools

    def get_display_class_parameters(self, parameters, display_class_name, to_callable_parameters=lambda _parameters: [ _parameters ]):
        # For classes in WILL_USE_PARAMETERS_FROM
        display_class_parameters = getattr(parameters, u'_parameters_{}'.format(display_class_name), None) or {}
        to_parameters = getattr(parameters, display_class_name.replace('_display_class', '_to_parameters'), None)
        if to_parameters:
            display_class_parameters = mergeDicts(
                display_class_parameters,
                to_parameters(*to_callable_parameters(parameters))
                if callable(to_parameters)
                else to_parameters
            )
        return display_class_parameters

############################################################
############################################################
############################################################
############################################################
# Display classes

############################################################
# Text with icon

class _MagiDisplayText(MagiDisplay):
    """
    Value: string
    Optional image or icon
    Options for icons can be found at http://localhost:8000/static/css/flaticon.html
    """
    OPTIONAL_PARAMETERS = {
        'text_icon': None,
        'text_image': None,
        'text_image_height': 30,
        'text_image_alt': None, # defaults to verbose_name
        'text_badge': None,
    }
    truc = True

    def to_display_value(self, value, parameters):
        if isMarkedSafe(value):
            return value
        return unicode(value)

    def to_parameters_extra(self, parameters):
        parameters.text_image_alt = parameters.text_image_alt or parameters.verbose_name
        if parameters.text_badge == 0:
            parameters.text_badge = None

    template = u'{text_icon} {text_image} <span>{display_value}</span> {text_badge}'
    template_text_icon = u'<i class="flaticon-{text_icon}"></i>'
    template_text_image = u'<img src="{text_image}" alt="{text_image_alt}" height="{text_image_height}">'
    template_text_badge = u'<span class="badge progress-bar-main">{text_badge}</span>'

MagiDisplayText = _MagiDisplayText()

############################################################
# Long text

class _MagiDisplayLongText(MagiDisplay):
    """
    value: string
    """
    def to_display_value(self, value, parameters):
        if isMarkedSafe(value):
            return value
        return unicode(value)

    template = u'<div class="long-text-value">{display_value}</div>'

MagiDisplayLongText = _MagiDisplayLongText()

############################################################
# Text with link

class _MagiDisplayTextWithLink(MagiDisplay):
    """
    value: string
    A text value followed by a link right under it, with an image on the side.
    """
    REQUIRED_PARAMETERS = [
        'link',
        'link_text',
    ]
    OPTIONAL_PARAMETERS = {
        'new_window': True,
        'ajax_link': None,
        'ajax_link_title': None, # defaults to unicode of display_value
        'image_for_link': None, # defaults to image
    }

    def to_display_value(self, value, parameters):
        if isMarkedSafe(value):
            return value
        return unicode(value)

    def to_parameters_extra(self, parameters):
        parameters.ajax_link_title = parameters.ajax_link_title or unicode(parameters.display_value)
        parameters.image_for_link = parameters.image_for_link or parameters.image

    template = u"""
    <div class="text_with_link_wrapper">
        <span class="text_with_link">{display_value}<br>
            <a href="{link}" {new_window} {ajax_link}>
                {link_text}
                <i class="flaticon-link fontx0-8"></i>
            </a>
        </span>
        <a href="{link}" {new_window} {ajax_link}>
          {image_for_link}
        </a>
    </div>
    """

    template_new_window = u'target="_blank"'
    template_ajax_link = u'data-ajax-url="{ajax_link}" data-ajax-title="{display_value}" data-ajax-handle-form="true"'
    template_image_for_link = u'<img src="{image_for_link}" alt="{link_text}" class="text_with_link_image">'

MagiDisplayTextWithLink = _MagiDisplayTextWithLink()

############################################################
# Markdown

class _MagiDisplayMarkdown(MagiDisplay):
    """
    Value: tuple (True, '<b>something</b>') or (False, '**something**')
    """
    OPTIONAL_PARAMETERS = {
        'allow_html': False,
    }

    def is_valid_display_value(self, parameters):
        return (
            isinstance(parameters.original_value, tuple)
            and len(parameters.original_value) >= 2
            and isinstance(parameters.original_value[0], bool)
        )

    def to_display_value(self, value, parameters):
        if value[0]:
            return markSafe(value[1])
        return value[1]

    def template(self, parameters):
        return u"""
        <div class="long-text-value {was_markdown_class}">
        {{display_value}}
        </div>
        """.format(
            was_markdown_class='was-markdown' if parameters.original_value[0] else u''
        )

    def template_display_value(self, parameters):
        if parameters.original_value[0]:
            return u'{display_value}'
        return u'<div class="to-markdown {allow_html}">{{display_value}}</div>'.format(
            allow_html='allow-html' if parameters.allow_html else u'',
        )

MagiDisplayMarkdown = _MagiDisplayMarkdown()

############################################################
# Link

class _MagiDisplayLink(MagiDisplay):
    """
    Value: depends on display class.
    Default is MagiDisplay, so a simple string works.

    What's displayed within the link depends on link_content_display_class.
    Default link_content_display_class is MagiDisplayText.
    If you use a different display_class, you can setup parameters using link_content_to_parameters.
    """
    REQUIRED_PARAMETERS = [
        'link',
    ]
    OPTIONAL_PARAMETERS = {
        'ajax_link': None,
        'ajax_link_title': None, # defaults to verbose_name
        'link_attributes': {},
        'data_attributes': {},
        'link_classes': [],
        'link_subtitle': None,
        'new_window': False,
        'external_link_icon': False,
        'button': False,
        'button_class': 'secondary',
        'button_size': 'lg',

        'link_content_display_class': MagiDisplayText,
        'link_content_to_parameters': lambda _parameters: {},
        'link_content_to_value': lambda _value, _parameters: _value,
    }
    WILL_USE_PARAMETERS_FROM = [
        'link_content_display_class',
    ]

    def to_parameters_extra(self, parameters):
        parameters.ajax_link_title = parameters.ajax_link_title or parameters.verbose_name

    template = u"""
    <a href="{link}" class="{button} {link_classes}" {new_window} {ajax_link} {link_attributes}>
        {display_value} {external_link_icon} {link_subtitle}
    </a>
    """
    template_button = u'btn btn-{button_size} btn-{button_class} btn-lines'
    template_new_window = u'target="_blank"'
    template_external_link_icon = u'<i class="flaticon-link"></i>'
    template_link_subtitle = u'<br><span class="faded fontx0-8">{link_subtitle}</span>'
    template_ajax_link = u'data-ajax-url="{ajax_link}" data-ajax-title="{ajax_link_title}" data-ajax-handle-form="true"'
    template_link_attributes_foreach = u'{key}="{value}"'
    template_data_attributes_foreach = u'data-{key}="{value}"'
    template_link_classes_foreach = u'{value}'

    def to_display_value(self, value, parameters):
        return parameters['link_content_display_class'].to_html(
            parameters['item'], parameters.link_content_to_value(value, parameters),
            **self.get_display_class_parameters(parameters, 'link_content_display_class')
        )

MagiDisplayLink = _MagiDisplayLink()

############################################################
# Button

class _MagiDisplayButton(_MagiDisplayLink):
    OPTIONAL_PARAMETERS = mergeDicts(_MagiDisplayLink.OPTIONAL_PARAMETERS, {
        'button': True,
        'button_size': 'md',
    })

MagiDisplayButton = _MagiDisplayButton()

############################################################
# Image

class _MagiDisplayImage(MagiDisplayWithTooltipMixin, MagiDisplay):
    """
    Value: image URL (string), usually what's stored in the field, so TinyPNG optimized version
    """
    OPTIONAL_PARAMETERS = {
        'original': None, # Defaults to display_value
        'thumbnail': None, # Defaults to display_value
        'hq': None,
        'alt': None, # defaults to verbose_name

        # Single link
        'with_link_wrapper': True,
        'link': None, # defaults to opening the image in a new tab
        'ajax_link': None,
        'ajax_link_title': None, # only when ajax_link, defaults to alt then verbose_name
        'new_window': True,

        # Multiple links (including when hq is set)
        'original_label': _('Original'),
        'extra_links': [], # List of dicts with verbose (button name), url (image url),
        # optional: new_window, ajax_link, ajax_link_title
        'popover_title': _('Download'), # Only used when there is a hq or extra_links
        'background_size': None,
    }

    def to_parameters_extra(self, parameters):
        super(_MagiDisplayImage, self).to_parameters_extra(parameters)
        parameters.thumbnail = parameters.thumbnail or parameters.display_value
        parameters.original = parameters.original or parameters.display_value
        parameters.link = parameters.link or parameters.original
        parameters.alt = parameters.alt or parameters.verbose_name
        parameters.ajax_link_title = parameters.ajax_link_title or parameters.alt
        if parameters.hq or parameters.extra_links:
            parameters.links = [
                { 'verbose': parameters.original_label, 'url': parameters.original },
            ] + ([
                { 'verbose': parameters.alt, 'url': parameters.link },
            ] if parameters.link != parameters.original else []) + ([
                { 'verbose': _('High quality'), 'url': parameters.hq },
            ] if parameters.hq else []) + (
                parameters.extra_links or []
            )
        else:
            parameters.links = []

    def to_default_tooltip(self, parameters):
        return parameters.alt or parameters.verbose_name

    _BASE_TEMPLATE = u'<img class="image" src="{thumbnail}" alt="{alt}" {tooltip}>'

    def template(self, parameters):
        if parameters.links:
            return u"""
            <div class="image-with-links" data-thumbnail="{thumbnail}" style="{background_size}" {tooltip}>
                <h4>{popover_title}</h4>
                <ul class="list-group inline-block">
                    {links}
                </ul>
            </div>
            """
        elif parameters.with_link_wrapper:
            return u'<a href="{{link}}" {{new_window}} {{ajax_link}}>{}</a>'.format(self._BASE_TEMPLATE)
        return self._BASE_TEMPLATE

    template_background_size = u'background-size: {background_size};'
    template_new_window = u'target="_blank"'
    template_ajax_link = u'data-ajax-url="{ajax_link}" data-ajax-title="{ajax_link_title}" data-ajax-handle-form="true"'
    template_links_foreach = u'<li class="list-group-item"><a href="{url}" {new_window} {ajax_link}>{verbose} <i class="flaticon-link"></i></a></li>'
    template_links_ajax_link = template_ajax_link
    template_links_new_window = template_new_window

MagiDisplayImage = _MagiDisplayImage()

############################################################
# Figure

class _MagiDisplayFigure(MagiDisplayWithTooltipMixin, MagiDisplay):
    """
    Value: image URL (string), usually what's stored in the field, so TinyPNG optimized version
    """
    OPTIONAL_PARAMETERS = {
        'original': None, # Defaults to display_value
        'thumbnail': None, # Defaults to value
        'alt': None, # defaults to verbose_name
        'figcaption': None, # defaults to alt, set to False to not show
        'figure_attributes': [],
    }

    def to_parameters_extra(self, parameters):
        super(_MagiDisplayFigure, self).to_parameters_extra(parameters)
        parameters.thumbnail = parameters.thumbnail or parameters.display_value
        parameters.alt = parameters.alt or parameters.verbose_name
        parameters.original = parameters.original or parameters.display_value
        if parameters.figcaption is None:
            parameters.figcaption = parameters.alt

    def to_default_tooltip(self, parameters):
        return parameters.alt

    template = u"""
    <figure {figure_attributes}>
      <img class="image" src="{thumbnail}" alt="{alt}" {tooltip}>
      {figcaption}
    </figure>"""
    template_figcaption = u'<figcaption>{figcaption}</figcaption>'
    template_figure_attributes_foreach = u'{key}="{value}"'

MagiDisplayFigure = _MagiDisplayFigure()

############################################################
# DateTime fields

class _MagiDisplayDateTimeMixin(object):
    def is_valid_display_value(self, parameters):
        return isinstance(parameters.original_value, datetime.date)

    def to_display_value(self, value, parameters):
        return torfc2822(value)

# DateTime with timezones

class _MagiDisplayDateTimeWithTimezones(_MagiDisplayDateTimeMixin, MagiDisplay):
    """
    Value: a datetime in UTC
    """
    OPTIONAL_PARAMETERS = {
        'timezones': [
            'Local time',
        ],
        'show_how_long_ago': True,

        # https://github.com/MagiCircles/MagiCircles/wiki/HTML-elements-with-automatic-Javascript-behavior#timezones
        # Example: { 'month': 'short' }
        'format': {},
    }

    template = u'{timezones} {show_how_long_ago}'
    template_timezones_foreach = u"""
    <span class="timezone" data-to-timezone="{value}" {i} {format}>
        <span class="datetime">{display_value}</span>
        (<span class="current_timezone">UTC</span>)
    </span>
    """
    template_format_foreach = u'data-{key}-format="{value}"'
    template_timezones_separator = u'<br>'

    def template_timezones_i(self, parameters_per_item):
        # Only the 1st one should be visible when Javascript is off
        if parameters_per_item.i != 0:
            return u'style="display: none;"'
        return u''

    template_show_how_long_ago = u"""
    <br>
    <small class="text-muted"><span class="timezone" data-timeago="true" style="display: none;">
        <span class="datetime">{display_value}</span>
    </span></small>
    """

MagiDisplayDateTimeWithTimezones = _MagiDisplayDateTimeWithTimezones()

# Countdown

class _MagiDisplayCountdown(_MagiDisplayDateTimeMixin, MagiDisplay):
    """
    Value: a datetime in UTC
    """
    OPTIONAL_PARAMETERS = {
        'countdown_classes': [],
        'countdown_template': _('Starts in {time}'),
    }
    def to_display_value(self, value, parameters):
        return torfc2822(value)

    template = u"""
    <span class="countdown {countdown_classes}" data-date="{display_value}"
          data-format="{countdown_template}"></span>
    """
    template_countdown_classes_foreach = u'{value}'

MagiDisplayCountdown = _MagiDisplayCountdown()

############################################################
# iTunes

class _MagiDisplayITunes(MagiDisplay):
    """
    Value: iTunes id (int)
    """
    template = u'<div class="itunes" data-itunes-id="{display_value}"></div>'

MagiDisplayITunes = _MagiDisplayITunes()

############################################################
# Color

class _MagiDisplayColor(MagiDisplay):
    """
    Value: Hex code
    """
    OPTIONAL_PARAMETERS = {
        'color_text': None, # defaults to value = hex code
    }
    def to_parameters_extra(self, parameters):
        parameters.color_text = parameters.color_text or parameters.display_value

    template = u"""
    <span class="text-muted">{color_text}</span>
    <div class="color-viewer" style="background-color: {display_value};"></div>
    """

MagiDisplayColor = _MagiDisplayColor()

############################################################
# YouTube video

class _MagiDisplayYouTubeVideo(MagiDisplay):
    """
    Value: Embed URL https://www.youtube.com/embed/xxxxxxxxxxx
    """
    REQUIRED_PARAMETERS = [
        'url', # https://www.youtube.com/watch?v=xxxxxxxxxxx
    ]
    OPTIONAL_PARAMETERS = {
        'thumbnail': None,
    }

    template = u"""
    <a href="{url}" target="_blank" class="youtube-embed-container" {thumbnail}>
      <iframe src="{display_value}" frameborder="0" allowfullscreen></iframe>
    </a>
    """
    template_thumbnail = u'style="background: url({thumbnail}); background-size: cover;"'

MagiDisplayYouTubeVideo = _MagiDisplayYouTubeVideo()

############################################################
############################################################
############################################################

############################################################
# MagiDisplayMultiple
# Used by list, grid, gallery, etc

class _MagiDisplayMultiple(MagiDisplay):
    """
    Value:
       List [ _('Fly'), _('Dance'), ... ]
    OR Dict: OrderedDict({ 'fly': _('Fly'), ... })

    What's displayed within a list item depends on item_display_class.
    Default item_display_class is MagiDisplayText, so you can add optional parameters like so:
    def item_to_parameters(self, key, value):
        return {
            'text_image': '...',
        }
    """
    OPTIONAL_PARAMETERS = {
        'item_display_class': MagiDisplayText,
        'item_to_parameters': lambda _key, _value: {},
        'item_to_value': lambda _value, _parameters_per_item: _value,
    }
    WILL_USE_PARAMETERS_FROM = [
        'item_display_class',
    ]

    template = u'{display_value}'
    template_foreach = u'{value}'

    def to_foreach_value(self, parameters_per_item):
        html = parameters_per_item['item_display_class'].to_html(
            parameters_per_item['item'],
            parameters_per_item['item_to_value'](parameters_per_item['value'], parameters_per_item),
            **self.get_display_class_parameters(
                parameters_per_item,
                'item_display_class',
                to_callable_parameters=lambda _parameters: (parameters_per_item['key'], parameters_per_item['value']),
            )
        )
        return html

MagiDisplayMultiple = _MagiDisplayMultiple()

class _MagiDisplayDict(_MagiDisplayMultiple):
    """
    Value:
    - A dict: { 'What\'s your name?': 'Deby' }
    - A dict of dicts: { 'name_question': { 'verbose': _('What\'s your name?'), 'value': 'Deby' } }

    Similar to DisplayMultiple but also allows to provide a display_class for the key
    """
    OPTIONAL_PARAMETERS = mergeDicts(_MagiDisplayMultiple.OPTIONAL_PARAMETERS, {
        'item_key_display_class': MagiDisplayText,
        'item_key_to_parameters': lambda _key, _value: {},
        'item_key_to_value': lambda _key, _value, _parameters_per_item: (
            _value['verbose'] if isinstance(_value, dict) and 'verbose' in _value else _key
        ),
    })
    WILL_USE_PARAMETERS_FROM = _MagiDisplayMultiple.WILL_USE_PARAMETERS_FROM + [
        'item_key_display_class',
    ]

    def is_valid_display_value(self, parameters):
        return isinstance(parameters.original_value, dict)

    template = u'{display_value}'
    template_foreach = u'{display_dict_key}: {value}<br>'

    def to_foreach_parameters_extra(self, parameters_per_item):
        html = parameters_per_item['item_key_display_class'].to_html(
            parameters_per_item['item'],
            parameters_per_item['item_key_to_value'](
                parameters_per_item['key'],
                parameters_per_item['display_value'][parameters_per_item['key']],
                parameters_per_item,
            ),
            **self.get_display_class_parameters(
                parameters_per_item,
                'item_key_display_class',
                to_callable_parameters=lambda _parameters: (parameters_per_item['key'], parameters_per_item['value']),
            )
        )
        return { 'display_dict_key': html }

    def to_foreach_value(self, parameters_per_item):
        if isinstance(parameters_per_item['value'], dict) and 'value' in parameters_per_item['value']:
            parameters_per_item['value'] = parameters_per_item['value']['value']
        return super(_MagiDisplayDict, self).to_foreach_value(parameters_per_item)

MagiDisplayDict = _MagiDisplayDict()

############################################################
# Unordered list

class _MagiDisplayList(_MagiDisplayMultiple):
    """
    Value:
       List [ _('Fly'), _('Dance'), ... ]
    OR Dict: OrderedDict({ 'fly': _('Fly'), ... })
    """
    OPTIONAL_PARAMETERS = mergeDicts(_MagiDisplayMultiple.OPTIONAL_PARAMETERS, {
        'inline': False,
        'with_bullet': True,
    })

    template = u'<div class="list-wrapper {with_bullet}"><ul>{display_value}</ul></div>'
    template_with_bullet = u'with-bullet'
    template_foreach = u'<li {key} {inline}>{value}</li>'
    template_key = u'data-list-key="{key}"'
    template_inline = u'class="inline-block padding10 padding-novertical"'

MagiDisplayList = _MagiDisplayList()

############################################################
# Ordereded list

class _MagiDisplayOrderedList(_MagiDisplayList):
    """
    Value:
       List [ _('Fly'), _('Dance'), ... ]
    OR Dict: OrderedDict({ 'fly': _('Fly'), ... })
    """
    template = u'<div class="list-wrapper"><ol>{display_value}</ol></div>'

MagiDisplayOrderedList = _MagiDisplayOrderedList()

############################################################
# Description list

class _MagiDisplayDescriptionList(_MagiDisplayDict):
    """
    Value:
    - A dict: { 'What\'s your name?': 'Deby' }
    - A dict of dicts: { 'name_question': { 'verbose': _('What\'s your name?'), 'value': 'Deby' } }
    """
    OPTIONAL_PARAMETERS = mergeDicts(_MagiDisplayDict.OPTIONAL_PARAMETERS, {
        'inline': False,
    })
    template = u'<dl {inline}>{display_value}</dl>'
    template_inline = u'class="inline"'
    template_foreach = u'<dt data-key="{key}">{display_dict_key}</dt><dd>{value}</dd>'

MagiDisplayDescriptionList = _MagiDisplayDescriptionList()

############################################################
# Grid

class _MagiDisplayGrid(_MagiDisplayMultiple):
    OPTIONAL_PARAMETERS = mergeDicts(_MagiDisplayMultiple.OPTIONAL_PARAMETERS, {
        'col_break': 'sm',
        'per_line': 5,
        'align': 'right',
    })

    def to_parameters_extra(self, parameters):
        parameters.col_size = getColSize(parameters.per_line)

    template = u'<div class="row row-align-{align}">{display_value}</div>'
    template_foreach = u'<div class="col-{col_break}-{col_size} {offset}" {offset_margin} {key}>{value}</div>{close_row}'
    template_close_row = u'</div><div class="row row-align-{align}">'
    template_offset = u'col-{col_break}-offset-{offset}'
    template_offset_margin = u'style="margin-left: {offset_margin}%;"'
    template_key = u'data-grid-key="{key}"'

    def to_foreach_parameters_extra(self, parameters_per_item):
        with_class, offset_or_margin = getColOffset(
            align=parameters_per_item.align, per_line=parameters_per_item.per_line,
            total=len(parameters_per_item.display_value), i=parameters_per_item.i,
        )
        return {
            'close_row': (
                ( parameters_per_item.i + 1 ) != 0
                and ( parameters_per_item.i + 1 ) % parameters_per_item.per_line == 0
            ),
            'offset': offset_or_margin if with_class and offset_or_margin else ('special' if offset_or_margin else None),
            'offset_margin': offset_or_margin if not with_class and offset_or_margin else None,
        }

MagiDisplayGrid = _MagiDisplayGrid()

############################################################
# Gallery

class _MagiDisplayGallery(_MagiDisplayList):
    OPTIONAL_PARAMETERS = mergeDicts(_MagiDisplayList.OPTIONAL_PARAMETERS, {
        'inline': True,
        'with_bullet': False,
        'item_display_class': MagiDisplayImage,
    })

MagiDisplayGallery = _MagiDisplayGallery()

############################################################
# Table

class MagiDisplayTableTitle(object):
    def __init__(self, title):
        self.title = title

class _MagiDisplayTable(MagiDisplay):
    """
    Value: List of lists (rows, columns)
    """
    OPTIONAL_PARAMETERS = {
        'align': 'center',
        'column_display_class': MagiDisplayText,
        'column_to_parameters': lambda _row, _column, _value: {},
        'column_to_value': lambda _row, _column, _value: _value,
        'title_display_class': MagiDisplayText,
        'title_to_parameters': lambda _row, _column, _value: {},
        'title_to_value': lambda _row, _column, _value: _value,
    }
    WILL_USE_PARAMETERS_FROM = [
        'column_display_class',
        'title_display_class',
    ]

    template = u"""
    <div class="flex-table with-border table-rounded text-{align}">
      {display_value}
    </div>
    """
    template_foreach = u"""
    <div class="flex-tr">{value}</div>
    """
    _template_title_column = u"""
    <div class="flex-th flex-collapse-sm">{column_value}</div>
    """
    _template_column = u"""
    <div class="flex-td flex-collapse-sm">{column_value}</div>
    """

    def to_foreach_value(self, parameters_per_item):
        columns_html = []
        for j, column in enumerate(parameters_per_item['value']):
            if isinstance(column, MagiDisplayTableTitle):
                template = self._template_title_column
                value_html = parameters_per_item['title_display_class'].to_html(
                    parameters_per_item['item'],
                    parameters_per_item['title_to_value'](parameters_per_item['i'], j, column.title),
                    **self.get_display_class_parameters(
                        parameters_per_item,
                        'title_display_class',
                        to_callable_parameters=lambda _parameters: (
                            (parameters_per_item['i'], j, column.title)
                        ),
                ))
            elif not hasValue(column):
                template = self._template_column
                value_html = u''
            else:
                template = self._template_column
                value_html = parameters_per_item['column_display_class'].to_html(
                    parameters_per_item['item'],
                    parameters_per_item['column_to_value'](parameters_per_item['i'], j, column),
                    **self.get_display_class_parameters(
                        parameters_per_item,
                        'column_display_class',
                        to_callable_parameters=lambda _parameters: (
                            (parameters_per_item['i'], j, column)
                        ),
                ))
            html = markSafeFormat(
                template,
                column_value=value_html,
            )
            columns_html.append(html)
        return markSafeJoin(columns_html)

MagiDisplayTable = _MagiDisplayTable()

############################################################
# Textarea

class _MagiDisplayTextarea(MagiDisplay):
    """
    Value: string
    """
    OPTIONAL_PARAMETERS = {
        'height': 300,
    }
    template = u'<textarea style="width: 100%; height: {height}px;">{display_value}</textarea>'

MagiDisplayTextarea = _MagiDisplayTextarea()

############################################################
# Alert

class _MagiDisplayAlert(MagiDisplay):
    OPTIONAL_PARAMETERS = {
        'alert_type': 'info', # success, info, warning, danger
        'alert_icon': 'about',
        'alert_title': None,
        'alert_message': None, # defaults to display_value
        'alert_button': None, # Can be a dict with url, verbose, icon
    }
    template = ALERT_TEMPLATE
    template_alert_title = u'<h4><b>{alert_title}</b></h4>'
    template_alert_message = u'<p>{alert_message}</p>'
    template_alert_button = ALERT_BUTTON_TEMPLATE

    def to_parameters_extra(self, parameters):
        parameters.alert_col_size = 7 if parameters.alert_button else 10
        parameters.alert_message = parameters.alert_message or parameters.display_value
        if parameters.alert_button:
            if 'icon' not in parameters.alert_button:
                parameters.alert_button['icon'] = 'link'

MagiDisplayAlert = _MagiDisplayAlert()

############################################################
############################################################
############################################################

############################################################
# Mini buttons (below fields)

class _MagiDisplayButtons(_MagiDisplayMultiple):
    OPTIONAL_PARAMETERS = mergeDicts(_MagiDisplayMultiple.OPTIONAL_PARAMETERS, {
        'item_display_class': MagiDisplayButton,
    })

MagiDisplayButtons = _MagiDisplayButtons()
