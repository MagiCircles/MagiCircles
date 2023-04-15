from collections import OrderedDict
from django.utils.translation import get_language
from magi.default_settings import RAW_CONTEXT
from magi.utils import (
    couldSpeakEnglish,
    getEventStatus,
    listUnique,
    tourldash,
    LANGUAGES_DICT,
    getAccountVersionsFromSession,
)

############################################################
# Pick relevant version automatically

def getFirstVersion(item=None, versions=None):
    versions = versions or (item.VERSIONS if item else {})
    return versions.keys()[0]

def getRelevantVersion(
        request=None,
        exclude_versions=[],
        # Either:
        item=None,
        # Or:
        versions=None, versions_statuses=None,
        # Customize what's checked
        check_filtered_choice=True,
        check_status=True,
        check_accounts=True,
        check_language=True,
        fallback_to_first=True,
):
    """
    See getBaseEventWithVersions in magi/abstract_models.py
    for details of versions dict.
    """
    versions = versions or (item.VERSIONS if item else {})
    i_version_string_to_version = {
        unicode(i): version_name
        for i, version_name in enumerate(versions.keys())
    }
    if exclude_versions:
        versions = OrderedDict([
            (version_name, version)
            for version_name, version in versions.items()
            if version_name not in exclude_versions
        ])

    if not versions:
        return None

    if not request and item:
        request = getattr(item, 'request', None)

    # Filtered choice
    if check_filtered_choice and request:
        version_name = request.GET.get('version', None)
        if version_name in versions:
            return version_name
        version_name = i_version_string_to_version.get(request.GET.get('i_version', None), None)
        if version_name in versions:
            return version_name
        c_versions = request.GET.get('c_versions', '')
        if not isinstance(c_versions, list):
            c_versions = c_versions.split(',')
        for version_name in c_versions:
            if version_name in versions:
                return version_name

    # Based on status
    if check_status and (versions_statuses or item):
        for status in ['current']:
            for version_name, version in versions.items():
                if versions_statuses:
                    if versions_statuses.get(version_name, None) == status:
                        return version_name
                elif item:
                    if ((getattr(item, u'{}status'.format(version['prefix']), None) == status)
                        or (hasattr(item, 'get_status')
                            and item.get_status(version_name) == status)
                        or (status == 'current'
                            and hasattr(item, u'{}start_date'.format(version['prefix']))
                            and hasattr(item, u'{}end_date'.format(version['prefix']))
                            and getEventStatus(
                                getattr(item, u'{}start_date'.format(version['prefix'])),
                                getattr(item, u'{}end_date'.format(version['prefix'])),
                            ) == status)):
                        return version_name

    # Based on status with more tolerance
    if check_status and (versions_statuses or item):
        for status in ['current', 'starts_soon', 'ended_recently']:
            for version_name, version in versions.items():
                if versions_statuses:
                    if versions_statuses.get(version_name, None) == status:
                        return version_name
                elif item:
                    if ((getattr(item, u'{}status'.format(version['prefix']), None) == status)
                        or (hasattr(item, 'get_status')
                            and item.get_status(version_name) == status)
                        or (status == 'current'
                            and hasattr(item, u'{}start_date'.format(version['prefix']))
                            and hasattr(item, u'{}end_date'.format(version['prefix']))
                            and getEventStatus(
                                getattr(item, u'{}start_date'.format(version['prefix'])),
                                getattr(item, u'{}end_date'.format(version['prefix'])),
                            ) == status)):
                        return version_name

    # Based on account versions
    if check_accounts and request:
        account_versions = getAccountVersionsFromSession(request)
        for version_name in account_versions:
            if version_name in versions:
                return version_name

    # User language
    if check_language:
        language = request.LANGUAGE_CODE if request else get_language()
        for version_name, version in versions.items():
            for version_language in getLanguagesForVersion(version):
                if language == version_language:
                    return version_name

    # Fallback to first
    if fallback_to_first:
        return getFirstVersion(versions=versions)

    return None

