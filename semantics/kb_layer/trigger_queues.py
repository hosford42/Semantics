import typing

if typing.TYPE_CHECKING:
    import semantics.kb_layer.interface as kb_interface


class TriggerQueue:

    def __init__(self, kb: 'kb_interface.KnowledgeBaseInterface'):
        self._kb = kb

    @property
    def pending(self) -> bool:
        """Whether there are pending trigger events that need to be processed."""
        raise NotImplementedError()

    def process_one(self) -> bool:
        """If there are pending trigger events, process the first one. Return whether an event
        was processed or not."""
        raise NotImplementedError()

    def process_all(self) -> int:
        """Process all pending trigger events, returning the number of processed events upon
        completion."""
        count = 0
        while self.process_one():
            count += 1
        return count
