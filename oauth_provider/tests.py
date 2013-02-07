"""
=====================
Django OAuth provider
=====================

The `OAuth protocol`_ enables websites or applications (Consumers) to access 
Protected Resources from a web service (Service Provider) via an API, without 
requiring Users to disclose their Service Provider credentials to the 
Consumers. More generally, OAuth creates a freely-implementable and generic 
methodology for API authentication.

.. _`OAuth protocol`: http://oauth.net/core/1.0a


Authenticating with OAuth
=========================

OAuth authentication is the process in which Users grant access to their 
Protected Resources without sharing their credentials with the Consumer. 
OAuth uses Tokens generated by the Service Provider instead of the User's 
credentials in Protected Resources requests. The process uses two Token types:

    * **Request Token:**
      Used by the Consumer to ask the User to authorize access to the 
      Protected Resources. The User-authorized Request Token is exchanged for 
      an Access Token, MUST only be used once, and MUST NOT be used for any 
      other purpose. It is RECOMMENDED that Request Tokens have a limited 
      lifetime.
    * **Access Token:**
      Used by the Consumer to access the Protected Resources on behalf of the 
      User. Access Tokens MAY limit access to certain Protected Resources, and 
      MAY have a limited lifetime. Service Providers SHOULD allow Users to 
      revoke Access Tokens. Only the Access Token SHALL be used to access the 
      Protect Resources.

OAuth Authentication is done in three steps:

    * The Consumer obtains an unauthorized Request Token.
    * The User authorizes the Request Token.
    * The Consumer exchanges the Request Token for an Access Token.

See the `OAuth Authentication Flow`_ if you need visual details.

.. _`OAuth Authentication Flow`: http://oauth.net/core/diagram.png


Django installation
===================

First, install dependencies through pip::

    pip install -r requirements.txt

You need to specify the OAuth provider application in your settings and to 
sync your database thanks to the ``syncdb`` command. Then add it to your 
URLs::

    # urls.py
    urlpatterns = patterns('',
        url(r'^oauth/', include('oauth_provider.urls'))
    )

.. note::
    The ``oauth`` prefix is not required, you can specify whatever you want.

As a provider, you probably need to customize the view you display to the user
in order to allow access. The ``OAUTH_AUTHORIZE_VIEW`` setting allow you to
specify this view, for instance::

    # settings.py
    OAUTH_AUTHORIZE_VIEW = 'myapp.views.oauth_authorize'

.. note::
    See example below with a custom callback view (optional), which depends on
    ``OAUTH_CALLBACK_VIEW`` setting.

.. note::
    This implementation set an ``oauth`` flag in session which certify that 
    the validation had been done by the current user. Otherwise, the external 
    service can directly POST the validation argument and validate the token 
    without any action from the user if he is already logged in. Do not delete
    it in your own view.

There is another setting dedicated to OAuth ``OAUTH_REALM_KEY_NAME``, which
allows you to specify a realm which will be used in headers::

    # settings.py
    OAUTH_REALM_KEY_NAME = 'http://photos.example.net'
    
    # response
    WWW-Authenticate: OAuth realm="http://photos.example.net/"

With this setup, your OAuth URLs will be:

    * Request Token URL: /oauth/request_token/
    * User Authorization URL: /oauth/authorize/, using HTTP GET.
    * Access Token URL: /oauth/access_token/

That is the only thing you need to document for external developers.

.. note::
    You can customize the length of your key/secret attributes with 
    constants ``KEY_SIZE``, ``SECRET_SIZE`` and ``CONSUMER_KEY_SIZE`` defined 
    in consts.py. Default is set to 16 characters for ``KEY_SIZE`` and 
    ``SECRET_SIZE`` and 256 characters for ``CONSUMER_KEY_SIZE``.

The ``OAUTH_BLACKLISTED_HOSTNAMES`` setting allows you to restrict callback
URL hostnames, it must be a list of blacklisted ones. For example::

    OAUTH_BLACKLISTED_HOSTNAMES = ['localhost', '127.0.0.1']

Default is an empty list.

The ``OAUTH_SIGNATURE_METHODS`` setting allows you to restrict signatures'
methods you'd like to use. For example if you don't want plaintext signature::

    OAUTH_SIGNATURE_METHODS = ['hmac-sha1',]

Default is ``['plaintext', 'hmac-sha1']``.

A complete example is available in ``oauth_examples/provider/`` folder, you
can run tests from this example with this command::

    $ python manage.py test oauth_provider
    ...
    Ran 1 test in 0.264s
    
    OK
    ...


Protocol Example 1.0a
=====================

.. warning::
    THIS IS THE RECOMMENDED WAY TO USE THIS APPLICATION.

This example is exactly the same as 1.0 except it uses newly introduced
arguments to be 1.0a compatible and fix the security issue.

An account for Jane is necessary::

    >>> from django.contrib.auth.models import User
    >>> jane = User.objects.create_user('jane', 'jane@example.com', 'toto')


Documentation and Registration
------------------------------

The Service Provider documentation explains how to register for a Consumer Key 
and Consumer Secret, and declares the following URLs:

    * Request Token URL:
      http://photos.example.net/request_token, using HTTP POST
    * User Authorization URL:
      http://photos.example.net/authorize, using HTTP GET
    * Access Token URL:
      http://photos.example.net/access_token, using HTTP POST
    * Photo (Protected Resource) URL:
      http://photos.example.net/photo with required parameter file and 
      optional parameter size

The Service Provider declares support for the HMAC-SHA1 signature method for 
all requests, and PLAINTEXT only for secure (HTTPS) requests.

The Consumer printer.example.com already established a Consumer Key and 
Consumer Secret with photos.example.net and advertizes its printing services 
for photos stored on photos.example.net. The Consumer registration is:

    * Consumer Key: dpf43f3p2l4k3l03
    * Consumer Secret: kd94hf93k423kf44

We need to create the Protected Resource and the Consumer first::

    >>> from oauth_provider.models import Resource, Consumer
    >>> resource = Resource(name='photos', url='/oauth/photo/')
    >>> resource.save()
    >>> CONSUMER_KEY = 'dpf43f3p2l4k3l03'
    >>> CONSUMER_SECRET = 'kd94hf93k423kf44'
    >>> consumer = Consumer(key=CONSUMER_KEY, secret=CONSUMER_SECRET, 
    ...                     name='printer.example.com', user=jane)
    >>> consumer.save()


Obtaining a Request Token
-------------------------

After Jane informs printer.example.com that she would like to print her 
vacation photo stored at photos.example.net, the printer website tries to 
access the photo and receives HTTP 401 Unauthorized indicating it is private. 
The Service Provider includes the following header with the response::

    >>> from django.test.client import Client
    >>> c = Client()
    >>> response = c.get("/oauth/request_token/")
    >>> response.status_code
    401
    >>> # depends on REALM_KEY_NAME Django setting
    >>> response._headers['www-authenticate']
    ('WWW-Authenticate', 'OAuth realm=""')
    >>> response.content
    'Invalid request parameters.'

The Consumer sends the following HTTP POST request to the Service Provider::

    >>> import time
    >>> parameters = {
    ...     'oauth_consumer_key': CONSUMER_KEY,
    ...     'oauth_signature_method': 'PLAINTEXT',
    ...     'oauth_signature': '%s&' % CONSUMER_SECRET,
    ...     'oauth_timestamp': str(int(time.time())),
    ...     'oauth_nonce': 'requestnonce',
    ...     'oauth_version': '1.0',
    ...     'oauth_callback': 'http://printer.example.com/request_token_ready',
    ...     'scope': 'photos', # custom argument to specify Protected Resource
    ... }
    >>> response = c.get("/oauth/request_token/", parameters)

The Service Provider checks the signature and replies with an unauthorized 
Request Token in the body of the HTTP response::

    >>> response.status_code
    200
    >>> response.content
    'oauth_token_secret=...&oauth_token=...&oauth_callback_confirmed=true'
    >>> from oauth_provider.models import Token
    >>> token = list(Token.objects.all())[-1]
    >>> token.key in response.content, token.secret in response.content
    (True, True)
    >>> token.callback, token.callback_confirmed
    (u'http://printer.example.com/request_token_ready', True)

If you try to access a resource with a wrong scope, it will return an error::

    >>> parameters['scope'] = 'videos'
    >>> parameters['oauth_nonce'] = 'requestnoncevideos'
    >>> response = c.get("/oauth/request_token/", parameters)
    >>> response.status_code
    401
    >>> response.content
    'Resource videos does not exist.'
    >>> parameters['scope'] = 'photos' # restore

If you try to put a wrong callback, it will return an error::

    >>> parameters['oauth_callback'] = 'wrongcallback'
    >>> parameters['oauth_nonce'] = 'requestnoncewrongcallback'
    >>> response = c.get("/oauth/request_token/", parameters)
    >>> response.status_code
    401
    >>> response.content
    'Invalid callback URL.'

If you do not provide any callback (i.e. oob), the Service Provider SHOULD 
display the value of the verification code::

    >>> parameters['oauth_callback'] = 'oob'
    >>> parameters['oauth_nonce'] = 'requestnonceoob'
    >>> response = c.get("/oauth/request_token/", parameters)
    >>> response.status_code
    200
    >>> response.content
    'oauth_token_secret=...&oauth_token=...&oauth_callback_confirmed=true'
    >>> oobtoken = list(Token.objects.all())[-1]
    >>> oobtoken.key in response.content, oobtoken.secret in response.content
    (True, True)
    >>> oobtoken.callback, oobtoken.callback_confirmed
    (None, False)


Requesting User Authorization
-----------------------------

The Consumer redirects Jane's browser to the Service Provider User 
Authorization URL to obtain Jane's approval for accessing her private photos.

The Service Provider asks Jane to sign-in using her username and password::

    >>> parameters = {
    ...     'oauth_token': token.key,
    ... }
    >>> response = c.get("/oauth/authorize/", parameters)
    >>> response.status_code
    302
    >>> response['Location']
    'http://.../accounts/login/?next=/oauth/authorize/%3Foauth_token%3D...'
    >>> token.key in response['Location']
    True

If successful, asks her if she approves granting printer.example.com access to 
her private photos. If Jane approves the request, the Service Provider 
redirects her back to the Consumer's callback URL::

    >>> c.login(username='jane', password='toto')
    True
    >>> token.is_approved
    0
    >>> response = c.get("/oauth/authorize/", parameters)
    >>> response.status_code
    200
    >>> response.content
    'Fake authorize view for printer.example.com with params: oauth_token=...'
    
    >>> # fake authorization by the user
    >>> parameters['authorize_access'] = 1
    >>> response = c.post("/oauth/authorize/", parameters)
    >>> response.status_code
    302
    >>> response['Location']
    'http://printer.example.com/request_token_ready?oauth_verifier=...&oauth_token=...'
    >>> token = Token.objects.get(key=token.key)
    >>> token.key in response['Location']
    True
    >>> token.is_approved
    1

    >>> # without session parameter (previous POST removed it)
    >>> response = c.post("/oauth/authorize/", parameters)
    >>> response.status_code
    401
    >>> response.content
    'Action not allowed.'
    
    >>> # fake access not granted by the user (set session parameter again)
    >>> response = c.get("/oauth/authorize/", parameters)
    >>> parameters['authorize_access'] = 0
    >>> response = c.post("/oauth/authorize/", parameters)
    >>> response.status_code
    302
    >>> response['Location']
    'http://printer.example.com/request_token_ready?oauth_verifier=...&error=Access+not+granted+by+user.'
    >>> c.logout()

With OAuth 1.0a, the callback argument can be set to "oob" (out-of-band), 
you can specify your own default callback view with the
``OAUTH_CALLBACK_VIEW`` setting::

    >>> from oauth_provider.consts import OUT_OF_BAND
    >>> token.callback = OUT_OF_BAND
    >>> token.save()
    >>> parameters = {
    ...     'oauth_token': token.key,
    ... }
    >>> c.login(username='jane', password='toto')
    True
    >>> response = c.get("/oauth/authorize/", parameters)
    >>> parameters['authorize_access'] = 0
    >>> response = c.post("/oauth/authorize/", parameters)
    >>> response.status_code
    200
    >>> response.content
    'Fake callback view.'
    >>> c.logout()


Obtaining an Access Token
-------------------------

Now that the Consumer knows Jane approved the Request Token, it asks the 
Service Provider to exchange it for an Access Token::

    >>> c = Client()
    >>> parameters = {
    ...     'oauth_consumer_key': CONSUMER_KEY,
    ...     'oauth_token': token.key,
    ...     'oauth_signature_method': 'PLAINTEXT',
    ...     'oauth_signature': '%s&%s' % (CONSUMER_SECRET, token.secret),
    ...     'oauth_timestamp': str(int(time.time())),
    ...     'oauth_nonce': 'accessnonce',
    ...     'oauth_version': '1.0',
    ...     'oauth_verifier': token.verifier,
    ...     'scope': 'photos',
    ... }
    >>> response = c.get("/oauth/access_token/", parameters)

.. note::
    You can use HTTP Authorization header, if you provide both, header will be
    checked before parameters. It depends on your needs.

The Service Provider checks the signature and replies with an Access Token in 
the body of the HTTP response::

    >>> response.status_code
    200
    >>> response.content
    'oauth_token_secret=...&oauth_token=...'
    >>> access_token = list(Token.objects.filter(token_type=Token.ACCESS))[-1]
    >>> access_token.key in response.content
    True
    >>> access_token.secret in response.content
    True
    >>> access_token.user.username
    u'jane'

The Consumer will not be able to request another Access Token with the same
parameters because the Request Token has been deleted once Access Token is
created::

    >>> response = c.get("/oauth/access_token/", parameters)
    >>> response.status_code
    400
    >>> response.content
    'Invalid request token.'

The Consumer will not be able to request another Access Token with a missing
or invalid verifier::

    >>> new_request_token = Token.objects.create_token(
    ...     token_type=Token.REQUEST,
    ...     timestamp=str(int(time.time())),
    ...     consumer=Consumer.objects.get(key=CONSUMER_KEY),
    ...     user=jane,
    ...     resource=Resource.objects.get(name='photos'))
    >>> new_request_token.is_approved = True
    >>> new_request_token.save()
    >>> parameters['oauth_token'] = new_request_token.key
    >>> parameters['oauth_signature'] = '%s&%s' % (CONSUMER_SECRET, new_request_token.secret)
    >>> parameters['oauth_verifier'] = 'invalidverifier'
    >>> response = c.get("/oauth/access_token/", parameters)
    >>> response.status_code
    400
    >>> response.content
    'Invalid OAuth verifier.'
    >>> parameters['oauth_verifier'] = new_request_token.verifier # restore

The Consumer will not be able to request an Access Token if the token is not
approved::

    >>> new_request_token.is_approved = False
    >>> new_request_token.save()
    >>> parameters['oauth_nonce'] = 'anotheraccessnonce'
    >>> response = c.get("/oauth/access_token/", parameters)
    >>> response.status_code
    400
    >>> response.content
    'Request Token not approved by the user.'


Accessing Protected Resources
-----------------------------

The Consumer is now ready to request the private photo. Since the photo URL is 
not secure (HTTP), it must use HMAC-SHA1.

Generating Signature Base String
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To generate the signature, it first needs to generate the Signature Base 
String. The request contains the following parameters (oauth_signature 
excluded) which are ordered and concatenated into a normalized string::

    >>> parameters = {
    ...     'oauth_consumer_key': CONSUMER_KEY,
    ...     'oauth_token': access_token.key,
    ...     'oauth_signature_method': 'HMAC-SHA1',
    ...     'oauth_timestamp': str(int(time.time())),
    ...     'oauth_nonce': 'accessresourcenonce',
    ...     'oauth_version': '1.0',
    ... }


Calculating Signature Value
~~~~~~~~~~~~~~~~~~~~~~~~~~~

HMAC-SHA1 produces the following digest value as a base64-encoded string 
(using the Signature Base String as text and kd94hf93k423kf44&pfkkdhi9sl3r4s00 
as key)::

    >>> import oauth2 as oauth
    >>> oauth_request = oauth.Request.from_token_and_callback(access_token,
    ...     http_url='http://testserver/oauth/photo/', parameters=parameters)
    >>> signature_method = oauth.SignatureMethod_HMAC_SHA1()
    >>> signature = signature_method.sign(oauth_request, consumer, access_token)


Requesting Protected Resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All together, the Consumer request for the photo is::

    >>> parameters['oauth_signature'] = signature
    >>> response = c.get("/oauth/photo/", parameters)
    >>> response.status_code
    200
    >>> response.content
    'Protected Resource access!'

Otherwise, an explicit error will be raised::

    >>> parameters['oauth_signature'] = 'wrongsignature'
    >>> parameters['oauth_nonce'] = 'anotheraccessresourcenonce'
    >>> response = c.get("/oauth/photo/", parameters)
    >>> response.status_code
    401
    >>> response.content
    'Invalid signature. Expected signature base string: GET&http%3A%2F%2F...%2Foauth%2Fphoto%2F&oauth_...'

    >>> response = c.get("/oauth/photo/")
    >>> response.status_code
    401
    >>> response.content
    'Invalid request parameters.'


Revoking Access
---------------

If Jane deletes the Access Token of printer.example.com, the Consumer will not 
be able to access the Protected Resource anymore::

    >>> access_token.delete()
    >>> # Note that an "Invalid signature" error will be raised here if the
    >>> # token is not revoked by Jane because we reuse a previously used one.
    >>> parameters['oauth_signature'] = signature
    >>> parameters['oauth_nonce'] = 'yetanotheraccessresourcenonce'
    >>> response = c.get("/oauth/photo/", parameters)
    >>> response.status_code
    401
    >>> response.content
    'Invalid access token: ...'

"""

