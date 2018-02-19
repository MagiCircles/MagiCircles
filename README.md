![MagiCircles](http://i.imgur.com/67S7coa.png)

MagiCircles
=====

MagiCircles is a web framework to build collections databases and social network websites.

Its core features are:
- Collections: a powerful way to link a database table and its views item/list/add/edit
- A full-featured social network: activities, likes, comments, notifications, ...
- Customizable profiles
- Many pages provided by default: map, wiki, ...
- A default layout made with Bootstrap
- Very few lines of code required to get a full featured website
- Highly customizable to fit your needs
- Translated in many languages

![](http://i.imgur.com/DfNfUYB.png)

- Based on [Django](https://www.djangoproject.com/)
- Uses: [Django-Rest-Framework](http://www.django-rest-framework.org/), [Tinyfy](https://github.com/tinify/tinify-python), [Bootstrap](http://getbootstrap.com/), [jQuery](https://jquery.com/), [Bower](https://bower.io/)
- And more, see `requirements.txt` and `sample_project/bower.json`

[![](http://i.imgur.com/oQbvhxD.png)](http://i.imgur.com/oQbvhxD.png)

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

![](http://i.imgur.com/nsFXA0Z.png)

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

# Table of content

1. [Start a new website](#start-a-new-website)
    1. [Requirements](#requirements)
    1. [Quick start](#quick-start)
    1. [Full starting guide](#full-starting-guide)
    1. [Start coding!](#start-coding)
    1. [Frequent problems](#frequent-problems)
1. [Files tree](#files-tree)
1. [Website Settings](#website-settings)
1. [Collections](#collections)
    1. [Models](#models)
        1. [Inherit from MagiModel and provide a name](#inherit-from-magimodel-and-provide-a-name)
        1. [Have an owner](#have-an-owner)
        1. [Override `__unicode__`](#override-__unicode__)
        1. [MagiModel utils](#magimodel-utils)
            1. [MagiModel collection utils](#magimodel-collection-utils)
            1. [MagiModel Images](#magimodel-images)
            1. [BaseAccount model](#baseaccount-model)
            1. [Save choices values as integer rather than strings](#save-choices-values-as-integer-rather-than-strings)
            1. [Store comma separated values](#store-comma-separated-values)
            1. [Transform images before saving them](#transform-images-before-saving-them)
            1. [Check choices at form level instead of model level](#check-choices-at-form-level-instead-of-model-level)
    1. [MagiCollection](#magicollection)
        1. [Views](#views)
            1. [All views](#all-views)
            1. [List view](#list-view)
            1. [Item view](#item-view)
            1. [Add view](#add-view)
            1. [Edit view](#edit-view)
        1. [MagiCollection utils](#magicollection-utils)
            1. [Collectible](#collectible)
            1. [CuteForm](#cuteform)
            1. [Item types](#item-types)
            1. [to_fields method](#to_fields-method)
            1. [AccountCollection](#accountcollection)
    1. [MagiForm](#magiform)
    1. [MagiFilter](#magifilter)
        1. [Search and ordering](#search-and-ordering)
        1. [Configure fields](#configure-fields)
1. [Enabled Pages](#enabled-pages)
1. [Default pages and collections](#default-pages-and-collections)
    1. [Default pages](#default-pages)
    1. [Default collections](#default-collections)
        1. [Collections disabled by default](#collections-disabled-by-default)
    1. [Enable/Disable/Configure default pages and collections](#enabledisableconfigure-default-pages-and-collections)
1. [Nav bar lists](#nav-bar-lists)
1. [API](#api)
    1. [MagiSerializer](#magiserializer)
    1. [ImageField](#imagefield)
    1. [IField](#ifield)
    1. [Full Example](#full-example)
1. [Utils](#utils)
    1. [Python](#python)
        1. [Models upload](#models-upload)
        1. [Access MagiCollections](#access-magicollections)
        1. [Optimize images with TinyPNG](#optimize-images-with-tinypng)
        1. [Validators](#validators)
        1. [Other tools](#other-tools)
    1. [Templates](#templates)
        1. [Tools](#tools)
    1. [Javascript](#javascript)
        1. [HTML elements with automatic Javascript behavior](#html-elements-with-automatic-javascript-behavior)
        1. [Commons](#commons)
1. [Recommendations](#recommendations)
    1. [Don't concatenate translated strings](#dont-concatenate-translated-strings)
    1. [Internal cache for foreign keys in models](#internal-cache-for-foreign-keys-in-models)
    1. [Calling functions in templates](#calling-functions-in-templates)
    1. [Utility functions for models](#utility-functions-for-models)
    1. [Generated Settings](#generated-settings)
    1. [Avoid generating translation terms for terms already available in Django framework](#avoid-generating-translation-terms-for-terms-already-available-in-django-framework)
    1. [Disable activities](#disable-activities)
    1. [Disable activities but keep news for staff members](#disable-activities-but-keep-news-for-staff-members)
1. [Production Environment](#production-environment)
1. [Translations](#translations)
1. [Flaticon](#flaticon)
1. [Migrate from MagiCircles1 to MagiCircles2](#migrate-from-magicircles1-to-magicircles2)

Start a new website
==========

Requirements
------------

- Debian, Ubuntu, and variants:

  ```shell
  apt-get install libpython-dev libffi-dev python-virtualenv libmysqlclient-dev libssl-dev nodejs npm
  npm install lessc bower
  ```

- Arch:

  ```shell
  pacman -S libffi python-virtualenv libmysqlclient libssl nodejs npm
  npm install lessc bower
  ```

- OS X (install [brew](https://brew.sh/) if you don't have it):

  ```shell
  brew install python node
  sudo pip install virtualenv
  npm install lessc bower
  ```

Quick start
-----------

This section allows you to get a website up and running in a few minutes. If you'd like to get a better understanding of how to set up a new MagiCircles website, skip this section and follow the section ⎡[Full Starting Guide](#full-starting-guide)⎦ instead.

1. Create a GitHub repository and copy the URL:

   ```shell
   GITHUB=git@github.com:SchoolIdolTomodachi/Hello.git
   ```

2. Pick a shortname for your website.

   ```shell
   PROJECTNAME='hello'
   ```

3. Copy the content of the folder called `sample_project` to your project:

```shell
git clone ${GITHUB}
git clone -b MagiCircles2 https://github.com/SchoolIdolTomodachi/MagiCircles.git
GITFOLDER=`echo ${GITHUB} | rev | cut -d/ -f1 | rev | cut -d. -f1`
cp -r MagiCircles/sample_project/* ${GITFOLDER}/
cp -r MagiCircles/sample_project/.bowerrc ${GITFOLDER}/
cp -r MagiCircles/sample_project/.gitignore ${GITFOLDER}/
cd ${GITFOLDER}/
```

4. Rename the files and recursively replace the string `sample` with your shortname:

   ```shell
   mv sample ${PROJECTNAME}
   mv sample_project ${PROJECTNAME}_project
   mv ${PROJECTNAME}/static/img/sample.png ${PROJECTNAME}/static/img/${PROJECTNAME}.png
   for f in `grep -rl sample . | \grep -v '.git/' | \grep -E '.py$|.json$|.bowerrc$|.gitignore$'`; do echo $f; sed -i '' -e "s/sample/${PROJECTNAME}/g" $f; done
   ```

5. Setup your local python working environment, install the dependencies and run your first website:

   ```shell
   virtualenv env
   source env/bin/activate
   pip install -r requirements.txt
   python manage.py makemigrations ${PROJECTNAME}
   python manage.py migrate
   bower install
   python manage.py generate_css
   python manage.py runserver
   ```
   Open http://localhost:8000/

   ![](http://i.imgur.com/8CfckKj.png)

Full starting guide
-------------------

The ⎡[Quick Start](#quick-start)⎦ section above will do all this for you, but feel free to follow this instead if you want to understand how MagiCircles works in more details.

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
   git+https://github.com/SchoolIdolTomodachi/MagiCircles.git@MagiCircles2
   ```

5. Install the requirements:
   ```shell
   pip install -r requirements.txt
   ```

6. Create the app:
   ```shell
   python manage.py startapp sample
   ```

7. Edit `sample_project/settings.py` to specify your website name, add the following installed apps and middlewares, and some configuration:
   ```python
   SITE = 'sample'

   INSTALLED_APPS = (
     ...
     'corsheaders',
     'bootstrapform',
     'bootstrap_form_horizontal',
     'rest_framework',
     'storages',
     'magi',
   )

   MIDDLEWARE_CLASSES = (
     ...
       'django.middleware.locale.LocaleMiddleware',
       'corsheaders.middleware.CorsMiddleware',
       'django.middleware.common.CommonMiddleware',
       'magi.middleware.languageFromPreferences.LanguageFromPreferenceMiddleWare',
       'magi.middleware.httpredirect.HttpRedirectMiddleware',
   )

   FAVORITE_CHARACTERS = []

   MAX_WIDTH = 1200
   MAX_HEIGHT = 1200
   MIN_WIDTH = 300
   MIN_HEIGHT = 300

   AUTHENTICATION_BACKENDS = ('magi.backends.AuthenticationBackend',)

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
     os.path.join(BASE_DIR, 'magi/locale'),
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
       STATIC_UPLOADED_FILES_PREFIX = 'magi/static/uploaded/' if DEBUG else 'u/'
   ```

8. Include the URLs in `sample_project/urls.py`:
   ```python
   urlpatterns = patterns('',
     url(r'^', include('magi.urls')),
     ...
   )
   ```

9. Create the file `sample/settings.py` that will describe how you want your website to look like:
   ```python
   from django.conf import settings as django_settings
   from magi.default_settings import DEFAULT_ENABLED_COLLECTIONS, DEFAULT_ENABLED_PAGES
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

10. Create a few images:
   - Your logo in `sample/static/img/sample.png`
   - The default avatar for your users in `sample/static/img/avatar.png`
   - An illustration of the game in `sample/static/img/game.png`

11. Create a django model in `sample/models.py` that will contain the info about the users game accounts:
   ```python
   from django.contrib.auth.models import User
   from django.utils.translation import ugettext_lazy as _
   from django.db import models
   from magi.item_model import MagiModel
   from magi.abstract_models import BaseAccount

   class Account(BaseAccount):
       class Meta:
           pass
   ```

   Make this model available in your administration, edit `sample/admin.py`:
   ```python
   from django.contrib import admin
   from sample import models

   admin.site.register(models.Account)
   ```

15. Create the template to display an account in the leaderboard in `sample/templates/items/accountItem.html` (note: owner and owner.preferences in account item have been prefetched in the default queryset):
   ```html
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
   <div class="row"><div class="col-md-12">
     {% include 'items/defaultAccountItem.html' with without_link=True %}
   </div></div>
   {% endfor %}
   ```
   In a real website, you would probably want to display the account differently in the context of the profile.

17. Create your LESS main file in `sample/static/less/style.less`:
   ```css
    /* Uncomment these lines when you need to compile LESS -> CSS */
    // @import "../../../env/lib/python2.7/site-packages/magi/static/less/main.less";
    // @import "../../../env/lib/python2.7/site-packages/magi/static/less/mixins/magicircles.less";

    /* Comment these lines when you need to compile LESS -> CSS */
    @import "main.less";
    @import "mixins/magicircles.less";

    /******************************************/
    /* Variables */

    @mainColor: #4a86e8;
    @secondaryColor: #73c024;

    /******************************************/
    /* Tools */

    /******************************************/
    /* MagiCircles */

    html {
        .setup-sidebar(@mainColor);
        .magicircles(@mainColor, @secondaryColor);
    }

    @import "generated_colors.less";

    /******************************************/
    /* Single pages */

    /******************************************/
    /* MagiCollections */
    ```
   You may customize the content depending on the page you're on using `.current-page` where page corresponds to the page name (example: `current-index`, `current-card_list`, ...).

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
   python manage.py generate_css
   ```

21. Initialize the models:
   ```shell
   python manage.py makemigrations sample
   python manage.py migrate
   ```

22. Set up your `.gitignore`:
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
   Those are in addition to usual python ignored files. You can get a basic `.gitignore` when you create a GitHub repository.

23. Test that the homepage works:
   ```shell
   python manage.py runserver
   ```
   Open [http://localhost:8000/](http://localhost:8000/) in your browser

![](http://i.imgur.com/8CfckKj.png)

Start coding!
------------

1. Initial commit

```
git add .gitignore .bowerrc bower.json manage.py requirements.txt ${PROJECTNAME} ${PROJECTNAME}_project
git commit -m "Getting started with MagiCircles2"
git push
```

2. Create an admin or staff

   All users, including administrators (= superuser) or staff, need to be created using the sign up form in the website: http://localhost:8000/signup/

   After your user has been created, you may change it to super administrator by doing so:

   ```shell
   python manage.py shell
   ```

   ```python
   from magi import models
   username='YOURUSERNAME'

   # Set as super user
   models.User.objects.filter(username=username).update(is_superuser=True, is_staff=True)

   # Or set as staff
   models.User.objects.filter(username=username).update(is_staff=True)
   ```

23. Start setting up your settings, custom pages and collections:
    - See ⎡[Website Settings](#website-settings)⎦
    - See ⎡[Collections](#collections)⎦
    - See ⎡[Enabled pages](#enabled-pages)⎦

Frequent problems
-----------------

- **I can't install / get errors for some requirements**

  You may ignore the following requirements which are not needed in a development environment:
     - `mysql`: uses sqlite3 in development
     - `less`: compiling to `.css` is only needed in production, development environment will render the less file in the browser
     - `gettext`: only needed to generate translations
     - `boto`, `django-storages`, `django-ses`, `s3`: only used in production when using AWS
     - `djangorestframework`, `django-oauth-toolkit`: only needed if you provide a REST API
     - `geopy`: used to generate the lat/long of users' locations for the map
     - `tinify`: compress the images, only useful in production

- **I can't / don't want to use the port 8000**

  Create a file `sample_project/local_settings.py` with:
  ```python
  DEBUG_PORT = 1234
  ```

  Start the server with:
  ```python
  python manage.py runserver 0.0.0.0:1234
  ```

***

Files tree
==========

This is the recommended file tree for your MagiCircles projects.

Required files are marked with ✳️. Any other file is optional and you should only create them if needed.

- `sample/`: main folder that contains your source code
    - ✳️`settings.py`: [the settings of your website](#website-settings)
    - ✳️`models.py`: [your models](#models)
    - ✳️`magicollections.py`: [your magicollections](#collections)
    - `forms.py`: [your forms](#magiform) (including [filter forms](#magifilter))
    - `views.py`: [your standalone pages](#enabled-pages)
    - `utils.py`: your utility functions
    - `admin.py`: settings of your admin panel (for super users only)
    - `django_translated.py`: terms translated by django (See ⎡[Avoid generating translation terms for terms already available in Django framework](#avoid-generating-translation-terms-for-terms-already-available-in-django-framework)⎦)
    - `templates/`: your django templates
        - `items/`: templates for [item views](#item-view)
            - `IdolItem.html`: a template for an example collection `Idol`
        - `pages/`: templates for your standalone pages
        - `include/`: partial templates included in other templates
    - ✳️`static/`:
        - ✳️`img/`: your images
            - ✳️`avatar.png`: avatar used by default when users don't provide it
            - ✳️`sample.png`: your illustration image
            - `sample_logo.png`: the logo on your homepage
            - `sample_logo_ja.png`: the logo for a specific language
            - `name_of_the_game.png`: illustration of the game
            - ✳️`favicon.ico`: your favicon
            - `rarity/`: example of the name of a field that contains a choice. this folder is used with cuteform
                - `1.png`: image for the choice (1 corresponds to the value)
                - `2.png`: //
        - ✳️`js/`: your javascript sources
            - ✳️`main.js`: your main js file, loaded on all pages
        - ✳️`less/`: your LESS sources
            - ✳️`style.less`: your main LESS file
            - `mixins/`: your mixins
        - ✳️`css/`: CSS compiled from LESS sources goes here
            - `style.css`: your compiled CSS file
        - `bower/`: Frontend dependencies get automatically installed here
    - `locale/`: translation files `.po` and `.mo`
    - `management/commands/`: your custom commands
        - `generate_settings.py`: script to generate cached settings, see ⎡[Generated Settings](#generated-settings)⎦
    - `migrations`: your migration files (auto-generated by django)
- ✳️`sample_project/`: app deployment settings
    - ✳️`settings.py`: django settings
    - `local_settings.py`: your local settings, should not be committed to your repo
    - `generated_settings.py`: generated by your `generate_settings` command
    - ✳️`urls.py`: your router for URLS - you shouldn't need to configure it, as MagiCircles will take care of that using your magicollections and enabled pages
    - ✳️`wsgi.py`: WSGI config
- `api/`: if you provide a REST API, the sources will be here
- ✳️`bower.json`: your frontend requirements
- ✳️`.bowerrc`: configuration of frontend requirements installation
- `.gitignore`: the list of files that shouldn't be committed
- `README.md`: description of your repository
- ✳️`manage.py`: default django script script to run commands
- ✳️`requirements.txt`: your python dependencies

Website Settings
===============

Your settings file is located in `sample/settings.py`.

Required settings:

| Setting | About |
|---------|-------|
| ACCOUNT_MODEL | Your custom model to handle game accounts (`models.Account`). It's highly recommended to make it inherit from `magi.abstract_models.BaseAccount`. |
| COLOR | The dominant hex color of the website, must be the same than @mainColor in LESS ("#4a86e8") |
| DISQUS_SHORTNAME | Go to [Disqus](https://disqus.com/admin/create/) to create a new website and provide the shortname of your new website here. It will be used to display comment sections under some of your pages or collections. :warning: Make sure you disable adertisments in your disqus website settings! |
| GAME_NAME | Full name of the game that the website is about ("Sample Game") |
| SITE_IMAGE | Path of the image in `sample/static/img` folder ("sample.png"). This image is used as the main illustration of the website, shared on social media. It is recommended to avoid transparency in this image.  |
| SITE_NAME | Full name of the website (can be different from `SITE` in django settings) ("Sample Website") |
| SITE_STATIC_URL | Full URL of the static files (images, javascript, uploaded files), differs in production and development, ends with a `/` ("//i.sample.com/") |
| SITE_URL | Full URL of the website, ends with a `/` ("http://sample.com/") |

Optional settings:

| Setting | About | Default value |
|---------|-------|---------------|
| ABOUT_PHOTO | Path of the image in `sample/static/img` folder | "engildeby.gif" |
| ACCOUNT_TAB_ORDERING | List of tabs names in the order you would like them to appear for each profile account tabs. Missing tab names in this list will just appear at the end.  | None (order not guaranteed) |
| ACTIVITY_TAGS | List of tuples (raw value, full localizable tag name) for the tags that can be added ao an activity | None |
| BUG_TRACKER_URL | Full URL where people can see issues (doesn't have to be github) | Full URL created from the GITHUB_REPOSITORY value |
| CALL_TO_ACTION | A sentence shown on the default index page to encourage visitors to sign up | _('Join the community!') |
| CONTACT_EMAIL | Main contact email address | Value in django settings `AWS_SES_RETURN_PATH` |
| CONTACT_FACEBOOK | Contact Facebook username or page | "db0company" |
| CONTACT_REDDIT | Contact reddit username | "db0company" |
| CONTACT_DISCORD | Contact Discord server invite URL | "https://discord.gg/mehDTsv" |
| CONTRIBUTE_URL | Full URL of the guide (or README) for developers who would like to contribute | [link](https://github.com/SchoolIdolTomodachi/SchoolIdolAPI/wiki/Contribute) |
| DONATE_IMAGE | Path of the image in DONATE_IMAGES_FOLDER | None |
| DONATORS_STATUS_CHOICES | List of tuples (status, full string) for the statuses of donators, statuses must be THANKS, SUPPORTER, LOVER, AMBASSADOR, PRODUCER and DEVOTEE | "Thanks", "Player", "Super Player", "Extreme Player", "Master Player", "Ultimate Player" |
| EMAIL_IMAGE | Path of the image in `sample/static/img` folder ("sample.png") that will appear at the beginning of all the emails. | value of SITE_IMAGE |
| EMPTY_IMAGE | Path of the image for empty values in cute form in `sample/static/img` folder | "empty.png" |
| ENABLED_NAVBAR_LISTS | See ⎡[Navbar Links](#navbar-links)⎦ | |
| ENABLED_PAGES | See ⎡[Enabled pages](#enabled-pages)⎦ | |
| FAVORITE_CHARACTERS | List of tuples (id, full name, image path - must be squared image and full url) for each character that can be set as a favorite on users' profiles, if it's in a database it's recommended to use [Generated Settings](#generated-settings) to save them once in a while | None |
| FAVORITE_CHARACTER_NAME | String that will be localized to specify what's a "character". Must contain `{nth}` (example: "{nth} Favorite Idol") | "{nth} Favorite Character" |
| FAVORITE_CHARACTER_TO_URL | A function that will return the URL to get more info about that character. This function takes a link object with value (full name), raw_value (id), image | lambda _: '#' |
| FEEDBACK_FORM | URL of a form used to gather feedback from user. When not specified, it will just link to the bug tracker. | None |x
| GAME_DESCRIPTION | A long description of the game. Used on the about game page. | None (just shows game image) |
| GAME_URL | A link to the official homepage of the game. Used on the about game page. | None (just shows game image) |
| GET_GLOBAL_CONTEXT | Function that takes a request and return a context, must call `globalContext` in `magi.utils` | None |
| GITHUB_REPOSITORY | Tuple (Username, repository) for the sources of this website, used in about page | ('MagiCircles', 'MagiCircles') |
| GOOGLE_ANALYTICS | Tracking number for Google Analytics | 'UA-67529921-1' |
| HASHTAGS | List of hashtags when sharing on Twitter + used as keywords for the page (without `#`) | [] |
| HELP_WIKI | Tuple (Username, repository) for the GitHub wiki pages to display the help pages | ('MagiCircles', 'MagiCircles') |
| JAVASCRIPT_TRANSLATED_TERMS | Terms used in `gettext` function in Javascript, must contain `DEFAULT_JAVASCRIPT_TRANSLATED_TERMS` in `magi.default_settings` | None |
| LATEST NEWS | A list of dictionaries that should contain image, title, url and may contain hide_title, used if you keep the default index page to show a carousel. Recommended to get this from [generated Settings](#generated-settings). | None |
| LAUNCH_DATE | If you want to tease your community before officially opening the website, or just let your staff team test it, you can set a launch date. It will make all the pages and collections only available to staff and make the homepage a countdown before the website opens. Example: `import datetime, pytz datetime.datetime(2017, 04, 9, 12, 0, 0, tzinfo=pytz.UTC)` | None |
| NAVBAR_ORDERING | List of collection or page names in the order you would like them to appear in the nav bar. Missing collection or page name in this list will just appear at the end.  | None (order not guaranteed) |
| ONLY_SHOW_SAME_LANGUAGE _ACTIVITY_BY_DEFAULT _FOR_LANGUAGES  | You may use this instead of `ONLY_SHOW_SAME_LANGUAGE _ACTIVITY_BY_DEFAULT` to specify per language | ['ja', 'zh-hans', 'kr'] |
| ONLY_SHOW_SAME_LANGUAGE _ACTIVITY_BY_DEFAULT | If set to `True`, uers will only see the activities in their language (regardless of authentication), otherwise, they'll see all activities in all languages. Note that users can override this behavior in their settings. | False |
| ON_PREFERENCES_EDITED | Callback after a user's preferences have been changed, takes user instance (contains updated user.preferences). If you call this yourself, make sure you also call `models.onPreferencesEdited`. | None |
| ON_USER_EDITED | Callback after a user's username or email has been changed, takes user instance. If you call this yourself, make sure you also call `models.onUserEdited`. | None |
| PRELAUNCH_ENABLED_PAGES  | When launch date is set, all the pages in `ENABLED_PAGES` get changed to only be available to staff members, except the pages listed here. | 'login', 'signup', 'prelaunch', 'about', 'about_game', 'changelanguage', 'help' |
| PROFILE_EXTRA_TABS | A dictionary of tab name -> dictionary (name, icon, callback (= js)) to show more tabs on profile (in addition to activities and accounts) | None |
| PROFILE_TABS | Tabs visible in a user's profile page, under the box that contins the avatar, the description and the links. A dictionary with: <ul><li>`name`: localized tab name</li><li>`icon`: String name of a [flaticon](#flaticon) that illustrates the tab</li><li>`callback`: optional, name of javasript function to call to get the content of the tab - takes: <ul><li>user_id</li><li>A callback that you must call and give it the HTML tree to display for this tab and an optional other callback to call after it's been displayed</li></ul></li></ul> | accounts, activities and badges. Will be disabled if you disable their respective collection. |
| SHOW_TOTAL_ACCOUNTS | On profiles, show or hide the total number of accounts before showing the accounts | True |
| SITE_DESCRIPTION | Slogan, catch phrase of the website. May be a callable that doesn't take any argument (`lambda: _('Best database for best game')`) | "The {game name} Database & Community" |
| SITE_LOGO | Path of the image displayed on the homepage. | value of SITE_IMAGE |
| SITE_LOGO_PER_LANGUAGE | The logo displayed on the homepage may need to be different depending on the language. This is a dictionary of language code => path of the image | None |
| SITE_LONG_DESCRIPTION | A long description of what the website does. Used on the about page. May be a callable that doesn't take any argument | A long text |
| SITE_NAV_LOGO | Path of the image displayed instead of the website name in the nav bar | None |
| STATIC_FILES_VERSION | A number or string that you can change when you update the css or js file of your project to force update the cache of your users in production | '1' |
| TOTAL_DONATORS | Total number of donators (you may use magi.tools.totalDonators to save this value in the [generated settings](#generated-settings)) | 2 |
| TRANSLATION_HELP_URL | URL with guide or tools to allow people to contribute to the website's translation | [link](https://github.com/SchoolIdolTomodachi/MagiCircles/wiki/Translate-the-website) |
| TWITTER_HANDLE | Official Twitter account of this website | "schoolidolu" |
| USER_COLORS | List of tuples (raw value, full localizable color name, CSS elements name (`btn-xx`, `panel-xx`, ...), hex code of the color) | None |
| WIKI | Tuple (Username, repository) for the GitHub wiki pages to display the help pages | Value of GITHUB_REPOSITORY |

- Full details of the configuration of the settings in: `magi/settings.py` and `magi/default_settings.py`

Collections
===

![](http://i.imgur.com/9M0K2G3.png)

MagiCircles' most powerful feature is the collections, or "MagiCollections".

Pretty much everything in MagiCircles is represented using a collection.

Collections are the link between a database table and its views. It also handles some logic like routing and permissions.

Collections should be used to represent game elements such as cards, characters, songs, levels, pokémons, etc, or website elements such as users, activities, reports, etc.

It's super easy to create a collection, and they will automatically provide pages to view, list, add and edit items. Views are also available in Ajax to allow loading in a modal.

![Example of collections](http://i.imgur.com/oGPEjiZ.png)

Collections are generally composed of:

- The database: a class that inherits from `MagiModel` that corresponds to django model, with some extra helpers.
  - See ⎡[Models](#models)⎦
- The MagiCollection: a class that inherits from `MagiCollection` that will contain all the configuration.
  - See ⎡[MagiCollection](#magicollection)⎦
- (Optional) The form: one or more classes that inherit from `MagiForm` that correspond to django forms, with some extra checks. Used to add/edit.
  - See ⎡[MagiForm](#magiform)⎦
- (Optional) The filters: class that inherits from `MagiFilter` that correspond to a django form and is used to search / filter results in the list page.
  - See ⎡[MagiFilter](#magifilter)⎦

## Models

A MagiCollection always refers to a django model, but all your models aren't necessarily collections.

Models that don't need to be MagiCollections include models used only in pages (see ⎡[Enabled pages](#enabled-pages)⎦) or within another MagiCollection that has its own model.

All the django models used in collections MUST:

- [Inherit from MagiModel and provide a name](#inherit-from-magiModel-and-provide-a-name)
- [Have an owner](#have-an-owner)
- [Override `__unicode__`](#override-unicode-)

#### Inherit from MagiModel and provide a name

```python
from magi.models import MagiModel

class Idol(MagiModel):
    collection_name = 'idol'
    ...
```

`collection_name` is used to get the MagiCollection associated with this item. While multiple MagiCollections can use the same model class, the item itself will only be aware of one associated MagiCollection.

Thanks to `MagiModel`, you'll have access to some properties on all your objects which can be useful. You can also name some of your fields a certain way to unlock some features, like interger choices and CSV.

See ⎡[MagiModel Utils](#magimodel-utils)⎦.

You may use `BaseMagiModel` if you'd like to enjoy MagiModel's features without tying it to a collection.

#### Have an owner

```python
class Idol(MagiModel):
    owner = models.ForeignKey(User, related_name='idols')
```

Because it's very common to associate an item to an `account` and not directly to an `owner`, since `account` already has an owner, you may make your model class inherit from `AccountAsOwnerModel` instead of `MagiModel`:

```python
from magi.models import AccountAsOwnerModel

class OwnedCard(AccountAsOwnerModel):
    """
    Will automatically provide a cache for the account and provide `owner` and `owner_id` properties.
    """
    account = models.ForeignKey(Account, related_name='ownedcards')
```

If your model doesn't have a direct owner or account, you may fake it by providing properties for `owner` and `owner_id`, and specify `fk_as_owner` in your model:

```python
class Book(MagiModel):
    owner = models.ForeignKey(User, related_name='books')

class Chapter(MagiModel):
    book = models.ForeignKey(Book, related_name='chapters')
    fk_as_owner = 'book'

    @property
    def owner(self):
        return self.book.owner

    @property
    def owner_id(self):
        return self.book.owner_id
```

If you have multiple layers of foreign keys before finding the owner, you may specify `selector_to_owner`:

```python
class Paragraph(MagiModel):
    chapter = models.ForeignKey(Chapter, related_name='paragraphs')
    fk_as_owner = 'chapter'
    selector_to_owner = classmethod(justReturn('chapter__book__owner'))
    ...
```

Note: `Account` model MUST contain an actual model field `owner`.

In our example above, book would be retrieved when the propety `owner` is accessed, resulting in extra database queries. To optimize this, you can:
- Set your MagiCollection `queryset` to use `select_related` to get the book:
  ```python
  class ChapterCollection:
      queryset = models.Chapter.objects.select_related('book')
  ```
- Or save a cache of the book in your model (recommended)
    - See ⎡[Internal cache for foreign keys in models](#internal-cache-for-foreign-keys-in-models)⎦

#### Override `__unicode__`

Django models already have a `__unicode__` method, but since MagiCircles uses it extensively, it's highly recommended to override it and not rely on its default value.

```python
class Card(MagiModel):
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

  If you want to use an internal cache (see ⎡[Internal cache for foreign keys in models](#internal-cache-for-foreign-keys-in-models)⎦) in your unicode function, only do it when the object has actually been created, like so:

```python
def __unicode__(self):
    if self.id:
        return u'{name} - {rarity}'.format(name=self.cached_idol.name, rarity=self.rarity)
    return u'{rarity}'.format(rarity=self.rarity)
```


### MagiModel utils

#### MagiModel collection utils

All your models that inherit from `MagiModel` or `BaseMagiModel` provide the following class methods:

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| selector_to_owner | Django model query selector you can use to retrieve the User object that correspond to the owner of this instance. | None | String query selector (example: 'owner', 'account__owner', 'chapter__book__owner') |
| owner_ids | Get the list of ids of the fk_as_owner. For example, for a card that uses accounts as owner, it would return the list of account ids owned by the user. For the 'chapter__book__owner' case, it would return the list of chapters owned by the user. | user | List of ids |
| owner_collection | For example for account would return AccountCollection. | None | An instance of a MagiCollection or None |

All your models that inherit from `MagiModel` or `BaseMagiModel` provide the following methods:

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| is_owner | Is the user in parameters the owner of this instance? | user | True or False |

All your models that inherit from `MagiModel` (not `BaseMagiModel`) provide the following properties (not meant to be overriden):

| Key | Value | Example |
|-----|-------|---------|
| `collection` | Associated MagiCollection object (retrieved using the `collection_name`) | Instance of IdolCollection |
| `collection_title` | MagiCollection setting for localized title | _('Idol') |
| `collection_plural_name` | MagiCollection setting for non-localized plural | For 'idol', it would be  `idols`, for 'activity', it would be `activities` |
| `item_url` | The URL to the ItemView | `/idol/1/Nozomi/` |
| `ajax_item_url` | The URL to the ajax ItemView | `/ajax/idol/1/` |
| `full_item_url` | The URL to the ItemView with the domain | `//sample.com/idol/1/Nozomi/` |
| `http_item_url` | The URL to the ItemView with the domain and `http` (when `//` URLs are not supported, such as in emails or when sharing) | `http://sample.com/idol/1/Nozomi/` |
| `edit_url` | The URL of the EditView | `/idols/edit/1/` |
| `ajax_edit_url` | The URL of the ajax EditView | `/ajax/idols/edit/1/` |
| `report_url` | The URL to report this item | `/idols/report/1/` |
| `open_sentence` | Localized sentence to open this item (open the ItemView) | `Open idol` |
| `edit_sentence` | Localized sentence to edit this item, also used to open the page to edit this item (EditView)  | `Edit idol` |
| `delete_sentence` | Localized sentence to delete this item | `Delete idol` |
| `report_sentence` | Localized sentence to report this item, or open the page to report this item | `Report idol` |

These properties are only available for `MagiModel` and not `BaseMagiModel`.

#### MagiModel Images

If your model contains images, you may access the following properties for each of the images, where `image` is the name of the field:

| Key | Value | Example |
|-----|-------|---------|
| `image_url` | The full url of the `image` field | `//i.sample.com/static/uploaded/idols/Nozomi.png` |
| `http_image_url` | The full url of the `image` field with `http` (when `//` URLs are not supported, such as in emails or when sharing) | `http://i.sample.com/static/uploaded/idols/Nozomi.png` |

#### BaseAccount model

You have to provide the model class that corresponds to an account (see [Start a new website](#start-a-new-website)):

```python
   from magi.abstract_models import BaseAccount

   class Account(BaseAccount):
       class Meta:
           pass
```

By using `BaseAccount` and the default `AccountCollection` classes, MagiCircles will provide default templates and default behavior.

Some fields are not in `BaseAccount`, but if you add them in your `Account` model, templates and logic will know how to handle expected behavior:

| Expected field name | Recommended field type | Behavior |
|---------------------|------------------------|----------|
| `friend_id` | models.PositiveIntegerField(_('Friend ID'), null=True) | Displayed on the account details both on leaderboard and profile. |
| `show_friend_id` | models.BooleanField(_('Should your friend ID be visible to other players?'), default=True) | Will show/hide friend id displayed on the account details both on leaderboard, profile, and profile account tab "about". |
| `center` | models.ForeignKey('CollectibleCard', verbose_name=_('Center'), related_name='center_of_account', null=True, on_delete=models.SET_NULL) | Will select_related on profile only (not leaderboard) and display the center instead of the avatar on profile page accounts. <ul><li>`.image` is required</li><li>`.color` will be used as a class `panel-`, otherwise css color in preferences</li><li>`.art` will be used as an image background instead of side small image if present.</li></ul> |
| `screenshot` | models.ImageField(_('Screenshot'), help_text=_('In-game profile screenshot'), upload_to=uploadItem('account_screenshot'), null=True) | Used for self service verifications. Becomes required when user tries to jump 10+ levels and level is > 200. |

Note that even though you need the exact same field name, you can give it a label of your choice to have a display name that matches your needs.

If you want to personalize the templates and behavior of the default accounts, you can override variables and methods in both `Account` model and `AccountCollection` class.

Note that you can't remove any model field in `BaseAccount`. If you don't want to use one, just delete it from the fields in the form so it never gets populated.

#### Save choices values as integer rather than strings

Instead of saving your choice field as a string which values is from a list of string choices, use integers. It makes the database queries faster when filtering.

To do that, start your field name with `i_` like so:

```python
from magi.models import MagiModel, i_choices

class Card(MagiModel):

    POWER_CHOICES = (
        _('Happy'),
        _('Cool'),
        _('Rock'),
    )
    i_power = models.PositiveIntegerField(choices=i_choices(POWER_CHOICES), default=0)
```

It will be stored as an integer in the database, but you can easily access the human readable value with:

```python
card.power   # will return _('Cool')
card.i_power # will return 1
```

Note: your model must contain the list of choices with the right naming: `power` -> `POWER_CHOICES`, `super_power` -> `SUPER_POWER_CHOICES`.

Note: Do not use dictionaries, as the order is not guaranteed. You may use an OrderedDict instead of a list of tuples if needed.

If you need a clear way to compare the value, you may want to use untranslated values:

```python
if card.power == _('Happy'): # comparing translated strings doesn't work
   ...
```

To do so, you can provide a string key to your choices like so:

```python
from magi.models import MagiModel, i_choices

class Card(MagiModel):

    POWER_CHOICES = (
        ('happy', _('Happy')),
        ('cool', _('Cool')),
        ('rock', _('Rock')),
    )
    i_power = models.PositiveIntegerField(choices=i_choices(POWER_CHOICES), default=0)
```

You may now do:

```python
if card.power == 'happy':
   ...
```

And you can access the translated value with:

```python
card.t_power # translated "Happy"
```

If filtering by these choices is done very often, you may also set a db index:
```python
    i_power = models.PositiveIntegerField(choices=i_choices(POWER_CHOICES), default=0, db_index=True)
```

If you need to initialize or update the value outside of the context of a form, you may want to retrieve the integer value for a given string field. You can do so using the class method `get_i`:

```python
new_card = models.Card.objects.create(name='Julia', i_power=models.Card.get_i('power', 'rock'))
# or
new_card.i_power = models.Card.get_i('power', 'cool')
```

Similarly, you may retrieve the integer value from the string value using `get_reverse_i`:

```python
print models.Card.get_reverse_i('cool') # will print 1
```

Note: If you want to change your choices in the future, keep in mind that you might need to update your database manually to reflect the correct integer values.

You can still call your field `i_something` if you would like to enjoy the handy shortcuts provided by i_ but still want to store your value as something else than an integer. You just need to specify that your choices don't use i_choices using `SOMETHING_WITHOUT_I_CHOICES` like so:

```python
class Article(BaseMagiModel):
    LANGUAGE_CHOICES = (
        ('en', _('English')),
        ('es', _('Spanish')),
        ('ru', _('Russian')),
        ('it', _('Italian')),
    )
    LANGUAGE_WITHOUT_I_CHOICES = True
    i_language = models.CharField(_('Language'), max_length=10, choices=LANGUAGE_CHOICES, default='en')

print article.language # will print en
print article.i_language # will print en
print article.t_language # will print English
```

If you want to provide more details for a specific choice, you can use a sub dictionary and create the choices from there, then use `getInfoFromChoices` to retrieve the details easily like so:

```python
from magi.item_model import BaseMagiModel, getInfoFromChoices

class Article(BaseMagiModel):
    LANGUAGES = OrderedDict([
        ('ja', {
            'translation': _('Japanese'),
            'image': 'ja',
        }),
        ('en', {
            'translation': _('English'),
            'image': 'us',
        }),
        ('tw', {
            'translation': _('Taiwanese'),
            'image': 'tw',
        }),
        ('kr', {
            'translation': _('Korean'),
            'image': 'kr',
        }),
    ])
    LANGUAGE_CHOICES = [(_name, _info['translation']) for _name, _info in LANGUAGES.items()]
    i_language = models.PositiveIntegerField(_('Language'), choices=i_choices(LANGUAGE_CHOICES))
    language_image = property(getInfoFromChoices('language', LANGUAGES, 'image'))
    language_image_url = property(lambda _a: staticImageURL(_a.language_image, folder=u'language', extension='png'))
```

#### Store comma separated values

While the recommended Django way of storing a list of values in a model is to use a separate model with `ManyToMany`, it can be quite costly, since you will need extra queries to retrieve the values. For simple list of values like strings, you can store them as comma separated values.

To do so, start your field name with `c_`, like so:

```python
class Card(MagiModel):
    c_abilities = models.TextField(blank=True, null=True)
```

You may now access the CSV values in a convenient array like so:

```python
print card.abilities # ["fly", "dance", "heal"] (list)
print card.c_abilities # "fly","dance","heal" (string)
```

You may limit your CSV values to a list of choices like so:

```python
class Card(MagiModel):
    ABILITIES_CHOICES = (
        ('fly', _('Fly')),
        ('dance', _('Dance')),
        ('sing', _('Sing')),
        ('heal', _('Heal')),
    )
    c_abilities = models.TextField(blank=True, null=True)
```

Choices will not be enforced at the database level, but will help MagiForms show checkboxes.

You can get the list of translated CSV values using `t_`. It will return an ordered dictionary.

```python
card.t_abilities # { 'fly': _('Fly'), 'dance': _('Dance'), 'heal': _('Heal') }
```

If choices are not provided or are provided without translations, it's going to return a dictionary with the same value as key and value.

Some methods are available directly in MagiModel to add and remove values from the CSV:

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| add_c | Add strings to a CSV formatted c_something | field_name, to_add | None |
| remove_c | Remove strings from a CSV formatted c_something | field_name, to_remove | None |
| save_c | Completely replace any existing CSV formatted list into c_something | field_name, c | None |

You still need to call `save` on your instance to save the values in database.

Example:

```
card = model.Card.objects.get(id=1)
card.add_c('abilities', ['fly', 'dance'])
card.save()
```

#### Transform images before saving them

You may provide a `tinypng_settings` dictionary in your MagiModel to let your future MagiForm know how to transform your images before saving them.

For the full details of the dictionary, see ⎡[Optimize images with TinyPNG](#optimize-images-with-tinypng)⎦.

#### Check choices at form level instead of model level

It's recommended to add the choices in your field and let django validators and your database engine do the work for you.

If for some reason you can't or don't want to enforce it at the model level, you can enforce the choices at the form level (when using MagiForm):

```python
class Idol(MagiModel):
    LANGUAGE_SOFT_CHOICES = (
        ('en', _('English')),
        ('es', _('Spanish')),
    )
    i_language = models.CharField(max_length=10)
```

## MagiCollection

Collections available should be configured in `sample/magicollections.py`. It's a class that inherits from `MagiCollection`.

```python
from magi.magicollections import MagiCollection
from sample import models

class IdolCollection(MagiCollection):
    queryset = models.Idol.objects.all()
```

For each collection, you may also override the fields and methods. When overriding methods, it's recommended to call its `super`. Not doing so may cause unexpected behavior.

- Required settings:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| queryset | Queryset to get the items, don't forget to use `select_related` when you always use fields in foreign key (or use a cache in model). | *required* | models.Card.objects.all() |

- Highly recommended settings:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| title | Localized title for one item, visible for website's users  | Capitalized key | _('Card') |
| plural_title | Localized title for multiple items, visible for website's users | Capitalized key + 's' | _('Cards') |

- Other available settings:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| enabled | Is the collection enabled? When not, it won't be initialized at all and won't be available when getting a collection by name. | True | |
| item_buttons_classes | Only used in ListView and ItemView. Classes used for the buttons under items. Can be overriden in ItemView and ListView. | ['btn', 'btn-secondary', 'btn-lines'] | |
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
| show_collect_button | Should button(s) to add a collectible to your collection be displayed under each item? When multiple collectible exist, you may provide a dictionary of { collectibleCollectionName: boolean }. Can be overriden in ItemView and ListView. | True |
| show_edit_button | Should the edit button under each item be displayed? (Note: will not be displayed regardless of this setting if the edit view is disabled or the current user doesn't have permissions.) Can be overriden in ItemView and ListView. | True | |
| show_edit_button_superuser_only | If the edit button under each item is available for staff only, should it be shown for super users only? Note: it doesn't prevent staff to go to the edit page themselves if they have permission. Can be overriden in ItemView and ListView. | False | |
| show_item_buttons | Let MagiCircles display the buttons under each items automatically? Set to False if you'd like to insert the buttons yourself. To insert the buttons anywhere in your item template, use `{% include 'include/below_item.html' with buttons_only=True show_item_buttons=True %}`. Can be overriden in ItemView and ListView. | True | |
| show_item_buttons_as_icons | Should only icons be displayed in buttons under each items? False = also shows text. Can be overriden in ItemView and ListView. | False | |
| show_item_buttons_in_one_line | Show butons under each item in one line? False = displays buttons each under the other. Can be overriden in ItemView and ListView. | True | |
| show_report_button | Should the report button be displayed under each item? Note: Will not be displayed regardless of this setting if the item is not reportable or reports are disabled globally. Can be overriden in ItemView and ListView. | True | |
| types | See ⎡[Item Types](#item-types)⎦ | | |
| filter_cuteform | See ⎡[CuteForm](#cuteform)⎦. Can be overriden in ListView, AddView and EditView. | | |

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
| buttons_per_item | Used to display buttons below item, only for ItemView and ListView. Any new dictionary within the returned dictionary of buttons must contain the following keys: show, has_permissions, title, url, classes and may contain icon, image, url, open_in_new_window, ajax_url, ajax_title, extra_attributes. Can be overriden in ItemView and ListView. | view, request, context, item | Dictionary of dictionary | Will automatically determine and fill up buttons for collectibles, edit, report. |
| get_queryset | Queryset used to retrieve the item(s). Can be overriden per view. | queryset, parameters, request | Django queryset | The queryset given as parameters |
| form_class | Form class to add / edit an item. Doesn't have to be a method (see above). Can be overriden per view. | request, context | A form class | AutoForm |
| to_fields | See ⎡[to_fields method](#to_fields-method)⎦ |

### Views

![](http://i.imgur.com/SgWuilP.png)

For each of your collections, you may enable, disable or configure views. By default, all views are enabled.

- ⎡[List view](#list-view)⎦: Paginated list of items with filters/search
- ⎡[Item view](#item-view)⎦: A page with a single item, shows comments for this item
- ⎡[Add view](#add-view)⎦: Page with a form to add a new item
- ⎡[Edit view](#edit-view)⎦: Page with a form to edit and delete an item

For each view, you may also override the fields and methods. When overriding methods, it's recommended to call its `super`.

```python
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from magi.magicollections import MagiCollection

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
from magi.magicollections import MagiCollection

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
| get_queryset | Queryset used to retrieve the item(s). Can be specified in collection. | queryset, parameters, request | Django queryset | `get_queryset` in MagiCollection |
| check_permissions | Check if the current user has permissions to load this view | request, context | None, should raise exceptions when the user doesn't have permissions. | Will check permissions depending on the views settings (such as `staff_required`, etc.), and either raise `PermissionDenied` or `HttpRedirectException` |
| check_owner_permissions | Only for ItemView and EditView, will be called after getting the item and check if the current user has permissions to load this view | request, context, item | None, should raise exceptions when the user doesn't have permissions | Will check permissions depending on the view settings (`owner_only`) and either raise `PermissionDenied` or `HttpRedirectException`.

- All views provide the following methods (not meant to be overriden):

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| has_permissions | Calls `check_permissions` and `check_owner_permissions`, catches exceptions and returns True or False | request, context, item=None | True or False |
| get_page_title | Get the title of the page | None | localized string |

#### List view

![](http://i.imgur.com/p2O8Dh1.png)
![](http://i.imgur.com/E1lrmtc.png)

List view for a staff member will hide all the staff buttons by default and you can show them using the bottom left button.

![](http://i.imgur.com/Y7uVbFb.png)

- List views contain the following settings (can be overriden):

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| filter_form | Django form that will appear on the right side panel and allow people to search / filter. It's recommended to make it inherit from `MagiFilter`. | None (no side bar) | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L8) |
| ajax_pagination_callback | The name of a javascript function to call everytime a new page loads (including the first time) | None | "updateCards" (See [Example](https://gist.github.com/db0company/b9fde532eafb333beb57ab7903e69749#file-magicirclesexamples-js-L1)) |
| alt_views | See ⎡[Alt views](#alt-views)⎦. | [] | |
| auto_reloader | Should items be automatically reloaded when there is a change in ajax? (for example, when an item is edited through a modal within the same page) | True | |
| display_style | Choice between `rows` and `table` | `rows` | |
| display_style_table_fields | When `display_style` is `table`, provide the list of fields displayed in the table | ['image', 'name'] | |
| item_buttons_classes | Classes used for the buttons under items. Can be specified in collection. | Value from collection | |
| item_template | Path of the HTML template in `sample/templates/items/` to display the item (without `.html`). If you don't want to use the default one, it's highly recommended to use the standard name for custom templates. To do so, use `custom_item_template` in `magi.utils`. | "default_item_in_list" | "cardDetails" |
| item_padding | Padding (in px) around the item, only applied when using the default template. | 20 | |
| before_template | Name of a template to include between the title (if shown) and the add buttons (if any) and results (without `.html`) | None | "include/beforeCards" |
| after_template | Name of a template to include at the end of the list, when the last page loads (without `.html`), if you provide something in `extra_context` for this template, first check `if context['is_last_page']: ...` | None | "include/afterCards" |
| no_result_template | Name of a template to show if there's no results to show, otherwise it will just show "No result" in a bootstrap `alert-info` | None | "include/cardsNoResult" |
| per_line | Number of elements displayed per line (1, 2, 3, 4, 6, 12), make sure it's aligned with the page_size or it'll look weird :s | 3 | |
| col_break | Minimum size of the column so when the screen is too small it only shows one per line, options are 'xs' (never breaks), 'sm' (= 768px), 'md' (= 992px), 'lg' (= 1200px)  | 'md' | |
| page_size | Number of items per page | 12 | |
| show_edit_button | Should a button to edit the item be displayed under the item (if the user has permissions to edit)? Set this to `False` is your template already includes a button to edit the item. | True | |
| show_item_buttons_as_icons | When buttons are enabled (edit, report, collectible, ...), should the buttons be displayed as icons or as full width buttons? | False | |
| authentication_required | Should the page be available only for authenticated users? | False | |
| distinct | When retrieving the items from the database, should the query include a `distinct`? ⚠️ Makes the page much slower, only use if you cannot guarantee that items will only appear once. | False | |
| add_button_subtitle | A button to add an item will be displayed on top of the page, with a subtitle. | _('Become a contributor to help us fill the database') | _('Share your adventures!') |
| show_title | Should a title be displayed on top of the page? If set to `True`, the title will be the `plural_title` in the collection. | False | |
| full_width | By default, the page will be in a bootstrap container, which will limit its width to a maximum, depending on the screen size. You may change this to `True` to always get the full width | False | |
| show_relevant_fields_on_ordering | By default, when an `ordering` is specified in the search bar, the specified ordering field will be displayed under each item (see ⎡[to_fields method](#to_fields-method)⎦). | True | |
| hide_sidebar | By default, the side bar will be open when you open the page. You may leave it close by default, but keep in mind that it's very unlikely that your users will find it by themselves. | False | |
| filter_cuteform | See ⎡[CuteForm](#cuteform)⎦. Can be specified in collection. | | |
| default_ordering | String name of a field (only one) | '-creation' | 'level' |
| show_collect_button | Should button(s) to add a collectible to your collection be displayed under each item? When multiple collectible exist, you may provide a dictionary of { collectibleCollectionName: boolean }. Can be specified in collection. | Value from collection |
| show_edit_button | Should the edit button under each item be displayed? (Note: will not be displayed regardless of this setting if the edit view is disabled or the current user doesn't have permissions.) Can be specified in collection. | Value from collection | |
| show_edit_button_superuser_only | If the edit button under each item is available for staff only, should it be shown for super users only? Note: it doesn't prevent staff to go to the edit page themselves if they have permission. Can be specified in collection. | Value from collection | |
| show_item_buttons | Let MagiCircles display the buttons under each items automatically? Set to False if you'd like to insert the buttons yourself. To insert the buttons anywhere in your item template, use `{% include 'include/below_item.html' with buttons_only=True show_item_buttons=True %}`. Can be specified in collection. | Value from collection | |
| show_item_buttons_as_icons | Should only icons be displayed in buttons under each items? False = also shows text. Can be specified in collection. | Value from collection | |
| show_item_buttons_in_one_line | Show butons under each item in one line? False = displays buttons each under the other. Can be specified in collection. | Value from collection | |
| show_report_button | Should the report button be displayed under each item? Note: Will not be displayed regardless of this setting if the item is not reportable or reports are disabled globally. Can be specified in collection. | Value from collection | |

See also: [settings available in all views](#all-views).

- List views contain the following methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| buttons_per_item | Used to display buttons below item. Any new dictionary within the returned dictionary of buttons must contain the following keys: show, has_permissions, title, url, classes and may contain icon, image, url, open_in_new_window, ajax_url, ajax_title. Can be specified in collection. | request, context, item | Dictionary of dictionary | Method from collection will be called |
| table_fields_headers | When `display_style` is `table`, provide a list of headers at the top of the table. | fields, view=None | List of pairs (name, verbose_name) | Will get them from the models verbose_names and make them from the field name otherwise (overall_max -> Overall max) |
| table_fields_headers_sections | When `display_style` is `table`, allows to use colspans in table headers and have 2 layers of headers if needed | view=None | List of tuple (name, verbose_name, colspan) | [] |
| foreach_item | Function called for all the elements about to be displayed, that takes the item position, the item and the context ([example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L23)). If you can, provide a property inside the model's class instead, to avoid an extra loop. | index, item, context | None | None |
| show_add_button | Should a button be displayed at the beginning to let users add new items (if they have the permission to do so)? | request | Boolean | returns `True` |
| to_fields | See ⎡[to_fields method](#to_fields-method)⎦ |
| ordering_fields | See ⎡[to_fields method](#to_fields-method)⎦ |
| table_fields | See ⎡[to_fields method](#to_fields-method)⎦ |
| top_buttons | Will be called to display buttons at the beginning of the list view. Any new dictionary within the returned dictionary of buttons must contain the following keys: show, has_permissions, url, classes, title and may contain ajax_url, open_in_new_window, icon, image, subtitle | request, context | Dictionary of dictionary | Will automatically determine which add buttons should be displayed. |

See also: [methods available in all views](#all-views).

- List views provide the following methods (not meant to be overriden):

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| plain_default_ordering | Transforms the `default_ordering` of the list view into a simple string, without the reverse setting and extra options. Example: `'-level,id'` becomes `'level'`. Used as the pre-selected value in the filter form. | None | string |

See also: [methods available in all views](#all-views).

- If you provide your own template for `item_template`, the context will contain the following:
todo

#### Item view


![](http://i.imgur.com/mObTPc4.png)
![](http://i.imgur.com/19bYwFm.png)
![](http://i.imgur.com/REkJzTT.png)

- Item views contain the following settings (can be overriden):

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| item_buttons_classes | Classes used for the buttons under items. Can be specified in collection. | Value from collection | |
| template | Path of the HTML template in `sample/templates/items/` to display the item (without `.html`). By default, will use the defaut view with the image on top and the list of fields below it. See ⎡[to_fields method](#to_fields-method)⎦ for more details about the `default` template. If you don't want to use the default one, it's highly recommended to use the standard name for custom templates. To do so, use `custom_item_template` in `magi.utils`. | "default" | "cardItem" |
| item_padding | Padding (in px) around the item, only applied when using the default template. | 20 | |
| top_illustration | If the `default` template is used, it will show either the `image` in the object or its name. You may display something else by specifying the path of a HTML template (full path in template folder), without `.html`. | None | `include/topCard` |
| show_edit_button | Should a button to edit the item be displayed under the item (if the user has permissions to edit)? Set this to `False` is your template already includes a button to edit the item. | True | |
| comments_enabled | Should we display a comment section below the item? | True | |
| share_enabled | Should we display share buttons below the item (only with default template)? | True | |
| full_width | By default, the page will be in a bootstrap container, which will limit its width to a maximum, depending on the screen size. You may change this to `True` to always get the full width | False | |

See also: [settings available in all views](#all-views).

- Item views contain the following methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| buttons_per_item | Used to display buttons below item. Any new dictionary within the returned dictionary of buttons must contain the following keys: show, has_permissions, title, url, classes and may contain icon, image, url, open_in_new_window, ajax_url, ajax_title. Can be specified in collection. | request, context, item | Dictionary of dictionary | Method from collection will be called |
| get_item | How is the item retrieved using the `pk` (=id) provided in the URL? For example, in the URL `/card/12/super-rare-lily/`, `pk` will be `12` | request, pk (in URL) | a dictionary that will be used with the queryset to get a single item | `{ 'pk': pk }` |
| reverse_url | Allows you to have URLs with just a string and find the item with thout, instead of the id. For example, the default URL of a profile is `/user/1/db0/`, but with this, you can make `/user/db0/` and still be able to retrieve the corresponding user, without knowing its id. | string (text in URL, for example if the URL is `/user/tom/`, this will be `'tom'`) | a dictionary that will be used with the queryset to get a single item | None |
| to_fields | See ⎡[to_fields method](#to_fields-method)⎦ |

See also: [methods available in all views](#all-views)⎦.

- If you provide your own template for `template`, the context will contain the following:
todo

#### Add view

![](http://i.imgur.com/CjYBkCO.png)

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
| filter_cuteform | See ⎡[CuteForm](#cuteform)⎦. Can be specified in collection. | | |
| max_per_user | By default, users can add as many as they'd like. You can restrict to a max number of added per user to avoid spam. | None | 3000 |
| max_per_user_per_day | Will limit how many a user can add within 24 hours. | None | 24 |
| max_per_user_per_hour | Will limit how many a user can add within an hour. | None | 3 |
| unique_per_owner | Will specify that only one of this item can be added. Will redirect to edit page when trying to add again. | False | |

See also: [settings available in all views](#all-views).

- Add views contain the following methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| before_save | Function called before the form is saved. Not recommended, overload `save`in your form instead | request, instance, type=None | instance | Just returns the instance |
| after_save | Function called after the form is saved. Not recommended, overload `save`in your form instead | request, instance, type=None | instance | Just returns the instance |
| form_class | Form class to add an item. Doesn't have to be a method (see above). Can be specified in collection. | request, context | A form class | AutoForm |
| quick_add_to_collection | (Collectibles only) Will automatically load javascript utility "directAddCollectible" to add to your collection in one click. Will load the form and attempt to submit it in the background, so will only work if all the fields in the form are optional or have a default selected/entered value when the form is loaded. Combined with “unique_per_owner”, will allow users to easily add or delete with one click. | request, parent_item | True or False | False |
| redirect_after_add | Where should the user be redirected after the item has been added successfully? | request, item, ajax | URL to redirect to | Redirect to the item view of the item that has been created if the item view is enabled, otherwise to the list view |

See also: [methods available in all views](#all-views).

#### Edit view

![](http://i.imgur.com/oaSXXyj.png)

- Edit views contain the following settings (can be overriden):

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| otherbuttons_template | Template path (without `.html`) for extra buttons at the end of the form | None | "include/cardsExtraButtons" |
| after_template | Name of a template to include after the form | None | "include/afterAddCard" |
| allow_delete | Should we show a button to delete the item as well? | False | |
| savem2m | Should we call save_m2m to save the manytomany items after saving this model? | False | |
| back_to_list_button | Should we display a button to go back to the list view at the end of the form? | True | |
| multipart | Should the HTML form allow multipart (uploaded files)? Can be specified in collection. | False | |
| form_class | Form class to edit an item. Can be a method (see below). Can be specified in collection. | AutoForm | | filter_cuteform | See ⎡[CuteForm](#cuteform)⎦. Can be specified in collection. | | |
IdolForm |

See also: [settings available in all views](#all-views).

- Edit views contain the following methods (can be overriden):

| Name | Description | Parameters | Return value | Default |
|------|-------------|------------|--------------|---------|
| before_delete | Function called before the item gets deleted. | request, instance, ajax | None | Nothing |
| before_save | Function called before the form is saved. Not recommended, overload `save`in your form instead | request, instance, type=None | instance | Just returns the instance |
| after_save | Function called after the form is saved. Not recommended, overload `save`in your form instead | request, instance, type=None | instance | Just returns the instance |
| form_class | Form class to edit an item. Doesn't have to be a method (see above). Can be specified in collection. | request, context | A form class | AutoForm |
| redirect_after_edit | Where should the user be redirected after the item has been edited successfully? | request, item, ajax | URL to redirect to | Redirect to the item view of the item that has been edited if the item view is enabled, otherwise to the list view |
| redirect_after_delete | Where should the user be redirected after the item has been deleted successfully? | request, item, ajax | URL to redirect to | Redirect to the list view |
| get_item | How is the item retrieved using the `pk` (=id) provided in the URL? For example, in the URL `/card/edit/12/`, `pk` will be `12` | request, pk (in URL) | a dictionary that will be used with the queryset to get a single item | `{ 'pk': pk }` |

See also: [methods available in all views](#all-views).

### MagiCollection utils

#### Collectible

![](http://i.imgur.com/r3FrVK5.png)

To make a collection collectible, you need to provide a [model](#model). The model should always have either an `owner` or an `account` foreign key, allowing users to collect them.

```python
from magi.models import AccountAsOwnerModel

class CollectibleCard(AccountAsOwnerModel):
    collection_name = 'collectiblecards'

    account = models.ForeignKey(Account, related_name='collectedcards')
    card = models.ForeignKey(Card, related_name='collectiblecards')

    ...
```

Then specify this model in the collection you want to make collectible with that model:

```python
from magi.magicollections import MagiCollection
from sample import models

class CardCollection(MagiCollection):
    collectible = models.CollectibleCard
```

You can customize the MagiCollection of the collectible itself:

```python
from magi.magicollections import MagiCollection
from sample import models

class CardCollection(MagiCollection):
    collectible = models.CollectibleCard

    def collectible_to_class(self, model_class):
	cls = super(CardCollection, self).collectible_to_class(model_class)
        class _CollectibleCard(cls):
            icon = 'world'
        return _CollectibleCard
```

When customizing your collectible's MagiCollection, keep in mind that types are not compatible and shouldn't be used in a collectible's MagiCollection.

You may provide multiple collectibles for one collection. For example, you may want to allow users to save the cards they own and their favorite cards. To do so, you can provide a list to collectible. The name of the collections will be infered from `collection_name` variable within the model.

```python
from magi.magicollections import MagiCollection
from sample import models

class CardCollection(MagiCollection):
    collectible = [
        models.CollectibleCard,
        models.WishedCard,
    ]
```

The selector to the item foreign key inside the collectible item model will be inferred from the model name (`Card` model -> `card`) but you can specify it within the collectible item model:

```shell
class StarterCard(AccountAsOwnerModel):
    collection_name = 'startercard'
    selector_to_collected_item = 'starter'

    starter = models.ForeignKey(Card)
```

#### CuteForm

![](http://i.imgur.com/nL7JVGw.png)

CuteForm is a Javascript library that transforms your form `<select>` into selectable images. [Learn more](http://db0company.github.io/CuteForm/).

Because it is used a lot by forms and filter forms in MagiCircles, an integration is provided directly within the collections, so you don't need to add extra Javascript dependencies.

The setting `filter_cuteform` in the collection itself, or in the list view, add view and item view seperately allow you to customize your cuteform settings.

You may also configure cuteform for your own form in your own standalone pages or anywhere else using the utility function `cuteFormFieldsForContext`, which takes the same dictionary expected by `filter_cuteform` in collection, as well as the context and an optional `form` object.

Dictionary of:
- Key = field name
- Value = dictionary of:
    - `type`: CuteFormType.Images, .HTML, .YesNo or .OnlyNone, will be images if not specified
    - `to_cuteform`: 'key' or 'value' or lambda that takes key and value, will be 'key' if not specified
    - `choices`: list of pair, if not specified will use form
    - `selector`: will be #id_{field_name} if not specified
    - `transform`: when to_cuteform is a lambda: CuteFormTransform.No, .ImagePath, .Flaticon, .FlaticonWithText
    - `image_folder`: only when to_cuteform = 'images' or transform = .ImagePath, will specify the images path

#### Alt views

List views can have alternative views. For example, you may want to provide a condensed table of data to show stats.

Your alt view must provide:
- `verbose_name`

You can provide (which will override value in list view):
- `template`
- `display_style`
- `display_style_table_fields`
- `per_line`

```python
class CardCollection(MagiCollection):
    ...
    class ListView(MagiCollection.ListView):
        ...
        alt_views = MagiCollection.ListView.alt_views + [
            ('statistics', {
                'verbose_name': _('Statistics'),
                'template': 'default_item_table_view',
                'display_style': 'table',
                'display_style_table_fields': [
                    'image', 'image_trained',
                    'smile_min', 'smile_max', 'smile_trained_max',
                    'pure_min', 'pure_max', 'pure_trained_max',
                    'cool_min', 'cool_max', 'cool_trained_max',
                ],
            }),
        ]
```

#### Item types

![](http://i.imgur.com/AUcuMU8.png)

You may display different forms and URLs to add an item depending on "types".

When you use types on a collection, its model must have a `type` (ie we should be able to do `instance.type`), which can be stored in database or returned with `@property`. It'll be used to retrieve the right form when editing.

![](http://i.imgur.com/vNDaGbk.png)

For example, let's say we have 3 types of cards: Normal, Rare and Super Rare and we want to use different forms for those. Our collection will look like that:

```python
class CardCollection(MagiCollection):
    ...
    types = {
        'normal': { ... },
        'rare': { ... },
        'superrare': { ... },
    }
```

For each type, you may specify the following settings in its dictionary:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| form_class | FormClass to add/edit the item, must take request (make it inherit from FormWithRequest), can be a function that takes request, context and collection | *required* | [Example](https://gist.github.com/db0company/819ec1900fb207f865be69b92ce62c8e#file-magicirclesexamples-py-L44) |
| title | Localized title of the type | type (key) | _('Rare') |
| image | Path of an image displayed near the title of the form that illustrates the type | None | "" |

The type will be passed to the formClass when it's initialized, which allows you to reuse the same form class for all your types if you'd like.

#### to_fields method

`to_fields` is a method in collections. It can also be overrided per view for ItemView and ListView.

- Where is it called?
    - **ListView:** Will be called when `ordering` is specified to show the field(s) details, with `only_fields` in parameters. For example, if you order the list by level, the level is going to be displayed under the item, because it's very likely that you'll want to compare that between the items.
    - **ListView:** Will be called when `display_style` is `table`, with force_all_fields=True and only_fields = the value of `display_style_table_fields`.
    - **ItemView:** If you use the default template, it will show a table with all the fields returned by this function.
- Can it be overriden?
    - You may override this function, but you should always call its `super`.
- Parameters
    - `view, item, to_dict=True, only_fields=[], icons={}, images={}, force_all_fields=False, order=[], extra_fields=[], exclude_fields=[]`
    - The same method in ItemView and ListView will take the same parameters except the view.
    - `item` is the item object, an instance of an `MagiModel`
    - `icons` is a dictionary of the icons associated with the fields
    - `images` is a dictionary of the images associated with the fields
    - (DEPRECATED SOON) `to_dict` will return a dict by default, otherwise a list or pair. Useful if you plan to change the order or ionsert items at certain positions.
    - `only_fields` if specified will ignore any other field
    - `force_all_Fields` will return empty fields when not finding fields data, should be coupled with `only_fields`
    - `order` lets you provide an ordering of the fields, all other fields will be added at the end
    - `extra_fields` lets you provide fields that can't be determined automatically from the model
    - `exclude_fields` will exclude the fields with the given name
- Return value
    - Returns a dictionary of key = field name, value = dictionary with:
        - verbose_name
        - value
        - type
        - optional: icon, image, link, link_text, ajax_link, images
    - Available types:
        - text
        - title_text (needs 'title')
        - text_annotation (needs 'annotation', which corresponds to a small, grey text under the main text)
        - image (needs images with 'value', 'ajax_link')
        - images
        - bool
        - list ('value' becomes a lit of values)
        - link (needs 'link_text')
        - image_link (needs 'link', 'link_text')
        - images_links (needs images with 'value', 'ajax_link', 'link', 'link_text')
        - button (needs 'link_text')
        - text_with_link (needs 'link' and 'link_text', will show a 'View all' button)
        - timezone_datetime (needs 'ago' and 'timezones' list. can be 'local')
        - long_text
        - html
- Default
    - Will automatically guess what should be displayed from the model fields and `reverse`  in the model if specified.

You may override it in both the collection and the views. As long as you call the super, both logics will be called.

In ListView, if you want to separate functions called for ordering or table by using `ordering_fields` and `table_fields`. The default behavior for these 2 functions is to call `to_fields`.

In ListView, when ordering is specified:

![](http://i.imgur.com/z1ei25k.png)

In ItemView, when using the default template:

![](http://i.imgur.com/ikMoXCq.png)

#### AccountCollection

You can override the following variables in account collection:

| View | Name | Type | Description |
|------|------|------|-------------|
| Add view | simpler_form | Form class | If you provide it, it will use it instead of the form_class by default and display an "Advanced" button to switch back to the full form. |

You can override the following methods in account collection:

| View | Name | Parameters | Return value | Description |
|------|------|------------|--------------|-------------|
| None | get_profile_account_tabs | request, context, account | Ordered dict that: <ul><li>MUST contain name, callback (except for about)</li><li>May contain icon, image, callback</li></ul> | List of tabs displayed on profile page, called by ItemView of User (corresponds to profile view) |

## MagiForm

- Inherit from `MagiForm`
- Used by add view and/or edit view
- Optional, with default: `AutoForm`

```python
from django import forms
from magi.forms import AutoForm

class EventForm(AutoForm):
    start_date = forms.DateField(label=_('Beginning'))
    end_date = forms.DateField(label=_('End'))

    class Meta:
        model = models.Event
        fields = '__all__'
        optional_fields = ('end_date')
        save_owner_on_creation = True
```

- Will make fields in `optional_fields` optional, regardless of db field
- Will show the correct date picker for date fields
- Will replace any empty string with None for better database consistency
- Will use tinypng to optimize images and will use settings specified in models
- When `save_owner_on_creation` is True in Meta form object, will save the field `owner` using the current user

MagiForm's behavior is similar to django's form, while `AutoForm` will try to detect automatically what should be the fields in the form.

![](http://i.imgur.com/CjYBkCO.png)

If you want to add some extra logic at the initialization of the form, you can override `__init__`:

```python
class CardForm(AutoForm):
    def __init__(self, *args, **kwargs):
        super(CardForm, self).__init__(*args, **kwargs)
        self.fields['skill_details'].label = _('Skill details')

    ...
```

If you want to add some extra logic before saving the item in the dabatase, you can override `save`:

```python
class CardForm(AutoForm):
    def save(self, commit=False):
	instance = super(CardForm, self).save(commit=False)
    instance.score = instance.score / 100
    if commit:
            instance.save()
	return instance

    ...
```

If you want to do something depending on a specific field that changed, you can save the previous value in `__init__` and add your logic in `save`. This can be useful to update cached foreign keys.

```python
class CardForm(AutoForm):
    def __init__(self, *args, **kwargs):
        super(CardForm, self).__init__(*args, **kwargs)
        self.previous_member_id = None if self.is_creating else self.instance.member_id

    def save(self, commit=False):
        instance = super(CardForm, self).save(commit=False)
        if self.previous_member_id != instance.member_id:
            instance.update_cache_member()
        if commit:
            instance.save()
        return instance

    ...
```

## MagiFilter


![](http://i.imgur.com/exJJP53.png)

- Inherit from `MagiFiltersForm`
- Used by list view
- Optional, will not show a sidebar when not provided

While `MagiFiltersForm` is very similar to `MagiForm`, it doesn't have any logic to "save" an item.

It provides a method `filter_queryset` that takes a queryset, the parameters (as a dictionary), the current request and returns a queryset.

If your collection provides alt views, a selector to pick the view will also be available in the side bar filters.

### Search and ordering

Search and ordering fields are provided by default, but you need to specify `search_fields` and `ordering_fields` to enable them.

```python
from magi.forms import MagiFiltersForm
from sample import models

class CardFilterForm(MagiFiltersForm):
    search_fields = ['name', 'skill_name']
    ordering_fields = [
        ('id', _('ID')),
        ('performance_max', _('Performance')),
    ]

    class Meta:
        model = models.Card
```

### Configure fields

For most fields, the default behavior of `MagiFiltersForm` is enough. Fields like NullBooleanFields or MultipleChoiceFields are already handled.

But for some fields that are not direct fields of the model or to handle special cases, you may provide some configuration for that field.

To do so, just provide an attribute `name_filter` where `name` is the corresponding field name. It has to be an instance of `MagiFilter`, to which you can pass the following named parameters:

| Name | Description | Default | Example |
|------|-------------|---------|---------|
| to_queryset | function that takes form, queryset, request, value and returns a queryset. Optional, will filter automatically. `selector`, `selectors` and `multiple` are ignored when specified. | None (default behavior) | lambda form, queryset, request, value: queryset.filter(name__in=['a', 'b'] if value == 'a_or_b' else queryset) |
| selector | will be the name of the field by default | None (will use the name of the filter field) | 'owner__username' |
| selectors | same as selector but works with multiple values. | None (will use selector) | ['card__name', 'card__japanese_name'] |
| to_value | function that takes the value and transforms the value if needed. May receive a string or a list. | None (will not transform the value) | lambda value: value + 1 |
| multiple | allow multiple values separated by commas. Set to `False` if your value may contain commas. | True | |
| operator_for_multiple | When multiple is enabled, what should be the operation? Choices are: `OrContains`, `OrExact` or `And`. | Depends on field type. | MagiFilterOperator.OrExact |
| allow_csv | When `multiple` is unabled or the field is a MultipleChoiceField, is it allowed to provide values as comma separated? Example: `?rarity=SR,UR`. When csv is not allowed, values must be provided as a list like so: `?rarity=SR&rarity=UR` | True | |
| noop | Will not affect the queryset. Useful when you need a GET parameter that does something else than filtering, such as changing the way items are displayed. | False | |

Example:

```python
from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH
from magi.forms import MagiFiltersForm
from bang import models

class CardFilterForm(MagiFiltersForm):
    member_band = forms.ChoiceField(choices=BLANK_CHOICE_DASH + models.BAND_CHOICES, initial=None, label=_('Band'))
    member_band_filter = MagiFilter(selector='member__i_band')

    class Meta:
        model = models.Card
        fields = ('member_id', 'member_band')

```

Enabled Pages
===

![](http://i.imgur.com/eWoovuB.png)

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

All your pages must contain the global context, which you can override to add your own global context settings. It's recommended to use the same globalContext function in your views than the one specified in your [website settings](#website-settings).

```python
from magi.utils import globalContext as magi_globalContext

def globalContext(request):
    context = magi_globalContext(request)
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

By default, if you use the global context, all your pages will have a context that contains the following:
todo

In your page's template, you may override the following blocks:
todo

You may add some variables in your context which will automatically be used and may have useful behaviors for you:
todo

Default pages and collections
===

Some pages and collections are provided by default.

## Default pages

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
| /help/ | Yes | The homepage of the help pages of the website, with FAQ and guides. |
| /help/{wiki_url}/ | Yes | A specific page in the help pages. |
| /wiki/ | No | The homepage of the wiki of the website, with FAQ and guides. |
| /wiki/{wiki_url}/ | No | A specific page in the wiki. |
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

- Full details of the configuration of each page in: `magi/default_settings.py`
- Full details of the implementation of each page in `magi/views.py`

## Default collections

| Name | Class | Model | Details |
|------|-------|-------|---------|
| user | UserCollection | User | <ul><li>Reportable.</li><li>ItemView corresponds to the profile.</li><li>AddView is disabled (use signup page instead).</li><li>EditView is staff only, users may edit their profiles using the settings page.</li><li>ListView is enabled but likely to be used mostly when showing followers/following or likes for an activity, in an ajax popup.  |
| activity | ActivityCollection | Activity | <ul><li>Activities posted by the community, with likes and comments.</li><li>Has an empty shortcut that corresponds to the homepage, allowing the homepage to be the list of activities.</li><li> Reportable.</li></ul> |
| account | AccountCollection | `ACCOUNT_MODEL` in settings | <ul><li>Also called "leaderboard", corresponds to the list of accounts.</li><li>That's the page users see to discover other users. It links to the profiles.</li><li>ItemView is enabled but is very likely to be used only in reports view.</li><li>Reportable.</li></ul> |
| notification | NotificationCollection | Notification | <ul><li>Only ListView is enabled.</li><li>Available as a small popup from the nav bar or as a separate page.</li><li>Notifications are generated automatically when something happens that might interest the user.</li></ul> |
| report | ReportCollection | Report | <ul><li>Uses collection types, with types corresponding to reportable collections.</li><li>People who report can see/edit their own reports, but only staff can list all the reports and take actions.</ul> |

- Default collections are in `magi/magicollections.py`

### Collections disabled by default

| Name | Class | Model | Details |
|------|-------|-------|---------|
| donate | DonateCollection | DonationMonth | Page with a link to allow user to donate money to support the development and maintenance of the website. Pages to add / edit months allow staff members to keep track of the budget and show a % of funds + all the donators for that month. |
| badge | BadgeCollection | Badge | Badges can be used to show recognition when a member of the community does something. It's mostly used for donators, but can also be used as prizes when participating in a contest or for annual community rewards. |

These 2 collections allow [the author of MagiCircles](http://db0.company) to monetize the platforms, pay for the server and pay for the development time needed to make these websites available.

For this reason, it is not allowed to enable these 2 collections if you are using MagiCircles yourself. Only [the author of MagiCircles](http://db0.company) is allowed to monetize websites that use MagiCircles, except when given excplicit authorization. [Learn more](#join-the-magicircles-family).

## Enable/Disable/Configure default pages and collections

You may enable or disable them at your convenience, or override their default configurations.

Disable a page in `sample/settings.py`:
```python
ENABLED_PAGES = DEFAULT_ENABLED_PAGES
ENABLED_PAGES['help']['enabled'] = False
```

Disable a collection in `sample/magicollections.py`:
```python
from magi.magicollections import ReportCollection as _ReportCollection

class ReportCollection(_ReportCollection):
    enabled = False
```

Change something in an existing collection:
```python
from magi.magicollections import AccountCollection as _AccountCollection

class AccountCollection(_AccountCollection):
    icon = 'heart'

    class ListView(_AccountCollection.ListView):
        show_edit_button = False
```

Nav bar lists
===

![](http://i.imgur.com/5X1V7ef.png)

You might not want all your links to pages and collections to be on the nav bar itself, but in dropdown lists instead.

To achieve that, you may specify a `navbar_link_list` in your page or collection settings. It's a string that corresponds to the name of a list.

By default, your website will already contain 2 lists: `you` and `more`.

You may add more lists in your settings:

```python
from magi.default_settings import DEFAULT_ENABLED_NAVBAR_LISTS

ENABLED_NAVBAR_LISTS = DEFAULT_ENABLED_NAVBAR_LISTS
ENABLED_NAVBAR_LISTS['stuff'] = { ... }
```

The settings of a navbar list may contain:

| Key | Value | Default | Example |
|-----|-------|---------|---------|
| title | Localized name of the list or function that takes the context and return a string | *required* |
| icon | String name of a [flaticon](#flaticon) that illustrates the nav bar list | None | 'fingers' |
| image | Path to image that illustrates the nav bar list | None | 'stuff.png' |

API
===

![](http://i.imgur.com/3ZIP11o.png)

:warning: This is a work in progress. The following guide doesn't work yet. Currently, API endpoints have be done manually.

API endpoints are based on Django-Rest-Framework. Refer to [the documentation](http://www.django-rest-framework.org/) to learn more.

MagiCircles provides the following:
- [MagiSerializer](#magiserializer)

## MagiSerializer

Make your serializers inherit from `MagiSerializer` instead of the regular `ModelSerializer`.

It will:
- Save the owner when you create the object if `save_owner_on_creation` is set to `True` in Meta
- Compress the images with TinyPNG before saving them

You may override `post_save` and `pre_save` (and call the super for each) in your serializer to add extra logic.

- `pre_save` takes validated_data
- `post_save` takes validated_data and the instance created/edited

## ImageField

Use `ImageField` to return the full URLs of the images in your API endpoints:

```python
from api.serializers import MagiSerializer, ImageField

class CardSerializer(MagiSerializer):
    image = ImageField(required=True)

    class Meta:
        models = models.Card
        fields = ('id', 'name', 'image')
```

Your endpoint will return:

```json
{
   id: 501,
   name: "Go Ahead!",
   image: "http://i.bandori.party/u/c/501Kasumi-Toyama-Pure-LYS54o.png",
}
```

## IField

If you followed the recommended way to store choices using integers, you might want to return the human readable values in your endpoints. `IField` can help with that.

```python
from api.serializers import MagiSerializer, IField

class CardSerializer(MagiSerializer):
    i_attribute = IField(models.ENGLISH_ATTRIBUTE_DICT)

    ...
```

With this, for example, even though the value saved in the database is `1`, the value returned in the json object will be "Smile". Similarly, the value expected when creating/updating will be "Smile" and not `1`.

## Full Example

```python
from rest_framework import viewsets
from api import permissions
from api.serializers import MagiSerializer

class CardSerializer(MagiSerializer):
    class Meta:
        model = models.Card
        save_owner_on_creation = True
        fields = ('id', 'name', 'japanese_name')

class CardViewSet(viewsets.ModelViewSet):
    queryset = models.Card.objects.all()
    serializer_class = CardSerializer
    permission_classes = (api_permissions.IsStaffOrReadOnly, )
```

Utils
===

## Python

### Models upload

```python
from magi.utils import uploadToRandom, uploadItem

class Idol(MagiModel):
    image = models.ImageField(upload_to=uploadItem('i'))
    other_image = models.ImageField(upload_to=uploadToRandom('i'))
```

- `uploadItem` will use the `__unicode__` function of the model to name the file, in addition to random characters (to make sure browsers load the latest uploaded images when re-written). It is useful for SEO purposes and recommended for the main collections (cards, characters, ...).
- `uploadRandom` will just generate a random string as the file name. It's only recommended when the `__unicode__` of the model is meaningless or for user-submitted content (activities for example).

### Access MagiCollections

- From anywhere:
  ```python
  from magi.utils import getMagiCollections, getMagiCollection

  print len(getMagiCollections())
  print getMagiCollection('idol').name
  ```
- From an instance of a model (`MagiModel`):
  ```python
  from magi import models

  user = models.User.objects.get(id=1)
  print user.collection.name
  ```
  (will call `getMagiCollection` using `user.collection_name`)

Both are not recommended, and you'll usually find other ways to get the information you need than by accessing the collection object.

### Optimize images with TinyPNG

If you use the recommended MagiForm classes, you don't need to worry about optimizing images yourself. Outside of this context, you may use `shrinkImageFromData`:

```python
from magi.utils import shrinkImageFromData

f = open('/tmp/image.png', 'r+')
image = shrinkImageFromData(f.read(), 'image.png')
```

You may also provide some settings:

```python
image = shrinkImageFromData(f.read(), 'image.png', settings={
    'resize': 'cover',
    'width': 200,
    'height': 200,
})
```

Settings can be either:
- `{ 'resize': 'cover' }`, with default values `{ 'width': 300, 'height': 300 }`
- `{ 'resize': 'fit' }`, with default values `{ 'max_width': MAX_WIDTH, 'max_height': MAX_HEIGHT, 'min_width': MIN_WIDTH, 'min_height': MIN_HEIGHT }` (default values in your django settings)

See [TinyPNG's documentation](https://tinypng.com/developers/reference) for more details about how images get resized.

### Validators

Validators may be used on forms and models.

#### FutureOnlyValidator and PastOnlyValidator

```python
from magi.utils import PastOnlyValidator

class Account(MagiModel):
    ...
    start_date = models.DateField(validators=[PastOnlyValidator])
```

In this example, if you try to set the start_date to some time in the future, it will raise an error.

### Other tools

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| AttrDict | Make a python dictionary act like an object (ie you can do `the_dict.something` instead of `the_dict['something']`) | dict | AttrDict object |
| ajaxContext | Lighter than globalContext, with just what's needed for an ajax view | request | dict |
| cuteFormFieldsForContext | See ⎡[CuteForm](#cuteform)⎦. | cuteform_fields, context, form=None | None |
| custom_item_template | To be used in MagiCollections when using a custom template instead of the default one. | view | string |
| dumpModel | Take an instance of a model and transform it into a dictonary with all its info (easily flattenable). Allows to delete an instance without losing data (used by Report collection) | instance | dictionary |
| emailContext | Lighter than globalContext, with just what's needed for an ajax view | request | dict |
| getAccountIdsFromSession | Get the list of account ids of the currently logged in user | request | list of ids |
| globalContext | Default context required by MagiCircles | request | dict |
| justReturn | Returns a lambda that takes whatever and returns the same value. May be useful in MagiCollections when you want to override a method but ignore its parameters and return the same constant value. | value | lambda |
| ordinalNumber | Returns 1st, 2nd, 3rd, 4th, etc. Not localized. | n | string |
| propertyFromCollection | To be used in a view, will set the value to the value in the parent collection | property_name | any |
| randomString | Generates a random string | length, choice=(string.ascii_letters + string.digits) | string |
| redirectToProfile | Raises an exception that will make the current request redirect to the profile of the authenticated user. If specified, will redirect to a specific account anchor within the profile. | request, account=None | None (raises an exception) |
| redirectWhenNotAuthenticated | Will check if the current user is authenticated, and if not, will redirect to the signup page with `next` set as the `current_url` | request, context, next_title=None | None (raises an exception) |
| send_email | Send an email | subject, template_name, to=[], context={}, from_email=django_settings.AWS_SES_RETURN_PATH | None |
| setSubField | Mostly used when overriding `to_fields`. See ⎡[to_fields method](#to_fields-method)⎦. | fields, field_name, value, key='icon' | None (updates fields in place) |
| staticImageURL | Returns the full URL of a static asset (in `sample/static/img/...`) | path, folder=None, extension=None | string |
| torfc2822 | Date format frequently used in Javascript | date | string |
| tourldash | Takes any string and returns a URL-friendly string. Example: "Hi! You're awesome." becomes "Hi-You-re-awesome" | string | string |

## Templates

Note that using template tags, either provided ones below or your own, adds a significant loading cost. See ⎡[Using template tags](#using-template-tags)⎦.

### Tools

The missing utility functions in django templates.

```html
{% load tools %}
```

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| addint | Concatenate an integer at the end of a string | string, int | string |
| anon_format | Same than `format` but parameters that are not named. Equivalent of `'hello {}'.format('Deby')` | string, **kwargs | string |
| call | Call a function | function, parameter | returns the returned value after the function has been called |
| callWithContext | Takes a dict that contains a function, calls it with the current context, up to 3 parameters and stores the returned value in `result_of_callwithcontext` in the context | dict, function (= string name key in dict), p1=None, p2=None, p3=None | None |
| format | Format a string with the given dictionary. Equivalent of: `'hello {name}!'.format(name='Deby')` | string, **kwargs | string |
| getattribute | Gets an attribute of an object dynamically from a string name | value, arg | the attribute |
| isList | Is `thing` a list? | thing | bool |
| isnone | Return True if the value is `None` | value | bool |
| mod | Is a divisible by b? | a, b | a % b == 0 |
| modelName | Takes an instance of a django model and returns the string name | thing | string |
| orcallable | Will check if a variable is callable and call it, or just return it if it's not. Will also translate it if needed. | var_or_callable | value |
| padzeros | Pad an integer with zeros | value, length | string |
| split | Returns a list of strings from a string | string, splitter=',') | list |
| startswith | Check if a string starts with another string | string, string | bool |
| t | Translated string for terms in `django_translated`, see ⎡[Avoid generating translation terms for terms already available in Django framework](#avoid-generating-translation-terms-for-terms-already-available-in-django-framework)⎦ | string | localized string |
| times | Create a range from 0 to value | value | list of integers |
| trans_anon_format | Same than `trans_format` but parameters that are not named. Equivalent of `_('hello {}').format('Deby')` | string, **kwargs | string |
| trans_format | Same than `format` but with a translated string. Equivalent of `_('hello {name}!').format(name='Deby')` | string, **kwargs | string |

## Javascript

All the following functions are available in all pages. You can call them from any javascript file, as long as it's included after the inclusion of all the main Javascript files.

| Name | Description | Parameters | Return value |
|------|-------------|------------|--------------|
| disableButton | Make any button not clickable. Can be useful to avoid allowing someone to click a button again after it's been clicked. See also ⎡[Make a form only submittable once](#make-a-form-only-submittable-once)⎦. | button | None |
| gettext | Get the translation of a term. In python, you need to provide this translation in `JAVASCRIPT_TRANSLATED_TERMS` MagiCircles settings. | term | translated string |
| freeModal | Show a bootstrap modal. <ul><li>Use true for modal_size to not change the size</li><li>Use 0 for buttons to remove all buttons</li><li>modal_size can be `md`, `lg` or `sm`</li></ul> | title, body, buttons=(Go button that closes the modal), modal_size='lg' | None |
| confirmModal | Show a modal to confirm a critical action. It takes a callback that you can use to perform the action. | onConfirmed, onCanceled=undefined, title=gettext('Confirm'), body=gettext('You can\'t cancel this action afterwards.') | None |
| genericAjaxError | You may use this function to handle errors in your ajax calls. It will simply display the error in an alert | xhr, ajaxOptions, thrownError | None |
| directAddCollectible | To be used with buttons to add an item to your collection. Instead of loading the form to add in a modal, will attempt to load it in the background and submit it, then update the counter of total collected items. uniquePerOwner can also be set in data-unique-per-owner. | buttons, uniquePerOwner (optional, default=False) | None |

### HTML elements with automatic Javascript behavior

There are some classes you can add to your HTML elements that will automatically make them do something for you. It allows you to avoid loading a Javascript file just to run something simple and common.

#### Load an Ajax page in a modal

- Add an attribute `data-ajax-url` to any button or link.

```html
<a href="/something/" data-ajax-url="/ajax/something/"></a>
```

It will open the ajax version of the page in a bootstrap modal instead of opening a new page. Users may right click on the link to open the original link in a new tab if they want. It will also open the page if they disable Javascript.

While the ajax page is loading, the button or link clicked transforms into a loader.

In case of an error, the default function `genericAjaxError` will be called.

When the page is loaded within the modal, the browser URL changes without reloading the page. This allows users to easily bookmark or share a specific page.

If the user uses the back button of their browser, the modal will be closed, behaving like it was loaded as a new page, which is the behavior users expect.

You may configure this further using the following attributes:
- `data-ajax-show-button`: If set to `true`, will show the default ajax button "Go" which simply closes the modal on click. Otherwise, no button will be visible and the user may close the modal using the top right cross, by clicking outside of the modal or by using the back button in browser
- `data-ajax-title`: By default, the title of the modal will be the inner HTML of the clicked button or link. You may specify a different title here.
- `data-modal-size`: Specify the size of the modal. Choices are `md`, `lg` and `sm`. Default size is `lg`.
- `data-ajax-handle-form`: If your loaded ajax page contains forms, you may set this to `true` to make the form response appear in this modal as well. Make sure the page loaded in response to this form is also in ajax (doesn't contain the page's boilerplate).
    -  If you need the form response to be displayed in a modal of a different size, you may provide `data-ajax-modal-after-form-size`
    -  It will understand that you got an error if your return form response contains a `form` with `.error-list`, and handle the form within the modal again (without changing the size)

#### Load an Ajax page in a popover

- Add attributes `data-ajax-popover` and `title` to any button or link:

```html
<a href="/something/" data-ajax-popover="/ajax/something/" title="something"></a>
```

It will open the ajax version of the page in a bootstrap modal instead of opening a new page. Users may right click on the link to open the original link in a new tab if they want. It will also open the page if they disable Javascript.

While the ajax page is loading, the popover will open and display a loader.

In case of an error, the default function `genericAjaxError` will be called.

Unline modal loading, the URL doesn't change.

#### Smooth scroll to an anchor

- Add a class `.page-scroll` to any link to an anchor within the same page

![](http://i.imgur.com/jKxMLrX.gif)

#### Make a form only submittable once

- Add a class `.form-loader` to any button

It will show a loader inside the button when you click it, and make it invalid.
It should only be used for forms handled server side that expect a page reload (ie will not work if you use Ajax to submit the form)

#### Hide staff-only buttons

- Add a class `.staff-only` to any HTML element

It's important to hide staff only buttons by default, allowing staff members to easily take screenshots of our website similar to what everybody else can see, and share them.

A button in the bottom left corner of the website allows staff members to show all the staff only buttons.

#### Countdowns

- Add a class `.countdown` and an attribute `data-date` to any HTML element

The inner HTML will transform into a countdown before the date specified in `data-date`. The date must be specified in RFC2822 format. You may use the utility function `torfc2822` in python. See ⎡[Utils - Python - Other tools](#other-tools)⎦.

It requires the [countdown javascript library](http://rendro.github.io/countdown/), which will be loaded asynchronosly only if at least one `.countdown` element is present in the page.

You may provide `data-format` to specify a sentence. For example: `data="Only {time} left! Play now!"` will display `Only 1 day 2 hours 5 minutes 36 seconds left! Play now!`. The `{time}` sentence will be translated, so it's recommended to make sure the sentence you provide is also translated.

#### Timezones

- Add a class `.timezone` to an HTMl element, with an inner element with a class `.datetime` should

The date in the `.datetime` element must be specified in RFC2822 format. You may use the utility function `torfc2822` in python. See ⎡[Utils - Python - Other tools](#other-tools)⎦.

It will display the date in a human readable, translated format in the timezone of the current user.

You may specify a different timezone using `data-to-timezone`. Example: `Asia/Tokyo`

You may also display how long ago that date was or is going to be in a human readable format by setting `data-timeago` to `true`. Example: `less than a minute ago`, `9 months ago`, ...

In that case, the user may put their mouse over this element to see the date in their local timezone in a booltstrap tooltip.

It requires the [timeago javascript library](http://timeago.yarp.com/), which will be loaded asynchronosly only if at least one `.timezone` element with `data-timeago` set to `true` is present in the page.

#### Markdown

- Add a class `.to-markdown` to any HTML element

The content will be converted in HTML using the markdown format. It will also automatically transform links to become clickable. HTML is not considered part of the markdown format and will be escaped.

It requires the [marked javascript library](https://github.com/chjj/marked), which will be loaded asynchronosly only if at least one `.to-markdown` element is present in the page.

### Commons

A bunch of "common" functions are called together when:
- on load of any page
- when a view is loaded in a modal
- when a new pagination page is loaded

You may call `loadCommons` again if needed, for example if you load new HTMl within the page. You may also call these functions individually.

Functions called (in this order):

| Name | Description |
|------|-------------|
| loadToolTips | Load Bootstrap tooltips. [Learn more](http://getbootstrap.com/javascript/#tooltips). |
| loadPopovers | Load Bootstrap popovers. [Learn more](http://getbootstrap.com/javascript/#popovers) |
| formloaders | See ⎡[Make a form only submittable once](#make-a-form-only-submittable-once)⎦. |
| dateInputSupport | Check if the current browser has support for HTML5 date input and if not (= just a text input), will show a help text with the date format. |
| hideStaffButtons | See ⎡[Hide staff-only buttons](#hide-staff-only-buttons)⎦. |
| ajaxModals | See ⎡[Load an Ajax page in a modal](#load-an-ajax-page-in-a-modal)⎦.
| loadCountdowns | See ⎡[Countdowns](#countdowns)⎦ |
| loadTimezones | See ⎡[Timezones](#timezones)⎦ |
| loadMarkdown | See ⎡[Markdown](#markdown)⎦ |
| reloadDisqus | Will force reload Disqus script that displays the total number of comments in the link to the comment section of a page. |
| directAddCollectible($('[data-quick-add-to-collection="true"]')) | Will load Javascript utility to quickly add collectibles to your collection. |

Recommendations
===============

## Don't concatenate translated strings

In some languages, the order of the words in a sentence might not be what you expect. If you force the order of words with concatenation, you make the translators' job very hard, if not impossible.

Example in python:
```python
context['greetings'] = _('Hello') + request.user.username + '!'
```
should be:
```python
context['greetings'] = _('Hello {name}!').format(name=request.user.username)
```

Example in template:
```html
{% trans 'Hello' %} {{ user.username }}!
```
should be:
```html
{% load tools %}
{% trans_format string='Hello {name}!' name=user.username %}
```

Note that in general, it is recommended to do that transformation in python and not in the template, since doing it in template requires the inclusion of the tools module, which adds a significant cost.

## Internal cache for foreign keys in models

Use an internal cache for fields in forein keys that are accessed often, to avoid extra `JOIN` in your queries (ie `select_related`) which slow down the queries.

Let's say every time we display a card, we also display the name and age of the idol featured in the card:

```python
from magi.utils import AttrDict

class Card(MagiModel):
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
  class Idol(MagiModel):
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
from magi.tools import totalDonators
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
from magi.django_translated import t

t.update({
    'Japanese': _('Japanese'),
})
```

When you want to use the term, do:
```python
from sample.django_translated import t

print t['Japanese']
```

When generating the terms, make sure you don't include the terms in this file:

```shell
python manage.py makemessages ... --ignore=sample/django_translated.py
```

See ⎡[Translations](#translations)⎦.

## Disable activities

`sample/settings.py`:

```python
from magi.default_settings import DEFAULT_ENABLED_PAGES

ENABLED_PAGES = DEFAULT_ENABLED_PAGES
ENABLED_PAGES['index']['enabled'] = True
```

`sample/magicollections.py`:

```python
from magi.magicollections import ActivityCollection as _ActivityCollection

class ActivityCollection(_ActivityCollection):
    enabled = False
```

## Disable activities but keep news for staff members

`sample/settings.py`:

```python
from magi.default_settings import DEFAULT_ENABLED_PAGES

ENABLED_PAGES = DEFAULT_ENABLED_PAGES
ENABLED_PAGES['index']['enabled'] = True
```

`sample/magicollections.py`:

```python
from magi.magicollections import ActivityCollection as _ActivityCollection

class ActivityCollection(_ActivityCollection):
    enabled = False

Activity.collection_name = 'news'

class NewsCollection(_ActivityCollection):
    plural_name = 'news'
    title = _('Staff News')
    plural_title = _('Staff News')
    reportable = False
    queryset = Activity.objects.all()
    navbar_link = True
    navbar_link_list = 'more'

    class ListView(_ActivityCollection.ListView):
        show_title = True
        item_template = 'activityItem'
        shortcut_urls = []

    class ItemView(_ActivityCollection.ItemView):
        template = 'activityItem'

    class AddView(_ActivityCollection.AddView):
        staff_required = True
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
   @import "../../../env/lib/python2.7/site-packages/magi/static/less/main.less";
   @import "../../../env/lib/python2.7/site-packages/magi/static/less/mixins/buttons.less";
   @import "../../../env/lib/python2.7/site-packages/magi/static/less/mixins/a.less";
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

6. Set up cron jobs

    - Send email for unread notifications, every 2 hours
    - Generate the map with locations of the users, every day at midnight
    - Generate settings, every day at midnight
    - Reload the website with the new generated settings, every day at midnight + 10 minutes

   ```shell
   crontab -e
   ```

   ```
   0 */2 * * * /home/ubuntu/SampleWebsite/env/bin/python /home/ubuntu/SampleWebsite/manage.py cron_notifications >> /home/ubuntu/cronjob.log 2>&1
   0 0 * * * /home/ubuntu/SampleWebsite/env/bin/python /home/ubuntu/SampleWebsite/manage.py latlong >> /home/ubuntu/latlong_cronjob.log 2>&1
   0 0 * * * /home/ubuntu/SampleWebsite/env/bin/python /home/ubuntu/SampleWebsite/manage.py generate_settings >> /home/ubuntu/settings_cronjob.log 2>&1
   10 0 * * * root service uwsgi reload
   ```


Translations
============

todo

Flaticon
========

The icons come from [flaticon.com](http://www.flaticon.com/) and are credited in the about page.

To get the list of available icons and their codes, open your website on `/static/css/flaticon.html`.


Migrate from MagiCircles1 to MagiCircles2
=========================================

1. **Update MagiCircles2**

    Change your `requirements.txt` to use MagiCircles2 branch:
    ```txt
    git+https://github.com/SchoolIdolTomodachi/MagiCircles.git@MagiCircles2
    ```
    Update requirements:
    ```shell
    pip install -r requirements.txt --upgrade
    ```

    DO NOT PERFORM MIGRATIONS AT THIS POINT!

1. **Rename your SQL tables from web to magi**

    ```sql
    UPDATE django_content_type SET app_label='magi' WHERE app_label='web';
    UPDATE django_migrations SET app='magi' WHERE app='web';
    ALTER TABLE web_activity RENAME TO magi_activity;
    ALTER TABLE web_activity_likes RENAME TO magi_activity_likes;
    ALTER TABLE web_badge RENAME TO magi_badge;
    ALTER TABLE web_donationmonth RENAME TO magi_donationmonth;
    ALTER TABLE web_notification RENAME TO magi_notification;
    ALTER TABLE web_report RENAME TO magi_report;
    ALTER TABLE web_report_images RENAME TO magi_report_images;
    ALTER TABLE web_userimage RENAME TO magi_userimage;
    ALTER TABLE web_userlink RENAME TO magi_userlink;
    ALTER TABLE web_userpreferences RENAME TO magi_userpreferences;
    ALTER TABLE web_userpreferences_following RENAME TO magi_userpreferences_following;
    ```

1. **Rename web to magi in your code**

    Python imports:
    ```python
    from web import forms
    from web import models as web_models
    from web.magicollections import MagiCollection
    ```
    should be:
    ```python
    from magi import forms
    from magi import models as magi_models
    from magi.magicollections import MagiCollection
    ```

    In settings.py:
    ```
    INSTALLED_APPS = (
        ...
        'web',
    )

    AUTHENTICATION_BACKENDS = ('web.backends.AuthenticationBackend',)

    ...
    ```
    should be:
    ```
    INSTALLED_APPS = (
        ...
        'magi',
    )

    AUTHENTICATION_BACKENDS = ('magi.backends.AuthenticationBackend',)

    ...
    ```

    If you have manual SQL queries or partial queries in your code, you'll need to update the table names as well:

    ```python
    def get_queryset(self, queryset, parameters, request):
        if request.user.is_authenticated():
            queryset = queryset.extra(select={
                'followed': 'SELECT COUNT(*) FROM web_userpreferences_following WHERE userpreferences_id = {} AND user_id = auth_user.id'.format(request.user.preferences.id),
            })
    ```
    should be:
    ```python
    def get_queryset(self, queryset, parameters, request):
        if request.user.is_authenticated():
            queryset = queryset.extra(select={
                'followed': 'SELECT COUNT(*) FROM magi_userpreferences_following WHERE userpreferences_id = {} AND user_id = auth_user.id'.format(request.user.preferences.id),
            })
    ```

    If your code base is quite big, you may want to replace it automatically:

    ```shell
    find sample/ -type f -name '*.py' -exec sed -i 's/web\./magi\./g;s/from web/from magi/g;s#web/#magi/#g;'"s/'web'/'magi'/g;"'s/web_tags/magi_tags/g;' \{\} \;
    find sample/templates/ -type f -name '*.html' -exec sed -i 's/web\./magi\./g;s/from web/from magi/g;s#web/#magi/#g;'"s/'web'/'magi'/g;"'s/web_tags/magi_tags/g;' \{\} \;
    ```

1. **Add the new required settings in `sample/settings.py`**

    ```python
    MIDDLEWARE_CLASSES = (
        ...
        'magi.middleware.languageFromPreferences.LanguageFromPreferenceMiddleWare',
    )

    FAVORITE_CHARACTERS = []

    MAX_WIDTH = 1200
    MAX_HEIGHT = 1200
    MIN_WIDTH = 300
    MIN_HEIGHT = 300
    ```
1. **Use the new settings available to configure your website**

    Many new features have been added in your website settings, so it's recommended to use them instead of whatever you manually implemented in the past to achieve the same behavior.

    - `LAUNCH_DATE`
    - `NAVBAR_ORDERING`
    - `ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT`
    - `ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES`
    - `PRELAUNCH_ENABLED_PAGES`
    - `PROFILE_TABS`
    - `SITE_LOGO_PER_LANGUAGE`
    - `SITE_LOGO`
    - Note: `SITE_LOGO` has been renamed to `SITE_NAV_LOGO` and `SITE_LOGO` now corresponds to the logo on the homepage

1. **Make your models inherit from MagiModel**

    See ⎡[MagiModel](#models)⎦ documentation.

    - Add `collection_name` before your model's fields
    - If your model uses `account` to determine the owner, make it inherit from `AccountAsOwnerModel`

1. **Remove ENABLED_COLLECTIONS dictionary and configure your collections with MagiCollection objects**

    Previously in `sample/settings.py`:
    ```python
    ENABLED_COLLECTIONS['card'] = {
        'queryset': models.Card.objects.all(),
        'list': {
            'default_ordering': '-release_date',
        },
    }
    ```
    should be in `sample/magicollections.py`:
    ```python
    class CardCollection(MagiCollection):
        queryset = models.Card.objects.all()

        class ListView(MagiCollection.ListView):
            default_ordering = '-release_date'
    ```

    If your dictionary was referring to functions defined somewhere else, it's now recommended to have the full function inside the collection object.

1. **Use the new settings available in MagiCollections and views**

    Many new features have been added in MagiCollection objects, so it's recommended to use them instead of whatever you manually implemented in the past to achieve the same behavior.

    New settings in collection:
    - `types`, `form_class` and `multipart` can be set for the whole collection in addition to per view
    - `navbar_link_title`, `navbar_link_list_divider_before`, `navbar_link_list_divider_after`
    - `reportable`, `report_edit_templates`, `report_delete_templates`, `report_allow_edit`, `report_allow_edit`
    - `filter_cuteform`
    - `collectible`
    - New overridable methods: `get_queryset`, `to_fields`

    New settings in views:
    - All views: `ajax_callback`, `check_owner_permissions`, `check_permissions`, `enabled`, `get_queryset`, `logout_required`, `multipart`, `owner_only`, `shortcut_urls`
        - Note: `filter_queryset` is now called `get_queryset` and should be used for semantically different operations. Filtering should be done using `MagiFiltersForm`.
        - Note: `types` is not in the collection itself and not per view.
    - List View: `filter_cuteform`, `hide_sidebar`, `item_template`, `show_edit_button`, `show_relevant_fields_on_ordering`, `item_padding`, `display_style`, `display_style_table_fields`, `alt_views`, `table_fields_headers`, `table_fields_headers_sections`, `ordering_fields`, `table_fields`
    - Item View: `show_edit_button`, `top_illustration`, `get_item`, `reverse_url`, `item_padding`
    - Add View: `filter_cuteform`, `max_per_user_per_hour`, `max_per_user_per_day`, `max_per_user`
    - Edit View: `form_class`, `get_item`

1. **Specify your template for accounts in profile**

    MagiCircles now provides a default template for accounts in profile. If you would like to keep the one you made
    and not use the default one, specify it in your UserCollection ItemView:

    ```python
    from magi.magicollections import UserCollection as _UserCollection

    class UserCollection(_UserCollection):
        class ItemView(_UserCollection.ItemView):
            accounts_template = 'accountsForProfile'
    ```

1. **Fix ON_USER_EDITED and ON_PREFERENCES_EDITED**

    Both used to take `request` as a parameter and now take the user that has been updated.

    In addition, if for some reasons you were calling these 2 functions youself, you should now also call `models.onPreferencesEdited` or `models.onUserEdited` right before.

1. **Specify your templates for List views or Item views, or use the default one**

    MagiCircles2 now comes with default templates for List views and Item views. If you don't specify `template` in Item view and `item_template` in List view, the default templates will be used.

    If you want to use the default templates because they suit your needs, don't provide `template` and `item_template` in your views settings.

    If you want to use your own templates:

    ```python
    from magi.utils import custom_item_template

    class IdolCollection(MagiCollection):
        ...
        class ListView(MagiCollection.ListView):
            item_template = custom_item_template
    ```

    This will use the standard name for template, which is the collection name + "Item". For example: `idolItem`.
    It will now load your template file in `sample/templates/items/idolItem.html`.

    Though it's recommended to use the standard name for your custom templates, you may use your own template name:

    ```python
    class IdolCollection(MagiCollection):
        ...
        class ListView(MagiCollection.ListView):
            item_template = 'idolDetails'
    ```

    In that case, it will load the template file in `sample/templates/items/idolDetails.html`.

    If you already had a custom template called `default`, you'll need to rename it.

1. **Make your forms inherit from MagiForm or MagiFiltersForm**

    See ⎡[MagiForm](#magiform)⎦ and ⎡[MagiFilter](#magifilter)⎦ documentations.

    Do not use `get_queryset` (previously `filter_queryset`) to filter the result of the filters side bar. Instead, use [MagiFiltersForm](#magifilter).

    Do not use `before_save` and `after_save` if possible, and prefer customizing your [MagiForm](#magiform).

    If you used to manually call TinyPNG for your images, you may now remove this code since MagiForm will do it for you.

1. **Remove any useless form**

    MagiCircles2 now comes with a `form_class` provided by default. You may want to remove your own custom forms if the default one works for you.

1. **Use sentences helpers in MagiModel**

    Search for all the places where you created a sentence regarding an action by concatenating 2 words and replace that with the sentence helper.

    Example:
    ```html
    <a href="{{ card.item_url }}">{% trans 'Open' %} {% trans 'Card' %}</a>
    ```
    should be:
    ```html
    <a href="{{ card.item_url }}">{{ card.open_sentence }}}</a>
    ```

    See all sentences helpers in ⎡[MagiModel documentation](#inherit-from-magimodel-and-provide-a-name)⎦

    ```
    emacs `gs "'Open'" | \grep -v bower | \grep -v locale | \grep -v collected`
    emacs `gs "'Edit'" | \grep -v bower | \grep -v locale | \grep -v collected`
    emacs `gs "verb" | \grep -v bower | \grep -v locale | \grep -v collected`
    emacs `gs "'Delete'" | \grep -v bower | \grep -v locale | \grep -v collected`
    emacs `gs "'Report'" | \grep -v bower | \grep -v locale | \grep -v collected`
    emacs `gs "'Add'" | \grep -v bower | \grep -v locale | \grep -v collected`
    ```

    Some languages don't have the same order of words for these sentences, so it is not recommended to concatenate words.
    It also applies to any other sentences you created like that.

    See ⎡[Don't concatenate translated strings](#dont-concatenate-translated-string)⎦.


1. **Use links helpers in MagiModel**

    If you manually created links to an item or item pages, you may want to use the new helpers.

    Example:
    ```html
    <a href="/cards/{{ card.id }}">...</a>
    ```
    should be:
    ```html
    <a href="{{ card.item_url }}">...</a>
    ```

    See all links helpers in ⎡[MagiModel documentation](#inherit-from-magimodel-and-provide-a-name)⎦

    ```
    emacs `gs "/card" | \grep -v bower | \grep -v locale | \grep -v collected`
    emacs `gs "/edit" | \grep -v bower | \grep -v locale | \grep -v collected`
    emacs `gs "/add/" | \grep -v bower | \grep -v locale | \grep -v collected`
    emacs `gs "RAW_CONTEXT\[\'magi" | \grep -v bower | \grep -v locale | \grep -v collected`
    ```
1. **Localize text representations of MagiModel instances**

    MagiCircles1 recommended to keep only one way to represent an item, but MagiCircles2 encourages localization for SEO purposes.

    Example:
    ```python
    class Idol(MagiModel):
        ...
        def __unicode__(self):
            return self.name
    ```
    should be:
    ```python
    from django.utils.translation import get_language

    class Idol(MagiModel):
        ...
        def __unicode__(self):
            return self.japanese_name if get_language == 'ja' else self.name
    ```

1. **Add more supported languages**

     Many new languages got added since MagiCircles1. Take a look at [our collaborative translation tool](https://poeditor.com/join/project/h6kGEpdnmM) to pick languages you might be interested in.

1. **Migrate**

    Once you're done updating, you will need to perform the databases migrations for the new models in MagiCircles2.

    ```shell
    python manage.py migrate
    ```
