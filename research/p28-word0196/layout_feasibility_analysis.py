"""Own invented-only integer layout geometry. No IO, codecs, CPU or emission.

LogicalSiteId and SyntheticAssignedPC are separate audit concepts.
A verified interval/delta is not a physical ROM placement or native safe exit.
The pinned M2bd JSON below is retained STATIC metadata, not executable semantics.
"""
import json

UPSTREAM = json.loads(r'''{"schemaVersion":1,"classification":"ReviewedStaticTypedLoweringSpecification","exactBase":"8fe005d1ba5f7b18f8df391b3fdf09d6330fad8e","sourceBindings":[{"file":"word0196_ir.json","bytes":32188,"sha256":"4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4"},{"file":"target_abi_contract.json","bytes":40753,"sha256":"1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66"},{"file":"independent_encoder_design.json","bytes":21765,"sha256":"9403279ed7570f1cb36280954a0f3249d41de2d64ae767b840649b066c625be9"},{"file":"independent_encoder.py","bytes":9868,"sha256":"603092893afbdb3d69cbcd43585ff6fc9886c45919920f432ec4b2905d830879"},{"file":"independent_encoder_contract.json","bytes":12182,"sha256":"414e5326cec42538ea6b64aa12a810c9d548c8b755b61a4f5c285b60c1837d47"},{"file":"independent_decoder.py","bytes":11036,"sha256":"e91c862d07d102c67ffa471603744c87eaee6d940fd27305e524afc91b946404"},{"file":"independent_decode_encode_contract.json","bytes":17800,"sha256":"547a09d9cd60dc6e2543870a5a5d0ee228e1051c28748fc53a526208355f5f2d"}],"components":{"m2av":"BoundedSourceLevelEquivalenceEstablished","m2aw":"TargetArchitectureContextEstablished","m2ba":"IndependentEncoderRouteSpecified","m2bb":"Independent15FormSyntheticEncodingVerified","m2bc":"Independent15FormDecodeEncodeCompatibilityVerified","runnerVersion":"0.43.0","protocol":1,"fixIdentities":38,"encoderDecoderUse":"PublicImmutableTypesOnly_NoFragmentCalls"},"primarySources":{"manual":"Oki_66201_Instruction_Manual.pdf","edition":"September1991","manualSha256":"f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271","manufacturerExpectationsSha256":"a268815a0c04a4e2f0fccb64021ead26e1cbdaa02c1cc435d816f7d35fa2ab44","instructionPdfPages":[76,77,90,119,120,121,124,153,160,163,173,197,208],"excludedSemanticsInputs":["ASM662","DASM662","Doc66207OpcodeTable","GeneratedThirdPartyOpcodeTables","EncoderOutput","RustOpcodeTables"],"priorThirdPartyExposureDisclosed":true,"legalCleanRoomCertification":false},"context":{"requiredLRB":33,"currentPage":256,"localBankBase":264,"localBankEnd":271,"SCB":"DerivedPSWLowThreeBits","fixedSCBAssumption":null,"initialDD":[0,1],"AL":{"widthBits":8,"nativeAddress":6},"AH":{"widthBits":8,"nativeAddress":7,"preservation":"AllScopedSites"},"A":{"widthBits":16,"lowAlias":"AL","highAlias":"AH"},"localRegisters":[{"name":"r0","address":264,"widthBits":8},{"name":"r1","address":265,"widthBits":8}],"registerPairAliases":[{"name":"er0","lowRegister":"r0","highRegister":"r1","lowAddress":264,"highAddress":265},{"name":"er1","lowRegister":"r2","highRegister":"r3","lowAddress":266,"highAddress":267},{"name":"er2","lowRegister":"r4","highRegister":"r5","lowAddress":268,"highAddress":269},{"name":"er3","lowRegister":"r6","highRegister":"r7","lowAddress":270,"highAddress":271}],"localPairByteOrder":"LittleEndian","r1WriteAlias":"OnlyHighByteOfEr0ChangesAt557F;R0LowByteRetained","LRBRebasingAllowed":false,"hostPointerCastsAllowed":false,"aliasesOutsideScope":"NotEstablished;NoGlobalAliasAbsenceClaim"},"addressObligations":[{"nativeAddress":279,"rawOffset":23,"widthBits":8,"operandKind":"PageOffset8","mode":"CurrentPage","requiredLRB":33,"byteOrder":"Byte","highByteAddress":null},{"nativeAddress":292,"rawOffset":36,"widthBits":8,"operandKind":"PageOffset8","mode":"CurrentPage","requiredLRB":33,"byteOrder":"Byte","highByteAddress":null},{"nativeAddress":298,"rawOffset":42,"widthBits":8,"operandKind":"PageOffset8","mode":"CurrentPage","requiredLRB":33,"byteOrder":"Byte","highByteAddress":null},{"nativeAddress":398,"rawOffset":142,"widthBits":8,"operandKind":"PageOffset8","mode":"CurrentPage","requiredLRB":33,"byteOrder":"Byte","highByteAddress":null},{"nativeAddress":399,"rawOffset":143,"widthBits":8,"operandKind":"PageOffset8","mode":"CurrentPage","requiredLRB":33,"byteOrder":"Byte","highByteAddress":null},{"nativeAddress":406,"rawOffset":150,"widthBits":16,"operandKind":"EvenPageOffset8","mode":"CurrentPage","requiredLRB":33,"byteOrder":"LittleEndian","highByteAddress":407}],"flagDomain":{"arithmeticFlags":["CF","ZF","HC"],"DD":"FormSelectionAndTransferNotArithmeticOperand","scalarDomain":["CF","ZF","HC","DD","PSW0","PSW1","PSW2","PSW3","PSW4","PSW5","PSW6","PSW7","PSW8","PSW9","PSW10","PSW11"],"groupedOtherPSW":["PSW0","PSW1","PSW2","PSW3","PSW4","PSW5","PSW6","PSW7","PSW8","PSW9","PSW10","PSW11"],"SCBBits":[0,1,2],"functionalEntryLive":["HC","OtherPSW"],"initialCF":"RetainedBy556FThenKilledBy5571BeforeFunctionalRead","initialZF":"KilledBy556FBeforeFunctionalRead","initialDD":"EitherAcceptedThenKilledBy556F;NotOrdinaryArithmeticUse","terminalObservable":["CF","ZF","HC","DD","OtherPSW"],"intermediateWrites":"AllNativeFlagWritesRetainedEvenWhenFunctionallyDead","futureMayClobber":false,"livenessPolicy":"BackwardFunctionalAndDDSelectionSeparate;RetainedTerminalSnapshot;NoOptimizationPermission"},"sites":[{"pc":21871,"formId":"lb-a-page","length":2,"typedOperands":[{"kind":"AccumulatorA"},{"kind":"PageOffset8","value":142}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"SetsDD0WhenExecuted"},"flags":{"functionalRead":[],"written":["ZF","DD"],"preserved":["CF","HC","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[]},"successors":[21873],"branch":null,"primary":{"pdfPage":124,"printedPage":"3-70"}},{"pc":21873,"formId":"sllb-a","length":1,"typedOperands":[{"kind":"AccumulatorA"}],"dataWidthBits":8,"dd":{"selection":"RequiresDD0","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":["CF"],"preserved":["ZF","HC","DD","OtherPSW"],"selectionRead":["DD"]},"memory":{"reads":[],"writes":[]},"successors":[21874],"branch":null,"primary":{"pdfPage":197,"printedPage":"3-144"}},{"pc":21874,"formId":"rolb-page","length":3,"typedOperands":[{"kind":"PageOffset8","value":142}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"PreservesDD"},"flags":{"functionalRead":["CF"],"written":["CF"],"preserved":["ZF","HC","DD","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[{"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteRotateThroughCarry","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}]},"successors":[21877],"branch":null,"primary":{"pdfPage":173,"printedPage":"3-120"}},{"pc":21877,"formId":"lb-a-r0","length":1,"typedOperands":[{"kind":"AccumulatorA"},{"kind":"Register0","value":0}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"SetsDD0WhenExecuted"},"flags":{"functionalRead":[],"written":["ZF","DD"],"preserved":["CF","HC","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":264,"widthBits":8,"mode":"LocalRegister","byteOrder":"Byte"}],"writes":[]},"successors":[21878],"branch":null,"primary":{"pdfPage":124,"printedPage":"3-70"}},{"pc":21878,"formId":"andb-a-page","length":2,"typedOperands":[{"kind":"AccumulatorA"},{"kind":"PageOffset8","value":142}],"dataWidthBits":8,"dd":{"selection":"RequiresDD0","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":["ZF"],"preserved":["CF","HC","DD","OtherPSW"],"selectionRead":["DD"]},"memory":{"reads":[{"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[]},"successors":[21880],"branch":null,"primary":{"pdfPage":76,"printedPage":"3-24"}},{"pc":21880,"formId":"cmp-page-imm16","length":5,"typedOperands":[{"kind":"EvenPageOffset8","value":150},{"kind":"Immediate16","value":192}],"dataWidthBits":16,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":["CF","ZF"],"preserved":["HC","DD","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":406,"widthBits":16,"mode":"CurrentPage","byteOrder":"LittleEndian"}],"writes":[]},"successors":[21885],"branch":null,"primary":{"pdfPage":90,"printedPage":"3-38"}},{"pc":21885,"formId":"jlt-rel8","length":2,"typedOperands":[{"kind":"TargetPC16","value":21951}],"dataWidthBits":null,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"PreservesDD"},"flags":{"functionalRead":["CF"],"written":[],"preserved":["CF","ZF","HC","DD","OtherPSW"],"selectionRead":[]},"memory":{"reads":[],"writes":[]},"successors":[21951,21887],"branch":{"predicate":{"kind":"FlagEquals","flag":"CF","value":1},"producerPc":21880,"trueTarget":21951,"falseTarget":21887,"mathematicalSignedDistance":64},"primary":{"pdfPage":120,"printedPage":"3-66/3-67"}},{"pc":21887,"formId":"movb-r1-page","length":3,"typedOperands":[{"kind":"Register1","value":1},{"kind":"PageOffset8","value":23}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":[],"preserved":["CF","ZF","HC","DD","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[{"address":265,"widthBits":8,"mode":"LocalRegister","byteOrder":"Byte","operation":"CopyByte","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}]},"successors":[21890],"branch":null,"primary":{"pdfPage":153,"printedPage":"3-99"}},{"pc":21890,"formId":"andb-page-a","length":3,"typedOperands":[{"kind":"PageOffset8","value":23},{"kind":"AccumulatorA"}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":["ZF"],"preserved":["CF","HC","DD","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[{"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteAnd","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}]},"successors":[21893],"branch":null,"primary":{"pdfPage":77,"printedPage":"3-25"}},{"pc":21893,"formId":"jbs-page-bit7","length":3,"typedOperands":[{"kind":"PageBit7","offset":42,"bit":7},{"kind":"TargetPC16","value":21906}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":[],"preserved":["CF","ZF","HC","DD","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":298,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[]},"successors":[21906,21896],"branch":{"predicate":{"kind":"MemoryBitEquals","address":298,"bit":7,"value":1},"producerPc":null,"trueTarget":21906,"falseTarget":21896,"mathematicalSignedDistance":10},"primary":{"pdfPage":119,"printedPage":"3-65"}},{"pc":21896,"formId":"jbs-page-bit5","length":3,"typedOperands":[{"kind":"PageBit5","offset":36,"bit":5},{"kind":"TargetPC16","value":21906}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":[],"preserved":["CF","ZF","HC","DD","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":292,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[]},"successors":[21906,21899],"branch":{"predicate":{"kind":"MemoryBitEquals","address":292,"bit":5,"value":1},"producerPc":null,"trueTarget":21906,"falseTarget":21899,"mathematicalSignedDistance":7},"primary":{"pdfPage":119,"printedPage":"3-65"}},{"pc":21899,"formId":"andb-page-a","length":3,"typedOperands":[{"kind":"PageOffset8","value":143},{"kind":"AccumulatorA"}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":["ZF"],"preserved":["CF","HC","DD","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[{"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteAnd","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}]},"successors":[21902],"branch":null,"primary":{"pdfPage":77,"printedPage":"3-25"}},{"pc":21902,"formId":"orb-page-imm8","length":4,"typedOperands":[{"kind":"PageOffset8","value":42},{"kind":"Immediate8","value":1}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":["ZF"],"preserved":["CF","HC","DD","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":298,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[{"address":298,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteOr","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}]},"successors":[21906],"branch":null,"primary":{"pdfPage":163,"printedPage":"3-110"}},{"pc":21906,"formId":"lb-a-page","length":2,"typedOperands":[{"kind":"AccumulatorA"},{"kind":"PageOffset8","value":143}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"SetsDD0WhenExecuted"},"flags":{"functionalRead":[],"written":["ZF","DD"],"preserved":["CF","HC","OtherPSW"],"selectionRead":[]},"memory":{"reads":[{"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"writes":[]},"successors":[21908],"branch":null,"primary":{"pdfPage":124,"printedPage":"3-70"}},{"pc":21908,"formId":"orb-a-imm8","length":2,"typedOperands":[{"kind":"AccumulatorA"},{"kind":"Immediate8","value":240}],"dataWidthBits":8,"dd":{"selection":"RequiresDD0","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":["ZF"],"preserved":["CF","HC","DD","OtherPSW"],"selectionRead":["DD"]},"memory":{"reads":[],"writes":[]},"successors":[21910],"branch":null,"primary":{"pdfPage":160,"printedPage":"3-107"}},{"pc":21951,"formId":"lb-a-imm8","length":2,"typedOperands":[{"kind":"AccumulatorA"},{"kind":"Immediate8","value":15}],"dataWidthBits":8,"dd":{"selection":"AcceptsBothIncomingDD","transfer":"SetsDD0WhenExecuted"},"flags":{"functionalRead":[],"written":["ZF","DD"],"preserved":["CF","HC","OtherPSW"],"selectionRead":[]},"memory":{"reads":[],"writes":[]},"successors":[21953],"branch":null,"primary":{"pdfPage":124,"printedPage":"3-70"}},{"pc":21953,"formId":"stb-a-page","length":2,"typedOperands":[{"kind":"AccumulatorA"},{"kind":"PageOffset8","value":23}],"dataWidthBits":8,"dd":{"selection":"RequiresDD0","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":[],"preserved":["CF","ZF","HC","DD","OtherPSW"],"selectionRead":["DD"]},"memory":{"reads":[],"writes":[{"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"StoreByte","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}]},"successors":[21955],"branch":null,"primary":{"pdfPage":208,"printedPage":"3-155"}},{"pc":21955,"formId":"stb-a-page","length":2,"typedOperands":[{"kind":"AccumulatorA"},{"kind":"PageOffset8","value":143}],"dataWidthBits":8,"dd":{"selection":"RequiresDD0","transfer":"PreservesDD"},"flags":{"functionalRead":[],"written":[],"preserved":["CF","ZF","HC","DD","OtherPSW"],"selectionRead":["DD"]},"memory":{"reads":[],"writes":[{"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"StoreByte","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}]},"successors":[21957],"branch":null,"primary":{"pdfPage":208,"printedPage":"3-155"}}],"cfg":{"entryPc":21871,"stopBeforePcs":[21910,21957],"completePaths":4,"pathLengths":[10,12,13,15],"allSitesMustReachable":true,"cyclesAllowed":false,"undefinedSuccessorsAllowed":false,"extraTerminalsAllowed":false,"terminalInstructionsExecuted":false,"originalPCs":"AuditedIdentityOnly_NotPlacementPermission","relativeDistance":"MathematicalIntegers_NoWrap_NoBytes_NoRelaxation_NoRelocation"},"pathObligations":[{"id":"A","pcs":[21871,21873,21874,21877,21878,21880,21885,21951,21953,21955],"conditions":[{"pc":21885,"result":true}],"terminal":21957,"historical":"HistoricalNativeValidated","instructionCount":10,"orderedReads":[{"pc":21871,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21874,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21877,"address":264,"widthBits":8,"mode":"LocalRegister","byteOrder":"Byte"},{"pc":21878,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21880,"address":406,"widthBits":16,"mode":"CurrentPage","byteOrder":"LittleEndian"}],"orderedWrites":[{"pc":21874,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteRotateThroughCarry","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21953,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"StoreByte","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21955,"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"StoreByte","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}],"mustNotRead":[],"finalAL":{"kind":"ConstantByte","value":15},"finalCF":1,"finalZF":0,"finalDD":0},{"id":"B","pcs":[21871,21873,21874,21877,21878,21880,21885,21887,21890,21893,21906,21908],"conditions":[{"pc":21885,"result":false},{"pc":21893,"result":true}],"terminal":21910,"historical":"HistoricalNativeValidated","instructionCount":12,"orderedReads":[{"pc":21871,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21874,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21877,"address":264,"widthBits":8,"mode":"LocalRegister","byteOrder":"Byte"},{"pc":21878,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21880,"address":406,"widthBits":16,"mode":"CurrentPage","byteOrder":"LittleEndian"},{"pc":21887,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21890,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21893,"address":298,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21906,"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"orderedWrites":[{"pc":21874,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteRotateThroughCarry","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21887,"address":265,"widthBits":8,"mode":"LocalRegister","byteOrder":"Byte","operation":"CopyByte","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21890,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteAnd","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}],"mustNotRead":[292],"finalAL":{"kind":"FinalMemoryOrImmediate","address":399,"immediate":240},"finalCF":0,"finalZF":0,"finalDD":0},{"id":"C","pcs":[21871,21873,21874,21877,21878,21880,21885,21887,21890,21893,21896,21906,21908],"conditions":[{"pc":21885,"result":false},{"pc":21893,"result":false},{"pc":21896,"result":true}],"terminal":21910,"historical":"StaticPrimaryAndInventedCoverage","instructionCount":13,"orderedReads":[{"pc":21871,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21874,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21877,"address":264,"widthBits":8,"mode":"LocalRegister","byteOrder":"Byte"},{"pc":21878,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21880,"address":406,"widthBits":16,"mode":"CurrentPage","byteOrder":"LittleEndian"},{"pc":21887,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21890,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21893,"address":298,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21896,"address":292,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21906,"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"orderedWrites":[{"pc":21874,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteRotateThroughCarry","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21887,"address":265,"widthBits":8,"mode":"LocalRegister","byteOrder":"Byte","operation":"CopyByte","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21890,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteAnd","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}],"mustNotRead":[],"finalAL":{"kind":"FinalMemoryOrImmediate","address":399,"immediate":240},"finalCF":0,"finalZF":0,"finalDD":0},{"id":"D","pcs":[21871,21873,21874,21877,21878,21880,21885,21887,21890,21893,21896,21899,21902,21906,21908],"conditions":[{"pc":21885,"result":false},{"pc":21893,"result":false},{"pc":21896,"result":false}],"terminal":21910,"historical":"HistoricalNativeValidated","instructionCount":15,"orderedReads":[{"pc":21871,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21874,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21877,"address":264,"widthBits":8,"mode":"LocalRegister","byteOrder":"Byte"},{"pc":21878,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21880,"address":406,"widthBits":16,"mode":"CurrentPage","byteOrder":"LittleEndian"},{"pc":21887,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21890,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21893,"address":298,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21896,"address":292,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21899,"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21902,"address":298,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"},{"pc":21906,"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte"}],"orderedWrites":[{"pc":21874,"address":398,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteRotateThroughCarry","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21887,"address":265,"widthBits":8,"mode":"LocalRegister","byteOrder":"Byte","operation":"CopyByte","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21890,"address":279,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteAnd","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21899,"address":399,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteAnd","ordered":true,"sameValueWrite":"RetainFreshOrdinal"},{"pc":21902,"address":298,"widthBits":8,"mode":"CurrentPage","byteOrder":"Byte","operation":"ReadModifyWriteOr","ordered":true,"sameValueWrite":"RetainFreshOrdinal"}],"mustNotRead":[],"finalAL":{"kind":"FinalMemoryOrImmediate","address":399,"immediate":240},"finalCF":0,"finalZF":0,"finalDD":0}],"terminalObligations":[{"pc":21910,"branch":"NotBelow","AL":{"kind":"FinalMemoryOrImmediate","address":399,"immediate":240},"CF":0,"ZF":0,"DD":0,"HC":"IncomingHC","OtherPSW":"IncomingOtherPSW","AH":"IncomingAH"},{"pc":21957,"branch":"Below","AL":{"kind":"ConstantByte","value":15},"CF":1,"ZF":0,"DD":0,"HC":"IncomingHC","OtherPSW":"IncomingOtherPSW","AH":"IncomingAH"}],"provenance":{"data0196":"Native05EBWriterGeneration;Historical54FAAnd5578ReadSameGeneration","data0117":"RetainedOnceInitialThenNativeWriteHistory","data018e":"InitialScratchThenNative5572History","data018f":"InitialScratchThenBranchSpecificNativeWriteHistory","data012a":"RetainedNeighborBits;Bit0WriteOnly558E","data0124":"UpstreamNativeOwnership","data0128bit2":"OnceInitialMaskedHistory;NoScopedAccess","transition05ed54f5":"ExplicitHarnessSchedule","nativeOwnerAcceptedFromHost":false,"secondMachineHandoff":false,"reseedAt556f":false,"syntheticSSPFrame":false,"extraEventSource":false,"physicalMeaning":"Unknown","currentWord0196PhysicalRole":"Unknown","historicalCompletedObservations":42,"historicalSnapshots":552,"historicalOrderedWrites":170,"historicalNativePath13Witnesses":0},"nativeBoundary":{"entry":"NativeBasicBlockEntry","nativeCFunctionEntry":"NotEstablished","calFrameAt556f":"NotEstablished","ordinaryReturnAllowed":false,"stopBoundariesAreRT":false,"preserved":["AH","HC","OtherPSW","SCB","LRB","X1","X2","DP","USP","SSP","SFHostReplay","localr0","localr2..r7","DATA0124","DATA0128","DATA0196","DATA0197","UnrepresentedNativeStateRequiresFutureProof"],"exitOutputs":["A_AL_AH","PSW","LRB","SCB","PointingRegisterBanks","SSP","RelevantRAM","OrderedWrites","BranchSelectedContinuation"],"adapter":"NotImplemented","prologueEpilogueAllowed":false,"pushPopAllowed":false,"sf":"PrimaryConflictUnresolved;NoNativeBooleanInterpretation","stackSafety":"NotEstablished","codePlacement":"NotEstablished","widerContinuationLiveness":"NotEstablished"},"unresolved":{"targetCompilerABI":"NotEstablished","SFMeaningStorageWidth":"PrimaryConflictUnresolved","stackSafety":"NotEstablished","codePlacement":"NotEstablished","targetMachineCodeEquivalence":"NotEstablished","nativeProgramEquivalence":"NotEstablished","firmwareIntegration":"NotEstablished","recoveredECUScheduler":"NotEstablished","coherentResetFullbootFlow":"NotEstablished"},"permissions":{"runtimeExecution":false,"productionAdmission":false,"CPUExecution":false,"RAMExecution":false,"encoderOriginalSiteCalls":false,"decoderNativeFragmentCalls":false,"targetByteEmission":false,"instructionConcatenation":false,"assemblyText":false,"symbolResolution":false,"codePlacement":false,"linkerRelocation":false,"branchRelaxation":false,"nativeOwnerCreation":false,"firmwareReady":false,"ROMReplacement":false,"GUIExecution":false,"hardwareExecution":false},"counts":{"actualROMExecutions":0,"ASM662Executions":0,"nativeAssemblerExecutions":0,"codegenExecutions":0,"emittedTargetBytes":0,"instructionStreams":0,"targetAssemblyFiles":0,"targetObjects":0,"targetHEX":0,"FirmwareBIN":0,"inquiriesSent":0},"historicalStatuses":{"m2bc":"DecodeEncodeCompatibilityVerified","m2bb":"IndependentEncoderVerified","m2ba":"IndependentRouteSpecified","m2az":"HistoricalSourceRightsBlocked","m2ay":"ASM662BuildEncodingBlocked","m2ax":"MAC66KAcquisitionBlocked","m2aw":"ArchitectureContextEstablished","m2av":"BoundedSourceEquivalenceEstablished","m2au":"INTAccountingComplete","m2at":"DECDPHCFixComplete","m2an":"SLLBFixComplete","WDT3C":"ResearchBlocked","JGT_C8":"PrimaryConflictUnresolved","m2aqCAL2689_RT5C80":"NotRun","m2ap":"SSPADCBlocked","m2ao":"DATA019BFrontierUnchanged","m2ah":"STOPBefore5722","DATA019B2RuntimeOwner":"NotEstablished","m2t":"JGT233ABlockedUnresolved","StrictM2i":"Blocked","IRQ":"NotInjected","TimerEvolution":"NotModeled","RecoveredECUScheduler":"NotEstablished","TargetCompilerABI":"NotEstablished","TargetIntegration":"NotEstablished","Readiness":"PcInspectionOnly_NotFlashReady","PhysicalFuelTimeDegrees":"Unavailable","GUIHardwareFullboot":"NotRun","ASM662_WDT_C8Inquiries":"NotSent"}}''')
BLOCKS = {
    "Common": (0x556F, 0x5571, 0x5572, 0x5575, 0x5576, 0x5578, 0x557D),
    "NotBelow": (0x557F, 0x5582, 0x5585, 0x5588, 0x558B, 0x558E, 0x5592, 0x5594),
    "Below": (0x55BF, 0x55C1, 0x55C3),
}
# Own reviewed logical identities/lengths; no encoding definitions or bytes.
INVENTORY = (
    (0x556F, "lb-a-page", 2), (0x5571, "sllb-a", 1), (0x5572, "rolb-page", 3),
    (0x5575, "lb-a-r0", 1), (0x5576, "andb-a-page", 2), (0x5578, "cmp-page-imm16", 5),
    (0x557D, "jlt-rel8", 2), (0x557F, "movb-r1-page", 3), (0x5582, "andb-page-a", 3),
    (0x5585, "jbs-page-bit7", 3), (0x5588, "jbs-page-bit5", 3), (0x558B, "andb-page-a", 3),
    (0x558E, "orb-page-imm8", 4), (0x5592, "lb-a-page", 2), (0x5594, "orb-a-imm8", 2),
    (0x55BF, "lb-a-imm8", 2), (0x55C1, "stb-a-page", 2), (0x55C3, "stb-a-page", 2),
)
CONTEXT_KEYS = ("context", "addressObligations", "flagDomain", "pathObligations",
                "terminalObligations", "provenance", "nativeBoundary", "unresolved")
