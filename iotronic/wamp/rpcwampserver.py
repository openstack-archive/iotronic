from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
import multiprocessing
from twisted.internet import reactor
from oslo_log import log
from oslo_config import cfg

LOG = log.getLogger(__name__)

CONF = cfg.CONF
CONF.register_opts(wamp_opts, 'wamp')

wamp_opts = [
    cfg.StrOpt('wamp_ip', default='127.0.0.1', help='URL of wamp broker'),
    cfg.IntOpt('wamp_port', default=8181, help='port wamp broker'),
    cfg.StrOpt('wamp_realm', default='s4t', help='realm broker')
]


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


class RPCWampServer:

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


class RPC_Wamp_Server:

    def __init__(self):
        self.ip = unicode(CONF.wamp.wamp_ip)
        self.port = unicode(CONF.wamp.wamp_port)
        self.realm = unicode(CONF.wamp.wamp_realm)
        server = RPCWampServer(self.ip, self.port, self.realm)
        server.start()
        multi = multiprocessing.Process(target=reactor.run, args=())
        multi.start()
