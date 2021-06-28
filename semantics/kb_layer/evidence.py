import semantics.graph_layer.elements as elements


# Keys used to look up evidence in the element's data dictionary.
EVIDENCE_MEAN_KEY = 'EV_MEAN'
EVIDENCE_SAMPLES_KEY = 'EV_SAMPLES'

# Together, the initial mean and initial samples implement additive smoothing (aka Laplacian
# smoothing) of the evidence.
INITIAL_MEAN = 0.5
INITIAL_SAMPLES = 1.0


def get_evidence_mean(element: elements.Element) -> float:
    """The balance of evidence for/against the existence of a given graph element."""
    result = element.get_data_key(EVIDENCE_MEAN_KEY, INITIAL_MEAN)
    assert 0 <= result <= 1
    return result


def get_evidence_samples(element: elements.Element) -> int:
    """The total amount of evidence, both positive and negative, considered when determining the
    element's evidence mean."""
    result = element.get_data_key(EVIDENCE_SAMPLES_KEY, INITIAL_SAMPLES)
    assert result >= INITIAL_SAMPLES
    return result


def apply_evidence(element: elements.Element, value: float, samples: float = 1):
    """Apply evidence for or against the given graph element."""
    assert 0 <= value <= 1
    assert samples >= 0
    total_samples = get_evidence_samples(element) + samples
    mean = get_evidence_mean(element)
    mean += (value - mean) * samples / total_samples
    element.set_data_key(EVIDENCE_MEAN_KEY, mean)
    element.get_data_key(EVIDENCE_SAMPLES_KEY, total_samples)