PROOF_LEVELS = {
    "instructionGeometry": "InstructionSpanGeometryVerified",
    "internalCFG": "SyntheticInternalBranchReachVerified",
    "context": "StaticContextPreservationObligationsVerified",
    "nativeExitIsolation": "NativeExitIsolationNotEstablished",
    "physicalROMPlacement": "PhysicalROMPlacementNotEstablished",
    "targetProgramEquivalence": "TargetProgramEquivalenceNotEstablished",
    "firmwareIntegration": "FirmwareIntegrationNotEstablished",
}
CONTEXT_RETENTION = {
    "initialDD": [0, 1], "DD0After556F": True,
    "carryDependencies": [{"producer": 0x5571, "consumer": 0x5572}, {"producer": 0x5578, "consumer": 0x557D}],
    "HC": "Preserved", "OtherPSW": "Preserved", "AH": "Preserved", "LRB": 33,
    "currentPage": 256, "localBank": [264, 271], "SCB": "IncomingPSWLowThreeBits_NotFixed",
    "SSP": "Retained_NoFrameEstablished", "SF": "PrimaryConflictUnresolved",
    "dataAddresses": [0x117, 0x124, 0x128, 0x12A, 0x18E, 0x18F, 0x196, 0x197],
    "RAMAddressesRelocated": False, "r1Alias": "HighByteEr0_R0Retained_NotWholeEr0",
    "word0196": "EvenLE16_CodeOwned00C0_NotRAM00C0",
    "potentialWordAliases": [[0x116, 0x117], [0x124, 0x125], [0x128, 0x129],
                            [0x12A, 0x12B], [0x18E, 0x18F], [0x196, 0x197]],
    "stackAliases": "UnknownSSPMayAliasRegistersRamOrSFR", "runtimeContextVerified": False,
    "nativeOwnerCreated": False,
}
ERROR_CODES = frozenset(("RequestShape", "Classification", "InventoryMismatch", "SiteIdentityMismatch",
    "FormMismatch", "LengthMismatch", "CFGChanged", "ContextMismatch", "UpstreamIdentity",
    "BlockOrderInvalid", "EntryBlockOrder", "GapInvalid", "AssignmentShape", "AssignmentInventory",
    "OriginInvalid", "LengthInvalid", "SpanOutsideProfile", "InstructionOverlap",
    "FallthroughMismatch", "BranchNextOutsideProfile", "TargetInvalid", "Rel8OutOfRange",
    "AssignmentModelMismatch", "Contract", "SourcePolicy", "SourceIdentity"))


