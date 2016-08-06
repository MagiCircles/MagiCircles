MagiCircles
=====

MagiCircles is a web framework based on Django to build video game collections databases and social network websites similar to [School Idol Tomodachi](http://schoolido.lu/#aboutsukutomoModal).

It's meant to be used as a full project, not installed in an existing website.

Quick start
-----------

1. Pick a shortname for your site.
 - Example: `frgl` for [fr.gl](http://fr.gl/).
 ```shell
 PROJECTNAME='frgl'
 ```

2. Copy the content of the folder called `sample_project` to your project:
   ```shell
   git clone your_project_repository
   git clone https://github.com/SchoolIdolTomodachi/MagiCircles.git
   cp -r MagiCircles/sample_project/* your_project_repository/
   cp -r MagiCircles/sample_project/.bowerrc your_project_repository/
   cp -r MagiCircles/sample_project/.gitignore your_project_repository/
   cd your_project_repository/
   ```

3. Rename the files and recursively replace the string `sample` with your shortname:
   ```shell
   mv sample ${PROJECTNAME}
   mv sample_project ${PROJECTNAME}_project
   mv ${PROJECTNAME}/static/img/sample.png ${PROJECTNAME}/static/img/${PROJECTNAME}.png
   for f in `grep -l sample . | \grep -v '.git/' | \grep -E '.py$|.json$|.bowerrc$|.gitignore$'`; do echo $f; sed -i '' -e "s/sample/${PROJECTNAME}/g" $f; done
   ```

4. Setup your local python working environment, install the dependencies and run your first site:
   ```shell
   virtualenv env
   source env/bin/activate
   pip install -r requirements.txt
   python manage.py makemigrations ${PROJECTNAME}
   python manage.py migrate
   bower install
   python manage.py runserver
   ```

Start a new site
-----------

1. Pick a shortname for your site.
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

7. Edit `sample_project/settings.py` to specify your site name:
   ```python
   SITE = 'sample'
   ```

8. Edit `sample_project/settings.py` to add the following installed apps and middlewares:
   ```python
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
       'web.middleware.httpredirect.HttpRedirectMiddleware',
   )
   ```

9. Copy paste this at the end of `sample_project/settings.py`:
   ```python
   AUTHENTICATION_BACKENDS = ('web.backends.AuthenticationBackend',)

   DEBUG_PORT = 8000

   from django.utils.translation import ugettext_lazy as _

   LANGUAGES = (
     ('en', _('English')),
     ('es', _('Spanish')),
     ('ru', _('Russian')),
     ('fr', _('French')),
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

11. Create the file `sample/settings.py` that will describe the pages and collections you'd like to enable in your site:
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

   ENABLED_COLLECTIONS = DEFAULT_ENABLED_COLLECTIONS

   ENABLED_COLLECTIONS['account']['add']['form_class'] = forms.AccountForm
   ENABLED_COLLECTIONS['account']['edit']['form_class'] = forms.AccountForm

   ENABLED_PAGES = DEFAULT_ENABLED_PAGES
   ```

12. Save your logo in `sample/static/img/sample.png`, the default avatar for your users in `sample/static/img/avatar.png` and an illustration of the game in `sample/static/img/game.png`

13. Create a django model in `sample/models.py` that will contain the info about the users game accounts:
   ```python
   from django.contrib.auth.models import User
   from django.utils.translation import ugettext_lazy as _
   from django.db import models

   class Account(models.Model):
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

14. Create the form to add and edit the accounts in `sample/forms.py`:
   ```python
   from django import forms
   from sample import models

   class FormWithRequest(forms.ModelForm):
       def __init__(self, *args, **kwargs):
           self.request = kwargs.pop('request', None)
           super(FormWithRequest, self).__init__(*args, **kwargs)

   class AccountForm(FormWithRequest):
       class Meta:
           model = models.Account
           fields = ('level',)
   ```

15. Create the template to display an account in the leaderboard in `sample/templates/items/accountItem.html` (note: owner and owner.preferences in account item have been prefetched in the default queryset):
   ```html
   {% load web_tags %}
   {% with account=item %}
   <br>
   <div class="well">
     <a href="{{ 'user'|itemURL:account.owner }}">
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
       "jquery-easing": "*"
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
   python manage.py makemessages -l ru --ignore=sample/settings.py
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
    - See [Enabled collections](#enabled-collections) documentation

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

Site Settings
===

Your settings file is located in `sample/settings.py`.

| Setting | About | Default value |
|---------|-------|---------------|
| SITE_NAME | Full name of the site (can be different from `SITE` in django settings) ("Sample Website") | *required* |
| SITE_URL | Full URL of the website, ends with a `/` ("http://sample.com/") | *required* |
| SITE_IMAGE | Path of the image in `sample/static/img` folder ("sample.png") | *required* |
| SITE_STATIC_URL | Full URL of the static files (images, javascript, uploaded files), differs in production and development, ends with a `/` ("//i.sample.com/") | *required* |
| GAME_NAME | Full name of the game that the site is about ("Sample Game") | *required* |
| ACCOUNT_MODEL | Your custom model to handle game accounts (`models.Account`) | *required* |
| COLOR | The dominant hex color of the site, must be the same than @mainColor in LESS ("#4a86e8") | *required* |
| SITE_DESCRIPTION | Slogan, catch phrase of the site | "The {game name} Database & Community" |
| ENABLED_NAVBAR_LISTS | See [Navbar Links](#navbar-links) documentation | |
| ENABLED_PAGES | See [Enabled pages](#enabled-pages) documentation | |
| ENABLED_COLLECTIONS | See [Enabled collections](#enabled-collections) documentation | |
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
| DONATE_IMAGES_FOLDER | Path for `donations` folder in `sample/static/img/` for images to illustrate donations perks | "" |
| TRANSLATION_HELP_URL | URL with guide or tools to allow people to contribute to the site's translation | [link](https://poeditor.com/join/project/h6kGEpdnmM) |
| SITE_LOGO | Path of the image displayed instead of the site name in the nav bar | None |
| FAVORITE_CHARACTERS | List of tuples (id, full name, image path - must be squared image) for each character that can be set as a favorite on users' profiles, if it's in a database it's recommended to use [Generated Settings](#generated-settings) to save them once in a while | None |
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
| SITE_LONG_DESCRIPTION | A long description of what the website does. Used on the about page. | A long text |
| GAME_DESCRIPTION | A long description of the game. Used on the about game page. | None (just shows game image) |
| TOTAL_DONATORS | Total number of donators (you may use web.tools.totalDonators to save this value in the [generated settings](#generated-settings)) | 2 |

Enable/Disable default pages and collections
===

If, for instance, you don't want to enable the help pages and the reports on your site, you can easily disable a page or a collection:

```python
ENABLED_PAGES = DEFAULT_ENABLED_PAGES
ENABLED_PAGES['help']['enabled'] = False

ENABLED_COLLECTIONS = DEFAULT_ENABLED_COLLECTIONS
ENABLED_COLLECTIONS['report']['enabled'] = False
```

Enabled Collections
===

A collection can be game elements such as cards, characters, songs, levels, pokémons, etc, or website elements such as users, activities, reports, etc.

##### Collections Django models

A collection always refers to a django model, but all your models aren't necessarily collections. You may create a model used only in a page (see [Enabled pages](#enabled-pages)) or within another collection that has its own model.

All the django models used in collections must:

- **Have an owner**
  Which means we should be able to do `instance.owner` and `instance.owner_id`.
  It can be an actual model field or returned with `@property` (for both `owner` and `owner_id`), with the exception of the `Account` model that must contain an actual model field `owner`.

   ```python
   class Idol(models.Model):
     """
     This model has an actual owner field
     """
       owner = models.ForeignKey(User, related_name='idols')

   class Score(models.Model):
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
  Preferably avoid special characters. If you have an English and Japanese sentence, go for the English one.
  ```python
  class Card(models.Model):
      name = models.CharField(max_length=100)

      def __unicode__(self):
        return self.name
  ```

- **Use an internal cache for fields in forein keys that are accessed often**
  To avoid extra `JOIN` in your queries (ie select_related) which slow down the queries.
  Let's say every time we display a card, we also display the name and age of the idol featured in the card:

   ```python
   from web.utils import AttrDict

   class Card(models.Model):
       ...
       idol = models.ForeignKey(Idol, related_name='cards')
       ...

       # Cache
       _cache_days = 20
       _cache_last_update = models.DateTimeField(null=True)
       _cache_idol_name = models.CharField(max_length=32, null=True)
       _cache_idol_age = models.PositiveIntegerField(null=True)

       def force_cache(self):
           """
           Recommended to use select_related('idol') when calling this method
           """
           self._cache_last_update = timezone.now()
           self._cache_idol_name = self.idol.name
           self._cache_idol_age = self.idol.age
           self.save()

       @property
       def cached_idol(self):
           if not self._cache_last_update or self._cache_last_update < timezone.now() - datetime.timedelta(days=self._cache_days):
               self.force_cache()
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

##### Collections Settings

Collections available should be configured in your site's settings file (in `sample/settings.py`).

To add a collection in your settings, add a new dictionary in the `ENABLED_COLLECTIONS` dictionary. The key is the name of the collection referred to in various places in your code. It's also the name of a singular item. In this example, let's say the key is `card`:

```python
ENABLED_COLLECTIONS['card'] = {
  'title': _('Card'),
  ...
}
```

Collection settings dictionaries may contain the following settings:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| queryset | Queryset to get the items, don't forget to use `select_related` when using fields in foreign key | *required* | models.Card.objects.all().select_related('idol') |
| plural_name | Multiple items string, used in URLs | key + 's' | 'cards' |
| title | Localized title for one item, visible for site's users  | Capitalized key | _('Card') |
| plural_title | Localized title for multiple items, visible for site's users | Capitalized key + 's' | _('Cards') |
| icon | String name of a [flaticon](#flaticon) that illustrates the collection (used in navbar) | None | 'album' |
| image | Path to image that illustrates the collection (used in navbar + when adding/editing items) | None | 'card.png' |
| navbar_link | Should a link to the list view of this collection appear in the nav bar? | True | True |
| navbar_link_list | Name of the [nav bar list](#nav-bar-lists) in which the link is going to appear | None | 'more' |

For each of your collections, you may enable or disable the following views:

- [List view](#list-view): Paginated list of items with filters/search
- [Item view](#item-view): A page with a single item, shows comments for this item
- [Add view](#add-view): Form to add a new item
- [Edit view](#edit-view): Form to edit and delete an item

To enable a view, add a dictionary in the collection's dictionary:

```python
ENABLED_COLLECTIONS['card'] = {
  ...
  'list': { ... },
  'item': { ... },
  'add': { ... },
  'edit': { ... },
}
```

### List view

Collections list view settings dictionaries may contain the following:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| js_files | List of javascript files to include, all files are in `static/js` except if it starts with `bower/` | [] | ['cards.js, 'bower/marked/lib/marked'] |
| per_line | Number of elements displayed per line (1, 2, 3, 4, 6, 12), make sure it's aligned with the page_size or it'll look weird :s | 3 | |
| page_size | Number of items per page | 12 | |
| get_global_context | Function to get the global context | GET_GLOBAL_CONTEXT in your settings | |
| authentication_required | Should the page be available only for authenticated users? | False | |
| staff_required | Should the page be available only for staff users? | False | |
| filter_queryset | A function that takes a queryset, parameters and the request and return a modified queryset | None| [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L1) |
| default_ordering | String name of a field (only one) | '-creation' | 'level' |
| distinct | The database query makes sure the results only appear once (significantly slower) | True | |
| filter_form | Django form that will appear on the right side panel and allow people to search / filter, must take request (make it inherit from FormWithRequest) | None (no side bar) | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L8) |
| add_button_subtitle | Sentence to write below the add buttons | _('Become a contributor to help us fill the database') | _('Create an account to join the community!') |
| show_title | Should the plural_title of the collection be displayed on top of the list? | False | |
| ajax | Enable getting this page in ajax, the ajax auto scroll pagination will not work if this is disabled, not recommended | True | |
| ajax_pagination_callback | The name of a javascript function to call everytime a new page loads (including the first time) | None | "updateCards" (See [Example](https://gist.github.com/db0company/b9fde532eafb333beb57ab7903e69749#file-magicirclesexamples-js-L1)) |
| full_width | Should the list take 100% of the page width? | False | |
| extra_context | Function that takes the context (with request inside) which allows you to add extra context, typically for your templates | None | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L20) |
| foreach_item | Function called for all the elements about to be displayed, that takes the item position, the item and the context | None | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L23) |
| before_template | Name of a template to include between the title (if shown) and the add buttons (if any) and results (without `.html`) | None | "include/beforeCards" |
| after_template | Name of a template to include at the end of the list, when the last page loads (without `.html`), if you provide something in `extra_context` for this template, first check `if context['is_last_page']: ...` | None | "include/afterCards" |
| no_result_template | Name of a template to show if there's no results to show, otherwise it will just show "No result" in a bootstrap `alert-info` | None | "include/cardsNoResult" |

### Item view

Collections item view settings dictionaries may contain the following:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| js_files | List of javascript files to include, all files are in `static/js` except if it starts with `bower/` | [] | ['cards.js, 'bower/marked/lib/marked'] |
| get_global_context | Function to get the global context | GET_GLOBAL_CONTEXT in your settings | |
| authentication_required | Should the page be available only for authenticated users? | False | |
| staff_required | Should the page be available only for staff users? | False | |
| owner_only | Should the page be available only for the owner of the item? | False | |
| filter_queryset | A function that takes a queryset, parameters and the request and return a modified queryset | None | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L1) |
| comments_enabled | Should we display a comment section below the item? | True | |
| template | Path of the HTML template in `sample/templates/items/` to display the item (without `.html`) | Collection name + "Item" | "cardItem" |
| ajax_callback | The name of a javascript function to call when the page loads | None | "updateCards" (See [Example](https://gist.github.com/db0company/b9fde532eafb333beb57ab7903e69749#file-magicirclesexamples-js-L1)) |
| ajax | Enable getting this page in ajax, the ajax auto scroll pagination will not work if this is disabled, not recommended | True | |
| extra_context | Function that takes the context (with request inside) which allows you to add extra context, typically for your templates | None | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L20) |

### Add view

Collections add view settings dictionaries may contain the following:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| form_class | FormClass to add the item, must take request (make it inherit from FormWithRequest), can be a function that takes request, context and collection | *required* | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L31) |
| get_global_context | Function to get the global context | GET_GLOBAL_CONTEXT in your settings | |
| authentication_required | Should the page be available only for authenticated users? | True | |
| staff_required | Should the page be available only for staff users? | False | |
| types | See [Item Types](#item-types) | | |
| js_files | List of javascript files to include, all files are in `static/js` except if it starts with `bower/` | [] | ['cards.js, 'bower/marked/lib/marked'] |
| before_save | Function called before the form is saved, takes request, instance and type. Not recommended, overload `save`in your form instead | None | |
| savem2m | Should we call save_m2m to save the manytomany items after saving this model? | False | |
| redirect_after_add | String URL or callback (that takes request, item, ajax) to redirect to after the item has been added | item URL | "/" |
| alert_duplicate | Should we display a warning that asks users to check if it doesn't already exist before adding it? | True | |
| extra_context | Function that takes the context (with request inside) which allows you to add extra context, typically for your templates | None | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L20) |
| filter_queryset | A function that takes a queryset, parameters and the request and return a modified queryset | None | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L1) |
| ajax | Enable getting this page in ajax, the ajax auto scroll pagination will not work if this is disabled, not recommended | True | |
| multipart | Should the HTML form allow multipart (uploaded files)? | False | |
| otherbuttons_template | Template path (without `.html`) for extra buttons at the end of the form | None | "include/cardsExtraButtons" |
| back_to_list_button | Should we display a button to go back to the list view at the end of the form? | True | |
| after_template | Name of a template to include after the form | None | "include/afterAddCard" |

### Edit view

Collections edit view settings dictionaries may contain the following:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| form_class | FormClass to add the item, must take request (make it inherit from FormWithRequest), can be a function that takes request, context and collection | *required* | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L31) |
| allow_delete | Should we show a button to delete the item as well? | False | |
| redirect_after_delete | String URL or callback (that takes request, ajax) to redirect to after the item has been deleted | List view | "/" |
| get_global_context | Function to get the global context | GET_GLOBAL_CONTEXT in your settings | |
| authentication_required | Should the page be available only for authenticated users? | True | |
| staff_required | Should the page be available only for staff users? | False | |
| owner_only | Should the owner of the item be the only one who can edit it? Note: only the owner + staff will be able to delete, regardless this setting | True | |
| types | See [Item Types](#item-types) | | |
| js_files | List of javascript files to include, all files are in `static/js` except if it starts with `bower/` | [] | ['cards.js, 'bower/marked/lib/marked'] |
| filter_queryset | A function that takes a queryset, parameters and the request and return a modified queryset | None | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L1) |
| before_save | Function called before the form is saved, takes request, instance and type. Not recommended, overload `save`in your form instead | None | |
| savem2m | Should we call save_m2m to save the manytomany items after saving this model? | False | |
| redirect_after_edit | String URL or callback (that takes request, item, ajax) to redirect to after the item has been added | item URL | "/" |
| extra_context | Function that takes the context (with request inside) which allows you to add extra context, typically for your templates | None | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L20) |
| ajax | Enable getting this page in ajax, the ajax auto scroll pagination will not work if this is disabled, not recommended | True | |
| multipart | Should the HTML form allow multipart (uploaded files)? | False | |
| otherbuttons_template | Template path (without `.html`) for extra buttons at the end of the form | None | "include/cardsExtraButtons" |
| back_to_list_button | Should we display a button to go back to the list view at the end of the form? | True | |
| after_template | Name of a template to include after the form | None | "include/afterAddCard" |

##### Item types

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

Generated Settings
===

Some values shouldn't be calculated from the database everytime, so it's recommended to write a script in `sample/management/commands/generate_settings.py` that will update the settings and call that script in a cron or a scheduler.

```python
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings as django_settings
from web.tools import totalDonators, itemURL
from web.templatetags.web_tags import imageURL
from sample import models

def generate_settings():

        print 'Get total donators'
        total_donators = totalDonators()

        print 'Get the latest news'
        current_events = models.Event.objects.get(end__lte=timezone.now())
        latest_news = [{
            'title': event.name,
            'image': imageURL(event.image),
            'url': itemURL('event', event),
        } for event in current_events]

        print 'Get the characters'
        all_idols = model.Idol.objects.all().order_by('name')
        favorite_characters = [(
            idol.pk,
            idol.name,
            imageURL(idol.image),
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
