# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""Iotronic base exception handling.

Includes decorator for re-raising Iotronic-type exceptions.

SHOULD include dedicated exception logging.

"""

from oslo_config import cfg
from oslo_log import log as logging
import six

from iotronic.common.i18n import _
from iotronic.common.i18n import _LE


LOG = logging.getLogger(__name__)

exc_log_opts = [
    cfg.BoolOpt('fatal_exception_format_errors',
                default=False,
                help='Used if there is a formatting error when generating an '
                     'exception message (a programming error). If True, '
                     'raise an exception; if False, use the unformatted '
                     'message.'),
]

CONF = cfg.CONF
CONF.register_opts(exc_log_opts)


def _cleanse_dict(original):
    """Strip all admin_password, new_pass, rescue_pass keys from a dict."""
    return dict((k, v) for k, v in original.iteritems() if "_pass" not in k)


class IotronicException(Exception):
    """Base Iotronic Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")
    code = 500
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.message % kwargs

            except Exception as e:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_LE('Exception in string format operation'))
                for name, value in kwargs.items():
                    LOG.error("%s: %s" % (name, value))

                if CONF.fatal_exception_format_errors:
                    raise e
                else:
                    # at least get the core message out if something happened
                    message = self.message

        super(IotronicException, self).__init__(message)

    def __str__(self):
        """Encode to utf-8 then wsme api can consume it as well."""
        if not six.PY3:
            return unicode(self.args[0]).encode('utf-8')

        return self.args[0]

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return six.text_type(self)


class NotAuthorized(IotronicException):
    message = _("Not authorized.")
    code = 403


class OperationNotPermitted(NotAuthorized):
    message = _("Operation not permitted.")


class Invalid(IotronicException):
    message = _("Unacceptable parameters.")
    code = 400


class Conflict(IotronicException):
    message = _('Conflict.')
    code = 409


class TemporaryFailure(IotronicException):
    message = _("Resource temporarily unavailable, please retry.")
    code = 503


class NotAcceptable(IotronicException):
    # TODO(deva): We need to set response headers in the API for this exception
    message = _("Request not acceptable.")
    code = 406


class InvalidState(Conflict):
    message = _("Invalid resource state.")


class NodeAlreadyExists(Conflict):
    message = _("A node with UUID %(uuid)s already exists.")


class MACAlreadyExists(Conflict):
    message = _("A port with MAC address %(mac)s already exists.")


class PortAlreadyExists(Conflict):
    message = _("A port with UUID %(uuid)s already exists.")


class InstanceAssociated(Conflict):
    message = _("Instance %(instance_uuid)s is already associated with a node,"
                " it cannot be associated with this other node %(node)s")


class DuplicateName(Conflict):
    message = _("A node with name %(name)s already exists.")


class DuplicateCode(Conflict):
    message = _("A node with code %(code)s already exists.")


class InvalidUUID(Invalid):
    message = _("Expected a uuid but received %(uuid)s.")


class InvalidUuidOrName(Invalid):
    message = _("Expected a logical name or uuid but received %(name)s.")


class InvalidName(Invalid):
    message = _("Expected a logical name but received %(name)s.")


class InvalidIdentity(Invalid):
    message = _("Expected an uuid or int but received %(identity)s.")


class InvalidMAC(Invalid):
    message = _("Expected a MAC address but received %(mac)s.")


class InvalidStateRequested(Invalid):
    message = _('The requested action "%(action)s" can not be performed '
                'on node "%(node)s" while it is in state "%(state)s".')


class PatchError(Invalid):
    message = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


class InstanceDeployFailure(IotronicException):
    message = _("Failed to deploy instance: %(reason)s")


class ImageUnacceptable(IotronicException):
    message = _("Image %(image_id)s is unacceptable: %(reason)s")


class ImageConvertFailed(IotronicException):
    message = _("Image %(image_id)s is unacceptable: %(reason)s")


# Cannot be templated as the error syntax varies.
# msg needs to be constructed when raised.
class InvalidParameterValue(Invalid):
    message = _("%(err)s")


class MissingParameterValue(InvalidParameterValue):
    message = _("%(err)s")


class Duplicate(IotronicException):
    message = _("Resource already exists.")


class NotFound(IotronicException):
    message = _("Resource could not be found.")
    code = 404


class DHCPLoadError(IotronicException):
    message = _("Failed to load DHCP provider %(dhcp_provider_name)s, "
                "reason: %(reason)s")


class DriverNotFound(NotFound):
    message = _("Could not find the following driver(s): %(driver_name)s.")


