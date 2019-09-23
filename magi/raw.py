# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _, string_concat

please_understand_template_sentence = 'Please understand that we have a very young audience, so we have to be very careful with what appears on our website.'

unrealistic_template_sentence = u'Your {thing} is unrealistic, so we edited it. If this was a mistake, please upload a screenshot of your game to the details of your account to prove your {thing} and change it back. Thank you for your understanding.'

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

GET_PARAMETERS_IN_FORM_HANDLED_OUTSIDE = [
    'ordering', 'reverse_order',
    'view',
]

GET_PARAMETERS_NOT_IN_FORM = [
    'ids',
    'page', 'page_size',
    'ajax_modal_only', 'ajax_show_top_buttons',
    'show_owner', 'get_started'
    'max_per_line',
    'only_show_buttons',
    'open',
]

other_sites = [
    {
        'name': 'Idol Story',
        'names': {
            'ja': u'アイドルストーリー',
        },
        'game_name': 'Love Live! SIF All Stars',
        'game_names': {
            'ja': u'ラブライブ！スクフェス All Stars',
        },
        'image': 'idolstory',
        'url': 'https://idol.st/',
        'profile_url': 'https://idol.st/user/{}/',
        'shortname': 'idolstory',
    },
    {
        'name': 'Bandori Party',
        'names': {
            'ja': u'バンドリパーティー',
            'kr' : u'밴드리파티',
            'zh-hans': u'Bandori 派对',
            'zh-hant': u'Bandori 派對',
            'ru': u'бандори парти',
        },
        'game_name': 'BanG Dream! Girls Band Party',
        'game_names': {
            'ja': u'バンドリ！ガールズバンドパーティ',
            'kr': u'뱅드림! 걸즈 밴드 파티!',
            'zh-hans': u'BanG Dream! 少女乐团派对',
            'zh-hant': u'BanG Dream! 少女樂團派對',
        },
        'image': 'bang',
        'url': 'https://bandori.party/',
        'profile_url': 'https://bandori.party/user/{}/',
        'shortname': 'bang',
    },
    {
        'name': 'Starlight Academy',
        'names': {
            'ja': u'スタァライト アカデミー',
            'kr': u'스타라이트 아카데미',
            'zh-hant': u'星光學院',
        },
        'game_name': 'Revue Starlight',
        'game_names': {
            'ja': u'少女☆歌劇 レヴュースタァライト',
            'kr': u'소녀가극 레뷰 스타라이트',
            'zh-hant': u'少女☆歌劇 Revue Starlight',
        },
        'image': 'starlight',
        'url': 'https://starlight.academy/',
        'profile_url': 'https://starlight.academy/user/{}/',
        'shortname': 'starlight',
    },
    {
        'name': 'Cinderella Producers',
        'names': {
            'ja': u'シンデレラプロ',
        },
        'game_name': 'THE iDOLM@STER Cinderella Girls: Starlight Stage',
        'game_names': {
            'ja': u'アイドルマスター シンデレラガールズ スターライトステージ',
            'kr': u'아이돌마스터 신데렐라 걸즈 스타라이트 스테이지',
            'zh-hant': u'偶像大師 灰姑娘女孩 星光舞台',
            'zh-hans': u'偶像大師 灰姑娘女孩 星光舞台',
        },
        'image': 'cpro',
        'url': 'https://cinderella.pro/',
        'profile_url': 'https://cinderella.pro/user/{}/',
        'shortname': 'cpro',
    },
    {
        'name': 'School Idol Tomodachi',
        'names': {
            'ja': u'スクールアイドル友達',
            'kr': u'스쿨 아이돌 토모다치',
            'zh-hans': u'学园偶像朋友',
            'zh-hant': u'學園偶像朋友',
        },
        'game_name': 'LoveLive! School Idol Festival',
        'game_names': {
            'ja': u'ラブライブ',
            'kr': u'러브라이브! 스쿨아이돌 페스티벌',
            'zh-hans': u'LoveLive! 学园偶像祭',
            'zh-hant': u'LoveLive! 學園偶像祭',
        },
        'image': 'schoolidolu',
        'url': 'https://schoolido.lu/',
        'profile_url': 'https://schoolido.lu/user/{}/',
        'shortname': 'schoolidolu',
    },
    {
        'name': 'Maji Love',
        'names': {
            'ja': u'マジLOVE',
            'kr': u'진심 LOVE',
        },
        'game_name': 'Utano☆Princesama Shining Live',
        'game_names': {
            'ja': u'うたの☆プリンスさまっ♪',
            'kr': u'노래의☆왕자님♪',
            'zh-hans': u'歌之王子殿下',
            'ru': u'Поющий☆принц',
        },
        'image': 'majilove',
        'url': 'https://maji.love/',
    },
    {
        'name': 'Stardust Run',
        'names': {
            'ja': u'スターダストラン',
            'zh-hans': u'星尘RUN',
            'zh-hant': u'星屑RUN',
            'ru': u'Звездная пыльRUN',
        },
        'game_name': 'Pokémon Go',
        'game_names': {
            'ja': u'ポケモン ゴー',
            'kr': u'포켓몬 GO',
            'zh-hans': u'精靈寶可夢GO',
            'zh-hant': u'精靈寶可夢GO',
        },
        'image': 'stardustrun',
        'url': 'https://stardust.run/',
        'profile_url': 'https://stardust.run/user/{}/',
        'shortname': 'stardustrun',
    },
    {
        'name': 'fr.gl',
        'game_name': 'Glee Forever',
        'game_names': {
            'ja': u'グリーフォーエバー',
        },
        'image': 'frgl',
        'url': 'http://frgl.db0.company/',
        'profile_url': 'http://frgl.db0.company/user/{}/',
        'shortname': 'frgl',
    },
]
