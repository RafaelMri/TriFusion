#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  
#  Copyright 2012 Unknown <diogo@arch>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  Author: Diogo N. Silva
#  Version: 0.1
#  Last update: 11/02/14

from process.sequence import Alignment

from collections import OrderedDict
from operator import itemgetter
from base.plotter import *
import os
from os.path import join


class Cluster():
    """ Object for clusters of the OrthoMCL groups file. It is useful to set a
     number of attributes that will make subsequent filtration and
     processing much easier """

    def __init__(self, line_string):
        """
        To initialize a Cluster object, only a string compliant with the
        format of a cluster in an OrthoMCL groups file has to be provided.
        This line should contain the name of the group, a colon, and the
        sequences belonging to that group separated by whitespace
        :param line_string: String of a cluster
        """

        # Initializing attributes for parse_string
        self.name = None
        self.sequences = None
        self.species_frequency = {}

        # Initializing attributes for apply filter
        # If the value is different than None, this will inform downstream
        # objects of whether this cluster is compliant with the specified
        # gene_threshold
        self.gene_compliant = None
        # If the value is different than None, this will inform downstream
        # objects of whether this cluster is compliant with the specified
        # species_threshold
        self.species_compliant = None

        self.parse_string(line_string)

    def parse_string(self, cluster_string):
        """
        Parses the string and sets the group name and sequence list attributes
        """

        fields = cluster_string.split(":")
        # Setting the name and sequence list of the clusters
        self.name = fields[0].strip()
        self.sequences = fields[1].strip().split()

        # Setting the gene frequency for each species in the cluster
        species_list = set([field.split("|")[0] for field in self.sequences])
        self.species_frequency = dict((species, frequency) for species,
                                      frequency in zip(species_list,
                                      map(lambda species: str(
                                          self.sequences).count(species),
                                          species_list)))

    def apply_filter(self, gene_threshold, species_threshold):
        """
        This method will update two Cluster attributes, self.gene_flag and
        self.species_flag, which will inform downstream objects if this
        cluster respects the gene and species threshold
        :param gene_threshold: Integer for the maximum number of gene copies
        per species
        :param species_threshold: Integer for the minimum number of species
        present
        """

        # Check whether cluster is compliant with species_threshold
        if len(self.species_frequency) >= species_threshold and \
                species_threshold:
            self.species_compliant = True
        else:
            self.species_compliant = False

        # Check whether cluster is compliant with gene_threshold
        if max(self.species_frequency.values()) <= gene_threshold and \
                gene_threshold:
            self.gene_compliant = True
        else:
            self.gene_compliant = False


class OrthoGroupException(Exception):
    pass


