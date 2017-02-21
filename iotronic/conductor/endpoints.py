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

from iotronic.common import exception
from iotronic.common import states
from iotronic.conductor.provisioner import Provisioner
from iotronic import objects
from iotronic.objects import base as objects_base
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

    def registration_uuid(self, ctx, uuid, session_num):
        LOG.debug('Received registration from %s with session %s',
                  uuid, session_num)
        try:
            node = objects.Node.get_by_uuid(ctx, uuid)
        except Exception:
            return exception.NodeNotFound(node=uuid)
        try:
            old_session = objects.SessionWP(
                ctx).get_session_by_node_uuid(node.uuid, valid=True)
            old_session.valid = False
            old_session.save()
        except Exception:
            LOG.debug('valid session for %s not found', node.uuid)

        node.status = states.REGISTERED
        node.save()

        session = objects.SessionWP(ctx)
        session.node_id = node.id
        session.node_uuid = node.uuid
        session.session_id = session_num
        session.create()
        session.save()
        return

    def registration(self, ctx, code, session_num):
        LOG.debug('Received registration from %s with session %s',
                  code, session_num)
        try:
            node = objects.Node.get_by_code(ctx, code)
        except Exception:
            return exception.NodeNotFound(node=code)
        try:
            old_session = objects.SessionWP(ctx
                                            ).get_session_by_node_uuid(
                node.uuid, valid=True)
            old_session.valid = False
            old_session.save()
        except Exception:
            LOG.debug('valid session for %s Not found', node.uuid)

        session = objects.SessionWP(ctx)
        session.node_id = node.id
        session.node_uuid = node.uuid
        session.session_id = session_num
        session.create()
        session.save()

        node.agent = get_best_agent(ctx)
        agent = objects.WampAgent.get_by_hostname(ctx, node.agent)

        prov = Provisioner(node)
        prov.conf_registration_agent(self.ragent.wsurl)

        prov.conf_main_agent(agent.wsurl)
        node.config = prov.get_config()
        node.save()

        LOG.debug('sending this conf %s', node.config)
        return node.config

    def destroy_node(self, ctx, node_id):
        LOG.info('Destroying node with id %s',
                 node_id)
        node = objects.Node.get_by_uuid(ctx, node_id)

        prov = Provisioner()
        prov.conf_clean()
        p = prov.get_config()
        LOG.debug('sending this conf %s', p)
        try:
            self.execute_on_node(ctx, node_id, 'destroyNode', (p,))
        except Exception:
            LOG.error('cannot execute remote destroynode on %s. '
                      'Maybe it is OFFLINE', node_id)

        node.destroy()

        return

    def update_node(self, ctx, node_obj):
        node = serializer.deserialize_entity(ctx, node_obj)
        LOG.debug('Updating node %s', node.name)
        node.save()
        return serializer.serialize_entity(ctx, node)

    def create_node(self, ctx, node_obj, location_obj):
        new_node = serializer.deserialize_entity(ctx, node_obj)
        LOG.debug('Creating node %s',
                  new_node.name)
        new_location = serializer.deserialize_entity(ctx, location_obj)
        new_node.create()
        new_location.node_id = new_node.id
        new_location.create()

        return serializer.serialize_entity(ctx, new_node)

    def execute_on_node(self, ctx, node_uuid, wamp_rpc_call, wamp_rpc_args):
        LOG.debug('Executing \"%s\" on the node: %s', wamp_rpc_call, node_uuid)

        node = objects.Node.get_by_uuid(ctx, node_uuid)

        # check the session; it rise an excpetion if session miss
        # session = objects.SessionWP.get_session_by_node_uuid(node_uuid)

        s4t_topic = 's4t_invoke_wamp'
        full_topic = node.agent + '.' + s4t_topic

        self.target.topic = full_topic

        full_wamp_call = 'iotronic.' + node.uuid + "." + wamp_rpc_call

        return self.wamp_agent_client.call(ctx, full_topic,
                                           wamp_rpc_call=full_wamp_call,
                                           data=wamp_rpc_args)

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
        new_plugin.create()
        return serializer.serialize_entity(ctx, new_plugin)
