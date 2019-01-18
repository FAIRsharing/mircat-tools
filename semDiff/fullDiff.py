from collections import namedtuple
from copy import deepcopy
from semDiff import compareNetwork, compareEntities
from utils.schema2context import generate_context_mapping, generate_labels_from_contexts
from utils.prepare_fulldiff_input import load_context

import json


class FullSemDiff:
    """
    A class that computes the coverage at entity level and extracts 'semantic synonyms'
    (named twins in the code) between two network. It will then compute the coverage at
    attribute level between 'semantic synonyms'.
    """

    def __init__(self, contexts, network_1, network_2):
        """ The class constructor

        :param contexts: an array containing the two context networks to use
        :param network_1: a dictionary containing the first set of schemas
        :param network_2: a dictionary containing the second set of schemas
        """

        self.total_entities = 0
        self.half_twins = 0
        self.twins = []

        twin_tuple = namedtuple('Twins', ['first_entity', 'second_entity'])
        twin_coverage = namedtuple('TwinCoverage', ['twins', 'overlap'])

        # Compute the comparison of entities based on their semantic type
        entity_coverage = compareNetwork.NetworkCoverage(contexts)

        # for each mapped entity
        for entity_name in entity_coverage.covered_entities:
            self.total_entities += 1
            twins = entity_coverage.covered_entities[entity_name]

            # if the entity has twins
            if twins is not None and entity_name.lower() + "_schema.json" in network_1.keys():
                entity_schema = network_1[entity_name.lower() + "_schema.json"]
                entity_context = {"@context": contexts[0][entity_name.lower() + "_schema.json"]}

                # For each twin
                for twin in twins:
                    if twin.lower() + "_schema.json" in network_2.keys():
                        self.half_twins += 1
                        twin_schema = network_2[twin.lower() + "_schema.json"]
                        twin_context = {"@context": contexts[1][twin.lower() + "_schema.json"]}
                        local_twin = twin_tuple(entity_name, twin)

                        # compare the entities
                        attribute_diff = compareEntities.EntityCoverage(entity_schema,
                                                                        entity_context,
                                                                        twin_schema,
                                                                        twin_context)
                        # create the tuple
                        attribute_coverage = twin_coverage(local_twin,
                                                           attribute_diff.full_coverage)

                        # adds it to output
                        self.twins.append(attribute_coverage)


class FullSemDiffMultiple:
    """
    A class that computes the coverage at entity level and extracts
    'semantic synonyms' (named twins in the code) between multiple
    networks. It will then compute the coverage at attribute level between 'semantic synonyms'.
    """

    def __init__(self, networks):

        self.networks = deepcopy(networks)
        self.contexts = []
        self.output = []

        for network in self.networks:
            self.contexts.append(network["contexts"])

        self.compute_overlap()

    def compute_overlap(self, start_position=0):
        local_overlap = []
        for i in range(start_position + 1, len(self.networks)):
            contexts = [self.networks[start_position]["contexts"], self.networks[i]["contexts"]]
            coverage = FullSemDiff(contexts,
                                   self.networks[start_position]["schemas"],
                                   self.networks[i]["schemas"])
            local_overlap.append(coverage.twins)

        if len(local_overlap) > 0:
            self.output.append(local_overlap)

        if start_position < len(self.networks):
            self.compute_overlap(start_position + 1)


class FullDiffGenerator:

    def __init__(self, first_network, second_network):

        network_1_resolved = generate_context_mapping(first_network['url'], first_network['regex'])
        raw_context_1 = {
            'contexts': network_1_resolved[0]
        }
        context_1 = load_context(raw_context_1)

        network_2_resolved = generate_context_mapping(second_network['url'],
                                                      second_network['regex'])
        raw_context_2 = {
            'contexts': network_2_resolved[0]
        }
        context_2 = load_context(raw_context_2)

        labels = generate_labels_from_contexts(context_1, {})
        labels = generate_labels_from_contexts(context_2, labels)

        prepared_input = [
            {
                "name": first_network['name'],
                "schemas": network_1_resolved[1],
                "contexts": context_1
            },
            {
                "name": second_network['name'],
                "schemas": network_2_resolved[1],
                "contexts": context_2
            }
        ]

        overlaps = FullSemDiffMultiple(prepared_input)
        final_output = {
            "network1": overlaps.networks[0],
            "network2": overlaps.networks[1],
            "overlaps": overlaps.output[0][0],
            "labels": labels
        }

        self.json = final_output


if __name__ == '__main__':
    output_file = "html/overlap.json"

    regex_1 = {
        "/schema": "/context/obo",
        "_schema.json": "_obo_context.jsonld"
    }

    network_1 = {
        "url": "https://w3id.org/mircat/miacme/schema/miacme_schema.json",
        "regex": regex_1,
        "name": "MIACME"
    }
    network_2 = {
        "url": "https://w3id.org/mircat/miaca/schema/miaca_schema.json",
        "regex": regex_1,
        "name": "MIACA"
    }
    network_3 = {
        "url": "https://w3id.org/mircat/miacme/schema/miacme_schema.json",
        "regex": regex_1,
        "name": "MIACME"
    }

    report = FullDiffGenerator(network_1, network_3)

    with open("outputfile.json", "w") as writter:
        writter.write(json.dumps(report.json, indent=4))
        writter.close()