class LayoutError(ValueError):
    """Explicit deterministic refusal, never a partial target artifact."""

    def __init__(self, code, path, stage):
        self.code, self.path, self.stage = code, path, stage
        self.args = (f"{stage}/{code}: {path}",)


def demand(condition, code, path, stage):
    if not condition:
        raise LayoutError(code, path, stage)


def strict_same(value, expected):
    if type(value) is not type(expected):
        return False
    if type(value) is dict:
        return value.keys() == expected.keys() and all(strict_same(value[k], expected[k]) for k in value)
    if type(value) in (list, tuple):
        return len(value) == len(expected) and all(strict_same(a, b) for a, b in zip(value, expected))
    return value == expected


def expect(value, expected, code, path, stage):
    demand(strict_same(value, expected), code, path, stage)


def _copy(value):
    # Metadata JSON copying only, not a machine-code serialization API.
    return json.loads(json.dumps(value, ensure_ascii=True))


def instruction_span(start, length):
    """Standalone interval arithmetic, not an admitted new instruction."""
    demand(type(start) is int and 0 <= start <= 65535, "OriginInvalid", "span.start", "Span")
    demand(type(length) is int and 1 <= length <= 5, "LengthInvalid", "span.length", "Span")
    end = start + length
    demand(end <= 65536, "SpanOutsideProfile", "span.endExclusive", "Span")
    return {"start": start, "endExclusive": end, "lastByte": end - 1}


