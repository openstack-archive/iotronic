from pecan import rest
from iotronic.api import expose
from wsme import types as wtypes
from iotronic import objects
from iotronic.api.controllers.v1 import types
from iotronic.api.controllers.v1 import collection
from iotronic.api.controllers.v1 import location as loc
from iotronic.api.controllers.v1 import utils as api_utils
from iotronic.api.controllers import base
from iotronic.common import exception
import wsme
import pecan
import code


class Node(base.APIBase):
    """API representation of a node.
    """

    uuid = types.uuid
    code = wsme.wsattr(wtypes.text)
    status = wsme.wsattr(wtypes.text)
    name = wsme.wsattr(wtypes.text)
    device = wsme.wsattr(wtypes.text)
    session = wsme.wsattr(wtypes.text)
    mobile = types.boolean
    location = wsme.wsattr([loc.Location])
    extra = types.jsontype

    @staticmethod
    def _convert_with_locates(node, url, expand=True, show_password=True):

        try:
            session = objects.SessionWP(
                {}).get_session_by_node_uuid(
                node.uuid, valid=True)
            node.session = session.session_id
        except:
            pass

        if not expand:
            except_list = ['name', 'code', 'status', 'uuid', 'session']
            node.unset_fields_except(except_list)
            return node

        list_loc = objects.Location({}).list_by_node_id({}, node.id)
        node.location = loc.Location.convert_with_list(list_loc)

        '''
        else:
            if not show_password:
                node.driver_info = ast.literal_eval(strutils.mask_password(
                                                    node.driver_info,
                                                    "******"))
            node.ports = [link.Link.make_link('self', url, 'nodes',
                                              node.uuid + "/ports"),
                          link.Link.make_link('bookmark', url, 'nodes',
                                              node.uuid + "/ports",
                                              bookmark=True)
                          ]

        node.chassis_id = wtypes.Unset

        node.links = [link.Link.make_link('self', url, 'nodes',
                                          node.uuid),
                      link.Link.make_link('bookmark', url, 'nodes',
                                          node.uuid, bookmark=True)
                      ]
        '''
        return node

    @classmethod
    def convert_with_locates(cls, rpc_node, expand=True):
        node = Node(**rpc_node.as_dict())
        node.id = rpc_node.id
        return cls._convert_with_locates(node, pecan.request.host_url,
                                         expand,
                                         pecan.request.context.show_password)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Node.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))


class NodeCollection(collection.Collection):
    """API representation of a collection of nodes."""

    nodes = [Node]
    """A list containing nodes objects"""

    def __init__(self, **kwargs):
        self._type = 'nodes'

    @staticmethod
    def convert_with_locates(nodes, limit, url=None, expand=False, **kwargs):
        collection = NodeCollection()
        collection.nodes = [
            Node.convert_with_locates(
                n, expand) for n in nodes]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class NodesController(rest.RestController):

    invalid_sort_key_list = ['properties']

    def _get_nodes_collection(self, chassis_uuid, instance_uuid, associated,
                              maintenance, marker, limit, sort_key, sort_dir,
                              expand=False, resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Node.get_by_uuid(pecan.request.context,
                                                  marker)

        if sort_key in self.invalid_sort_key_list:
            raise exception.InvalidParameterValue(
                _("The sort_key value %(key)s is an invalid field for "
                  "sorting") % {'key': sort_key})

        if instance_uuid:
            nodes = self._get_nodes_by_instance(instance_uuid)
        else:
            filters = {}
            '''
            if chassis_uuid:
                filters['chassis_uuid'] = chassis_uuid
            if associated is not None:
                filters['associated'] = associated
            if maintenance is not None:
                filters['maintenance'] = maintenance
            '''
            nodes = objects.Node.list(pecan.request.context, limit, marker_obj,
                                      sort_key=sort_key, sort_dir=sort_dir,
                                      filters=filters)

        parameters = {'sort_key': sort_key, 'sort_dir': sort_dir}
        '''
        if associated:
            parameters['associated'] = associated
        if maintenance:
            parameters['maintenance'] = maintenance
        '''
        return NodeCollection.convert_with_locates(nodes, limit,
                                                   url=resource_url,
                                                   expand=expand,
                                                   **parameters)

    @expose.expose(NodeCollection, types.uuid, types.uuid, types.boolean,
                   types.boolean, types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, chassis_uuid=None, instance_uuid=None, associated=None,
                maintenance=None, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of nodes.

        :param chassis_uuid: Optional UUID of a chassis, to get only nodes for
                           that chassis.
        :param instance_uuid: Optional UUID of an instance, to find the node
                              associated with that instance.
        :param associated: Optional boolean whether to return a list of
                           associated or unassociated nodes. May be combined
                           with other parameters.
        :param maintenance: Optional boolean value that indicates whether
                            to get nodes in maintenance mode ("True"), or not
                            in maintenance mode ("False").
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_nodes_collection(chassis_uuid, instance_uuid,
                                          associated, maintenance, marker,
                                          limit, sort_key, sort_dir)

    @expose.expose(Node, types.uuid_or_name)
    def get(self, node_ident):
        """Retrieve information about the given node.

        :param node_ident: UUID or logical name of a node.
        """
        rpc_node = api_utils.get_rpc_node(node_ident)
        node = Node(**rpc_node.as_dict())
        node.id = rpc_node.id
        return Node.convert_with_locates(node)

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, node_ident):
        """Delete a node.

        :param node_ident: UUID or logical name of a node.
        """
        rpc_node = api_utils.get_rpc_node(node_ident)

        try:
            topic = pecan.request.rpcapi.get_topic_for(rpc_node)
        except exception.NoValidHost as e:
            e.code = 400
            raise e

        pecan.request.rpcapi.destroy_node(pecan.request.context,
                                          rpc_node.uuid, topic)

    @expose.expose(Node, body=Node, status_code=201)
    def post(self, Node):
        """Create a new Node.

        :param Node: a Node within the request body.
        """
        if not Node.name:
            raise exception.MissingParameterValue(
                _("Name is not specified."))
        if not Node.code:
            raise exception.MissingParameterValue(
                _("Code is not specified."))
        if not Node.location:
            raise exception.MissingParameterValue(
                _("Location is not specified."))

        if Node.name:
            if not api_utils.is_valid_node_name(Node.name):
                msg = _("Cannot create node with invalid name %(name)s")
                raise wsme.exc.ClientSideError(msg % {'name': Node.name},
                                               status_code=400)

        new_Node = objects.Node(pecan.request.context,
                                **Node.as_dict())
        new_Node.create()

        new_Location = objects.Location(pecan.request.context,
                                        **Node.location[0].as_dict())
        new_Location.node_id = new_Node.id
        new_Location.create()

        # pecan.response.location = link.build_url('Nodes', new_Node.uuid)
        return Node.convert_with_locates(new_Node)
