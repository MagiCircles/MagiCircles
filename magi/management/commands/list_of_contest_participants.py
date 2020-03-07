# -*- coding: utf-8 -*-
import requests, json, random, csv
from optparse import make_option
from django.core.management.base import BaseCommand
from django.conf import settings as django_settings
from django.db.models import Prefetch
from magi.import_data import (
    loadJsonAPIPage,
    twitterAPICall,
    TWITTER_API_SEARCH_URL,
)
from magi.urls import RAW_CONTEXT
from magi.utils import (
    addParametersToURL,
    csvToDict,
    getSubField,
    listUnique,
    makeImageGrid,
    makeBadgeImage,
    titleToSnakeCase,
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
            '--csv',
            action='store',
            help='CSV file with list of entries'),
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
            'owner', 'owner__preferences').prefetch_related(
                Prefetch('owner__links', queryset=models.UserLink.objects.filter(
                    i_type__in=self.platforms), to_attr='all_links'),
            )
        entries = []
        for activity in activities:
            entry = {
                'platform': django_settings.SITE,
                u'{}_username'.format(django_settings.SITE): activity.owner.username,
                u'{}_profile_url'.format(django_settings.SITE): activity.owner.http_item_url,
                'url': activity.http_item_url,
                'image': activity.get_first_image(),
            }
            # Add username/profile for other platforms that could be in user links
            for platform in self.platforms:
                for link in activity.owner.all_links:
                    if platform == link.type:
                        if u'{}_username'.format(platform) not in entry:
                            entry[u'{}_username'.format(platform)] = []
                        entry[u'{}_username'.format(platform)].append(link.value)
                        if u'{}_profile_url'.format(platform) not in entry:
                            entry[u'{}_profile_url'.format(platform)] = []
                        entry[u'{}_profile_url'.format(platform)].append(link.url)
            entries.append(entry)
        return entries

    def get_csv_rows(self):
        if not getattr(self, '_csv_rows', None):
            csv_file = open(self.options['csv'])
            csv_reader = csv.reader(csv_file)
            csv_titles = []
            entries = {}
            for i, row in enumerate(csv_reader):
                if i == 0:
                    csv_titles = row
                    continue
                entry = csvToDict(row, csv_titles, snake_case=True)
                platform = titleToSnakeCase(entry['platform'])
                entry['platform'] = platform
                if platform not in entries:
                    entries[platform] = []
                entries[platform].append(entry)
            csv_file.close()
            self._csv_rows = entries
        return self._csv_rows

    def get_platforms_from_csv(self):
        return self.get_csv_rows().keys()

    def get_csv_entries(self, all_entries):
        for platform, entries in self.get_csv_rows().items():
            if platform not in all_entries:
                all_entries[platform] = []
            all_entries[platform] += entries

    def get_entries_per_unique_user(self, all_entries):
        entries_per_user = [] # list of list of entry. each sub-list is a single user

        def add_to_entries_per_user(platform, entry):
            for other_entries_per_user in entries_per_user:
                for other_entry in other_entries_per_user:
                    for other_platform in self.platforms:
                        usernames = entry.get(u'{}_username'.format(other_platform), None)
                        if not usernames:
                            continue
                        other_usernames = other_entry.get(u'{}_username'.format(other_platform), None)
                        if not other_usernames:
                            continue
                        if not isinstance(usernames, list):
                            usernames = [usernames]
                        if not isinstance(other_usernames, list):
                            other_usernames = [other_usernames]
                        for username in usernames:
                            for other_username in other_usernames:
                                if username == other_username:
                                    other_entries_per_user.append(entry)
                                    return
            entries_per_user.append([entry])

        for platform, entries in all_entries.items():
            for entry in entries:
                add_to_entries_per_user(platform, entry)
        return entries_per_user

    def get_unique_entries(self, all_entries):
        return [
            random.choice(entries_per_user)
            for entries_per_user in self.get_entries_per_unique_user(all_entries)
        ]

    def get_all_flat_entries(self, all_entries):
        return [
            entry
            for platform in all_entries
            for entry in all_entries[platform]
        ]

    def get_flat_entries(self, all_entries):
        # Make entries unique per user if needed
        one_chance_per_user = self.options.get('one_chance_per_user', False)
        if one_chance_per_user:
            return self.get_unique_entries(all_entries)
        return self.get_all_flat_entries(all_entries)

    def pick_random_winners(self, all_entries):
        return random.sample(self.get_flat_entries(all_entries), self.options['pick_random_winners'])

    def list_first(self, l):
        if isinstance(l, list):
            return l[0] if l else None
        return l

    def make_markdown_post(self, all_entries, winners):
        grid_instance = None
        if self.options.get('grid_per_line', None):
            images = [
                entry['image']
                for entry in self.get_flat_entries(all_entries)
                if entry.get('image', None)
            ]
            random.shuffle(images)
            grid_instance = makeImageGrid(
                images, per_line=int(self.options['grid_per_line']),
                width=800,
                upload=True,
                model=models.UserImage,
            )

        # Make badge image
        badge_instance = None
        if self.options.get('add_badges', None):
            badge_instance = makeBadgeImage(
                self.badge,
                upload=True,
                model=models.UserImage,
                with_padding=200,
                width=200,
            )

        print ''
        print '# MARKDOWN POST'
        print ''
        print ''
        name = self.options.get('contest_name', None)
        if name:
            print '# {}'.format(name)
            print ''
        print '### **Thanks to everyone who participated and helped make this event a success! We loved your entries!**'
        print ''

        if grid_instance:
            print u'![All participants]({})'.format(grid_instance.http_image_url)
            print ''

        print '***'
        print ''
        if badge_instance:
            print 'As promised, you all received a badge on your profile, as a thank you for participating.'
            print ''
            print u'![Badge]({})'.format(badge_instance.http_image_url)
            print ''
            print '***'
            print ''

        if winners:
            print 'And the winner{}...'.format('s are' if len(winners) > 1 else ' is')
            print ''
            for entry in winners:
                print u'## **[{username}]({url})**'.format(**({
                    'username': self.list_first(entry[u'{}_username'.format(django_settings.SITE)]),
                    'url': self.list_first(entry[u'{}_profile_url'.format(django_settings.SITE)]),
                } if entry.get(u'{}_username'.format(django_settings.SITE), None) else {
                    'username': self.list_first(entry[u'{}_username'.format(entry['platform'])]),
                    'url': self.list_first(entry[u'{}_profile_url'.format(entry['platform'])]),
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
            print ''
            print 'They will receive a prize of their choice among the prizes we offer.'
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
        for platform, entries in all_entries.items():
            if len(self.platforms) > 1:
                platform_name = {
                    django_settings.SITE: settings.SITE_NAME,
                    'instagram': 'Instagram',
                    'twitter': 'Twitter',
                }.get(platform, None)
                if not platform_name:
                    try:
                        platform_name = models.UserLink.get_verbose_i('type', platform)
                    except KeyError:
                        platform_name = platform
                print u'On {}:'.format(platform_name)
            print u', '.join([u'[{}]({})'.format(
                entry[u'{}_username'.format(platform)], entry['url']) for entry in entries]
            )
            print ''

    def find_site_user_from_platform(self, platform, username):
        try:
            return models.UserLink.objects.filter(
                i_type=platform, value=username,
            ).select_related('owner', 'owner__preferences')[0].owner
        except IndexError:
            return None

    def add_badges(self, all_entries, winners):
        print '# ADD BADGES'
        badge = models.Badge.objects.get(id=self.options['add_badges'])
        self.badge = badge
        cant_get = {}
        for platform in all_entries:
            for entry in all_entries[platform]:
                username = entry.get(u'{}_username'.format(django_settings.SITE), None)
                user = None
                # Try to get user from user links
                if not username:
                    user = self.find_site_user_from_platform(platform, entry.get(
                        u'{}_username'.format(platform)))
                    if user:
                        username = user.username
                # If couldn't find, add do cant_get
                if not username:
                    if platform not in cant_get:
                        cant_get[platform] = {}
                    username = entry[u'{}_username'.format(platform)]
                    if username not in cant_get[platform]:
                        cant_get[platform][username] = entry['url']
                else:
                    name = badge.name
                    # Check for existing badge
                    try:
                        existing_badge = models.Badge.objects.filter(
                            user__username=username,
                            name__startswith=name.replace(' - Participant', '').replace(' - Winner', ''),
                        )[0]
                    except IndexError:
                        existing_badge = None
                    # Determine name and rank based on winning or not
                    rank = None
                    name = badge.name.replace(' - Winner', ' - Participant')
                    for winner in winners:
                        if winner == entry:
                            rank = models.Badge.RANK_GOLD
                            name = name.replace(' - Participant', ' - Winner')
                    # Fix existing badge if winners changed
                    if existing_badge:
                        if (existing_badge.name != name
                            or existing_badge.rank != rank):
                            existing_badge.name = name
                            existing_badge.rank = rank
                            existing_badge.save()
                    # Add badge
                    else:
                        print 'Adding badge to {}'.format(username)
                        if not user:
                            try:
                                user = models.User.objects.select_related('preferences').filter(username=username)[0]
                            except IndexError:
                                print '   User not found'
                        if user:
                            models.Badge.objects.create(
                                owner=badge.owner,
                                user=user,
                                name=name,
                                m_description=badge.m_description,
                                _cache_description=badge._cache_description,
                                image=badge.image,
                                url=entry['url'],
                                show_on_top_profile=badge.show_on_top_profile,
                                show_on_profile=badge.show_on_profile,
                                rank=rank,
                            )
                            user.preferences.force_update_cache('tabs_with_content')
        if self.options.get('list_missing_badges'):
            print 'Couldn\'t add badges to:'
            print json.dumps(cant_get, indent=4)

    def handle(self, *args, **options):
        self.options = options
        all_entries = {}
        winners = []

        # Get the list of platforms
        self.platforms = []
        if options.get('instagram', None):
            self.platforms.append('instagram')
        if options.get('twitter', None):
            self.platforms.append('twitter')
        if options.get(django_settings.SITE, None):
            self.platforms.append(django_settings.SITE)
        if options.get('csv', None):
            self.platforms += self.get_platforms_from_csv()

        # Get entries for each platform
        if options.get('instagram', None):
            all_entries['instagram'] = self.get_instagram_entries()
        if options.get('twitter', None):
            all_entries['twitter'] = self.get_twitter_entries()
        if options.get(django_settings.SITE, None):
            all_entries[django_settings.SITE] = self.get_site_entries()
        if options.get('csv', None):
            self.get_csv_entries(all_entries)

        # Fix usernames starting with @
        for platform, entries in all_entries.items():
            for entry in entries:
                for key, value in entry.items():
                    if key.endswith('username'):
                        if isinstance(value, list):
                            entry[key] = [
                                (u[1:] if u.startswith('@') else u)
                                for u in value
                            ]
                        elif value.startswith('@'):
                            entry[key] = value[1:]

        # Totals
        totals = {
            platform: len(all_entries[platform])
            for platform in all_entries
        }
        totals['all'] = sum(totals.values())

        # Print entries
        print '# ALL ENTRIES'
        print json.dumps(all_entries, indent=4)
        print ''
        print 'TOTAL'
        print json.dumps(totals, indent=4)
        print '  ---  '
        print ''

        # Pick random winners
        if options.get('pick_random_winners', None):
            winners = self.pick_random_winners(all_entries)

            print '# WINNERS'
            print json.dumps(winners, indent=4)
            print '  ---  '
            print ''

        # Add badges
        if options.get('add_badges', None):
            self.add_badges(all_entries, winners)

        # Make markdown post
        if options.get('make_markdown_post', False):
            self.make_markdown_post(all_entries, winners)
