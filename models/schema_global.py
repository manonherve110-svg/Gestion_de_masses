from dataclasses import dataclass, field
from typing import List


@dataclass
class Symptom:
    id: str
    name: str
    pertinence_score: float = 0.0
    clinical_score: float = 0.0

@dataclass
class Disease:
    id: str
    name: str
    symptoms: List[Symptom] = field(default_factory=list)
    treatments: List[str] = field(default_factory=list)
    pertinence_score: float = 0.0
    clinical_score: float = 0.0

@dataclass
class Drug:
    id: str
    name: str
    indications: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    pertinence_score: float = 0.0
    clinical_score: float = 0.0
