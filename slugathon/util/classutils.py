__copyright__ = "Copyright (c) 2014 Yclept Nemo"
__license__ = "GNU GPL v3"


class Deletable(type):
    marker = "__deletable__"

    @classmethod
    def mark(cls, obj):
        setattr(obj, cls.marker, True)
        return obj

    @classmethod
    def marked(cls, obj):
        try:
            mark = getattr(obj, cls.marker)
        except AttributeError:
            return False
        else:
            return bool(mark)

    def __new__(cls, name,  bases, namespace):
        namespace = { k:v
                      for k,v
                      in namespace.items()
                      if not cls.marked(v)
                    }
        return super().__new__(cls, name, bases, namespace)
