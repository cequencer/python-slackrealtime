"""
slackrealtime/api.py - Barebones implementation of the Slack API.
Copyright 2014-2015 Michael Farrell <http://micolous.id.au>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import absolute_import
import requests, json
from urlparse import urljoin

SLACK_API_URL = 'https://slack.com/api/'

class SlackError(Exception):
	"""
	Thrown by ``SlackMethod`` calls in response to an error returned by the Slack API.
	"""
	pass

class SlackMethod(object):
	def __init__(self, url, group, method):
		self.url = url
		self.method = group + '.' + method

	def __call__(self, **kwargs):
		# Prune any None parameters -- these should be defaults
		params = {}
		for k, v in kwargs.iteritems():
			if v is not None:
				if isinstance(v, list) or isinstance(v, dict):
					# Complex datatypes, JSON encode it
					params[k] = json.dumps(v)
				else:
					# Simple datatypes
					params[k] = v

		response = requests.post(urljoin(self.url, self.method), data=params)

		if callable(response.json):
			# Newer versions of requests use this API
			response = response.json()
		else:
			# Older versions implement this as a property.
			response = response.json

		assert response['ok'] in (True, False), 'ok must be True or False'
		if not response['ok']:
			raise SlackError, response['error']

		# Trim this attribute as it is no longer required
		del response['ok']
		return response

	def __str__(self):
		return '<SlackMethod: %s at %s>' % (self.method, self.url)


class SlackMethodGroup(object):
	def __init__(self, url, group):
		self.url = url
		self.group = group

	def __getattr__(self, method):
		if self.group == 'user' and method == 'admin':
			# 'xoxs' keys can access some extra undocumented methods.
			return SlackMethodGroup(self.url, self.group + '.' + method)

		return SlackMethod(self.url, self.group, method)

	def __str__(self):
		return '<SlackMethodGroup: %s at %s>' % (self.group, self.url)


class SlackApi(object):
	"""
	SlackApi is a barebones, zero-knowledge (dynamic) implementation of Slack's REST API.  

	It uses some ``__getattr__`` and ``__call__`` tricks in order to present the API it's
	method calls as a set of Python objects, allowing interactions like this::

		slack = SlackApi()
		response = slack.rtm.start(token=token)

	It automatically handles the deserialisation of objects for you, and sends parameters
	as a ``HTTP POST`` request.  When errors occur, they are thrown as a
	``SlackException``.

	When the official Slack HTTPS URI is used (the default), ``requests`` provides a
	certificate and connection validation facility.

	Reference for the Slack API is provided at: https://api.slack.com/
	"""
	def __init__(self, url=SLACK_API_URL):
		if not url.endswith('/'):
			url += '/'
		self.url = url
	
	def __getattr__(self, group):
		# Gets a method descriptor
		return SlackMethodGroup(self.url, group)

