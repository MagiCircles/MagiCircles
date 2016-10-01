from django.utils import translation

class LanguageFromPreferenceMiddleWare(object):
    def process_request(self, request):
        if request.user.is_authenticated() and not request.user.is_anonymous():
            translation.activate(request.user.preferences.language)
            request.LANGUAGE_CODE = translation.get_language()
