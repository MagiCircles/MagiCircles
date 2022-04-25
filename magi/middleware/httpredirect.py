from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin

class HttpRedirectException(Exception):
    pass

class HttpRedirectMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, HttpRedirectException):
            return HttpResponseRedirect(exception.args[0])
