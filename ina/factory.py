"""Tools to manage different actions of a project."""

import sys
import logging


class Option:
    """Class to represent a basic option that a user can specify using a CLI"""

    def __init__(self, short, name, default, cast=lambda x: x):
        self.arity = 0
        self.short = short
        self.name = name
        self.default = default
        self.cast = cast
        self.value = None

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __str__(self):
        return "<Option; name=\"%s\">; value=\"%s\">" % (self.name, self.get())

    def __repr__(self):
        return str(self)

    def parse(self, raw):
        """Parse the option value from user input"""
        self.value = self.cast(*raw)

    def get(self):
        """Return the current option value, if overriden by user"""
        if self.value is None:
            return self.default
        return self.value


class UnaryOption(Option):
    """A unary option, i.e. a flag"""

    def __init__(self, *args, **kwargs):
        Option.__init__(self, *args, **kwargs)
        self.arity = 1

    def parse(self, raw):
        self.value = not self.value


class BinaryOption(Option):
    """A binary option, that use a casting function for its value"""

    def __init__(self, *args, **kwargs):
        Option.__init__(self, *args, **kwargs)
        self.arity = 2


class OptionSet(dict):
    """Hashmap to handle several options"""

    def __init__(self, option_list):
        super(OptionSet, self).__init__()
        self.list = option_list
        for option in option_list:
            self[option.short] = option
            self[option.name] = option

    def dictify(self):
        """Return the final option values"""
        return {
            option.name: option.get()
            for option in self.list
        }


class Factory:
    """Factory that handles options and actions, and parse arguments"""

    def __init__(self, option_list, actions):
        self.options = OptionSet(option_list)
        self.actions = actions

    def _parse_arguments(self, args):
        i = 0
        while i < len(args):
            name = args[i]
            if not name.startswith("-"):
                raise ValueError("Illegal argument: '%s'" % name)
            name = name[1:]
            if name.startswith("-"):
                name = name[1:]
            try:
                option = self.options[name]
            except KeyError:
                raise ValueError("Unknown argument: '%s'" % name)
            option.parse(args[i + 1: i + option.arity])
            i += option.arity

    def _parse_actions(self, name):
        action = self.actions.get(name, None)
        if action is None:
            raise ValueError("Unknown action: '%s'" % name)
        return action

    def get_documentation(self):
        """Return the documentation for this factory usage"""
        text = "Usage\n"
        text += "\tpython %s [action] [option]*\n" % sys.argv[0]
        text += "\nActions\n"
        for name, function in self.actions.items():
            text += "\t%s %s\n" % (name.ljust(12), function.__doc__)
        text += "\nOptions\n"
        for option in self.options.list:
            text += "\t-%s --%s %s\n" % (
                option.short,
                option.name.ljust(24),
                option.default
            )
        return text

    def parse(self, args):
        """Parse the system arguments"""
        if len(args) == 0:
            raise ValueError("Specify at least an action.")
        action = self._parse_actions(args[0])
        self._parse_arguments(args[1:])
        return action, self.options.dictify()

    def start(self):
        """Parse arguments and execute the action"""
        try:
            action, options = self.parse(sys.argv[1:])
        except ValueError as error:
            print(self.get_documentation())
            raise error
        for key, value in options.items():
            logging.debug("Option '%s' is set to '%s'", key, value)
        action(options)
