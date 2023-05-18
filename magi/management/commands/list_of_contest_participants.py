# -*- coding: utf-8 -*-
import json, random, csv
from collections import OrderedDict
from optparse import make_option
from django.core.management.base import BaseCommand
from django.conf import settings as django_settings
from django.db.models import Prefetch, Q
from magi.urls import RAW_CONTEXT
from magi.utils import (
    andJoin,
    AttrDict,
    csvToDict,
    failSafe,
    listUnique,
    makeImageGrid,
    makeBadgeImage,
    matchesTemplate,
    ordinalNumber,
    toHumanReadable,
    titleToSnakeCase,
)
from magi import models
from magi import settings

SITE = django_settings.SITE

class Entry(AttrDict):
    @property
    def usernames(self):
        return self.get_usernames(self.platform)

    def clean_username(self, username):
        if username and username.startswith('@'):
            return username[1:]
        return username

    def get_usernames(self, platform):
        usernames = self.get(u'{}_username'.format(platform), [])
        if not isinstance(usernames, list):
            usernames = [ self.clean_username(usernames) ] if usernames else []
        else:
            usernames = listUnique([
                self.clean_username(username) for username in usernames if username ], remove_empty=True)
        self[u'{}_username'.format(platform)] = usernames
        return usernames

    def set_username(self, platform, username):
        usernames = self.get_usernames(platform)
        self[u'{}_username'.format(platform)] = listUnique([
            self.clean_username(username) for username in usernames
        ]+ [ self.clean_username(username) ], remove_empty=True)

    def set_usernames(self, platform, usernames):
        for username in usernames:
            self.set_username(platform, username)

    @property
    def site_usernames(self):
        return self.get_usernames(SITE)

    def set_site_username(self, username):
        self.set_username(SITE, username)

    def has_usernames_in_common(self, platform, other_entry):
        usernames = self.get_usernames(platform)
        for username in other_entry.get_usernames(platform):
            if username in usernames:
                return True
        return False

    @property
    def profile_urls(self):
        return self.get_profile_urls(self.platform)

    def get_profile_urls(self, platform):
        profile_urls = self.get(u'{}_profile_url'.format(platform), [])
        if not isinstance(profile_urls, list):
            profile_urls = [ profile_urls ] if profile_urls else []
        else:
            profile_urls = listUnique(
                [ profile_url for profile_url in profile_urls if profile_url ],
                remove_empty=True,
            )
        self[u'{}_profile_url'.format(platform)] = profile_urls
        return profile_urls

    def set_profile_url(self, platform, profile_url):
        profile_urls = self.get_profile_urls(platform)
        self[u'{}_profile_url'.format(platform)] = listUnique(profile_urls + [ profile_url ], remove_empty=True)

    def set_profile_urls(self, platform, profile_urls):
        for profile_url in profile_urls:
            self.set_profile_url(platform, profile_url)

    @property
    def site_profile_urls(self):
        return self.get_profile_urls(SITE)

    def set_site_profile_url(self, profile_url):
        self.set_profile_url(SITE, profile_url)

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--' + SITE,
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
            '--pick-likes-winners',
            action='store',
            type='int',
            help='How many winners should be picked based on how many likes they have?',
        ),
        make_option(
            '--random-winners',
            action='store',
            type='string',
            help='IDs or URLs of winning posts picked randomly, separated with a comma',
        ),
        make_option(
            '--judges-panel-winners',
            action='store',
            type='string',
            help='IDs or URLs of winning posts picked by the judges panel, separated with a comma',
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
            '--lower-chance-for-previous-winners',
            action='store_true',
            help='People who won something already have a lower chance to win.',
        ),
        make_option(
            '--lower-chance-for-staff',
            action='store_true',
            help='Members of the staff team have a lower chance to win.',
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
        make_option(
            '--stretch-goals',
            action='store_true',
            help='Were stretch goals reached?',
        ),
        make_option(
            '--physical-prizes',
            action='store_true',
            help='Are there physical prizes offered to winners?',
        ),
        make_option(
            '--prizes-image',
            action='store',
            help='Prizes image',
        ),
        make_option(
            '--print-table',
            action='store_true',
            help='Display in table format, to be copy-pasted in a spreadhseet',
        ),

    )

    ############################################################
    # Retrieve entries

    def get_site_entries(self):
        self.activities_by_url = {}
        tag = self.options[SITE]
        activities = models.Activity.objects.filter(c_tags__contains='"{}"'.format(tag)).select_related(
            'owner', 'owner__preferences').prefetch_related(
                Prefetch('owner__links', queryset=models.UserLink.objects.filter(
                    i_type__in=self.platforms), to_attr='all_links'),
            ).exclude(c_tags__contains='"news"')
        entries = []
        for activity in activities:
            url = activity.http_item_url
            self.activities_by_url[url] = activity
            entry = {
                'platform': SITE,
                u'{}_username'.format(SITE): activity.owner.username,
                u'{}_profile_url'.format(SITE): activity.owner.http_item_url,
                'url': url,
                'image': activity.get_first_image(),
                'likes': activity.cached_total_likes,
            }
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
                try:
                    platform = titleToSnakeCase(entry['platform']).strip()
                except KeyError:
                    print '[Warning] Invalid entry, skipped', entry
                    continue
                entry['platform'] = platform
                if (not entry.get('url', None) or
                    (not entry.get(u'{}_username'.format(platform), None)
                     and not entry.get(u'{}_profile_url'.format(platform), None))):
                    print '[Warning] Invalid entry, skipped', entry
                    continue
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

    ############################################################
    # Make entries consistent

    def get_users_queryset(self):
        return models.User.objects.select_related(
            'preferences').prefetch_related(
                Prefetch('links', queryset=models.UserLink.objects.filter(
                    i_type__in=self.platforms), to_attr='all_links'),
            )

    def find_site_users_from_usernames(self):
        self.users_by_username = {}
        usernames_to_lookup = []
        for platform, entries_per_platform in self.all_entries_by_platform.items():
            for entry in entries_per_platform.values():
                for username in entry.site_usernames:
                    if username not in self.users_by_username:
                        if platform == SITE and entry.url in getattr(self, 'activities_by_url', []):
                            activity = self.activities_by_url[entry.url]
                            self.users_by_username[activity.owner.username] = activity.owner
                        else:
                            usernames_to_lookup.append(username)
        if not usernames_to_lookup:
            return
        usernames_to_lookup = listUnique(usernames_to_lookup, remove_empty=True)
        print 'Fetch users by username:', usernames_to_lookup
        for user in self.get_users_queryset().filter(username__in=usernames_to_lookup):
            self.users_by_username[user.username] = user

    def get_profile_url_template(self, platform):
        return models.UserLink.LINK_URLS.get(platform, u'https://{}.com/{{}}'.format(platform))

    def username_to_profile_url(self, platform, username):
        if platform == SITE:
            if username in self.users_by_username:
                return self.users_by_username[username].http_item_url
            print '[Warning] User with username', username, 'not found'
        return self.get_profile_url_template(platform).format(username)

    def profile_url_to_username(self, platform, profile_url):
        if platform == SITE:
            if profile_url.endswith('/'):
                return profile_url.split('/')[-2]
            return profile_url.split('/')[-1]
        template = self.get_profile_url_template(platform)
        if template.startswith('http://'):
            templates_to_try = [ template, template.replace('http://', 'https://') ]
        else:
            templates_to_try = [ template, template.replace('https://', 'http://') ]
        templates_to_try += [
            template[:-1] if template.endswith('/') else template + u'/'
            for template in templates_to_try
        ]
        for template in templates_to_try:
            try:
                return matchesTemplate(template, profile_url)[0]
            except (IndexError, TypeError):
                continue
        return None

    def find_users_from_other_platforms(self):
        users_to_lookup = []
        for entries_per_platform in self.all_entries_by_platform.values():
            for entry in entries_per_platform.values():
                for platform in self.platforms:
                    if platform != SITE:
                        for username in entry.get_usernames(platform):
                            users_to_lookup.append((platform, username))
        if not users_to_lookup:
            return
        print 'Lookup users by other platform usernames:', users_to_lookup
        condition = Q()
        for platform, username in listUnique(users_to_lookup):
            condition |= Q(links__i_type=platform, links__value__iexact=username)
        users_by_platform_username = { platform: {} for platform in self.platforms }
        for user in self.get_users_queryset().filter(condition):
            self.users_by_username[user.username] = user
            for link in user.all_links:
                users_by_platform_username[link.i_type][link.value.lower()] = user
        for entries_per_platform in self.all_entries_by_platform.values():
            for entry in entries_per_platform.values():
                for platform in self.platforms:
                    if platform != SITE:
                        for username in entry.get_usernames(platform):
                            if username.lower() in users_by_platform_username[platform]:
                                user = users_by_platform_username[platform][username.lower()]
                                entry.set_site_username(user.username)
                                entry.set_site_profile_url(user.http_item_url)
                                for link in user.all_links:
                                    if link.i_type != platform:
                                        entry.set_username(link.i_type, link.value)
                                        entry.set_profile_url(link.i_type, link.url)

    def make_entries_consistent(self):
        # Lookup users
        self.find_site_users_from_usernames()
        # Add profile urls and usernames when missing
        for entries_per_platform in self.all_entries_by_platform.values():
            for entry in entries_per_platform.values():
                for platform in self.platforms:
                    if len(entry.get_profile_urls(platform)) < len(entry.get_usernames(platform)):
                        for username in entry.get_usernames(platform):
                            entry.set_profile_url(platform, self.username_to_profile_url(platform, username))
                    if len(entry.get_profile_urls(platform)) > len(entry.get_usernames(platform)):
                        for profile_url in entry.get_profile_urls(platform):
                            entry.set_username(platform, self.profile_url_to_username(platform, profile_url))
        # Find users from other platforms
        self.find_users_from_other_platforms()
        # Find and add usernames and profile urls on entries by the same users to make sure it's consistent
        for platform, entries_per_platform in self.all_entries_by_platform.items():
            for entry in entries_per_platform.values():
                if len(self.platforms) > 1:
                    for other_platform in self.platforms:
                        if other_platform == platform:
                            continue
                        if entry.get_usernames(other_platform):
                            for other_entry in self.all_entries_by_platform[other_platform].values():
                                if entry.has_usernames_in_common(other_platform, other_entry):
                                    other_entry.set_usernames(platform, entry.get_usernames(platform))
                                    other_entry.set_profile_urls(platform, entry.get_profile_urls(platform))

    ############################################################
    # Check users who won before

    def get_users_who_won_before(self):
        if not self.options.get('lower_chance_for_previous_winners', False):
            return [] # doesn't matter, will not be used
        users_who_won_before = []
        for message in models.PrivateMessage.objects.filter(
                owner__is_staff=True,
                to_user__username__in=self.users_by_username.keys(),
        ).filter(
            Q(message__contains=u'Congratulations! 🎉')
            & Q(message__contains='Can you fill this form for me so I can send you your prize?'),
        ).select_related('to_user'):
            users_who_won_before.append(message.to_user.username)
        return users_who_won_before

    ############################################################
    # Prepare entries

    def get_all_entries_by_platform(self, all_entries):
        return {
            platform: OrderedDict([
                (entry_dict['url'], Entry(entry_dict))
                for entry_dict in platform_entries
            ]) for platform, platform_entries in all_entries.items()
        }

    def get_all_entries_by_url(self):
        return OrderedDict([
            (entry.url, entry)
            for entries_per_platform in self.all_entries_by_platform.values()
            for entry in entries_per_platform.values()
        ])

    def get_entries_per_user(self):
        all_entries_per_user = [] # [ { url: entry }, ... ]
        for url, entry in self.all_entries_by_url.items():
            found = False
            # Look for previously inserted users in list and check if it's the same user
            for entries_per_user in all_entries_per_user:
                # only need to check common usernames in main platforms because we know
                # all platforms have been set for all entries in self.make_entries_consistent
                if entry.has_usernames_in_common(entry.platform, entries_per_user[entries_per_user.keys()[0]]):
                    entries_per_user[url] = entry
                    found = True
                    break
            if not found:
                all_entries_per_user.append({ url: entry })
        # Set other_entries_by_same_user on all entries with multiple entries per user
        for entries_per_user in all_entries_per_user:
            if len(entries_per_user) > 1:
                for url, entry in entries_per_user.items():
                    entry.other_entries_by_same_user = [
                        other_url for other_url in entries_per_user.keys() if other_url != url ]
        return all_entries_per_user

    ############################################################
    # Entries eligibility to win

    def entry_won_this_time(self, entry):
        winners_urls = sum([ winners.keys() for winners in self.winners.values() ], [])
        for url in [ entry.url ] + entry.get('other_entries_by_same_user', []):
            if url in winners_urls:
                return True
        return False

    def entry_is_staff(self, entry):
        for username in entry.site_usernames:
            if username in self.users_by_username:
                if self.users_by_username[username].is_staff:
                    return True
        return False

    def entry_won_before(self, entry):
        for username in entry.site_usernames:
            if username in self.users_who_won_before:
                return True
        return False

    def is_entry_eligible(self, entry):
        """returns eligible True/False and wether or not it's a lower chance to win"""
        if self.entry_won_this_time(entry):
            return False, False
        lower_chance = False
        if self.options.get('lower_chance_for_staff', False):
            if self.entry_is_staff(entry):
                lower_chance = True
        if not lower_chance and self.options.get('lower_chance_for_previous_winners', False):
            if self.entry_won_before(entry):
                lower_chance = True
        return True, lower_chance

    def get_eligible_entries(self):
        eligible_entries = OrderedDict()
        preferred_entries = OrderedDict()
        if self.options.get('one_chance_per_user', False):
            for entries_per_user in self.all_entries_per_user:
                # When there's only one chance per user, we only count the most
                # liked entry as eligible
                entry = self.sort_entries_by_likes(entries_per_user.values())[-1]
                eligible, lower_chance = self.is_entry_eligible(entry)
                if eligible:
                    eligible_entries[entry.url] = entry
                    if not lower_chance:
                        preferred_entries[entry.url] = entry
        else:
            for url, entry in self.all_entries_by_url.items():
                eligible, lower_chance = self.is_entry_eligible(entry)
                if eligible:
                    eligible_entries[url] = entry
                    if not lower_chance:
                        preferred_entries[url] = entry
        return eligible_entries, preferred_entries

    ############################################################
    # Pick winners

    def get_pre_picked_winners(self, winning_urls_or_pks):
        winners = OrderedDict()
        for winning_url_or_pk in winning_urls_or_pks:
            if SITE in self.platforms and winning_url_or_pk.isdigit():
                pk = winning_url_or_pk
                try:
                    url = models.Activity.objects.filter(pk=pk)[0].http_item_url
                except IndexError:
                    print '[Warning] Couldn\'t find activity #{}'.format(pk)
                    url = None
            else:
                url = winning_url_or_pk
            if url is not None:
                winner_entry = self.all_entries_by_url.get(url, None)
                if winner_entry:
                    winners[winner_entry.url] = winner_entry
                else:
                    print '[Warning] Entry {} is not a valid entry'.format(url)
        return winners

    def judges_panel_winners(self):
        return self.get_pre_picked_winners(self.options.get('judges_panel_winners').split(','))

    def random_winners(self):
        return self.get_pre_picked_winners(self.options.get('random_winners').split(','))

    def sort_entries_by_likes(self, entries):
        return sorted(
            entries, key=lambda entry: failSafe(
                lambda: int(entry.get('likes', -1) or 0),
                exceptions=[ ValueError ], default=-1)
        )

    def pick_winners(self, pick_number, pick_function):
        eligible_entries, preferred_entries = self.get_eligible_entries()
        if len(preferred_entries) < len(eligible_entries):
            print '{} eligible entries, but we will pick from {} preferred entries'.format(
                len(eligible_entries), len(preferred_entries),
            )
        if pick_number <= len(preferred_entries):
            pick_from = preferred_entries
        else:
            pick_from = eligible_entries
            if pick_number <= len(eligible_entries):
                print '[Warning] Not enough eligible entries, some winners will be picked from the lower chance bucket'
            else:
                print '[Warning] Not enough eligible entries, picking', len(eligible_entries), 'instead of', pick_number, 'entries'
                pick_number = len(eligible_entries)
        winners = OrderedDict()
        for i in range(0, pick_number):
            winner_url = pick_function(pick_from)
            winner_entry = pick_from[winner_url]
            del(pick_from[winner_url])
            winners[winner_url] = winner_entry
        return winners

    def pick_random_winners(self):
        def _pick_random_winner(pick_from):
            return random.choice(pick_from.keys())
        return self.pick_winners(self.options['pick_random_winners'], _pick_random_winner)

    def pick_likes_winners(self):
        def _pick_likes_winner(pick_from):
            entries = list(pick_from.values())
            random.shuffle(entries) # in case multiple entries have the same number of likes
            return self.sort_entries_by_likes(entries)[-1].url
        return self.pick_winners(self.options['pick_likes_winners'], _pick_likes_winner)

    ############################################################
    # Markdown post

    def get_platform_name(self, platform):
        platform_name = {
            SITE: settings.SITE_NAME,
            'instagram': 'Instagram',
            'twitter': 'Twitter',
            'tiktok': 'TikTok',
        }.get(platform, None)
        if not platform_name:
            try:
                platform_name = models.UserLink.get_verbose_i('type', platform)
            except KeyError:
                platform_name = toHumanReadable(platform)
        return platform_name

    def make_markdown_post(self):
        grid_instance = None
        if self.options.get('grid_per_line', None):
            images = [
                entry.image
                for entry in self.all_entries_by_url.values()
                if entry.get('image', None)
            ]
            if images:
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
                badge_image=self.badge_image,
                upload=True,
                model=models.UserImage,
                with_padding=200,
                width=200,
            )
            badge_instance._thumbnail_image = badge_instance.image
            badge_instance.save()

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

        total_winners = sum(len(v) for v in self.winners.values())
        if total_winners:
            if self.options.get('stretch_goals', False) and self.totals:
                print u'## **Stretch goals reached!**'
                print ''
            print u'With a total of {}{} participants, we are proud to announce that there will be {} winner{}!'.format(
                u'{} participating entries by '.format(
                    self.totals['all']) if self.totals['all'] != self.totals['unique'] else '',
                self.totals['unique'],
                total_winners,
                's' if total_winners > 1 else '',
            )
            print ''
            print 'And the winner{}...'.format('s are' if total_winners > 1 else ' is')
            print ''
            for category, category_winners in self.winners.items():
                for url, entry in category_winners.items():
                    suffix = ''
                    if len(self.platforms) > 1 or self.platforms[0] != SITE:
                        suffix = u' on {}'.format(self.get_platform_name(entry.platform))
                    if entry.site_usernames:
                        print u'## **[{username}]({url})**{suffix}'.format(
                            username=entry.site_usernames[0],
                            url=entry.site_profile_urls[0],
                            suffix=suffix,
                        )
                    else:
                        print u'## **[{username}]({url})**{suffix}'.format(
                            username=entry.usernames[0],
                            url=entry.profile_urls[0],
                            suffix=suffix,
                        )
                    print ''
                    if category == 'judges_panel':
                        print '*Awarded by our [panel of judges](https://goo.gl/forms/42sCU6SXnKbqnag23)*'
                    elif category == 'likes':
                        if failSafe(lambda: int(entry.get('likes', 0) or 0), default=0) > 1:
                            print '*Selected by the community with {} likes*'.format(entry['likes'])
                        else:
                            print '*Selected based on popularity.*'
                    elif category == 'random':
                        print '*Selected randomly, one chance per {}*'.format(
                            'user' if self.options.get('one_chance_per_user', False) else 'entry')
                    print ''
                    print u'↳ [See entry]({})'.format(url)
                    print ''
                    if entry.get('image', None):
                        print '![winning entry image]({})'.format(entry.image)
                        print ''
                    if category == 'judges_panel':
                        print 'INSERT JUDGES COMMENTS HERE!!'
                        print ''
            print ''
            print '## **Congratulations to our winner{}!**'.format('s' if total_winners > 1 else '')
            print ''
            print 'They will be able to pick their prize between:'
            print ''
            if self.options.get('prizes_image', None):
                print '![Prizes]({})'.format(self.options['prizes_image'])
                print ''
            if self.options.get('physical_prizes', False):
                print '- 1 {} physical prize (official merch)'.format(unicode(settings.GAME_NAME))
            print '- 1 {} art commission'.format(unicode(settings.GAME_NAME))
            print '- 1 {} graphic edit commission'.format(unicode(settings.GAME_NAME))
            print ''
            print '*Subject to availability*'
            print ''
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
        if self.totals['all'] != self.totals['unique']:
            print '# **All eligible entries**'
        else:
            print '# **All participants**'
        print ''
        for platform, entries in self.all_entries_by_platform.items():
            if self.totals[platform] < 1:
                continue
            if len(self.platforms) > 1:
                print u'On {}{}:'.format(
                    self.get_platform_name(platform), u' ({})'.format(self.totals[platform])
                    if platform in self.totals else '')
            print andJoin([
                u'[{}]({})'.format(entry.usernames[0], url)
                for url, entry in entries.items()
            ])
            print ''
        if self.totals['all'] != self.totals['unique']:
            print '# **All participants**'
            print ''
            l = []
            for entries_per_user in self.all_entries_per_user:
                if len(entries_per_user) > 1:
                    platforms = listUnique([ entry.platform for entry in entries_per_user.values() ])
                    ll = []
                    entry = entries_per_user.values()[0]
                    if (len(platforms) > 1 or len(self.platforms) == 1):
                        u = '[{}]({}):'.format(entry.usernames[0], entry.profile_urls[0])
                    else:
                        u = '[{} on {}]({}):'.format(
                            entry.usernames[0], self.get_platform_name(entry.platform), entry.profile_urls[0],
                        )
                    for i, (url, entry) in enumerate(entries_per_user.items()):
                        if len(platforms) > 1:
                            ll.append(u'[{} on {}]({})'.format(
                                ordinalNumber(i + 1),
                                self.get_platform_name(entry.platform),
                                url,
                            ))
                        else:
                            ll.append(u'[{}]({})'.format(ordinalNumber(i + 1), url))
                    l.append(u'{} {}'.format(u, andJoin(ll)))
                elif len(self.platforms) > 1:
                    url, entry = entries_per_user.items()[0]
                    l.append(u'[{} on {}]({})'.format(
                        entry.usernames[0], self.get_platform_name(entry.platform), url))
                else:
                    url, entry = entries_per_user.items()[0]
                    l.append(u'[{}]({})'.format(entry.usernames[0], entry.url))
            for participant in l:
                print '- {}'.format(participant)
            print ''

    def find_site_user_from_platform(self, platform, username):
        try:
            return models.UserLink.objects.filter(
                i_type=platform, value=username,
            ).select_related('owner', 'owner__preferences')[0].owner
        except IndexError:
            return None

    def add_badges(self):
        print '# ADD BADGES'
        badge = models.Badge.objects.get(id=self.options['add_badges'])
        self.badge_image = badge.image
        badge_base_name = badge.name.replace(' - Participant', '').replace(' - Winner', '')
        existing_badges = list(models.Badge.objects.filter(
            name__startswith=badge_base_name,
        ).select_related('user', 'user__preferences'))
        cant_get_badge = {
            platform: {}
            for platform in self.platforms
        }
        badges_added = OrderedDict()
        badges_updated = OrderedDict()
        users_already_handled = []

        def _add_badge(entry, winner_position=None):
            if not entry.site_usernames:
                cant_get_badge[entry.platform][entry.usernames[0]] = entry
                return
            for username in entry.site_usernames:
                if username in users_already_handled:
                    return
                users_already_handled.append(username)
                # Rank and badge name
                if winner_position is not None:
                    rank = models.Badge.position_to_rank(winner_position)
                    name = badge_base_name + u' - Winner'
                else:
                    rank = None
                    name = badge_base_name + u' - Participant'
                # Check for existing badge
                try:
                    existing_badge = next(
                        existing_badge for existing_badge in existing_badges
                        if existing_badge.user.username == username
                    )
                except StopIteration:
                    existing_badge = None
                if existing_badge:
                    existing_badge.name = name
                    existing_badge.rank = rank
                    existing_badge.url = entry['url']
                    existing_badge.image = badge.image
                    existing_badge.m_description = badge.m_description
                    existing_badge._cache_description = badge._cache_description
                    existing_badge.save()
                    badges_updated[username] = entry['url']
                    return
                # Add badge
                user = self.users_by_username.get(username, None)
                if not user:
                    cant_get_badge[entry.platform][username] = entry
                    return
                models.Badge.objects.create(
                    owner=badge.owner,
                    user=user,
                    show_on_top_profile=badge.show_on_top_profile,
                    show_on_profile=badge.show_on_profile,

                    name=name,
                    rank=rank,
                    url=entry.url,
                    image=badge.image,
                    m_description=badge.m_description,
                    _cache_description=badge._cache_description,
                )
                user.preferences.force_update_cache('tabs_with_content')
                badges_added[username] = entry.url

        winner_position = 1
        winners_urls = []
        for category, category_winners in self.winners.items():
            for winner_url, winner_entry in category_winners.items():
                _add_badge(winner_entry, winner_position=winner_position)
                winners_urls.append(winner_url)
                winner_position += 1
        for url, entry in self.all_entries_by_url.items():
            if url not in winners_urls:
                _add_badge(entry, winner_position=None)

        if badges_added:
            print 'Badges added:', andJoin(badges_added.keys())
        if badges_updated:
            print 'Badges updated:', andJoin(badges_updated.keys())
        if self.options.get('list_missing_badges'):
            print 'Couldn\'t add badges to:'
            print json.dumps(cant_get_badge, indent=4)
        else:
            print 'Could\'t give badges to:', andJoin([
                u'@{} on {}'.format(entry.usernames[0], platform)
                for platform, entries in cant_get_badge.items()
                for entry in entries.values()
            ])

    def print_table(self, all_entries):
        headers = [
            'Platform',
            'URL',
            'Image',
        ]
        for platform in self.platforms:
            headers += [
                u'{} username'.format(platform.title()),
                u'{} profile URL'.format(platform.title()),
            ]
        rows = [
            headers,
        ]
        for platform, entries in all_entries.items():
            for entry in entries:
                rows.append([
                    entry.get(titleToSnakeCase(header), '') or ''
                    for header in headers
                ])
        print ''
        for row in rows:
            print u'\t'.join([ u','.join(col) if isinstance(col, list) else col for col in row ])
        print ''

    def handle(self, *args, **options):
        self.options = options
        all_entries = {}

        # Get the list of platforms
        self.platforms = []
        if options.get('instagram', None):
            self.platforms.append('instagram')
        if options.get('twitter', None):
            self.platforms.append('twitter')
        if options.get(SITE, None):
            self.platforms.append(SITE)
        if options.get('csv', None):
            self.platforms += self.get_platforms_from_csv()

        # Get entries for each platform
        if options.get('instagram', None):
            all_entries['instagram'] = self.get_instagram_entries()
        if options.get('twitter', None):
            all_entries['twitter'] = self.get_twitter_entries()
        if options.get(SITE, None):
            all_entries[SITE] = self.get_site_entries()
        if options.get('csv', None):
            self.get_csv_entries(all_entries)
        self.all_entries_by_platform = self.get_all_entries_by_platform(all_entries)

        # Make entries consistent (it also sets self.users_by_username)
        self.make_entries_consistent()

        # Check who won before
        self.users_who_won_before = self.get_users_who_won_before()

        # Set entries variables
        # all_entries_by_platform { platform: { url: entry } }
        self.all_entries_by_url = self.get_all_entries_by_url()
        # all_entries_by_url { url: entry }
        self.all_entries_per_user = self.get_entries_per_user()
        # all_entries_per_user [ { url: entry } ]

        # Totals
        self.totals = {
            platform: len(entries)
            for platform, entries in self.all_entries_by_platform.items()
        }
        self.totals['all'] = sum(self.totals.values())
        self.totals['unique'] = len(self.all_entries_per_user)

        # Print entries
        print '# ALL ENTRIES'
        print json.dumps(self.all_entries_by_platform, indent=4)
        if self.options.get('print_table', False):
            self.print_table(all_entries)
        print ''
        print 'TOTAL'
        print json.dumps(self.totals, indent=4)
        print '  ---  '
        print ''

        # Pick winners
        self.winners = OrderedDict([
            ('judges_panel', OrderedDict()),
            ('likes', OrderedDict()),
            ('random', OrderedDict()),
        ])
        # Pre-picked:
        # -> Judges panel (pre-picked)
        if options.get('judges_panel_winners', None):
            self.winners['judges_panel'].update(self.judges_panel_winners())
        # -> Random (pre-picked)
        if options.get('random_winners', None):
            self.winners['random'].update(self.random_winners())
        # Pick now:
        # -> Pick likes
        if options.get('pick_likes_winners', None):
            self.winners['likes'].update(self.pick_likes_winners())
        # -> Pick random
        if options.get('pick_random_winners', None):
            self.winners['random'].update(self.pick_random_winners())

        print '# WINNERS'
        for category, winners in self.winners.items():
            if winners:
                print '  ', toHumanReadable(category)
                for winner_url in winners.keys():
                    print '    ', winner_url
        print '  ---  '
        print ''

        # Add badges
        if options.get('add_badges', None):
            self.add_badges()

        # Make markdown post
        if options.get('make_markdown_post', False):
            self.make_markdown_post()
