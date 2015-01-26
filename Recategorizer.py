#!/usr/bin/env python
"""Recategorizer.py

Bulk edit policy categories.

Copyright (C) 2014 Shea G Craig <shea.craig@da.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import argparse
import os.path
import pprint
import readline
import subprocess

from Foundation import (NSData,
                        NSPropertyListSerialization,
                        NSPropertyListMutableContainers,
                        NSPropertyListXMLFormat_v1_0)

import jss


# Globals
# Edit these if you want to change their default values.
AUTOPKG_PREFERENCES = '~/Library/Preferences/com.github.autopkg.plist'

__version__ = '0.1.0'

class ChoiceError(Exception):
    """An invalid choice was made."""
    pass


class Plist(dict):
    """Abbreviated plist representation (as a dict) with methods for
    reading, writing, and creating blank plists.

    """
    def __init__(self, filename=None):
        """Parses an XML file into a Recipe object."""
        self._xml = {}

        if filename:
            self.read_recipe(filename)
        else:
            self.new_plist()

    def __getitem__(self, key):
        return self._xml[key]

    def __setitem__(self, key, value):
        self._xml[key] = value

    def __delitem__(self, key):
        del self._xml[key]

    def __iter__(self):
        return iter(self._xml)

    def __len__(self):
        return len(self._xml)

    def __repr__(self):
        return dict(self._xml).__repr__()

    def __str__(self):
        return dict(self._xml).__str__()

    def read_recipe(self, path):
        """Read a recipe into a dict."""
        path = os.path.expanduser(path)
        if not (os.path.isfile(path)):
            raise Exception("File does not exist: %s" % path)
        info, pformat, error = \
            NSPropertyListSerialization.propertyListWithData_options_format_error_(
                NSData.dataWithContentsOfFile_(path),
                NSPropertyListMutableContainers,
                None,
                None
            )
        if error:
            raise Exception("Can't read %s: %s" % (path, error))

        self._xml = info

    def write_recipe(self, path):
        """Write a recipe to path."""
        path = os.path.expanduser(path)
        plist_data, error = NSPropertyListSerialization.dataWithPropertyList_format_options_error_(
            self._xml,
            NSPropertyListXMLFormat_v1_0,
            0,
            None
        )
        if error:
            raise Exception(error)
        else:
            if plist_data.writeToFile_atomically_(path, True):
                return
            else:
                raise Exception("Failed writing data to %s" % path)

    def new_plist(self):
        """Generate a barebones recipe plist."""
        pass


class Menu(object):
    """Presents users with a menu and handles their input."""
    def __init__(self):
        self.submenus = []
        self.results = {}

    def run(self):
        """Run, in order, through our submenus, asking questions."""
        for submenu in self.submenus:
            while True:
                try:
                    result = submenu.ask()
                    break
                except ChoiceError:
                    print("\n**Invalid entry! Try again.**")
                    continue
            self.results.update(result)

    def add_submenu(self, submenu):
        """Add a submenu to our questions list."""
        if isinstance(submenu, Submenu):
            self.submenus.append(submenu)
        else:
            raise Exception("Only Submenu may be added!")


class Submenu(object):
    """Represents an individual menu 'question'."""
    def __init__(self, name, options, default=''):
        """Create a submenu.

        name:               Policy name.
        options:            List of potential string "name" values.
                            Will also accept a single value.
        default:            The default choice (to accept, hit enter).

        """
        self.name = name
        if not isinstance(options, list):
            self.options = [options]
        else:
            self.options = options
        self.default = default

    def ask(self):
        """Ask user a question based on configured values."""
        cls()

        # We're not afraid of zero-indexed lists!
        indexes = xrange(len(self.options))
        option_list = zip(indexes, self.options)
        for option in option_list:
            choice_string = "%s: %s" % option
            if self.default == option[1]:
                choice_string += " (DEFAULT)"
            print(choice_string)

        print("\nHit enter to accept default choice, or enter a number.")
        print("Create a new category by entering a new name.")
        print("\nPlease choose a category for policy: %s" % self.name)
        choice = raw_input("Choose and perish: (DEFAULT \'%s\') " %
                        self.default)

        if choice.isdigit() and in_range(int(choice), len(option_list)):
            result = self.options[int(choice)]
        elif choice == '':
            result = self.default
        elif choice.isdigit() and not in_range(int(choice),
                                                len(option_list)):
            raise ChoiceError("Invalid Choice")
        else:
            # User provided a new object value.
            result = choice

        return {self.name: result}


def configure_jss(env):
    """Configure a JSS object."""
    repo_url = env["JSS_URL"]
    auth_user = env["API_USERNAME"]
    auth_pass = env["API_PASSWORD"]
    ssl_verify = env.get("JSS_VERIFY_SSL", True)
    suppress_warnings = env.get("JSS_SUPPRESS_WARNINGS", False)
    repos = env.get("JSS_REPOS")
    j = jss.JSS(url=repo_url, user=auth_user, password=auth_pass,
                ssl_verify=ssl_verify, repo_prefs=repos,
                suppress_warnings=suppress_warnings)
    return j


def build_menu(j):
    """Construct the menu for prompting users to create a JSS recipe."""
    menu = Menu()

    # Categories
    categories = [cat.name for cat in j.Category()]

    policies = j.Policy().retrieve_all()
    for policy in policies:
        menu.add_submenu(Submenu(policy.name, categories,
                                 policy.findtext('general/category/name')))

    return menu


def build_argparser():
    """Create our argument parser."""
    parser = argparse.ArgumentParser(description="Bulk edit policy "
                                     "categories.")

    return parser


def in_range(val, size):
    """Determine whether a value x is within the range 0 > x <= size."""
    return val < size and val >= 0


def cls():
    """Clear the dang screen!"""
    subprocess.call(['clear'])


def main():
    """Commandline processing."""
    # Handle command line arguments
    parser = build_argparser()
    args = parser.parse_args()

    # Get AutoPkg configuration settings for python-jss/JSSImporter.
    autopkg_env = Plist(AUTOPKG_PREFERENCES)
    j = configure_jss(autopkg_env)

    # Build our interactive menu
    menu = build_menu(j)
    menu.submenus = menu.submenus[0:5]

    # Run the questions past the user.
    menu.run()
    for name, category in menu.results.items():
        print(name, category)
        policy = j.Policy(name)
        policy.set_category(j.Category(category))
        policy.save()


if __name__ == '__main__':
    main()
