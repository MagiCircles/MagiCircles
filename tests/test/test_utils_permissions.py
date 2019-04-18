from django.test import TestCase
from magi import utils
from magi import models as magi_models
from test import models

class PermissionsTestCase(TestCase):
    def setUp(self):
        self.maxDiff = None

        self.user = models.User.objects.create(id=8888, username='8888')
        self.user.preferences = magi_models.UserPreferences.objects.create(user=self.user)
        self.user.save()

        self.user2 = models.User.objects.create(id=9999, username='9999')
        self.user2.preferences = magi_models.UserPreferences.objects.create(user=self.user2)
        self.user2.save()

        self.user_without_groups = models.User.objects.create(id=7777, username='7777')
        self.user_without_groups.preferences = magi_models.UserPreferences.objects.create(user=self.user_without_groups)
        self.user_without_groups.save()
        self.user_without_groups.preferences.save_c('groups', [])
        self.user_without_groups.preferences.save()

    def test_hasGroup(self):
        self.user.preferences.save_c('groups', ['a_moderator'])
        self.user.preferences.save()
        self.assertEqual(utils.hasGroup(self.user, 'team'), False)
        self.user.preferences.save_c('groups', ['team'])
        self.user.preferences.save()
        self.assertEqual(utils.hasGroup(self.user, 'team'), True)

    def test_hasPermission(self):
        self.user.preferences.save_c('groups', ['team'])
        self.user.preferences.save()
        self.assertEqual(utils.hasPermission(self.user, 'edit_staff_status'), True)
        self.assertEqual(utils.hasPermission(self.user, 'manage_main_items'), False)

    def test_hasOneOfPermissions(self):
        self.user.preferences.save_c('groups', ['team'])
        self.user.preferences.save()
        self.assertEqual(utils.hasOneOfPermissions(self.user, ['edit_staff_status', 'manage_main_items']), True)
        self.assertEqual(utils.hasOneOfPermissions(self.user, ['edit_staff_configurations', 'add_badges']), False)

    def test_hasPermissions(self):
        self.user.preferences.save_c('groups', ['team'])
        self.user.preferences.save()
        self.assertEqual(utils.hasPermissions(self.user, ['edit_staff_status', 'see_profile_edit_button']), True)
        self.assertEqual(utils.hasPermissions(self.user, ['edit_staff_status', 'manage_main_items']), False)

    def test_groupsForAllPermissions(self):
        self.assertDictEqual({
            k: { gn:  g['verbose_permissions'] for gn, g in v.items() }
            for k, v in utils.groupsForAllPermissions(self.user.preferences.GROUPS).items()
        }, {
            'add_badges': {
                'manager':
                 [
                     'Edit roles',
                     'Edit staff status',
                     'Edit donator status',
                     'See profile edit button',
                     'Edit staff configurations',
                     'Add badges',
                     'Edit own staff profile',
                 ],
                'entertainer':
                 [
                     'Edit staff configurations',
                     'Add badges',
                     'Edit own staff profile',
                 ],
            },
            'add_donation_badges': {
                'finance':
                 [
                     'Add donation badges',
                     'Manage donation months',
                     'Edit donator status',
                     'Edit own staff profile',
                 ],
            },
            'advanced_staff_configurations': {
                'developer':
                 [
                     'Advanced staff configurations',
                 ],
                'sysadmin':
                 [
                     'Advanced staff configurations',
                     'Manage main items',
                 ],
            },
            'edit_donator_status': {
                'manager':
                 [
                     'Edit roles',
                     'Edit staff status',
                     'Edit donator status',
                     'See profile edit button',
                     'Edit staff configurations',
                     'Add badges',
                     'Edit own staff profile',
                 ],
                'finance':
                 [
                     'Add donation badges',
                     'Manage donation months',
                     'Edit donator status',
                     'Edit own staff profile',
                 ],
            },
            'edit_own_staff_profile': {
                'a_moderator': ['Edit own staff profile'],
                'cm': ['Edit staff configurations',
                       'Edit own staff profile'],
                'd_moderator': ['Moderate reports',
                                'Edit reported things',
                                'Edit own staff profile'],
                'db': ['Manage main items',
                       'Edit own staff profile'],
                'entertainer': ['Edit staff configurations',
                                'Add badges',
                                'Edit own staff profile'],
                'external_cm': ['Edit own staff profile'],
                'finance': ['Add donation badges',
                            'Manage donation months',
                            'Edit donator status',
                            'Edit own staff profile'],
                'manager': ['Edit roles',
                            'Edit staff status',
                            'Edit donator status',
                            'See profile edit button',
                            'Edit staff configurations',
                            'Add badges',
                            'Edit own staff profile'],
                'support': ['Edit own staff profile'],
                'team': ['Edit staff status',
                         'Edit roles',
                         'See profile edit button',
                         'Edit own staff profile'],
                'twitter_cm': ['Edit own staff profile']},
            'edit_reported_things': {
                'd_moderator':
                 [
                     'Moderate reports', 'Edit reported things',
                     'Edit own staff profile',
                 ],
            },
            'edit_roles': {
                'manager':
                 [
                     'Edit roles',
                     'Edit staff status',
                     'Edit donator status',
                     'See profile edit button',
                     'Edit staff configurations',
                     'Add badges',
                     'Edit own staff profile',
                 ],
                'team':
                 [
                     'Edit staff status',
                     'Edit roles',
                     'See profile edit button',
                     'Edit own staff profile',
                 ],
            },
            'edit_staff_configurations': {
                'manager':
                 [
                     'Edit roles',
                     'Edit staff status',
                     'Edit donator status',
                     'See profile edit button',
                     'Edit staff configurations',
                     'Add badges',
                     'Edit own staff profile',
                 ],
                'cm': [
                    'Edit staff configurations',
                     'Edit own staff profile',
                ],
                'entertainer':
                 [
                     'Edit staff configurations', 'Add badges',
                     'Edit own staff profile',
                 ],
            },
            'edit_staff_status': {
                'manager':
                 [
                     'Edit roles',
                     'Edit staff status',
                     'Edit donator status',
                     'See profile edit button',
                     'Edit staff configurations',
                     'Add badges',
                     'Edit own staff profile',
                 ],
                'team':
                 [
                     'Edit staff status',
                     'Edit roles',
                     'See profile edit button',
                     'Edit own staff profile',
                 ],
            },
            'manage_donation_months': {
                'finance':
                 [
                     'Add donation badges',
                     'Manage donation months',
                     'Edit donator status',
                     'Edit own staff profile',
                 ],
            },
            'manage_main_items': {
                'db': [
                    'Manage main items',
                     'Edit own staff profile',
                ],
                'sysadmin':
                 [
                     'Advanced staff configurations',
                     'Manage main items',
                 ],
            },
            'moderate_reports': {
                'd_moderator':
                 [
                     'Moderate reports', 'Edit reported things',
                     'Edit own staff profile',
                 ],
            },
            'see_profile_edit_button': {
                'manager':
                 [
                     'Edit roles',
                     'Edit staff status',
                     'Edit donator status',
                     'See profile edit button',
                     'Edit staff configurations',
                     'Add badges',
                     'Edit own staff profile',
                 ],
                'team':
                 [
                     'Edit staff status',
                     'Edit roles',
                     'See profile edit button',
                     'Edit own staff profile',
                 ],
            },
            'translate_items': {
                'translator':
                 [
                     'Translate items', 'Translate staff configurations',
                 ],
            },
            'translate_staff_configurations': {
                'translator':
                 [
                     'Translate items',
                     'Translate staff configurations',
                 ],
            }
        })

    def test_allPermissions(self):
        self.assertItemsEqual(utils.allPermissions(self.user.preferences.GROUPS), [
            'advanced_staff_configurations',
            'edit_roles',
            'see_profile_edit_button',
            'add_badges',
            'translate_staff_configurations',
            'edit_staff_status',
            'moderate_reports',
            'edit_donator_status',
            'manage_main_items',
            'translate_items',
            'add_donation_badges',
            'manage_donation_months',
            'edit_reported_things',
            'edit_staff_configurations',
            'edit_own_staff_profile',
        ])

    def test_groupsPerPermission(self):
        self.assertEqual(utils.groupsPerPermission(self.user.preferences.GROUPS, 'edit_roles').keys(), [
            'manager', 'team',
        ])

    def test_groupsWithPermissions(self):
        self.assertItemsEqual(utils.groupsWithPermissions(
            self.user.preferences.GROUPS, ['edit_roles', 'edit_staff_status']).keys(), [
                'manager', 'team',
        ])
        self.assertItemsEqual(utils.groupsWithPermissions(
            self.user.preferences.GROUPS, ['manage_donation_months', 'edit_donator_status']).keys(), [
                'finance',
        ])
        self.assertItemsEqual(utils.groupsWithPermissions(
            self.user.preferences.GROUPS, ['translate_items', 'add_badges']).keys(), [
        ])

    def test_groupsWithOneOfPermissions(self):
        self.assertItemsEqual(utils.groupsWithOneOfPermissions(
            self.user.preferences.GROUPS, ['edit_roles', 'edit_staff_configurations']).keys(), [
                'manager', 'team', 'cm', 'entertainer',
        ])

    def test_usersWithGroup(self):
        self.user.preferences.save_c('groups', ['team', 'translator', 'manager'])
        self.user.preferences.save()
        self.user2.preferences.save_c('groups', ['team', 'translator', 'entertainer'])
        self.user2.preferences.save()
        self.assertItemsEqual([u.username for u in utils.usersWithGroups(models.User.objects, ['team', 'translator'])], [
            '8888',
            '9999',
        ])
        self.assertItemsEqual([u.username for u in utils.usersWithGroups(models.User.objects, ['team', 'manager'])], [
            '8888',
        ])

    def test_usersWithOneOfGroups(self):
        self.user.preferences.save_c('groups', ['team', 'translator', 'manager'])
        self.user.preferences.save()
        self.user2.preferences.save_c('groups', ['team', 'translator', 'entertainer'])
        self.user2.preferences.save()
        self.assertEqual([u.username for u in utils.usersWithOneOfGroups(models.User.objects, ['team', 'manager'])], [
            '8888',
            '9999',
        ])
        self.assertEqual([u.username for u in utils.usersWithOneOfGroups(models.User.objects, ['entertainer'])], [
            '9999',
        ])
        self.assertEqual([u.username for u in utils.usersWithOneOfGroups(models.User.objects, ['developer'])], [
        ])

    def test_usersWithPermission(self):
        self.user.preferences.save_c('groups', ['team', 'translator'])
        self.user.preferences.save()
        self.user2.preferences.save_c('groups', ['translator', 'entertainer'])
        self.user2.preferences.save()
        self.assertEqual([u.username for u in utils.usersWithPermission(
            models.User.objects, self.user.preferences.GROUPS, 'translate_items')], [
                '8888',
                '9999',
            ])
        self.assertEqual([u.username for u in utils.usersWithPermission(
            models.User.objects, self.user.preferences.GROUPS, 'add_badges')], [
                '9999',
            ])

    def test_usersWithPermissions(self):
        self.user.preferences.save_c('groups', ['db', 'translator'])
        self.user.preferences.save()
        self.user2.preferences.save_c('groups', ['translator'])
        self.user2.preferences.save()
        self.assertEqual([u.username for u in utils.usersWithPermissions(
            models.User.objects, self.user.preferences.GROUPS, [
                'manage_main_items',
                'translate_items',
            ])], [
                '8888',
            ])

    def test_usersWithOneOfPermissions(self):
        self.user.preferences.save_c('groups', ['db', 'translator'])
        self.user.preferences.save()
        self.user2.preferences.save_c('groups', ['translator'])
        self.user2.preferences.save()
        self.assertEqual([u.username for u in utils.usersWithOneOfPermissions(
            models.User.objects, self.user.preferences.GROUPS, [
                'manage_main_items',
                'translate_items',
            ])], [
                '8888',
                '9999',
            ])
        self.assertEqual([u.username for u in utils.usersWithOneOfPermissions(
            models.User.objects, self.user.preferences.GROUPS, [
                'manage_main_items',
                'add_badges',
            ])], [
                '8888',
            ])
