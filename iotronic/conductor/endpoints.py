# Copyright 2017 MDSLAB - University of Messina
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

import _pickle as cpickle
from iotronic.common import exception
from iotronic.common import neutron
from iotronic.common import states
from iotronic.conductor.provisioner import Provisioner
from iotronic import objects
from iotronic.objects import base as objects_base
from iotronic.wamp import wampmessage as wm
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
import random


LOG = logging.getLogger(__name__)

serializer = objects_base.IotronicObjectSerializer()

Port = list()


def get_best_agent(ctx):
    agents = objects.WampAgent.list(ctx, filters={'online': True})
    LOG.debug('found %d Agent(s).', len(agents))
    agent = random.choice(agents)
    LOG.debug('Selected agent: %s', agent.hostname)
    return agent.hostname


def random_public_port():
    return random.randint(6000, 7000)


def manage_result(res, wamp_rpc_call, board_uuid):
    if res.result == wm.SUCCESS:
        return res.message
    elif res.result == wm.WARNING:
        LOG.warning('Warning in the execution of %s on %s', wamp_rpc_call,
                    board_uuid)
        return res.message
    elif res.result == wm.ERROR:
        LOG.error('Error in the execution of %s on %s: %s', wamp_rpc_call,
                  board_uuid, res.message)
        raise exception.ErrorExecutionOnBoard(call=wamp_rpc_call,
                                              board=board_uuid,
                                              error=res.message)
    return res.message


