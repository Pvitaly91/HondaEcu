"""Primary-derived single-instruction direct-J encoder, never a stream emitter.

MSM66201 Instruction Manual (September1991), printed3-62/physical116:
the independently reviewed code cells are 03, adrL, adrH. The manual's
function and flag table are documentary metadata, not runtime authority.
"""

from direct_j_types import (
    DirectJEncodeError,
    DirectJEncodeRequest,
    EncodedDirectJ,
    EncodeErrorCode,
    ProgramTarget16,
)


def encode_direct_j(request):
    """Validate the sealed order completely before constructing three bytes."""
    if type(request) is not DirectJEncodeRequest:
        return DirectJEncodeError(EncodeErrorCode.RequestShape)
    if not all(hasattr(request, name) for name in ("target", "origin_pc", "incoming_dd")):
        return DirectJEncodeError(EncodeErrorCode.RequestShape)
    target = request.target
    if type(target) is not ProgramTarget16 or not hasattr(target, "value"):
        return DirectJEncodeError(EncodeErrorCode.TargetTypeInvalid)
    value = target.value
    if type(value) is not int:
        return DirectJEncodeError(EncodeErrorCode.TargetTypeInvalid)
    if not 0 <= value <= 65535:
        return DirectJEncodeError(EncodeErrorCode.TargetOutOfRange)
    if type(request.incoming_dd) is not int or request.incoming_dd not in (0, 1):
        return DirectJEncodeError(EncodeErrorCode.IncomingDDInvalid)
    if type(request.origin_pc) is not int or not 0 <= request.origin_pc <= 65535:
        return DirectJEncodeError(EncodeErrorCode.OriginInvalid)
    end_exclusive = request.origin_pc + 3
    if end_exclusive > 65536:
        return DirectJEncodeError(EncodeErrorCode.OriginSpanOutsideProfile)
    # Independent primary code-cell implementation: no decoder/oracle/table call.
    encoded = bytes((0x03, value & 0xFF, (value >> 8) & 0xFF))
    return EncodedDirectJ(
        target, request.origin_pc, request.incoming_dd, encoded, end_exclusive,
    )
