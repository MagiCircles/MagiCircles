# -*- coding: utf-8 -*-
from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _, string_concat

TWITTER_MAX_CHARACTERS = 280
TWITTER_LINKS_COUNT_AS_X_CHARACTERS = 23

MAX_URL_LENGTH = 1200 # Real max is 2014 but we don't want our URLs to be this long

please_understand_template_sentence = 'Please understand that we have a very young audience, so we have to be very careful with what appears on our web app.'

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
    'ajax_modal_only', 'ajax_show_top_buttons', 'ajax_show_top_buttons',
    'hide_relevant_fields_on_ordering',
    'show_owner', 'get_started'
    'max_per_line',
    'open',
    'buttons_color',
]

# Values that may be added to a form field after it was instanciated
FORM_FIELDS_EXTRA_VALUES = [
    'form_group_classes',
    'before_field', 'above_field', 'below_field', 'after_field',
    'show_value_instead', 'show_as_required',
]

KNOWN_CRAWLERS = [
    'Googlebot',
    'DuckDuckBot',
    'Applebot',
    'Baiduspider',
    'Bingbot',
    'Slurp',
    'YandexBot',
    'facebot',
    'ia_archiver',
    'Exabot',
    'Majestic',
    'PetalBot',
    'AhrefsBot',
    'SEMrushBot',
    'DotBot',
]

KNOWN_ITEM_PROPERTIES = [
    'birthday_banner',
    'birthday_banner_css_class',
    'birthday_banner_hide_title',
    'blocked',
    'blocked_by_owner',
    'blocked_owner_id',
    'display_ajax_item_url',
    'display_item_url',
    'display_name',
    'display_name_in_list',
    'get_ajax_item_url',
    'get_item_url',
    'html_attributes',
    'html_attributes_in_list',
    'image_for_favorite_character',
    'image_for_prefetched',
    'IS_PERSON',
    'name_for_questions',
    'new_row',
    'reverse_related',
    'REVERSE_RELATED',
    'selector_to_collected_item',
    'share_image',
    'share_image_in_list',
    'show_image_on_homepage',
    'show_section_header',
    'template_for_prefetched',
    'thumbnail_size',
    'tinypng_settings',
    'top_html',
    'top_html_item',
    'top_html_list',
    'top_image',
    'top_image_item',
    'top_image_list',
    'TRANSLATED_FIELDS',
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
        'name': 'AC',
        'game_name': 'Animal Crossing: New Horizons',
        'game_names': {
            'ja': u'あつまれ どうぶつの森',
            'kr': u'모여봐요 동물의 숲',
            'zh-hans': u'集合啦！動物森友會',
            'zh-hant': u'集合啦！動物森友會',
        },
        'image': 'ac',
        'url': 'https://ac.db0.company/',
        'profile_url': 'https://ac.db0.company/user/{}/',
        'shortname': 'ac',
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

DEFAULT_ICONS_BASED_ON_NAMES = OrderedDict([
    ('name', 'about'), # can be the name of a person or a thing, which is why we don't default to id
    ('images', 'pictures'),
    ('image', 'pictures'),
    ('description', 'id'),
    ('details', 'id'),
    ('tags', 'hashtag'),
    ('source', 'about'),
    ('color', 'palette'),
    ('video', 'film'),
    ('age', 'scoreup'),
    ('score', 'scoreup'),
    ('birthday', 'birthday'),
    ('screenshot', 'screenshot'),
    ('badge', 'badge'),
    ('achievement', 'achievement'),
    ('medal', 'medal'),
    ('message', 'chat'),
    ('comment', 'comments'),
    ('comments', 'comments'),
    ('chat', 'chat'),
    ('favorite_food', 'food-like'),
    ('least_favorite_food' , 'food-dislike'),
    ('food', 'food'),
    ('cards', 'deck'),
    ('fans', 'heart'),
    ('idol', 'idol'),
    ('idols', 'idol'),
    ('song', 'song'),
    ('songs', 'song'),
    ('promo', 'promo'),
    ('nickname', 'heart'),
    ('height', 'measurements'),
    ('hips', 'measurements'),
    ('waist', 'measurements'),
    ('bust', 'measurements'),
    ('measurements', 'measurements'),
    ('blood', 'hp'),
    ('length', 'times'),
    ('bpm', 'hp'),
    ('voice_actress', 'voice-actress'),
    ('voice_actresses', 'voice-actress'),
    ('school', 'school'),
    ('school', 'school'),
    ('hobbies', 'hobbies'),
    ('trivia', 'hobbies'),
    ('specialty', 'star'),
    ('signature', 'author'),
    ('autograph', 'author'),
    ('social_media', 'link'),
    ('itunes_id', 'play'),
    ('release_date', 'date'),
    ('lyrics', 'translate'),
    ('singer', 'singer'),
    ('singers', 'singer'),
    ('buy_url', 'shop'),
    ('download', 'download'),
    ('downloads', 'download'),
    ('unlock', 'unlock'),
    ('lock', 'lock'),
    ('story', 'wiki'),
    ('outfit', 'dress'),
    ('skill', 'skill'),
    ('power', 'power'),
    ('ability', 'power'),
    ('instrument', 'guitar'),
    ('guitar', 'guitar'),
    ('ticket', 'ticket'),
    ('cost', 'money'),
    ('price', 'money'),
    ('fee', 'money'),
    ('voice_actor', 'voice-actor'),
    ('voice_actors', 'voice-actor'),
    ('trade', 'trade'),
    ('exchange', 'trade'),
    ('box', 'box'),
    ('translation', 'translate'),
    ('translate', 'translate'),
    ('idea', 'idea'),
    ('tips', 'idea'),
    ('tip', 'idea'),
    ('advice', 'advice'),
    ('center', 'center'),
    ('category', 'category'),
    ('section', 'category'),
    ('3d', '3d'),
    ('2d', '3d'),
    ('jp', 'jp'),
    ('japanese', 'jp'),
    ('japan', 'jp'),
    ('kr', 'kr'),
    ('korea', 'kr'),
    ('korean', 'kr'),
    ('tw', 'tw'),
    ('taiwan', 'tw'),
    ('taiwanese', 'tw'),
    ('cn', 'cn'),
    ('china', 'cn'),
    ('chinese', 'cn'),
    ('android', 'android'),
    ('map', 'map'),
    ('address', 'map'),
    ('gift', 'present'),
    ('present', 'present'),
    ('warning', 'warning'),
    ('twitter', 'twitter'),
    ('announcement', 'megaphone'),
    ('announcements', 'megaphone'),
    ('news', 'megaphone'),
    ('hand', 'fingers'),
    ('hands', 'fingers'),
    ('fingers', 'fingers'),
    ('archive', 'archive'),
    ('team', 'users'),
])

"""
RFC 3066 -> ISO 639-2

RFC 3066: http://www.i18nguy.com/unicode/language-identifiers.html
ISO 639-2: https://www.loc.gov/standards/iso639-2/php/code_list.php

No change for:
en, es, ru, it, fr, de, pl, ja, id, vi, pt, tr, th, uk
"""
RFC3066_TO_ISO6392 = {
    'zh-hans': 'zh-CN',
    'zh-hant': 'zh-TW',
    'kr': 'ko',
    'pt-br': 'pt',
}
