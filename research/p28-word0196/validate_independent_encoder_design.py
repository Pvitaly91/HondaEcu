"""M2ba static specification and INVENTED input-policy model, NOT an encoder.

No source parser, emitted bytes, execution, linking, placement or ROM interface.
Functional facts were independently read from the primary manufacturer manual.
The model returns admission metadata/errors only; JSON claims are not evidence.
"""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
BASE = "5c819e0f5675850050c5bc3a8e6301a66d448136"
MANUAL = "f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271"
EXPECTATIONS = "a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44"
# Own fixed form identifiers, not imported grammar/pattern/table indices.
# id, mnemonic, PDF/printed page, data width, DD, operand kinds, layout,
# invented operands, origin, STATIC primary-manual expected example bytes.
FACTS = [
    ("lb-a-page", "LB A,off N8", 124, "3-70", 8, "EitherSets0", ["AccumulatorA", "PageOffset8"], ["F4", "offset8"], [None, 55], 256, [244, 55]),
    ("sllb-a", "SLLB A", 197, "3-144", 8, "Requires0", ["AccumulatorA"], ["53"], [None], 256, [83]),
    ("rolb-page", "ROLB off N8", 173, "3-120", 8, "Independent", ["PageOffset8"], ["C4", "offset8", "B7"], [55], 256, [196, 55, 183]),
    ("lb-a-r0", "LB A,r0", 124, "3-70", 8, "EitherSets0", ["AccumulatorA", "Register0"], ["78"], [None, 0], 256, [120]),
    ("andb-a-page", "ANDB A,off N8", 76, "3-24", 8, "Requires0", ["AccumulatorA", "PageOffset8"], ["D7", "offset8"], [None, 55], 256, [215, 55]),
    ("cmp-page-imm16", "CMP off N8,#N16", 90, "3-38", 16, "Independent", ["EvenPageOffset8", "Immediate16"], ["B4", "offset8", "C0", "imm16Low", "imm16High"], [54, 42330], 256, [180, 54, 192, 90, 165]),
    ("jlt-rel8", "JLT rel8", 120, "3-66/3-67", None, "Independent", ["TargetPC16"], ["CA", "rel8"], [265], 256, [202, 7]),
    ("movb-r1-page", "MOVB r1,off N8", 153, "3-99", 8, "Independent", ["Register1", "PageOffset8"], ["C4", "offset8", "49"], [1, 55], 256, [196, 55, 73]),
    ("andb-page-a", "ANDB off N8,A", 77, "3-25", 8, "Independent", ["PageOffset8", "AccumulatorA"], ["C4", "offset8", "D1"], [55, None], 256, [196, 55, 209]),
    ("jbs-page-bit7", "JBS off N8.7,rel8", 119, "3-65", 8, "Independent", ["PageBit7", "TargetPC16"], ["EF", "offset8", "rel8"], [{"offset": 55, "bit": 7}, 508], 512, [239, 55, 249]),
    ("jbs-page-bit5", "JBS off N8.5,rel8", 119, "3-65", 8, "Independent", ["PageBit5", "TargetPC16"], ["ED", "offset8", "rel8"], [{"offset": 55, "bit": 5}, 778], 768, [237, 55, 7]),
    ("orb-page-imm8", "ORB off N'8,#N8", 163, "3-110", 8, "Independent", ["PageOffset8", "Immediate8"], ["C4", "offset8", "E0", "imm8"], [55, 166], 256, [196, 55, 224, 166]),
    ("orb-a-imm8", "ORB A,#N8", 160, "3-107", 8, "Requires0", ["AccumulatorA", "Immediate8"], ["E6", "imm8"], [None, 166], 256, [230, 166]),
    ("lb-a-imm8", "LB A,#N8", 124, "3-70", 8, "EitherSets0", ["AccumulatorA", "Immediate8"], ["77", "imm8"], [None, 166], 256, [119, 166]),
    ("stb-a-page", "STB A,off N8", 208, "3-155", 8, "Requires0", ["AccumulatorA", "PageOffset8"], ["D4", "offset8"], [None, 55], 256, [212, 55]),
]
ERRORS = ["RequestShape", "UnsupportedForm", "IncomingDDInvalid", "WrongDD", "OriginInvalid",
          "OriginSpanOutsideProfile", "OperandCount", "OperandKind", "OperandShape", "OperandRange",
          "FixedOperandMismatch", "OddWordOffsetOutsideProfile", "Rel8OutOfRange"]


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def example_request(fact, dd=0):
    operands = []
    for kind, value in zip(fact[6], fact[8]):
        if kind == "AccumulatorA":
            operands.append({"kind": kind})
        elif kind.startswith("PageBit"):
            operands.append(dict(kind=kind, **value))
        else:
            operands.append(dict(kind=kind, value=value))
    return dict(reviewedFormId=fact[0], typedOperands=operands, incomingDD=dd, originPC=fact[9])


