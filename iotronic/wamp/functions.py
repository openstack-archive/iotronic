from iotronic import objects
from oslo_utils import uuidutils
import pecan
from oslo_log import log
from iotronic.common import exception

LOG = log.getLogger(__name__)


def leave_function(session_id):
    LOG.debug('Node with %s disconnectd', session_id)
    try:
        old_session = objects.SessionWP({}).get_by_session_id({}, session_id)
        old_session.valid = False
        old_session.save()
        LOG.debug('Session %s deleted', session_id)
    except:
        LOG.debug('Error in deleting session %s', session_id)


def test():
    LOG.debug('hello')
    return u'hello!'


def registration(code_node, session_num):
    LOG.debug(
        'Receved registration from %s with session %s',
        code_node,
        session_num)
    response = ''
    try:
        node = objects.Node.get_by_code({}, code_node)
    except:
        response = exception.NodeNotFound(node=code_node)
    try:
        old_session = objects.SessionWP(
            {}).get_session_by_node_uuid(
            node.uuid, valid=True)
        old_session.valid = False
        old_session.save()
    except:
        LOG.debug('valid session for %s Not found', node.uuid)

    session = objects.SessionWP({})
    session.node_id = node.id
    session.node_uuid = node.uuid
    session.session_id = session_num
    session.create()
    session.save()

    return unicode(response)
