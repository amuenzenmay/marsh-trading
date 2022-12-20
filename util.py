import inspect
import io
import sys
import json


class TwoWayDict(dict):
    def __init__(self, seq=None, **kwargs):
        if seq is None:
            super(TwoWayDict, self).__init__(**kwargs)
        else:
            super(TwoWayDict, self).__init__(seq, **kwargs)
            for k, v in seq.items():
                dict.__setitem__(self, v, k)
            for k, v in kwargs.items():
                dict.__setitem__(self, v, k)

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        if value in self:
            del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)

    def __len__(self):
        """Returns the number of connections"""
        return dict.__len__(self) // 2


def raiseNotDefined():
    file_name = inspect.stack()[1][1]
    line = inspect.stack()[1][2]
    method = inspect.stack()[1][3]

    print("*** Method not implemented: {} at line {} of {}".format(method, line, file_name))
    sys.exit(1)


def exception_alert(msg, tick):
    fileName = inspect.stack()[1][1]
    line = inspect.stack()[1][2]
    method = inspect.stack()[1][3]

    print("***{}\t {}: {} at line {} of {}".format(tick, msg, method, line, fileName))


def write_json(data, path):
    try:
        to_unicode = unicode
    except NameError:
        to_unicode = str
    with io.open(path, 'w', encoding='utf8') as outfile:
        str_ = json.dumps(data,
                          indent=4, sort_keys=True,
                          separators=(',', ': '), ensure_ascii=False)
        outfile.write(to_unicode(str_))


def read_json(path):
    with open(path) as data_file:
        data_loaded = json.load(data_file)
    return data_loaded


if __name__ == '__main__':
    pass