def profile():
    forms = []
    for f in FACTS:
        relative = "rel8" in f[7]
        forms.append(dict(reviewedFormId=f[0], mnemonic=f[1], pdfPage=f[2], printedPage=f[3],
                          dataWidth=f[4], incomingDD=f[5], operandOrder=f[6], components=f[7],
                          expectedLength=len(f[10]), evidenceSourceSha256=MANUAL,
                          relativeArithmetic="targetPC-(originPC+instructionLength);signed[-128,127];twoComplement8" if relative else None,
                          positiveSyntheticExample=dict(request=example_request(f), staticExpectedBytes=f[10]),
                          negativeCases=["unknownForm", "wrongOperandKind", "wrongOperandCount", "invalidIncomingDD", "originSpanOverflow"]
                          + (["wrongDD"] if f[5] == "Requires0" else [])
                          + (["rel8BelowMinus128", "rel8Above127", "nextPCWrap"] if relative else [])
                          + (["oddWordOffsetProfileRefusal", "imm16Overflow", "bigEndianExpectation"] if f[0] == "cmp-page-imm16" else [])))
    return dict(schemaVersion=1, milestone="M2ba", exactBase=BASE,
                route="PrimaryManualDerivedIndependentEncoderRoute",
                status="SpecificationEstablished;ImplementationNotStarted", legalCleanRoomClaim=False,
                conceptualInterface="EncodeInstruction(reviewedFormId,typedOperands,incomingDD,originPC) -> EncodedInstruction | ExplicitError",
                sources=dict(manual="Oki_66201_Instruction_Manual.pdf", edition="September1991", sha256=MANUAL,
                             independentlyReviewedM2ayExpectationsSha256=EXPECTATIONS,
                             implementationInputs=["PrimaryManufacturerFunctionalFacts", "IndependentPrimaryExpectationLedger"],
                             excludedInputs=["ASM662Source", "ASM662Grammar", "ASM662Generators", "DocDerivedTables", "RustDecoderOutput", "CSharpExecutorOutput"],
                             priorThirdPartySourceExposureDisclosed=True, arrangement="OwnFixedFormIdentifiersAndTypedSpecification"),
                operandTypes=dict(AccumulatorA="FixedA;no value field", Register0="Exact0", Register1="Exact1",
                                  PageOffset8="RawOffsetInteger0..255;notDATA16;noLRBconversion",
                                  EvenPageOffset8="Even0..254;conservativeProfileOnly;CPUAlignsOddWordAddressDown",
                                  Immediate8="Integer0..255", Immediate16="Integer0..65535;lowByteFirst",
                                  PageBit7="RawOffset0..255AndExactBit7", PageBit5="RawOffset0..255AndExactBit5",
                                  TargetPC16="Integer0..65535;explicitTargetNotLabel"),
                policies=dict(incomingDD="ExactInteger0Or1;unknownRejected", originPC="ExactInteger0..65535",
                              instructionExtent="origin+length<=65536;lastByteMayBeFFFF",
                              relativeBoundary="NoWrapProfile;nextPC<=65535;linearSignedDifference;noModuloRepair",
                              wordAlignmentReference=dict(pdfPage=22, printedPage="1-18", rule="CPUWordReadAlignsDown;OddOffsetRefusalIsEncoderProfileRestrictionNotISAIllegal"),
                              littleEndianReference=dict(pdfPage=9, printedPage="1-5"),
                              lbDD="EitherIncoming;ExecutedLBsetsDD0;encodingDoesNotExecuteOrMutateContext",
                              output="FutureExactLengthOnly;noZeroDefaultPaddingOrTruncation",
                              errorCodes=ERRORS,
                              operandValidationOrder="LeftToRight;kindThenShapeThenRangeThenFixedValueThenAlignmentThenRelative;errorCodesDoNotDeclareGlobalCrossOperandPriority",
                              unsupported="Reject;noDerivedFallback"),
                exactForms=forms, knownLimits=["ROLBWordLongDescriptionTypo;ByteHeadingAndCodeTableUsed", "JGT_C8ConflictUnresolvedOutsideScope", "ADDer3_A_4781PrimaryMissingOutsideScope", "PrimedNInORBIsSeparateVariableNotNewAddressMode"],
                futureVerification=dict(inventedOnly=True, boundaryValues=[0, 1, 127, 128, 254, 255, 256, 65535, 65536],
                                        rel8Boundaries=[-129, -128, -1, 0, 127, 128],
                                        primaryStaticExamples=15, byteComparison="FutureEmittedBytesVersusSealedPrimaryExpectations;NotPerformed",
                                        independentReviewRequired=True, rejectOutputOnError=True,
                                        semanticReplacementGates=["Flags", "CPUContext", "RegisterAllocation", "MemoryWrites", "ControlFlow", "ActualTargetExecutionEquivalence"]),
                exclusions=dict(encoderImplemented=False, assemblerExecutions=0, generatorExecutions=0,
                                actualRomExecutions=0, targetBytes=0, targetAssemblyFiles=0, targetObjects=0,
                                firmwareBin=0, runtimeVerified=False, noPreload=True, noRomInput=True, noLinker=True,
                                noMemoryPlacement=True, noCompilerAbiAssumption=True, noFirmwareOutput=True,
                                noNativeFragmentReplacement=True, noProductionChange=True),
                nextMilestone="ImplementOwn15FormTypedInstructionEncoderAndInventedPrimaryVectorTestsOnly;SeparateAuthorizationRequired")


