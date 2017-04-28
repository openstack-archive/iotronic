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

from autobahn.twisted import wamp
from autobahn.twisted import websocket
from autobahn.wamp import types
from twisted.internet.defer import inlineCallbacks

from iotronic.common import exception
from iotronic.common.i18n import _LI
from iotronic.common.i18n import _LW
from iotronic.db import api as dbapi
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_messaging.rpc import dispatcher
import threading
from threading import Thread
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import reactor

import os
import signal

LOG = logging.getLogger(__name__)

wamp_opts = [
    cfg.StrOpt('wamp_transport_url',
               default='ws://localhost:8181/',
               help=('URL of wamp broker')),
    cfg.StrOpt('wamp_realm',
               default='s4t',
               help=('realm broker')),
    cfg.BoolOpt('register_agent',
                default=False,
                help=('Flag for se a registration agent')),
    cfg.IntOpt('autoPingInterval',
               default=2,
               help=('autoPingInterval parameter for wamp')),
    cfg.IntOpt('autoPingTimeout',
               default=2,
               help=('autoPingInterval parameter for wamp')),

]

CONF = cfg.CONF
CONF.register_opts(wamp_opts, 'wamp')

shared_result = {}
wamp_session_caller = None
AGENT_HOST = None


def wamp_request(e, kwarg, session):
    id = threading.current_thread().ident
    shared_result[id] = {}
    shared_result[id]['result'] = None

    def success(d):
        shared_result[id]['result'] = d
        LOG.debug("DEVICE sent: %s", str(d))
        e.set()
        return shared_result[id]['result']

    def fail(failure):
        shared_result[id]['result'] = failure
        LOG.error("WAMP FAILURE: %s", str(failure))
        e.set()
        return shared_result[id]['result']

    LOG.debug("Calling %s...", kwarg['wamp_rpc_call'])
    d = session.wamp_session.call(wamp_session_caller,
                                  kwarg['wamp_rpc_call'], *kwarg['data'])
    d.addCallback(success)
    d.addErrback(fail)


# OSLO ENDPOINT
class WampEndpoint(object):
    def __init__(self, wamp_session, agent_uuid):
        self.wamp_session = wamp_session
        setattr(self, agent_uuid + '.s4t_invoke_wamp', self.s4t_invoke_wamp)

    def s4t_invoke_wamp(self, ctx, **kwarg):
        e = threading.Event()
        LOG.debug("CONDUCTOR sent me:", kwarg)

        th = threading.Thread(target=wamp_request, args=(e, kwarg, self))
        th.start()

        e.wait()
        LOG.debug("result received from wamp call: %s",
                  str(shared_result[th.ident]['result']))

        result = shared_result[th.ident]['result']
        del shared_result[th.ident]['result']
        return result


class WampFrontend(wamp.ApplicationSession):
    @inlineCallbacks
    def onJoin(self, details):
        global wamp_session_caller, AGENT_HOST
        wamp_session_caller = self

        import iotronic.wamp.functions as fun

        self.subscribe(fun.board_on_leave, 'wamp.session.on_leave')
        self.subscribe(fun.board_on_join, 'wamp.session.on_join')

        try:
            if CONF.wamp.register_agent:
                self.register(fun.registration, u'stack4things.register')
                LOG.info("I have been set as registration agent")
            self.register(fun.connection,
                          AGENT_HOST + u'.stack4things.connection')
            self.register(fun.echo,
                          AGENT_HOST + u'.stack4things.echo')
            LOG.info("procedure registered")
        except Exception as e:
            LOG.error("could not register procedure: {0}".format(e))

        LOG.info("WAMP session ready.")

        session_l = yield self.call(u'wamp.session.list')
        session_l.remove(details.session)
        fun.update_sessions(session_l)

    def onDisconnect(self):
        LOG.info("disconnected")


class WampClientFactory(websocket.WampWebSocketClientFactory,
                        ReconnectingClientFactory):
    maxDelay = 30

    def clientConnectionFailed(self, connector, reason):
        # print "reason:", reason
        LOG.warning("Wamp Connection Failed.")
        ReconnectingClientFactory.clientConnectionFailed(self,
                                                         connector, reason)

    def clientConnectionLost(self, connector, reason):
        # print "reason:", reason
        LOG.warning("Wamp Connection Lost.")
        ReconnectingClientFactory.clientConnectionLost(self,
                                                       connector, reason)


class RPCServer(Thread):
    def __init__(self):
        global AGENT_HOST

        # AMQP CONFIG
        endpoints = [
            WampEndpoint(WampFrontend, AGENT_HOST),
        ]

        Thread.__init__(self)
        transport = oslo_messaging.get_transport(CONF)
        target = oslo_messaging.Target(topic=AGENT_HOST + '.s4t_invoke_wamp',
                                       server='server1')

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
        component_config = types.ComponentConfig(
            realm=unicode(CONF.wamp.wamp_realm))
        session_factory = wamp.ApplicationSessionFactory(
            config=component_config)
        session_factory.session = WampFrontend
        transport_factory = WampClientFactory(session_factory,
                                              url=CONF.wamp.wamp_transport_url)

        transport_factory.autoPingInterval = CONF.wamp.autoPingInterval
        transport_factory.autoPingTimeout = CONF.wamp.autoPingTimeout

        LOG.debug("wamp url: %s wamp realm: %s",
                  CONF.wamp.wamp_transport_url, CONF.wamp.wamp_realm)
        websocket.connectWS(transport_factory)

    def start(self):
        LOG.info("Starting WAMP server...")
        reactor.run()

    def stop(self):
        LOG.info("Stopping WAMP-agent server...")
        reactor.stop()
        LOG.info("WAMP server stopped.")


class WampAgent(object):
    def __init__(self, host):

        signal.signal(signal.SIGINT, self.stop_handler)

        logging.register_options(CONF)
        CONF(project='iotronic')
        logging.setup(CONF, "iotronic-wamp-agent")

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
