from __future__ import print_function
import requests, json, os.path
from django.conf import settings as django_settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, ImageField, Model
from django.db import connections
from magi.utils import (
    addParametersToURL,
    AttrDict,
    failSafe,
    getSubField,
    getIndex,
    hasValue,
    join_data,
    modelHasField,
    matchesTemplate,
    saveImageURLToModel,
)
from magi.models import StaffConfiguration, MagiModel
from magi.tools import get_default_owner

############################################################
# Twitter API

TWITTER_TOKEN_URL = 'https://api.twitter.com/oauth2/token'

def getTwitterBearerToken(log_function=print, verbose=False, force_reload=False):
    token = None

    if not force_reload:
        try:
            token = StaffConfiguration.objects.filter(key='_twitter_bearer_token')[0].value
            if verbose:
                log_function('Twitter: Using existing token')
        except IndexError:
            pass

    if not token:
        api_key = getattr(django_settings, 'TWITTER_API_KEY', None)
        api_secret = getattr(django_settings, 'TWITTER_API_SECRET', None)
        if not api_key or not api_secret:
            log_function('Twitter: Missing API key or secret')
            return None
        result = loadJsonAPIPage(TWITTER_TOKEN_URL, post=True, request_options={
            'auth': (api_key, api_secret),
            'data': { 'grant_type': 'client_credentials' },
        }, verbose=True)
        if result.get('errors', []):
            log_function(result['errors'])
            return None
        token = result['access_token']
        StaffConfiguration.objects.filter(key='_twitter_bearer_token').delete()
        StaffConfiguration.objects.create(
            key='_twitter_bearer_token',
            owner=get_default_owner(),
            verbose_key='Twitter bearer token',
            value=token,
        )
        if verbose:
            log_function('Twitter: Creating new token')

    return token

TWITTER_API_SEARCH_URL = 'https://api.twitter.com/1.1/tweets/search/fullarchive/{env}.json'

def twitterAPICall(url, data, load_json_api_options={}, verbose=False, log_function=print):
    token = getTwitterBearerToken()
    if not token:
        log_function('Twitter: Missing TWITTER_API_KEY and TWITTER_API_SECRET in settings.')
        return None

    request_options = {
        'headers': {
            'authorization': u'Bearer {}'.format(token),
            'content-type': 'application/json',
        },
    }
    request_options['data'] = json.dumps(data)

    new_load_json_api_options = {
        'url': url.format(env=getattr(django_settings, 'TWITTER_API_ENV', 'env')),
        'post': True,
        'request_options': request_options,
        'verbose': verbose,
        'log_function': log_function,
    }
    new_load_json_api_options.update(load_json_api_options)

    result = loadJsonAPIPage(**new_load_json_api_options)
    errors = result.get('errors', [])

    # Retry when invalid token
    if errors and len(errors) == 1 and errors[0]['code'] == 89: # "Invalid or expired token"
        if verbose:
            log_function('Twitter: Bearer token was invalid, retrieving a new one')
        token = getTwitterBearerToken(force_reload=True)
        if not token:
            log_function('Twitter: Couldn\'t retrieve Bearer token. Check TWITTER_API_KEY and TWITTER_API_SECRET')
            return None
        result = loadJsonAPIPage(**new_load_json_api_options)
        errors = result.get('errors', [])

    if errors:
        log_function('Twitter: Error(s) ' + errors)
        return None

    return result

############################################################
# From Google Spreadsheet

