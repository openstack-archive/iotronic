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
import asyncio
import subprocess
import time
import txaio

from iotronic.common import exception
from iotronic.common.i18n import _
from iotronic.common.i18n import _LI
from iotronic.common.i18n import _LW
from iotronic.db import api as dbapi
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_messaging.rpc import dispatcher

import importlib
from threading import Thread

import ssl

import os
import signal

from autobahn.asyncio.component import Component

LOG = logging.getLogger(__name__)

service_opts = [
    cfg.StrOpt('notification_level',
               choices=[('debug', _('"debug" level')),
                        ('info', _('"info" level')),
                        ('warning', _('"warning" level')),
                        ('error', _('"error" level')),
                        ('critical', _('"critical" level'))],
               help=_('Specifies the minimum level for which to send '
                      'notifications. If not set, no notifications will '
                      'be sent. The default is for this option to be unset.')),
]

wamp_opts = [
    cfg.StrOpt('wamp_transport_url',
               default='ws://localhost:8181/',
               help=('URL of wamp broker')),
    cfg.StrOpt('wamp_realm',
               default='s4t',
               help=('realm broker')),
    cfg.BoolOpt('register_agent',
                default=False,
                help=('Flag for marking this agent as a registration agent')),
    cfg.BoolOpt('skip_cert_verify',
                default=False,
                help=(
                    'Flag for skipping the verification of the server cert '
                    '(for the auto-signed ones)')),
    cfg.IntOpt('autoPingInterval',
               default=2,
               help=('autoPingInterval parameter for wamp')),
    cfg.IntOpt('autoPingTimeout',
               default=2,
               help=('autoPingInterval parameter for wamp')),

]

proxy_opts = [
    cfg.StrOpt('proxy',
               choices=[('nginx', _('nginx proxy')), ],
               help=_('Proxy for webservices')),
]

CONF = cfg.CONF
cfg.CONF.register_opts(service_opts)
cfg.CONF.register_opts(proxy_opts)
CONF.register_opts(wamp_opts, 'wamp')

txaio.start_logging(level="info")

wamp_session_caller = None
AGENT_HOST = None
LOOP = None
connected = False


async def wamp_request(kwarg):
    LOG.debug("calling: " + kwarg['wamp_rpc_call'])
    d = await wamp_session_caller.call(kwarg['wamp_rpc_call'], *kwarg['data'])
    return d


# OSLO ENDPOINT
class WampEndpoint(object):

    def s4t_invoke_wamp(self, ctx, **kwarg):
        LOG.debug("CONDUCTOR sent me: " + kwarg['wamp_rpc_call'])

        r = asyncio.run_coroutine_threadsafe(wamp_request(kwarg), LOOP)

        return r.result()


