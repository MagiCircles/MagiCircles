from django import template
from web import model_choices

register = template.Library()
register.filter('statusToString', model_choices.statusToString)
register.filter('statusToColor', model_choices.statusToColor)
register.filter('statusToColorString', model_choices.statusToColorString)
register.filter('linkToString', model_choices.linkToString)
register.filter('linkRelevanceToString', model_choices.linkRelevanceToString)
register.filter('tagToString', model_choices.tagToString)
register.filter('languageToString', model_choices.languageToString)
register.filter('reportStatusToString', model_choices.reportStatusToString)