def branch_geometry(start, length, target):
    """Standalone mathematical boundary control; no rel8 byte construction."""
    span = instruction_span(start, length)
    next_pc = span["endExclusive"]
    demand(next_pc <= 65535, "BranchNextOutsideProfile", "branch.nextPC", "Branch")
    demand(type(target) is int and 0 <= target <= 65535, "TargetInvalid", "branch.target", "Branch")
    delta = target - next_pc
    demand(-128 <= delta <= 127, "Rel8OutOfRange", "branch.signedDelta", "Branch")
    return {"nextPC": next_pc, "signedDelta": delta, "feasible": True}


def reviewed_inventory(upstream):
    """Keep inherited static obligations exact; do not rerun CPU/codec logic."""
    demand(type(upstream) is dict and type(upstream.get("sites")) is list
           and len(upstream["sites"]) == 18, "InventoryMismatch", "upstream.sites", "Inventory")
    ids = [s.get("pc") if type(s) is dict else None for s in upstream["sites"]]
    demand(all(type(pc) is int for pc in ids) and len(set(ids)) == 18,
           "InventoryMismatch", "upstream.siteIdentities", "Inventory")
    for index, (pc, form, length) in enumerate(INVENTORY):
        site, old = upstream["sites"][index], UPSTREAM["sites"][index]
        expect(site.get("pc"), pc, "SiteIdentityMismatch", f"upstream.sites.{index}.pc", "Inventory")
        expect(site.get("formId"), form, "FormMismatch", f"upstream.sites.{index}.formId", "Inventory")
        expect(site.get("length"), length, "LengthMismatch", f"upstream.sites.{index}.length", "Inventory")
        for key in ("successors", "branch"):
            expect(site.get(key), old[key], "CFGChanged", f"upstream.sites.{index}.{key}", "Inventory")
        for key in ("typedOperands", "dataWidthBits", "dd", "flags", "memory", "primary"):
            expect(site.get(key), old[key], "ContextMismatch", f"upstream.sites.{index}.{key}", "Context")
        expect(set(site), set(old), "ContextMismatch", f"upstream.sites.{index}.schema", "Context")
    expect(upstream.get("cfg"), UPSTREAM["cfg"], "CFGChanged", "upstream.cfg", "Inventory")
    for key in CONTEXT_KEYS:
        expect(upstream.get(key), UPSTREAM[key], "ContextMismatch", f"upstream.{key}", "Context")
    expect(upstream, UPSTREAM, "UpstreamIdentity", "upstream.completeStaticContract", "Inventory")
    return {s["pc"]: s for s in upstream["sites"]}


