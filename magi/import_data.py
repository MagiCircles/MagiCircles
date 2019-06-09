from __future__ import print_function
import requests, json
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from magi.utils import (
    modelHasField,
    matchesTemplate,
    addParametersToURL,
)

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

def prepare_data(data, model, unique):
    manytomany = {}
    dictionaries = {}
    for k, v in data.items():
        if k.startswith('d_') and isinstance(v, dict):
            if unique:
                data[k] = json.dumps(v)
            else:
                dictionaries[k] = v
        elif (k.startswith('i_')
            and not getattr(model, u'{}_WITHOUT_I_CHOICES'.format(k[2:].upper()), False)
            and not isinstance(v, int)):
            data[k] = model.get_i(k[2:], v)
        elif (k.startswith('j_')):
            data[k] = json.dumps(v)
        elif not unique and isinstance(v, list):
            manytomany[k] = v
    for k in manytomany.keys():
        del(data[k])
    for k in dictionaries.keys():
        del(data[k])
    if unique:
        return data
    return data, manytomany, dictionaries

def save_item(model, unique_data, data, log_function, unique_together=False):
    if (data or unique_data):
        unique_data = prepare_data(unique_data, model, unique=True)
        data, manytomany, dictionaries = prepare_data(data, model, unique=False)
        log_function(model.__name__)
        log_function('- Unique data:')
        log_function(unique_data)
        log_function('- Data:')
        log_function(data)
        data.update(unique_data)
        try:
            item = model.objects.get(reduce(
                ((lambda qs, (k, v): qs & Q(**{k: v}))
                 if unique_together else (lambda qs, (k, v): qs | Q(**{k: v}))), [
                    (k, v) for k, v in unique_data.items() if v is not None
                ], Q()
            ))
            model.objects.filter(pk=item.pk).update(**data)
            item = model.objects.filter(pk=item.pk)[0]
            log_function('Updated')
        except ObjectDoesNotExist:
            if modelHasField(model, 'owner') and 'owner' not in data and 'owner_id' not in data:
                data['owner_id'] = 1
            item = model.objects.create(**data)
            log_function('Created')
        if manytomany:
            log_function('- Many to many:')
            for field_name, list_of_items in manytomany.items():
                getattr(item, field_name).add(*list_of_items)
                log_function('    ', field_name)
            item.save()
        if dictionaries:
            log_function('- Updated dictionaries:')
            for field_name, dictionary in dictionaries.items():
                for k, v in dictionary.items():
                    item.add_d(field_name[2:], k, v)
                log_function('    ', field_name, getattr(item, field_name[2:]))
            item.save()
        return item
    return None

def api_pages(url, name, details, local=False, results_location=None, log_function=print):
    log_function('Downloading list of {}...'.format(name))
    details.get('callback_before', lambda: None)()
    url = addParametersToURL(
        u'{}{}/'.format(
            details.get('url', url),
            details.get('endpoint', name),
        ),
        details.get('url_parameters', {}),
    )
    log_function(url)
    total = 0
    while url:
        if local:
            f = open('{}.json'.format(name), 'r')
            result = json.loads(f.read())
            f.close()
        else:
            r = requests.get(url)
            f = open('{}.json'.format(name), 'w')
            f.write(r.text.encode('utf-8'))
            f.close()
            result = r.json()
        results = result
        if 'results_location' in details:
            results = getSubField(results, details['results_location'], default=[])
        elif results_location is not None:
            results = getSubField(results, results_location, default=[])
        for item in results:
            not_in_fields = {}
            if details.get('callback_per_item', False):
                unique_data, data = details['callback_per_item'](details, item)
            else:
                unique_data, data, not_in_fields = import_generic_item(details, item)
            save_item(details['model'], unique_data, data, log_function, unique_together=details.get(
                'unique_together', False))
            if not_in_fields:
                log_function('- Ignored:')
                log_function(not_in_fields)
            total += 1
        if local:
            url = None
        else:
            url = result['next']
    details.get('callback_end', lambda: None)()
    log_function('Total {}'.format(total))
    log_function('Done.')

def download_image(url):
    return url
    # to do download and return image

def import_data(
        url, import_configuration, results_location=None,
        local=False, to_import=None, log_function=print,
):
    """
    url: must end with a /. Example: https://schoolido.lu/api/. can be overriden per conf
    import_configuration: dict with details on how to import (see below)
    local: when True, will only read local file {key}.json
    to_import: list of keys to take into account in import_configuration
    results_location: in case the results are not at the root of the JSON response
    log_function: where to log

    import_configuration must be a dictionary with:
    - key: name of the items
    - value: dictionary with:
        model (MagiModel): required
        url (string): defaults to url global setting
        url_parameters (dict): defaults to {}
        results_location (list): defaults to results_location global setting
        endpoint (string): defaults to key in dict
        callback (function(details, item, unique_data, data)): called at the end of generic importing
        callback_per_item (function): called instead of generic importing
        callback_before (function): called before importing all the items
        callback_end (function): called after importing all the items
        mapping (dict of string or callable): see below
        unique_fields (list): list of fields to detect if it already exists
        unique_together (bool): should the unique fields be considered together? (or/and condition)
        ignore_fields (list): list of explicitely ignored fields, no warning printed

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
            )
