from __future__ import print_function
import requests, json
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, ImageField
from magi.utils import (
    addParametersToURL,
    getSubField,
    join_data,
    modelHasField,
    matchesTemplate,
    saveImageURLToModel,
)
from magi.tools import get_default_owner

def import_map(maps, field_name, value):
    if not isinstance(maps, list):
        maps = [maps]
    fields = None
    for mapped in maps:
        # Dict of values -> new values
        if isinstance(mapped, dict):
            value = mapped.get(value, value)
        # Function to get value
        elif callable(mapped):
            result = mapped(value)
            # Function can return multiple fields in a dict
            if isinstance(result, dict):
                fields = result
            # Or return a new field_name and a value
            else:
                field_name, value = result
        # If the new field name is a dict, add to the dict
        elif mapped.startswith('d_'):
            value = { field_name: value }
            field_name = mapped
        # Or map can just change the field_name
        else:
            field_name = mapped
    return fields if fields is not None else { field_name: value }

def import_generic_item(details, item):
    data = {}
    unique_data = {}
    all_fields = details.get('fields', []) + details.get('unique_fields', [])
    ignored_fields = details.get('ignored_fields', [])
    not_in_fields = {}
    for field_name, value in item.items():

        if field_name in ignored_fields:
            continue

        fields = { field_name: value }

        # Map
        if field_name in details.get('mapping', {}):
            fields = import_map(details['mapping'][field_name], field_name, value)

        elif field_name not in all_fields:
            not_in_fields[field_name] = value
            continue

        for field_name, value in fields.items():
            # Get i_choices if field name is i_
            if field_name.startswith('i_'):
                for i, choice in details['model'].get_choices(field_name):
                    choice = choice[0] if isinstance(choice, tuple) else choice
                    if value == choice:
                        value = i
                        break
            # Push to unique fields or normal fields
            if field_name in details.get('unique_fields', ['id']):
                # Update existing dictionaries
                if (field_name.startswith('d_')
                    and isinstance(value, dict)
                    and field_name in data):
                    unique_data[field_name].update(value)
                else:
                    unique_data[field_name] = value
            else:
                # Update existing dictionaries
                if (field_name.startswith('d_')
                    and isinstance(value, dict)
                    and field_name in data):
                    data[field_name].update(value)
                else:
                    data[field_name] = value

    if 'callback' in details:
        details['callback'](details, item, unique_data, data)
    return unique_data, data, not_in_fields

def prepare_data(data, model, unique, download_images):
    manytomany = {}
    dictionaries = {}
    images = {}
    for k, v in data.items():
        if isinstance(model._meta.get_field(k), ImageField):
            if download_images:
                images[k] = v
        elif k.startswith('d_') and isinstance(v, dict):
            if unique:
                data[k] = json.dumps(v)
            else:
                dictionaries[k] = v
        elif (k.startswith('i_')
            and not getattr(model, u'{}_WITHOUT_I_CHOICES'.format(k[2:].upper()), False)
            and not isinstance(v, int)):
            data[k] = model.get_i(k[2:], v)
        elif (k.startswith('c_')
              and isinstance(v, list)):
            data[k] = join_data(*v)
        elif (k.startswith('j_')):
            data[k] = json.dumps(v)
        elif not unique and isinstance(v, list):
            manytomany[k] = v
    for k in manytomany.keys():
        del(data[k])
    for k in dictionaries.keys():
        del(data[k])
    for k in images.keys():
        del(data[k])
    if unique:
        return data
    return data, manytomany, dictionaries, images

def default_find_existing_item(model, unique_together, unique_data):
    try:
        return model.objects.filter(reduce(
            ((lambda qs, (k, v): qs & Q(**{k: v}))
             if unique_together else (lambda qs, (k, v): qs | Q(**{k: v}))), [
                     (k, v) for k, v in unique_data.items() if v is not None
             ], Q()
        ))[0]
    except IndexError:
        return None

def save_item(
        details, unique_data, data, log_function=print, json_item=None,
        verbose=False, download_images=False, force_reload_images=False):
    model = details['model']
    unique_together = details.get('unique_together', False)
    download_images = details.get('download_images', download_images)
    find_existing_item = details.get('find_existing_item', None)
    dont_erase_existing_value_fields = details.get('dont_erase_existing_value_fields', [])
    if (data or unique_data):
        unique_data = prepare_data(unique_data, model, unique=True, download_images=download_images)
        data, manytomany, dictionaries, images = prepare_data(
            data, model, unique=False, download_images=download_images,
        )
        if verbose:
            log_function(model.__name__)
            log_function('- Unique data:')
            log_function(unique_data)
            log_function('- Data:')
            log_function(data)
        data.update(unique_data)

        if find_existing_item:
            item = find_existing_item(model, unique_data, data, manytomany, dictionaries)
        else:
            item = default_find_existing_item(model, unique_together, unique_data)

        if item:
            data = {
                k: v for k, v in data.items()
                if v or k not in dont_erase_existing_value_fields
            }
            model.objects.filter(pk=item.pk).update(**data)
            item = model.objects.filter(pk=item.pk)[0]
            if verbose:
                log_function(u'Updated {} #{}'.format(model.__name__, item.pk))
        else:
            if modelHasField(model, 'owner') and 'owner' not in data and 'owner_id' not in data:
                data['owner'] = get_default_owner()
            item = model.objects.create(**data)
            log_function(u'Created {} #{}'.format(model.__name__, item.pk))

        if manytomany:
            if verbose:
                log_function('- Many to many:')
            for field_name, list_of_items in manytomany.items():
                getattr(item, field_name).add(*list_of_items)
                if verbose:
                    log_function('    ', field_name)
            item.save()
        if dictionaries:
            if verbose:
                log_function('- Updated dictionaries:')
            for field_name, dictionary in dictionaries.items():
                for k, v in dictionary.items():
                    item.add_d(field_name[2:], k, v)
                if verbose:
                    log_function('    ', field_name, getattr(item, field_name[2:]))
            item.save()
        if images:
            saved_images = []
            for field_name, url in images.items():
                if not getattr(item, field_name, None) or force_reload_images:
                    image = saveImageURLToModel(item, field_name, url)
                    saved_images.append(field_name)
            if saved_images:
                if not verbose:
                    log_function(u'{} #{}'.format(model.__name__, item.pk))
                log_function(u'- Uploaded images: {}'.format(', '.join(saved_images)))
                item.save()

        if 'callback_after_save' in details:
            details['callback_after_save'](details, item, json_item)

        return item
    return None

