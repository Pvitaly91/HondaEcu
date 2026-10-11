"""Closed M2bg documentary/source contract validation, not a byte-proof suite.

Only fixed project metadata/source files are read by the CLI. Codecs and oracle
are never imported or executed here. AST checks are trusted-source defense in
depth, not a Python sandbox. Run direct_j_tests.py separately for fresh bytes.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys

NORMATIVE = json.loads("{\"primary\":{\"manual\":\"Oki_66201_Instruction_Manual.pdf\",\"edition\":\"September1991\",\"manualSha256\":\"f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271\",\"detail\":{\"physicalPDFPage\":116,\"zeroBasedPDFIndex\":115,\"printedPage\":\"3-62\"},\"corroboration\":{\"physicalPDFPage\":263,\"zeroBasedPDFIndex\":262,\"printedPage\":\"3-210\",\"table\":\"3-34\"},\"fixedHeaderHex\":\"03\",\"length\":3,\"codeCellOrder\":[\"Fixed03\",\"TargetLow8\",\"TargetHigh8\"],\"targetAddressSpace\":\"PROGRAM\",\"headerEstablishedByFreshFullPageReviewBeforeImplementation\":true},\"api\":{\"encoder\":\"encode_direct_j(DirectJEncodeRequest)\",\"decoder\":\"decode_direct_j(DirectJDecodeRequest)\"},\"publicTypes\":{\"ProgramTarget16\":[\"value\"],\"DirectJEncodeRequest\":[\"target\",\"origin_pc\",\"incoming_dd\"],\"DirectJDecodeRequest\":[\"encoded_bytes\",\"origin_pc\",\"incoming_dd\"],\"EncodedDirectJ\":[\"target\",\"origin_pc\",\"incoming_dd\",\"encoded_bytes\",\"form\",\"length\",\"end_exclusive\",\"pc_effect\",\"dd_effect\",\"noninterference_scope\",\"classification\"],\"DecodedDirectJ\":[\"target\",\"origin_pc\",\"incoming_dd\",\"form\",\"length\",\"end_exclusive\",\"pc_effect\",\"dd_effect\",\"noninterference_scope\",\"classification\"],\"DirectJEncodeError\":[\"code\"],\"DirectJDecodeError\":[\"code\"]},\"enumClasses\":{\"form\":\"DirectJForm\",\"encoderError\":\"EncodeErrorCode\",\"decoderError\":\"DecodeErrorCode\"},\"form\":{\"enumClass\":\"DirectJForm\",\"member\":\"J_ADDRESS\",\"value\":\"j-address\",\"length\":3,\"operand\":\"ProgramTarget16\",\"programTargetRange\":[0,65535],\"fixedHeaderHex\":\"03\",\"headerProof\":\"PersonallyReadPrimary116CodeCell1BeforeImplementation\",\"operandOrder\":[\"Low8\",\"High8\"],\"incomingDD\":[0,1],\"originRange\":[0,65535],\"extent\":\"origin+3<=65536\",\"endExclusive\":\"AnalyticalIntegerMayEqual65536_NotSequentialPC16OrFallthroughPermission\",\"signedRel8Restriction\":false},\"metadata\":{\"pc_effect\":\"DocumentedPCReplacement\",\"dd_effect\":\"DocumentedDDPreservedWhenExecuted\",\"noninterference_scope\":\"ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence\",\"encoderClassification\":\"SyntheticDirectJEncodingOnly\",\"decoderClassification\":\"SyntheticDirectJDecodingOnly\"},\"typePolicy\":\"FrozenSlotsDataclasses_ExactTypesOnly_NoCoercion_RequestMissingSlotsRefused_TargetExactProgramTarget16WithExactIntValue\",\"encodeValidationOrder\":[\"ExactDirectJEncodeRequestAndAllThreeSlots_RequestShape\",\"ExactProgramTarget16AndValueSlotAndExactInt_TargetTypeInvalid\",\"Target0To65535_TargetOutOfRange\",\"ExactIntDD0Or1_IncomingDDInvalid\",\"ExactIntOrigin0To65535_OriginInvalid\",\"OriginPlus3AtMost65536_OriginSpanOutsideProfile\",\"OnlyThenConstructThreeImmutableBytesAndResult\"],\"decodeValidationOrder\":[\"ExactDirectJDecodeRequestAndAllThreeSlots_RequestShape\",\"ExactBytesType_EncodedBytesInvalid\",\"Length0_EncodedLengthInvalid_Length1Or2_TruncatedEncoding_LengthGreater3_TrailingBytes\",\"ExactIntDD0Or1_IncomingDDInvalid\",\"ExactIntOrigin0To65535_OriginInvalid\",\"OriginPlus3AtMost65536_OriginSpanOutsideProfile\",\"ExactPrimaryHeader03_UnsupportedEncoding\",\"OnlyThenReconstructTargetAndImmutableResult\"],\"encodeErrorCodes\":[\"RequestShape\",\"TargetTypeInvalid\",\"TargetOutOfRange\",\"IncomingDDInvalid\",\"OriginInvalid\",\"OriginSpanOutsideProfile\"],\"decodeErrorCodes\":[\"RequestShape\",\"EncodedBytesInvalid\",\"EncodedLengthInvalid\",\"TruncatedEncoding\",\"TrailingBytes\",\"IncomingDDInvalid\",\"OriginInvalid\",\"OriginSpanOutsideProfile\",\"UnsupportedEncoding\"],\"outputPolicy\":\"ErrorsOnlyEnumCode_NoPartialBytesOrTarget_NoCPUStackRAMState_NoRuntimeAuthority\",\"inputPolicies\":{\"typedTarget\":\"ExactProgramTarget16_ExactIntValue0To65535_NoDataAddressOrImmediateSubstitution\",\"DD\":\"ExactInt0Or1_BothAccepted_EncodingDecodingDoNotExecuteOrChangeDD\",\"origin\":\"ExactInt0To65535_FFFDMaximumCompleteOrigin_NoWrapRepair\",\"span\":\"origin+3<=65536_EndExclusiveAnalyticalNotNativeSequentialPC\",\"oddProgramTargets\":\"Accepted_NotDATAWordAlignmentPolicy\",\"physicalMappingFilter\":\"None_FullEncodedProgramAddressDomainIsNotMappedECUAvailability\",\"bytes\":\"DecoderExactImmutableBytesExactly3_NoSlicePaddingCoercionOrIgnoredTrailing\",\"unsupported\":\"UnsupportedEncodingWithinIsolatedDirectJProfile_NotGlobalISAIllegality\",\"relative\":\"NotRelative_NoRel8Restriction\",\"atomicity\":\"FullValidationBeforeAnySuccessBytesTargetOrMetadata\",\"mutation\":\"ChangedOperandOctetsMayEncodeOtherValidTargets_NoBlanketRefusal\"},\"documentaryNoninterference\":{\"scope\":\"ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence\",\"operation\":\"PCReplacement\",\"incomingDD\":[0,1],\"listedFlagWrites\":[],\"functionalDATAOperandReadsListed\":false,\"RAMWriterListed\":false,\"SSPStackFrameWriterListed\":false,\"programInstructionOperandFetch\":\"OccursAsPROGRAMFetch_NotFunctionalDATAOperandRead\",\"otherArchitecturalWriters\":\"NoneListedInReviewedDirectJFunction_NotGlobalASICProof\",\"nativeSFMeaningStorageWidth\":\"NotEstablished\",\"ASICApplicability\":\"NotEstablished\",\"externalProgramMapping\":\"NotEstablished\",\"globalBusInterruptPeripheralNoninterference\":\"NotEstablished\"},\"sourceIndependence\":{\"implementationInputs\":[\"FreshManufacturerFunctionalAndEncodingFacts\",\"OwnSeparateTypedValidation\",\"IndependentPreimplementationPrimaryLiterals\"],\"encoderDecoderSharedInputs\":\"PublicImmutableTypesOnly_NoSharedOpcodeOrEmissionTables\",\"oracleImportsCodec\":false,\"decoderImportsEncoder\":false,\"encoderImportsDecoder\":false,\"excludedInputs\":[\"ASM662\",\"DocGeneratedOpcodeTable\",\"RustFULL_OPCODES\",\"CSharpExecutor\",\"EncoderOutput\",\"DecoderOutput\"],\"priorThirdPartyExposureDisclosed\":true,\"legalCleanRoomCertification\":false,\"thirdPartyRightsGrant\":false},\"proofDirections\":{\"A\":\"PrimarySpecificationToEncoderAgainstIndependentExpectedThreeBytes\",\"B\":\"IndependentPrimaryThreeBytesToDecoderAgainstIndependentTypedTargetAndMetadata\",\"C1\":\"TypedEncodeDecodeCompatibilityOnly\",\"C2\":\"IndependentBytesDecodeEncodeExactByteCompatibilityOnly\",\"roundTripsAloneEstablishISA\":false},\"plannedCoverage\":{\"targets\":65536,\"DD\":[0,1],\"origins\":[0,4096,65533],\"uniqueMainContexts\":393216,\"literalLabels\":24,\"literalLabelsOverlapMainDomain\":24,\"literalContextsAdditionalToMain\":0,\"countsPerActualRunNotCumulative\":true,\"operandMutationAcceptance\":\"ValidChangedLowHighAndSwapRecognizedAsNewTarget\",\"negativeDomain\":\"ShapesExactTypesSlotsRangesDDOriginsSpanLengthsAll255OtherHeadersAndValidationPrecedence\"},\"preservedOldResearch\":{\"old15FormEnumUnchanged\":true,\"old15Forms\":15,\"old18SiteInventory\":18,\"oldInstructionLengthSum\":45,\"oldBlocks\":[16,23,6],\"oldEdges\":21,\"oldLogicalPaths\":[10,12,13,15],\"historical13StepNativeWitnesses\":0,\"oldM2beNativeExitIsolation\":\"NotEstablished\",\"oldM2bfActualDownstreamRejoin\":\"NotEstablished\",\"nativeFragmentGenerated\":false,\"programLayoutOrGapReservation\":false,\"continuationPCsAreNotWritable\":true},\"permissions\":{\"singleInstructionInMemory\":true,\"instructionStreams\":false,\"CPUExecution\":false,\"actualROM\":false,\"persistentMachineCodeFiles\":false,\"assemblyObjectsFirmware\":false,\"productionAdmission\":false},\"operations\":{\"CPUExecutions\":0,\"actualROMExecutions\":0,\"ASM662Executions\":0,\"MAC66KExecutions\":0,\"persistentMachineCodeFiles\":0,\"instructionStreams\":0,\"targetAssemblyFiles\":0,\"targetObjects\":0,\"targetHEX\":0,\"FirmwareBIN\":0,\"ROMPatches\":0,\"nativeTraceJournals\":0,\"externalInquiries\":\"NotSent\",\"GUIHardwareFullBoot\":\"NotRun\"},\"unresolvedBoundaries\":{\"nativeExitIsolation\":\"NotEstablished\",\"actualDownstreamRejoin\":\"NotEstablished\",\"full18SiteMachineCodeEquivalence\":\"NotEstablished\",\"targetCodeGeneration\":\"NotReady\",\"firmwareIntegration\":\"NotEstablished\",\"compilerABI\":\"NotEstablished\",\"codePlacement\":\"NotEstablished\",\"customerASICIdentityRevision\":\"NotEstablished\",\"SF\":\"NotEstablished\",\"stackSafety\":\"NotEstablished\",\"nativeOwner019B2\":\"NotEstablished\",\"recoveredECUScheduler\":\"NotEstablished\",\"WDT3C\":\"Unresolved\",\"JGTC8\":\"PrimaryConflictUnresolved\",\"CAL2689_RT5C80\":\"NotRun\",\"SSP_ADC\":\"Blocked\",\"DATA019BFrontier\":\"Unchanged\",\"M2ah\":\"STOPBefore5722\",\"IRQ\":\"NotInjected\",\"timerEvolution\":\"NotModeled\",\"readiness\":\"PcInspectionOnly_NotFlashReady\"},\"historicalRunner\":{\"version\":\"0.43.0\",\"protocol\":1,\"semanticAccountingIdentities\":38},\"excludedInterfaces\":[\"GenericAssembler\",\"GeneralDisassembler\",\"TextMnemonics\",\"BatchOrStreams\",\"LabelsSymbols\",\"RelocationLinking\",\"Old18SiteEmission\",\"ROMInput\",\"ROMPlacement\",\"NativeStubTrampoline\",\"CPUExecution\",\"SyntheticStackRAMSnapshot\",\"FirmwareExport\",\"ProductionAdmission\",\"GUI\",\"Hardware\"],\"validatorMeaning\":{\"closedMetadataAndCurrentSourceIdentityOnly\":true,\"sourceASTGuard\":\"TrustedSourceDefenseInDepth_NotArbitraryPythonSandbox\",\"attackFixturesParsedOnlyNeverExecuted\":true,\"doesNotImportOrRunCodecsToManufactureExpectedResults\":true,\"requiresSeparateFreshByteSuite\":true,\"observedReferencesAreHistoricalSourceBoundReceiptsNotSelfAttestation\":true},\"historicalResults\":{\"M2bf\":\"ExternalContinuationObligationsAndTransferFormEvidenceEstablished\",\"M2be\":\"SyntheticLayoutBranchFeasibilityEstablished\",\"M2bd\":\"TypedIRToFormMappingAndDataflowObligationsEstablished\",\"M2bc\":\"Independent15FormDecodeEncodeCompatibilityVerified\",\"M2bb\":\"Independent15FormSyntheticEncodingVerified\",\"M2ba\":\"IndependentRouteSpecified_HistoricalEncoderNotImplemented\",\"M2az\":\"ASM662ComponentRightsBlocked\",\"M2ay\":\"ASM662BuildEncodingBlocked\",\"M2ax\":\"MAC66KAcquisitionBlocked\",\"M2aw\":\"TargetArchitectureContextEstablished\",\"M2av\":\"BoundedSourceEquivalenceEstablished\",\"M2au\":\"INTAccountingComplete\",\"M2at\":\"DEC_DP_HCFixComplete\",\"M2an\":\"SLLBSemanticFixComplete\",\"M2t\":\"JGT233ABlocked\",\"StrictM2i\":\"Blocked\",\"physicalFuelTimeDegrees\":\"Unavailable\",\"physicalRPMAvailable\":false,\"ASM662_WDT_C8Inquiries\":\"NotSent\"}}")
UPSTREAM = json.loads("[{\"file\":\"research/p28-word0196/continuation_transfer_analysis.py\",\"bytes\":78628,\"sha256\":\"86eb302ae13138aef5a64b192e5d4b63982afa1e4bb3e9c4b3d71b9f927c355c\"},{\"file\":\"research/p28-word0196/continuation_transfer_oracle.py\",\"bytes\":12784,\"sha256\":\"5c250c75ee7d950e766cf747381efc125545b192a5c7d7b0e8b01a1c6b3909fb\"},{\"file\":\"research/p28-word0196/continuation_transfer_tests.py\",\"bytes\":19256,\"sha256\":\"e47b4e34bf2ee42e5e5f7c118becb9dffb71864e1a57030a9aedd2fbb83b833d\"},{\"file\":\"research/p28-word0196/external_continuation_contract.json\",\"bytes\":58097,\"sha256\":\"bce975c6427e0ab9294af8227933f0b2553efa13a47b89383f53fc4ac6138660\"},{\"file\":\"research/p28-word0196/independent_decode_encode_contract.json\",\"bytes\":17800,\"sha256\":\"547a09d9cd60dc6e2543870a5a5d0ee228e1051c28748fc53a526208355f5f2d\"},{\"file\":\"research/p28-word0196/independent_decoder_primary_oracle.py\",\"bytes\":12745,\"sha256\":\"9154ceac6709d8ad93fa71ab77f5b1e5c601dbaa812d60d4e3681b08f4b8e1df\"},{\"file\":\"research/p28-word0196/independent_decoder_tests.py\",\"bytes\":19933,\"sha256\":\"cdc5d43ee866dba4fb619fc6169e2ec5e869d4050f98137bb67e62ca0a2bdb64\"},{\"file\":\"research/p28-word0196/independent_decoder.py\",\"bytes\":11036,\"sha256\":\"e91c862d07d102c67ffa471603744c87eaee6d940fd27305e524afc91b946404\"},{\"file\":\"research/p28-word0196/independent_encoder_contract.json\",\"bytes\":12182,\"sha256\":\"414e5326cec42538ea6b64aa12a810c9d548c8b755b61a4f5c285b60c1837d47\"},{\"file\":\"research/p28-word0196/independent_encoder_design.json\",\"bytes\":21765,\"sha256\":\"9403279ed7570f1cb36280954a0f3249d41de2d64ae767b840649b066c625be9\"},{\"file\":\"research/p28-word0196/independent_encoder_oracle.py\",\"bytes\":7092,\"sha256\":\"6575f802c0703da087f1f06fdff095dcf4c4b948b7fe59e8fb35972210cb6361\"},{\"file\":\"research/p28-word0196/independent_encoder_tests.py\",\"bytes\":18429,\"sha256\":\"76ca001260dbf07b0c5ad99f72e156732b940756af2c177e2b97311acba3b62c\"},{\"file\":\"research/p28-word0196/independent_encoder.py\",\"bytes\":9868,\"sha256\":\"603092893afbdb3d69cbcd43585ff6fc9886c45919920f432ec4b2905d830879\"},{\"file\":\"research/p28-word0196/layout_feasibility_analysis.py\",\"bytes\":40569,\"sha256\":\"840320c5eed83d2a393dd3d1f4c8b90cb0aa7608c5c2ba721384265e79d151db\"},{\"file\":\"research/p28-word0196/layout_feasibility_contract.json\",\"bytes\":66622,\"sha256\":\"9d1baf1e4914fa1b611924ff48b75854e9fc7d2e06e6e05542c56c14e18abb2f\"},{\"file\":\"research/p28-word0196/layout_feasibility_oracle.py\",\"bytes\":10843,\"sha256\":\"be17e854a1b474b3800b09d74219ba097fc48bd2a2a53db93752169c3da06394\"},{\"file\":\"research/p28-word0196/layout_feasibility_tests.py\",\"bytes\":26061,\"sha256\":\"55377f7bd6c6c0ad1b5c29e7cc66eeb32aa63a3db8d1b849318c98326d74cd5e\"},{\"file\":\"research/p28-word0196/target_abi_contract.json\",\"bytes\":40753,\"sha256\":\"1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66\"},{\"file\":\"research/p28-word0196/transfer_form_evidence.json\",\"bytes\":37225,\"sha256\":\"f4279b5c86cc78be18f641e0638ea58892329f0b8903db28a8b6b77d69d34194\"},{\"file\":\"research/p28-word0196/typed_lowering_analysis.py\",\"bytes\":31589,\"sha256\":\"bd0ad1ee186cb76922926a957c21bacafc601e77200ff3bdcdc09fd866143bc5\"},{\"file\":\"research/p28-word0196/typed_lowering_contract.json\",\"bytes\":44984,\"sha256\":\"6f62c23e99f72e7df51a0117b7c5ff600d892f2a8d3e4c4231a383e1d96c6bf4\"},{\"file\":\"research/p28-word0196/typed_lowering_oracle.py\",\"bytes\":12601,\"sha256\":\"2e7b613813e81cf54ea6ee17c378344800022454f8d0074af15ecec586a77e4a\"},{\"file\":\"research/p28-word0196/typed_lowering_tests.py\",\"bytes\":29917,\"sha256\":\"1e46516c85b1d0b0593b67e59943b7b2d459725a073f29f23d385f59f73d7c6a\"},{\"file\":\"research/p28-word0196/validate_external_continuation_contract.py\",\"bytes\":76985,\"sha256\":\"6dfd2a85c6fa5187e4bb2649d8b96db2b61ffe584f0b9b7b4124fc058550da7e\"},{\"file\":\"research/p28-word0196/validate_layout_feasibility_contract.py\",\"bytes\":48319,\"sha256\":\"e6656112d6272adeac3f382ee672a4ddd3b01fe645dcab356444b0cefd6d51ea\"},{\"file\":\"research/p28-word0196/word0196_equivalent.c\",\"bytes\":8507,\"sha256\":\"4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3\"},{\"file\":\"research/p28-word0196/word0196_equivalent.h\",\"bytes\":2390,\"sha256\":\"df8da1511708fb29cb747981a959544e549a67a9a982e15586b5c12ce8826f0e\"},{\"file\":\"research/p28-word0196/word0196_ir.json\",\"bytes\":32188,\"sha256\":\"4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4\"},{\"file\":\"src/HondaEcu.Core/P28Word0196AlternateModel.cs\",\"bytes\":3464,\"sha256\":\"ac3162dfc6255e25ac24d7430531243f7856090ce55bab8b46e20d07f06fd74f\"}]")
PREPARATION = json.loads("[{\"file\":\"private/reports/m2bg/api-specification-before-implementation.json\",\"bytes\":4448,\"sha256\":\"1bb87ecb8215fda026feb772242ec5add78201b04140984719b919894f3b0273\"},{\"file\":\"private/reports/m2bg/api-enum-names-addendum-before-implementation.json\",\"bytes\":433,\"sha256\":\"d41322581d265bc81116126485032eec903fb6129a27cc09443b9d407c0b5dcc\"},{\"file\":\"private/reports/m2bg/primary-vectors/primary-literals-sealed.json\",\"bytes\":13233,\"sha256\":\"199aefc355011e9ee2ebd47901e728cff4b62e93995c121ab66629021b11da05\"},{\"file\":\"private/reports/m2bg/primary-vectors/independent-primary-review.json\",\"bytes\":5053,\"sha256\":\"7d2d39318ab7d3b9db45bcb97f9947ef232c1ff41118a433228d021ba537b5e5\"}]")
EXPECTED_PHASE = json.loads("{\"stage\":\"ObservedIndependentDirectJSyntheticEncodingDecodingCompatibilityAndSourceReviewPassed\",\"observedSyntheticCounts\":{\"decoderCalls\":800330,\"encoderCalls\":786570,\"immutabilityChecks\":1746,\"mainUniqueContexts\":393216,\"negativeDecoderCalls\":3162,\"negativeDecoderLabels\":1581,\"negativeEncoderCalls\":90,\"negativeEncoderLabels\":45,\"operandMutationAttempts\":12312,\"operandMutationDecoderCalls\":10688,\"positiveLabels\":393240,\"primaryDecodeEncodeComparisons\":393240,\"primaryDecoderComparisons\":393240,\"primaryEncoderComparisons\":393240,\"primaryLiteralCases\":24,\"successfulDecodedResults\":797168,\"successfulEncodedOctets\":2359440,\"successfulEncodedSequences\":786480,\"typedEncodeDecodeComparisons\":393240},\"observedProofAccounting\":{\"uniquePositiveContexts\":393216,\"literalLabelsOverlapMainDomain\":24,\"uniqueAcceptedMutationInputs\":10688,\"uniqueNegativeEncoderDescriptors\":45,\"uniqueNegativeDecoderDescriptors\":1581,\"observedEncodeErrorCodes\":[\"IncomingDDInvalid\",\"OriginInvalid\",\"OriginSpanOutsideProfile\",\"RequestShape\",\"TargetOutOfRange\",\"TargetTypeInvalid\"],\"observedDecodeErrorCodes\":[\"EncodedBytesInvalid\",\"EncodedLengthInvalid\",\"IncomingDDInvalid\",\"OriginInvalid\",\"OriginSpanOutsideProfile\",\"RequestShape\",\"TrailingBytes\",\"TruncatedEncoding\",\"UnsupportedEncoding\"],\"spoofedFieldReads\":0,\"failed\":0,\"skipped\":0,\"firstMismatch\":null,\"primaryProofDirections\":[\"A_IndependentBytesToEncoder\",\"B_IndependentBytesToDecoder\"],\"roundTripDirections\":\"CompatibilityOnly_NotIndependentISAProof\",\"countsPerOneObservedRunNotCumulative\":true},\"perFormEvidenceStatuses\":[\"PrimaryEncodingSpecified\",\"IndependentEncoderImplemented\",\"SyntheticBytesMatchPrimary\",\"PrimaryDecodingSpecified\",\"IndependentDecoderImplemented\",\"PrimarySyntheticBytesCorrectlyDecoded\",\"EncodeDecodeCompatibilityPassed\",\"DecodeEncodeCompatibilityPassed\",\"NegativeBoundaryTestsPassed\",\"IndependentReviewPassed\",\"ActualTargetExecutionNotObserved\"],\"implementationSourceBindings\":[{\"file\":\"research/p28-word0196/direct_j_types.py\",\"bytes\":3021,\"sha256\":\"f11877a07340b88a7c222acec250767524778955a96235a6dd147207fa99467b\"},{\"file\":\"research/p28-word0196/direct_j_encoder.py\",\"bytes\":1926,\"sha256\":\"1149ba3fcc142fa1fb78677ddd14b8c4bbab1ee333ef926aaffe22839d7f6f60\"},{\"file\":\"research/p28-word0196/direct_j_decoder.py\",\"bytes\":2006,\"sha256\":\"32738de208889d288856feda6f030c78b08d5cf3cf7ca0154120b32fc788c3a4\"},{\"file\":\"research/p28-word0196/direct_j_primary_oracle.py\",\"bytes\":4051,\"sha256\":\"91793837663e8d0341ce0d4e224fc97e256c549409807ea9b43e8d9266f55f39\"},{\"file\":\"research/p28-word0196/direct_j_tests.py\",\"bytes\":18346,\"sha256\":\"c5a3cbb6f10b9cafaf342a0ed5b5bd86921f58fcfa9af1f469f1b741f6cc8d7c\"}],\"actualTestReceipt\":{\"file\":\"private/reports/m2bg/first-suite-actual.json\",\"bytes\":5102,\"sha256\":\"551385616d468d7be602de2eee4ab8931eab2d559dcc6166bac9bba710597150\"},\"actualTestRawOutput\":{\"file\":\"private/reports/m2bg/first-suite.actual.raw.log\",\"bytes\":1738,\"sha256\":\"8fd29c9388cebfc91bbbbe0e4986df8923700b2547dfd098fd6cc8db409a35d2\"},\"preimplementationTestExpectation\":{\"file\":\"private/reports/m2bg/oracle-preparation/test-expectations-sealed.json\",\"bytes\":2850,\"sha256\":\"484d922966cbabbe7a6ff14c4cffe3c58153c0acb9b8c2e80292f23f7016642d\"},\"independentReviewReceipt\":{\"file\":\"private/reports/m2bg/contract-audit/independent-static-source-review.json\",\"bytes\":3086,\"sha256\":\"d4876207de2021be1b06010f9f23ed1fca2d447b89a4e29485ad450e8fc567a6\"},\"preimplementationReviewReceipt\":{\"file\":\"private/reports/m2bg/contract-audit/independent-preimplementation-review-seal.json\",\"bytes\":1335,\"sha256\":\"013ea571aecb5b25fce667f5f07e779e41823decf1af22adf96536a71b4b9a92\"},\"historyMetadataSupersession\":{\"file\":\"private/reports/m2bg/contract-audit/history-metadata-v2-supersession.json\",\"bytes\":1243,\"sha256\":\"1bc0aab4e5fb6b1a05def5a87b785b93b9b726d6e48978cbc82b407f6401be7f\"},\"actualTargetExecutionObserved\":false,\"fullNativeProgramEquivalenceEstablished\":false,\"nativeExitIsolation\":\"NotEstablished\",\"actualDownstreamRejoin\":\"NotEstablished\",\"referencesMeaning\":\"ReviewedActualPrivateReceiptsBoundToCurrentFiveSources_NotJSONSelfAttestation_FreshSuiteSeparatelyRequired\"}")
BASE = "3c76b6a54ac1e298470e1452a433090f34c49e1c"
SOURCE_FILES = (
    "direct_j_types.py", "direct_j_encoder.py", "direct_j_decoder.py",
    "direct_j_primary_oracle.py", "direct_j_tests.py",
)
DATACLASS_FIELDS = json.loads("{\"ProgramTarget16\":[\"value\"],\"DirectJEncodeRequest\":[\"target\",\"origin_pc\",\"incoming_dd\"],\"DirectJDecodeRequest\":[\"encoded_bytes\",\"origin_pc\",\"incoming_dd\"],\"EncodedDirectJ\":[\"target\",\"origin_pc\",\"incoming_dd\",\"encoded_bytes\",\"form\",\"length\",\"end_exclusive\",\"pc_effect\",\"dd_effect\",\"noninterference_scope\",\"classification\"],\"DecodedDirectJ\":[\"target\",\"origin_pc\",\"incoming_dd\",\"form\",\"length\",\"end_exclusive\",\"pc_effect\",\"dd_effect\",\"noninterference_scope\",\"classification\"],\"DirectJEncodeError\":[\"code\"],\"DirectJDecodeError\":[\"code\"]}")
FIXED_METADATA = {
    "form": ("enum", "DirectJForm", "J_ADDRESS"),
    "length": 3,
    "pc_effect": "DocumentedPCReplacement",
    "dd_effect": "DocumentedDDPreservedWhenExecuted",
    "noninterference_scope": "ManufacturerFunctionAndFlagTablesOnly_NoRuntimeEvidence",
}
FORBIDDEN = frozenset((
    "eval", "exec", "compile", "__import__", "open", "input", "print",
    "breakpoint", "help", "getattr", "setattr", "delattr", "vars", "globals",
    "locals", "dir", "object", "super", "memoryview", "bytearray",
    "ord", "chr", "hex", "oct",
    "_FORM_SHAPES", "FULL_OPCODES", "OPCODES", "encode_instruction",
    "decode_instruction", "Cpu", "CPU", "Bus", "ROM", "RAM",
    "encode_direct_j"  # Only refused in decoder/oracle, allowed encoder definition.
))
FORBIDDEN_ATTRIBUTES = frozenset((
    "read", "write", "read_bytes", "write_bytes", "read_text", "write_text",
    "open", "system", "popen", "run", "Popen", "get", "setdefault", "update",
    "to_bytes", "from_bytes", "fromhex", "encode", "decode", "join", "extend",
    "append", "__dict__", "__class__", "__getattribute__", "__subclasses__",
    "__globals__", "__code__", "CPUState", "RAMState", "stack_frame",
    "runtimePermission", "firmwareReady", "_FORM_SHAPES", "FULL_OPCODES",
))
IMPORTS = {
    "types": {
        "__future__": {"annotations"},
        "dataclasses": {"dataclass", "field"},
        "enum": {"Enum", "unique"},
    },
    "encoder": {
        "__future__": {"annotations"},
        "direct_j_types": {"ProgramTarget16", "DirectJForm", "DirectJEncodeRequest",
                          "EncodedDirectJ", "DirectJEncodeError", "EncodeErrorCode"},
    },
    "decoder": {
        "__future__": {"annotations"},
        "direct_j_types": {"ProgramTarget16", "DirectJForm", "DirectJDecodeRequest",
                          "DecodedDirectJ", "DirectJDecodeError", "DecodeErrorCode"},
    },
    "oracle": {"dataclasses": {"dataclass"}},
}


class ContractError(ValueError):
    """Deterministic refusal. A policy failure is not a failed ISA byte proof."""
    __slots__ = ("code", "path")
    def __init__(self, code, path):
        self.code, self.path = code, path
        self.args = (code, path)


def equal(actual, expected, path="$"):
    """Exact recursive values/types; bool is never an integer substitute."""
    if type(actual) is not type(expected):
        raise ContractError("Contract", path)
    if type(expected) is dict:
        if set(actual) != set(expected):
            raise ContractError("Contract", path)
        for key in expected:
            equal(actual[key], expected[key], path + "." + key)
    elif type(expected) is list:
        if len(actual) != len(expected):
            raise ContractError("Contract", path)
        for index, value in enumerate(expected):
            equal(actual[index], value, f"{path}[{index}]")
    elif actual != expected:
        raise ContractError("Contract", path)


def validate_contract(contract):
    if EXPECTED_PHASE is None:
        raise ContractError("ObservationNotSealed", "$.phaseEvidence")
    expected = {
        "schemaVersion": 1, "milestone": "M2bg", "exactBase": BASE,
        "scope": "IsolatedSingleInventedDirectJInstructionInMemoryOnly",
        "classification": "PrimaryManualDerivedIndependentImplementation",
        "normative": NORMATIVE, "upstreamBindings": UPSTREAM,
        "preparationBindings": PREPARATION, "phaseEvidence": EXPECTED_PHASE,
    }
    equal(contract, expected)
    return {
        "passed": True, "milestone": "M2bg",
        "classification": "ClosedDocumentaryAndSourceIdentityValidationOnly",
        "upstreamBindings": len(UPSTREAM),
        "freshByteProofPerformedByValidator": False,
        "requiresSeparateFreshByteSuite": True,
        "runtimePermission": False,
        "nativeExitIsolation": "NotEstablished",
        "actualDownstreamRejoin": "NotEstablished",
        "CPUExecutions": 0, "actualROMExecutions": 0,
    }


def reject(node, reason):
    raise ContractError("SourcePolicy", f"{reason}:line{getattr(node, 'lineno', 0)}")


def fixed_hasattr(call, tree, role):
    if role not in ("encoder", "decoder") or len(call.args) != 2 or call.keywords:
        return False
    owner, slot = call.args
    if not isinstance(owner, ast.Name):
        return False
    if owner.id in ("target", "request_target"):
        return role == "encoder" and isinstance(slot, ast.Constant) and slot.value == "value"
    if owner.id != "request":
        return False
    slots = {"target", "origin_pc", "incoming_dd"} if role == "encoder" else {
        "encoded_bytes", "origin_pc", "incoming_dd"}
    if isinstance(slot, ast.Constant):
        return type(slot.value) is str and slot.value in slots
    if isinstance(slot, ast.Name):
        for generator in ast.walk(tree):
            if isinstance(generator, ast.comprehension) and isinstance(generator.target, ast.Name):
                if generator.target.id == slot.id and isinstance(generator.iter, (ast.Tuple, ast.List)):
                    values = generator.iter.elts
                    if len(values) == 3 and all(isinstance(v, ast.Constant)
                                               and type(v.value) is str for v in values):
                        return {v.value for v in values} == slots
    return False


def dataclass_policy(tree, role):
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if role == "types":
        expected_classes = set(DATACLASS_FIELDS) | {"DirectJForm", "EncodeErrorCode", "DecodeErrorCode"}
        if {node.name for node in classes} != expected_classes or len(classes) != len(expected_classes):
            reject(tree, "closed-class-inventory")
        for node in classes:
            if node.name not in DATACLASS_FIELDS:
                if len(node.bases) != 1 or not isinstance(node.bases[0], ast.Name) or node.bases[0].id != "Enum":
                    reject(node, "enum-base")
                rows = [row for row in node.body if isinstance(row, ast.Assign)]
                if any(isinstance(row, (ast.FunctionDef, ast.AsyncFunctionDef)) for row in node.body):
                    reject(node, "enum-no-hooks")
                wanted_values = {"j-address"} if node.name == "DirectJForm" else set(
                    NORMATIVE["encodeErrorCodes"] if node.name == "EncodeErrorCode" else NORMATIVE["decodeErrorCodes"])
                values = [row.value.value for row in rows if isinstance(row.value, ast.Constant)
                          and type(row.value.value) is str]
                if len(rows) != len(wanted_values) or len(values) != len(rows) or set(values) != wanted_values:
                    reject(node, "closed-enum-values")
                if node.name == "DirectJForm" and (len(rows[0].targets) != 1 or not isinstance(rows[0].targets[0], ast.Name)
                                                  or rows[0].targets[0].id != "J_ADDRESS"):
                    reject(node, "fixed-form-member")
                continue
            if node.bases or len(node.decorator_list) != 1:
                reject(node, "dataclass-shape")
            deco = node.decorator_list[0]
            if (not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Name)
                    or deco.func.id != "dataclass" or deco.args
                    or {k.arg for k in deco.keywords} != {"frozen", "slots"}
                    or not all(isinstance(k.value, ast.Constant) and k.value.value is True for k in deco.keywords)):
                reject(node, "frozen-slots")
            fields = [n for n in node.body if isinstance(n, ast.AnnAssign)]
            if len(fields) != len(DATACLASS_FIELDS[node.name]) or {n.target.id for n in fields if isinstance(n.target, ast.Name)} != set(DATACLASS_FIELDS[node.name]):
                reject(node, "fixed-fields")
            if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in node.body):
                reject(node, "no-state-or-type-hooks")
            if node.name in ("EncodedDirectJ", "DecodedDirectJ"):
                defaults = dict(FIXED_METADATA)
                defaults["classification"] = "SyntheticDirectJEncodingOnly" if node.name == "EncodedDirectJ" else "SyntheticDirectJDecodingOnly"
                for row in fields:
                    if row.target.id in defaults:
                        call = row.value
                        if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name)
                                or call.func.id != "field" or call.args
                                or {k.arg for k in call.keywords} != {"default", "init"}):
                            reject(row, "metadata-init-false")
                        keys = {k.arg: k.value for k in call.keywords}
                        if not isinstance(keys["init"], ast.Constant) or keys["init"].value is not False:
                            reject(row, "metadata-init-false")
                        wanted = defaults[row.target.id]
                        if type(wanted) is tuple:
                            if not isinstance(keys["default"], ast.Attribute) or not isinstance(keys["default"].value, ast.Name) or (keys["default"].value.id, keys["default"].attr) != wanted[1:]:
                                reject(row, "metadata-form")
                        elif not isinstance(keys["default"], ast.Constant) or type(keys["default"].value) is not type(wanted) or keys["default"].value != wanted:
                            reject(row, "metadata-fixed-default")
    elif classes and role in ("encoder", "decoder"):
        reject(classes[0], "codec-no-class-hooks")
    elif role == "oracle":
        if len(classes) != 1 or classes[0].name != "PrimaryJLiteral":
            reject(tree, "oracle-literal-class-only")
        node = classes[0]
        if node.bases or len(node.decorator_list) != 1:
            reject(node, "oracle-immutable-literal")
        deco = node.decorator_list[0]
        if (not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Name)
                or deco.func.id != "dataclass" or deco.args
                or {k.arg for k in deco.keywords} != {"frozen", "slots"}
                or not all(isinstance(k.value, ast.Constant) and k.value.value is True for k in deco.keywords)):
            reject(node, "oracle-frozen-slots")
        fields = [row for row in node.body if isinstance(row, ast.AnnAssign)]
        if [row.target.id for row in fields if isinstance(row.target, ast.Name)] != [
                "identifier", "target", "incoming_dd", "origin", "expected_bytes"]:
            reject(node, "oracle-literal-fields")


def validate_source(source, role):
    """Parse only; never execute fixture text. Not a sandbox claim."""
    if type(source) is not str or role not in IMPORTS:
        raise ContractError("SourcePolicy", "source-or-role")
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise ContractError("SourcePolicy", "syntax") from error
    local_functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    wanted_api = "encode_direct_j" if role == "encoder" else "decode_direct_j"
    if role in ("encoder", "decoder"):
        if wanted_api not in local_functions or any(not n.startswith("_") and n != wanted_api for n in local_functions):
            reject(tree, "closed-single-instruction-api")
    allowed_calls = {"type", "len", "all"} | local_functions
    allowed_calls |= set().union(*IMPORTS[role].values())
    if role == "oracle":
        allowed_calls |= {"PrimaryJLiteral"}
    if role == "encoder":
        allowed_calls |= {"bytes", "hasattr"}
    if role == "decoder":
        allowed_calls |= {"hasattr"}
    if role == "oracle":
        allowed_calls |= {"bytes", "divmod", "ValueError"}
    if role == "types":
        allowed_calls |= {"dataclass", "field"}
    byte_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            reject(node, "no-module-import-or-alias")
        if isinstance(node, ast.ImportFrom):
            if node.level or node.module not in IMPORTS[role]:
                reject(node, "dependency")
            if any(a.asname or a.name not in IMPORTS[role][node.module] for a in node.names):
                reject(node, "public-symbol-imports-only")
        if isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom,
                             ast.Try, ast.With, ast.AsyncWith, ast.Global, ast.Nonlocal,
                             ast.Delete, ast.AugAssign)):
            reject(node, "unsupported-dynamic-or-mutating-statement")
        if isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES or node.attr in FORBIDDEN or node.attr.startswith("__"):
                reject(node, "forbidden-attribute")
            if isinstance(node.ctx, ast.Store):
                reject(node, "no-state-mutation")
        if isinstance(node, ast.Name):
            forbidden = FORBIDDEN - {"encode_direct_j"} if role == "encoder" else FORBIDDEN
            if node.id in forbidden or node.id.startswith("__") and node.id != "__name__":
                reject(node, "forbidden-name")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in allowed_calls:
                reject(node, "closed-call-set")
            if node.func.id == "hasattr" and not fixed_hasattr(node, tree, role):
                reject(node, "fixed-slot-hasattr-only")
            if node.func.id == "bytes":
                byte_calls.append(node)
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            reject(node, "no-container-mutation")
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice) and role in ("encoder", "decoder"):
            reject(node, "no-stream-slicing")
        if isinstance(node, (ast.Mod, ast.FloorDiv, ast.Pow)) and role in ("encoder", "decoder"):
            reject(node, "no-wrap-or-normalization-arithmetic")
    if role == "encoder":
        if len(byte_calls) != 1:
            reject(tree, "single-three-byte-construction")
        call = byte_calls[0]
        if call.keywords or len(call.args) != 1 or not isinstance(call.args[0], ast.Tuple):
            reject(call, "three-byte-tuple")
        cells = call.args[0].elts
        if len(cells) != 3 or not isinstance(cells[0], ast.Constant) or type(cells[0].value) is not int or cells[0].value != 3:
            reject(call, "primary-fixed-header-three-cells")
    if role == "decoder" and byte_calls:
        reject(byte_calls[0], "decoder-no-emitter")
    dataclass_policy(tree, role)
    return {"passed": True, "role": role, "parsedOnly": True,
            "trustedSourceDefenseInDepthNotSandbox": True}


def fixed_bindings(root, rows):
    for row in rows:
        path = root / row["file"]
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ContractError("SourceIdentity", row["file"])


def main():
    if sys.argv[1:]:
        raise ContractError("Input", "NoExternalFilesROMOrStreamArguments")
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    contract = json.loads((here / "direct_j_contract.json").read_text(encoding="utf-8"))
    summary = validate_contract(contract)
    fixed_bindings(root, UPSTREAM)
    fixed_bindings(root, EXPECTED_PHASE["implementationSourceBindings"])
    for role, filename in (("types", "direct_j_types.py"), ("encoder", "direct_j_encoder.py"),
                           ("decoder", "direct_j_decoder.py"), ("oracle", "direct_j_primary_oracle.py")):
        validate_source((here / filename).read_text(encoding="utf-8"), role)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
