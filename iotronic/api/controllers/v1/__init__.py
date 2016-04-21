# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Version 1 of the Iotronic API
"""

from iotronic.api.controllers import base
from iotronic.api.controllers import link
from iotronic.api.controllers.v1 import node
from iotronic.api import expose
from iotronic.common.i18n import _
import pecan
from pecan import rest
from webob import exc
from wsme import types as wtypes


BASE_VERSION = 1

MIN_VER_STR = '1.0'

MAX_VER_STR = '1.0'


MIN_VER = base.Version({base.Version.string: MIN_VER_STR},
                       MIN_VER_STR, MAX_VER_STR)
MAX_VER = base.Version({base.Version.string: MAX_VER_STR},
                       MIN_VER_STR, MAX_VER_STR)


class V1(base.APIBase):
    """The representation of the version 1 of the API."""

    id = wtypes.text
    """The ID of the version, also acts as the release number"""

    # links = [link.Link]
    """Links that point to a specific URL for this version and documentation"""

    nodes = [link.Link]
    """Links to the nodes resource"""

    @staticmethod
    def convert():
        v1 = V1()
        v1.id = "v1"

        v1.nodes = [link.Link.make_link('self', pecan.request.host_url,
                                        'nodes', ''),
                    link.Link.make_link('bookmark',
                                        pecan.request.host_url,
                                        'nodes', '',
                                        bookmark=True)
                    ]

        '''
        v1.links = [link.Link.make_link('self', pecan.request.host_url,
                                        'v1', '', bookmark=True),
                    link.Link.make_link('describedby',
                                        'http://docs.openstack.org',
                                        'developer/iotronic/dev',
                                        'api-spec-v1.html',
                                        bookmark=True, type='text/html')
                    ]
        '''
        return v1


class Controller(rest.RestController):
    """Version 1 API controller root."""

    nodes = node.NodesController()

    @expose.expose(V1)
    def get(self):
        # NOTE: The reason why convert() it's being called for every
        #       request is because we need to get the host url from
        #       the request object to make the links.
        return V1.convert()

    def _check_version(self, version, headers=None):
        if headers is None:
            headers = {}
        # ensure that major version in the URL matches the header
        if version.major != BASE_VERSION:
            raise exc.HTTPNotAcceptable(_(
                "Mutually exclusive versions requested. Version %(ver)s "
                "requested but not supported by this service. The supported "
                "version range is: [%(min)s,%(max)s]."
                ) % {'ver': version, 'min': MIN_VER_STR,
                     'max': MAX_VER_STR},
                headers=headers)
        # ensure the minor version is within the supported range
        if version < MIN_VER or version > MAX_VER:
            raise exc.HTTPNotAcceptable(_(
                "Version %(ver)s was requested but the minor version is not "
                "supported by this service. The supported version range is: "
                "[%(min)s, %(max)s].") % {'ver': version, 'min': MIN_VER_STR,
                                          'max': MAX_VER_STR}, headers=headers)

    @pecan.expose()
    def _route(self, args):
        v = base.Version(pecan.request.headers, MIN_VER_STR, MAX_VER_STR)

        # Always set the min and max headers
        pecan.response.headers[base.Version.min_string] = MIN_VER_STR
        pecan.response.headers[base.Version.max_string] = MAX_VER_STR

        # assert that requested version is supported
        self._check_version(v, pecan.response.headers)
        pecan.response.headers[base.Version.string] = str(v)
        pecan.request.version = v

        return super(Controller, self)._route(args)


__all__ = (Controller)