def original_geometry(upstream):
    sites = reviewed_inventory(upstream)
    lengths = {name: sum(sites[pc]["length"] for pc in pcs) for name, pcs in BLOCKS.items()}
    original_start = min(sites)
    original_end = max(pc + s["length"] for pc, s in sites.items())
    not_below_end = max(pc + sites[pc]["length"] for pc in BLOCKS["NotBelow"])
    below_start = min(BLOCKS["Below"])
    return {"instructionSites": len(sites), "instructionLengthSum": sum(s["length"] for s in sites.values()),
            "blockLengths": lengths, "originalOuterEnvelope": original_end - original_start,
            "originalExcludedRegion": below_start - not_below_end}


def _logical_edges(sites):
    result = []
    for pc, site in sites.items():
        for index, successor in enumerate(site["successors"]):
            kind = ("AnalyticalTerminal" if successor in (0x5596, 0x55C5) else
                    "ConditionalTaken" if site["branch"] is not None and index == 0 else "Fallthrough")
            result.append((pc, successor, kind))
    return result


def _assign(sites, base, order, gaps):
    cursor, result = base, {}
    for index, name in enumerate(order):
        for pc in BLOCKS[name]:
            result[pc] = cursor
            cursor += sites[pc]["length"]
        if index < 2:
            cursor += gaps[index]
    return result