def getFieldForRelevantVersion(item, field_name, default=None, request=None, get_value=None, return_version=False, fallback=True):
    if not request:
        request = getattr(item, 'request', None)
    if not item.VERSIONS:
        if return_version:
            return None, default
        return default
    exclude_versions = []
    # Try to get from most relevant version, if value does not exist, move on to next most relevant version
    while len(exclude_versions) < len(item.VERSIONS):
        version_name = getRelevantVersion(item=item, request=request, exclude_versions=exclude_versions, fallback_to_first=False)
        if not version_name:
            break
        version = item.VERSIONS[version_name]
        value = getFieldForVersion(item, field_name, version_name, version, get_value=get_value)
        if value:
            if return_version:
                return version_name, value
            return value
        exclude_versions.append(version_name)
    if not fallback:
        if return_version:
            return None, default
        return default
    # Fallback to English if any version features English
    if couldSpeakEnglish(request=request):
        english_version_name, english_version = _findVersionWithEnglishLanguage(item.VERSIONS)
        if english_version_name:
            value = getFieldForVersion(item, field_name, english_version_name, english_version, get_value=get_value)
            if value:
                if return_version:
                    return english_version_name, value
                return value
    # Fallback to first version in list of versions
    first_version_name, first_version = item.VERSIONS.items()[0]
    first_version_value = getFieldForVersion(item, field_name, first_version_name, first_version, get_value=get_value)
    if first_version_value:
        if return_version:
            return first_version_name, first_version_value
        return first_version_value
    # Fallback to default
    if return_version:
        return None, default
    return default

def getRelevantVersions(
        request=None,
        exclude_versions=[],
        # Either:
        item=None,
        # Or:
        versions=None, versions_statuses=None,
        # Customize what's checked
        check_filtered_choice=True,
        check_status=True,
        check_accounts=True,
        check_language=True,
        fallback_to_first=False,
):
    relevant_versions = []
    while True:
        relevant_version = getRelevantVersion(
            request=request,
            exclude_versions=exclude_versions + relevant_versions,
            item=item, versions=versions, versions_statuses=versions_statuses,
            check_filtered_choice=check_filtered_choice,
            check_status=check_status,
            check_accounts=check_accounts,
            check_language=check_language,
            fallback_to_first=False,
        )
        if not relevant_version:
            break
        relevant_versions.append(relevant_version)
    if not relevant_versions and fallback_to_first:
        versions = versions or (item.VERSIONS if item else {})
        if versions:
            relevant_versions.append(versions.keys()[0])
    return relevant_versions

def getAllVersionsOrderedByRelevance(*args, **kwargs):
    relevant_versions = getRelevantVersions(*args, **kwargs)
    versions = kwargs.get('versions', None) or (kwargs['item'].VERSIONS if kwargs.get('item', None) else {})
    return listUnique(relevant_versions + versions.keys())

# Translated fields

def getTranslatedValueForRelevantVersion(item, field_name, request=None, default=None, return_version=False):
    _get_value = lambda item, version_name, version: getRelevantTranslatedValueForVersion(
        item, field_name, version_name, version, request=request,
    )
    return (
        getFieldForRelevantVersion(
            item, field_name, request=request, get_value=_get_value,
            fallback=False, return_version=return_version,
        ) or _getFallbackForTranslatedValue(
            item, field_name, request=request, return_version=return_version,
        ) or default
    )

def sortByRelevantVersions(
        queryset,
        sorted_field_name='{}start_date',
        # Arguments given to getRelevantVersions
        *args, **kwargs):
    item = kwargs.get('item', None)
    versions = kwargs.get('versions', None) or (item.VERSIONS if item else {})
    relevant_versions = getRelevantVersions(*args, **kwargs)
    first_version = getFirstVersion(item=item, versions=versions)
    neutral_field_name = getVersionNeutralFieldName(sorted_field_name)
    if first_version not in relevant_versions:
        relevant_versions.append(first_version)
    if len(relevant_versions) == 1:
        queryset = queryset.extra(select={
            neutral_field_name: getFieldNameForVersion(sorted_field_name, versions[relevant_versions[0]]),
        })
    elif relevant_versions:
        queryset = queryset.extra(select={
            neutral_field_name: u'COALESCE({})'.format(u', '.join([
                getFieldNameForVersion(sorted_field_name, versions[version_name])
                for version_name in relevant_versions
            ])),
        })
    return queryset

