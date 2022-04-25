from django.utils.text import format_lazy

############################################################
# General

#### string_concat polyfill
def string_concat(*params):
    return format_lazy("{}"*len(params), *params)