def evaluate_layout(upstream, request):
    """Accept only mathematical geometry; native exit remains execution-blocked.

    Precedence: inherited inventory/CFG/context, request schema, base/order/gaps,
    assignments, every span, overlap, real16 fallthrough checks, real3 branch
    checks, then symbolic block-plan consistency. Metadata errors never count as
    meaningful branch feasibility tests. Analytical end markers may be65536.
    """
    sites = reviewed_inventory(upstream)
    required = {"syntheticBase", "blockOrder", "gaps", "siteAssignments", "classification"}
    demand(type(request) is dict and set(request) == required, "RequestShape", "request", "Input")
    expect(request["classification"], "InventedOnlySymbolicLayout", "Classification", "request.classification", "Policy")
    base, order, gaps = request["syntheticBase"], request["blockOrder"], request["gaps"]
    demand(type(base) is int and 0 <= base <= 65535, "OriginInvalid", "request.syntheticBase", "Span")
    demand(type(order) is list and len(order) == 3 and all(type(n) is str for n in order)
           and set(order) == set(BLOCKS), "BlockOrderInvalid", "request.blockOrder", "Input")
    demand(order[0] == "Common", "EntryBlockOrder", "request.blockOrder.0", "Policy")
    demand(type(gaps) is list and len(gaps) == 2 and all(type(g) is int and g >= 0 for g in gaps),
           "GapInvalid", "request.gaps", "Input")
    expected = _assign(sites, base, order, gaps)
    override = request["siteAssignments"]
    if override is None:
        assigned = expected
    else:
        demand(type(override) is list and len(override) == 18 and all(type(row) is dict
               and set(row) == {"logicalSiteId", "syntheticAssignedPC"}
               and type(row["logicalSiteId"]) is int and type(row["syntheticAssignedPC"]) is int for row in override),
               "AssignmentShape", "request.siteAssignments", "Input")
        assigned = {row["logicalSiteId"]: row["syntheticAssignedPC"] for row in override}
        demand(len(assigned) == 18 and set(assigned) == set(sites), "AssignmentInventory", "request.siteAssignments", "Inventory")
    spans = {pc: instruction_span(assigned[pc], s["length"]) for pc, s in sites.items()}
    intervals = sorted((span["start"], span["endExclusive"], pc) for pc, span in spans.items())
    for left, right in zip(intervals, intervals[1:]):
        demand(left[1] <= right[0], "InstructionOverlap", f"{left[2]:04X}/{right[2]:04X}", "Overlap")
    logical_edges = _logical_edges(sites)
    for pc, successor, kind in logical_edges:
        if kind == "Fallthrough":
            demand(assigned[successor] == spans[pc]["endExclusive"], "FallthroughMismatch",
                   f"{pc:04X}->{successor:04X}", "Fallthrough")
    branches = {}
    for pc, successor, kind in logical_edges:
        if kind == "ConditionalTaken":
            branches[pc] = branch_geometry(assigned[pc], sites[pc]["length"], assigned[successor])
    # A negative-distance malformed arrangement can be tested before this policy,
    # but an override passing geometry still cannot silently change its block plan.
    expect(assigned, expected, "AssignmentModelMismatch", "request.siteAssignments.blockPlan", "Policy")
    terminals, terminal_addresses = [], {}
    for logical_stop, block in ((0x5596, "NotBelow"), (0x55C5, "Below")):
        end = spans[BLOCKS[block][-1]]["endExclusive"]
        terminal_addresses[logical_stop] = end
        adjacent = next((name for name, pcs in BLOCKS.items() if assigned[pcs[0]] == end), None)
        terminals.append({"logicalStopBefore": logical_stop, "assignedEndExclusive": end,
            "requiredContinuation": "ExternalNativeContinuationNotEstablished",
            "adjacentBlock": adjacent,
            "hazard": "PotentialFallthroughIntoSyntheticBlock" if adjacent is not None else "UnmodeledGapOrOutsideRegion",
            "nativeExitIsolation": "Blocked"})
    edges = []
    for pc, successor, kind in logical_edges:
        target = terminal_addresses[successor] if kind == "AnalyticalTerminal" else assigned[successor]
        edges.append({"source": pc, "target": successor, "kind": kind, "assignedSource": assigned[pc],
                      "nextPC": spans[pc]["endExclusive"], "assignedTarget": target,
                      "signedDelta": branches[pc]["signedDelta"] if kind == "ConditionalTaken" else None,
                      "feasible": True})
    holes = [{"start": left[1], "endExclusive": right[0],
              "classification": "UnmodeledSymbolicHole_NotPaddingOrFreeROM"}
             for left, right in zip(intervals, intervals[1:]) if left[1] < right[0]]
    end = max(span["endExclusive"] for span in spans.values())
    return {"passed": True, "classification": "InventedOnlySymbolicLayout",
            "geometry": original_geometry(upstream),
            "assignments": [{"logicalSiteId": pc, "syntheticAssignedPC": assigned[pc],
                "length": s["length"], "endExclusive": spans[pc]["endExclusive"], "formId": s["formId"]}
                for pc, s in sites.items()],
            "edges": edges, "terminalMarkers": terminals, "proofLevels": _copy(PROOF_LEVELS),
            "contextRetention": _copy(CONTEXT_RETENTION), "pathsLogical": _copy(upstream["pathObligations"]),
            "syntheticEnvelope": {"start": base, "endExclusive": end, "extent": end - base}, "holes": holes,
            "executionBlocked": True, "runtimePermission": False, "currentSourceStaticOnly": True,
            "historicalCoverageInheritedOnly": True, "targetBytes": 0, "encoderCalls": 0, "decoderCalls": 0,
            "CPUExecutions": 0, "actualROMExecutions": 0, "nativeWriteJournals": 0}