class ImageNotFound(NotFound):
    message = _("Image %(image_id)s could not be found.")


class NoValidHost(NotFound):
    message = _("No valid host was found. Reason: %(reason)s")


class InstanceNotFound(NotFound):
    message = _("Instance %(instance)s could not be found.")


class NodeNotFound(NotFound):
    message = _("Node %(node)s could not be found.")


class NodeNotConnected(Invalid):
    message = _("Node %(node)s is not connected.")


class NodeAssociated(InvalidState):
    message = _("Node %(node)s is associated with instance %(instance)s.")


class PortNotFound(NotFound):
    message = _("Port %(port)s could not be found.")


class FailedToUpdateDHCPOptOnPort(IotronicException):
    message = _("Update DHCP options on port: %(port_id)s failed.")


class FailedToGetIPAddressOnPort(IotronicException):
    message = _("Retrieve IP address on port: %(port_id)s failed.")


class InvalidIPv4Address(IotronicException):
    message = _("Invalid IPv4 address %(ip_address)s.")


class FailedToUpdateMacOnPort(IotronicException):
    message = _("Update MAC address on port: %(port_id)s failed.")


class NoDriversLoaded(IotronicException):
    message = _("Conductor %(conductor)s cannot be started "
                "because no drivers were loaded.")


class ConductorNotFound(NotFound):
    message = _("Conductor %(conductor)s could not be found.")


class ConductorAlreadyRegistered(IotronicException):
    message = _("Conductor %(conductor)s already registered.")

class WampAgentNotFound(NotFound):
    message = _("WampAgent %(wampagent)s could not be found.")


class WampAgentAlreadyRegistered(IotronicException):
    message = _("WampAgent %(wampagent)s already registered.")


class PowerStateFailure(InvalidState):
    message = _("Failed to set node power state to %(pstate)s.")


class ExclusiveLockRequired(NotAuthorized):
    message = _("An exclusive lock is required, "
                "but the current context has a shared lock.")


class NodeMaintenanceFailure(Invalid):
    message = _("Failed to toggle maintenance-mode flag "
                "for node %(node)s: %(reason)s")


class NodeConsoleNotEnabled(Invalid):
    message = _("Console access is not enabled on node %(node)s")


class NodeInMaintenance(Invalid):
    message = _("The %(op)s operation can't be performed on node "
                "%(node)s because it's in maintenance mode.")


class IPMIFailure(IotronicException):
    message = _("IPMI call failed: %(cmd)s.")


class AMTConnectFailure(IotronicException):
    message = _("Failed to connect to AMT service.")


class AMTFailure(IotronicException):
    message = _("AMT call failed: %(cmd)s.")


class MSFTOCSClientApiException(IotronicException):
    message = _("MSFT OCS call failed.")


class SSHConnectFailed(IotronicException):
    message = _("Failed to establish SSH connection to host %(host)s.")


class SSHCommandFailed(IotronicException):
    message = _("Failed to execute command via SSH: %(cmd)s.")


class UnsupportedObjectError(IotronicException):
    message = _('Unsupported object type %(objtype)s')


class OrphanedObjectError(IotronicException):
    message = _('Cannot call %(method)s on orphaned %(objtype)s object')


class UnsupportedDriverExtension(Invalid):
    message = _('Driver %(driver)s does not support %(extension)s '
                '(disabled or not implemented).')


class IncompatibleObjectVersion(IotronicException):
    message = _('Version %(objver)s of %(objname)s is not supported')


class GlanceConnectionFailed(IotronicException):
    message = _("Connection to glance host %(host)s:%(port)s failed: "
                "%(reason)s")


class ImageNotAuthorized(NotAuthorized):
    message = _("Not authorized for image %(image_id)s.")


class InvalidImageRef(Invalid):
    message = _("Invalid image href %(image_href)s.")


class ImageRefValidationFailed(IotronicException):
    message = _("Validation of image href %(image_href)s failed, "
                "reason: %(reason)s")


class ImageDownloadFailed(IotronicException):
    message = _("Failed to download image %(image_href)s, reason: %(reason)s")


class KeystoneUnauthorized(IotronicException):
    message = _("Not authorized in Keystone.")


class KeystoneFailure(IotronicException):
    pass


class CatalogNotFound(IotronicException):
    message = _("Service type %(service_type)s with endpoint type "
                "%(endpoint_type)s not found in keystone service catalog.")


class ServiceUnavailable(IotronicException):
    message = _("Connection failed")