def validate(record):
    demand(equal(record, profile()), "Not the exact primary-reviewed M2ba design; input claims cannot establish an encoder")
    return dict(milestone="M2ba", domain="EncoderDesign", passed=True, forms=15,
                encoderImplemented=False, runtimeVerified=False, actualRomExecutions=0,
                assemblerExecutions=0, targetBytes=0, firmwareBin=0)


def parse_contract(raw):
    demand(type(raw) is bytes and len(raw) <= 65536, "BoundedUTF8Required")
    def pairs(items):
        result = {}
        for key, value in items:
            demand(key not in result, "DuplicateKey")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("NonFiniteJSON:" + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant)


def specification_request_model(request):
    """Invented policy model only: metadata or error; NEVER produces bytes."""
    def error(code):
        return dict(status="ExplicitError", code=code)
    if type(request) is not dict or set(request) != {"reviewedFormId", "typedOperands", "incomingDD", "originPC"}:
        return error("RequestShape")
    form_id = request["reviewedFormId"]
    fact = next((f for f in FACTS if type(form_id) is str and f[0] == form_id), None)
    if fact is None:
        return error("UnsupportedForm")
    dd = request["incomingDD"]
    if type(dd) is not int or dd not in (0, 1):
        return error("IncomingDDInvalid")
    if fact[5] == "Requires0" and dd != 0:
        return error("WrongDD")
    origin = request["originPC"]
    if type(origin) is not int or not 0 <= origin <= 65535:
        return error("OriginInvalid")
    length = len(fact[10])
    relative = "rel8" in fact[7]
    if origin + length > (65535 if relative else 65536):
        return error("OriginSpanOutsideProfile")
    operands = request["typedOperands"]
    if type(operands) is not list or len(operands) != len(fact[6]):
        return error("OperandCount")
    displacement = None
    for operand, kind in zip(operands, fact[6]):
        if type(operand) is not dict or operand.get("kind") != kind or type(operand.get("kind")) is not str:
            return error("OperandKind")
        keys = {"kind"} if kind == "AccumulatorA" else {"kind", "offset", "bit"} if kind.startswith("PageBit") else {"kind", "value"}
        if set(operand) != keys:
            return error("OperandShape")
        if kind == "AccumulatorA":
            continue
        if kind.startswith("PageBit"):
            if type(operand["offset"]) is not int or not 0 <= operand["offset"] <= 255:
                return error("OperandRange")
            if type(operand["bit"]) is not int or operand["bit"] != int(kind[-1]):
                return error("FixedOperandMismatch")
            continue
        value = operand["value"]
        maximum = 65535 if kind in ("Immediate16", "TargetPC16") else 255
        if type(value) is not int or not 0 <= value <= maximum:
            return error("OperandRange")
        if kind.startswith("Register") and value != int(kind[-1]):
            return error("FixedOperandMismatch")
        if kind == "EvenPageOffset8" and value % 2:
            return error("OddWordOffsetOutsideProfile")
        if kind == "TargetPC16":
            displacement = value - (origin + length)
            if not -128 <= displacement <= 127:
                return error("Rel8OutOfRange")
    return dict(status="SpecificationAccepts", expectedLength=length, displacement=displacement,
                executionDDPostcondition=0 if fact[5] == "EitherSets0" else dd)


if __name__ == "__main__":
    try:
        record = parse_contract(Path(__file__).with_name("independent_encoder_design.json").read_bytes())
        print(json.dumps(validate(record), sort_keys=True))
    except (ValueError, TypeError, OSError, RecursionError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
