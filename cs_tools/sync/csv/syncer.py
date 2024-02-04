from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Literal, Union
import csv
import logging
import pathlib

import pydantic

from cs_tools import utils
from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import Syncer

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class CSV(Syncer):
    """Interact with a CSV file."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "csv"

    directory: Union[pydantic.DirectoryPath, pydantic.NewPath]
    delimiter: str = "|"
    escape_character: str = "\\"
    quoting: Literal["ALL", "MINIMAL"] = "MINIMAL"
    date_time_format: str = sync_utils.DATETIME_FORMAT_TSLOAD
    header: bool = True
    save_strategy: Literal["APPEND", "OVERWRITE"] = "OVERWRITE"

    _written_header: dict[str, bool] = pydantic.PrivateAttr(default_factory=dict)
    """Whether or not the header has been written for a given file already"""

    @pydantic.field_validator("delimiter", "escape_character", mode="after")
    @classmethod
    def _only_single_characters_allowed(cls, value: str, info: pydantic.ValidationInfo) -> str:
        if len(value) > 1:
            raise ValueError(f"{info.field_name} must be a one-character string")
        return value

    @pydantic.field_validator("quoting", mode="after")
    @classmethod
    def _map_to_csv_literals(cls, value: str) -> str:
        return {"ALL": csv.QUOTE_ALL, "MINIMAL": csv.QUOTE_MINIMAL}.get(value)

    def dialect_and_format_parameters(self) -> dict[str, Any]:
        """The specification passed to csv.DictWriter"""
        # fmt: off
        parameters = {
            "delimiter": self.delimiter,
            # A one-character string used to separate fields.

            "doublequote": False,
            # When False, the escapechar is used as a prefix to the quotechar.

            "escapechar": self.escape_character,
            # A one-character string used by the writer to escape the delimiter if quoting is set to QUOTE_NONE and 
            # the quotechar if doublequote is False.

            "lineterminator": "\r\n",
            # The string used to terminate lines.

            "quotechar": '"',
            # A one-character string used to quote fields containing special characters, such as the delimiter or
            # quotechar, or which contain new-line characters.

            "quoting": self.quoting,
            # Controls when quotes should be generated by the writer and recognised by the reader.
            #
            #     QUOTE_ALL - quote all fields
            # QUOTE_MINIMAL - only quote those fields which contain special characters (ie. any chars defined above)
        }
        # fmt: on
        return parameters

    def __repr__(self):
        return f"<CSVSyncer path='{self.directory}' in '{self.save_strategy}' mode>"

    def read_stream(self, filename: str, *, batch: int = 100_000) -> Iterator[TableRows]:
        """Read rows from a CSV file in the directory."""
        path = self.directory.joinpath(f"{filename}.csv")

        if not path.exists():
            return iter([])

        with path.open(mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, **self.dialect_and_format_parameters())

            yield from utils.batched(reader, n=batch)

    # MANDATORY PROTOCOL MEMBERS

    def load(self, filename: str) -> TableRows:
        """Read rows from a CSV file in the directory."""
        path = self.directory.joinpath(f"{filename}.csv")

        if not path.exists():
            return []

        with path.open(mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, **self.dialect_and_format_parameters())
            data = list(reader)

        return data

    def dump(self, filename: str, *, data: TableRows) -> None:
        """Write rows to a CSV file in the directory."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        path = self.directory.joinpath(f"{filename}.csv")
        header = data[0].keys()
        mode = "a" if self.save_strategy == "APPEND" else "w"

        with path.open(mode=mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header, **self.dialect_and_format_parameters())

            if self.header and not self._written_header.get(filename, False):
                self._written_header[filename] = True
                writer.writeheader()

            writer.writerows([sync_utils.format_datetime_values(r, dt_format=self.date_time_format) for r in data])