class Forbidden(IotronicException):
    message = _("Requested OpenStack Images API is forbidden")


class BadRequest(IotronicException):
    pass


class InvalidEndpoint(IotronicException):
    message = _("The provided endpoint is invalid")


class CommunicationError(IotronicException):
    message = _("Unable to communicate with the server.")


class HTTPForbidden(Forbidden):
    pass


class Unauthorized(IotronicException):
    pass


class HTTPNotFound(NotFound):
    pass


class ConfigNotFound(IotronicException):
    message = _("Could not find config at %(path)s")


class NodeLocked(Conflict):
    message = _("Node %(node)s is locked by host %(host)s, please retry "
                "after the current operation is completed.")


class NodeNotLocked(Invalid):
    message = _("Node %(node)s found not to be locked on release")


class NoFreeConductorWorker(TemporaryFailure):
    message = _('Requested action cannot be performed due to lack of free '
                'conductor workers.')
    code = 503  # Service Unavailable (temporary).


class VendorPassthruException(IotronicException):
    pass


class ConfigInvalid(IotronicException):
    message = _("Invalid configuration file. %(error_msg)s")


class DriverLoadError(IotronicException):
    message = _("Driver %(driver)s could not be loaded. Reason: %(reason)s.")


class ConsoleError(IotronicException):
    pass


class NoConsolePid(ConsoleError):
    message = _("Could not find pid in pid file %(pid_path)s")


class ConsoleSubprocessFailed(ConsoleError):
    message = _("Console subprocess failed to start. %(error)s")


class PasswordFileFailedToCreate(IotronicException):
    message = _("Failed to create the password file. %(error)s")


class IBootOperationError(IotronicException):
    pass


class IloOperationError(IotronicException):
    message = _("%(operation)s failed, error: %(error)s")


class IloOperationNotSupported(IotronicException):
    message = _("%(operation)s not supported. error: %(error)s")


class DracRequestFailed(IotronicException):
    pass


class DracClientError(DracRequestFailed):
    message = _('DRAC client failed. '
                'Last error (cURL error code): %(last_error)s, '
                'fault string: "%(fault_string)s" '
                'response_code: %(response_code)s')


class DracOperationFailed(DracRequestFailed):
    message = _('DRAC operation failed. Message: %(message)s')


class DracUnexpectedReturnValue(DracRequestFailed):
    message = _('DRAC operation yielded return value %(actual_return_value)s '
                'that is neither error nor expected %(expected_return_value)s')


class DracPendingConfigJobExists(IotronicException):
    message = _('Another job with ID %(job_id)s is already created  '
                'to configure %(target)s. Wait until existing job '
                'is completed or is canceled')


class DracInvalidFilterDialect(IotronicException):
    message = _('Invalid filter dialect \'%(invalid_filter)s\'. '
                'Supported options are %(supported)s')


class FailedToGetSensorData(IotronicException):
    message = _("Failed to get sensor data for node %(node)s. "
                "Error: %(error)s")


class FailedToParseSensorData(IotronicException):
    message = _("Failed to parse sensor data for node %(node)s. "
                "Error: %(error)s")


class InsufficientDiskSpace(IotronicException):
    message = _("Disk volume where '%(path)s' is located doesn't have "
                "enough disk space. Required %(required)d MiB, "
                "only %(actual)d MiB available space present.")


class ImageCreationFailed(IotronicException):
    message = _('Creating %(image_type)s image failed: %(error)s')


class SwiftOperationError(IotronicException):
    message = _("Swift operation '%(operation)s' failed: %(error)s")


class SNMPFailure(IotronicException):
    message = _("SNMP operation '%(operation)s' failed: %(error)s")


class FileSystemNotSupported(IotronicException):
    message = _("Failed to create a file system. "
                "File system %(fs)s is not supported.")


class IRMCOperationError(IotronicException):
    message = _('iRMC %(operation)s failed. Reason: %(error)s')


class VirtualBoxOperationFailed(IotronicException):
    message = _("VirtualBox operation '%(operation)s' failed. "
                "Error: %(error)s")


class HardwareInspectionFailure(IotronicException):
    message = _("Failed to inspect hardware. Reason: %(error)s")


class NodeCleaningFailure(IotronicException):
    message = _("Failed to clean node %(node)s: %(reason)s")


class PathNotFound(IotronicException):
    message = _("Path %(dir)s does not exist.")


class DirectoryNotWritable(IotronicException):
    message = _("Directory %(dir)s is not writable.")
