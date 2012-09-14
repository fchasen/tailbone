import datetime
import json
import random
import tailbone
import time
import unittest
import webapp2
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.ext import testbed

class DataBindingTestCase(unittest.TestCase):
  pass

class RestfulTestCase(unittest.TestCase):

  def setUp(self):
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_memcache_stub()
    self.model_url = "/api/todo/"

  def tearDown(self):
    self.testbed.deactivate()

  def create(self, url, data):
    request = webapp2.Request.blank(url)
    request.method = "POST"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(tailbone.app)
    self.assertEqual(response.headers["Content-Type"], "application/json")
    response_data = json.loads(response.body)
    return response, response_data

  def assertJsonResponseData(self, response, data):
    self.assertEqual(response.headers["Content-Type"], "application/json")
    response_data = json.loads(response.body)
    for ignored in ["Id"]:
      if response_data.has_key(ignored):
        del response_data[ignored]
      if data.has_key(ignored):
        del data[ignored]
    self.assertEqual(data, response_data)


  def test_query_by_id(self):
    data = {"text": "example"}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank(self.model_url+str(response_data["Id"]))
    response = request.get_response(tailbone.app)

    self.assertJsonResponseData(response, data)

  def test_query_all(self):
    num_items = 3
    data = {"text": "example"}
    for i in xrange(num_items):
      response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank(self.model_url)
    response = request.get_response(tailbone.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), num_items)
    self.assertEqual(response.headers["Content-Type"], "application/json")

  def test_query_gte(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": i+0.1}
      response, response_data = self.create(self.model_url, data)
    data = {"text": 2}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?filter=text>=1".format(self.model_url))
    response = request.get_response(tailbone.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), 3)

  def test_query_bool(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": True}
      response, response_data = self.create(self.model_url, data)
    data = {"text": False}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?filter=text==true".format(self.model_url))
    response = request.get_response(tailbone.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), num_items)

  def test_query_in(self):
    pass

  def test_query_subobject(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": {"sub": True}}
      response, response_data = self.create(self.model_url, data)
    data = {"text": {"sub": False}}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?filter=text.sub==true".format(self.model_url))
    response = request.get_response(tailbone.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), num_items)

  def test_order_asc(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": i}
      response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?order=text".format(self.model_url))
    response = request.get_response(tailbone.app)
    items = json.loads(response.body)
    self.assertEqual(items[0], {"text":0, "Id": 1})
    self.assertEqual(len(items), num_items)

  def test_order_desc(self):
    num_items = 3
    for i in xrange(num_items):
      data = {"text": i}
      response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank("{}?order=-text".format(self.model_url))
    response = request.get_response(tailbone.app)
    items = json.loads(response.body)
    self.assertEqual(items[0], {"text":2, "Id": 3})
    self.assertEqual(len(items), num_items)

  def test_create_with_post(self):
    data = {"text": "example"}
    response, response_data = self.create(self.model_url, data)
    data["Id"] = 1
    self.assertEqual(json.dumps(data), json.dumps(response_data))

  def test_update_with_put(self):
    data = {"text": "example"}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank(self.model_url+str(response_data["Id"]))
    data = {"text": "new text"}
    request.method = "PUT"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(tailbone.app)

    self.assertEqual(json.loads(response.body).get("Id"), 1)

    self.assertJsonResponseData(response, data)

  def test_delete(self):
    data = {"text": "example"}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank(self.model_url+str(response_data["Id"]))
    data = {"text": "example"}
    request.method = "DELETE"
    request.headers["Content-Type"] = "application/json"
    request.body = json.dumps(data)
    response = request.get_response(tailbone.app)
    response_data = json.loads(response.body)
    self.assertEqual(json.dumps(response_data), json.dumps({}))

    request = webapp2.Request.blank(self.model_url)
    response = request.get_response(tailbone.app)
    items = json.loads(response.body)
    self.assertEqual(len(items), 0)

  def test_put_to_create(self):
    pass

  def test_create_with_specific_id(self):
    pass

  def test_variable_data_same_class(self):
    data = {"text": "example"}
    response, response_data = self.create(self.model_url, data)
    data = {"different": "text"}
    response, response_data = self.create(self.model_url, data)
    data = {"different": "text", "subobject": {"more": 323232}}
    response, response_data = self.create(self.model_url, data)

    request = webapp2.Request.blank(self.model_url)
    response = request.get_response(tailbone.app)
    items = json.loads(response.body)

  def test_datetime(self):
    obj = datetime.datetime.now()
    ms = time.mktime(obj.utctimetuple()) * 1000
    ms += getattr(obj, "microseconds", 0) / 1000
    data = {"date": int(ms)}
    response, response_data = self.create(self.model_url, data)

    self.assertJsonResponseData(response, data)

  def test_large_text(self):
    data = {"text": "example" * 100}
    response, response_data = self.create(self.model_url, data)

    self.assertJsonResponseData(response, data)

  def test_dict_property(self):
    data = {"obj": {"another": "obj"}}
    response, response_data = self.create(self.model_url, data)

    self.assertJsonResponseData(response, data)