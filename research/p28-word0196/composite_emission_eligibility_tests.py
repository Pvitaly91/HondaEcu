"""Frozen-API M2bi tests; oracle predates planner, final tests may follow authoring.

Tests use only independent literal expectations and published immutable contracts.
No new planner source/output is used to author this suite. Codecs, typed codec
objects, target bytes, streams, CPU and ROM are never constructed or invoked.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys

from composite_emission_eligibility_oracle import (
    ROWS, J_NB, J_BELOW, expected_plan, geometry_reason, positions, summary,
)

HERE = Path(__file__).resolve().parent
DOMAINS = ((0,), (1,), (0, 1))
MANDATORY_LABEL_COUNT = 50
CASES = [{"label": "WrongSourceSHA", "expectedCode": "SourceIdentityMismatch", "domain": "SourceIdentity", "patches": [{"op": "set", "path": ["eligibility", "upstreamBindings", 0, "sha256"], "value": "0000000000000000000000000000000000000000000000000000000000000000"}]}, {"label": "MissingSourceBinding", "expectedCode": "SourceBindingMissing", "domain": "SourceIdentity", "patches": [{"op": "delete", "path": ["eligibility", "upstreamBindings", 0]}]}, {"label": "WrongM2bbCodecRoute", "expectedCode": "CodecRouteMismatch", "domain": "Routing", "patches": [{"op": "set", "path": ["eligibility", "routes", "A", "function"], "value": "encode_direct_j"}]}, {"label": "WrongDirectJCodecRoute", "expectedCode": "CodecRouteMismatch", "domain": "Routing", "patches": [{"op": "set", "path": ["eligibility", "routes", "B", "module"], "value": "independent_encoder"}]}, {"label": "MissingOriginalNode", "expectedCode": "NodeInventoryMismatch", "domain": "Inventory", "patches": [{"op": "delete", "path": ["eligibility", "typedRequestMapping", 0]}]}, {"label": "DuplicateOriginalNode", "expectedCode": "NodeInventoryMismatch", "domain": "Inventory", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 1, "nodeId"], "value": 21871}]}, {"label": "MissingDirectJSlot", "expectedCode": "NodeInventoryMismatch", "domain": "Inventory", "patches": [{"op": "delete", "path": ["eligibility", "typedRequestMapping", 15]}]}, {"label": "ThirdTransferSlot", "expectedCode": "NodeInventoryMismatch", "domain": "Inventory", "patches": [{"op": "duplicate", "path": ["eligibility", "typedRequestMapping", 15]}]}, {"label": "WrongBlockOrder", "expectedCode": "ComponentPlanMismatch", "domain": "InheritedPlan", "patches": [{"op": "reverse", "path": ["composition", "componentPlan"]}]}, {"label": "WrongTypedOperand", "expectedCode": "OperandKind", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "operandDescriptors", 1, "kind"], "value": "Immediate8"}]}, {"label": "PageOffset8ReplacedDATA16", "expectedCode": "OperandKind", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "operandDescriptors", 1, "kind"], "value": "DATA16"}]}, {"label": "WrongWordWidth", "expectedCode": "OperandKind", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 5, "operandDescriptors", 1, "kind"], "value": "Immediate8"}]}, {"label": "CMPImmediate00C0Changed", "expectedCode": "OperandValueMismatch", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 5, "operandDescriptors", 1, "fields", "value"], "value": 193}]}, {"label": "OddCMPPageOffset", "expectedCode": "OddWordOffsetOutsideProfile", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 5, "operandDescriptors", 0, "fields", "value"], "value": 151}]}, {"label": "OriginalPCAsRelocatedOrigin", "expectedCode": "OriginProjectionMismatch", "domain": "OriginMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "originOffset"], "value": 17775}]}, {"label": "MissingAssignedPC", "expectedCode": "AssignmentInventory", "domain": "GeometryAssignment", "patches": [{"op": "canonicalAssignments"}, {"op": "delete", "path": ["request", "nodeAssignments", 0, "assignedPC"]}]}, {"label": "WrongInstructionLength", "expectedCode": "InstructionLengthMismatch", "domain": "Length", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 5, "plannedLength"], "value": 4}]}, {"label": "WrongDDAt5571", "expectedCode": "DDProjectionMismatch", "domain": "DDProjection", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 1, "incomingDDDomain"], "value": [1]}]}, {"label": "MissingLBReset", "expectedCode": "DDRequirementViolation", "domain": "InheritedDD", "patches": [{"op": "delete", "path": ["ir", "instructions", 0, "effects", 2]}, {"op": "delete", "path": ["composition", "originalIRInstructions", 0, "effects", 2]}]}, {"label": "WrongJLTTarget", "expectedCode": "BranchTargetMismatch", "domain": "BranchMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 6, "relocatedTargetNodeId"], "value": 21906}]}, {"label": "OldJLT64Reused", "expectedCode": "BranchTargetMismatch", "domain": "BranchMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 6, "operandDescriptors", 0, "fields", "value"], "value": 4176}]}, {"label": "JBSChangedTarget", "expectedCode": "BranchTargetMismatch", "domain": "BranchMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 9, "relocatedTargetNodeId"], "value": 21951}]}, {"label": "IncorrectRel8Boundary", "expectedCode": "Rel8OutOfRange", "domain": "ActualGeometry", "patches": [{"op": "set", "path": ["request", "gap"], "value": 102}]}, {"label": "DirectJSubjectToRel8", "expectedCode": "CodecRouteMismatch", "domain": "RoutingPolicy_NotStandaloneRangeProof", "patches": [{"op": "set", "path": ["eligibility", "routes", "B", "signedRel8Restriction"], "value": True}]}, {"label": "NotBelowJTargets55C5", "expectedCode": "ContinuationMismatch", "domain": "TypedContinuation", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 15, "operandDescriptors", 0, "fields", "value"], "value": 21957}]}, {"label": "BelowJTargets5596", "expectedCode": "ContinuationMismatch", "domain": "TypedContinuation", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 19, "operandDescriptors", 0, "fields", "value"], "value": 21910}]}, {"label": "BothJsSameTarget", "expectedCode": "ContinuationMismatch", "domain": "TypedContinuation", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 15, "operandDescriptors", 0, "fields", "value"], "value": 24576}, {"op": "set", "path": ["eligibility", "typedRequestMapping", 19, "operandDescriptors", 0, "fields", "value"], "value": 24576}]}, {"label": "TransferBeforeFinalRAMWrite", "expectedCode": "InstructionOverlap", "domain": "ActualGeometry", "patches": [{"op": "canonicalAssignments"}, {"op": "set", "path": ["request", "nodeAssignments", 19, "assignedPC"], "value": 4141}]}, {"label": "NotBelowFallsIntoBelow", "expectedCode": "CFGRelationMismatch", "domain": "InheritedCFG", "patches": [{"op": "set", "path": ["composition", "composedCFG", 21, "kind"], "value": "Fallthrough"}, {"op": "set", "path": ["composition", "composedCFG", 21, "to"], "value": 21951}]}, {"label": "MissingBranchEdge", "expectedCode": "CFGRelationMismatch", "domain": "InheritedCFG", "patches": [{"op": "delete", "path": ["composition", "composedCFG", 6]}]}, {"label": "AddedHiddenBranch", "expectedCode": "CFGRelationMismatch", "domain": "InheritedCFG", "patches": [{"op": "append", "path": ["composition", "composedCFG"], "value": {"from": 21885, "to": "DirectJ_NotBelow", "kind": "ConditionalTaken", "predicate": {"kind": "FlagEquals", "flag": "CF", "value": 1}}}]}, {"label": "AddedStackPrologue", "expectedCode": "TransferSpecificationMismatch", "domain": "InheritedTransferEffects", "patches": [{"op": "set", "path": ["composition", "abstractTransfers", 0, "stackWrites"], "value": ["SSP"]}]}, {"label": "AddedRAMPointerRead", "expectedCode": "TransferSpecificationMismatch", "domain": "InheritedTransferEffects", "patches": [{"op": "set", "path": ["composition", "abstractTransfers", 0, "functionalDATAReads"], "value": [399]}]}, {"label": "AddedDATAWriter", "expectedCode": "TransferSpecificationMismatch", "domain": "InheritedTransferEffects", "patches": [{"op": "set", "path": ["composition", "abstractTransfers", 0, "DATAWrites"], "value": [399]}]}, {"label": "ChangedSCBLRB", "expectedCode": "ContextObligationMismatch", "domain": "InheritedContext", "patches": [{"op": "set", "path": ["composition", "context", "requiredLRB"], "value": 32}]}, {"label": "LostSameValueStore", "expectedCode": "MemoryEffectMismatch", "domain": "InheritedOrderedEffects", "patches": [{"op": "set", "path": ["ir", "instructions", 17, "effects", 0, "sameValueWrite"], "value": "Suppress"}, {"op": "set", "path": ["composition", "originalIRInstructions", 17, "effects", 0, "sameValueWrite"], "value": "Suppress"}]}, {"label": "GateOrderChanged", "expectedCode": "CFGRelationMismatch", "domain": "InheritedCFG", "patches": [{"op": "set", "path": ["composition", "composedCFG", 10, "from"], "value": 21896}, {"op": "set", "path": ["composition", "composedCFG", 12, "from"], "value": 21893}]}, {"label": "Forced0124ReadOnB", "expectedCode": "MemoryEffectMismatch", "domain": "InheritedActualExtraRead", "patches": [{"op": "insert", "path": ["ir", "instructions", 9, "effects"], "index": 0, "value": {"op": "LoadAccumulatorLow", "type": "u8", "source": {"kind": "CurrentPageRam", "address": 292, "widthBits": 8, "selectorField": "n8", "requiredLrb": 33, "byteOrder": "NotApplicable"}, "extension": "None", "preserveHighByte": True}}, {"op": "insert", "path": ["composition", "originalIRInstructions", 9, "effects"], "index": 0, "value": {"op": "LoadAccumulatorLow", "type": "u8", "source": {"kind": "CurrentPageRam", "address": 292, "widthBits": 8, "selectorField": "n8", "requiredLrb": 33, "byteOrder": "NotApplicable"}, "extension": "None", "preserveHighByte": True}}]}, {"label": "Path13ClaimedNativeValidated", "expectedCode": "MetadataMismatch", "domain": "HistoricalMetadata", "patches": [{"op": "set", "path": ["composition", "paths", 2, "originalPath", "historical"], "value": "HistoricalNativeValidated"}]}, {"label": "GapTreatedFilledProgram", "expectedCode": "RuntimePolicyMismatch", "domain": "FutureOutputPolicy", "patches": [{"op": "set", "path": ["eligibility", "allowedSyntheticGeometry", "unmodeledGapExecutable"], "value": True}]}, {"label": "UnknownROMClaimedFree", "expectedCode": "RuntimePolicyMismatch", "domain": "PlacementMetadata", "patches": [{"op": "set", "path": ["eligibility", "allowedSyntheticGeometry", "physicalPlacementAuthorized"], "value": True}]}, {"label": "SyntheticBytesClaimedProductionFirmware", "expectedCode": "RuntimePolicyMismatch", "domain": "RuntimeMetadata", "patches": [{"op": "set", "path": ["eligibility", "runtimeExclusions", "CompositeMachineCode"], "value": "ProductionFirmwareGenerated"}]}, {"label": "MissingIndependentVerifier", "expectedCode": "FuturePrimaryVerificationMismatch", "domain": "FutureVerifierPolicy", "patches": [{"op": "set", "path": ["eligibility", "futurePrimaryVerification", "ruleInventory"], "value": []}, {"op": "set", "path": ["eligibility", "futurePrimaryVerification", "ruleCount"], "value": 0}]}, {"label": "OutputAllowedAfterCodecError", "expectedCode": "AtomicityPolicyMismatch", "domain": "FutureAtomicityPolicy", "patches": [{"op": "set", "path": ["eligibility", "atomicity", "codecErrors"], "value": "ContinueAndPublishPartial"}]}, {"label": "PartialCompositeBufferSuccess", "expectedCode": "AtomicityPolicyMismatch", "domain": "FutureAtomicityPolicy", "patches": [{"op": "set", "path": ["eligibility", "atomicity", "noPartialSuccess"], "value": False}]}, {"label": "UnexpectedPadding", "expectedCode": "AtomicityPolicyMismatch", "domain": "FutureAtomicityPolicy", "patches": [{"op": "set", "path": ["eligibility", "atomicity", "noPadding"], "value": False}]}, {"label": "Declared51WrongFormLengths", "expectedCode": "InstructionLengthMismatch", "domain": "ExactFormLength", "patches": [{"op": "set", "path": ["eligibility", "exactForms", 5, "length"], "value": 4}]}, {"label": "RuntimePermissionPromoted", "expectedCode": "RuntimePolicyMismatch", "domain": "RuntimeMetadata", "patches": [{"op": "set", "path": ["eligibility", "runtimeExclusions", "runtimePermission"], "value": True}]}, {"label": "NativeExitVerifiedFabricated", "expectedCode": "RuntimePolicyMismatch", "domain": "RuntimeMetadata", "patches": [{"op": "set", "path": ["eligibility", "runtimeExclusions", "NativeExitIsolation"], "value": "Verified"}]}, {"label": "TargetEquivalenceVerifiedFabricated", "expectedCode": "RuntimePolicyMismatch", "domain": "RuntimeMetadata", "patches": [{"op": "set", "path": ["eligibility", "runtimeExclusions", "TargetProgramEquivalence"], "value": "Verified"}]}, {"label": "UnknownRoute", "expectedCode": "CodecRouteMismatch", "domain": "Routing", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 1, "routeId"], "value": "Unknown"}]}, {"label": "DirectJInOldFormId", "expectedCode": "UnsupportedForm", "domain": "Form", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "formId"], "value": "j-address"}]}, {"label": "UnsupportedSJForJSlot", "expectedCode": "UnsupportedForm", "domain": "Form", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 15, "formId"], "value": "sj-address"}]}, {"label": "ProgramTargetReplacedTargetPC", "expectedCode": "OperandKind", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 15, "operandDescriptors", 0, "kind"], "value": "TargetPC16"}]}, {"label": "AccumulatorHasIllegalValueSlot", "expectedCode": "OperandShape", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "operandDescriptors", 0, "fields", "value"], "value": 0}]}, {"label": "Register0WrongFixedValue", "expectedCode": "FixedOperandMismatch", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 3, "operandDescriptors", 1, "fields", "value"], "value": 1}]}, {"label": "Register1WrongFixedValue", "expectedCode": "FixedOperandMismatch", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 7, "operandDescriptors", 0, "fields", "value"], "value": 0}]}, {"label": "Bit7WrongFixedBit", "expectedCode": "FixedOperandMismatch", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 9, "operandDescriptors", 0, "fields", "bit"], "value": 6}]}, {"label": "OffsetBoolNotInt", "expectedCode": "OperandShape", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "operandDescriptors", 1, "fields", "value"], "value": True}]}, {"label": "OffsetNegative", "expectedCode": "OperandRange", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "operandDescriptors", 1, "fields", "value"], "value": -1}]}, {"label": "Offset256", "expectedCode": "OperandRange", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "operandDescriptors", 1, "fields", "value"], "value": 256}]}, {"label": "Immediate16Overflow", "expectedCode": "OperandRange", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 5, "operandDescriptors", 1, "fields", "value"], "value": 65536}]}, {"label": "EvenCMP255Odd", "expectedCode": "OddWordOffsetOutsideProfile", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 5, "operandDescriptors", 0, "fields", "value"], "value": 255}]}, {"label": "ProgramTargetOverflow", "expectedCode": "OperandRange", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 15, "operandDescriptors", 0, "fields", "value"], "value": 65536}]}, {"label": "CorrectShapeWrongReviewedOffset", "expectedCode": "OperandValueMismatch", "domain": "TypedMapping", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "operandDescriptors", 1, "fields", "value"], "value": 143}]}, {"label": "MappingRowMissingLength", "expectedCode": "InputShape", "domain": "Shape", "patches": [{"op": "delete", "path": ["eligibility", "typedRequestMapping", 1, "plannedLength"]}]}, {"label": "SlotForgedOriginalIdentity", "expectedCode": "NodeInventoryMismatch", "domain": "Inventory", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 15, "originalLogicalSiteId"], "value": 21910}]}, {"label": "OriginalForgedAbstractKind", "expectedCode": "NodeInventoryMismatch", "domain": "Inventory", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "nodeKind"], "value": "AbstractTransferSlot"}]}, {"label": "SuccessorChangedOnlyInTypedMapping", "expectedCode": "CFGRelationMismatch", "domain": "MappedCFG", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "successorIds"], "value": [21874]}]}, {"label": "PrimaryPageChanged", "expectedCode": "PrimaryEvidenceMismatch", "domain": "PrimaryMetadata", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "primary", "pdfPage"], "value": 123}]}, {"label": "FutureDecodeVerifierMissing", "expectedCode": "FutureDecodeVerificationMismatch", "domain": "FutureDecodePolicy", "patches": [{"op": "set", "path": ["eligibility", "futureDecodeVerification", "noTrailing"], "value": False}]}, {"label": "FutureEffectVerifierDropsWrites", "expectedCode": "EffectVerificationPolicyMismatch", "domain": "FutureEffectsPolicy", "patches": [{"op": "set", "path": ["eligibility", "futureOrderedEffectsVerification", "preserveFullOrderedWrites"], "value": False}]}, {"label": "NewInheritedContextRebased", "expectedCode": "ContextObligationMismatch", "domain": "StaticContextPolicy", "patches": [{"op": "set", "path": ["eligibility", "inheritedContextAndEffectObligations", "context", "requiredLRB"], "value": 0}]}, {"label": "MatrixMayPromoteRuntime", "expectedCode": "RuntimePolicyMismatch", "domain": "DecisionPolicy", "patches": [{"op": "set", "path": ["eligibility", "decisionMatrix", "runtimePermissions"], "value": True}]}, {"label": "FalseEditableEligibilityTag", "expectedCode": "MetadataMismatch", "domain": "Metadata", "patches": [{"op": "set", "path": ["eligibility", "eligibilityVerdict"], "value": "FirmwareReady"}]}, {"label": "SchemaVersionChanged", "expectedCode": "MetadataMismatch", "domain": "Metadata", "patches": [{"op": "set", "path": ["eligibility", "schemaVersion"], "value": 2}]}, {"label": "FloatBase", "expectedCode": "InputShape", "domain": "ExactJSONShape", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 4096.5}]}, {"label": "FloatOperand", "expectedCode": "InputShape", "domain": "ExactJSONShape", "patches": [{"op": "set", "path": ["eligibility", "typedRequestMapping", 0, "operandDescriptors", 1, "fields", "value"], "value": 142.5}]}, {"label": "BoolBase", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": True}]}, {"label": "NegativeGap", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "set", "path": ["request", "gap"], "value": -1}]}, {"label": "WrongRequestClassification", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "set", "path": ["request", "classification"], "value": "FirmwareReady"}]}, {"label": "RequestExtraRuntimeField", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "set", "path": ["request", "runtimePermission"], "value": True}]}, {"label": "MissingRequestOrigin", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "delete", "path": ["request", "syntheticBase"]}]}, {"label": "NullIR", "expectedCode": "InputShape", "domain": "Shape", "patches": [{"op": "set", "path": ["ir"], "value": None}]}, {"label": "MissingRequiredModelGroup", "expectedCode": "InputShape", "domain": "Shape", "patches": [{"op": "delete", "path": ["eligibility", "typedRequestMapping"]}]}, {"label": "InvalidInitialDD-[]", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "set", "path": ["request", "initialDD"], "value": []}]}, {"label": "InvalidInitialDD-[1,0]", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "set", "path": ["request", "initialDD"], "value": [1, 0]}]}, {"label": "InvalidInitialDD-[0,0]", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "set", "path": ["request", "initialDD"], "value": [0, 0]}]}, {"label": "InvalidInitialDD-[2]", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "set", "path": ["request", "initialDD"], "value": [2]}]}, {"label": "InvalidInitialDD-[true]", "expectedCode": "RequestDomain", "domain": "RequestDomain", "patches": [{"op": "set", "path": ["request", "initialDD"], "value": [True]}]}, {"label": "DenseFFCDStaticOnly", "expectedCode": "LayoutNotAllowlisted", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 65485}, {"op": "set", "path": ["request", "gap"], "value": 0}]}, {"label": "DenseFFCEOverflow", "expectedCode": "SpanOutsideProfile", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 65486}, {"op": "set", "path": ["request", "gap"], "value": 0}]}, {"label": "Gap101FF68StaticOnly", "expectedCode": "LayoutNotAllowlisted", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 65384}, {"op": "set", "path": ["request", "gap"], "value": 101}]}, {"label": "Gap101FF69Overflow", "expectedCode": "SpanOutsideProfile", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 65385}, {"op": "set", "path": ["request", "gap"], "value": 101}]}, {"label": "Gap1StaticOnly", "expectedCode": "LayoutNotAllowlisted", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 4096}, {"op": "set", "path": ["request", "gap"], "value": 1}]}, {"label": "Gap41StaticOnly", "expectedCode": "LayoutNotAllowlisted", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 4096}, {"op": "set", "path": ["request", "gap"], "value": 41}]}, {"label": "Gap101StaticOnly", "expectedCode": "LayoutNotAllowlisted", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 4096}, {"op": "set", "path": ["request", "gap"], "value": 101}]}, {"label": "BaseZeroStaticOnly", "expectedCode": "LayoutNotAllowlisted", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 0}, {"op": "set", "path": ["request", "gap"], "value": 0}]}, {"label": "Base1001StaticOnly", "expectedCode": "LayoutNotAllowlisted", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 4097}, {"op": "set", "path": ["request", "gap"], "value": 0}]}, {"label": "HugeGapSpanBeforeReach", "expectedCode": "SpanOutsideProfile", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 4096}, {"op": "set", "path": ["request", "gap"], "value": 1208925819614629174706176}]}, {"label": "Anchor5596Collision", "expectedCode": "SyntheticExternalAnchorCollision", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 21910}, {"op": "set", "path": ["request", "gap"], "value": 0}]}, {"label": "Anchor55C5Collision", "expectedCode": "SyntheticExternalAnchorCollision", "domain": "ActualGeometryOrAllowlist", "patches": [{"op": "set", "path": ["request", "syntheticBase"], "value": 21957}, {"op": "set", "path": ["request", "gap"], "value": 0}]}, {"label": "ActualSignedBoundary-129", "expectedCode": "Rel8OutOfRange", "domain": "ActualGeometry", "patches": [{"op": "canonicalAssignments"}, {"op": "shiftBelow", "by": -155}]}, {"label": "ActualSignedBoundary-128", "expectedCode": "BranchTargetMismatch", "domain": "ActualGeometry", "patches": [{"op": "canonicalAssignments"}, {"op": "shiftBelow", "by": -154}]}, {"label": "ActualSignedBoundary127", "expectedCode": "BranchTargetMismatch", "domain": "ActualGeometry", "patches": [{"op": "canonicalAssignments"}, {"op": "shiftBelow", "by": 101}]}, {"label": "ActualSignedBoundary128", "expectedCode": "Rel8OutOfRange", "domain": "ActualGeometry", "patches": [{"op": "canonicalAssignments"}, {"op": "shiftBelow", "by": 102}]}, {"label": "JBSJoinTailFT_NoIncidentalOverlap", "expectedCode": "FallthroughMismatch", "domain": "ActualGeometry", "patches": [{"op": "canonicalAssignments"}, {"op": "shiftJoinTailAndBelow", "by": 1}]}]


def stable(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fingerprint(value):
    return hashlib.sha256(stable(value).encode("utf-8")).hexdigest()


def request(initial=(0, 1), assignments=None):
    return {"syntheticBase": 0x1000, "gap": 0, "initialDD": list(initial),
            "nodeAssignments": assignments, "classification": "InventedOnlyCompositeEmissionEligibility"}


def canonical_assignments():
    assigned = positions(0x1000, 0)
    return [{"nodeId": node, "assignedPC": assigned[node]} for node, *_ in ROWS]


def mutate(inputs, patch):
    op = patch["op"]
    if op == "canonicalAssignments":
        inputs["request"]["nodeAssignments"] = canonical_assignments()
        return
    if op in ("shiftBelow", "shiftJoinTailAndBelow"):
        nodes = (0x55BF, 0x55C1, 0x55C3, J_BELOW)
        if op == "shiftJoinTailAndBelow":
            nodes += (0x5592, 0x5594, J_NB)
        for row in inputs["request"]["nodeAssignments"]:
            if row["nodeId"] in nodes:
                row["assignedPC"] += patch["by"]
        return
    cursor = inputs
    for key in patch["path"][:-1]:
        cursor = cursor[key]
    final = patch["path"][-1]
    if op == "delete":
        del cursor[final]
    elif op == "duplicate":
        cursor.insert(final + 1, copy.deepcopy(cursor[final]))
    elif op == "append":
        cursor[final].append(copy.deepcopy(patch["value"]))
    elif op == "insert":
        cursor[final].insert(patch["index"], copy.deepcopy(patch["value"]))
    elif op == "reverse":
        cursor[final].reverse()
    else:
        cursor[final] = copy.deepcopy(patch["value"])


def materialize(ir, composition, eligibility, case):
    inputs = {"ir": copy.deepcopy(ir), "composition": copy.deepcopy(composition),
              "eligibility": copy.deepcopy(eligibility), "request": request()}
    for patch in case["patches"]:
        mutate(inputs, patch)
    return inputs


def geometry_certificate(case, inputs):
    """Earliest real geometry, never new planner output or metadata-only inference."""
    if case["domain"] not in ("ActualGeometry", "ActualGeometryOrAllowlist"):
        return None
    candidate = inputs["request"]
    assignments = candidate["nodeAssignments"]
    if assignments is not None:
        assignments = {row["nodeId"]: row["assignedPC"] for row in assignments}
    reason = geometry_reason(candidate["syntheticBase"], candidate["gap"], assignments)
    if reason is None and (candidate["syntheticBase"], candidate["gap"]) != (0x1000, 0):
        reason = "LayoutNotAllowlisted"
    assert reason == case["expectedCode"], (case["label"], reason, case["expectedCode"])
    return {"label": case["label"], "earliestIndependentReason": reason,
            "geometryBeforeAllowlist": True, "noPlannerOrCodecCalls": True}


def load_inputs(directory):
    return tuple(json.loads((directory / name).read_text(encoding="utf-8")) for name in (
        "word0196_ir.json", "static_composition_contract.json",
        "composite_emission_eligibility_contract.json"))


def preparation(ir, composition, eligibility):
    assert summary()["nodes"] == 20 and summary()["plannedLength"] == 51
    projections, variants = [], []
    for initial in DOMAINS:
        expected = expected_plan(initial)
        assert len(expected["nodePlans"]) == 20
        assert expected["counts"]["routeANodes"] == 18 and expected["counts"]["routeBNodes"] == 2
        assert expected["counts"]["totalRequestVariants"] == 19 + len(initial)
        assert expected["counts"]["originalForms"] == 15
        assert [row["signedDelta"] for row in expected["branchRows"]] == [26, 10, 7]
        assert expected["counts"]["composedPathCounts"] == [11, 13, 14, 16]
        assert expected["counts"]["orderedWriteCounts"] == [3, 3, 3, 5]
        assert all(row["incomingDDDomain"] == [0] for row in expected["nodePlans"][1:])
        assert expected["nodePlans"][0]["incomingDDDomain"] == list(initial)
        assert all(len(row["requestVariants"]) == len(row["incomingDDDomain"]) for row in expected["nodePlans"])
        for row in expected["nodePlans"]:
            for variant in row["requestVariants"]:
                assert type(variant["fields"]["incoming_dd"]) is int
                assert variant["fields"]["origin_pc"] == row["assignedPC"]
                if row["routeId"] == "B":
                    assert set(variant["fields"]) == {"target", "origin_pc", "incoming_dd"}
                    assert variant["fields"]["target"]["kind"] == "ProgramTarget16"
                    assert abs(variant["fields"]["target"]["fields"]["value"] - row["endExclusive"]) > 127
                else:
                    assert set(variant["fields"]) == {"reviewed_form_id", "typed_operands", "incoming_dd", "origin_pc"}
                    assert variant["fields"]["typed_operands"]["container"] == "tuple"
        projections.append(fingerprint(expected))
        variants.append(expected["counts"]["totalRequestVariants"])
    baseline = {"ir": ir, "composition": composition, "eligibility": eligibility, "request": request()}
    mutant_fingerprints, certificates = [], []
    for case in CASES:
        mutated = materialize(ir, composition, eligibility, case)
        assert fingerprint(mutated) != fingerprint(baseline), case["label"]
        mutant_fingerprints.append(fingerprint(mutated))
        certificate = geometry_certificate(case, mutated)
        if certificate is not None:
            certificates.append(certificate)
    return {
        "phase": "FrozenAPIIndependentTestPreparation_NoPlannerComparison",
        "oraclePredatesPlanner": True, "allTestsPredatePlanner": False,
        "testsReadNewPlannerSourceOrOutput": False,
        "positiveRequestLabels": 9, "uniquePositiveRequests": 9,
        "uniqueEligibleGeometryDDContexts": 3,
        "nodePlanComparisonsExpected": 180, "requestVariantComparisonsExpected": 183,
        "mandatoryUserMutationLabels": MANDATORY_LABEL_COUNT, "negativeLabels": len(CASES),
        "uniqueNegativeInputs": len(set(mutant_fingerprints)), "negativeCallsExpected": 2 * len(CASES),
        "domains": {domain: sum(case["domain"] == domain for case in CASES)
                    for domain in sorted({case["domain"] for case in CASES})},
        "expectedProjectionCorpusSHA256": fingerprint(projections),
        "expectedMutationDescriptorSHA256": fingerprint(CASES),
        "actualMutantInputCorpusSHA256": fingerprint(mutant_fingerprints),
        "earliestGeometryCertificates": certificates,
        "plannedScalarVariants": variants, "actualPlannerCalls": 0,
        "actualEncoderCalls": 0, "actualDecoderCalls": 0, "actualCPUExecutions": 0,
        "compositeBytes": 0, "fakeRED": False,
    }


def main():
    directory = HERE
    if "--data-directory" in sys.argv:
        directory = Path(sys.argv[sys.argv.index("--data-directory") + 1]).resolve()
    ir, composition, eligibility = load_inputs(directory)
    prepared = preparation(ir, composition, eligibility)
    if "--prepare-only" in sys.argv:
        print(json.dumps({**prepared, "passed": True}, sort_keys=True))
        return

    from composite_emission_eligibility_analysis import EligibilityError, prepare_composite_emission_plan

    baseline_hashes = fingerprint(ir), fingerprint(composition), fingerprint(eligibility)
    counts = {"positiveCalls": 0, "negativeCalls": 0, "negativeLabels": 0,
              "nodePlansCompared": 0, "requestVariantsCompared": 0}
    positive_requests, negative_inputs, refusal_codes = set(), set(), set()
    for initial in DOMAINS:
        candidates = (request(initial), request(initial, canonical_assignments()),
                      request(initial, list(reversed(canonical_assignments()))))
        for candidate in candidates:
            expected = expected_plan(initial)
            before = fingerprint(candidate)
            actual = prepare_composite_emission_plan(ir, composition, eligibility, candidate)
            counts["positiveCalls"] += 1
            assert type(actual) is dict and actual == expected, (
                "Independent plan projection mismatch", initial, fingerprint(actual), fingerprint(expected))
            assert set(actual) == set(expected)
            counts["nodePlansCompared"] += len(actual["nodePlans"])
            counts["requestVariantsCompared"] += sum(len(row["requestVariants"]) for row in actual["nodePlans"])
            assert fingerprint(candidate) == before
            positive_requests.add(stable(candidate))
    for case in CASES:
        inputs = materialize(ir, composition, eligibility, case)
        before = fingerprint(inputs)
        negative_inputs.add(before)
        seen = []
        for _ in range(2):
            try:
                prepare_composite_emission_plan(inputs["ir"], inputs["composition"], inputs["eligibility"], inputs["request"])
            except EligibilityError as error:
                assert type(error.code) is str and error.code == case["expectedCode"], (
                    case["label"], case["domain"], error.code, case["expectedCode"])
                assert type(error.location) is str and error.location
                assert not any(hasattr(error, name) for name in (
                    "plan", "partial", "nodePlans", "encoded_bytes", "program", "payload", "result"))
                seen.append((error.code, error.location, error.args))
                refusal_codes.add(error.code)
            else:
                raise AssertionError((case["label"], "Required preflight refusal did not occur"))
            counts["negativeCalls"] += 1
        assert seen[0] == seen[1], (case["label"], "Nondeterministic refusal")
        assert fingerprint(inputs) == before, (case["label"], "Refused caller data was mutated")
        counts["negativeLabels"] += 1
    assert (fingerprint(ir), fingerprint(composition), fingerprint(eligibility)) == baseline_hashes
    assert counts["positiveCalls"] == len(positive_requests) == 9
    assert counts["nodePlansCompared"] == 180 and counts["requestVariantsCompared"] == 183
    assert counts["negativeLabels"] == len(CASES) and counts["negativeCalls"] == 2 * len(CASES)
    print(json.dumps({
        "milestone": "M2bi", "passed": True, "failed": 0, "skipped": 0,
        "counts": counts, "uniquePositiveRequests": len(positive_requests),
        "uniqueNegativeInputs": len(negative_inputs), "observedRefusalCodes": sorted(refusal_codes),
        "independentPreparation": prepared,
        "codecCallsForFullFragment": 0, "encoderCalls": 0, "decoderCalls": 0,
        "compositeBytes": 0, "instructionStreams": 0, "CPUExecutions": 0, "actualROMExecutions": 0,
        "nativeJournals": 0, "targetObjects": 0, "targetHEX": 0, "FirmwareBIN": 0,
        "ActualCompositeEmission": "NotRun", "NativeExitIsolation": "NotEstablished",
        "ActualDownstreamRejoin": "NotEstablished", "PhysicalROMPlacement": "NotEstablished",
        "TargetProgramEquivalence": "NotEstablished", "FirmwareIntegration": "NotEstablished",
        "FirmwareReady": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
