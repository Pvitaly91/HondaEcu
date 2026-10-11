"""Closed immutable research types for one synthetic direct PROGRAM jump.

These definitions contain no opcode table, execution state or output interface.
Constructors intentionally do not coerce or validate input: the pure APIs return
their own explicit, atomic errors for malformed requests.
"""

from dataclasses import dataclass, field
from enum import Enum, unique


@unique
class DirectJForm(Enum):
    J_ADDRESS = "j-address"


@unique
class EncodeErrorCode(Enum):
    RequestShape = "RequestShape"
    TargetTypeInvalid = "TargetTypeInvalid"
    TargetOutOfRange = "TargetOutOfRange"
    IncomingDDInvalid = "IncomingDDInvalid"
    OriginInvalid = "OriginInvalid"
    OriginSpanOutsideProfile = "OriginSpanOutsideProfile"


@unique
class DecodeErrorCode(Enum):
    RequestShape = "RequestShape"
    EncodedBytesInvalid = "EncodedBytesInvalid"
    EncodedLengthInvalid = "EncodedLengthInvalid"
    TruncatedEncoding = "TruncatedEncoding"
    TrailingBytes = "TrailingBytes"
    IncomingDDInvalid = "IncomingDDInvalid"
    OriginInvalid = "OriginInvalid"
    OriginSpanOutsideProfile = "OriginSpanOutsideProfile"
    UnsupportedEncoding = "UnsupportedEncoding"


@dataclass(frozen=True, slots=True)
class ProgramTarget16:
    value: int


@dataclass(frozen=True, slots=True)
class DirectJEncodeRequest:
    target: ProgramTarget16
    origin_pc: int
    incoming_dd: int


@dataclass(frozen=True, slots=True)
class DirectJDecodeRequest:
    encoded_bytes: bytes
    origin_pc: int
    incoming_dd: int


@dataclass(frozen=True, slots=True)
class EncodedDirectJ:
    target: ProgramTarget16
    origin_pc: int
    incoming_dd: int
    encoded_bytes: bytes
    form: DirectJForm = field(default=DirectJForm.J_ADDRESS, init=False)
    length: int = field(default=3, init=False)
    end_exclusive: int
    pc_effect: str = field(default="DocumentedPCReplacement", init=False)
    dd_effect: str = field(default="DocumentedDDPreservedWhenExecuted", init=False)
    noninterference_scope: str = field(
        default="ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence",
        init=False,
    )
    classification: str = field(default="SyntheticDirectJEncodingOnly", init=False)


@dataclass(frozen=True, slots=True)
class DecodedDirectJ:
    target: ProgramTarget16
    origin_pc: int
    incoming_dd: int
    form: DirectJForm = field(default=DirectJForm.J_ADDRESS, init=False)
    length: int = field(default=3, init=False)
    end_exclusive: int
    pc_effect: str = field(default="DocumentedPCReplacement", init=False)
    dd_effect: str = field(default="DocumentedDDPreservedWhenExecuted", init=False)
    noninterference_scope: str = field(
        default="ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence",
        init=False,
    )
    classification: str = field(default="SyntheticDirectJDecodingOnly", init=False)


@dataclass(frozen=True, slots=True)
class DirectJEncodeError:
    code: EncodeErrorCode


@dataclass(frozen=True, slots=True)
class DirectJDecodeError:
    code: DecodeErrorCode
