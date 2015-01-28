#!/usr/bin/env python
"""Recategorizer.py

Reassign categories to all policies and packages, then offer to remove
unused categories.

Copyright (C) 2015 Shea G Craig <shea.craig@da.org>

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
import sys

from Foundation import (NSData,
                        NSPropertyListSerialization,
                        NSPropertyListMutableContainers,
                        NSPropertyListXMLFormat_v1_0)

import jss


# Globals
# Edit these if you want to change their default values.
AUTOPKG_PREFERENCES = '~/Library/Preferences/com.github.autopkg.plist'
DESCRIPTION = ("Recategorizer will first ask you to assign categories to all "
               "policies. You will be offered a chance to bail prior to "
               "committing changes.\nNext, you will be asked to assign "
               "categories to all packages.  Again, you may bail prior to "
               "committing changes.\nFinally, a list of unused categories "
               "will be generated, and you will be prompted individually to "
               "keep or delete them.")


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
        print("\nPlease choose a category for: %s" % self.name)
        choice = raw_input("Choose and perish: (DEFAULT \'%s\') " %
                        self.default)

        if choice.isdigit() and in_range(int(choice), len(option_list)):
            result = {self.name: self.options[int(choice)]}
        elif choice == '':
            result = {}
        elif choice.isdigit() and not in_range(int(choice),
                                                len(option_list)):
            raise ChoiceError("Invalid Choice")
        else:
            # User provided a new object value.
            result = {self.name: choice}

        return result


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


def build_policy_menu(j):
    """Construct the menu for prompting users to create a JSS recipe."""
    menu = Menu()

    # Categories
    categories = [cat.name for cat in j.Category()]

    policies = j.Policy().retrieve_all()
    for policy in policies:
        menu.add_submenu(Submenu(policy.name, categories,
                                 policy.findtext('general/category/name')))

    return menu


def build_package_menu(j):
    """Construct the menu for prompting users to create a JSS recipe."""
    menu = Menu()

    # Categories
    categories = [cat.name for cat in j.Category()]

    packages = j.Package().retrieve_all()
    for package in packages:
        menu.add_submenu(Submenu(package.name, categories,
                                 package.findtext('category')))

    return menu


def build_argparser():
    """Create our argument parser."""
    parser = argparse.ArgumentParser(description="Bulk edit policy "
                                     "categories. %s" % DESCRIPTION)

    return parser


def in_range(val, size):
    """Determine whether a value x is within the range 0 > x <= size."""
    return val < size and val >= 0


def cls():
    """Clear the dang screen!"""
    subprocess.call(['clear'])


def confirm(results):
    """Offer user a chance to bail prior to committing changes."""
    cls()
    pprint.pprint(results)
    while True:
        choice = raw_input("Last chance: Are you sure you want to commit these"
                           " changes? (Y|N) ")
        if choice.upper() == 'Y':
            response = True
            break
        elif choice.upper() == 'N':
            response = False
            break
        else:
            next

    return response


def ensure_categories(j, categories):
    """Given a list of categories, ensure that they all exist on the
    JSS.

    """
    print("Ensuring categories exist...")
    category_set = set(categories)
    for category in category_set:
        try:
            j.Category(category)
            print("Category %s exists..." % category)
        except jss.exceptions.JSSGetError:
            jss.Category(j, category).save()
            print("Category %s created." % category)


def get_unused_categories(j):
    """Return a set of empty categories."""
    # Unused cats = {all_cats} - {policy_categories + package_categories}
    policy_categories = {policy.findtext('general/category/name')for policy in
                         j.Policy().retrieve_all()}
    package_categories = {package.findtext('category') for package in
                          j.Package().retrieve_all()}
    all_categories = {cat.name for cat in j.Category().retrieve_all()}

    used_categories = policy_categories.union(package_categories)
    unused_categories = all_categories.difference(used_categories)
    # Remove the reserved category types:
    unused_categories.difference_update({'Unknown', 'No category assigned'})

    return unused_categories


def main():
    """Commandline processing."""
    # Handle command line arguments (None at this time).
    parser = build_argparser()
    args = parser.parse_args()

    # Get AutoPkg configuration settings for python-jss/JSSImporter.
    autopkg_env = Plist(AUTOPKG_PREFERENCES)
    j = configure_jss(autopkg_env)

    print("\n%s\n\n" % DESCRIPTION)
    response = raw_input("Hit enter to continue. ")
    print("Building data...")

    # Build our interactive policy menu
    policy_menu = build_policy_menu(j)

    # Run the policy questions past the user.
    policy_menu.run()

    if policy_menu.results:
        # Give them a chance to bail.
        response = confirm(policy_menu.results)

        # Save changes to policies.
        if response:
            ensure_categories(j, policy_menu.results.values())
            for name, category in policy_menu.results.items():
                print("Updating policy: %s to category %s" % (name, category))
                policy = j.Policy(name)
                policy.set_category(j.Category(category))
                policy.save()
        else:
            sys.exit()

    # Pause before continuing so user can see what just happened.
    ready = raw_input("Ready to continue onto packages? (Hit any enter) ")

    # Build our interactive package menu
    package_menu = build_package_menu(j)

    # Run the package questions past the user.
    package_menu.run()

    if package_menu.results:
        # Give them a chance to bail.
        response = confirm(package_menu.results)

        # Save changes to policies.
        if response:
            ensure_categories(j, package_menu.results.values())
            for name, category in package_menu.results.items():
                print("Updating package: %s to category %s" % (name, category))
                package = j.Package(name)
                package.set_category(j.Category(category))
                package.save()
        else:
            sys.exit()

    # Offer to delete unused categories:
    unused_categories = get_unused_categories(j)
    for category in unused_categories:
        response = raw_input("Category: %s is not in use. Would you like to "
                             "delete it? (Y|N) " % category)

        if response.upper() == 'Y':
            j.Category(category).delete()


if __name__ == '__main__':
    main()
