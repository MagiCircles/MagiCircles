from django.http import HttpResponseRedirect

class HttpRedirectException(Exception):
    pass

class HttpRedirectMiddleware(object):
    def process_exception(self, request, exception):
        if isinstance(exception, HttpRedirectException):
            return HttpResponseRedirect(exception.args[0])
