from abc import ABC, abstractmethod


class Exporter(ABC):
    @abstractmethod
    def export(self, text: str) -> bytes:
        pass