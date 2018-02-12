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


def get_best_agent(ctx):
    agents = objects.WampAgent.list(ctx, filters={'online': True})
    LOG.debug('found %d Agent(s).', len(agents))
    agent = random.choice(agents)
    LOG.debug('Selected agent: %s', agent.hostname)
    return agent.hostname


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
                                                  board=board.uuid,
                                                  error=res.message)

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
        new_plugin.code = cpickle.dumps(new_plugin.code, 0)
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