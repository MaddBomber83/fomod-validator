#!/usr/bin/env python

# Copyright 2016 Daniel Nunes
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os.path import join, isfile, isdir
from lxml import etree
from .utility import check_file, check_fomod
from .exceptions import MissingFileError, MissingFolderError, WarningError, ParserError


def check_warnings(package_path, elem_tree=None):
    """
    Check for common errors that are usually ignored by mod managers. Raises WarningError if any are found.
    :param package_path: The root folder of your package. Should contain a "fomod" folder with the installer inside.
    :param elem_tree: The root element of your config xml tree.
    """
    try:
        if not elem_tree:
            fomod_folder = check_fomod(package_path)
            config_file = check_file(join(package_path, fomod_folder))
            config_root = etree.parse(join(package_path, fomod_folder, config_file)).getroot()
        else:
            config_root = elem_tree

        element_list = [_WarningElement(config_root,
                                        ("moduleName", "moduleImage", "moduleDependencies", "requiredInstallFiles",
                                         "installSteps", "conditionalFileInstalls"),
                                        "Repeated Elements",
                                        "The tag {} has several occurrences, this may produce unexpected results.",
                                        lambda elem, x: sum(1 for value in x if value.tag == elem.tag) >= 2),
                        _WarningElement(config_root,
                                        ("folder",),
                                        "Missing Source Folders",
                                        "These source folders weren't found inside the package. "
                                        "The installers ignore this so be sure to fix it.",
                                        lambda elem: not isdir(join(package_path, elem.get("source")))),
                        _WarningElement(config_root,
                                        ("file",),
                                        "Missing Source Files",
                                        "These source files weren't found inside the package. "
                                        "The installers ignore this so be sure to fix it.",
                                        lambda elem: not isfile(join(package_path, elem.get("source")))),
                        _WarningElement(config_root,
                                        ("moduleImage", "image"),
                                        "Missing Images",
                                        "These images weren't found inside the package. "
                                        "The installers ignore this so be sure to fix it.",
                                        lambda elem: not isfile(join(package_path, elem.get("path"))))]

        log_list = []
        for warn in element_list:
            log_list.append(warn.tag_log)

        result = _log_warnings(log_list)

        if result:
            raise WarningError(result)
    except (MissingFolderError, MissingFileError):
        raise
    except etree.ParseError as e:
        raise ParserError(str(e))


class _WarningElement(object):
    def __init__(self, elem_root, tags, title, error_msg, condition):
        tag_list = []
        for element in elem_root.iter():
            if element.tag in tags:
                tag_list.append(element)

        tag_result = []
        for elem in tag_list:
            from inspect import signature
            if signature(condition).parameters == 2:
                if condition(elem, tag_list):
                    tag_result.append(elem)
            else:
                if condition(elem):
                    tag_result.append(elem)

        self.tag_log = _ElementLog(tag_result, title, error_msg) if tag_result else None


class _ElementLog(object):
    def __init__(self, elements, title, msg):
        self.elements = {}
        for elem_ in elements:
            if elem_.tag not in self.elements.keys():
                self.elements[elem_.tag] = [elem_]
            else:
                self.elements[elem_.tag].append(elem_)

        self.title = title

        self.msgs = {}
        for elem_ in elements:
            self.msgs[elem_.tag] = msg.replace("{}", elem_.tag)


def _log_warnings(list_):
    result = ""

    for log in list_:
        if log:
            result += "<i>" + log.title + "</i><br><br>"

            for tag in log.elements:
                result += "Lines"
                for elem in log.elements[tag]:
                    result += " " + str(elem.sourceline) + ","
                result = result[:-1]
                result += ": " + log.msgs[tag] + "<br>"

            result += "<br><br>"

    return result
