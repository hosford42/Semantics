"""
Utilities for dealing with evidence.
"""
from dataclasses import dataclass

from semantics.graph_layer import elements


# Keys used to look up evidence in the element's data dictionary.
EVIDENCE_MEAN_KEY = 'EV_MEAN'
EVIDENCE_SAMPLES_KEY = 'EV_SAMPLES'

# Together, the initial mean and initial samples implement additive smoothing (aka Laplacian
# smoothing) of the evidence.
INITIAL_MEAN = 0.5
INITIAL_SAMPLES = 1.0


@dataclass
class Evidence:
    """A data class for representing the evidence for/against the existence of an element."""
    mean: float
    samples: float

    def __bool__(self) -> bool:
        """Treat the evidence as a boolean value by rounding its mean."""
        return self.mean > 0.5

    def update(self, other: 'Evidence') -> None:
        """Update this evidence by incorporating the other evidence."""
        self.samples += other.samples
        self.mean += (other.mean - self.mean) * other.samples / self.samples


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


def get_evidence(element: elements.Element) -> Evidence:
    """Get the evidence for/against the existence of an element. Returns an Evidence instance."""
    mean = get_evidence_mean(element)
    samples = get_evidence_samples(element)
    return Evidence(mean, samples)


def update_evidence(element: elements.Element, new_evidence: Evidence) -> None:
    evidence = get_evidence(element)
    evidence.update(new_evidence)
    element.set_data_key(EVIDENCE_MEAN_KEY, evidence.mean)
    element.set_data_key(EVIDENCE_SAMPLES_KEY, evidence.samples)


def apply_evidence(element: elements.Element, value: float, samples: float = 1) -> None:
    """Apply evidence for or against the given graph element."""
    if not 0 <= value <= 1:
        raise ValueError(value)
    if samples < 0:
        raise ValueError(samples)
    new_evidence = Evidence(value, samples)
    update_evidence(element, new_evidence)
