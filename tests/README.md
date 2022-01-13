# MagiCircles Unit Tests

```shell
virtualenv --python=`which python2` env
source env/bin/activate
pip install --upgrade setuptools
pip install pip==9.0.1
pip install -r requirements.txt
python manage.py test
```

To run a single test:

```shell
python manage.py test test.tests.IChoicesTestModelTestCase.test_notification_icon
python manage.py test test.test_utils.UtilsTestCase.test_markSafeJoin
```
