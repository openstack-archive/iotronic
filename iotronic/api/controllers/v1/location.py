#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.


from iotronic.api.controllers import base
from iotronic import objects
import wsme
from wsme import types as wtypes


class Location(base.APIBase):
    """API representation of a location.

    """

    longitude = wsme.wsattr(wtypes.text)
    latitude = wsme.wsattr(wtypes.text)
    altitude = wsme.wsattr(wtypes.text)

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Location.fields)
        for k in fields:
            # Skip fields we do not expose.
            if k is not 'created_at':
                if not hasattr(self, k):
                    continue
                self.fields.append(k)
                setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def convert_with_list(list):
        list_locations = []
        for l in list:
            list_locations.append(Location(**l.as_dict()))
        return list_locations
