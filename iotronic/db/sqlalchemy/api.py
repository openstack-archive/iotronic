# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""SQLAlchemy storage backend."""

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound

from iotronic.common import exception
from iotronic.common.i18n import _
from iotronic.common import states
from iotronic.db import api
from iotronic.db.sqlalchemy import models

CONF = cfg.CONF
CONF.import_opt('heartbeat_timeout',
                'iotronic.conductor.manager',
                group='conductor')

_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def get_backend():
    """The backend is this module itself."""
    return Connection()


def model_query(model, *args, **kwargs):
    """Query helper for simpler session usage.

    :param session: if present, the session to use
    """

    session = kwargs.get('session') or get_session()
    query = session.query(model, *args)
    return query


def add_identity_filter(query, value):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if strutils.is_int_like(value):
        return query.filter_by(id=value)
    elif uuidutils.is_uuid_like(value):
        return query.filter_by(uuid=value)
    else:
        raise exception.InvalidIdentity(identity=value)


def _paginate_query(model, limit=None, marker=None, sort_key=None,
                    sort_dir=None, query=None):
    if not query:
        query = model_query(model)
    sort_keys = ['id']
    if sort_key and sort_key not in sort_keys:
        sort_keys.insert(0, sort_key)
    try:
        query = db_utils.paginate_query(query, model, limit, sort_keys,
                                        marker=marker, sort_dir=sort_dir)
    except db_exc.InvalidSortKey:
        raise exception.InvalidParameterValue(
            _('The sort_key value "%(key)s" is an invalid field for sorting')
            % {'key': sort_key})

    return query.all()


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_location_filter_by_board(self, query, value):
        if strutils.is_int_like(value):
            return query.filter_by(board_id=value)
        else:
            query = query.join(models.Board,
                               models.Location.board_id == models.Board.id)
            return query.filter(models.Board.uuid == value)

    def _add_boards_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'project_id' in filters:
            query = query.filter(models.Board.project == filters['project_id'])
        if 'status' in filters:
            query = query.filter(models.Board.status == filters['status'])
        if 'fleet' in filters:
            query = query.filter(models.Board.fleet == filters['fleet'])

        return query

    def _add_plugins_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'owner' in filters:
            if 'with_public' in filters and filters['with_public']:
                query = query.filter(
                    or_(
                        models.Plugin.owner == filters['owner'],
                        models.Plugin.public == 1)
                )
            else:
                query = query.filter(models.Plugin.owner == filters['owner'])

        elif 'public' in filters and filters['public']:
            query = query.filter(models.Plugin.public == 1)

        return query

    def _add_services_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'owner' in filters:
            query = query.filter(models.Plugin.owner == filters['owner'])
        return query

    def _add_enabled_webservices_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'project_id' in filters:
            query = query.join(models.Board,
                               models.EnabledWebservice.board_uuid ==
                               models.Board.uuid)
            query = query.filter(
                models.Board.project == filters['project_id'])

        return query

    def _add_webservices_filters(self, query, filters):
        # if filters is None:
        #    filters = []
        if 'project_id' in filters:
            query = query.join(models.Board,
                               models.Webservice.board_uuid ==
                               models.Board.uuid)
            query = query.filter(
                models.Board.project == filters['project_id'])

        if 'board_uuid' in filters:
            query = query.filter(
                models.Webservice.board_uuid == filters['board_uuid'])

        return query

    def _add_fleets_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'project' in filters:
            query = query.filter(models.Fleet.project == filters['project'])
        return query

    def _add_wampagents_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'online' in filters:
            if filters['online']:
                query = query.filter(models.WampAgent.online == 1)
            else:
                query = query.filter(models.WampAgent.online == 0)

        if 'no_ragent' in filters:
            if filters['no_ragent']:
                query = query.filter(models.WampAgent.ragent == 0)
            else:
                query = query.filter(models.WampAgent.ragent == 1)

        return query

    def _add_ports_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'board_uuid' in filters:
            query = query. \
                filter(models.Port.board_uuid == filters['board_uuid'])

    def _do_update_board(self, board_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Board, session=session)
            query = add_identity_filter(query, board_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.BoardNotFound(board=board_id)

            ref.update(values)
        return ref

    def _do_update_plugin(self, plugin_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Plugin, session=session)
            query = add_identity_filter(query, plugin_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.PluginNotFound(plugin=plugin_id)

            ref.update(values)
        return ref

    def _do_update_injection_plugin(self, injection_plugin_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.InjectionPlugin, session=session)
            query = add_identity_filter(query, injection_plugin_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.InjectionPluginNotFound(
                    injection_plugin=injection_plugin_id)

            ref.update(values)
        return ref

    # BOARD api

    def get_boardinfo_list(self, columns=None, filters=None, limit=None,
                           marker=None, sort_key=None, sort_dir=None):
        # list-ify columns default values because it is bad form
        # to include a mutable list in function definitions.
        if columns is None:
            columns = [models.Board.id]
        else:
            columns = [getattr(models.Board, c) for c in columns]

        query = model_query(*columns, base_model=models.Board)
        query = self._add_boards_filters(query, filters)
        return _paginate_query(models.Board, limit, marker,
                               sort_key, sort_dir, query)

    def get_board_list(self, filters=None, limit=None, marker=None,
                       sort_key=None, sort_dir=None):
        query = model_query(models.Board)
        query = self._add_boards_filters(query, filters)
        return _paginate_query(models.Board, limit, marker,
                               sort_key, sort_dir, query)

    def create_board(self, values):
        # ensure defaults are present for new boards
        if 'uuid' not in values:
            values['uuid'] = uuidutils.generate_uuid()
        if 'status' not in values:
            values['status'] = states.REGISTERED

        board = models.Board()
        board.update(values)
        try:
            board.save()
        except db_exc.DBDuplicateEntry as exc:
            if 'code' in exc.columns:
                raise exception.DuplicateCode(code=values['code'])
            raise exception.BoardAlreadyExists(uuid=values['uuid'])
        return board

    def get_board_by_id(self, board_id):
        query = model_query(models.Board).filter_by(id=board_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BoardNotFound(board=board_id)

    def get_board_id_by_uuid(self, board_uuid):
        query = model_query(models.Board.id).filter_by(uuid=board_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BoardNotFound(board=board_uuid)

    def get_board_by_uuid(self, board_uuid):
        query = model_query(models.Board).filter_by(uuid=board_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BoardNotFound(board=board_uuid)

    def get_board_by_name(self, board_name):
        query = model_query(models.Board).filter_by(name=board_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BoardNotFound(board=board_name)

    def get_board_by_code(self, board_code):
        query = model_query(models.Board).filter_by(code=board_code)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BoardNotFound(board=board_code)

    #    def get_board_by_port_uuid(self, port_uuid):
    #        query = model_query(models.Port).filter_by(uuid=port_uuid)

    def destroy_board(self, board_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Board, session=session)
            query = add_identity_filter(query, board_id)
            try:
                board_ref = query.one()
            except NoResultFound:
                raise exception.BoardNotFound(board=board_id)

            # Get board ID, if an UUID was supplied. The ID is
            # required for deleting all ports, attached to the board.
            if uuidutils.is_uuid_like(board_id):
                board_id = board_ref['id']

            location_query = model_query(models.Location, session=session)
            location_query = self._add_location_filter_by_board(
                location_query, board_id)
            location_query.delete()

            query.delete()

    def update_board(self, board_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Board.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_board(board_id, values)
        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])
            elif 'uuid' in e.columns:
                raise exception.BoardAlreadyExists(uuid=values['uuid'])
            else:
                raise e

    # CONDUCTOR api

    def register_conductor(self, values, update_existing=False):
        session = get_session()
        with session.begin():
            query = (model_query(models.Conductor, session=session)
                     .filter_by(hostname=values['hostname']))
            try:
                ref = query.one()
                if ref.online is True and not update_existing:
                    raise exception.ConductorAlreadyRegistered(
                        conductor=values['hostname'])
            except NoResultFound:
                ref = models.Conductor()
            ref.update(values)
            # always set online and updated_at fields when registering
            # a conductor, especially when updating an existing one
            ref.update({'updated_at': timeutils.utcnow(),
                        'online': True})
            ref.save(session)
        return ref

    def get_conductor(self, hostname):
        try:
            return (model_query(models.Conductor)
                    .filter_by(hostname=hostname, online=True)
                    .one())
        except NoResultFound:
            raise exception.ConductorNotFound(conductor=hostname)

    def unregister_conductor(self, hostname):
        session = get_session()
        with session.begin():
            query = (model_query(models.Conductor, session=session)
                     .filter_by(hostname=hostname, online=True))
            count = query.update({'online': False})
            if count == 0:
                raise exception.ConductorNotFound(conductor=hostname)

    def touch_conductor(self, hostname):
        session = get_session()
        with session.begin():
            query = (model_query(models.Conductor, session=session)
                     .filter_by(hostname=hostname))
            # since we're not changing any other field, manually set updated_at
            # and since we're heartbeating, make sure that online=True
            count = query.update({'updated_at': timeutils.utcnow(),
                                  'online': True})
            if count == 0:
                raise exception.ConductorNotFound(conductor=hostname)

    # LOCATION api

    def create_location(self, values):
        location = models.Location()
        location.update(values)
        location.save()
        return location

    def update_location(self, location_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        session = get_session()
        try:
            with session.begin():
                query = model_query(models.Location, session=session)
                query = add_identity_filter(query, location_id)
                ref = query.one()
                ref.update(values)
        except NoResultFound:
            raise exception.LocationNotFound(location=location_id)
        return ref

    def destroy_location(self, location_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Location, session=session)
            query = add_identity_filter(query, location_id)
            count = query.delete()
            if count == 0:
                raise exception.LocationNotFound(location=location_id)

    def get_locations_by_board_id(self, board_id, limit=None, marker=None,
                                  sort_key=None, sort_dir=None):
        query = model_query(models.Location)
        query = query.filter_by(board_id=board_id)
        return _paginate_query(models.Location, limit, marker,
                               sort_key, sort_dir, query)

    # SESSION api

    def create_session(self, values):
        session = models.SessionWP()
        session.update(values)
        session.save()
        return session

    def update_session(self, ses_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        session = get_session()
        try:
            with session.begin():
                query = model_query(models.SessionWP, session=session)
                query = add_identity_filter(query, ses_id)
                ref = query.one()
                ref.update(values)
        except NoResultFound:
            raise exception.SessionWPNotFound(ses=ses_id)
        return ref

    def get_session_by_board_uuid(self, board_uuid, valid):
        query = model_query(
            models.SessionWP).filter_by(
            board_uuid=board_uuid).filter_by(
            valid=valid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BoardNotConnected(board=board_uuid)

    def get_session_by_id(self, session_id):
        query = model_query(models.SessionWP).filter_by(session_id=session_id)
        try:
            return query.one()
        except NoResultFound:
            return None

    def get_valid_wpsessions_list(self):
        query = model_query(models.SessionWP).filter_by(valid=1)
        return query.all()

    # WAMPAGENT api

    def register_wampagent(self, values, update_existing=False):
        session = get_session()
        with session.begin():
            query = (model_query(models.WampAgent, session=session)
                     .filter_by(hostname=values['hostname']))
            try:
                ref = query.one()
                if ref.online is True and not update_existing:
                    raise exception.WampAgentAlreadyRegistered(
                        wampagent=values['hostname'])
            except NoResultFound:
                ref = models.WampAgent()
            ref.update(values)
            # always set online and updated_at fields when registering
            # a wampagent, especially when updating an existing one
            ref.update({'updated_at': timeutils.utcnow(),
                        'online': True})
            ref.save(session)
        return ref

    def get_wampagent(self, hostname):
        try:
            return (model_query(models.WampAgent)
                    .filter_by(hostname=hostname, online=True)
                    .one())
        except NoResultFound:
            raise exception.WampAgentNotFound(wampagent=hostname)

    def get_registration_wampagent(self):
        try:
            return (model_query(models.WampAgent)
                    .filter_by(ragent=True, online=True)
                    .one())
        except NoResultFound:
            raise exception.WampRegistrationAgentNotFound()

    def unregister_wampagent(self, hostname):
        session = get_session()
        with session.begin():
            query = (model_query(models.WampAgent, session=session)
                     .filter_by(hostname=hostname, online=True))
            count = query.update({'online': False})
            if count == 0:
                raise exception.WampAgentNotFound(wampagent=hostname)

    def touch_wampagent(self, hostname):
        session = get_session()
        with session.begin():
            query = (model_query(models.WampAgent, session=session)
                     .filter_by(hostname=hostname))
            # since we're not changing any other field, manually set updated_at
            # and since we're heartbeating, make sure that online=True
            count = query.update({'updated_at': timeutils.utcnow(),
                                  'online': True})
            if count == 0:
                raise exception.WampAgentNotFound(wampagent=hostname)

    def get_wampagent_list(self, filters=None, limit=None, marker=None,
                           sort_key=None, sort_dir=None):
        query = model_query(models.WampAgent)
        query = self._add_wampagents_filters(query, filters)
        return _paginate_query(models.WampAgent, limit, marker,
                               sort_key, sort_dir, query)

    # PLUGIN api

    def get_plugin_by_id(self, plugin_id):
        query = model_query(models.Plugin).filter_by(id=plugin_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PluginNotFound(plugin=plugin_id)

    def get_plugin_by_uuid(self, plugin_uuid):
        query = model_query(models.Plugin).filter_by(uuid=plugin_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PluginNotFound(plugin=plugin_uuid)

    def get_plugin_by_name(self, plugin_name):
        query = model_query(models.Plugin).filter_by(name=plugin_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PluginNotFound(plugin=plugin_name)

    def destroy_plugin(self, plugin_id):

        session = get_session()
        with session.begin():
            query = model_query(models.Plugin, session=session)
            query = add_identity_filter(query, plugin_id)
            try:
                plugin_ref = query.one()
            except NoResultFound:
                raise exception.PluginNotFound(plugin=plugin_id)

            # Get plugin ID, if an UUID was supplied. The ID is
            # required for deleting all ports, attached to the plugin.
            if uuidutils.is_uuid_like(plugin_id):
                plugin_id = plugin_ref['id']

            query.delete()

    def update_plugin(self, plugin_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Plugin.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_plugin(plugin_id, values)
        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])
            elif 'uuid' in e.columns:
                raise exception.PluginAlreadyExists(uuid=values['uuid'])
            else:
                raise e

    def create_plugin(self, values):
        # ensure defaults are present for new plugins
        if 'uuid' not in values:
            values['uuid'] = uuidutils.generate_uuid()
        plugin = models.Plugin()
        plugin.update(values)
        try:
            plugin.save()
        except db_exc.DBDuplicateEntry:
            raise exception.PluginAlreadyExists(uuid=values['uuid'])
        return plugin

    def get_plugin_list(self, filters=None, limit=None, marker=None,
                        sort_key=None, sort_dir=None):
        query = model_query(models.Plugin)
        query = self._add_plugins_filters(query, filters)
        return _paginate_query(models.Plugin, limit, marker,
                               sort_key, sort_dir, query)

    # INJECTION PLUGIN api

    def get_injection_plugin_by_board_uuid(self, board_uuid):
        query = model_query(
            models.InjectionPlugin).filter_by(
            board_uuid=board_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.InjectionPluginNotFound()

    def create_injection_plugin(self, values):
        # ensure defaults are present for new plugins
        if 'uuid' not in values:
            values['uuid'] = uuidutils.generate_uuid()
        inj_plug = models.InjectionPlugin()
        inj_plug.update(values)
        try:
            inj_plug.save()
        except db_exc.DBDuplicateEntry:
            raise exception.PluginAlreadyExists(uuid=values['uuid'])
        return inj_plug

    def update_injection_plugin(self, plugin_injection_id, values):

        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Plugin.")
            raise exception.InvalidParameterValue(err=msg)
        try:
            return self._do_update_injection_plugin(
                plugin_injection_id, values)

        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])
            elif 'uuid' in e.columns:
                raise exception.PluginAlreadyExists(uuid=values['uuid'])
            else:
                raise e

    def get_injection_plugin_by_uuids(self, board_uuid, plugin_uuid):
        query = model_query(
            models.InjectionPlugin).filter_by(
            board_uuid=board_uuid).filter_by(
            plugin_uuid=plugin_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.InjectionPluginNotFound()

    def destroy_injection_plugin(self, injection_plugin_id):

        session = get_session()
        with session.begin():
            query = model_query(models.InjectionPlugin, session=session)
            query = add_identity_filter(query, injection_plugin_id)
            try:
                query.delete()

            except NoResultFound:
                raise exception.InjectionPluginNotFound()

    def get_injection_plugin_list(self, board_uuid):
        query = model_query(
            models.InjectionPlugin).filter_by(
            board_uuid=board_uuid)
        return query.all()

    # SERVICE api

    def get_service_by_id(self, service_id):
        query = model_query(models.Service).filter_by(id=service_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ServiceNotFound(service=service_id)

    def get_service_by_uuid(self, service_uuid):
        query = model_query(models.Service).filter_by(uuid=service_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ServiceNotFound(service=service_uuid)

    def get_service_by_name(self, service_name):
        query = model_query(models.Service).filter_by(name=service_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ServiceNotFound(service=service_name)

    def destroy_service(self, service_id):

        session = get_session()
        with session.begin():
            query = model_query(models.Service, session=session)
            query = add_identity_filter(query, service_id)
            try:
                service_ref = query.one()
            except NoResultFound:
                raise exception.ServiceNotFound(service=service_id)

            # Get service ID, if an UUID was supplied. The ID is
            # required for deleting all ports, attached to the service.
            if uuidutils.is_uuid_like(service_id):
                service_id = service_ref['id']

            query.delete()

    def update_service(self, service_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Service.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_service(service_id, values)
        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])
            elif 'uuid' in e.columns:
                raise exception.ServiceAlreadyExists(uuid=values['uuid'])
            else:
                raise e

    def create_service(self, values):
        # ensure defaults are present for new services
        if 'uuid' not in values:
            values['uuid'] = uuidutils.generate_uuid()
        service = models.Service()
        service.update(values)
        try:
            service.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ServiceAlreadyExists(uuid=values['uuid'])
        return service

    def get_service_list(self, filters=None, limit=None, marker=None,
                         sort_key=None, sort_dir=None):
        query = model_query(models.Service)
        query = self._add_services_filters(query, filters)
        return _paginate_query(models.Service, limit, marker,
                               sort_key, sort_dir, query)

    def _do_update_service(self, service_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Service, session=session)
            query = add_identity_filter(query, service_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ServiceNotFound(service=service_id)

            ref.update(values)
        return ref

    # EXPOSED SERVICE api

    def get_exposed_services_by_board_uuid(self, board_uuid):
        query = model_query(
            models.ExposedService).filter_by(
            board_uuid=board_uuid)
        try:
            return query.all()
        except NoResultFound:
            raise exception.NoExposedServices(uuid=board_uuid)

    def create_exposed_service(self, values):
        # ensure defaults are present for new services
        if 'uuid' not in values:
            values['uuid'] = uuidutils.generate_uuid()
        exp_serv = models.ExposedService()
        exp_serv.update(values)
        try:
            exp_serv.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ServiceAlreadyExposed(uuid=values['uuid'])
        return exp_serv

    def update_exposed_service(self, service_exposed_id, values):

        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Service.")
            raise exception.InvalidParameterValue(err=msg)
        try:
            return self._do_update_exposed_service(
                service_exposed_id, values)

        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])
            elif 'uuid' in e.columns:
                raise exception.ServiceAlreadyExists(uuid=values['uuid'])
            else:
                raise e

    def get_exposed_service_by_uuids(self, board_uuid, service_uuid):
        query = model_query(
            models.ExposedService).filter_by(
            board_uuid=board_uuid).filter_by(
            service_uuid=service_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ExposedServiceNotFound(uuid=service_uuid)

    def destroy_exposed_service(self, exposed_service_id):

        session = get_session()
        with session.begin():
            query = model_query(models.ExposedService, session=session)
            query = add_identity_filter(query, exposed_service_id)
            try:
                query.delete()

            except NoResultFound:
                raise exception.ExposedServiceNotFound()

    def get_exposed_service_list(self, board_uuid):
        query = model_query(
            models.ExposedService).filter_by(
            board_uuid=board_uuid)
        return query.all()

    def _do_update_exposed_service(self, service_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ExposedService, session=session)
            query = add_identity_filter(query, service_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ServiceNotFound(uuid=service_id)

            ref.update(values)
        return ref

    def get_port_by_id(self, port_id):
        query = model_query(models.Port).filter_by(id=port_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PortNotFound(id=port_id)

    def get_port_by_uuid(self, port_uuid):
        query = model_query(models.Port).filter_by(uuid=port_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PortNotFound(uuid=port_uuid)

    def get_port_by_name(self, port_name):
        query = model_query(models.Port).filter_by(name=port_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PortNotFound(name=port_name)

    def get_ports_by_board_uuid(self, board_uuid):
        query = model_query(
            models.Port).filter_by(
            board_uuid=board_uuid)
        try:
            return query.all()
        except NoResultFound:
            raise exception.NoPorts(uuid=board_uuid)

    def get_ports_by_wamp_agent_id(self, wamp_agent_id):
        query = model_query(
            models.Port).filter_by(
            wamp_agent_id=wamp_agent_id)
        try:
            return query.all()
        except NoResultFound:
            raise exception.NoPortsManaged(wamp_agent_id=wamp_agent_id)

    def get_port_list(
            self, filters=None, limit=None, marker=None,
            sort_key=None, sort_dir=None):
        query = model_query(models.Port)
        query = self._add_ports_filters(query, filters)
        return _paginate_query(models.Port, limit, marker,
                               sort_key, sort_dir, query)

    def create_port(self, values):
        port = models.Port()
        port.update(values)
        port.save()
        return port

    def destroy_port(self, uuid):
        session = get_session()
        with session.begin():
            query = model_query(models.Port, session=session)
            query = add_identity_filter(query, uuid)
            count = query.delete()
            if count == 0:
                raise exception.PortNotFound(uuid=uuid)

    # FLEET api

    def get_fleet_by_id(self, fleet_id):
        query = model_query(models.Fleet).filter_by(id=fleet_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.FleetNotFound(fleet=fleet_id)

    def get_fleet_by_uuid(self, fleet_uuid):
        query = model_query(models.Fleet).filter_by(uuid=fleet_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.FleetNotFound(fleet=fleet_uuid)

    def get_fleet_by_name(self, fleet_name):
        query = model_query(models.Fleet).filter_by(name=fleet_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.FleetNotFound(fleet=fleet_name)

    def destroy_fleet(self, fleet_id):

        session = get_session()
        with session.begin():
            query = model_query(models.Fleet, session=session)
            query = add_identity_filter(query, fleet_id)
            try:
                fleet_ref = query.one()
            except NoResultFound:
                raise exception.FleetNotFound(fleet=fleet_id)

            # Get fleet ID, if an UUID was supplied. The ID is
            # required for deleting all ports, attached to the fleet.
            if uuidutils.is_uuid_like(fleet_id):
                fleet_id = fleet_ref['id']

            query.delete()

    def update_fleet(self, fleet_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Fleet.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_fleet(fleet_id, values)
        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])
            elif 'uuid' in e.columns:
                raise exception.FleetAlreadyExists(uuid=values['uuid'])
            else:
                raise e

    def create_fleet(self, values):
        # ensure defaults are present for new fleets
        if 'uuid' not in values:
            values['uuid'] = uuidutils.generate_uuid()
        fleet = models.Fleet()
        fleet.update(values)
        try:
            fleet.save()
        except db_exc.DBDuplicateEntry:
            raise exception.FleetAlreadyExists(uuid=values['uuid'])
        return fleet

    def get_fleet_list(self, filters=None, limit=None, marker=None,
                       sort_key=None, sort_dir=None):
        query = model_query(models.Fleet)
        query = self._add_fleets_filters(query, filters)
        return _paginate_query(models.Fleet, limit, marker,
                               sort_key, sort_dir, query)

    def _do_update_fleet(self, fleet_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Fleet, session=session)
            query = add_identity_filter(query, fleet_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.FleetNotFound(fleet=fleet_id)

            ref.update(values)
        return ref

    # WEBSERVICE api

    def get_webservice_by_id(self, webservice_id):
        query = model_query(models.Webservice).filter_by(id=webservice_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.WebserviceNotFound(webservice=webservice_id)

    def get_webservice_by_uuid(self, webservice_uuid):
        query = model_query(models.Webservice).filter_by(uuid=webservice_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.WebserviceNotFound(webservice=webservice_uuid)

    def get_webservice_by_name(self, webservice_name):
        query = model_query(models.Webservice).filter_by(name=webservice_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.WebserviceNotFound(webservice=webservice_name)

    def destroy_webservice(self, webservice_id):

        session = get_session()
        with session.begin():
            query = model_query(models.Webservice, session=session)
            query = add_identity_filter(query, webservice_id)
            try:
                webservice_ref = query.one()
            except NoResultFound:
                raise exception.WebserviceNotFound(webservice=webservice_id)

            # Get webservice ID, if an UUID was supplied. The ID is
            # required for deleting all ports, attached to the webservice.
            if uuidutils.is_uuid_like(webservice_id):
                webservice_id = webservice_ref['id']

            query.delete()

    def update_webservice(self, webservice_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Webservice.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_webservice(webservice_id, values)
        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])
            elif 'uuid' in e.columns:
                raise exception.WebserviceAlreadyExists(uuid=values['uuid'])
            else:
                raise e

    def create_webservice(self, values):
        # ensure defaults are present for new webservices
        if 'uuid' not in values:
            values['uuid'] = uuidutils.generate_uuid()
        webservice = models.Webservice()
        webservice.update(values)
        try:
            webservice.save()
        except db_exc.DBDuplicateEntry:
            raise exception.WebserviceAlreadyExists(uuid=values['uuid'])
        return webservice

    def get_webservice_list(self, filters=None, limit=None, marker=None,
                            sort_key=None, sort_dir=None):
        query = model_query(models.Webservice)
        query = self._add_webservices_filters(query, filters)
        return _paginate_query(models.Webservice, limit, marker,
                               sort_key, sort_dir, query)

    def _do_update_webservice(self, webservice_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Webservice, session=session)
            query = add_identity_filter(query, webservice_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.WebserviceNotFound(webservice=webservice_id)

            ref.update(values)
        return ref

    # ENABLED_WEBSERIVCE api

    def get_enabled_webservice_by_id(self, enabled_webservice_id):
        query = model_query(models.EnabledWebservice).filter_by(
            id=enabled_webservice_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.EnabledWebserviceNotFound(
                enabled_webservice=enabled_webservice_id)

    def get_enabled_webservice_by_board_uuid(self, board_uuid):
        query = model_query(models.EnabledWebservice).filter_by(
            board_uuid=board_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.EnabledWebserviceNotFound(
                enabled_webservice=board_uuid)

    def destroy_enabled_webservice(self, enabled_webservice_id):

        session = get_session()
        with session.begin():
            query = model_query(models.EnabledWebservice, session=session)
            query = add_identity_filter(query, enabled_webservice_id)
            try:
                enabled_webservice_ref = query.one()
            except NoResultFound:
                raise exception.EnabledWebserviceNotFound(
                    enabled_webservice=enabled_webservice_id)

            # Get enabled_webservice ID, if an UUID was supplied. The ID is
            # required for deleting all ports, attached to the enabled_
            # webservice.
            if uuidutils.is_uuid_like(enabled_webservice_id):
                enabled_webservice_id = enabled_webservice_ref['id']

            query.delete()

    def create_enabled_webservice(self, values):
        # ensure defaults are present for new enabled_webservices
        if 'uuid' not in values:
            values['uuid'] = uuidutils.generate_uuid()
        enabled_webservice = models.EnabledWebservice()
        enabled_webservice.update(values)
        try:
            enabled_webservice.save()
        except db_exc.DBDuplicateEntry:
            raise exception.EnabledWebserviceAlreadyExists(uuid=values['uuid'])
        return enabled_webservice

    def get_enabled_webservice_list(self, filters=None, limit=None,
                                    marker=None,
                                    sort_key=None, sort_dir=None):
        query = model_query(models.EnabledWebservice)
        query = self._add_enabled_webservices_filters(query, filters)
        return _paginate_query(models.EnabledWebservice, limit, marker,
                               sort_key, sort_dir, query)
