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
from iotronic.db import api as db_api
from iotronic.objects import base
from iotronic.objects import utils as obj_utils


class EnabledWebservice(base.IotronicObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': int,
        'board_uuid': obj_utils.str_or_none,
        'http_port': int,
        'https_port': int,
        'dns': obj_utils.str_or_none,
        'zone': obj_utils.str_or_none,
        'extra': obj_utils.dict_or_none,
    }

    @staticmethod
    def _from_db_object(enabled_webservice, db_enabled_webservice):
        """Converts a database entity to a formal object."""
        for field in enabled_webservice.fields:
            enabled_webservice[field] = db_enabled_webservice[field]
        enabled_webservice.obj_reset_changes()
        return enabled_webservice

    @base.remotable_classmethod
    def get(cls, context, enabled_webservice_id):
        """Find a enabled_webservice based on its id or uuid and return a
        Board object.

        :param enabled_webservice_id: the id *or* uuid of a enabled_webservice.
        :returns: a :class:`Board` object.
        """
        if strutils.is_int_like(enabled_webservice_id):
            return cls.get_by_id(context, enabled_webservice_id)
        elif uuidutils.is_uuid_like(enabled_webservice_id):
            return cls.get_by_uuid(context, enabled_webservice_id)
        else:
            raise exception.InvalidIdentity(identity=enabled_webservice_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, enabled_webservice_id):
        """Find a enabled_webservice based on its integer id and return a
        Board object.

        :param enabled_webservice_id: the id of a enabled_webservice.
        :returns: a :class:`Board` object.
        """
        db_enabled_webservice = cls.dbapi.get_enabled_webservice_by_id(
            enabled_webservice_id)
        en_webserv = EnabledWebservice._from_db_object(cls(context),
                                                       db_enabled_webservice)
        return en_webserv

    @base.remotable_classmethod
    def get_by_board_uuid(cls, context, uuid):
        """Find a enabled_webservice based on uuid and return a Board object.

        :param uuid: the uuid of a enabled_webservice.
        :returns: a :class:`Board` object.
        """
        db_enabled_webservice = cls.dbapi.get_enabled_webservice_by_board_uuid(
            uuid)
        en_webserv = EnabledWebservice._from_db_object(cls(context),
                                                       db_enabled_webservice)
        return en_webserv

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, sort_key=None,
             sort_dir=None, filters=None):
        """Return a list of EnabledWebservice objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`EnabledWebservice` object.

        """
        db_enabled_webservices = cls.dbapi.get_enabled_webservice_list(
            filters=filters,
            limit=limit,
            marker=marker,
            sort_key=sort_key,
            sort_dir=sort_dir)
        return [EnabledWebservice._from_db_object(cls(context), obj)
                for obj in db_enabled_webservices]

    @base.remotable
    def create(self, context=None):
        """Create a EnabledWebservice record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        enabled_webservice before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: EnabledWebservice(context)

        """

        values = self.obj_get_changes()
        db_enabled_webservice = self.dbapi.create_enabled_webservice(values)
        self._from_db_object(self, db_enabled_webservice)

    @base.remotable
    def destroy(self, context=None):
        """Delete the EnabledWebservice from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: EnabledWebservice(context)
        """
        self.dbapi.destroy_enabled_webservice(self.id)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this EnabledWebservice.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        enabled_webservice before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: EnabledWebservice(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_enabled_webservice(self.uuid, updates)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: EnabledWebservice(context)
        """
        current = self.__class__.get_by_uuid(self._context, self.uuid)
        for field in self.fields:
            if (hasattr(
                    self, base.get_attrname(field))
                    and self[field] != current[field]):
                self[field] = current[field]
