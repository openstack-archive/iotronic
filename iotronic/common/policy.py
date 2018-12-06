# Copyright (c) 2011 OpenStack Foundation
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

"""Policy Engine For Ironic."""

import sys

from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log
from oslo_policy import policy

from iotronic.common import exception
from iotronic.common.i18n import _LW

_ENFORCER = None
CONF = cfg.CONF
LOG = log.getLogger(__name__)

default_policies = [
    # Legacy setting, don't remove. Likely to be overridden by operators who
    # forget to update their policy.json configuration file.
    # This gets rolled into the new "is_admin" rule below.
    policy.RuleDefault('admin_api',
                       'role:admin or role:administrator',
                       description='Legacy rule for cloud admin access'),
    # is_public_api is set in the environment from AuthTokenMiddleware
    policy.RuleDefault('public_api',
                       'is_public_api:True',
                       description='Internal flag for public API routes'),

    policy.RuleDefault('is_admin',
                       'rule:admin_api',
                       description='Full read/write API access'),
    policy.RuleDefault('is_admin_iot_project',
                       'role:admin_iot_project',
                       description='Full read/write API access'),
    policy.RuleDefault('is_manager_iot_project',
                       'role:manager_iot_project',
                       description='Full read/write API access'),
    policy.RuleDefault('is_user_iot',
                       'role:user_iot',
                       description='Full read/write API access'),
    policy.RuleDefault('is_owner',
                       'user:%(owner)s',
                       description='full access to the owner'),
    policy.RuleDefault('admin_or_owner',
                       'rule:is_admin or rule:is_owner',
                       description='full access to the owner or the admin'),
    policy.RuleDefault('is_iot_member',
                       'rule:is_admin_iot_project '
                       'or rule:is_manager_iot_project or rule:is_user_iot',
                       description='define a member on iot context'),
]

# NOTE(deva): to follow policy-in-code spec, we define defaults for
#             the granular policies in code, rather than in policy.json.
#             All of these may be overridden by configuration, but we can
#             depend on their existence throughout the code.

board_policies = [
    policy.RuleDefault('iot:board:get',
                       'rule:is_admin or rule:is_iot_member',
                       description='Retrieve Board records'),
    policy.RuleDefault('iot:board:create',
                       'rule:is_admin_iot_project',
                       description='Create Board records'),
    policy.RuleDefault('iot:board:delete',
                       'rule:is_admin or rule:is_admin_iot_project '
                       'or rule:is_manager_iot_project',
                       description='Delete Board records'),
    policy.RuleDefault('iot:board:update',
                       'rule:is_admin or rule:is_admin_iot_project '
                       'or rule:is_manager_iot_project',
                       description='Update Board records'),

]

plugin_policies = [
    policy.RuleDefault('iot:plugin:get',
                       'rule:is_admin or rule:is_iot_member',
                       description='Retrieve Plugin records'),
    policy.RuleDefault('iot:plugin:create',
                       'rule:is_iot_member',
                       description='Create Plugin records'),
    policy.RuleDefault('iot:plugin:get_one', 'rule:admin_or_owner',
                       description='Retrieve a Plugin record'),
    policy.RuleDefault('iot:plugin:delete', 'rule:admin_or_owner',
                       description='Delete Plugin records'),
    policy.RuleDefault('iot:plugin:update', 'rule:admin_or_owner',
                       description='Update Plugin records'),

]

injection_plugin_policies = [
    policy.RuleDefault('iot:plugin_on_board:get',
                       'rule:admin_or_owner',
                       description='Retrieve Plugin records'),
    policy.RuleDefault('iot:plugin_remove:delete', 'rule:admin_or_owner',
                       description='Delete Plugin records'),

    policy.RuleDefault('iot:plugin_action:post',
                       'rule:admin_or_owner',
                       description='Create Plugin records'),
    policy.RuleDefault('iot:plugin_inject:put', 'rule:admin_or_owner',
                       description='Retrieve a Plugin record'),

]

