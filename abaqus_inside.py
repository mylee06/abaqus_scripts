""" Functions to be used by the Abaqus CAE Python interpreter.
    Developed by Rodrigo Rivero.
    https://github.com/rodrigo1392"""

from __future__ import print_function
from abaqus import *
from abaqusConstants import *
from caeModules import *
from collections import OrderedDict
import collections
import os
from tools_submodule.filesystem_tools import files_with_extension_lister
import ast


def mesh_extract_set_nodes(odb, set_name):
    """
    Returns a dict with a tuple (set_name, instance_name) as keys and
    a list of tuples (node label, node coordinates).
    Inputs: odb = Odb object to read from.
            set_name = str. Name of set which points labels are to be extracted.
    Output: Dict with nodes labels of the input set.
    """
    odb = odbs_odbobject_normalizer(odb)
    node_set = odb.rootAssembly.nodeSets[set_name]
    instances_names_list = [i for i in node_set.instanceNames]
    output = {set_name:
              {instance_name:
               collections.OrderedDict((node.label, node.coordinates) for
                                       node in node_set.nodes[num])
               for num, instance_name in enumerate(instances_names_list)}}
    return output


def models_modify_set_name(set_name, new_set_name):
    """
    Modifies the name of a set in all the Models of the current Database.
    Inputs: set_name = string. Name of the set to be renamed.
            new_set_name = string. New name for the set.
    """
    for model_key, model in mdb.models.items():
        model.rootAssembly.sets.changeKey(fromName=set_name, toName=new_set_name)
    return


def odbs_odbobject_normalizer(odb_ish):
    """
    Returns an Odb object, based on what kind of variable the input is.
    If it already is an Odb object, returns it.
    If not, it looks for the corresponend Odb object within the opened Odbs,
    if there's none, try to open it.
    Input: odb_ish. Odb object or path to one
    Output: Odb object.
    """
    if isinstance(odb_ish, str):
        try:
            odb = session.odbs[odb_ish]
        except KeyError:
            # Open odb
            odb = session.openOdb(odb_ish, readOnly=False)
    else:
        odb = odb_ish
    return odb


def odbs_get_calc_time_folder(odbs_folder, show=True, recursive=False, close_odbs=True):
    """
    Gets calculation time for all Odb object in a folder.
    Input: Folder to fetch Odb objects from.
           show. Boolean, if True, print Odb short name and OdbJobtime.
           recursive. Boolean, if True, search for Odb objects recursively.
           close_odbs. Boolean, if True, close all odbs after extracting info.
    Output: Dict of Odb names : Dict of times pairs.
    """
    output = {}
    odb_list = files_with_extension_lister(odbs_folder, '.odb', full_name_option=True, sub_folders_option=recursive)
    print(len(odb_list), 'Odb objects found')
    for job_key in odb_list:
        odb = odbs_odbobject_normalizer(job_key)
        output[job_key] = odbs_get_calc_time(odb, show)
    if close_odbs:
        from abaqusMacros import odbs_close_all_odbs
        odbs_close_all_odbs()
    return output


def odbs_get_calc_time(odb, show=True):
    """
    Gets calculation time for the Odb object.
    Input: Odb to read the calculation data from.
           show. Boolean, if True, print Odb short name and OdbJobtime.
    Output: Dict object, with systemTime, userTime and wallclockTime as keys
            and corresponding values in seconds as values.
    """
    odbs_odbobject_normalizer(odb)
    # Convert to dict
    calc_time = odb.diagnosticData.jobTime
    output = ast.literal_eval(str(calc_time)[1:-1])
    if show:
        odb_name = (os.path.splitext(os.path.basename(odb.name))[0])
        print(odb_name, ': ', str(calc_time))
    return output


def odbs_retrieve_odb_name(number, show_all=False):
    """
    Returns name of the Odb object correspondent to a given position in an
    alphabetically order list of session Odbs.
    Input: number. Int of position of the Odb in the list.
    Output: String of the corresponding Odb name.
    """
    keys = session.odbs.keys()
    keys = sorted(keys)
    selected_key = keys[number]
    if show_all:
        print('Currently opened Odbs', keys)
    return selected_key


def odbs_retrieve_set_name(odb, number, show_all=False):
    """
    Returns name of set correspondent to a given position in an
    alphabetically order list of Odb sets.
    Input: odb. OdbObject or path to it.
           number. Int of position of the set in the list.
    Output: String of the corresponding set name.
    """
    odb = odbs_odbobject_normalizer(odb)
    keys = odb.rootAssembly.nodeSets.keys()
    keys = sorted(keys)
    selected_key = keys[number]
    if show_all:
        print('Available node sets', keys)
    return selected_key


def odbs_upgrade_odbs_folder(odbs_folder, recursive=False, print_every=1):
    """
    Upgrades all Odb objects in odb_folder to current Abaqus CAE version.
    Inputs: odbs_folder. Folder to fetch Odb objects from.
            recursive. Boolean, if True, search for Odb objects recursively.
            print_every. Int that defines intervals for printing info.
    """
    import odbAccess
    odb_list = files_with_extension_lister(odbs_folder, '.odb', full_name_option=True, sub_folders_option=recursive)
    upgradable_odb_list = [i for i in odb_list if odbAccess.isUpgradeRequiredForOdb(i)]
    print(len(odb_list), 'Odb objects found', len(upgradable_odb_list), 'require upgrade')
    temp_name = os.path.join(odbs_folder, 'temp_odb_name.odb')
    for job_number, job_key in enumerate(upgradable_odb_list):
        # Option to print less
        if divmod(job_number, print_every)[1]==0:
             print('Processing', job_key, job_number + 1, 'of', len(upgradable_odb_list))
        new_name = job_key
        old_name = job_key.replace('.odb', '-old.odb')
        session.upgradeOdb(job_key, temp_name)
        # Rename old and new Odb files
        os.rename(job_key, old_name)
        os.rename(temp_name, new_name)
    print('DONE')
    return