class Group ():
    """ This represents the main object of the orthomcl toolbox module. It is
     initialized with a file name of a orthomcl groups file and provides
     several methods that act on that group file. To process multiple Group
     objects, see MultiGroups object """

    def __init__(self, groups_file, gene_threshold=None,
                 species_threshold=None, project_prefix="MyGroups"):

        # Initializing thresholds. These may be set from the start, or using
        #  some method that uses them as arguments
        self.gene_threshold = gene_threshold
        self.species_threshold = species_threshold

        # Attributes that will store the number (int) of cluster after gene and
        # species filter
        self.num_gene_compliant = 0
        self.num_species_compliant = 0

        # Attribute containing the total number of sequences
        self.total_seqs = 0

        # Attribute with name of the group file, which will be an ID
        self.group_name = groups_file
        # Initialize the project prefix for possible output files
        self.prefix = project_prefix
        # Initialize attribute containing the original groups
        self.groups = []
        # Initialize atribute containing the groups filtered using the gene and
        # species threshold. This attribute can be updated at any time using
        # the update_filtered_group method
        self.filtered_groups = []
        self.name = None
        # Parse groups file and populate groups attribute
        self.__parse_groups(groups_file)

    def __parse_groups(self, groups_file):
        """
        Parses the ortholog clusters in the groups file and populates the
         self.groups list with Cluster objects for each line in the groups file.
        :param groups_file: File name for the orthomcl groups file
        :return: populates the groups attribute
        """

        self.name = groups_file
        self.species_list = []
        groups_file_handle = open(groups_file)

        for line in groups_file_handle:
            cluster_object = Cluster(line)

            # Add cluster to general group list
            self.groups.append(cluster_object)

            # Update total sequence counter
            self.total_seqs += len(cluster_object.sequences)

            # Update species_list attribute
            cluster_species = cluster_object.species_frequency.keys()
            [self.species_list.append(species) for species in cluster_species
             if species not in self.species_list]

            # If thresholds have been specified, update self.filtered_groups
            # attribute
            if self.species_threshold and self.gene_threshold:
                cluster_object.apply_filter(self.gene_threshold,
                                            self.species_threshold)
                if cluster_object.species_compliant and \
                        cluster_object.gene_compliant:
                    # Add cluster to the filtered group list
                    self.filtered_groups.append(cluster_object)

                # Update num_species_compliant attribute
                if cluster_object.species_compliant:
                    self.num_species_compliant += 1
                # Update num_gene_compliant attribute
                if cluster_object.gene_compliant:
                    self.num_gene_compliant += 1


    def get_filters(self):
        """
        Returns a tuple with the thresholds for max gene copies and min species
        """

        return self.gene_threshold, self.species_threshold

    def basic_group_statistics(self):
        """
        This method creates a basic table in list format containing basic
        information of the groups file (total number of clusters, total number
        of sequences, number of clusters below the gene threshold, number of
        clusters below the species threshold and number of clusters below the
        gene AND species threshold)
        :return: List containing number of

        [total clusters,
         total sequences,
         clusters above gene threshold,
         clusters above species threshold,
         clusters above gene and species threshold]
        """

        # Total number of clusters
        total_cluster_num = len(self.groups)

        # Total number of sequenes
        total_sequence_num = self.total_seqs

        # Gene compliant clusters
        clusters_gene_threshold = self.num_gene_compliant

        # Species compliant clusters
        clusters_species_threshold = self.num_species_compliant

        clusters_all_threshold = len(self.filtered_groups)

        statistics = [total_cluster_num, total_sequence_num,
                      clusters_gene_threshold, clusters_species_threshold,
                      clusters_all_threshold]

        return statistics

    def paralog_per_species_statistic(self, output_file_name=
                                      "Paralog_per_species.csv", filt=True):
        """
        This method creates a CSV table with information on the number of
        paralog clusters per species
        :param output_file_name: string. Name of the output csv file
        :param filt: Boolean. Whether to use the filtered groups (True) or
        total groups (False)
        """

        # Setting which clusters to use
        if filt:
            groups = self.filtered_groups
        else:
            groups = self.groups

        paralog_count = dict((species, 0) for species in self.species_list)

        for cluster in groups:
            for species in paralog_count:
                if cluster.species_frequency[species] > 1:
                    paralog_count[species] += 1

        # Writing table
        output_handle = open(output_file_name, "w")
        output_handle.write("Species; Clusters with paralogs\n")

        for species, val in paralog_count.items():
            output_handle.write("%s; %s\n" % (species, val))

        output_handle.close()

    def export_filtered_group(self, output_file_name="filtered_groups",
                              get_stats=False):
        """ Writes the filtered groups into a new file """

        if self.filtered_groups:

            output_handle = open(output_file_name, "w")

            if get_stats:
                all_orthologs = len(self.groups)
                sp_compliant = 0
                gene_compliant = 0
                final_orthologs = 0

            for cluster in self.filtered_groups:
                if cluster.species_compliant and cluster.gene_compliant:
                    output_handle.write("%s: %s\n" % (
                                    cluster.name, " ".join(cluster.sequences)))
                    if get_stats:
                        final_orthologs += 1
                if get_stats:
                    if cluster.species_compliant:
                        sp_compliant += 1
                    if cluster.gene_compliant:
                        gene_compliant += 1

            output_handle.close()

            if get_stats:
                return all_orthologs, sp_compliant, gene_compliant,\
                       final_orthologs

        else:
            raise OrthoGroupException("The groups object must be filtered "
                                       "before using the export_filtered_group"
                                       "method")

    def update_filters(self, gn_filter, sp_filter):
        """
        Sets new values for the self.species_threshold and self.gene_threshold
        and updates the filtered_group
        :param gn_filter: int. Maximum value for gene copies in cluster
        :param sp_filter:  int. Minimum value for species in cluster
        """

        self.species_threshold = int(sp_filter)
        self.gene_threshold = int(gn_filter)

        self.update_filtered_group()

    def update_filtered_group(self):
        """
        This method creates a new filtered group variable, like
        export_filtered_group, but instead of writing into a new file, it
        replaces the self.filtered_groups variable
        """

        updated_group = []

        # Reset gene and species compliant counters
        self.num_gene_compliant = 0
        self.num_species_compliant = 0

        for cluster in self.groups:
            cluster.apply_filter(self.gene_threshold, self.species_threshold)
            if cluster.species_compliant and cluster.gene_compliant:
                updated_group.append(cluster)

            # Update num_species_compliant attribute
            if cluster.species_compliant:
                self.num_species_compliant += 1
            # Update num_gene_compliant attribute
            if cluster.gene_compliant:
                self.num_gene_compliant += 1

        self.filtered_groups = updated_group

    def retrieve_fasta(self, database, filt=True):
        """
        When provided with a database in Fasta format, this will use the
        Alignment object to retrieve sequences
        :param database: String. Fasta file
        :param filt: Boolean. Whether to use the filtered groups (True) or
        total groups (False)
        """

        if filt:
            groups = self.filtered_groups
        else:
            groups = self.groups

        if not os.path.exists("Orthologs"):
            os.makedirs("Orthologs")

        if isinstance(database, str):
            db_aln = Alignment(database)
            db_aln = db_aln.alignment
        elif isinstance(database, dict):
            db_aln = database
        else:
            raise OrthoGroupException("The input database is neither a string"
                                      "nor a dictionary object")

        for cluster in groups:
            output_handle = open(join("Orthologs", cluster.name + ".fas"), "w")
            for sequence_id in cluster.sequences:
                seq = db_aln[sequence_id]
                output_handle.write(">%s\n%s\n" % (sequence_id.split("|")[0],
                                                   seq))
            else:
                output_handle.close()


