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

from iotronic.common import rpc
from iotronic.common import states
from iotronic.conductor import rpcapi
from iotronic import objects
from iotronic.wamp import wampmessage as wm
from oslo_config import cfg
from oslo_log import log

LOG = log.getLogger(__name__)

CONF = cfg.CONF
CONF(project='iotronic')

rpc.init(CONF)

topic = 'iotronic.conductor_manager'
c = rpcapi.ConductorAPI(topic)


class cont(object):
    def to_dict(self):
        return {}


ctxt = cont()


def echo(data):
    LOG.info("ECHO: %s" % data)
    return data


def update_sessions(session_list):
    session_list = set(session_list)
    list_from_db = objects.SessionWP.valid_list(ctxt)
    list_db = set([int(elem.session_id) for elem in list_from_db])

    if session_list == list_db:
        LOG.debug('Sessions on the database are updated.')
        return

    old_connected = list_db.difference(session_list)
    for elem in old_connected:
        old_session = objects.SessionWP.get(ctxt, elem)
        old_session.valid = False
        old_session.save()
        LOG.debug('%s has been put offline.', old_session.board_uuid)
    if old_connected:
        LOG.warning('Some boards have been updated: status offline')

    keep_connected = list_db.intersection(session_list)
    for elem in keep_connected:
        for x in list_from_db:
            if x.session_id == str(elem):
                LOG.debug('%s need to be restored.', x.board_uuid)
                break
    if keep_connected:
        LOG.warning('Some boards need to be restored.')


def board_on_leave(session_id):
    LOG.debug('A board with %s disconnectd', session_id)

    try:
        old_session = objects.SessionWP.get(ctxt, session_id)
        old_session.valid = False
        old_session.save()
        LOG.debug('Session %s deleted', session_id)
    except Exception:
        LOG.debug('session %s not found', session_id)

    board = objects.Board.get_by_uuid(ctxt, old_session.board_uuid)
    board.status = states.OFFLINE
    board.save()
    LOG.debug('Board %s is now  %s', board.uuid, states.OFFLINE)


def connection(uuid, session):
    LOG.debug('Received registration from %s with session %s',
              uuid, session)
    try:
        board = objects.Board.get_by_uuid(ctxt, uuid)
    except Exception as exc:
        msg = exc.message % {'board': uuid}
        LOG.error(msg)
        return wm.WampError(msg).serialize()

    try:
        old_ses = objects.SessionWP(ctxt)
        old_ses = old_ses.get_session_by_board_uuid(ctxt, board.uuid,
                                                    valid=True)
        old_ses.valid = False
        old_ses.save()

    except Exception:
        LOG.debug('valid session for %s not found', board.uuid)

    session_data = {'board_id': board.id,
                    'board_uuid': board.uuid,
                    'session_id': session}
    session = objects.SessionWP(ctxt, **session_data)
    session.create()
    board.status = states.ONLINE
    board.save()
    LOG.info('Board %s (%s) is now  %s', board.uuid,
             board.name, states.ONLINE)
    return wm.WampSuccess('').serialize()


def registration(code, session):
    return c.registration(ctxt, code, session)


def board_on_join(session_id):
    LOG.debug('A board with %s joined', session_id['session'])
