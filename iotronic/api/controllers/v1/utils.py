# Copyright 2013 Red Hat, Inc.
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

import jsonpatch
from oslo_config import cfg
from oslo_utils import uuidutils
import pecan
import wsme

from iotronic.common import exception
from iotronic.common.i18n import _
from iotronic.common import utils
from iotronic import objects

CONF = cfg.CONF

JSONPATCH_EXCEPTIONS = (jsonpatch.JsonPatchException,
                        jsonpatch.JsonPointerException,
                        KeyError)


def validate_limit(limit):
    if limit is None:
        return CONF.api.max_limit

    if limit <= 0:
        raise wsme.exc.ClientSideError(_("Limit must be positive"))

    return min(CONF.api.max_limit, limit)


def validate_sort_dir(sort_dir):
    if sort_dir not in ['asc', 'desc']:
        raise wsme.exc.ClientSideError(_("Invalid sort direction: %s. "
                                         "Acceptable values are "
                                         "'asc' or 'desc'") % sort_dir)
    return sort_dir


def apply_jsonpatch(doc, patch):
    for p in patch:
        if p['op'] == 'add' and p['path'].count('/') == 1:
            if p['path'].lstrip('/') not in doc:
                msg = _('Adding a new attribute (%s) to the root of '
                        ' the resource is not allowed')
                raise wsme.exc.ClientSideError(msg % p['path'])
    return jsonpatch.apply_patch(doc, jsonpatch.JsonPatch(patch))


def get_patch_value(patch, path):
    for p in patch:
        if p['path'] == path:
            return p['value']


def allow_board_logical_names():
    # v1.5 added logical name aliases
    return pecan.request.version.minor >= 5


def get_rpc_board(board_ident):
    """Get the RPC board from the board uuid or logical name.

    :param board_ident: the UUID or logical name of a board.

    :returns: The RPC Board.
    :raises: InvalidUuidOrName if the name or uuid provided is not valid.
    :raises: BoardNotFound if the board is not found.
    """
    # Check to see if the board_ident is a valid UUID.  If it is, treat it
    # as a UUID.
    if uuidutils.is_uuid_like(board_ident):
        return objects.Board.get_by_uuid(pecan.request.context, board_ident)

    # We can refer to boards by their name, if the client supports it
    # if allow_board_logical_names():
    #    if utils.is_hostname_safe(board_ident):
    else:
        return objects.Board.get_by_name(pecan.request.context, board_ident)

    raise exception.InvalidUuidOrName(name=board_ident)

    raise exception.BoardNotFound(board=board_ident)


def get_rpc_plugin(plugin_ident):
    """Get the RPC plugin from the plugin uuid or logical name.

    :param plugin_ident: the UUID or logical name of a plugin.

    :returns: The RPC Plugin.
    :raises: InvalidUuidOrName if the name or uuid provided is not valid.
    :raises: PluginNotFound if the plugin is not found.
    """
    # Check to see if the plugin_ident is a valid UUID.  If it is, treat it
    # as a UUID.
    if uuidutils.is_uuid_like(plugin_ident):
        return objects.Plugin.get_by_uuid(pecan.request.context, plugin_ident)

    # We can refer to plugins by their name, if the client supports it
    # if allow_plugin_logical_names():
    #    if utils.is_hostname_safe(plugin_ident):
    else:
        return objects.Plugin.get_by_name(pecan.request.context, plugin_ident)

    raise exception.InvalidUuidOrName(name=plugin_ident)

    raise exception.PluginNotFound(plugin=plugin_ident)


def get_rpc_service(service_ident):
    """Get the RPC service from the service uuid or logical name.

    :param service_ident: the UUID or logical name of a service.

    :returns: The RPC Service.
    :raises: InvalidUuidOrName if the name or uuid provided is not valid.
    :raises: ServiceNotFound if the service is not found.
    """
    # Check to see if the service_ident is a valid UUID.  If it is, treat it
    # as a UUID.
    if uuidutils.is_uuid_like(service_ident):
        return objects.Service.get_by_uuid(pecan.request.context,
                                           service_ident)

    # We can refer to services by their name, if the client supports it
    # if allow_service_logical_names():
    #    if utils.is_hostname_safe(service_ident):
    else:
        return objects.Service.get_by_name(pecan.request.context,
                                           service_ident)

    raise exception.InvalidUuidOrName(name=service_ident)

    raise exception.ServiceNotFound(service=service_ident)


def get_rpc_port(port_ident):
    """Get the RPC port from the port uuid.

    :param port_ident: the UUID or logical name of a port.

    :returns: The RPC Port.
    :raises: InvalidUuidOrName if the name or uuid provided is not valid.
    :raises: portNotFound if the port is not found.
    """
#     Check to see if the port_ident is a valid UUID.  If it is, treat it
#     as a UUID.
    if uuidutils.is_uuid_like(port_ident):
        return objects.Port.get_by_uuid(pecan.request.context,
                                        port_ident)

#     We can refer to ports by their name, if the client supports it
    else:
        return objects.Port.get_by_name(pecan.request.context,
                                        port_ident)

    raise exception.InvalidUuidOrName(uuid=port_ident)

    raise exception.PortNottFound(uuid=port_ident)


def is_valid_board_name(name):
    """Determine if the provided name is a valid board name.

    Check to see that the provided board name is valid, and isn't a UUID.

    :param: name: the board name to check.
    :returns: True if the name is valid, False otherwise.
    """
    return utils.is_hostname_safe(name) and (not uuidutils.is_uuid_like(name))


def is_valid_name(name):
    """Determine if the provided name is a valid name.

    Check to see that the provided board name isn't a UUID.

    :param: name: the board name to check.
    :returns: True if the name is valid, False otherwise.
    """
    return not uuidutils.is_uuid_like(name)


def is_valid_logical_name(name):
    """Determine if the provided name is a valid hostname."""

    return utils.is_valid_logical_name(name)


def check_for_invalid_fields(fields, object_fields):
    """Check for requested non-existent fields.

    Check if the user requested non-existent fields.

    :param fields: A list of fields requested by the user
    :object_fields: A list of fields supported by the object.
    :raises: InvalidParameterValue if invalid fields were requested.

    """
    invalid_fields = set(fields) - set(object_fields)
    if invalid_fields:
        raise exception.InvalidParameterValue(
            _('Field(s) "%s" are not valid') % ', '.join(invalid_fields))
