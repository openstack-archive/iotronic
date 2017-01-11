# Copyright 2011 OpenStack LLC.
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


from oslo_log import log
LOG = log.getLogger(__name__)

def register_board():
    return 'hello!\n'

def board_on_leave(session_id):
    LOG.debug('A node with %s disconnectd', session_id)

def board_on_join(session_id):
    LOG.debug('A node with %s joined', session_id)   
