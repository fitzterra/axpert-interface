"""
Library functions
"""

from collections.abc import MutableMapping


def flattenDict(
    d: MutableMapping, sep: str = ".", parent_key: str = ""
) -> MutableMapping:
    """
    Flattens a nested dict by separating nested keys with the sep char arg and
    then bringing all key/values to the top level of the dict.

    Args:
        d: The nested dictionary to flatten
        sep: The separator to use between hierarchical keys to for the top
            level flattened key
        parent_key: This is used by the recursive calls to the function for
            nested dicts and not used for the initial call.

    Args:
        Returns a flatten dict. For example, given:
        {
            'a': 1,
            'c': {'a': 2,
                  'b': {'x': 5,
                        'y': 10}},
            'd': [1, 2, 3]
        }

         after flattening will be:
         {
             'a': 1,
             'c.a': 2,
             'c.b.x': 5,
             'c.b.y': 10,
             'd': [1, 2, 3]
         }
    """
    # This the container for the final flattened list of items
    items = []
    # Cycle through all key/vals in the given dict
    for k, v in d.items():
        # If we have a parent_key from a recursive call, build the new key from
        # the parent separator and this key. Else it's just this key.
        new_key = parent_key + sep + k if parent_key else k
        # If the value is another key/value container, we recursively call
        # ourselves to flatten this nested dict
        if isinstance(v, MutableMapping):
            items.extend(flattenDict(v, sep, new_key).items())
        else:
            # If not a nested value, we append the (key, value) tuple to the
            # items list
            items.append((new_key, v))

    # Return a dict from converting the list of (key, val) tuples
    return dict(items)