service_policies = [
    policy.RuleDefault('iot:service:get',
                       'rule:is_admin or rule:is_iot_member',
                       description='Retrieve Service records'),
    policy.RuleDefault('iot:service:create',
                       'rule:is_iot_member',
                       description='Create Service records'),
    policy.RuleDefault('iot:service:get_one', 'rule:admin_or_owner',
                       description='Retrieve a Service record'),
    policy.RuleDefault('iot:service:delete', 'rule:admin_or_owner',
                       description='Delete Service records'),
    policy.RuleDefault('iot:service:update', 'rule:admin_or_owner',
                       description='Update Service records'),

]

port_on_board_policies = [
    policy.RuleDefault('iot:port_on_board:get',
                       'rule:is_admin or rule:is_iot_member',
                       description='Retrieve Service records'),
    policy.RuleDefault('iot:port_on_board:create',
                       'rule:is_iot_member',
                       description='Create Service records'),
    policy.RuleDefault('iot:port_on_board:get_one', 'rule:admin_or_owner',
                       description='Retrieve a Service record'),
    policy.RuleDefault('iot:port_on_board:delete', 'rule:admin_or_owner',
                       description='Delete Service records'),
    policy.RuleDefault('iot:port_on_board:update', 'rule:admin_or_owner',
                       description='Update Service records'),

]

exposed_service_policies = [
    policy.RuleDefault('iot:service_on_board:get',
                       'rule:admin_or_owner',
                       description='Retrieve Service records'),
    policy.RuleDefault('iot:service_remove:delete', 'rule:admin_or_owner',
                       description='Delete Service records'),
    policy.RuleDefault('iot:service_action:post',
                       'rule:admin_or_owner',
                       description='Create Service records'),
    policy.RuleDefault('iot:service_inject:put', 'rule:admin_or_owner',
                       description='Retrieve a Service record'),

]

fleet_policies = [
    policy.RuleDefault('iot:fleet:get',
                       'rule:is_admin or rule:is_iot_member',
                       description='Retrieve Fleet records'),
    policy.RuleDefault('iot:fleet:create',
                       'rule:is_iot_member',
                       description='Create Fleet records'),
    policy.RuleDefault('iot:fleet:get_one', 'rule:admin_or_owner',
                       description='Retrieve a Fleet record'),
    policy.RuleDefault('iot:fleet:delete', 'rule:admin_or_owner',
                       description='Delete Fleet records'),
    policy.RuleDefault('iot:fleet:update', 'rule:admin_or_owner',
                       description='Update Fleet records'),

]

webservice_policies = [
    policy.RuleDefault('iot:webservice:get',
                       'rule:is_admin or rule:is_iot_member',
                       description='Retrieve Webservice records'),
    policy.RuleDefault('iot:webservice:create',
                       'rule:is_iot_member',
                       description='Create Webservice records'),
    policy.RuleDefault('iot:webservice:get_one', 'rule:admin_or_owner',
                       description='Retrieve a Webservice record'),
    policy.RuleDefault('iot:webservice:delete', 'rule:admin_or_owner',
                       description='Delete Webservice records'),
    policy.RuleDefault('iot:webservice:update', 'rule:admin_or_owner',
                       description='Update Webservice records'),

]

enabledwebservice_policies = [
    policy.RuleDefault('iot:enabledwebservice:get',
                       'rule:is_admin or rule:is_iot_member',
                       description='Retrieve EnabledWebservice records'),
    policy.RuleDefault('iot:enabledwebservice:get_one',
                       'rule:admin_or_owner',
                       description='Retrieve a EnabledWebservice record'),
]


def list_policies():
    policies = (default_policies
                + board_policies
                + plugin_policies
                + injection_plugin_policies
                + service_policies
                + exposed_service_policies
                + port_on_board_policies
                + fleet_policies
                + webservice_policies
                + enabledwebservice_policies
                )
    return policies


