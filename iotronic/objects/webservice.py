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


class Webservice(base.IotronicObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'port': int,
        'name': obj_utils.str_or_none,
        'board_uuid': obj_utils.str_or_none,
        'secure': bool,
        'extra': obj_utils.dict_or_none,
    }

    @staticmethod
    def _from_db_object(webservice, db_webservice):
        """Converts a database entity to a formal object."""
        for field in webservice.fields:
            webservice[field] = db_webservice[field]
        webservice.obj_reset_changes()
        return webservice

    @base.remotable_classmethod
    def get(cls, context, webservice_id):
        """Find a webservice based on its id or uuid and return a Board object.

        :param webservice_id: the id *or* uuid of a webservice.
        :returns: a :class:`Board` object.
        """
        if strutils.is_int_like(webservice_id):
            return cls.get_by_id(context, webservice_id)
        elif uuidutils.is_uuid_like(webservice_id):
            return cls.get_by_uuid(context, webservice_id)
        else:
            raise exception.InvalidIdentity(identity=webservice_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, webservice_id):
        """Find a webservice based on its integer id and return a Board object.

        :param webservice_id: the id of a webservice.
        :returns: a :class:`Board` object.
        """
        db_webservice = cls.dbapi.get_webservice_by_id(webservice_id)
        webservice = Webservice._from_db_object(cls(context), db_webservice)
        return webservice

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a webservice based on uuid and return a Board object.

        :param uuid: the uuid of a webservice.
        :returns: a :class:`Board` object.
        """
        db_webservice = cls.dbapi.get_webservice_by_uuid(uuid)
        webservice = Webservice._from_db_object(cls(context), db_webservice)
        return webservice

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a webservice based on name and return a Board object.

        :param name: the logical name of a webservice.
        :returns: a :class:`Board` object.
        """
        db_webservice = cls.dbapi.get_webservice_by_name(name)
        webservice = Webservice._from_db_object(cls(context), db_webservice)
        return webservice

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, sort_key=None,
             sort_dir=None, filters=None):
        """Return a list of Webservice objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: Filters to apply.
        :returns: a list of :class:`Webservice` object.

        """
        db_webservices = cls.dbapi.get_webservice_list(filters=filters,
                                                       limit=limit,
                                                       marker=marker,
                                                       sort_key=sort_key,
                                                       sort_dir=sort_dir)
        return [Webservice._from_db_object(cls(context), obj)
                for obj in db_webservices]

    @base.remotable
    def create(self, context=None):
        """Create a Webservice record in the DB.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        webservice before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Webservice(context)

        """

        values = self.obj_get_changes()
        db_webservice = self.dbapi.create_webservice(values)
        self._from_db_object(self, db_webservice)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Webservice from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Webservice(context)
        """
        self.dbapi.destroy_webservice(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Webservice.

        Column-wise updates will be made based on the result of
        self.what_changed(). If target_power_state is provided,
        it will be checked against the in-database copy of the
        webservice before updates are made.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Webservice(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_webservice(self.uuid, updates)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Webservice(context)
        """
        current = self.__class__.get_by_uuid(self._context, self.uuid)
        for field in self.fields:
            if (hasattr(
                    self, base.get_attrname(field))
                    and self[field] != current[field]):
                self[field] = current[field]
