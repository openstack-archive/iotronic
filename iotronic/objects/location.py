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


class Location(base.IotronicObject):
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'board_id': obj_utils.int_or_none,
        'longitude': obj_utils.str_or_none,
        'latitude': obj_utils.str_or_none,
        'altitude': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(location, db_location):
        """Converts a database entity to a formal object."""
        for field in location.fields:
            location[field] = db_location[field]

        location.obj_reset_changes()
        return location

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [
            Location._from_db_object(
                cls(context),
                obj) for obj in db_objects]

    # @base.remotable_classmethod
    # def get(cls, context, location_id):
    #     """Find a location based on its id or uuid and return a Location object.
    #
    #     :param location_id: the id *or* uuid of a location.
    #     :returns: a :class:`Location` object.
    #     """
    #     if strutils.is_int_like(location_id):
    #         return cls.get_by_id(context, location_id)
    #     elif uuidutils.is_uuid_like(location_id):
    #         return cls.get_by_uuid(context, location_id)
    #     else:
    #         raise exception.InvalidIdentity(identity=location_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, location_id):
        """Find a location based on its integer id and return a Location object.

        :param location_id: the id of a location.
        :returns: a :class:`Location` object.
        """
        db_location = cls.dbapi.get_location_by_id(location_id)
        location = Location._from_db_object(cls(context), db_location)
        return location

    # @base.remotable_classmethod
    # def get_by_uuid(cls, context, uuid):
    #     """Find a location based on uuid and return a :class:`Location` object.
    #
    #     :param uuid: the uuid of a location.
    #     :param context: Security context
    #     :returns: a :class:`Location` object.
    #     """
    #     db_location = cls.dbapi.get_location_by_uuid(uuid)
    #     location = Location._from_db_object(cls(context), db_location)
    #     return location

    # @base.remotable_classmethod
    # def list(cls, context, limit=None, marker=None,
    #          sort_key=None, sort_dir=None):
    #     """Return a list of Location objects.
    #
    #     :param context: Security context.
    #     :param limit: maximum number of resources to return in a single result.
    #     :param marker: pagination marker for large data sets.
    #     :param sort_key: column to sort results by.
    #     :param sort_dir: direction to sort. "asc" or "desc".
    #     :returns: a list of :class:`Location` object.
    #
    #     """
    #     db_locations = cls.dbapi.get_location_list(limit=limit,
    #                                                marker=marker,
    #                                                sort_key=sort_key,
    #                                                sort_dir=sort_dir)
    #     return Location._from_db_object_list(db_locations, cls, context)

    @base.remotable_classmethod
    def list_by_board_uuid(cls, context, board_uuid, limit=None, marker=None,
                           sort_key=None, sort_dir=None):
        """Return a list of Location objects associated with a given board ID.

        :param context: Security context.
        :param board_id: the ID of the board.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Location` object.

        """
        board_id = cls.dbapi.get_board_id_by_uuid(board_uuid)[0]
        db_loc = cls.dbapi.get_locations_by_board_id(board_id,
                                                     limit=limit,
                                                     marker=marker,
                                                     sort_key=sort_key,
                                                     sort_dir=sort_dir)
        return Location._from_db_object_list(db_loc, cls, context)

    @base.remotable_classmethod
    def list_by_board_id(cls, context, board_id, limit=None, marker=None,
                         sort_key=None, sort_dir=None):
        """Return a list of Location objects associated with a given board ID.

        :param context: Security context.
        :param board_id: the ID of the board.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Location` object.

        """
        db_loc = cls.dbapi.get_locations_by_board_id(board_id,
                                                     limit=limit,
                                                     marker=marker,
                                                     sort_key=sort_key,
                                                     sort_dir=sort_dir)
        return Location._from_db_object_list(db_loc, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a Location record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Location(context)

        """
        values = self.obj_get_changes()
        db_location = self.dbapi.create_location(values)
        self._from_db_object(self, db_location)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Location from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Location(context)
        """
        self.dbapi.destroy_location(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Location.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Location(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_location(self.uuid, updates)

        self.obj_reset_changes()

    # @base.remotable
    # def refresh(self, context=None):
    #     """Loads updates for this Location.
    #
    #     Loads a location with the same uuid from the database and
    #     checks for updated attributes. Updates are applied from
    #     the loaded location column by column, if there are any updates.
    #
    #     :param context: Security context. NOTE: This should only
    #                     be used internally by the indirection_api.
    #                     Unfortunately, RPC requires context as the first
    #                     argument, even though we don't use it.
    #                     A context should be set when instantiating the
    #                     object, e.g.: Location(context)
    #     """
    #     current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
    #     for field in self.fields:
    #         if (hasattr(
    #                 self, base.get_attrname(field))
    #                 and self[field] != current[field]):
    #             self[field] = current[field]
