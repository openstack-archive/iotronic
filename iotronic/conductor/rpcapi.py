# coding=utf-8

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
Client side of the conductor RPC API.
"""
from iotronic.common import rpc
from iotronic.conductor import manager
from iotronic.objects import base
import oslo_messaging


class ConductorAPI(object):
    """Client side of the conductor RPC API.

    API version history:
    |    1.0 - Initial version.
    """

    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        super(ConductorAPI, self).__init__()
        self.topic = topic
        if self.topic is None:
            self.topic = manager.MANAGER_TOPIC

        target = oslo_messaging.Target(topic=self.topic,
                                       version='1.0')
        serializer = base.IotronicObjectSerializer()
        self.client = rpc.get_client(target,
                                     version_cap=self.RPC_API_VERSION,
                                     serializer=serializer)

    def echo(self, context, data, topic=None):
        """Test

        :param context: request context.
        :param data: node id or uuid.
        :param topic: RPC topic. Defaults to self.topic.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'echo', data=data)

    def registration(self, context, code, session_num, topic=None):
        """Registration of a node.

        :param context: request context.
        :param code: token used for the first registration
        :param session_num: wamp session number
        :param topic: RPC topic. Defaults to self.topic.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'registration',
                          code=code, session_num=session_num)

    def registration_uuid(self, context, uuid, session_num, topic=None):
        """Registration of a node.

        :param context: request context.
        :param uuid: uuid node
        :param session_num: wamp session number
        :param topic: RPC topic. Defaults to self.topic.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'registration_uuid',
                          uuid=uuid, session_num=session_num)

    def create_node(self, context, node_obj, location_obj, topic=None):
        """Add a node on the cloud

        :param context: request context.
        :param node_obj: a changed (but not saved) node object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: created node object

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'create_node',
                          node_obj=node_obj, location_obj=location_obj)

    def update_node(self, context, node_obj, topic=None):
        """Synchronously, have a conductor update the node's information.

        Update the node's information in the database and return a node object.

        Note that power_state should not be passed via this method.
        Use change_node_power_state for initiating driver actions.

        :param context: request context.
        :param node_obj: a changed (but not saved) node object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: updated node object, including all fields.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'update_node', node_obj=node_obj)

    def destroy_node(self, context, node_id, topic=None):
        """Delete a node.

        :param context: request context.
        :param node_id: node id or uuid.
        :raises: NodeLocked if node is locked by another conductor.
        :raises: NodeAssociated if the node contains an instance
            associated with it.
        :raises: InvalidState if the node is in the wrong provision
            state to perform deletion.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'destroy_node', node_id=node_id)

    def execute_on_node(self, context, node_uuid, wamp_rpc_call,
                        wamp_rpc_args=None, topic=None):
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'execute_on_node', node_uuid=node_uuid,
                          wamp_rpc_call=wamp_rpc_call,
                          wamp_rpc_args=wamp_rpc_args)

    def create_plugin(self, context, plugin_obj, topic=None):
        """Add a plugin on the cloud

        :param context: request context.
        :param plugin_obj: a changed (but not saved) plugin object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: created plugin object

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'create_plugin',
                          plugin_obj=plugin_obj)

    def update_plugin(self, context, plugin_obj, topic=None):
        """Synchronously, have a conductor update the plugin's information.

        Update the plugin's information in the database and
        return a plugin object.

        :param context: request context.
        :param plugin_obj: a changed (but not saved) plugin object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: updated plugin object, including all fields.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'update_plugin', plugin_obj=plugin_obj)

    def destroy_plugin(self, context, plugin_id, topic=None):
        """Delete a plugin.

        :param context: request context.
        :param plugin_id: plugin id or uuid.
        :raises: PluginLocked if plugin is locked by another conductor.
        :raises: PluginAssociated if the plugin contains an instance
            associated with it.
        :raises: InvalidState if the plugin is in the wrong provision
            state to perform deletion.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'destroy_plugin', plugin_id=plugin_id)