############################################################
# Specify version

def getFieldTemplateForVersion(field_name):
    return field_name if '{}' in field_name else u'{}{}'.format('{}', field_name)

def getVersionNeutralFieldName(field_name):
    return getFieldTemplateForVersion(field_name).format('')

def getFieldNameForVersion(field_name, version):
    return getFieldTemplateForVersion(field_name).format(version['prefix'])

def getFieldNameForVersionAndLanguage(field_name, version, language):
    return getFieldTemplateForVersion(field_name).format(u'{}{}_'.format(
        version['prefix'], tourldash(language).replace('-', '')))

def getFieldForVersion(item, field_name, version_name, version, get_value=None, language=None):
    if get_value:
        return get_value(item, version_name, version)
    if language:
        return getattr(item, getFieldNameForVersionAndLanguage(field_name, version, language), None)
    return getattr(item, getFieldNameForVersion(field_name, version), None)

# Values per languages

def getValuesPerLanguagesForVersion(item, field_name, version_name, version, get_value=None):
    return OrderedDict([ (l, v) for l, v in [
        (language, getFieldForVersion(item, field_name, version_name, version, get_value=get_value, language=language,
        )) for language in getLanguagesForVersion(version) or LANGUAGES_DICT.keys()
    ] if v ])

def getValueOfRelevantLanguageForVersion(item, field_name, version_name, version, request=None, default=None):
    if not request:
        request = getattr(item, 'request', None)
    values = getValuesPerLanguagesForVersion(item, field_name, version_name, version)
    if values:
        # Try current language first
        language = request.LANGUAGE_CODE if request else get_language()
        if values.get(language, None):
            return values[language]
        # Fallback to 1st in list
        return values[values.keys()[0]]
    # Fallback to default
    return default

# Translated fields

def getLanguagesForVersion(version):
    return (version.get('languages', []) or []) + [l for l in [ version.get('language', None) ] if l ]

def getTranslatedValuesForVersion(item, field_name, version):
    return OrderedDict([ (l, v) for l, v in [
        (language, item.get_translation(
            field_name, language=language,
            fallback_to_english=False, fallback_to_other_sources=False,
        )) for language in getLanguagesForVersion(version)
    ] if v ])

def getRelevantTranslatedValueForVersion(item, field_name, version_name, version, request=None, fallback=False, default=None):
    if not request:
        request = getattr(item, 'request', None)
    translations = getTranslatedValuesForVersion(item, field_name, version)
    if translations:
        # Try current language first
        language = request.LANGUAGE_CODE if request else get_language()
        if translations.get(language, None):
            return translations[language]
        # Fallback to 1st in list
        return translations[translations.keys()[0]]
    elif fallback:
        fallback_value = _getFallbackForTranslatedValue(item, field_name, request=None)
        if fallback_value:
            return fallback_value
    # Fallback to default
    return default

############################################################
# Internal

def _findVersionWithEnglishLanguage(versions):
    for version_name, version in versions.items():
        if 'en' in getLanguagesForVersion(version):
            return version_name, version
    return None, None

def _getFallbackForTranslatedValue(item, field_name, request=None, return_version=False):
    if not request:
        request = getattr(item, 'request', None)
    # Fallback to English
    if couldSpeakEnglish(request=request):
        english_value = getattr(item, field_name)
        if english_value:
            if return_version:
                english_version_name, english_version = _findVersionWithEnglishLanguage(item.VERSIONS)
                return english_version_name, english_value
            return english_value
    # Fallback to first version in list of versions
    first_version_name, first_version = item.VERSIONS.items()[0]
    first_version_value = getRelevantTranslatedValueForVersion(
        item, field_name, first_version_name, first_version,
        request=request, fallback=False,
    )
    if first_version_value:
        if return_version:
            return first_version_name, first_version_value
        return first_version_value
    # Note: if a translation exists in any other language, it will not be returned.
    if return_version:
        return None, None
    return None
