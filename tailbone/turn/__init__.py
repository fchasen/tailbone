# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from tailbone import BaseHandler
from tailbone import as_json
from tailbone import AppError
from tailbone import DEBUG
from tailbone import PREFIX
from tailbone.compute_engine import LoadBalancer
from tailbone.compute_engine import TailboneCEInstance
from tailbone.compute_engine import STARTUP_SCRIPT_BASE

import binascii
from hashlib import sha1
import hmac
import md5
import time
import webapp2

from google.appengine.api import lib_config
from google.appengine.ext import ndb


class _ConfigDefaults(object):
  SECRET = "notasecret"
  RESTRICTED_DOMAINS = ["localhost"]

_config = lib_config.register('tailboneTurn', _ConfigDefaults.__dict__)

# Prefixing internal models with Tailbone to avoid clobbering when using RESTful API
class TailboneTurnInstance(TailboneCEInstance):
  PARAMS = dict(TailboneCEInstance.PARAMS, **{
    "name": "turn-id",
    "metadata": {
      "items": [
        {
          "key": "startup-script",
          "value": STARTUP_SCRIPT_BASE + """
# load turnserver
curl -O http://rfc5766-turn-server.googlecode.com/files/turnserver-1.8.7.0-binary-linux-wheezy-ubuntu-mint-x86-64bits.tar.gz
tar xvfz turnserver-1.8.7.0-binary-linux-wheezy-ubuntu-mint-x86-64bits.tar.gz
dpkg -i rfc5766-turn-server_1.8.7.0-1_amd64.deb
apt-get -fy install
turnserver --use-auth-secret -v -a -X -f --static-auth-secret %s %s
 
""" % (_config.SECRET, " ".join(["-r " + str(d) for d in _config.RESTRICTED_DOMAINS]),)
        },
      ],
    }
  })

  secret = ndb.StringProperty(default=_config.SECRET)

def credentials(username, secret=None):
  timestamp = str(time.mktime(time.gmtime())).split('.')[0]
  username = "{}:{}".format(username, timestamp)
  if not secret:
    secret = _config.SECRET
  # force string
  secret = str(secret)
  password = hmac.new(secret, username, sha1)
  password = binascii.b2a_base64(password.digest())[:-1]
  return username, password


class TurnHandler(BaseHandler):
  @as_json
  def get(self):
    username = self.request.get("username")
    if not username:
      raise AppError("Must provide username.")
    instance = LoadBalancer.find(TailboneTurnInstance, self.request)
    if not instance:
      raise AppError('Instance not found, try again later.')
    username, password = credentials(username, instance.secret)
    return {
      "username": username,
      "password": password,
      "turn": instance.address
    }

app = webapp2.WSGIApplication([
  (r"{}turn/?.*".format(PREFIX), TurnHandler),
], debug=DEBUG)