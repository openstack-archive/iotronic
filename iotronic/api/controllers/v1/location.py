import pecan
from wsme import types as wtypes
import wsme

from iotronic.api.controllers import base
from iotronic import objects


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

'''
class LocationCollection(collection.Collection):
    """API representation of a collection of locations."""

    locations = [Location]
    """A list containing locations objects"""

    def __init__(self, **kwargs):
        self._type = 'locations'

    @staticmethod
    def convert_with_locates(locations,
        limit, url=None, expand=False, **kwargs):
        collection = LocationCollection()
        collection.locations = [Location.convert_with_locates(n, expand)
            for n in locations]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection
'''