import time
import re

from django.test import TestCase
from django.test.client import Client

from django.contrib.auth.models import User
from oauth_provider.models import Resource, Consumer
from oauth_provider.models import Token

class BaseOAuthTestCase(TestCase):
    def setUp(self):
        username = self.username = 'jane'
        password = self.password = 'toto'
        email = self.email = 'jane@example.com'
        jane = self.jane = User.objects.create_user(username, email, password)
        resource = self.resource = Resource(name='photos', url='/oauth/photo/')
        resource.save()
        CONSUMER_KEY = self.CONSUMER_KEY = 'dpf43f3p2l4k3l03'
        CONSUMER_SECRET = self.CONSUMER_SECRET = 'kd94hf93k423kf44'
        consumer = self.consumer = Consumer(key=CONSUMER_KEY, secret=CONSUMER_SECRET,
            name='printer.example.com', user=jane)
        consumer.save()

        self.callback_token = self.callback = 'http://printer.example.com/request_token_ready'
        self.callback_confirmed = True
        self.request_token_parameters = {
            'oauth_consumer_key': self.CONSUMER_KEY,
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_signature': '%s&' % self.CONSUMER_SECRET,
            'oauth_timestamp': str(int(time.time())),
            'oauth_nonce': 'requestnonce',
            'oauth_version': '1.0',
            'oauth_callback': self.callback,
            'scope': 'photos',  # custom argument to specify Protected Resource
        }

        self.c = Client()

    def _request_token(self):
        # The Consumer sends the following HTTP POST request to the
        # Service Provider:
        response = self.c.get("/oauth/request_token/", self.request_token_parameters)
        self.assertEqual(
            response.status_code,
            200
        )
        self.assert_(
            re.match(r'oauth_token_secret=[^&]+&oauth_token=[^&]+&oauth_callback_confirmed=true',
                response.content
            ))
        token = self.request_token = list(Token.objects.all())[-1]
        self.assert_(token.key in response.content)
        self.assert_(token.secret in response.content)
        self.assert_(not self.request_token.is_approved)
        return response


