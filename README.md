![MagiCircles](http://i.imgur.com/aRdFuUE.png)

MagiCircles
=====

MagiCircles is a web framework based on Django to build video game collections databases and social network websites similar to [School Idol Tomodachi](http://schoolido.lu/#aboutsukutomoModal).

It's open source and open for contributions.

If you plan to create your own website using MagiCircles, you might want to know that you won't be able to monetize it, and it's probably easier for you if you join the MagiCircles family.

Join the MagiCircles family
----------------

We have a group of over 150 people who all work together to maintain and grow websites made with MagiCircles.

If you want to start a website with MagiCircles, we recommend you to join us:
- [The author of MagiCircles](http://db0.company) will help you develop it. No matter your level in programming, we'll make sure we get things done together.
- You'll be allowed to ask our teams of artists and designers to help you with the design of your website, as well as future graphic needs once the website starts.
- Our team of translators will translate the website for you.
- You won't need to worry about hosting the website and administrate its server and infrastructure.
- You won't need to worry about covering the server(s) cost.
- If the MagiCircles can afford it, you may be able to organize giveaways and games, which costs will be covered by the MagiCircles family.
- You'll have opportunities to meet great people who might even want to join your staff team to help you grow and maintain your website.

### [→ Join the MagiCircles family ←](https://goo.gl/forms/EDS5mAZ0eevGlpF82)

#### Not interested?

[The author of MagiCircles](http://db0.company) needs to monetize the platforms, pay for the servers and pay for the development time needed to make these websites and this framework available.

For this reason, it is not allowed to monetize your website if you are using MagiCircles yourself, outside of the MagiCircles family. Only [the author of MagiCircles](http://db0.company) is allowed to monetize websites that use MagiCircles, except when given excplicit authorization.

2 MagiCollections are provided in MagiCircles, but disabled by default: `BadgeCollection` and `DonateCollection`. Both are used to monetize the websites, and you are therefore not allowed to enable them if you are not part of the MagiCircles family.

Similarly, it is not allowed to monetize a website that uses MagiCircles using any other method, including but not limited to:
- advertisment on the website itself and any other platforms that depend on the website,
- receiving money donations within the website or using an external platform for the website itself,
- activating advertisments on disqus,
- raising funds from any kind of events or campaign,
- receiving cards or special codes that can be exchanged for money as part of the website,
- receiving money for the website.

Quick start
------

This section allows you to get a website up and running in a few minutes. If you'd like to get a better understanding of how to set up a new MagiCircles website, skip this section and follow the section ⎡[Start a new website](#start-a-new-website)⎦ instead.

1. Install some requirements:

    - Debian, Ubuntu, and variants:

      ```
      apt-get install libpython-dev libffi-dev python-virtualenv libmysqlclient-dev libssl-dev nodejs npm
      ```

    - Arch:

      ```
      pacman -S libffi python-virtualenv libmysqlclient libssl nodejs npm
      ```

    - OS X (install [brew](https://brew.sh/) if you don't have it):

      ```
      brew install python node
      sudo pip install virtualenv
      ```

2. Create a GitHub repository and copy the URL:

   ```
   GITHUB=git@github.com:SchoolIdolTomodachi/Hello.git
   ```

3. Pick a shortname for your website.

   ```
   PROJECTNAME='hello'
   ```

4. Copy the content of the folder called `sample_project` to your project:


```
git clone ${GITHUB}
git clone -b MagiCircles2 https://github.com/SchoolIdolTomodachi/MagiCircles.git
GITFOLDER=`echo ${GITHUB} | rev | cut -d/ -f1 | rev | cut -d. -f1`
cp -r MagiCircles/sample_project/* ${GITFOLDER}/
cp -r MagiCircles/sample_project/.bowerrc ${GITFOLDER}/
cp -r MagiCircles/sample_project/.gitignore ${GITFOLDER}/
cd ${GITFOLDER}/
```

5. Rename the files and recursively replace the string `sample` with your shortname:

   ```
   mv sample ${PROJECTNAME}
   mv sample_project ${PROJECTNAME}_project
   mv ${PROJECTNAME}/static/img/sample.png ${PROJECTNAME}/static/img/${PROJECTNAME}.png
   for f in `grep -rl sample . | \grep -v '.git/' | \grep -E '.py$|.json$|.bowerrc$|.gitignore$'`; do echo $f; sed -i '' -e "s/sample/${PROJECTNAME}/g" $f; done
   ```

6. Setup your local python working environment, install the dependencies and run your first website:

   ```
   virtualenv env
   source env/bin/activate
   pip install -r requirements.txt
   python manage.py makemigrations ${PROJECTNAME}
   python manage.py migrate
   bower install
   python manage.py runserver
   ```
   
   ![](http://i.imgur.com/8CfckKj.png)

7. Commit your changes

```
git add .gitignore .bowerrc bower.json manage.py requirements.txt ${PROJECTNAME} ${PROJECTNAME}_project
git commit -m "Getting started with MagiCircles2"
git push
```

Start a new website
-----------

The [Quick Start](#quick-start) section above will do all this for you, but feel free to follow this instead if you want to understand how MagiCircles works in more details.

1. Pick a shortname for your website.
 - Example: `frgl` for [fr.gl](http://fr.gl/).
 - Everytime you see "sample" in the following instructions, replace it with this name.

2. Start a django project (the `_project` is important):
   ```shell
   django-admin startproject sample_project
   cd sample_project
   ```

3. Setup your local python working environment:
   ```shell
   virtualenv env
   source env/bin/activate
   ```

4. Create a file called requirements.txt and add MagiCircles as a requirement:
   ```txt
   git+https://github.com/SchoolIdolTomodachi/MagiCircles.git
   ```

5. Install the requirements:
   ```shell
   pip install -r requirements.txt
   ```

6. Create the app:
   ```shell
   python manage.py startapp sample
   ```

7. Edit `sample_project/settings.py` to specify your site name, add the following installed apps and middlewares, and some configuration:
   ```python
   SITE = 'sample'
   
   INSTALLED_APPS = (
     ...
     'corsheaders',
     'bootstrapform',
     'bootstrap_form_horizontal',
     'rest_framework',
     'storages',
     'web',
   )

   MIDDLEWARE_CLASSES = (
     ...
       'django.middleware.locale.LocaleMiddleware',
       'corsheaders.middleware.CorsMiddleware',
       'django.middleware.common.CommonMiddleware',
       'web.middleware.languageFromPreferences.LanguageFromPreferenceMiddleWare',
       'web.middleware.httpredirect.HttpRedirectMiddleware',
   )
   
   FAVORITE_CHARACTERS = []
   
   MAX_WIDTH = 1200
   MAX_HEIGHT = 1200
   MIN_WIDTH = 300
   MIN_HEIGHT = 300

   AUTHENTICATION_BACKENDS = ('web.backends.AuthenticationBackend',)

   DEBUG_PORT = 8000

   from django.utils.translation import ugettext_lazy as _

   LANGUAGES = (
     ('en', _('English')),
     ('es', _('Spanish')),
     ('fr', _('French')),
     ('de', _('German')),
     ('it', _('Italian')),
     ('ru', _('Russian')),
   )

   LANGUAGE_CODE = 'en'

   LOCALE_PATHS = [
     os.path.join(BASE_DIR, 'web/locale'),
   ]

   STATIC_UPLOADED_FILES_PREFIX = None

   CORS_ORIGIN_ALLOW_ALL = True
   CORS_URLS_REGEX = r'^/api/.*$'

   LOGIN_REDIRECT_URL = '/'
   LOG_EMAIL = 'emails-log@schoolido.lu'
   PASSWORD_EMAIL = 'password@schoolido.lu'
   AWS_SES_RETURN_PATH = 'contact@schoolido.lu'

   try:
       from generated_settings import *
   except ImportError, e:
       pass
   try:
       from local_settings import *
   except ImportError, e:
       pass

   INSTALLED_APPS = list(INSTALLED_APPS)
   INSTALLED_APPS.append(SITE)

   LOCALE_PATHS = list(LOCALE_PATHS)
   LOCALE_PATHS.append(os.path.join(BASE_DIR, SITE, 'locale'))

   if STATIC_UPLOADED_FILES_PREFIX is None:
       STATIC_UPLOADED_FILES_PREFIX = 'web/static/uploaded/' if DEBUG else 'u/'
   ```

10. Include the URLs in `sample_project/urls.py`:
   ```python
   urlpatterns = patterns('',
     url(r'^', include('web.urls')),
     ...
   )
   ```

11. Create the file `sample/settings.py` that will describe how you want your website to look like:
   ```python
   from django.conf import settings as django_settings
   from web.default_settings import DEFAULT_ENABLED_COLLECTIONS, DEFAULT_ENABLED_PAGES
   from sample import models, forms

   SITE_NAME = 'Sample Website'
   SITE_URL = 'http://sample.com/'
   SITE_IMAGE = 'sample.png'
   DISQUS_SHORTNAME = 'sample'
   SITE_STATIC_URL = '//localhost:{}/'.format(django_settings.DEBUG_PORT) if django_settings.DEBUG else '//i.sample.com/'
   GAME_NAME = 'Sample Game'
   ACCOUNT_MODEL = models.Account
   COLOR = '#4a86e8'
   ```

12. Save your logo in `sample/static/img/sample.png`, the default avatar for your users in `sample/static/img/avatar.png` and an illustration of the game in `sample/static/img/game.png`

13. Create a django model in `sample/models.py` that will contain the info about the users game accounts:
   ```python
   from django.contrib.auth.models import User
   from django.utils.translation import ugettext_lazy as _
   from django.db import models
   from web.item_model import ItemModel

   class Account(ItemModel):
       collection_name = 'account'
       
       owner = models.ForeignKey(User, related_name='accounts')
       creation = models.DateTimeField(auto_now_add=True)
       level = models.PositiveIntegerField(_("Level"), null=True)

       def __unicode__(self):
           return u'#{} Level {}'.format(self.id, self.level)
   ```
   Note: This model *must* contain an owner and its `related_name` *must* be `accounts`.

   Make this model available in your administration, edit `sample/admin.py`:
   ```python
   from django.contrib import admin
   from sample import models

   admin.site.register(models.Account)
   ```

15. Create the template to display an account in the leaderboard in `sample/templates/items/accountItem.html` (note: owner and owner.preferences in account item have been prefetched in the default queryset):
   ```html
   {% load web_tags %}
   {% with account=item %}
   <br>
   <div class="well">
     <a href="{{ account.owner.item_url }}">
       <div class="row">
         <div class="col-md-2">{% include 'include/avatar.html' with av_user=account.owner av_size=30 av_image_size=100 %}</div>
         <div class="col-md-8"><h3>{{ account.owner.username }}</h3></div>
         <div class="col-md-2"><h3 class="text-right">{{ account.level }}</h3></div>
       </div>
     </a>
   </div>
   {% endwith %}
   ```

16. Create the template that will display the accounts under the users info in their profiles in `sample/templates/accountsForProfile.html`:
   ```html
   {% for item in profile_user.all_accounts %}
   {% include 'items/accountItem.html' %}
   {% endfor %}
   ```
   In a real website, you would probably want to display the account differently in the context of the profile.

17. Create your LESS main file in `sample/static/less/style.less`:
   ```css
   @import "main.less";
   @import "mixins/buttons.less";
   @import "mixins/a.less";

   @mainColor: #4a86e8;
   @secondaryColor: #f5f07b;

   html {
       .setup-sidebar(@mainColor);
       .magicircles(@mainColor, @secondaryColor);
   }
   ```
   You may customize the content depending on the page you're on using `body.current-page` where page corresponds to the page name (example: `current-index`, `current-card_list`, ...).

18. Create your Javascript main file in `sample/static/js/main.js`:
   ```javascript
   // Your functions or code that should load on all pages goes here.
   ```

19. Create your front-end dependencies file in `bower.json`:
   ```json
   {
     "name": "samplewebsite",
     "version": "0.0.0",
     "authors": [
       "db0company <db0company@gmail.com>"
     ],
     "description": "Database and community for Sample Game players.",
     "license": "Simple non code license (SNCL)",
     "dependencies": {
       "Autolinker.js": "0.15.2",
       "CuteForm": "~0.0.3",
       "bootstrap": "~3.3.5",
       "css-hexagon": "0.0.0",
       "github-wiki": "js-github-wiki#*",
       "jquery-visible": "1.2.0",
       "less": "~2.0.0",
       "navbar-variant": "~0.0.0",
       "jquery-easing": "*",
       "jquery-timeago": "timeago#^1.5.4"
     }
   }
   ```
   and the configuration file to specify the folder in `.bowerrc`:
   ```json
   {
       "directory": "sample/static/bower/"
   }
   ```

20. Get the front-end dependencies:
   ```shell
   npm install -g less bower
   bower install
   ```

21. Initialize the translation of the site:
   ```shell
   mkdir sample/locale/
   python manage.py makemessages -l ja --ignore=env/* --ignore=settings.py --ignore=sample_project/sample/settings.py --ignore=web/templates/password/* --ignore=web/django_translated.py
   ```

22. Initialize the models:
   ```shell
   python manage.py makemigrations sample
   python manage.py migrate
   ```

23. Test that the homepage works so far (open [http://localhost:8000/](http://localhost:8000/) in your browser):
   ```shell
   python manage.py runserver
   ```

24. Start setting up your settings, custom pages and collections:
    - See [Site Settings](#site-settings) documentation
    - See [Enabled pages](#enabled-pages) documentation
    - See [Collections](#collections) documentation

25. Before pushing your files to a repository, make sure you don't commit local and generated files with a `.gitignore`:
   ```
   env/
   sample_project/local_settings.py
   sample_project/generated_settings.py
   sample/static/bower
   sample/static/css/style.css
   sample/templates/pages/map.html
   sample/static/uploaded/
   collected/
   db.sqlite3
   ```
   Those are in addition to usual python ignored files. You can get a basic `.gitignore` when you create a GitHub repository).

Create an admin or staff
========================

All users, including administrators (= superuser) or staff, need to be created using the sign up form in the website.

After your user has been created, you may change it to super administrator by doing so:

```shell
python manage.py shell
```

```python
from web import models
username='YOURUSERNAME'

# Set as super user
models.User.objects.filter(username=username).update(is_superuser=True, is_staff=True)

# Or set as staff
models.User.objects.filter(username=username).update(is_staff=True)
```

Site Settings
===

Your settings file is located in `sample/settings.py`.

| Setting | About | Default value |
|---------|-------|---------------|
| NAVBAR_ORDERING | 
| SITE_NAME | Full name of the site (can be different from `SITE` in django settings) ("Sample Website") | *required* |
| SITE_URL | Full URL of the website, ends with a `/` ("http://sample.com/") | *required* |
| SITE_IMAGE | Path of the image in `sample/static/img` folder ("sample.png"). This image is used as the main illustration of the website, shared on social media. It is recommended to avoid transparency in this image.  | *required* |
| SITE_STATIC_URL | Full URL of the static files (images, javascript, uploaded files), differs in production and development, ends with a `/` ("//i.sample.com/") | *required* |
| GAME_NAME | Full name of the game that the site is about ("Sample Game") | *required* |
| DISQUS_SHORTNAME | Go to [Disqus](https://disqus.com/admin/create/) to create a new site and provide the shortname of your new site here. It will be used to display comment sections under some of your pages or collections. :warning: Make sure you disable adertisments in your disqus site settings! | *required* |
| ACCOUNT_MODEL | Your custom model to handle game accounts (`models.Account`) | *required* |
| COLOR | The dominant hex color of the site, must be the same than @mainColor in LESS ("#4a86e8") | *required* |
| SITE_DESCRIPTION | Slogan, catch phrase of the site. May be a callable that doesn't take any argument (`lambda: _('Best database for best game')`) | "The {game name} Database & Community" |
| SITE_LOGO | Path of the image displayed on the homepage. | value of SITE_IMAGE |
| SITE_NAV_LOGO | Path of the image displayed instead of the site name in the nav bar | None |
| EMAIL_IMAGE | Path of the image in `sample/static/img` folder ("sample.png") that will appear at the beginning of all the emails. | value of SITE_IMAGE |
| ENABLED_NAVBAR_LISTS | See [Navbar Links](#navbar-links) documentation | |
| ENABLED_PAGES | See [Enabled pages](#enabled-pages) documentation | |
| SHOW_TOTAL_ACCOUNTS | On profiles, show or hide the total number of accounts before showing the accounts | True |
| GITHUB_REPOSITORY | Tuple (Username, repository) for the sources of this site, used in about page | ('SchoolIdolTomodachi', 'MagiCircles') |
| WIKI | Tuple (Username, repository) for the GitHub wiki pages to display the help pages | Value of GITHUB_REPOSITORY |
| BUG_TRACKER_URL | Full URL where people can see issues (doesn't have to be github) | Full URL created from the GITHUB_REPOSITORY value |
| CONTRIBUTE_URL | Full URL of the guide (or README) for developers who would like to contribute | [link](https://github.com/SchoolIdolTomodachi/SchoolIdolAPI/wiki/Contribute) |
| CONTACT_EMAIL | Main contact email address | Value in django settings `AWS_SES_RETURN_PATH` |
| CONTACT_REDDIT | Contact reddit username | "db0company" |
| CONTACT_FACEBOOK | Contact Facebook username or page | "db0company" |
| TWITTER_HANDLE | Official Twitter account of this site | "schoolidolu" |
| HASHTAGS | List of hashtags when sharing on Twitter + used as keywords for the page (without `#`) | [] |
| ABOUT_PHOTO | Path of the image in `sample/static/img` folder | "engildeby.gif" |
| EMPTY_IMAGE | Path of the image for empty values in cute form in `sample/static/img` folder | "empty.png" |
| TRANSLATION_HELP_URL | URL with guide or tools to allow people to contribute to the site's translation | [link](https://github.com/SchoolIdolTomodachi/MagiCircles/wiki/Translate-the-website) |
| FAVORITE_CHARACTERS | List of tuples (id, full name, image path - must be squared image and full url) for each character that can be set as a favorite on users' profiles, if it's in a database it's recommended to use [Generated Settings](#generated-settings) to save them once in a while | None |
| FAVORITE_CHARACTER_TO_URL | A function that will return the URL to get more info about that character. This function takes a link object with value (full name), raw_value (id), image | lambda _: '#' |
| FAVORITE_CHARACTER_NAME | String that will be localized to specify what's a "character". Must contain `{nth}` (example: "{nth} Favorite Idol") | "{nth} Favorite Character" |
| DONATE_IMAGE | Path of the image in DONATE_IMAGES_FOLDER | None |
| GET_GLOBAL_CONTEXT | Function that takes a request and return a context, must call `globalContext` in `web.utils` | None |
| JAVASCRIPT_TRANSLATED_TERMS | Terms used in `gettext` function in Javascript, must contain `DEFAULT_JAVASCRIPT_TRANSLATED_TERMS` in `web.default_settings` | None |
| DONATORS_STATUS_CHOICES | List of tuples (status, full string) for the statuses of donators, statuses must be THANKS, SUPPORTER, LOVER, AMBASSADOR, PRODUCER and DEVOTEE | "Thanks", "Player", "Super Player", "Extreme Player", "Master Player", "Ultimate Player" |
| ACTIVITY_TAGS | List of tuples (raw value, full localizable tag name) for the tags that can be added ao an activity | None |
| USER_COLORS | List of tuples (raw value, full localizable color name, CSS elements name (`btn-xx`, `panel-xx`, ...), hex code of the color) | None |
| LATEST NEWS | A list of dictionaries that should contain image, title, url and may contain hide_title, used if you keep the default index page to show a carousel. Recommended to get this from [Generated Settings](#generated-settings) | None |
| CALL_TO_ACTION | A sentence shown on the default index page to encourage visitors to sign up | _('Join the community!') |
| SITE_LONG_DESCRIPTION | A long description of what the website does. Used on the about page. May be a callable that doesn't take any argument | A long text |
| GAME_DESCRIPTION | A long description of the game. Used on the about game page. | None (just shows game image) |
| GAME_URL | A link to the official homepage of the game. Used on the about game page. | None (just shows game image) |
| TOTAL_DONATORS | Total number of donators (you may use web.tools.totalDonators to save this value in the [generated settings](#generated-settings)) | 2 |
| ON_USER_EDITED | Callback after a user's username or email has been changed, takes request (contains updated request.user) | None |
| ON_PREFERENCES_EDITED | Callback after a user's preferences have been changed, takes request (contains updated request.user.preferences) | None |
| GOOGLE_ANALYTICS | Tracking number for Google Analytics | 'UA-67529921-1' |
| STATIC_FILES_VERSION | A number or string that you can change when you update the css or js file of your project to force update the cache of your users in production | '1' |
| PROFILE_EXTRA_TABS | A dictionary of tab name -> dictionary (name, icon, callback (= js)) to show more tabs on profile (in addition to activities and accounts) | None |

todo

Default pages and collections
===

Some pages and collections are provided by default.

### Default pages

| URL | Enabled by default | Details |
|-----|--------------------|---------|
| / | No | Index page. Can be used when activities are disabled. |
| /login/ | Yes | Login form, only when users are NOT authenticated. |
| /signup/ | Yes | Signup form, only when users are NOT authenticated. |
| /user/{pk}/{username}/ | Yes | Just an alias to the profile page, will just call `item_view`. Useful to have a link to that view in the navbar. |
| /settings/ | Yes | Allow an authenticated user to edit their profile and preferences. |
| /logout/ | Yes | Will logout the current user and redirect to the homepage. No view. |
| /about/ | Yes | About page with a description of the website, the owners, the staff members and credits. |
| /prelaunch/ | Yes | Useful page when `LAUNCH_DATE` is provided in settings. Will display a countdown. |
| /map/ | Yes | A world map of all the users who provided their location. |
| /help/ | Yes | The homepage of the wiki of the website, with FAQ and guides. |
| /help/{wiki_url}/ | Yes | A specific page in the wiki. |
| /twitter_avatar/{twitter}/ | Yes | A handy URL that will redirect to the Twitter avatar URL. |
Ajax:
| URL | Enabled by default | Details |
|-----|--------------------|---------|
| /ajax/about/ | Yes | Ajax version of the about page, see above. |
| /ajax/about_game/ | Yes | An illustration and a short description of the game. Opens as a popup from a link on the homepage when users are not authenticated. |
| /ajax/deletelink/{pk}/ | Yes | Called from the settings page to delete a link without leaving the page. |
| /ajax/likeactivity/{pk}/ | Yes | Called from the activities to like an activity without leaving the page. |
| /ajax/follow/{username}/ | Yes | Called from the profiles to follow a user without leaving the page. |
| /ajax/changelanguage/ | Yes | Triggered from the dropdown to change the language available on all pages. |
| /ajax/moderatereport/{report}/{action}/ | Yes | In staff page to manage reports, allows staff to moderate multiple reports in a row without leaving the page. |
| /ajax/reportwhatwillbedeleted/{report}/ | Yes | A popup shown when a staff member tries to delete a reported item to warn them of all the other items that will be cascadely deleted. |
| /ajax/successedit/ | Yes | A simple page to use on successful edit when ajax is disabled for an item view. |

- Full details of the configuration of each page in: `web/default_settings.py`
- Full details of the implementation of each page in `web/views.py`

### Default collections

| Name | Class | Model | Details |
|------|-------|-------|---------|
| user | UserCollection | User | <ul><li>Reportable.</li><li>ItemView corresponds to the profile.</li><li>AddView is disabled (use signup page instead).</li><li>EditView is staff only, users may edit their profiles using the settings page.</li><li>ListView is enabled but likely to be used mostly when showing followers/following or likes for an activity, in an ajax popup.  |
| activity | ActivityCollection | Activity | <ul><li>Activities posted by the community, with likes and comments.</li><li>Has an empty shortcut that corresponds to the homepage, allowing the homepage to be the list of activities.</li><li> Reportable.</li></ul> |
| account | AccountCollection | `ACCOUNT_MODEL` in settings | <ul><li>Also called "leaderboard", corresponds to the list of accounts.</li><li>That's the page users see to discover other users. It links to the profiles.</li><li>ItemView is enabled but is very likely to be used only in reports view.</li><li>Reportable.</li></ul> |
| notification | NotificationCollection | Notification | <ul><li>Only ListView is enabled.</li><li>Available as a small popup from the nav bar or as a separate page.</li><li>Notifications are generated automatically when something happens that might interest the user.</li></ul> |
| report | ReportCollection | Report | <ul><li>Uses collection types, with types corresponding to reportable collections.</li><li>People who report can see/edit their own reports, but only staff can list all the reports and take actions.</ul> |

- Default collections are in `web/magicollections.py`

### Collections disabled by default

| Name | Class | Model | Details |
|------|-------|-------|---------|
| donate | DonateCollection | DonationMonth | Page with a link to allow user to donate money to support the development and maintenance of the website. Pages to add / edit months allow staff members to keep track of the budget and show a % of funds + all the donators for that month. |
| badge | BadgeCollection | Badge | Badges can be used to show recognition when a member of the community does something. It's mostly used for donators, but can also be used as prizes when participating in a contest or for annual community rewards. |

These 2 collections allow [the author of MagiCircles](http://db0.company) to monetize the platforms, pay for the server and pay for the development time needed to make these websites available.

For this reason, it is not allowed to enable these 2 collections if you are using MagiCircles yourself. Only [the author of MagiCircles](http://db0.company) is allowed to monetize websites that use MagiCircles, except when given excplicit authorization. [Learn more](#join-the-magicircles-family).

### Enable/Disable/Configure default pages and collections

You may enable or disable them at your convenience, or override their default configurations.

Disable a page in `sample/settings.py`:
```python
ENABLED_PAGES = DEFAULT_ENABLED_PAGES
ENABLED_PAGES['help']['enabled'] = False
```

Disable a collection in `sample/magicollections.py`:
```python
from web.magicollections import ReportCollection as _ReportCollection

class ReportCollection(_ReportCollection):
    enabled = False
```

Change something in an existing collection:
```python
from web.magicollections import AccountCollection as _AccountCollection

class AccountCollection(_AccountCollection):
    icon = 'heart'
    
    class ListView(_AccountCollection.ListView):
        show_edit_button = False
```

Collections
===

MagiCircles' most powerful feature is the collections, or "MagiCollections".

Collections should be used to represent game elements such as cards, characters, songs, levels, pokémons, etc, or website elements such as users, activities, reports, etc.

It's super easy to create a collection, and they will automatically provide pages to view, list, add and edit items.

Collections are generally composed of:
- A class that inherits from `ItemModel` that corresponds to django model, with some extra helpers.
  - [See Collections Django models](#collections-django-models)
- A class that inherits from `MagiCollection` that will contain all the configuration.
  - [See MagiCollection objects](#magicollection-objects)
- (Optional) One or more classes that inherit from `MagiForm` that correspond to django forms, with some extra checks.
  - [See MagiForm objects](#magiform-objects)
- (Optional) A class that inherits from `MagiFilter` that correspond to a django form and is used to search / filter results in the list page.
  - [See MagiFilter objects](#magifilter-objects)

## Collections Django models

A MagiCollection always refers to a django model, but all your models aren't necessarily collections.

It's recommended to always use the `ItemModel` class for all your models, because it provides useful helpers.

Models that don't need to be MagiCollections include models used only in pages (see [Enabled pages](#enabled-pages)) or within another MagiCollection that has its own model.

All the django models used in collections MUST:

- **Inherit from ItemModel and provide a name**
  ```python
  from web.item_model import ItemModel

  class Idol(ItemModel):
      collection_name = 'idol'
      ...
  ```
  Thanks to `ItemModel`, you'll have access to some properties on all your objects which are required but might also be useful for you:
  - `collection` will return the associated MagiCollection object (retrieved using the `collection_name`)
  - `collection_title` corresponds to the MagiCollection setting for translated title, for example: `Idol`
  - `collection_plural_name` corresponds to the MagiCollection setting for non-translated plural (example: `idol -> idols`, `activity -> activities`)
  - `item_url`, for example `/idol/1/Nozomi/`
  - `ajax_item_url`, for example `/ajax/idol/1/`
  - `full_item_url`, for example `//sample.com/idol/1/Nozomi/`
  - `http_item_url`, for example `http://sample.com/idol/1/Nozomi/`
  - `edit_url`, for example `/idols/edit/1/`
  - `ajax_edit_url`, for example `/ajax/idols/edit/1/`
  - `report_url`, for example `/idols/report/1/`
  - `image_url`, will return the full url of the `image` field (if any), for example `//i.sample.com/static/uploaded/idols/Nozomi.png`
  - `http_image_url`, will return the full http url of the `image` field (if any), for example `http://i.sample.com/static/uploaded/idols/Nozomi.png`
  - `open_sentence` (translated), for example `Open idol`
  - `edit_sentence` (translated), for example `Edit idol`
  - `delete_sentence` (translated), for example `Delete idol`
  - `report_sentence` (translated), for example `Report idol`

  `image_url` and `http_image_url` will use the `image` field in your model.

  If you have other images in your model, you might want to add `fieldname_url` and `http_fieldname_url`, for example:
  ```python
  from web.utils import uploadItem
  from web.item_model import ItemModel, get_image_url, get_http_image_url

  class Idol(ItemModel):
    background = models.ImageField(upload_to=uploadItem('i'), null=True, blank=True)

    @property
    def background_url(self):
      return get_image_url(self.background)

    @property
    def http_background_url(self):
      return get_http_image_url(self.background)
  ```

- **Have an owner**
  Which means we should be able to do `instance.owner` and `instance.owner_id`.
  It can be an actual model field or returned with `@property` (for both `owner` and `owner_id`), with the exception of the `Account` model that must contain an actual model field `owner`.

   ```python
   class Idol(ItemModel):
     """
     This model has an actual owner field
     """
       owner = models.ForeignKey(User, related_name='idols')

   class Score(ItemModel):
     """
     This model doesn't have an actual owner field but uses @property to return the owner info.
     Note: In that case it's recommended to cache the account in the model.
     """
       account = models.ForeignKey(Account, related_name='scores')

     @property
       def owner(self):
           return self.account.owner

     @property
       def owner_id(self):
           return self.account.owner_id
   ```

- **Overload __unicode__**
  ```python
  class Card(ItemModel):
      name = models.CharField(max_length=100)

      def __unicode__(self):
        return self.name
  ```
  For SEO purposes, try to localize it if you can:
  ```python
  from django.utils.translation import get_language
  
  def __unicode__(self):
    if get_language() == 'ja':
      return self.japanese_name
    return self.name
  ```
  If you want to use the internal cache (see below) in your unicode function, only do it when the object has actually been created, like so:
  ```python
  def __unicode__(self):
      if self.id:
        return u'{name} - {rarity}'.format(name=self.cached_idol.name, rarity=self.rarity)
      return u'{rarity}'.format(rarity=self.rarity)
  ```

- **Use an internal cache for fields in forein keys that are accessed often**
  To avoid extra `JOIN` in your queries (ie `select_related`) which slow down the queries.
  Let's say every time we display a card, we also display the name and age of the idol featured in the card:

   ```python
   from web.utils import AttrDict

   class Card(ItemModel):
       ...
       idol = models.ForeignKey(Idol, related_name='cards')
       ...

       # Cache
       _cache_idol_days = 20
       _cache_idol_last_update = models.DateTimeField(null=True)
       _cache_idol_name = models.CharField(max_length=32, null=True)
       _cache_idol_age = models.PositiveIntegerField(null=True)

       def update_cache_idol(self):
           """
           Recommended to use select_related('idol') when calling this method
           """
           self._cache_last_update = timezone.now()
           self._cache_idol_name = self.idol.name
           self._cache_idol_age = self.idol.age

       def force_cache_idol(self):
           self.update_cache_idol()
           self.save()

       @property
       def cached_idol(self):
           if not self._cache_idol_last_update or self._cache_idol_last_update < timezone.now() - datetime.timedelta(days=self._cache_idol_days):
               self.force_cache_idol()
           return AttrDict({
               'pk': self.idol_id,
               'id': self.idol_id,
               'name': self._cache_idol_name,
               'age': self._cache_idol_age,
           })
   ```

   In your views and templates, when you need to use the name or age of the idol in the card, do the following:

   ```python
   print card.cached_idol.name, card.cached_idol.age
   ```

## MagiCollection objects

Collections available should be configured in `sample/magicollections.py`. It's a class that inherits from `MagiCollection`.

```python
from web.magicollections import MagiCollection
from sample import models

class IdolCollection(MagiCollection):
    queryset = models.Idol.objects.all()
```

For each collection, you may also override the fields and methods. When overriding methods, it's recommended to call its `super`.

- Required settings:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| queryset | Queryset to get the items, don't forget to use `select_related` when you always use fields in foreign key (or use a cache in model). | *required* | models.Card.objects.all() |

- Highly recommended settings:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| title | Localized title for one item, visible for site's users  | Capitalized key | _('Card') |
| plural_title | Localized title for multiple items, visible for site's users | Capitalized key + 's' | _('Cards') |

- Other available settings:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| enabled | Is the collection enabled? When not, it won't be initialized at all and won't be available when getting a collection by name. | True | |
| name | Name of the collection, unique | Lowercased name of the class without `collection` | 'card' |
| plural_name | Multiple items string, used in URLs | key + 's' | 'cards' |
| icon | String name of a [flaticon](#flaticon) that illustrates the collection (used in navbar) | None | 'album' |
| image | Path to image that illustrates the collection (used in navbar + when adding/editing items + when share_image not available) | None | 'card.png' |
| share_image | Path to image people can see when they share the pages of this collection on social media, can be a callable that takes (collection, view, item=None). Can be overriden per view. | Value of image | 'sample_screenshot.png' |
| form_class | Form class to add / edit an item. Can be a method (see below). Can be overriden per view. | AutoForm | IdolForm |
| multipart | Are Add/Edit forms multipart (ie contain files upload)? Can be overriden per view. | 
| navbar_link | Should a link to the list view of this collection appear in the nav bar? | True | |
| navbar_link_title | When `navbar_link` is True, title displayed as a button | Value of plural_title | _('Friends') |
| navbar_link_list | Name of the [nav bar list](#nav-bar-lists) in which the link is going to appear | None | 'more' |
| navbar_link_list_divider_before | When `navbar_link_list` is specific, whould display a divider before the button? | False | |
| navbar_link_list_divider_after | When `navbar_link_list` is specific, whould display a divider after the button? | False | |
| reportable | When the `ReportCollection` is enabled and this is set to `True`, items can be reported. Staff will then be able to review reports and ignore, edit the item or delete it if necessary. | True | |
| report_edit_templates | A dictionary of reasons why a reported item should be edited. The key is a short title for the reason, and the value is a fully detailed message that will be sent to the owner when the item gets edited. Both shouldn't be localized. | {} | ```{ 'Illegal content': 'Something you shared in this activity was illegal so it has been edited.' }```|
| report_delete_templates | A dictionary of reasons why a reported item should be deleted. The key is a short title for the reason, and the value is a fully detailed message that will be sent to the owner when the item gets deleted. Both shouldn't be localized. | {} | ```{ 'Illegal content': 'Something you shared in this activity was illegal so it has been edited.' }```|
| report_allow_edit | Should staff members be allowed to edit a reported item? Otherwise, only administrators will be able to. | True | |
| report_allow_edit | Should staff members be allowed to delete a reported item? Otherwise, only administrators will be able to. | True | |
| types | See [Item Types](#item-types) | | |
| filter_cuteform | See [CuteForm](#cuteform). Can be overriden in ListView, AddView and EditView. | | |

- All collections provide the following properties (not meant to be overriden):

| Key | Value | Example |
|-----|-------|---------|
| add_sentence | Localized sentence you can use for a button to the AddView | 'Add card' |
| edit_sentence | Localized sentence you can use for a button to the EditView | 'Edit card' |


- All collections provide the following tools (not meant to be overriden):

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| get_list_url | Get the URL of the ListView for this collection | ajax=False | URL (string), example: `/cards/` |
| get_add_url | Get the URL of the AddView for this collection | ajax=False, type=None | URL (string), example: `/cards/add/` or `/cards/add/rare/` (with type = `rare`) |

- Available methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| get_queryset | Queryset used to retrieve the item(s). Can be overriden per view. | queryset, parameters, request | Django queryset | The queryset given as parameters |
| form_class | Form class to add / edit an item. Doesn't have to be a method (see above). Can be overriden per view. | request, context | A form class | AutoForm |
| to_fields | [See to_fields dictionary](#to_field-dictionary). |


### Views

For each of your collections, you may enable, disable or configure views. By default, all views are enabled.

- [List view](#list-view): Paginated list of items with filters/search
- [Item view](#item-view): A page with a single item, shows comments for this item
- [Add view](#add-view): Page with a form to add a new item
- [Edit view](#edit-view): Page with a form to edit and delete an item

For each view, you may also override the fields and methods. When overriding methods, it's recommended to call its `super`.

```python
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from web.magicollections import MagiCollection

class IdolCollection(MagiCollection):
    title = _('Idol')
    
    class ListView(MagiCollection.ListView):
        staff_required = True
        
        def check_permissions(self, request, context):
            super(IdolCollection.ListView, self).check_permissions(request, context)
            if request.user.username == 'bad_staff':
                raise PermissionDenied()
```

If you need some logic behind settings that are not methods you can use `@property`:

```python
from web.magicollections import MagiCollection

class IdolCollection(MagiCollection):
    class ListView(MagiCollection.ListView):
        @property
        def default_ordering(self):
            return '-level' if hasattr(self.collection.queryset.model, 'level') else '-id'
```

#### All views

- All views share the following settings (can be overriden):

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| enbabled | Whether the view should be available or not. | True | |
| ajax | Is the view available in ajax? (allow to get just the page content without HTML boilerplate and navigation bar) | True | |
| ajax_callback | String name of a Javascript function to call when the view loaded. | None | 'loadCards' |
| js_files | List of javascript files to include, all files are in `static/js` except if it starts with `bower/` | [] | ['cards.js, 'bower/marked/lib/marked'] |
| shortcut_urls | <ul><li>ListView/AddView: List of URLs</li><li>AddView with types: List or (url, type) or list of URLs</li><li>ItemView/EditView: List of (url, pk) or list of URLs</li></ul> | [] | [('me', 1)] |
| multipart | Are Add/Edit forms multipart (ie contain files upload)? Can be specified in collection. | multipart in collection | True |
| authentication_required | **Permissions:** only when the user is authenticated | <ul><li>ListView/ItemView: False</li><li>AddView/EditView: True</li></ul> | |
| logout_required | **Permissions:** only when the user is NOT authenticated | False | |
| staff_required | **Permissions:** only when the user is authenticated AND part of the staff team | False | |
| owner_only | **Permissions:** only for ItemView/EditView, only when the authenticated user is the owner of the item |<ul><li>ItemView: False</li><li>EditView: True</li></ul> | |

- All views provide the following properties (not meant to be overriden):

| Key | Value | Example |
|-----|-------|---------|
| collection | The MagiCollection object associated with this view | CardCollection() |

- All views share the following methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| get_global_context | Function called to pre-fill the context before the view loads (even before checking for permissions) | request | dictionary | `GET_GLOBAL_CONTEXT` specified in settings for the website. |
| share_image | Image displayed when sharing this view on social media (Facebook, Twitter, etc). Full URL. Can be specified in collection. | context, item=None | String URL | `share_image` in MagiCollection |
| extra_context | Allows you to add extra context, typically for your templates. Called after most of the logic for the view has been executed already. [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L20)  | context | dictionary | Just returns the context |
| get_queryset | Queryset used to retrieve the item(s) | queryset, parameters, request | Django queryset | `get_queryset` in MagiCollection |
| check_permissions | Check if the current user has permissions to load this view | request, context | None, should raise exceptions when the user doesn't have permissions. | Will check permissions depending on the views settings (such as `staff_required`, etc.), and either raise `PermissionDenied` or `HttpRedirectException` |
| check_owner_permissions | Only for ItemView and EditView, will be called after getting the item and check if the current user has permissions to load this view | request, context, item | None, should raise exceptions when the user doesn't have permissions | Will check permissions depending on the view settings (`owner_only`) and either raise `PermissionDenied` or `HttpRedirectException`.

- All views provide the following methods (not meant to be overriden):

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| has_permissions | Calls `check_permissions` and `check_owner_permissions`, catches exceptions and returns True or False | request, context, item=None | True or False |
| get_page_title | Get the title of the page | None | localized string |

#### List view

- List views contain the following settings (can be overriden):

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| filter_form | Django form that will appear on the right side panel and allow people to search / filter. It's recommended to make it inherit from `MagiFilter`. | None (no side bar) | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L8) |
| ajax_pagination_callback | The name of a javascript function to call everytime a new page loads (including the first time) | None | "updateCards" (See [Example](https://gist.github.com/db0company/b9fde532eafb333beb57ab7903e69749#file-magicirclesexamples-js-L1)) |
| item_template | Path of the HTML template in `sample/templates/items/` to display the item (without `.html`) | Collection name + "Item" | "cardItem" |
| before_template | Name of a template to include between the title (if shown) and the add buttons (if any) and results (without `.html`) | None | "include/beforeCards" |
| after_template | Name of a template to include at the end of the list, when the last page loads (without `.html`), if you provide something in `extra_context` for this template, first check `if context['is_last_page']: ...` | None | "include/afterCards" |
| no_result_template | Name of a template to show if there's no results to show, otherwise it will just show "No result" in a bootstrap `alert-info` | None | "include/cardsNoResult" |
| per_line | Number of elements displayed per line (1, 2, 3, 4, 6, 12), make sure it's aligned with the page_size or it'll look weird :s | 3 | |
| col_break | Minimum size of the column so when the screen is too small it only shows one per line, options are 'xs' (never breaks), 'sm' (= 768px), 'md' (= 992px), 'lg' (= 1200px)  | 'md' | |
| page_size | Number of items per page | 12 | |
| show_edit_button | Should a button to edit the item be displayed under the item (if the user has permissions to edit)? Set this to `False` is your template already includes a button to edit the item. | True | |
| authentication_required | Should the page be available only for authenticated users? | False | |
| distinct | When retrieving the items from the database, should the query include a `distinct`? ⚠️ Makes the page much slower, only use if you cannot guarantee that items will only appear once. | False | |
| add_button_subtitle | A button to add an item will be displayed on top of the page, with a subtitle. | _('Become a contributor to help us fill the database') | _('Share your adventures!') |
| show_title | Should a title be displayed on top of the page? If set to `True`, the title will be the `plural_title` in the collection. | False | |
| full_width | By default, the page will be in a bootstrap container, which will limit its width to a maximum, depending on the screen size. You may change this to `True` to always get the full width | False | |
| show_relevant_fields_on_ordering | By default, when an `ordering` is specified in the search bar, the specified ordering field will be displayed under each item (see [to_fields method](#to_field-method)). | True | |
| hide_sidebar | By default, the side bar will be open when you open the page. You may leave it close by default, but keep in mind that it's very unlikely that your users will find it by themselves. | False | |
| filter_cuteform | See [CuteForm](#cuteform). Can be specified in collection. | | |
| default_ordering | String name of a field (only one) | '-creation' | 'level' |

See also: [settings available in all views](#all-views).

- List views contain the following methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| foreach_item | Function called for all the elements about to be displayed, that takes the item position, the item and the context ([example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L23)). If you can, provide a property inside the model's class instead, to avoid an extra loop. | index, item, context | None | None |
| show_add_button | Should a button be displayed at the beginning to let users add new items (if they have the permission to do so)? | request | Boolean | returns `True` |

See also: [methods available in all views](#all-views).

- List views provide the following methods (not meant to be overriden):

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| plain_default_ordering | Transforms the `default_ordering` of the list view into a simple string, without the reverse setting and extra options. Example: `'-level,id'` becomes `'level'`. Used as the pre-selected value in the filter form. | None | string |

See also: [methods available in all views](#all-views).

#### Item view

- Item views contain the following settings (can be overriden):

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| template | Path of the HTML template in `sample/templates/items/` to display the item (without `.html`). May be `default` to use the defaut view with the image on top and the list of fields below it. [See to_fields method](#to_field-method) for more details about the `default` template. | Collection name + "Item" | "cardItem" |
| top_illustration | If the `default` template is used, it will show either the `image` in the object or its name. You may display something else by specifying the path of a HTML template (full path in template folder), without `.html`. | None | `include/topCard` |
| show_edit_button | Should a button to edit the item be displayed under the item (if the user has permissions to edit)? Set this to `False` is your template already includes a button to edit the item. | True | |
| comments_enabled | Should we display a comment section below the item? | True | |

See also: [settings available in all views](#all-views).

- Item views contain the following methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| get_item | How is the item retrieved using the `pk` (=id) provided in the URL? For example, in the URL `/card/12/super-rare-lily/`, `pk` will be `12` | request, pk (in URL) | a dictionary that will be used with the queryset to get a single item | `{ 'pk': pk }` |
| reverse_url | Allows you to have URLs with just a string and find the item with thout, instead of the id. For example, the default URL of a profile is `/user/1/db0/`, but with this, you can make `/user/db0/` and still be able to retrieve the corresponding user, without knowing its id. | string (text in URL, for example if the URL is `/user/tom/`, this will be `'tom'`) | a dictionary that will be used with the queryset to get a single item | None |

See also: [methods available in all views](#all-views).

#### Add view

- Add views contain the following settings (can be overriden):

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| otherbuttons_template | Template path (without `.html`) for extra buttons at the end of the form | None | "include/cardsExtraButtons" |
| after_template | Name of a template to include after the form | None | "include/afterAddCard" |
| savem2m | Should we call save_m2m to save the manytomany items after saving this model? | False | |
| allow_next | Will ignore redirect_after_add and will redirect to what's specified in 'next' if speficied | True | |
| alert_duplicate | Should we display a warning that asks users to check if it doesn't already exist before adding it? | True | |
| back_to_list_button | Should we display a button to go back to the list view at the end of the form? | True | |
| multipart | Should the HTML form allow multipart (uploaded files)? Can be specified in collection. | False | |
| form_class | Form class to add an item. Can be a method (see below). Can be specified in collection. | AutoForm | IdolForm |
| filter_cuteform | See [CuteForm](#cuteform). Can be specified in collection. | | |

See also: [settings available in all views](#all-views).

- Add views contain the following methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| before_save | Function called before the form is saved. Not recommended, overload `save`in your form instead | request, instance, type=None | instance | Just returns the instance |
| after_save | Function called after the form is saved. Not recommended, overload `save`in your form instead | request, instance, type=None | instance | Just returns the instance |
| form_class | Form class to add an item. Doesn't have to be a method (see above). Can be specified in collection. | request, context | A form class | AutoForm |
| redirect_after_add | Where should the user be redirected after the item has been added successfully? | request, item, ajax | URL to redirect to | Redirect to the item view of the item that has been created if the item view is enabled, otherwise to the list view |

See also: [methods available in all views](#all-views).

#### Edit view

- Edit views contain the following settings (can be overriden):

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| otherbuttons_template | Template path (without `.html`) for extra buttons at the end of the form | None | "include/cardsExtraButtons" |
| after_template | Name of a template to include after the form | None | "include/afterAddCard" |
| allow_delete | Should we show a button to delete the item as well? | False | |
| savem2m | Should we call save_m2m to save the manytomany items after saving this model? | False | |
| back_to_list_button | Should we display a button to go back to the list view at the end of the form? | True | |
| multipart | Should the HTML form allow multipart (uploaded files)? Can be specified in collection. | False | |
| form_class | Form class to edit an item. Can be a method (see below). Can be specified in collection. | AutoForm | | filter_cuteform | See [CuteForm](#cuteform). Can be specified in collection. | | |
IdolForm |

See also: [settings available in all views](#all-views).

- Edit views contain the following methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| before_save | Function called before the form is saved. Not recommended, overload `save`in your form instead | request, instance, type=None | instance | Just returns the instance |
| after_save | Function called after the form is saved. Not recommended, overload `save`in your form instead | request, instance, type=None | instance | Just returns the instance |
| form_class | Form class to edit an item. Doesn't have to be a method (see above). Can be specified in collection. | request, context | A form class | AutoForm |
| redirect_after_edit | Where should the user be redirected after the item has been edited successfully? | request, item, ajax | URL to redirect to | Redirect to the item view of the item that has been edited if the item view is enabled, otherwise to the list view |
| redirect_after_delete | Where should the user be redirected after the item has been deleted successfully? | request, item, ajax | URL to redirect to | Redirect to the list view |
| get_item | How is the item retrieved using the `pk` (=id) provided in the URL? For example, in the URL `/card/edit/12/`, `pk` will be `12` | request, pk (in URL) | a dictionary that will be used with the queryset to get a single item | `{ 'pk': pk }` |

See also: [methods available in all views](#all-views).

### CuteForm

todo

### Item types

You may display different forms and URLs to add/edit an item depending on "types".

When you use types on a collection, its model must have a `type` (ie we should be able to do `instance.type`), which can be stored in database or returned with `@property`. It'll be used to retrieve the right form when editing.

For example, let's say we have 3 types of cards: Normal, Rare and Super Rare and we want to use different forms for those. Our collection will look like that:

```python
ENABLED_COLLECTIONS['card'] = {
  ...
  'add': {
     ...
     types: {
       'normal': { ... },
       'rare': { ... },
       'superrare': { ... },
     },
  },
}
```

For each type, you may specify the following settings in its dictionary:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| form_class | FormClass to add/edit the item, must take request (make it inherit from FormWithRequest), can be a function that takes request, context and collection | *required* | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L44) |
| title | Localized title of the type | type (key) | _('Rare') |
| image | Path of an image displayed near the title of the form that illustrates the type | None | "" |

The type will be passed to the formClass when it's initialized, which allows you to reuse the same form class for all your types if you'd like.

## to_fields dictionary

###### to_field method

`to_field` is a method in collections.

- Where is it called?
    - **ListView:** Will be called when `ordering` is specified to show the field(s) details, with `only_fields` in parameters. For example, if you order the list by level, the level is going to be displayed under the item, because it's very likely that you'll want to compare that between the items.
    - **ItemView:** If you use the template `default`, it will show a table with all the fields returned by this function.
- Can it be overriden?
    - You may override this function, but you should always call its `super`.
- Parameters
    - `item, to_dict=True, only_fields=None, in_list=False, icons={}, images={}`
    - `item` is the item object, an instance of an `ItemModel`
    - `to_dict` will return a dict by default, otherwise a list or pair. Useful if you plan to change the order or insert items at certain positions.
    - `only_fields` if specified will ignore any other field
    - `icons` is a dictionary of the icons associated with the fields
    - `images` is a dictionary of the images associated with the fields
- Return value
    - Returns a dictionary of key = field name, value = dictionary with:
        - verbose_name
        - value
        - type
        - optional: icon, image, link, link_text, ajax_link
    - Available types:
        - text
        - title_text (needs 'title')
        - image
        - bool
        - link (needs 'link_text')
        - image_link (needs 'link', 'link_text')
        - button (needs 'link_text')
        - text_with_link (needs 'link' and 'link_text', will show a 'View all' button)
        - timezone_datetime (useful when showing another timezone, otherwise use text. needs 'timezones' list. can be 'local')
        - long_text
        - html
- Default
    - Will automatically guess what should be displayed from the model fields and `reverse`  in the model if specified.

In ListView, when ordering is specified:
![](http://i.imgur.com/AGQhIH2.png)

In ItemView, when template is `default`:

![](http://i.imgur.com/ikMoXCq.png)

## MagiForm

todo

+ mention AutoForm

## MagiFilter

todo

Enabled Pages
===

Unlike a collection, a page corresponds to a standalone page with its own function.

It's recommended to store the templates for your pages in `sample/templates/pages/`.

To add a new page:

```python
ENABLED_PAGES['statistics'] = {
  'title': _('Statistics'),
  ...
}
```

The key corresponds to both the URL and the name of the function.

The function must be in `sample/views.py`. The function must take a request and the url_variables (if any) and return a rendered HTML page.

All your pages must contain the global context, which you can override to add your own global context settings. It's recommended to use the same globalContext function in your views than the one specified in your [site settings](#site-settings).

```python
from web.utils import globalContext as web_globalContext

def globalContext(request):
    context = web_globalContext(request)
    context['something'] = 'something'
    return context

def statistics(request):
    ...
    context = globalContext(request)
    context['statistics_data'] = ...
    return render(request, 'pages/statistics.html', context)
```

For each page, you may specify the following settings:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| title | Localized title of the page (used in navbar and HTML page title) | *required* (except when ajax=True, then None) | _('Statistics') |
| ajax | Is this page only available in AJAX? (URL starts with `ajax/`) | False | |
| icon | String name of a [flaticon](#flaticon) that illustrates the page (used in navbar) | None | 'about' |
| image | Path to image that illustrates the page (used in navbar) | None | 'statistics.png' |
| custom | Is the function for this view in your project (True) or already in MagiCircles (about, settings, etc)? (False) | True | |
| navbar_link | Should a link to the list view of this collection appear in the nav bar? | True | True |
| navbar_link_list | Name of the [nav bar list](#nav-bar-lists) in which the link is going to appear | None | 'more' |
| url_variables | List of tuples (name of the variable, regexp to match the variable in the URL, function that takes a context and returns the value that should be displayed in the navbar - optional when navbar_link = False) | [] | [('pk', '\d+', lambda context: context['request'].user.id)] |

Nav bar lists
===

You might not want all your links to pages and collections to be on the nav bar itself, but in lists instead.

To achieve that, you may specify a `navbar_link_list` in your page or collection settings. It's a string that corresponds to the name of a list.

By default, your site will already contain 2 lists: `you` and `more`.

You may add more lists in your settings:

```python
from web.default_settings import DEFAULT_ENABLED_NAVBAR_LISTS

ENABLED_NAVBAR_LISTS = DEFAULT_ENABLED_NAVBAR_LISTS
ENABLED_NAVBAR_LISTS['stuff'] = { ... }
```

The settings of a navbar list may contain:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| title | Localized name of the list or function that takes the context and return a string | *required* |
| icon | String name of a [flaticon](#flaticon) that illustrates the nav bar list | None | 'fingers' |
| image | Path to image that illustrates the nav bar list | None | 'stuff.png' |

Utils
===

#### Models upload

```python
from web.utils import uploadToRandom, uploadItem

class Idol(ItemModel):
    image = models.ImageField(upload_to=uploadItem('i'))
    other_image = models.ImageField(upload_to=uploadToRandom('i'))    
```

- `uploadItem` will use the `__unicode__` function of the model to name the file, in addition to random characters (to make sure browsers load the latest uploaded images when re-written). It is useful for SEO purposes and recommended for the main collections (cards, characters, ...).
- `uploadRandom` will just generate a random string as the file name. It's only recommended when the `__unicode__` of the model is meaningless or for user-submitted content (activities for example).

#### Access MagiCollections

- From anywhere:
  ```python
  from web.utils import getMagiCollections, getMagiCollection

  print len(getMagiCollections())
  print getMagiCollection('idol').name
  ```
- From an instance of a model (`ItemModel`):
  ```python
  from web import models
  
  user = models.User.objects.get(id=1)
  print user.collection.name
  ```
  (will call `getMagiCollection` using `user.collection_name`)

Both are not recommended, and you'll usually find other ways to get the information you need than by accessing the collection object.

Recommendations
===============

## Calling functions in templates

While Django provides `templatetags`, it is recommended to avoid having too many `load` inside your template, especially when it's likely to be included multiple times (in a forloop for example), because they slow down the generation of the HTML page.

Instead, try to provide as much as possible of the logic behind your template in your python code, and add variables inside your context.

Example:
- Instead of:
  ```html
  {% load mytags %}
  <div>{% get_percent a b %}</div>
  ```
- Do:
  ```python
  context['percent'] = get_percent(a, b)
  ```
  ```html
  <div>{{ percent }}</div>
  ```

## Utility functions for models

It's very likely that you'll need to do something to the fields of your models, and you won't be using most of them as they are stored in the database. In that case, it's recommended to add properties to your model classes.

Example:
- Instead of:
  ```python
  today = datetime.date.today()
  idols = models.Idol.objects.all()
  for idol in idols:
      idol.age = today.year - idol.birthdate.year - ((today.month, today.day) < (idol.birthdate.month, idol.birthdate.day))
  ```
- Do:
  ```python
  class Idol(ItemModel):
      ...
      birthdate = models.DateField(_('Birthdate'))
      
      @property
      def age(self):
          return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))
  ```
  ```html
  {% for idol in idols %}
  <div>{{ idol.age }}</div>
  {% endfor %}
  ```

## Generated Settings

Some values shouldn't be calculated from the database everytime, so it's recommended to write a script in `sample/management/commands/generate_settings.py` that will update the settings and call that script in a cron or a scheduler.

```python
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings as django_settings
from web.tools import totalDonators
from sample import models

def generate_settings():

        print 'Get total donators'
        total_donators = totalDonators()

        print 'Get the latest news'
        current_events = models.Event.objects.get(end__lte=timezone.now())
        latest_news = [{
            'title': event.name,
            'image': event.image_url,
            'url': event.item_url,
        } for event in current_events]

        print 'Get the characters'
        all_idols = model.Idol.objects.all().order_by('name')
        favorite_characters = [(
            idol.pk,
            idol.name,
	    idol.image_url,
        ) for idol in all_idols]

        print 'Save generated settings'
        s = u'\
import datetime\n\
TOTAL_DONATORS = ' + unicode(total_donators) + u'\n\
LATEST_NEWS = ' + unicode(latest_news) + '\n\
FAVORITE_CHARACTERS = ' + unicode(favorite_characters) + '\n\
GENERATED_DATE = datetime.datetime.fromtimestamp(' + unicode(time.time()) + u')\n\
'
        print s
        with open(django_settings.BASE_DIR + '/' + django_settings.SITE + '_project/generated_settings.py', 'w') as f:
            print >> f, s
        f.close()

class Command(BaseCommand):
    can_import_settings = True

    def handle(self, *args, **options):
        generate_settings()
```

And in your `sample/settings.py`, use the generated values:

```python
from django.conf import settings as django_settings

...

TOTAL_DONATORS = django_settings.TOTAL_DONATORS
LATEST_NEWS = django_settings.LATEST_NEWS
FAVORITE_CHARACTERS = django_settings.FAVORITE_CHARACTERS
```

## Avoid generating translation terms for terms already available in Django framework

Every time you add a new term to translate, check if it's not already provided by the Django Framework, to avoid adding more work to our translators when the terms don't need to be transated again.

If it is, add it in or create a file `sample/django_translated.py` like so:

```python
from django.utils.translation import ugettext_lazy as _
from web.django_translated import t

t.update({
    'Japanese': _('Japanese'),
})
```

When you want to use the term, do:
```python
from sample.django_translated import t

print t['Japanese']
```

When generating the terms

## Disable activities

## Disable activities but keep news for staff members

Production Environment
===

1. Create your production settings file in `sample_project/local_settings.py`:
   ```python
   SECRET_KEY = '#yt2*mvya*ulaxd+6jtr#%ouyco*2%3ngb=u-_$44j^86g0$$3'
   DEBUG = False

   AWS_ACCESS_KEY_ID = 'uTFJXQn9zZc9C93qy7rL'
   AWS_SECRET_ACCESS_KEY = 'XceSYgIhLgB1lDTB7T6IydFtK5SD5ZRfPr84syjD'

   DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
   AWS_STORAGE_BUCKET_NAME = 'i.schoolido.lu'

   EMAIL_BACKEND = 'django_ses.SESBackend'
   AWS_SES_REGION_NAME = 'us-east-1'
   AWS_SES_REGION_ENDPOINT = 'email.us-east-1.amazonaws.com'
   from boto.s3.connection import OrdinaryCallingFormat
   AWS_S3_CALLING_FORMAT = OrdinaryCallingFormat()

   BASE_DIR = os.path.dirname(os.path.dirname(__file__))
   STATIC_ROOT = os.path.join(BASE_DIR, 'collected')
   ```

2. Edit your LESS file `sample/static/less/style.less` to use the full paths for dependencies:
   ```css
   @import "../../../env/lib/python2.7/site-packages/web/static/less/main.less";
   @import "../../../env/lib/python2.7/site-packages/web/static/less/mixins/buttons.less";
   @import "../../../env/lib/python2.7/site-packages/web/static/less/mixins/a.less";
   ```

3. Compile the CSS:
   ```shell
   lessc sample/static/less/style.less sample/static/css/style.css
   ```

4. Collect all the static files:
   ```shell
   python manage.py collectstatic
   ```
   Upload the collected files (in `collected`) in your S3 bucket in a `static` folder.

5. Set up a MySQL database and edit your django settings file in `sample_project/local_settings.py`:
   ```python
   DATABASES = {'
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'sampledbname',
           'OPTIONS': {'charset': 'utf8mb4'},
           'USER': 'sampleuser',
           'PASSWORD': 'samplepassword',
           'HOST': 'sample.rds.amazonaws.com',
           'PORT': '3306',
       }
   }
       ```

Flaticon
===

The icons come from [flaticon.com](http://www.flaticon.com/) and are credited in the about page. To get the list of available icons, open your website on `/static/css/flaticon.html`.
