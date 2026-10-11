"""Independent primary-cell recognizer for exactly one direct-J instruction.

This module imports only shared immutable types, not an emitter or opcode table.
A decoded PROGRAM destination is metadata; no CPU, stack or RAM is instantiated.
"""

from direct_j_types import (
    DecodedDirectJ,
    DecodeErrorCode,
    DirectJDecodeError,
    DirectJDecodeRequest,
    ProgramTarget16,
)


def decode_direct_j(request):
    """Recognize exact immutable input after the sealed shape/context checks."""
    if type(request) is not DirectJDecodeRequest:
        return DirectJDecodeError(DecodeErrorCode.RequestShape)
    if not all(hasattr(request, name) for name in ("encoded_bytes", "origin_pc", "incoming_dd")):
        return DirectJDecodeError(DecodeErrorCode.RequestShape)
    payload = request.encoded_bytes
    if type(payload) is not bytes:
        return DirectJDecodeError(DecodeErrorCode.EncodedBytesInvalid)
    size = len(payload)
    if size == 0:
        return DirectJDecodeError(DecodeErrorCode.EncodedLengthInvalid)
    if size < 3:
        return DirectJDecodeError(DecodeErrorCode.TruncatedEncoding)
    if size > 3:
        return DirectJDecodeError(DecodeErrorCode.TrailingBytes)
    if type(request.incoming_dd) is not int or request.incoming_dd not in (0, 1):
        return DirectJDecodeError(DecodeErrorCode.IncomingDDInvalid)
    if type(request.origin_pc) is not int or not 0 <= request.origin_pc <= 65535:
        return DirectJDecodeError(DecodeErrorCode.OriginInvalid)
    end_exclusive = request.origin_pc + 3
    if end_exclusive > 65536:
        return DirectJDecodeError(DecodeErrorCode.OriginSpanOutsideProfile)
    # Independently transcribed J-address code cell, not learned from encoder.
    if payload[0] != 0x03:
        return DirectJDecodeError(DecodeErrorCode.UnsupportedEncoding)
    destination = payload[1] + 256 * payload[2]
    return DecodedDirectJ(
        ProgramTarget16(destination), request.origin_pc,
        request.incoming_dd, end_exclusive,
    )
