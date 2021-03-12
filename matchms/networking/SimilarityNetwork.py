import networkx as nx
import numpy
from matchms import Scores
from .networking_functions import get_top_hits


class SimilarityNetwork:
    """Create a spectal network from spectrum similarities.

    For example

    .. testcode::

        import numpy as np
        from matchms import Spectrum, calculate_scores
        from matchms.similarity import ModifiedCosine
        from matchms.networking import SimilarityNetwork

        spectrum_1 = Spectrum(mz=np.array([100, 150, 200.]),
                              intensities=np.array([0.7, 0.2, 0.1]),
                              metadata={"precursor_mz": 100.0,
                                        "testID": "one"})
        spectrum_2 = Spectrum(mz=np.array([104.9, 140, 190.]),
                              intensities=np.array([0.4, 0.2, 0.1]),
                              metadata={"precursor_mz": 105.0,
                                        "testID": "two"})

        # Use factory to construct a similarity function
        modified_cosine = ModifiedCosine(tolerance=0.2)
        spectrums = [spectrum_1, spectrum_2]
        scores = calculate_scores(spectrums, spectrums, modified_cosine)
        ms_network = SimilarityNetwork(identifier="testID")

        print(f"Modified cosine score is {score['score']:.2f} with {score['matches']} matched peaks")

    Should output

    .. testoutput::

        Modified cosine score is 0.83 with 1 matched peaks

    """
    def __init__(self, identifier: str = "spectrumid",
                 top_n: int = 20,
                 max_links: int = 10,
                 score_cutoff: float = 0.7):
        """
        Parameters
        ----------
        identifier
            Unique intentifier for each spectrum in scores. Will also be used for
            node names.
        top_n
            Consider edge between spectrumA and spectrumB if score falls into
            top_n for spectrumA or spectrumB (link_method="single"), or into
            top_n for spectrumA and spectrumB (link_method="mutual"). From those
            potential links, only max_links will be kept, so top_n must be >= max_links.
        max_links
            Maximum number of links to add per node. Default = 10.
            Due to incoming links, total number of links per node can be higher.
        score_cutoff
            Threshold for given similarities. Edges/Links will only be made for
            similarities > score_cutoff. Default = 0.7.
        """
        self.identifier = identifier
        self.top_n = top_n
        self.max_links = max_links
        self.score_cutoff = score_cutoff
        self.graph = None

    def create_network(self, scores: Scores) -> nx.Graph:
        """
        Function to create network from given top-n similarity values. Expects that
        similarities given in scores are from an all-vs-all comparison including all
        possible pairs.

        Args:
        --------
        scores
            Matchms Scores object containing all spectrums and pair similarities for
            generating a network.
        """
        assert self.top_n >= self.max_links, "top_n must be >= max_links"
        assert numpy.all(scores.queries == scores.references), \
            "Expected symmetric scores object with queries==references"
        unique_ids = list({s.get(self.identifier) for s in scores.queries})

        # Initialize network graph, add nodes
        msnet = nx.Graph()
        msnet.add_nodes_from(unique_ids)

        # Collect location and score of highest scoring candidates for queries and references
        similars_idx, similars_scores = get_top_hits(scores, top_n=self.top_n,
                                                     search_by="queries")

        # Add edges based on global threshold (cutoff) for weights
        for i, spec in enumerate(scores.queries):
            query_id = spec.get(self.identifier)

            ref_candidates = numpy.array([scores.references[x].get(self.identifier)
                                          for x in similars_idx[query_id]])
            idx = numpy.where((similars_scores[query_id] >= self.cutoff) &
                              (ref_candidates != query_id))[0][:self.max_links]
            if self.link_method == "single":
                new_edges = [(query_id, str(ref_candidates[x]),
                              float(similars_scores[query_id][x])) for x in idx]
            elif self.link_method == "mutual":
                new_edges = [(query_id, str(ref_candidates[x]),
                              float(similars_scores[query_id][x]))
                             for x in idx if i in similars_idx[ref_candidates[x]][:]]
            else:
                raise ValueError("Link method not kown")

            msnet.add_weighted_edges_from(new_edges)

        self.graph = msnet
