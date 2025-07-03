from abc import ABC, abstractmethod

class SchedulerPort(ABC):
    @abstractmethod
    def start(self):
        """Inicia o agendador de tarefas"""
        pass
