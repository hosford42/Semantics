import logging
import typing

import iso639

_logger = logging.getLogger(__name__)


class Language:
    """Unique language identifier"""

    def __init__(self, code: str):
        try:
            valid_code = iso639.to_iso639_2(code)
            if valid_code != code:
                _logger.info("Mapped language %s to ISO639-2/B code %s.", code, valid_code)
        except iso639.NonExistentLanguageError:
            valid_code = None
            _logger.warning("Unrecognized language: %s", code)
        self._code = valid_code or code
        self._valid = valid_code is not None

    def __repr__(self) -> str:
        return '%s(%r)' % (type(self).__name__, self._code)

    def __str__(self) -> str:
        return self._code

    def __getstate__(self):
        return self._code

    def __setstate__(self, code):
        self.__init__(code)

    def __eq__(self, other: 'Language') -> bool:
        if not isinstance(other, Language):
            return NotImplemented
        return self._code == other._code

    def __ne__(self, other: 'Language') -> bool:
        if not isinstance(other, Language):
            return NotImplemented
        return self._code != other._code

    def __hash__(self) -> int:
        return hash(self._code)

    @property
    def valid(self) -> bool:
        """Whether this language is a valid, ISO 639 language."""
        return self._valid

    @property
    def autonym(self) -> typing.Optional[str]:
        """The name of this language, as expressed in this language."""
        if self._valid:
            return iso639.to_native(self)
        else:
            return None

    @property
    def english_name(self) -> typing.Optional[str]:
        """The English name of this language."""
        if self._valid:
            return iso639.to_name(self)
        else:
            return None

    @property
    def iso639_2b(self) -> typing.Optional[str]:
        """The 3 letter ISO639-2/B code for this language."""
        if self._valid:
            return self._code
        else:
            return None

    @property
    def iso639_2t(self) -> typing.Optional[str]:
        """The 3 letter ISO639-2/T code for this language."""
        if self._valid:
            return iso639.to_iso639_2(self, 'T')
        else:
            return None

    @property
    def iso639_1(self) -> typing.Optional[str]:
        """The 2 letter ISO629-1 code for this language."""
        if self._valid:
            return iso639.to_iso639_1(self)
        else:
            return None
