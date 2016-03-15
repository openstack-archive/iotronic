# coding=utf-8
#
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

from oslo_utils import strutils
from oslo_utils import uuidutils

from iotronic.common import exception
from iotronic.db import api as dbapi
from iotronic.objects import base
from iotronic.objects import utils as obj_utils


class SessionWP(base.IotronicObject):
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'node_uuid': obj_utils.str_or_none,
        'session_id': obj_utils.str_or_none,
        'node_id': obj_utils.int_or_none,
        'valid': bool,
    }

    @staticmethod
    def _from_db_object(session, db_session):
        """Converts a database entity to a formal object."""
        for field in session.fields:
            session[field] = db_session[field]

        session.obj_reset_changes()
        return session

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [
            SessionWP._from_db_object(
                cls(context),
                obj) for obj in db_objects]

    @base.remotable_classmethod
    def get(cls, context, session_id):
        """Find a session based on its id or uuid and return a SessionWP object.

        :param session_id: the id *or* uuid of a session.
        :returns: a :class:`SessionWP` object.
        """
        if strutils.is_int_like(session_id):
            return cls.get_by_id(context, session_id)
        elif uuidutils.is_uuid_like(session_id):
            return cls.get_by_uuid(context, session_id)
        else:
            raise exception.InvalidIdentity(identity=session_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, ses_id):
        """Find a session based on its integer id and return a SessionWP object.

        :param ses_id: the id of a session.
        :returns: a :class:`SessionWP` object.
        """
        db_session = cls.dbapi.get_session_by_id(ses_id)
        session = SessionWP._from_db_object(cls(context), db_session)
        return session

    @base.remotable_classmethod
    def get_by_session_id(cls, context, session_id):
        """Find a session based on its integer id and return a SessionWP object.

        :param session_id: the id of a session.
        :returns: a :class:`SessionWP` object.
        """
        db_session = cls.dbapi.get_session_by_session_id(session_id)
        session = SessionWP._from_db_object(cls(context), db_session)
        return session

    @base.remotable_classmethod
    def get_session_by_node_uuid(cls, node_uuid, valid=True, context=None):
        """Find a session based on uuid and return a :class:`SessionWP` object.

        :param node_uuid: the uuid of a node.
        :param context: Security context
        :returns: a :class:`SessionWP` object.
        """
        db_session = cls.dbapi.get_session_by_node_uuid(node_uuid, valid)
        session = SessionWP._from_db_object(cls(context), db_session)
        return session

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of SessionWP objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`SessionWP` object.

        """
        db_sessions = cls.dbapi.get_session_list(limit=limit,
                                                 marker=marker,
                                                 sort_key=sort_key,
                                                 sort_dir=sort_dir)
        return SessionWP._from_db_object_list(db_sessions, cls, context)

    '''
    @base.remotable_classmethod
    def list_by_node_id(cls, context, node_id, limit=None, marker=None,
                        sort_key=None, sort_dir=None):
        """Return a list of SessionWP objects associated with a given node ID.

        :param context: Security context.
        :param node_id: the ID of the node.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`SessionWP` object.

        """
        db_sessions = cls.dbapi.get_sessions_by_node_id(node_id, limit=limit,
                                                  marker=marker,
                                                  sort_key=sort_key,
                                                  sort_dir=sort_dir)
        return SessionWP._from_db_object_list(db_sessions, cls, context)
    '''

    @base.remotable
    def create(self, context=None):
        """Create a SessionWP record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: SessionWP(context)

        """
        values = self.obj_get_changes()
        db_session = self.dbapi.create_session(values)
        self._from_db_object(self, db_session)

    @base.remotable
    def destroy(self, context=None):
        """Delete the SessionWP from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: SessionWP(context)
        """
        self.dbapi.destroy_session(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this SessionWP.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: SessionWP(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_session(self.id, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this SessionWP.

        Loads a session with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded session column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: SessionWP(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]