def api_pages(
        url, name, details, local=False, results_location=None,
        log_function=print, request_options={},
        verbose=False, download_images=False,
        force_reload_images=False,
):
    log_function('Downloading list of {}...'.format(name))
    details.get('callback_before', lambda: None)()
    url = addParametersToURL(
        u'{}{}'.format(
            details.get('url', url),
            details.get('endpoint', name),
        ),
        details.get('url_parameters', {}),
    )
    total = 0
    request_options = request_options.copy()
    request_options.update(details.get('request_options', {}))
    while url:
        if local:
            f = open('{}.json'.format(name), 'r')
            result = json.loads(f.read())
            f.close()
        else:
            r = requests.get(url, **request_options)
            if r.status_code != 200:
                log_function('ERROR: unable to load {}'.format(url))
                log_function(r.status_code)
                log_function(r.text)
                log_function('')
                return
            if total == 0:
                f = open('{}.json'.format(name), 'w')
                f.write(r.text.encode('utf-8'))
                f.close()
            result = r.json()
        if 'callback_before_page' in details:
            result = details['callback_before_page'](result)
        results = result
        if 'results_location' in details:
            results = getSubField(results, details['results_location'], default=[])
        elif results_location is not None:
            results = getSubField(results, results_location, default=[])
        for item in results:
            not_in_fields = {}
            if (details.get('callback_should_import', None)
                and not details['callback_should_import'](details, item)):
                continue
            if details.get('callback_per_item', False):
                unique_data, data = details['callback_per_item'](details, item)
            else:
                unique_data, data, not_in_fields = import_generic_item(details, item)
            save_item(
                details, unique_data, data, log_function, json_item=item,
                verbose=verbose, download_images=download_images,
                force_reload_images=force_reload_images,
            )
            if not_in_fields and verbose:
                log_function('- Ignored:')
                log_function(not_in_fields)
            total += 1
        if local:
            url = None
        else:
            if 'next' in result:
                url = result['next']
            else:
                url = None
    details.get('callback_end', lambda: None)()
    log_function('Total {}'.format(total))
    log_function('Done.')

def import_data(
        url, import_configuration, results_location=None,
        local=False, to_import=None, log_function=print,
        request_options={}, verbose=False, download_images=False,
        force_reload_images=False,
):
    """
    url: must end with a /. Example: https://schoolido.lu/api/. can be overriden per conf
    import_configuration: dict with details on how to import (see below)
    local: when True, will only read local file {key}.json
    to_import: list of keys to take into account in import_configuration
    results_location: in case the results are not at the root of the JSON response
    log_function: where to log
    request_options: dict of options passed to requests in python
    download_images: will download the image instead of just inserting the URL in the database

    import_configuration must be a dictionary with:
    - key: name of the items
    - value: dictionary with:
        model (MagiModel): required
        url (string): defaults to url global setting
        url_parameters (dict): defaults to {}
        results_location (list): defaults to results_location global setting
        download_images: will download the image instead of just inserting the URL in the database
        endpoint (string): defaults to key in dict
        callback (function(details, item, unique_data, data)): called at the end of generic importing
        callback_per_item (function): called instead of generic importing
        callback_should_import (function): called to check if the item should be imported or skipped
        callback_after_save (function(details, item, json_item)): called after each item has been saved
        callback_before (function): called before importing all the items
        callback_before_page (function): called before importing all the items of a page
        callback_end (function): called after importing all the items
        mapping (dict of string or callable): see below
        dont_erase_existing_value_fields (list): On update, if the value is None, it will not erase existing value
        unique_fields (list): list of fields to detect if it already exists
        unique_together (bool): should the unique fields be considered together? (or/and condition)
        ignored_fields (list): list of explicitely ignored fields, no warning printed
        find_existing_item (function(model, unique_data, data): retrieve the item to update, or None to create
        request_options: dict of options passed to requests in python

    mapping must be a dictionary with:
    key: field name in the result object
    value can be:
        - a string corresponding to the new name of the value
        - a lambda that takes the value and returns a tuple with the new name of the field and the value
        - a lambda that takes the value and returns a dict of multiple new fields
        - a dict of value -> new value
    Multiple maps can be chained. Just specify a list of above possible values.
    Note: To add a field as a dictionary key, you can use:
        ["field_key_name", "dictionary_name"]
        ex: 'english_t1_points': ['t1_points', 'd_ww_tiers']
    """
    for name, details in import_configuration.items():
        if to_import is None or name in to_import:
            api_pages(
                url, name, details, local=local,
                results_location=results_location,
                log_function=log_function,
                request_options=request_options,
                verbose=verbose, download_images=download_images,
                force_reload_images=force_reload_images,
            )
