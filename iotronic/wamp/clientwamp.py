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

from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationRunner
from autobahn.twisted.wamp import ApplicationSession
import multiprocessing
from twisted.internet.defer import inlineCallbacks


msg_queue = None


class Publisher(ApplicationSession):

    def onJoin(self, details):
        print("Publisher session ready")


class Subscriber(ApplicationSession):

    @inlineCallbacks
    def onJoin(self, details):
        print("Subscriber session ready")
        self.topic_reader = self.config.extra['topic']

        def manage_msg(*args):
            print (args)

        try:
            yield self.subscribe(manage_msg, self.topic_reader)
            print("subscribed to topic")
        except Exception as e:
            print("could not subscribe to topic: {0}".format(e))

        global msg_queue
        while True:
            if not msg_queue.empty():
                msg = msg_queue.get()
                self.publish(msg['topic'], msg['message'])
            yield sleep(0.01)


class PublisherClient(object):

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
        self.runner.run(Publisher, start_reactor=False)


class SubscriberClient(object):

    def __init__(self, ip, port, realm, topic):
        self.ip = unicode(ip)
        self.port = unicode(port)
        self.realm = unicode(realm)
        self.topic = unicode(topic)
        self._url = "ws://" + self.ip + ":" + self.port + "/ws"
        self.runner = ApplicationRunner(
            url=unicode(self._url),
            realm=self.realm,
            # debug=True, debug_wamp=True,
            # debug_app=True
            )

    def start(self):
        # Pass start_reactor=False to all runner.run() calls
        self.runner.run(Subscriber, start_reactor=False)


class ClientWamp(object):

    def __init__(self, ip, port, realm, topic='board.connection'):
        server = SubscriberClient(ip, port, realm, topic)
        sendMessage = PublisherClient(ip, port, realm)
        server.start()
        sendMessage.start()

        from twisted.internet import reactor
        global msg_queue
        msg_queue = multiprocessing.Queue()
        multi = multiprocessing.Process(target=reactor.run, args=())
        multi.start()

    def send(self, topic, msg):
        full_msg = {'topic': unicode(topic), 'message': unicode(msg)}
        msg_queue.put(full_msg)
