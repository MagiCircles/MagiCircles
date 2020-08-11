from collections import OrderedDict
from django.utils.translation import get_language
from magi.default_settings import RAW_CONTEXT
from magi.utils import (
    couldSpeakEnglish,
    getEventStatus,
)

############################################################
# Get relevant values that should be displayed
# based on base languages or specified languages (ordered)

def getRelevantValues():
    pass #todo

############################################################
# Pick relevant version automatically

def getRelevantVersion(
        request=None,
        fallback_to_first=True,
        exclude_versions=[],
        # Either:
        item=None,
        # Or:
        versions=None, versions_statuses=None,
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
    if request:
        version_name = request.GET.get('version', None)
        if version_name in versions:
            return version_name
        version_name = i_version_string_to_version.get(request.GET.get('i_version', None), None)
        if version_name in versions:
            return version_name

    # Based on status
    if versions_statuses or item:
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

    # User language
    language = request.LANGUAGE_CODE if request else get_language()
    for version_name, version in versions.items():
        for version_language in getLanguagesForVersion(version):
            if language == version_language:
                return version_name

    # Fallback to first
    if fallback_to_first:
        return versions.keys()[0]

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

# Translated fields

def getTranslatedValueForRelevantVersion(item, field_name, request=None, default=None, return_version=False):
    _get_value = lambda item, version_name, version: getRelevantTranslatedValueForVersion(
        item, field_name, version_name, version, request=request, fallback=False,
    )
    return (
        getFieldForRelevantVersion(
            item, field_name, request=request, get_value=_get_value,
            fallback=False, return_version=return_version,
        ) or _getFallbackForTranslatedValue(
            item, field_name, request=request, return_version=return_version,
        ) or default
    )

############################################################
# Specify version

def getFieldNameForVersion(field_name, version):
    return (
        field_name.format(version['prefix'])
        if '{}' in field_name
        else u'{}{}'.format(version['prefix'], field_name)
    )

def getFieldForVersion(item, field_name, version_name, version, get_value=None):
    if get_value:
        return get_value(item, version_name, version)
    return getattr(item, getFieldNameForVersion(field_name, version), None)

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