class OAuthTestsBug10(BaseOAuthTestCase):
    """
    See https://code.welldev.org/django-oauth-plus/issue/10/malformed-callback-url-when-user-denies
    """
    def test_Request_token_request_succeeds_with_valid_request_token_parameters(self):
        response = self._request_token()
        token = self.request_token

        self.assertEqual(token.callback,
                         self.callback_token)
        self.assertEqual(
            token.callback_confirmed,
            self.callback_confirmed)

    def test_Requesting_user_authorization_fails_when_user_denies_authorization(self):
        self._request_token()
        self.c.login(username=self.username, password=self.password)
        parameters = self.authorization_parameters = {'oauth_token': self.request_token.key}
        response = self.c.get("/oauth/authorize/", parameters)
        self.assertEqual(
            response.status_code,
            200)

        # fake access not granted by the user (set session parameter again)
        self.authorization_parameters['authorize_access'] = 0
        response = self.c.post("/oauth/authorize/", self.authorization_parameters)
        self.assertEqual(
            response.status_code,
            302)
        self.assertEqual('http://printer.example.com/request_token_ready?error=Access+not+granted+by+user.', response['Location'])
        self.c.logout()

class OAuthOutOfBoundTests(BaseOAuthTestCase):
    def test_Requesting_user_authorization_succeeds_when_oob(self):
        self.request_token_parameters['oauth_callback'] = 'oob'
        self._request_token()

        self.c.login(username=self.username, password=self.password)
        parameters = self.authorization_parameters = {'oauth_token': self.request_token.key}
        response = self.c.get("/oauth/authorize/", parameters)
        
        self.assertEqual(
            response.status_code,
            200)