class ConductorEndpoint(object):
    def __init__(self, ragent):
        transport = oslo_messaging.get_transport(cfg.CONF)
        self.target = oslo_messaging.Target()
        self.wamp_agent_client = oslo_messaging.RPCClient(transport,
                                                          self.target)
        self.wamp_agent_client.prepare(timeout=10)
        self.ragent = ragent

    def echo(self, ctx, data):
        LOG.info("ECHO: %s" % data)
        return data

    def registration(self, ctx, code, session_num):
        LOG.debug('Received registration from %s with session %s',
                  code, session_num)
        try:
            board = objects.Board.get_by_code(ctx, code)

        except Exception as exc:
            msg = exc.message % {'board': code}
            LOG.error(msg)
            return wm.WampError(msg).serialize()

        if not board.status == states.REGISTERED:
            msg = "board with code %(board)s cannot " \
                  "be registered again." % {'board': code}
            LOG.error(msg)
            return wm.WampError(msg).serialize()

        try:
            old_ses = objects.SessionWP(ctx)
            old_ses = old_ses.get_session_by_board_uuid(ctx, board.uuid,
                                                        valid=True)
            old_ses.valid = False
            old_ses.save()

        except Exception:
            LOG.debug('valid session for %s not found', board.uuid)

        session_data = {'board_id': board.id,
                        'board_uuid': board.uuid,
                        'session_id': session_num}
        session = objects.SessionWP(ctx, **session_data)
        session.create()

        board.agent = get_best_agent(ctx)
        agent = objects.WampAgent.get_by_hostname(ctx, board.agent)

        prov = Provisioner(board)
        prov.conf_registration_agent(self.ragent.wsurl)

        prov.conf_main_agent(agent.wsurl)
        loc = objects.Location.list_by_board_uuid(ctx, board.uuid)[0]
        prov.conf_location(loc)
        board.config = prov.get_config()

        board.status = states.OFFLINE
        board.save()

        LOG.debug('sending this conf %s', board.config)

        wmessage = wm.WampSuccess(board.config)
        return wmessage.serialize()

    def destroy_board(self, ctx, board_id):
        LOG.info('Destroying board with id %s',
                 board_id)
        board = objects.Board.get_by_uuid(ctx, board_id)
        result = None
        if board.is_online():
            prov = Provisioner()
            prov.conf_clean()
            p = prov.get_config()
            LOG.debug('sending this conf %s', p)
            try:
                result = self.execute_on_board(ctx,
                                               board_id,
                                               'destroyBoard',
                                               (p,))

            except exception:
                return exception
        board.destroy()
        if result:
            result = manage_result(result, 'destroyBoard', board_id)
            LOG.debug(result)
            return result
        return

    def update_board(self, ctx, board_obj):
        board = serializer.deserialize_entity(ctx, board_obj)
        LOG.debug('Updating board %s', board.name)
        board.save()
        return serializer.serialize_entity(ctx, board)

    def create_board(self, ctx, board_obj, location_obj):
        new_board = serializer.deserialize_entity(ctx, board_obj)
        LOG.debug('Creating board %s',
                  new_board.name)
        new_location = serializer.deserialize_entity(ctx, location_obj)
        new_board.create()
        new_location.board_id = new_board.id
        new_location.create()

        return serializer.serialize_entity(ctx, new_board)

    def execute_on_board(self, ctx, board_uuid, wamp_rpc_call, wamp_rpc_args):
        LOG.debug('Executing \"%s\" on the board: %s',
                  wamp_rpc_call, board_uuid)

        board = objects.Board.get_by_uuid(ctx, board_uuid)

        s4t_topic = 's4t_invoke_wamp'
        full_topic = board.agent + '.' + s4t_topic
        self.target.topic = full_topic
        full_wamp_call = 'iotronic.' + board.uuid + "." + wamp_rpc_call

        # check the session; it rise an excpetion if session miss
        if not board.is_online():
            raise exception.BoardNotConnected(board=board.uuid)

        res = self.wamp_agent_client.call(ctx, full_topic,
                                          wamp_rpc_call=full_wamp_call,
                                          data=wamp_rpc_args)
        res = wm.deserialize(res)

        return res

    def destroy_plugin(self, ctx, plugin_id):
        LOG.info('Destroying plugin with id %s',
                 plugin_id)
        plugin = objects.Plugin.get_by_uuid(ctx, plugin_id)
        plugin.destroy()
        return

    def update_plugin(self, ctx, plugin_obj):
        plugin = serializer.deserialize_entity(ctx, plugin_obj)
        LOG.debug('Updating plugin %s', plugin.name)
        plugin.save()
        return serializer.serialize_entity(ctx, plugin)

    def create_plugin(self, ctx, plugin_obj):
        new_plugin = serializer.deserialize_entity(ctx, plugin_obj)
        LOG.debug('Creating plugin %s',
                  new_plugin.name)
        new_plugin.code = cpickle.dumps(new_plugin.code, 0).decode()
        new_plugin.create()
        return serializer.serialize_entity(ctx, new_plugin)

    def inject_plugin(self, ctx, plugin_uuid, board_uuid, onboot):
        LOG.info('Injecting plugin with id %s into the board %s',
                 plugin_uuid, board_uuid)

        plugin = objects.Plugin.get(ctx, plugin_uuid)
        try:
            result = self.execute_on_board(ctx,
                                           board_uuid,
                                           'PluginInject',
                                           (plugin, onboot))
        except exception:
            return exception

        injection = None
        try:
            injection = objects.InjectionPlugin.get(ctx,
                                                    board_uuid,
                                                    plugin_uuid)
        except Exception:
            pass
        if injection:
            injection.status = 'updated'
            injection.save()
        else:
            inj_data = {
                'board_uuid': board_uuid,
                'plugin_uuid': plugin_uuid,
                'onboot': onboot,
                'status': 'injected'
            }
            injection = objects.InjectionPlugin(ctx, **inj_data)
            injection.create()

        result = manage_result(result, 'PluginInject', board_uuid)
        LOG.debug(result)

        return result

    def remove_plugin(self, ctx, plugin_uuid, board_uuid):
        LOG.info('Removing plugin with id %s into the board %s',
                 plugin_uuid, board_uuid)

        plugin = objects.Plugin.get_by_uuid(ctx, plugin_uuid)

        injection = objects.InjectionPlugin.get(ctx, board_uuid, plugin_uuid)

        try:
            result = self.execute_on_board(ctx, board_uuid, 'PluginRemove',
                                           (plugin.uuid,))
        except exception:
            return exception
        result = manage_result(result, 'PluginRemove', board_uuid)
        LOG.debug(result)
        injection.destroy()
        return result

    def action_plugin(self, ctx, plugin_uuid, board_uuid, action, params):
        LOG.info('Calling plugin with id %s into the board %s with params %s',
                 plugin_uuid, board_uuid, params)
        plugin = objects.Plugin.get(ctx, plugin_uuid)
        objects.plugin.is_valid_action(action)

        try:
            if objects.plugin.want_params(action):
                result = self.execute_on_board(ctx, board_uuid, action,
                                               (plugin.uuid, params))
            else:
                result = self.execute_on_board(ctx, board_uuid, action,
                                               (plugin.uuid,))
        except exception:
            return exception
        result = manage_result(result, action, board_uuid)
        LOG.debug(result)
        return result

    def create_service(self, ctx, service_obj):
        new_service = serializer.deserialize_entity(ctx, service_obj)
        LOG.debug('Creating service %s',
                  new_service.name)
        new_service.create()
        return serializer.serialize_entity(ctx, new_service)

    def destroy_service(self, ctx, service_id):
        LOG.info('Destroying service with id %s',
                 service_id)
        service = objects.Service.get_by_uuid(ctx, service_id)
        service.destroy()
        return

    def update_service(self, ctx, service_obj):
        service = serializer.deserialize_entity(ctx, service_obj)
        LOG.debug('Updating service %s', service.name)
        service.save()
        return serializer.serialize_entity(ctx, service)

    def action_service(self, ctx, service_uuid, board_uuid, action):
        service = objects.Service.get(ctx, service_uuid)
        objects.service.is_valid_action(action)

        if action == "ServiceEnable":
            LOG.info('Enabling service with id %s into the board %s',
                     service_uuid, board_uuid)
            try:
                objects.ExposedService.get(ctx,
                                           board_uuid,
                                           service_uuid)
                return exception.ServiceAlreadyExposed(uuid=service_uuid)
            except Exception:
                public_port = random_public_port()

                res = self.execute_on_board(ctx, board_uuid, action,
                                            (service, public_port))
                result = manage_result(res, action, board_uuid)

                exp_data = {
                    'board_uuid': board_uuid,
                    'service_uuid': service_uuid,
                    'public_port': public_port,
                }
                exposed = objects.ExposedService(ctx, **exp_data)
                exposed.create()

                LOG.debug(result)
                return result

        elif action == "ServiceDisable":
            LOG.info('Disabling service with id %s into the board %s',
                     service_uuid, board_uuid)
            exposed = objects.ExposedService.get(ctx,
                                                 board_uuid,
                                                 service_uuid)

            res = self.execute_on_board(ctx, board_uuid, action,
                                        (service,))

            result = manage_result(res, action, board_uuid)
            LOG.debug(res.message)
            exposed.destroy()
            return result

        elif action == "ServiceRestore":
            LOG.info('Restoring service with id %s into the board %s',
                     service_uuid, board_uuid)
            exposed = objects.ExposedService.get(ctx, board_uuid,
                                                 service_uuid)

            res = self.execute_on_board(ctx, board_uuid, action,
                                        (service, exposed.public_port))

            result = manage_result(res, action, board_uuid)
            LOG.debug(result)
            return result

    def restore_services_on_board(self, ctx, board_uuid):
        LOG.info('Restoring the services into the board %s',
                 board_uuid)
        exposed_list = objects.ExposedService.get_by_board_uuid(ctx,
                                                                board_uuid)

        for exposed in exposed_list:
            service = objects.Service.get_by_uuid(ctx, exposed.service_uuid)
            self.execute_on_board(ctx, board_uuid, "ServiceRestore",
                                  (service, exposed.public_port))

        return 0

    def create_port_on_board(self, ctx, board_uuid, network_uuid,
                             subnet_uuid, security_groups=None):

        LOG.info('Creation of a port on the board %s in the network',
                 board_uuid)

        board = objects.Board.get_by_uuid(ctx, board_uuid)
        port_iotronic = objects.Port(ctx)

        subnet_info = neutron.subnet_info(subnet_uuid)
        cidr = str(subnet_info['subnet']['cidr'])
        slash = cidr.split("/", 1)[1]
        try:

            port = neutron.add_port_to_network(board, network_uuid,
                                               subnet_uuid, security_groups)
            p = str(port['port']['id'])

            port_socat = random.randint(10000, 20000)

            i = 0
            while i < len(Port):
                if Port[i] == port_socat:
                    i = 0
                    port_socat = random.randint(10000, 20000)
                i += 1

            global Port
            Port.insert(0, port_socat)
            r_tcp_port = str(port_socat)

            s4t_topic = 'create_tap_interface'
            full_topic = str(board.agent) + '.' + s4t_topic
            self.target.topic = full_topic

            try:
                LOG.info('Creation of the VIF on the board')
                self.execute_on_board(ctx, board_uuid, "Create_VIF",
                                      (r_tcp_port,))

                try:
                    LOG.debug('starting the wamp client')
                    self.wamp_agent_client.call(ctx, full_topic,
                                                port_uuid=p,
                                                tcp_port=r_tcp_port)

                    try:
                        LOG.info('Updating the DB')
                        VIF = str("iotronic" + str(r_tcp_port))
                        port_iotronic.VIF_name = VIF
                        port_iotronic.uuid = port['port']['id']
                        port_iotronic.MAC_add = port['port']['mac_address']
                        port_iotronic.board_uuid = str(board_uuid)
                        port_iotronic.network = \
                            port['port']['fixed_ips'][0]['subnet_id']
                        port_iotronic.ip = \
                            port['port']['fixed_ips'][0]['ip_address']
                        port_iotronic.create()

                        try:
                            LOG.debug('Configuration of the VIF')
                            self.execute_on_board(ctx, board_uuid,
                                                  "Configure_VIF",
                                                  (port_iotronic, slash,))
                            return port_iotronic

                        except Exception:
                            LOG.error("Error while configuring the VIF")

                    except Exception as e:
                        LOG.error('Error while updating the DB :' + str(e))

                except Exception:
                    LOG.error('wamp client error')

            except Exception:
                LOG.error('Error while creating the VIF')

        except Exception as e:
            LOG.error(str(e))

    def remove_VIF_from_board(self, ctx, board_uuid, port_uuid):

        LOG.info('removing the port %s from board %s',
                 port_uuid, board_uuid)

        board = objects.Board.get_by_uuid(ctx, board_uuid)
        port = objects.Port.get_by_uuid(ctx, port_uuid)
        VIF_name = str(port.VIF_name)

        try:

            self.execute_on_board(ctx, board_uuid, "Remove_VIF", (VIF_name,))
            port_num = int(VIF_name[8:])
            global Port
            Port.remove(port_num)
            try:
                LOG.info("Removing the port from Neutron "
                         "and Iotronic databases")
                neutron.delete_port(board.agent, port_uuid)
                LOG.info("Port removed from Neutron DB")
                port.destroy()
                LOG.info("Port removed from Iotronic DB")

                return port

            except Exception as e:
                LOG.error(str(e))

        except Exception as e:
            LOG.error(str(e))
