#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from iotronic.api.controllers import base
from iotronic.api.controllers import link
from iotronic.api.controllers.v1 import collection
from iotronic.api.controllers.v1 import types
from iotronic.api.controllers.v1 import utils as api_utils
from iotronic.api import expose
from iotronic.common import exception
from iotronic.common import policy
from iotronic import objects

from oslo_log import log as logging
LOG = logging.getLogger(__name__)


import pecan
from pecan import rest
import wsme
from wsme import types as wtypes


_DEFAULT_RETURN_FIELDS = ('uuid', 'board_uuid', 'MAC_add',
                          'VIF_name', 'network', 'ip')


class Port(base.APIBase):
    """API representation of a port.

    """
    uuid = types.uuid
    board_uuid = types.uuid
    MAC_add = wsme.wsattr(wtypes.text)
    VIF_name = wsme.wsattr(wtypes.text)
    network = wsme.wsattr(wtypes.text)
    ip = wsme.wsattr(wtypes.text)

    links = wsme.wsattr([link.Link], readonly=True)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Port.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def _convert_with_links(port, url, fields=None):
        port_uuid = port.uuid
        if fields is not None:
            port.unset_fields_except(fields)

        port.links = [link.Link.make_link('self', url, 'ports', port_uuid),
                      link.Link.make_link('bookmark', url, 'ports',
                                          port_uuid, bookmark=True)]
        return port

    @classmethod
    def convert_with_links(cls, rpc_port, fields=None):
        port = Port(**rpc_port.as_dict())

        if fields is not None:
            api_utils.check_for_invalid_fields(fields, port.as_dict())

        return cls._convert_with_links(port, pecan.request.public_url,
                                       fields=fields)


class PortCollection(collection.Collection):
    """API representation of a collection of ports."""

    ports = [Port]
    """A list containing ports objects"""

    def __init__(self, **kwargs):
        self._type = 'ports'

    @staticmethod
    def convert_with_links(ports, limit, url=None, fields=None, **kwargs):
        collection = PortCollection()
        collection.ports = [Port.convert_with_links(n, fields=fields)
                            for n in ports]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class PortsController(rest.RestController):

    """REST controller for Ports."""

#    public = PublicPortsController()

    invalid_sort_key_list = ['extra', 'location']

    def _get_ports_collection(self, marker, limit, sort_key, sort_dir,
                              fields=None, with_public=False,
                              all_ports=False):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Port.get_by_uuid(pecan.request.context,
                                                  marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                ("The sort_key value %(key)s is an invalid field for "
                 "sorting") % {'key': sort_key})

        filters = {}
#        if all_ports and not pecan.request.context.is_admin:
#            msg = ("all_ports parameter can only be used  "
#                   "by the administrator.")
#            raise wsme.exc.ClientSideError(msg,
#                                           status_code=400)
#        else:
#            if not all_ports:
#                filters['owner'] = pecan.request.context.user_id
#                if with_public:
#                    filters['with_public'] = with_public

        ports = objects.Port.list(pecan.request.context, limit, marker_obj,
                                  sort_key=sort_key, sort_dir=sort_dir,
                                  filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}

        return PortCollection.convert_with_links(ports, limit,
                                                 fields=fields, **parameters)

    @expose.expose(PortCollection, types.uuid, int, wtypes.text,
                   wtypes.text, types.listtype, types.boolean, types.boolean)
    def get_all(self, marker=None,
                limit=None, sort_key='id', sort_dir='asc',
                fields=None, with_public=False, all_ports=False):
        """Retrieve a list of ports.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
                      This value cannot be larger than the value of max_limit
                      in the [api] section of the ironic configuration, or only
                      max_limit resources will be returned.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param with_public: Optional boolean to get also public ports.
        :param all_ports: Optional boolean to get all the ports.
                            Only for the admin
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        cdict = pecan.request.context.to_policy_values()
        policy.authorize('iot:port_on_board:get', cdict, cdict)

        if fields is None:
            fields = _DEFAULT_RETURN_FIELDS
        return self._get_ports_collection(marker,
                                          limit, sort_key, sort_dir,
                                          with_public=with_public,
                                          all_ports=all_ports,
                                          fields=fields)

    @expose.expose(Port, types.uuid_or_name, types.listtype)
    def get_one(self, port_ident, fields=None):
        """Retrieve information about the given port.

        :param port_ident: UUID or logical name of a port.
        :param fields: Optional, a list with a specified set of fields
            of the resource to be returned.
        """

        rpc_port = api_utils.get_rpc_port(port_ident)
#        if not rpc_port.public:
#            cdict = pecan.request.context.to_policy_values()
#            cdict['owner'] = rpc_port.owner
#            policy.authorize('iot:port:get_one', cdict, cdict)

        return Port.convert_with_links(rpc_port, fields=fields)

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, port_ident):

        rpc_port = api_utils.get_rpc_port(port_ident)
        board = rpc_port.board_uuid

        pecan.request.rpcapi.remove_port_from_board(pecan.request.context,
                                                    board, rpc_port.uuid)
        return
