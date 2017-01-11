# Copyright 2011 OpenStack LLC.
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

from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, defer


from twisted.internet.protocol import ReconnectingClientFactory
from autobahn.twisted import wamp, websocket
from autobahn.wamp import types


import threading
from threading import Thread

import oslo_messaging

from oslo_log import log as logging
from oslo_config import cfg

LOG = logging.getLogger(__name__)

wamp_opts = [
    cfg.StrOpt('wamp_transport_url',
            default='ws://localhost:8181/',
            help=('URL of wamp broker')),
    cfg.StrOpt('wamp_realm',
            default='s4t',
            help=('realm broker')),
]
    
CONF = cfg.CONF
CONF.register_opts(wamp_opts, 'wamp')

shared_result={}
wamp_session_caller=None

def wamp_request(e, kwarg,session):
    
    id=threading.current_thread().ident
    shared_result[id]={}
    shared_result[id]['result']=None
  
    def success(d):
      shared_result[id]['result']=d
      LOG.debug( "DEVICE sent: %s", str(d))
      e.set()
      return shared_result[id]['result']
      
      
    def fail(failure):
      shared_result[id]['result']=failure
      LOG.error( "WAMP FAILURE: %s", str(failure))
      e.set()
      return shared_result[id]['result']
    
    LOG.debug("Calling %s...",kwarg['wamp_rpc_call'])
    d = session.wamp_session.call(wamp_session_caller, kwarg['wamp_rpc_call'],*kwarg['data'])
    d.addCallback(success)	      
    d.addErrback(fail)


# OSLO ENDPOINT
class WampEndpoint(object):
    
    def __init__(self,wamp_session,agent_uuid):
        self.wamp_session=wamp_session
        setattr(self, agent_uuid+'.s4t_invoke_wamp', self.s4t_invoke_wamp)

    def s4t_invoke_wamp(self, ctx, **kwarg):
        e = threading.Event()
	LOG.debug( "CONDUCTOR sent me:",kwarg)

	th = threading.Thread(target=wamp_request,args=(e, kwarg,self))
	th.start()
        
        e.wait()
	LOG.debug("result received from wamp call: %s", str(shared_result[th.ident]['result']))
	
	result=shared_result[th.ident]['result']
	del shared_result[th.ident]['result']
	return result
    
    


class WampFrontend(wamp.ApplicationSession):
    

    
    def onJoin(self, details):
        global wamp_session_caller
        wamp_session_caller=self
        import iotronic.wamp.registerd_functions as fun
        
        self.subscribe(fun.board_on_leave, 'wamp.session.on_leave')
        self.subscribe(fun.board_on_join, 'wamp.session.on_join')

        try:
            self.register(fun.register_board, u'register_board')
            LOG.info("procedure registered")
        except Exception as e:
            LOG.error("could not register procedure: {0}".format(e))
        
        
	LOG.info("WAMP session ready.")


    def onDisconnect(self):
	LOG.info("disconnected")


class WampClientFactory(websocket.WampWebSocketClientFactory, ReconnectingClientFactory):
    maxDelay = 30

    def clientConnectionFailed(self, connector, reason):
        #print "reason:", reason
        LOG.warning("Wamp Connection Failed.")
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        #print "reason:", reason
        LOG.warning("Wamp Connection Lost.")
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

class RPCServer(Thread):
    def __init__(self,agent_uuid):
        
        # AMQP CONFIG
        endpoints = [
            WampEndpoint(WampFrontend,agent_uuid),
        ]  
        
        Thread.__init__(self)
        transport = oslo_messaging.get_transport(CONF)
        target = oslo_messaging.Target(topic=agent_uuid+'.s4t_invoke_wamp', server='server1')     

        self.server = oslo_messaging.get_rpc_server(transport, target, endpoints, executor='threading')
    
    def run(self):
        
        try:
            LOG.info("Starting AMQP server... ")
            self.server.start()
        except KeyboardInterrupt:
            
            LOG.info("Stopping AMQP server... ")
            self.server.stop()
            LOG.info("AMQP server stopped. ")
        
            
class WampManager(object):
    def __init__(self):
      component_config = types.ComponentConfig(realm = unicode(CONF.wamp.wamp_realm))
      session_factory = wamp.ApplicationSessionFactory(config = component_config)
      session_factory.session = WampFrontend
      transport_factory = WampClientFactory(session_factory, url=CONF.wamp.wamp_transport_url)
      
      LOG.debug("wamp url: %s wamp realm: %s", CONF.wamp.wamp_transport_url, CONF.wamp.wamp_realm)
      websocket.connectWS(transport_factory) 
    
    def start(self):
        LOG.info("Starting WAMP server...")
        reactor.run()
        
    def stop(self):        
        LOG.info("Stopping WAMP-agent server...")
        reactor.stop()
        LOG.info("WAMP server stopped.")

class WampAgent(object):
    def __init__(self):
        logging.register_options(CONF)
        CONF(project='iotronic')
        logging.setup(CONF, "iotronic-wamp-agent")
        
        agent_uuid='agent'
        
        r=RPCServer(agent_uuid)
        w=WampManager()

        try:
            r.start()
            w.start()
        except KeyboardInterrupt:
            w.stop()
            r.stop()
            exit()