@lockutils.synchronized('policy_enforcer')
def init_enforcer(policy_file=None, rules=None,
                  default_rule=None, use_conf=True):
    """Synchronously initializes the policy enforcer

       :param policy_file: Custom policy file to use, if none is specified,
                           `CONF.oslo_policy.policy_file` will be used.
       :param rules: Default dictionary / Rules to use. It will be
                     considered just in the first instantiation.
       :param default_rule: Default rule to use,
                            CONF.oslo_policy.policy_default_rule will
                            be used if none is specified.
       :param use_conf: Whether to load rules from config file.

    """
    global _ENFORCER

    if _ENFORCER:
        return

    # NOTE(deva): Register defaults for policy-in-code here so that they are
    # loaded exactly once - when this module-global is initialized.
    # Defining these in the relevant API modules won't work
    # because API classes lack singletons and don't use globals.
    _ENFORCER = policy.Enforcer(CONF, policy_file=policy_file,
                                rules=rules,
                                default_rule=default_rule,
                                use_conf=use_conf)

    _ENFORCER.register_defaults(list_policies())


def get_enforcer():
    """Provides access to the single instance of Policy enforcer."""

    if not _ENFORCER:
        init_enforcer()

    return _ENFORCER


def get_oslo_policy_enforcer():
    # This method is for use by oslopolicy CLI scripts. Those scripts need the
    # 'output-file' and 'namespace' options, but having those in sys.argv means
    # loading the Ironic config options will fail as those are not expected to
    # be present. So we pass in an arg list with those stripped out.

    conf_args = []
    # Start at 1 because cfg.CONF expects the equivalent of sys.argv[1:]
    i = 1
    while i < len(sys.argv):
        if sys.argv[i].strip('-') in ['namespace', 'output-file']:
            i += 2
            continue
        conf_args.append(sys.argv[i])
        i += 1

    cfg.CONF(conf_args, project='ironic')

    return get_enforcer()


# NOTE(deva): We can't call these methods from within decorators because the
# 'target' and 'creds' parameter must be fetched from the call time
# context-local pecan.request magic variable, but decorators are compiled
# at module-load time.


def authorize(rule, target, creds, *args, **kwargs):
    """A shortcut for policy.Enforcer.authorize()

    Checks authorization of a rule against the target and credentials, and
    raises an exception if the rule is not defined.
    Always returns true if CONF.auth_strategy == noauth.

    Beginning with the Newton cycle, this should be used in place of 'enforce'.
    """
    if CONF.auth_strategy == 'noauth':
        return True
    enforcer = get_enforcer()

    try:
        return enforcer.authorize(rule, target, creds, do_raise=True,
                                  *args, **kwargs)
    except policy.PolicyNotAuthorized:
        raise exception.HTTPForbidden(resource=rule)


def check(rule, target, creds, *args, **kwargs):
    """A shortcut for policy.Enforcer.enforce()

    Checks authorization of a rule against the target and credentials
    and returns True or False.
    """
    enforcer = get_enforcer()
    return enforcer.enforce(rule, target, creds, *args, **kwargs)


def enforce(rule, target, creds, do_raise=False, exc=None, *args, **kwargs):
    """A shortcut for policy.Enforcer.enforce()

    Checks authorization of a rule against the target and credentials.
    Always returns true if CONF.auth_strategy == noauth.

    """
    # NOTE(deva): this method is obsoleted by authorize(), but retained for
    # backwards compatibility in case it has been used downstream.
    # It may be removed in the Pike cycle.
    LOG.warning(_LW(
        "Deprecation warning: calls to ironic.common.policy.enforce() "
        "should be replaced with authorize(). This method may be removed "
        "in a future release."))
    if CONF.auth_strategy == 'noauth':
        return True
    enforcer = get_enforcer()
    return enforcer.enforce(rule, target, creds, do_raise=do_raise,
                            exc=exc, *args, **kwargs)