def import_from_sheet(spreadsheet_id, import_configuration, local=False, to_import=None, verbose=False, force_reload_images=False):
    """
    When used, the following needs to be added to your requirements.txt:
    google-api-python-client==1.8.3
    google-auth-httplib2==0.0.3
    google-auth-oauthlib==0.4.1

    The key in import configuration must match the name of the sheet tab (or provide "sheet_name").
    Must create credentials in google_sheets_credentials.json
    by going to https://developers.google.com/workspace/guides/create-credentials
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    sheet = _login_to_google_sheets(InstalledAppFlow)

    def request_call(url, *args, **kwargs):
        name = url.split('?')[0]
        sheet_name = import_configuration[name].get('sheet_name', name)
        result = sheet.get(
            includeGridData=True,
            spreadsheetId=spreadsheet_id,
            ranges=sheet_name,
            fields='sheets/data/rowData/values/userEnteredValue',
        ).execute()
        result = result['sheets'][0]['data'][0]['rowData']
        keys = [ col['userEnteredValue']['stringValue'] for col in result[0]['values'] ]
        def _col_to_value(row):
            if 'userEnteredValue' in row:
                image = row['userEnteredValue'].get('formulaValue', None)
                if image:
                    return image.replace('=IMAGE("', '').replace('")', '')
                return row['userEnteredValue'].get(
                    'stringValue', row['userEnteredValue'].get(
                        'numberValue', None
                    ))
        result = [
            {
                key: _col_to_value(getIndex(row.get('values', []), index, []))
                for index, key in enumerate(keys)
            } for row in result[1:]
        ]
        return AttrDict({
            'status_code': 200,
            'json': lambda: result,
            'text': json.dumps(result),
        })

    return import_data(
        '', import_configuration,
        local=local, to_import=to_import,
        verbose=verbose,
        force_reload_images=False,
        request_call=request_call,
    )

def _login_to_google_sheets(InstalledAppFlow):
    import pickle
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'google_sheets_credentials.json', [
                    'https://www.googleapis.com/auth/spreadsheets.readonly',
                ])
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    return sheet

############################################################
# Utils

def loadJsonAPIPage(url, parameters=None, local=False, local_file_name='tmp', request_options={}, page_number=0, log_function=print, load_on_not_found_local=False, verbose=False, post=False, request_call=None):
    if local:
        if load_on_not_found_local:
            try: f = open('{}.json'.format(local_file_name), 'r')
            except IOError: f = None
        else:
            f = open('{}.json'.format(local_file_name), 'r')
        if f:
            if verbose:
                log_function('Loading from local file ' + local_file_name + '.json')
            result = json.loads(f.read())
            f.close()
            return result
    if verbose:
        log_function('Loading ' + url)
    r = (request_call or (requests.post if post else requests.get))(
        addParametersToURL(url, parameters or {}), **request_options)
    if r.status_code != 200:
        log_function('ERROR: unable to load {}'.format(url))
        log_function(r.status_code)
        log_function(r.text)
        log_function('')
        return None
    if page_number == 0:
        f = open('{}.json'.format(local_file_name), 'w')
        f.write(r.text.encode('utf-8'))
        f.close()
    return r.json()

def loadLocalJson(path, log_function=print):
    """
    JSON from local files
    path = without base dir, doesn't start with a /
    """
    try:
        f = open(path, 'r')
    except IOError:
        log_function('File not found: {}'.format(path))
        return None
    result = json.loads(f.read())
    f.close()
    return result

############################################################
# Import data utils

def import_map(maps, field_name, value, verbose=False, log_function=print):
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
            # Or, for foreign keys, a tuple with (field_name, Model class, unique data dict, defaults dict)
            elif (isinstance(result, tuple)
                  and failSafe(lambda: issubclass(result[1], MagiModel), exceptions=[TypeError], default=False)):
                field_name = result[0]
                parameters = getIndex(result, 2, { 'pk': value }).copy()
                parameters['defaults'] = getIndex(result, 3, {}).copy()
                if (modelHasField(result[1], 'owner')
                    and 'owner' not in parameters['defaults']
                    and 'owner_id' not in parameters['defaults']):
                    parameters['defaults']['owner'] = get_default_owner()
                value, created = result[1].objects.get_or_create(**parameters)
                if created and verbose:
                    log_function('   Created foreign key', result[0], parameters)
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

def import_generic_item(details, item, verbose=False, log_function=print):
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
            fields = import_map(details['mapping'][field_name], field_name, value, verbose=verbose, log_function=log_function)

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
        if modelHasField(model, k) and isinstance(model._meta.get_field(k), ImageField):
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

def _is_item_when_unique_together(item, unique_data):
    for key, value in unique_data.items():
        if value and isinstance(value, Model):
            if getattr(item, u'{}_id'.format(key), None) != value.id:
                return False
        else:
            if getattr(item, key, None) != value:
                return False
    return True

def _is_item_when_any_unique(item, unique_data):
    for key, value in unique_data.items():
        if value and isinstance(value, Model):
            if getattr(item, u'{}_id'.format(key), None) == value.id:
                return True
        else:
            if getattr(item, key, None) == value:
                return True
    return False

def default_find_existing_item(model, unique_together, unique_data, all_items):
    if all_items:
        for item in all_items:
            if unique_together:
                if _is_item_when_unique_together(item, unique_data):
                    return item
            else:
                if _is_item_when_any_unique(item, unique_data):
                    return item
        return None
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
        details, unique_data, data, log_function=print, json_item=None, update=True,
        verbose=False, download_images=False, force_reload_images=False, all_items=None):
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
            item = default_find_existing_item(model, unique_together, unique_data, all_items)

        if item:
            if not update:
                changed = False
                for k, v in data.items():
                    if v and isinstance(v, Model):
                        if v and not getattr(item, u'{}_id'.format(k), None):
                            setattr(item, k, v)
                            changed = True
                    else:
                        if hasValue(v) and not hasValue(getattr(item, k, None)):
                            setattr(item, k, v)
                            changed = True
                if changed:
                    item.save()
                    if verbose:
                        log_function(u'Updated {} #{}'.format(model.__name__, item.pk))
                elif verbose:
                    log_function(u'Nothing to change {} #{}'.format(model.__name__, item.pk))
            else:
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
        if dictionaries:
            changed = False
            for field_name, dictionary in dictionaries.items():
                previous = getattr(item, field_name[2:])
                for k, v in dictionary.items():
                    if hasValue(previous.get(k, None)) and not update:
                        continue
                    item.add_d(field_name[2:], k, v)
                if previous != getattr(item, field_name[2:]):
                    changed = True
                    if verbose:
                        log_function('- Updated dictionary:')
                        log_function('    ', field_name, getattr(item, field_name[2:]))
            if changed:
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
        request_call=None,
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
    if verbose:
        log_function(url)
    total = 0
    page_number = 0
    request_options = request_options.copy()
    request_options.update(details.get('request_options', {}))
    while url:
        result = loadJsonAPIPage(
            url, local=local, load_on_not_found_local=local, verbose=verbose,
            local_file_name=name, request_options=request_options,
            page_number=page_number, log_function=log_function,
            request_call=request_call,
        )
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
                unique_data, data, not_in_fields = import_generic_item(details, item, verbose=verbose, log_function=log_function)
            save_item(
                details, unique_data, data, log_function, json_item=item,
                verbose=verbose, download_images=download_images,
                force_reload_images=force_reload_images,
            )
            if not_in_fields and verbose:
                log_function('- Ignored:')
                log_function(not_in_fields)
            total += 1
        page_number += 1
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

def import_from_json(
        folder, name, details,
        log_function=print,
        verbose=False, download_images=False,
        force_reload_images=False,
        results_location=None,
):
    log_function('Downloading list of {}...'.format(name))
    details.get('callback_before', lambda: None)()
    path = folder + details.get('filename', name) + '.json'
    if verbose:
        log_function(path)
    total = 0
    result = loadLocalJson(path, log_function=log_function)
    if 'callback_before_page' in details:
        result = details['callback_before_page'](result)
    results = result
    if 'results_location' in details:
        results = getSubField(results, details['results_location'], default=[])
    elif results_location is not None:
        results = getSubField(results, results_location, default=[])
    for item in (results.values() if isinstance(results, dict) else results):
        not_in_fields = {}
        if (details.get('callback_should_import', None)
            and not details['callback_should_import'](details, item)):
            continue
        if details.get('callback_per_item', False):
            unique_data, data = details['callback_per_item'](details, item)
        else:
            unique_data, data, not_in_fields = import_generic_item(
                details, item, verbose=verbose, log_function=log_function)
        save_item(
            details, unique_data, data, log_function, json_item=item,
            verbose=verbose, download_images=download_images,
            force_reload_images=force_reload_images,
        )
        if not_in_fields and verbose:
            log_function('- Ignored:')
            log_function(not_in_fields)
        total += 1
    details.get('callback_end', lambda: None)()
    log_function('Total {}'.format(total))
    log_function('Done.')


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def import_from_sqlite(
        db_name, name, details,
        log_function=print,
        verbose=False, download_images=False,
        force_reload_images=False,
        results_location=None, update=True,
):
    log_function('Downloading list of {}...'.format(name))
    details.get('callback_before', lambda: None)()
    total = 0

    if details.get('queryset', None):
        all_items = list(details['queryset'])
    else:
        all_items = list(details['model'].objects.all())

    with connections[db_name].cursor() as cursor:

        table_name = details.get('table', name)

        if 'callback_before_page' in details:
            result = details['callback_before_page'](result)

        query = 'SELECT * FROM {}'.format(table_name)
        if verbose:
            log_function(query)
        cursor.execute(query)
        for item in dictfetchall(cursor):
            not_in_fields = {}
            if (details.get('callback_should_import', None)
                and not details['callback_should_import'](details, item)):
                continue
            if details.get('callback_per_item', False):
                unique_data, data = details['callback_per_item'](details, item)
            else:
                unique_data, data, not_in_fields = import_generic_item(
                    details, item, verbose=verbose, log_function=log_function)
            save_item(
                details, unique_data, data, log_function, json_item=item,
                verbose=verbose, download_images=download_images,
                force_reload_images=force_reload_images, update=update,
                all_items=all_items,
            )
            if not_in_fields and verbose:
                log_function('- Ignored:')
                log_function(not_in_fields)
            total += 1
        details.get('callback_end', lambda: None)()

    log_function('Total {}'.format(total))
    log_function('Done.')

############################################################
# Import data

def import_data(
        url, import_configuration, results_location=None,
        local=False, to_import=None, log_function=print,
        request_options={}, verbose=False, download_images=False,
        force_reload_images=False,
        request_call=None,
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
                request_call=request_call,
            )

def import_data_from_local_json(
        import_configuration, folder='',
        to_import=None, log_function=print,
        verbose=False, download_images=False,
        force_reload_images=False,
        results_location=None,
):
    """
    Assumes name in import is the name of the file .json (can specify filename in import config)
    Folder = including BASE_DIR if needed
    path + name + .json
    """
    for name, details in import_configuration.items():
        if to_import is None or name in to_import:
            import_from_json(
                folder, name, details,
                results_location=results_location,
                log_function=log_function,
                verbose=verbose, download_images=download_images,
                force_reload_images=force_reload_images,
            )

def import_data_from_local_sqlite(
        db_name, import_configuration,
        to_import=None, log_function=print,
        verbose=False, download_images=False,
        force_reload_images=False,
        results_location=None, update=True,
):
    """
    db_name = db key in your ${PROJECT}_project/import_settings.py
    Assumes name in import is the name of the table (can specify table in import config)
    """
    for name, details in import_configuration.items():
        if to_import is None or name in to_import:
            import_from_sqlite(
                db_name, name, details,
                results_location=results_location,
                log_function=log_function,
                verbose=verbose, download_images=download_images,
                force_reload_images=force_reload_images, update=update,
            )
