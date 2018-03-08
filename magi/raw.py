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
        'image': 'http://i.schoolido.lu/android/icon.png',
        'url': 'http://schoolido.lu/',
    },
    {
        'name': 'Stardust Run',
        'game_name': 'Pokémon Go',
        'image': 'http://i.stardust.run/static/img/avatar.png',
        'url': 'http://stardust.run/',
    },
    {
        'name': 'Cinderella Producers',
        'game_name': 'THE iDOLM@STER Cinderella Girls: Starlight Stage',
        'image': 'http://i.cinderella.pro/static/img/avatar.png',
        'url': 'http://cinderella.pro/',
    },
    {
        'name': 'Bandori Party',
        'game_name': string_concat(_('BanG Dream!'), _('Girls Band Party')),
        'image': 'http://i.bandori.party/static/img/avatar.png',
        'url': 'http://bandori.party/',
    },
]
