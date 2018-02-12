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
        :param data: board id or uuid.
        :param topic: RPC topic. Defaults to self.topic.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'echo', data=data)

    def registration(self, context, code, session_num, topic=None):
        """Registration of a board.

        :param context: request context.
        :param code: token used for the first registration
        :param session_num: wamp session number
        :param topic: RPC topic. Defaults to self.topic.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'registration',
                          code=code, session_num=session_num)

    def connection(self, context, uuid, session_num, topic=None):
        """Connection of a board.

        :param context: request context.
        :param uuid: uuid board
        :param session_num: wamp session number
        :param topic: RPC topic. Defaults to self.topic.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'connection',
                          uuid=uuid, session_num=session_num)

    def create_board(self, context, board_obj, location_obj, topic=None):
        """Add a board on the cloud

        :param context: request context.
        :param board_obj: a changed (but not saved) board object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: created board object

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'create_board',
                          board_obj=board_obj, location_obj=location_obj)

    def update_board(self, context, board_obj, topic=None):
        """Synchronously, have a conductor update the board's information.

        Update the board's information in the database and return
        a board object.

        Note that power_state should not be passed via this method.
        Use change_board_power_state for initiating driver actions.

        :param context: request context.
        :param board_obj: a changed (but not saved) board object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: updated board object, including all fields.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'update_board', board_obj=board_obj)

    def destroy_board(self, context, board_id, topic=None):
        """Delete a board.

        :param context: request context.
        :param board_id: board id or uuid.
        :raises: BoardLocked if board is locked by another conductor.
        :raises: BoardAssociated if the board contains an instance
            associated with it.
        :raises: InvalidState if the board is in the wrong provision
            state to perform deletion.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'destroy_board', board_id=board_id)

    def execute_on_board(self, context, board_uuid, wamp_rpc_call,
                         wamp_rpc_args=None, topic=None):
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'execute_on_board', board_uuid=board_uuid,
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

    def inject_plugin(self, context, plugin_uuid,
                      board_uuid, onboot=False, topic=None):
        """inject a plugin into a board.

        :param context: request context.
        :param plugin_uuid: plugin id or uuid.
        :param board_uuid: board id or uuid.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'inject_plugin', plugin_uuid=plugin_uuid,
                          board_uuid=board_uuid, onboot=onboot)

    def remove_plugin(self, context, plugin_uuid, board_uuid, topic=None):
        """inject a plugin into a board.

        :param context: request context.
        :param plugin_uuid: plugin id or uuid.
        :param board_uuid: board id or uuid.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'remove_plugin', plugin_uuid=plugin_uuid,
                          board_uuid=board_uuid)

    def action_plugin(self, context, plugin_uuid,
                      board_uuid, action, params, topic=None):
        """Action on a plugin into a board.

        :param context: request context.
        :param plugin_uuid: plugin id or uuid.
        :param board_uuid: board id or uuid.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'action_plugin', plugin_uuid=plugin_uuid,
                          board_uuid=board_uuid, action=action, params=params)

    def create_service(self, context, service_obj, topic=None):
        """Add a service on the cloud

        :param context: request context.
        :param service_obj: a changed (but not saved) service object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: created service object

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'create_service',
                          service_obj=service_obj)

    def destroy_service(self, context, service_id, topic=None):
        """Delete a service.

        :param context: request context.
        :param service_id: service id or uuid.
        :raises: ServiceLocked if service is locked by another conductor.
        :raises: ServiceAssociated if the service contains an instance
            associated with it.
        :raises: InvalidState if the service is in the wrong provision
            state to perform deletion.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'destroy_service', service_id=service_id)


    def update_service(self, context, service_obj, topic=None):
        """Synchronously, have a conductor update the service's information.

        Update the service's information in the database and
        return a service object.

        :param context: request context.
        :param service_obj: a changed (but not saved) service object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: updated service object, including all fields.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'update_service', service_obj=service_obj)