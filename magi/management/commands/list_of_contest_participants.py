# -*- coding: utf-8 -*-
import requests, json, random
from optparse import make_option
from django.core.management.base import BaseCommand
from django.conf import settings as django_settings
from magi.import_data import (
    loadJsonAPIPage,
    twitterAPICall,
    TWITTER_API_SEARCH_URL,
)
from magi.urls import RAW_CONTEXT
from magi.utils import (
    addParametersToURL,
    getSubField,
    makeImageGrid,
)
from magi.tools import (
    getUserFromLink,
    get_default_owner,
)
from magi import models
from magi import settings

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--instagram',
            action='store',
            help='Instagram hashtag'),
        make_option(
            '--twitter',
            action='store',
            help='Twitter hashtag'),
        make_option(
            '--' + django_settings.SITE,
            action='store',
            help=settings.SITE_NAME + ' hashtag'),
        make_option(
            '--local',
            action='store_true',
            help='Use local files instead of loading from the API when possible.',
        ),

        make_option(
            '--pick-random-winners',
            action='store',
            type='int',
            help='How many winners should be picked randomly?',
        ),
        make_option(
            '--add-badges',
            action='store',
            type='int',
            help='ID of badge to add to all participants',
        ),
        make_option(
            '--list-missing-badges',
            action='store_true',
            help='Show the list of users who didn\'t get their badge because we couldn\'t find their username on ' + settings.SITE_NAME),
        make_option(
            '--one-chance-per-user',
            action='store_true',
            help='By default, all entries have the same chance to win. With this, entries are reduced to one per user bfore picking a random winner.',
        ),

        make_option(
            '--make-markdown-post',
            action='store_true',
            help='Generate a markdown post',
        ),
        make_option(
            '--grid-per-line',
            action='store',
            help='When generating a markdown post, how many images should show per line in the preview grid?',
        ),
        make_option(
            '--contest-name',
            action='store',
            help='When generating a markdown post, what should be the name of the contest?',
        ),
    )

    INSTAGRAM_URL = u'https://www.instagram.com/explore/tags/{hashtag}/'
    INSTAGRAM_GET_USERNAME_URL = u'https://i.instagram.com/api/v1/users/{owner_id}/info/'
    INSTAGRAM_GET_USERNAME_REQUEST_HEADER = {
        #'X-Instagram-GIS': x_instagram_gis,
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 Instagram 12.0.0.16.90 (iPhone9,4; iOS 10_3_3; en_US; en-US; scale=2.61; gamut=wide; 1080x1920)',
        # 'X-Requested-With': 'XMLHttpRequest',
    }
    INSTAGRAM_POST_URL = u'https://www.instagram.com/p/{shortcode}/'
    INSTAGRAM_PROFILE_URL = u'https://instagram.com/{username}/'

    def get_instagram_entries(self):
        local = self.options.get('local', False)
        hashtag = self.options['instagram']
        entries = []
        platform_username_to_site_user = {}
        user_ids = {}
        parameters = {
            '__a': 1,
        }
        page_number = 0
        get_url = lambda: addParametersToURL(self.INSTAGRAM_URL.format(hashtag=hashtag), parameters)
        url = get_url()
        while url:
            # Get posts
            result = loadJsonAPIPage(
                url, local=local, load_on_not_found_local=True, verbose=True,
                local_file_name='instagram-{}'.format(page_number),
            )
            result = getSubField(result, ['graphql', 'hashtag', 'edge_hashtag_to_media'], {})

            # Go through posts
            for post in result.get('edges', []):
                post = post.get('node', {})
                owner_id = getSubField(post, ['owner', 'id'])
                if owner_id not in user_ids:
                    user_result = loadJsonAPIPage(
                        url=self.INSTAGRAM_GET_USERNAME_URL.format(owner_id=owner_id),
                        load_on_not_found_local=True,
                        local_file_name='instagram-user-{}'.format(owner_id),
                        local=True, request_options={
                            'headers': self.INSTAGRAM_GET_USERNAME_REQUEST_HEADER,
                        },
                    )
                    user_ids[owner_id] = getSubField(user_result, ['user', 'username'])
                username = user_ids[owner_id]

                if username not in platform_username_to_site_user:
                    site_user = getUserFromLink(username, type='instagram')
                    if site_user:
                        platform_username_to_site_user[username] = site_user
                    else:
                        platform_username_to_site_user[username] = None

                site_user = platform_username_to_site_user[username]

                entries.append({
                    'platform': 'instagram',
                    'instagram_username': username,
                    'instagram_profile_url': self.INSTAGRAM_PROFILE_URL.format(username=username),
                    'url': self.INSTAGRAM_POST_URL.format(shortcode=post.get('shortcode', None)),
                    'image': post.get('thumbnail_src', None),
                    u'{}_username'.format(django_settings.SITE): site_user.username if site_user else None,
                    u'{}_profile_url'.format(django_settings.SITE): site_user.http_item_url if site_user else None,
                })

            # Get next page
            if getSubField(result, ['page_info', 'has_next_page'], default=False):
                parameters['max_id'] = getSubField(result, ['page_info', 'end_cursor'])
                url = get_url()
            else:
                url = None
            page_number +=1
        return entries

    TWEET_URL = 'https://twitter.com/{username}/status/{id}'
    TWITTER_PROFILE_URL = 'https://twitter.com/{username}'

    def get_twitter_entries(self):
        local = self.options.get('local', False)
        hashtag = self.options['twitter']
        entries = []
        platform_username_to_site_user = {}

        data = {
            'query': '#{}'.format(hashtag),
            'maxResults': 100,
        }
        page_number = 0
        has_next = True

        while has_next:
            # Get tweets
            result = twitterAPICall(TWITTER_API_SEARCH_URL, data, load_json_api_options={
                'local': local, 'load_on_not_found_local': True, 'verbose': True,
                'local_file_name': 'twitter-{}'.format(page_number),
            })
            if not result:
                break

            # Go through tweets
            for tweet in result['results']:

                if tweet['text'].startswith('RT @'):
                    continue

                username = tweet['user']['screen_name']
                if username == settings.TWITTER_HANDLE:
                    continue

                tweet_id = tweet['id_str']
                tweet_url = self.TWEET_URL.format(username=username, id=tweet_id)
                profile_url = self.TWITTER_PROFILE_URL.format(username=username)
                image = getSubField(tweet, ['extended_tweet', 'extended_entities', 'media', 0, 'media_url_https'])

                if username not in platform_username_to_site_user:
                    site_user = getUserFromLink(username, type='twitter')
                    if site_user:
                        platform_username_to_site_user[username] = site_user
                    else:
                        platform_username_to_site_user[username] = None

                site_user = platform_username_to_site_user[username]

                entries.append({
                    'platform': 'twitter',
                    'twitter_username': username,
                    'twitter_profile_url': profile_url,
                    'url': tweet_url,
                    'image': image,
                    u'{}_username'.format(django_settings.SITE): site_user.username if site_user else None,
                    u'{}_profile_url'.format(django_settings.SITE): site_user.http_item_url if site_user else None,
                })

            # Get next page
            next_page = result.get('next', None)
            if next_page:
                data['next'] = next_page
            else:
                has_next = False
            page_number += 1

        return entries

    def get_site_entries(self):
        tag = self.options[django_settings.SITE]
        activities = models.Activity.objects.filter(c_tags__contains='"{}"'.format(tag)).select_related(
            'owner', 'owner__preferences')
        return [
            {
                'platform': django_settings.SITE,
                u'{}_username'.format(django_settings.SITE): activity.owner.username,
                u'{}_profile_url'.format(django_settings.SITE): activity.owner.http_item_url,
                'url': activity.http_item_url,
                'image': activity.get_first_image(),
            } for activity in activities
        ]

    def pick_random_winners(self, all_entries):
        # Make entries unique per user if needed
        one_chance_per_user = self.options.get('one_chance_per_user', False)
        if one_chance_per_user:
            unique_entries_per_site = {} # dict of username -> entry
            unique_entries_per_platform = {} # dict of platform -> (dict of username -> entry)
            for platform in all_entries:
                for entry in all_entries[platform]:
                    site_username = entry.get(u'{}_username'.format(django_settings.SITE))
                    platform_username = entry.get(u'{}_username'.format(platform))
                    if site_username:
                        unique_entries_per_site[site_username.lower()] = entry
                    else:
                        if platform not in unique_entries_per_platform:
                            unique_entries_per_platform[platform] = {}
                        unique_entries_per_platform[platform][platform_username.lower()] = entry
            all_unique_entries = unique_entries_per_site.values()
            for platform, entries in unique_entries_per_platform.items():
                all_unique_entries += entries.values()
        else:
            all_unique_entries = [
                entry
                for platform in all_entries
                for entry in all_entries[platform]
            ]
        # Pick random entries
        return random.sample(all_unique_entries, self.options['pick_random_winners'])

    def make_markdown_post(self, all_entries, winners):
        print '# MARKDOWN POST'
        print ''
        print ''
        name = self.options.get('contest_name', None)
        if name:
            print '# {}'.format(name)
            print ''
        if winners:
            print 'And the winner{}...'.format('s are' if len(winners) > 1 else ' is')
            print ''
            for entry in winners:
                print u'## **[{username}]({url})**'.format(**({
                    'username': entry[u'{}_username'.format(django_settings.SITE)],
                    'url': entry[u'{}_profile_url'.format(django_settings.SITE)],
                } if entry.get(u'{}_username'.format(django_settings.SITE), None) else {
                    'username': entry[u'{}_username'.format(entry['platform'])],
                    'url': entry[u'{}_profile_url'.format(entry['platform'])],
                }))
                print ''
                print '*Selected randomly, one chance per {}*'.format(
                    'user' if self.options.get('one_chance_per_user', False) else 'entry')
                print ''
                print u'↳ [See entry]({})'.format(entry['url'])
                print ''
                if entry['image']:
                    print '![winning entry image]({})'.format(entry['image'])
                    print ''
            print ''
            print '## **Congratulations to our winners!**'
            print 'They will receive a prize of their choice among the prizes we offer. You can see the list of prizes with pictures in the original details post.'
            print ''
            print '***'
            print ''
        if self.options.get('grid_per_line', None):
            images = [
                entry['image']
                for platform in all_entries
                for entry in all_entries[platform]
                if entry.get('image', None)
            ]
            random.shuffle(images)
            grid_instance = makeImageGrid(
                images, per_line=int(self.options['grid_per_line']),
                width=800,
                upload=True,
                model=models.UserImage,
            )
            if grid_instance:
                print u'![All participants]({})'.format(grid_instance.http_image_url)
                print ''

        print 'Thanks to everyone who participated and helped make this contest a success! We loved your entries!'
        print ''
        print '***'
        print ''
        if 'donate' in RAW_CONTEXT['all_enabled']:
            print '# Support our giveaways!'
            print ''
            print u'[![Support us on Patreon](https://i.imgur.com/kmQ3vKP.png)](https://patreon.com/db0company/)'
            print ''
            print 'These special events are made possible thanks to the support of our warm-hearted donators. If you wish to support {site} for both our future special events and to cover the cost of our expensive servers in which our site run, please consider donating on Patreon.'.format(site=settings.SITE_NAME)
            print ''
            print '***'
            print ''
        print '# **F.A.Q.**'
        print ''
        print' - **I won and I didn\'t hear from you?**'
        print '    - Check [your private messages](/privatemessages/). You may have to wait up to 24 hours after announcement.'
        print '- **I didn\'t win and I\'m sad ;_;**'
        print u'   - The staff and the community loved your entry so your efforts didn\'t go to waste at all 💖 Please join our next special event!'
        print '- **How can  I thank you for your amazing work organizing these special events?**'
        print u'    - We always appreciate sweet comments below, and if you want to push it a little further, we have a [Patreon](https://patreon.com/db0company/) open for donations ❤️'
        print '- **More questions?**'
        print '    -  Read the [Giveaways FAQ](/help/Giveaways%20FAQ) and ask your questions in the comments.'
        print ''
        print '***'
        print ''
        print '# **All participants**'
        print ''
        for platform, platform_name in [
                (django_settings.SITE, settings.SITE_NAME),
                ('instagram', 'Instagram'),
                ('twitter', 'Twitter'),
        ]:
            entries = all_entries.get(platform, [])
            if entries:
                print 'On {}:'.format(platform_name)
                print u', '.join([u'[{}]({})'.format(
                    entry['{}_username'.format(platform)], entry['url']) for entry in entries]
                )
            print ''

    def add_badges(self, all_entries, winners):
        print '# ADD BADGES'
        badge = models.Badge.objects.get(id=self.options['add_badges'])
        cant_get = {}
        for platform in all_entries:
            for entry in all_entries[platform]:
                username = entry.get(u'{}_username'.format(django_settings.SITE), None)
                if not username:
                    if platform not in cant_get:
                        cant_get[platform] = []
                    cant_get[platform].append(entry[u'{}_username'.format(platform)])
                else:
                    try:
                        existing_badge = models.Badge.objects.filter(user__username=username, name=badge.name)[0]
                    except IndexError:
                        rank = None
                        for winner in winners:
                            if winner == entry:
                                rank = models.Badge.RANK_GOLD
                        print 'Adding badge to {}'.format(username)
                        models.Badge.objects.create(
                            owner=badge.owner,
                            user=models.User.objects.get(username=username),
                            name=badge.name,
                            description=badge.description,
                            image=badge.image,
                            url=badge.url,
                            show_on_top_profile=badge.show_on_top_profile,
                            show_on_profile=badge.show_on_profile,
                            rank=rank,
                        )
            '--list-missing-badges',
        if self.options.get('list_missing_badges'):
            print json.dumps(cant_get, indent=4)

    def handle(self, *args, **options):
        self.options = options
        all_entries = {}
        winners = []
        if options.get('instagram', None):
            all_entries['instagram'] = self.get_instagram_entries()
        if options.get('twitter', None):
            all_entries['twitter'] = self.get_twitter_entries()
        if options.get(django_settings.SITE, None):
            all_entries[django_settings.SITE] = self.get_site_entries()

        totals = {
            platform: len(all_entries[platform])
            for platform in all_entries
        }
        totals['all'] = sum(totals.values())
        print '# ALL ENTRIES'
        print json.dumps(all_entries, indent=4)
        print ''
        print 'TOTAL'
        print json.dumps(totals, indent=4)
        print '  ---  '
        print ''

        if options.get('pick_random_winners', None):
            winners = self.pick_random_winners(all_entries)

        if options.get('add_badges', None):
            self.add_badges(all_entries, winners)

            print '# WINNERS'
            print json.dumps(winners, indent=4)
            print '  ---  '
            print ''

        if options.get('make_markdown_post', False):
            self.make_markdown_post(all_entries, winners)
