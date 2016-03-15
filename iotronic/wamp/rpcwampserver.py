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

from autobahn.twisted.wamp import ApplicationRunner
from autobahn.twisted.wamp import ApplicationSession
import multiprocessing
from oslo_config import cfg
from oslo_log import log
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor


LOG = log.getLogger(__name__)

wamp_opts = [
    cfg.StrOpt('wamp_ip', default='127.0.0.1', help='URL of wamp broker'),
    cfg.IntOpt('wamp_port', default=8181, help='port wamp broker'),
    cfg.StrOpt('wamp_realm', default='s4t', help='realm broker')
]

CONF = cfg.CONF
CONF.register_opts(wamp_opts, 'wamp')


class RPCWampManager(ApplicationSession):

    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)
        LOG.info("RPC wamp manager created")

    '''
    #unused methods
    def onConnect(self):
        print("transport connected")
        self.join(self.config.realm)

    def onChallenge(self, challenge):
        print("authentication challenge received")

    def onLeave(self, details):
        print("session left")
        import os, signal
        os.kill(multi.pid, signal.SIGKILL)

    def onDisconnect(self):
        print("transport disconnected")
    '''

    @inlineCallbacks
    def onJoin(self, details):
        LOG.info('RPC Wamp Session ready')
        import iotronic.wamp.functions as fun
        self.subscribe(fun.leave_function, 'wamp.session.on_leave')

        try:
            yield self.register(fun.test, u'stack4things.test')
            yield self.register(fun.registration, u'stack4things.register')

            LOG.info("Procedures registered")
        except Exception as e:
            print("could not register procedure: {0}".format(e))


class RPCWampServer(object):

    def __init__(self, ip, port, realm):
        self.ip = unicode(ip)
        self.port = unicode(port)
        self.realm = unicode(realm)
        self._url = "ws://" + self.ip + ":" + self.port + "/ws"
        self.runner = ApplicationRunner(
            url=unicode(self._url),
            realm=self.realm,
            # debug=True, debug_wamp=True,
            # debug_app=True
            )

    def start(self):
        # Pass start_reactor=False to all runner.run() calls
        self.runner.run(RPCWampManager, start_reactor=False)


class RPC_Wamp_Server(object):

    def __init__(self):
        self.ip = unicode(CONF.wamp.wamp_ip)
        self.port = unicode(CONF.wamp.wamp_port)
        self.realm = unicode(CONF.wamp.wamp_realm)
        server = RPCWampServer(self.ip, self.port, self.realm)
        server.start()
        multi = multiprocessing.Process(target=reactor.run, args=())
        multi.start()
