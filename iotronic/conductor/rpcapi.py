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

    def action_service(self, context, service_uuid,
                       board_uuid, action, topic=None):
        """Action on a service into a board.

        :param context: request context.
        :param service_uuid: service id or uuid.
        :param board_uuid: board id or uuid.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')

        return cctxt.call(context, 'action_service', service_uuid=service_uuid,
                          board_uuid=board_uuid, action=action)

    def restore_services_on_board(self, context,
                                  board_uuid, topic=None):
        """Restore all the services on a board.

        :param context: request context.
        :param board_uuid: board id or uuid.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')

        return cctxt.call(context, 'restore_services_on_board',
                          board_uuid=board_uuid)

    def create_port_on_board(self, context, board_uuid, network,
                             subnet, sec_groups, topic=None):
        """Add a port on a Board

        :param context: request context.
        :param board_uuid: the uuid of the board.
        :param network: the network uuid where the port will be created.
        :param subnet: the subnet uuid where the port will be created.
        :param sec_groups: security groups associated to the port.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: created port object

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'create_port_on_board',
                          board_uuid=board_uuid, network_uuid=network,
                          subnet_uuid=subnet, security_groups=sec_groups)

    def remove_port_from_board(self, context, board_uuid,
                               port_uuid, topic=None):
        """remove a port from a Board

                :param context: request context.
                :param board_uuid: the board uuid where the port resides.
                :param port_uuid: the UUID of the port.
                :returns: delete port object

                """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'remove_VIF_from_board',
                          board_uuid=board_uuid,
                          port_uuid=port_uuid)

    def create_fleet(self, context, fleet_obj, topic=None):
        """Add a fleet on the cloud

        :param context: request context.
        :param fleet_obj: a changed (but not saved) fleet object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: created fleet object

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'create_fleet',
                          fleet_obj=fleet_obj)

    def destroy_fleet(self, context, fleet_id, topic=None):
        """Delete a fleet.

        :param context: request context.
        :param fleet_id: fleet id or uuid.
        :raises: FleetLocked if fleet is locked by another conductor.
        :raises: FleetAssociated if the fleet contains an instance
            associated with it.
        :raises: InvalidState if the fleet is in the wrong provision
            state to perform deletion.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'destroy_fleet', fleet_id=fleet_id)

    def update_fleet(self, context, fleet_obj, topic=None):
        """Synchronously, have a conductor update the fleet's information.

        Update the fleet's information in the database and
        return a fleet object.

        :param context: request context.
        :param fleet_obj: a changed (but not saved) fleet object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: updated fleet object, including all fields.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'update_fleet', fleet_obj=fleet_obj)

    def create_webservice(self, context, webservice_obj, topic=None):
        """Add a webservice on the cloud

        :param context: request context.
        :param webservice_obj: a changed (but not saved) webservice object.
        :param topic: RPC topic. Defaults to self.topic.
        :returns: created webservice object

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'create_webservice',
                          webservice_obj=webservice_obj)

    def destroy_webservice(self, context, webservice_id, topic=None):
        """Delete a webservice.

        :param context: request context.
        :param webservice_id: webservice id or uuid.
        :raises: WebserviceLocked if webservice is locked by another conductor.
        :raises: WebserviceAssociated if the webservice contains an instance
            associated with it.
        :raises: InvalidState if the webservice is in the wrong provision
            state to perform deletion.
        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'destroy_webservice',
                          webservice_id=webservice_id)

    def enable_webservice(self, context, dns, zone, email, board, topic=None):
        """Eneble a webservice on the board

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'enable_webservice',
                          dns=dns, zone=zone, email=email, board_uuid=board)

    def disable_webservice(self, context, board_uuid, topic=None):
        """Disable webservice manager.

        """
        cctxt = self.client.prepare(topic=topic or self.topic, version='1.0')
        return cctxt.call(context, 'disable_webservice',
                          board_uuid=board_uuid)