class MultiGroups ():
    """ Creates an object composed of multiple Group objects """

    def __init__(self, groups_files=None, gene_threshold=None,
                 species_threshold=None, project_prefix="MyGroups"):
        """
        :param groups_files: A list containing the file names of the multiple
        group files
        :return: Populates the self.multiple_groups attribute
        """

        # If a MultiGroups is initialized with duplicate Group objects, these
        # will be stored in a list. If all Group objects are unique, the list
        # will remain empty
        self.duplicate_groups = []

        # Initializing thresholds. These may be set from the start, or using
        # some method that uses them as arguments
        self.gene_threshold = gene_threshold
        self.species_threshold = species_threshold

        self.prefix = project_prefix

        self.multiple_groups = []

        if groups_files:
            for group_file in groups_files:

                # If group_file is already a Group object, just add it
                if isinstance(group_file, Group):
                    # Check for duplicate group files
                    if group_file.name in [x.name for x in
                                           self.multiple_groups]:
                        self.duplicate_groups.append(group_file)
                    else:
                        self.multiple_groups.append(group_file)

                else:
                    group_object = Group(group_file, self.gene_threshold,
                                         self.species_threshold)
                    if group_object.name in [x.name for x in
                                             self.multiple_groups]:
                        self.duplicate_groups.append(group_object)
                    else:
                        self.multiple_groups.append(group_object)

    def __iter__(self):

        return iter(self.multiple_groups)

    def add_group(self, group_obj):
        """
        Adds a group object
        :param group_obj: Group object
        """

        # Check for duplicate groups
        if group_obj.name not in [x.name for x in self.multiple_groups]:
            self.multiple_groups.append(group_obj)
        else:
            self.duplicate_groups.append(group_obj)

    def remove_group(self, group_id):
        """
        Removes a group object according to its name
        :param group_id: string, name matching a Group object name attribute
        """

        self.multiple_groups = [x for x in self.multiple_groups if
                                x.name.split(os.sep)[-1] != group_id]

    def get_group(self, group_id):
        """
        Returns a group object based on its name. If the name does not match
        any group object, returns None
        :param group_id: string. Name of group object
        """

        try:
            group_obj = [x for x in self.multiple_groups if
                         x.name.split(os.sep)[-1] == group_id][0]
            return group_obj
        except IndexError:
            return

    def add_multigroups(self, multigroup_obj):
        """
        Merges a MultiGroup object
        :param multigroup_obj: MultiGroup object
        """

        for group_obj in multigroup_obj:
            self.add_group(group_obj)

    def basic_multigroup_statistics(self, output_file_name=
                                    "multigroup_base_statistics.csv"):
        """
        :param output_file_name:
        :return:
        """

        # Creates the storage for the statistics of the several files
        statistics_storage = OrderedDict()

        for group in self.multiple_groups:
            group_statistics = group.basic_group_statistics()
            statistics_storage[group.name] = group_statistics

        output_handle = open(self.prefix + "." + output_file_name, "w")
        output_handle.write("Group file; Total clusters; Total sequences; "
                            "Clusters below gene threshold; Clusters above "
                            "species threshold; Clusters below gene and above"
                            " species thresholds\n")

        for group, vals in statistics_storage.items():
            output_handle.write("%s; %s\n" % (group, ";".join([str(x) for x
                                                               in vals])))

        output_handle.close()

    def bar_orthologs(self, output_file_name="Final_orthologs",
                             dest="./", stats="total"):
        """
        Creates a bar plot with the final ortholog values for each group file
        :param output_file_name: string. Name of output file
        :param dest: string. output directory
        :param stats: string. The statistics that should be used to generate
        the bar plot. Options are:
            ..: "1": Total orthologs
            ..: "2": Species compliant orthologs
            ..: "3": Gene compliant orthologs
            ..: "4": Final orthologs
            ..: "all": All of the above
            Multiple combinations can be provided, for instance: "123" will
            display bars for total, species compliant and gene compliant stats
        """

        # Stores the x-axys labels
        x_labels = []
        # Stores final ortholog values for all 4 possible data sets
        vals = [[], [], [], []]
        lgd = ["Total orthologs", "After species filter", "After gene filter",
               "Final orthologs"]

        # Get final ortholog values
        for g_obj in self.multiple_groups:

            x_labels.append(g_obj.name.split(os.sep)[-1])
            # Populate total orthologs
            if "1" in stats or stats == "all":
                vals[0].append(len(g_obj.groups))
            # Populate species compliant orthologs
            if "2" in stats or stats == "all":
                vals[1].append(g_obj.num_species_compliant)
            # Populate gene compliant orthologs
            if "3" in stats or stats == "all":
                vals[2].append(g_obj.num_gene_compliant)
            # Populate final orthologs
            if "4" in stats or stats == "all":
                vals[3].append(len(g_obj.filtered_groups))

        # Filter valid data sets
        lgd = [x for x in lgd if set(vals[lgd.index(x)]) != {None} and
               set(vals[lgd.index(x)]) != {0}]
        vals = [l for l in vals if set(l) != {None} and set(l) != {0}]

        # Sort values and labels
        # x_labels, vals = [list(x) for x in zip(*sorted(zip(x_labels, vals),
        #                                                key=itemgetter(1)))]

        # Create plot
        b_plt, lgd = bar_plot(vals, x_labels, lgd_list=lgd)
        b_plt.savefig(os.path.join(dest, output_file_name),
                      bbox_extra_artists=(lgd,), bbox_inches="tight",
                      transparent=True)
        b_plt.close()

    def group_overlap(self):
        """
        This will find the overlap of orthologs between two group files.
        THIS METHOD IS TEMPORARY AND EXPERIMENTAL
        """

        def parse_groups(group_obj):
            """
            Returns a list with the sorted ortholog clusters
            """

            storage = []

            for cluster in group_obj.groups:
                storage.append(set(cluster.sequences))

            return storage

        if len(self.multiple_groups) != 2:
            raise SystemExit("This method can only be used with two group "
                             "files")

        group1 = self.multiple_groups[0]
        group2 = self.multiple_groups[1]

        group1_list = parse_groups(group1)
        group2_list = parse_groups(group2)

        counter = 0
        for i in group1_list:
            if i in group2_list:
                counter += 1

        print(counter)

__author__ = "Diogo N. Silva"
__copyright__ = "Diogo N. Silva"
__credits__ = ["Diogo N. Silva"]
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Diogo N. Silva"
__email__ = "o.diogosilva@gmail.com"
__status__ = "Prototype"
