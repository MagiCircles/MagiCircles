# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _, string_concat

please_understand_template_sentence = 'Please understand that we have a very young audience, so we have to be very careful with what appears on our website.'

donators_adjectives = [
    _('lovely'),
    _('awesome'),
    _('incredible'),
    _('adorable'),
    _('generous'),
    _('idols-addicted'),
    _('friendly'),
    _('kind'),
    _('warmhearted'),
    _('nice'),
]

other_sites = [
    {
        'name': 'School Idol Tomodachi',
        'game_name': 'LoveLive! School Idol Festival',
        'image': 'https://i.schoolido.lu/static/sukutomo.png',
        'url': 'http://schoolido.lu/',
    },
    {
        'name': 'Cinderella Producers',
        'game_name': 'THE iDOLM@STER Cinderella Girls: Starlight Stage',
        'image': 'https://i.cinderella.pro/static/img/avatar.png',
        'url': 'https://cinderella.pro/',
    },
    {
        'name': 'Bandori Party',
        'game_name': string_concat(_('BanG Dream!'), _('Girls Band Party')),
        'image': 'https://i.bandori.party/static/img/avatar.png',
        'url': 'https://bandori.party/',
    },
    {
        'name': 'Maji Love',
        'game_name': string_concat(_(u'Utano☆Princesama'), ' ', _(u'Shining Live')),
        'image': 'http://i.maji.love/static/img/avatar.png',
        'url': 'https://maji.love/',
    },
    {
        'name': 'Stardust Run',
        'game_name': 'Pokémon Go',
        'image': 'https://i.stardust.run/static/img/avatar.png',
        'url': 'https://stardust.run/',
    },
]
