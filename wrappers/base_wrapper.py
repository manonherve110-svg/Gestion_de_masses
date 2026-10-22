from abc import ABC, abstractmethod
from typing import Any, Optional
from models.schema_global import Disease, Drug, Symptom


class BaseWrapper(ABC):
    """Interface de base pour tous les wrappers de données."""

    @abstractmethod
    def map_raw_to_drug(self, raw_data: Any) -> Optional[Drug]:
        raise NotImplementedError

    @abstractmethod
    def map_raw_to_disease(self, raw_data: Any) -> Optional[Disease]:
        raise NotImplementedError

    @abstractmethod
    def map_raw_to_symptom(self, raw_data: Any) -> Optional[Symptom]:
        raise NotImplementedError

    @abstractmethod
    def map_symptom_to_disease(self, raw_data: Any) -> Optional[Disease]:
        raise NotImplementedError

    @abstractmethod
    def map_disease_to_drug(self, raw_data: Any) -> Optional[Drug]:
        raise NotImplementedError
