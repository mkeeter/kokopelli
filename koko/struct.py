class Struct:
    """ @class Struct
        @brief Class with named member variables.
    """
    def __init__(self, **entries):
        """ @brief Struct constructor
            @param entries
        """
        self.__dict__.update(entries)

    def __str__(self):
        s = ''
        for d in self.__dict__:
            s += '%s:  %s\n' % (d, self.__dict__[d])
        return s[:-1]