class AgentEndpoint(object):

    # used for testing
    def echo(self, ctx, text):
        LOG.debug("ECHO of " + text)
        return text

    def create_tap_interface(self, ctx, port_uuid, tcp_port):
        time.sleep(12)
        LOG.debug('Creating tap interface on the wamp agent host')
        p = subprocess.Popen('socat -d -d TCP:localhost:' + tcp_port +
                             ',reuseaddr,forever,interval=10 TUN,tun-type=tap,'
                             'tun-name=tap' + port_uuid[0:14] +
                             ',up ', shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        return 1


class RPCServer(Thread):
    def __init__(self):
        # AMQP CONFIG

        proxy = importlib.import_module("iotronic.wamp.proxies." + CONF.proxy)

        endpoints = [
            WampEndpoint(),
            AgentEndpoint(),
            proxy.ProxyManager('iot.felooca.eu')
        ]

        Thread.__init__(self)
        transport = oslo_messaging.get_transport(CONF)

        target = oslo_messaging.Target(topic='s4t',
                                       server=AGENT_HOST)

        access_policy = dispatcher.DefaultRPCAccessPolicy
        self.server = oslo_messaging.get_rpc_server(
            transport, target,
            endpoints, executor='threading',
            access_policy=access_policy)

    def run(self):
        LOG.info("Starting AMQP server... ")
        self.server.start()

    def stop(self):
        LOG.info("Stopping AMQP server... ")
        self.server.stop()
        LOG.info("AMQP server stopped. ")


class WampManager(object):
    def __init__(self):

        LOG.debug("wamp url: %s wamp realm: %s",
                  CONF.wamp.wamp_transport_url, CONF.wamp.wamp_realm)

        self.loop = asyncio.get_event_loop()
        global LOOP
        LOOP = self.loop

        wamp_transport = CONF.wamp.wamp_transport_url
        wurl_list = wamp_transport.split(':')
        is_wss = False
        if wurl_list[0] == "wss":
            is_wss = True
        whost = wurl_list[1].replace('/', '')
        wport = int(wurl_list[2].replace('/', ''))

        if is_wss and CONF.wamp.skip_cert_verify:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            wamp_transport = [
                {
                    "url": CONF.wamp.wamp_transport_url,
                    "endpoint": {
                        "type": "tcp",
                        "host": whost,
                        "port": wport,
                        "tls": ctx
                    },
                },
            ]

        comp = Component(
            transports=wamp_transport,
            realm=CONF.wamp.wamp_realm
        )

        self.comp = comp

        @comp.on_join
        async def onJoin(session, details):

            global connected
            connected = True

            global wamp_session_caller, AGENT_HOST
            wamp_session_caller = session

            import iotronic.wamp.functions as fun

            session.subscribe(fun.board_on_leave,
                              'wamp.session.on_leave')
            session.subscribe(fun.board_on_join,
                              'wamp.session.on_join')

            try:
                if CONF.wamp.register_agent:
                    session.register(fun.registration,
                                     u'stack4things.register')
                    LOG.info("I have been set as registration agent")
                session.register(fun.connection,
                                 AGENT_HOST + u'.stack4things.connection')
                session.register(fun.echo,
                                 AGENT_HOST + u'.stack4things.echo')
                session.register(fun.alive,
                                 AGENT_HOST + u'.stack4things.alive')
                session.register(fun.wamp_alive,
                                 AGENT_HOST + u'.stack4things.wamp_alive')
                LOG.debug("procedure registered")

            except Exception as e:
                LOG.error("could not register procedure: {0}".format(e))

            LOG.info("WAMP session ready.")

            session_l = await session.call(u'wamp.session.list')
            session_l.remove(details.session)
            fun.update_sessions(session_l)

        @comp.on_leave
        async def onLeave(session, details):
            LOG.warning('WAMP Session Left: ' + str(details))

        @comp.on_disconnect
        async def onDisconnect(session, was_clean):
            LOG.warning('WAMP Transport Left: ' + str(was_clean))

            global connected
            connected = False
            if not connected:
                comp.start(self.loop)

    def start(self):
        LOG.info("Starting WAMP server...")
        self.comp.start(self.loop)
        self.loop.run_forever()

    def stop(self):
        LOG.info("Stopping WAMP server...")

        # Canceling pending tasks and stopping the loop
        asyncio.gather(*asyncio.Task.all_tasks()).cancel()
        # Stopping the loop
        self.loop.stop()
        LOG.info("WAMP server stopped.")


class WampAgent(object):
    def __init__(self, host):

        signal.signal(signal.SIGINT, self.stop_handler)

        logging.register_options(CONF)

        CONF(project='iotronic')
        logging.setup(CONF, "iotronic-wamp-agent")

        if CONF.debug:
            txaio.start_logging(level="debug")

        # to be removed asap
        self.host = host
        self.dbapi = dbapi.get_instance()

        try:
            wpa = self.dbapi.register_wampagent(
                {'hostname': self.host, 'wsurl': CONF.wamp.wamp_transport_url})

        except exception.WampAgentAlreadyRegistered:
            LOG.warn(_LW("A wampagent with hostname %(hostname)s "
                         "was previously registered. Updating registration"),
                     {'hostname': self.host})

        wpa = self.dbapi.register_wampagent(
            {'hostname': self.host, 'wsurl': CONF.wamp.wamp_transport_url},
            update_existing=True)
        self.wampagent = wpa
        self.wampagent.ragent = CONF.wamp.register_agent
        self.wampagent.save()

        global AGENT_HOST
        AGENT_HOST = self.host

        self.r = RPCServer()
        self.w = WampManager()

        self.r.start()
        self.w.start()

    def del_host(self, deregister=True):
        if deregister:
            try:
                self.dbapi.unregister_wampagent(self.host)
                LOG.info(_LI('Successfully stopped wampagent with hostname '
                             '%(hostname)s.'),
                         {'hostname': self.host})
            except exception.WampAgentNotFound:
                pass
        else:
            LOG.info(_LI('Not deregistering wampagent with hostname '
                         '%(hostname)s.'),
                     {'hostname': self.host})

    def stop_handler(self, signum, frame):
        self.w.stop()
        self.r.stop()
        self.del_host()
        os._exit(0)
