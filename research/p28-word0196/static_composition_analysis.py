"""M2bh pure mathematical composition, never target emission or CPU execution.

Reviewed immutable metadata constrains this one twenty-node profile. Real CFG,
DD/flag dataflow, ordered IR effects and actual placement relations are computed
before the late closed-metadata guard. Ordinary metadata collections below are
not target instructions. The separate independent oracle predates this source.
"""
import json

_REVIEWED = json.loads("{\"schemaVersion\":1,\"classification\":\"ReviewedStatic20NodeCompositionSpecification\",\"exactBase\":\"bae6a4b12a9839738117bac805a485d38f92d18b\",\"upstreamBindings\":[{\"file\":\"research/p28-word0196/continuation_transfer_analysis.py\",\"bytes\":78628,\"sha256\":\"86eb302ae13138aef5a64b192e5d4b63982afa1e4bb3e9c4b3d71b9f927c355c\"},{\"file\":\"research/p28-word0196/continuation_transfer_oracle.py\",\"bytes\":12784,\"sha256\":\"5c250c75ee7d950e766cf747381efc125545b192a5c7d7b0e8b01a1c6b3909fb\"},{\"file\":\"research/p28-word0196/continuation_transfer_tests.py\",\"bytes\":19256,\"sha256\":\"e47b4e34bf2ee42e5e5f7c118becb9dffb71864e1a57030a9aedd2fbb83b833d\"},{\"file\":\"research/p28-word0196/direct_j_contract.json\",\"bytes\":23868,\"sha256\":\"1be70eb96f4c75c8f42729f2b41aacc2f43b4923c3db0aacccd1b5bc2a2a8c35\"},{\"file\":\"research/p28-word0196/direct_j_decoder.py\",\"bytes\":2006,\"sha256\":\"32738de208889d288856feda6f030c78b08d5cf3cf7ca0154120b32fc788c3a4\"},{\"file\":\"research/p28-word0196/direct_j_encoder.py\",\"bytes\":1926,\"sha256\":\"1149ba3fcc142fa1fb78677ddd14b8c4bbab1ee333ef926aaffe22839d7f6f60\"},{\"file\":\"research/p28-word0196/direct_j_primary_oracle.py\",\"bytes\":4051,\"sha256\":\"91793837663e8d0341ce0d4e224fc97e256c549409807ea9b43e8d9266f55f39\"},{\"file\":\"research/p28-word0196/direct_j_tests.py\",\"bytes\":18346,\"sha256\":\"c5a3cbb6f10b9cafaf342a0ed5b5bd86921f58fcfa9af1f469f1b741f6cc8d7c\"},{\"file\":\"research/p28-word0196/direct_j_types.py\",\"bytes\":3021,\"sha256\":\"f11877a07340b88a7c222acec250767524778955a96235a6dd147207fa99467b\"},{\"file\":\"research/p28-word0196/external_continuation_contract.json\",\"bytes\":58097,\"sha256\":\"bce975c6427e0ab9294af8227933f0b2553efa13a47b89383f53fc4ac6138660\"},{\"file\":\"research/p28-word0196/independent_decode_encode_contract.json\",\"bytes\":17800,\"sha256\":\"547a09d9cd60dc6e2543870a5a5d0ee228e1051c28748fc53a526208355f5f2d\"},{\"file\":\"research/p28-word0196/independent_decoder_primary_oracle.py\",\"bytes\":12745,\"sha256\":\"9154ceac6709d8ad93fa71ab77f5b1e5c601dbaa812d60d4e3681b08f4b8e1df\"},{\"file\":\"research/p28-word0196/independent_decoder_tests.py\",\"bytes\":19933,\"sha256\":\"cdc5d43ee866dba4fb619fc6169e2ec5e869d4050f98137bb67e62ca0a2bdb64\"},{\"file\":\"research/p28-word0196/independent_decoder.py\",\"bytes\":11036,\"sha256\":\"e91c862d07d102c67ffa471603744c87eaee6d940fd27305e524afc91b946404\"},{\"file\":\"research/p28-word0196/independent_encoder_contract.json\",\"bytes\":12182,\"sha256\":\"414e5326cec42538ea6b64aa12a810c9d548c8b755b61a4f5c285b60c1837d47\"},{\"file\":\"research/p28-word0196/independent_encoder_design.json\",\"bytes\":21765,\"sha256\":\"9403279ed7570f1cb36280954a0f3249d41de2d64ae767b840649b066c625be9\"},{\"file\":\"research/p28-word0196/independent_encoder_oracle.py\",\"bytes\":7092,\"sha256\":\"6575f802c0703da087f1f06fdff095dcf4c4b948b7fe59e8fb35972210cb6361\"},{\"file\":\"research/p28-word0196/independent_encoder_tests.py\",\"bytes\":18429,\"sha256\":\"76ca001260dbf07b0c5ad99f72e156732b940756af2c177e2b97311acba3b62c\"},{\"file\":\"research/p28-word0196/independent_encoder.py\",\"bytes\":9868,\"sha256\":\"603092893afbdb3d69cbcd43585ff6fc9886c45919920f432ec4b2905d830879\"},{\"file\":\"research/p28-word0196/layout_feasibility_analysis.py\",\"bytes\":40569,\"sha256\":\"840320c5eed83d2a393dd3d1f4c8b90cb0aa7608c5c2ba721384265e79d151db\"},{\"file\":\"research/p28-word0196/layout_feasibility_contract.json\",\"bytes\":66622,\"sha256\":\"9d1baf1e4914fa1b611924ff48b75854e9fc7d2e06e6e05542c56c14e18abb2f\"},{\"file\":\"research/p28-word0196/layout_feasibility_oracle.py\",\"bytes\":10843,\"sha256\":\"be17e854a1b474b3800b09d74219ba097fc48bd2a2a53db93752169c3da06394\"},{\"file\":\"research/p28-word0196/layout_feasibility_tests.py\",\"bytes\":26061,\"sha256\":\"55377f7bd6c6c0ad1b5c29e7cc66eeb32aa63a3db8d1b849318c98326d74cd5e\"},{\"file\":\"research/p28-word0196/target_abi_contract.json\",\"bytes\":40753,\"sha256\":\"1e8b20872693c0a7dcfbcfc867b85c55c3a759eef616651d6760c08b9dd5af66\"},{\"file\":\"research/p28-word0196/transfer_form_evidence.json\",\"bytes\":37225,\"sha256\":\"f4279b5c86cc78be18f641e0638ea58892329f0b8903db28a8b6b77d69d34194\"},{\"file\":\"research/p28-word0196/typed_lowering_analysis.py\",\"bytes\":31589,\"sha256\":\"bd0ad1ee186cb76922926a957c21bacafc601e77200ff3bdcdc09fd866143bc5\"},{\"file\":\"research/p28-word0196/typed_lowering_contract.json\",\"bytes\":44984,\"sha256\":\"6f62c23e99f72e7df51a0117b7c5ff600d892f2a8d3e4c4231a383e1d96c6bf4\"},{\"file\":\"research/p28-word0196/typed_lowering_oracle.py\",\"bytes\":12601,\"sha256\":\"2e7b613813e81cf54ea6ee17c378344800022454f8d0074af15ecec586a77e4a\"},{\"file\":\"research/p28-word0196/typed_lowering_tests.py\",\"bytes\":29917,\"sha256\":\"1e46516c85b1d0b0593b67e59943b7b2d459725a073f29f23d385f59f73d7c6a\"},{\"file\":\"research/p28-word0196/validate_direct_j_contract.py\",\"bytes\":37218,\"sha256\":\"207b658479da79f911e317df8a71402370e7336f3ddcaa7f65a28de6efad8e85\"},{\"file\":\"research/p28-word0196/validate_external_continuation_contract.py\",\"bytes\":76985,\"sha256\":\"6dfd2a85c6fa5187e4bb2649d8b96db2b61ffe584f0b9b7b4124fc058550da7e\"},{\"file\":\"research/p28-word0196/validate_layout_feasibility_contract.py\",\"bytes\":48319,\"sha256\":\"e6656112d6272adeac3f382ee672a4ddd3b01fe645dcab356444b0cefd6d51ea\"},{\"file\":\"research/p28-word0196/word0196_equivalent.c\",\"bytes\":8507,\"sha256\":\"4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3\"},{\"file\":\"research/p28-word0196/word0196_equivalent.h\",\"bytes\":2390,\"sha256\":\"df8da1511708fb29cb747981a959544e549a67a9a982e15586b5c12ce8826f0e\"},{\"file\":\"research/p28-word0196/word0196_ir.json\",\"bytes\":32188,\"sha256\":\"4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4\"},{\"file\":\"src/HondaEcu.Core/P28Word0196AlternateModel.cs\",\"bytes\":3464,\"sha256\":\"ac3162dfc6255e25ac24d7430531243f7856090ce55bab8b46e20d07f06fd74f\"}],\"originalSiteObligations\":[{\"pc\":21871,\"formId\":\"lb-a-page\",\"length\":2,\"typedOperands\":[{\"kind\":\"AccumulatorA\"},{\"kind\":\"PageOffset8\",\"value\":142}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"SetsDD0WhenExecuted\"},\"flags\":{\"functionalRead\":[],\"written\":[\"ZF\",\"DD\"],\"preserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[]},\"successors\":[21873],\"branch\":null,\"primary\":{\"pdfPage\":124,\"printedPage\":\"3-70\"}},{\"pc\":21873,\"formId\":\"sllb-a\",\"length\":1,\"typedOperands\":[{\"kind\":\"AccumulatorA\"}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"RequiresDD0\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[\"CF\"],\"preserved\":[\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[\"DD\"]},\"memory\":{\"reads\":[],\"writes\":[]},\"successors\":[21874],\"branch\":null,\"primary\":{\"pdfPage\":197,\"printedPage\":\"3-144\"}},{\"pc\":21874,\"formId\":\"rolb-page\",\"length\":3,\"typedOperands\":[{\"kind\":\"PageOffset8\",\"value\":142}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[\"CF\"],\"written\":[\"CF\"],\"preserved\":[\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[{\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteRotateThroughCarry\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}]},\"successors\":[21877],\"branch\":null,\"primary\":{\"pdfPage\":173,\"printedPage\":\"3-120\"}},{\"pc\":21877,\"formId\":\"lb-a-r0\",\"length\":1,\"typedOperands\":[{\"kind\":\"AccumulatorA\"},{\"kind\":\"Register0\",\"value\":0}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"SetsDD0WhenExecuted\"},\"flags\":{\"functionalRead\":[],\"written\":[\"ZF\",\"DD\"],\"preserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":264,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\"}],\"writes\":[]},\"successors\":[21878],\"branch\":null,\"primary\":{\"pdfPage\":124,\"printedPage\":\"3-70\"}},{\"pc\":21878,\"formId\":\"andb-a-page\",\"length\":2,\"typedOperands\":[{\"kind\":\"AccumulatorA\"},{\"kind\":\"PageOffset8\",\"value\":142}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"RequiresDD0\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[\"ZF\"],\"preserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[\"DD\"]},\"memory\":{\"reads\":[{\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[]},\"successors\":[21880],\"branch\":null,\"primary\":{\"pdfPage\":76,\"printedPage\":\"3-24\"}},{\"pc\":21880,\"formId\":\"cmp-page-imm16\",\"length\":5,\"typedOperands\":[{\"kind\":\"EvenPageOffset8\",\"value\":150},{\"kind\":\"Immediate16\",\"value\":192}],\"dataWidthBits\":16,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[\"CF\",\"ZF\"],\"preserved\":[\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":406,\"widthBits\":16,\"mode\":\"CurrentPage\",\"byteOrder\":\"LittleEndian\"}],\"writes\":[]},\"successors\":[21885],\"branch\":null,\"primary\":{\"pdfPage\":90,\"printedPage\":\"3-38\"}},{\"pc\":21885,\"formId\":\"jlt-rel8\",\"length\":2,\"typedOperands\":[{\"kind\":\"TargetPC16\",\"value\":21951}],\"dataWidthBits\":null,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[\"CF\"],\"written\":[],\"preserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[],\"writes\":[]},\"successors\":[21951,21887],\"branch\":{\"predicate\":{\"kind\":\"FlagEquals\",\"flag\":\"CF\",\"value\":1},\"producerPc\":21880,\"trueTarget\":21951,\"falseTarget\":21887,\"mathematicalSignedDistance\":64},\"primary\":{\"pdfPage\":120,\"printedPage\":\"3-66/3-67\"}},{\"pc\":21887,\"formId\":\"movb-r1-page\",\"length\":3,\"typedOperands\":[{\"kind\":\"Register1\",\"value\":1},{\"kind\":\"PageOffset8\",\"value\":23}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[],\"preserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[{\"address\":265,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\",\"operation\":\"CopyByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}]},\"successors\":[21890],\"branch\":null,\"primary\":{\"pdfPage\":153,\"printedPage\":\"3-99\"}},{\"pc\":21890,\"formId\":\"andb-page-a\",\"length\":3,\"typedOperands\":[{\"kind\":\"PageOffset8\",\"value\":23},{\"kind\":\"AccumulatorA\"}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[\"ZF\"],\"preserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[{\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}]},\"successors\":[21893],\"branch\":null,\"primary\":{\"pdfPage\":77,\"printedPage\":\"3-25\"}},{\"pc\":21893,\"formId\":\"jbs-page-bit7\",\"length\":3,\"typedOperands\":[{\"kind\":\"PageBit7\",\"offset\":42,\"bit\":7},{\"kind\":\"TargetPC16\",\"value\":21906}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[],\"preserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[]},\"successors\":[21906,21896],\"branch\":{\"predicate\":{\"kind\":\"MemoryBitEquals\",\"address\":298,\"bit\":7,\"value\":1},\"producerPc\":null,\"trueTarget\":21906,\"falseTarget\":21896,\"mathematicalSignedDistance\":10},\"primary\":{\"pdfPage\":119,\"printedPage\":\"3-65\"}},{\"pc\":21896,\"formId\":\"jbs-page-bit5\",\"length\":3,\"typedOperands\":[{\"kind\":\"PageBit5\",\"offset\":36,\"bit\":5},{\"kind\":\"TargetPC16\",\"value\":21906}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[],\"preserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":292,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[]},\"successors\":[21906,21899],\"branch\":{\"predicate\":{\"kind\":\"MemoryBitEquals\",\"address\":292,\"bit\":5,\"value\":1},\"producerPc\":null,\"trueTarget\":21906,\"falseTarget\":21899,\"mathematicalSignedDistance\":7},\"primary\":{\"pdfPage\":119,\"printedPage\":\"3-65\"}},{\"pc\":21899,\"formId\":\"andb-page-a\",\"length\":3,\"typedOperands\":[{\"kind\":\"PageOffset8\",\"value\":143},{\"kind\":\"AccumulatorA\"}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[\"ZF\"],\"preserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[{\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}]},\"successors\":[21902],\"branch\":null,\"primary\":{\"pdfPage\":77,\"printedPage\":\"3-25\"}},{\"pc\":21902,\"formId\":\"orb-page-imm8\",\"length\":4,\"typedOperands\":[{\"kind\":\"PageOffset8\",\"value\":42},{\"kind\":\"Immediate8\",\"value\":1}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[\"ZF\"],\"preserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[{\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteOr\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}]},\"successors\":[21906],\"branch\":null,\"primary\":{\"pdfPage\":163,\"printedPage\":\"3-110\"}},{\"pc\":21906,\"formId\":\"lb-a-page\",\"length\":2,\"typedOperands\":[{\"kind\":\"AccumulatorA\"},{\"kind\":\"PageOffset8\",\"value\":143}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"SetsDD0WhenExecuted\"},\"flags\":{\"functionalRead\":[],\"written\":[\"ZF\",\"DD\"],\"preserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[{\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"writes\":[]},\"successors\":[21908],\"branch\":null,\"primary\":{\"pdfPage\":124,\"printedPage\":\"3-70\"}},{\"pc\":21908,\"formId\":\"orb-a-imm8\",\"length\":2,\"typedOperands\":[{\"kind\":\"AccumulatorA\"},{\"kind\":\"Immediate8\",\"value\":240}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"RequiresDD0\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[\"ZF\"],\"preserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[\"DD\"]},\"memory\":{\"reads\":[],\"writes\":[]},\"successors\":[21910],\"branch\":null,\"primary\":{\"pdfPage\":160,\"printedPage\":\"3-107\"}},{\"pc\":21951,\"formId\":\"lb-a-imm8\",\"length\":2,\"typedOperands\":[{\"kind\":\"AccumulatorA\"},{\"kind\":\"Immediate8\",\"value\":15}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"SetsDD0WhenExecuted\"},\"flags\":{\"functionalRead\":[],\"written\":[\"ZF\",\"DD\"],\"preserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"selectionRead\":[]},\"memory\":{\"reads\":[],\"writes\":[]},\"successors\":[21953],\"branch\":null,\"primary\":{\"pdfPage\":124,\"printedPage\":\"3-70\"}},{\"pc\":21953,\"formId\":\"stb-a-page\",\"length\":2,\"typedOperands\":[{\"kind\":\"AccumulatorA\"},{\"kind\":\"PageOffset8\",\"value\":23}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"RequiresDD0\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[],\"preserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[\"DD\"]},\"memory\":{\"reads\":[],\"writes\":[{\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"StoreByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}]},\"successors\":[21955],\"branch\":null,\"primary\":{\"pdfPage\":208,\"printedPage\":\"3-155\"}},{\"pc\":21955,\"formId\":\"stb-a-page\",\"length\":2,\"typedOperands\":[{\"kind\":\"AccumulatorA\"},{\"kind\":\"PageOffset8\",\"value\":143}],\"dataWidthBits\":8,\"dd\":{\"selection\":\"RequiresDD0\",\"transfer\":\"PreservesDD\"},\"flags\":{\"functionalRead\":[],\"written\":[],\"preserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"selectionRead\":[\"DD\"]},\"memory\":{\"reads\":[],\"writes\":[{\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"StoreByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}]},\"successors\":[21957],\"branch\":null,\"primary\":{\"pdfPage\":208,\"printedPage\":\"3-155\"}}],\"originalIRInstructions\":[{\"pc\":21871,\"form\":{\"mnemonic\":\"LB A, off N8\",\"pinnedPatternIndex\":747,\"length\":2,\"ddMode\":\"R\",\"parsedOperation\":\"LB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\"],\"inputs\":[\"RAM018E:u8\",\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\",\"DD\"],\"flagsPreserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"effects\":[{\"op\":\"LoadAccumulatorLow\",\"type\":\"u8\",\"source\":{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"extension\":\"None\",\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"},{\"op\":\"AssignDataDescriptor\",\"type\":\"bool\",\"value\":false}],\"branchPredicate\":null,\"successors\":[21873],\"provenance\":{\"primaryPdfPage\":124,\"primaryPrintedPage\":\"3-70\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR556F\"]}},{\"pc\":21873,\"form\":{\"mnemonic\":\"SLLB A\",\"pinnedPatternIndex\":2198,\"length\":1,\"ddMode\":\"0\",\"parsedOperation\":\"SLLB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[\"CF\"],\"flagsPreserved\":[\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"LogicalShiftLeft\",\"type\":\"u8\",\"source\":\"AL\",\"distance\":1,\"truncation\":\"Modulo256\",\"zeroFill\":true},{\"op\":\"AssignCarryFromOldBit\",\"type\":\"bool\",\"source\":\"AL\",\"bit\":7}],\"branchPredicate\":null,\"successors\":[21874],\"provenance\":{\"primaryPdfPage\":197,\"primaryPrintedPage\":\"3-144\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5571\"]}},{\"pc\":21874,\"form\":{\"mnemonic\":\"ROLB off N8\",\"pinnedPatternIndex\":1862,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"ROLB\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM018E:u8\",\"CF:bool\"],\"outputs\":[\"RAM018E:u8\"],\"flagsRead\":[\"CF\"],\"flagsWritten\":[\"CF\"],\"flagsPreserved\":[\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ReadModifyWriteRotateThroughCarry\",\"type\":\"u8\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"direction\":\"Left\",\"distance\":1,\"carryInput\":\"IncomingCF\",\"carryOutput\":\"OldBit7\",\"truncation\":\"Modulo256\",\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"branchPredicate\":null,\"successors\":[21877],\"provenance\":{\"primaryPdfPage\":173,\"primaryPrintedPage\":\"3-120\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5572\"]}},{\"pc\":21877,\"form\":{\"mnemonic\":\"LB A, r0\",\"pinnedPatternIndex\":739,\"length\":1,\"ddMode\":\"R\",\"parsedOperation\":\"LB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"LocalRegister\",\"name\":\"r0\",\"widthBits\":8,\"address\":264}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0108:u8\",\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\",\"DD\"],\"flagsPreserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"effects\":[{\"op\":\"LoadAccumulatorLow\",\"type\":\"u8\",\"source\":{\"kind\":\"LocalRegister\",\"name\":\"r0\",\"widthBits\":8,\"address\":264},\"extension\":\"None\",\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"},{\"op\":\"AssignDataDescriptor\",\"type\":\"bool\",\"value\":false}],\"branchPredicate\":null,\"successors\":[21878],\"provenance\":{\"primaryPdfPage\":124,\"primaryPrintedPage\":\"3-70\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5575\"]}},{\"pc\":21878,\"form\":{\"mnemonic\":\"ANDB A, off N8\",\"pinnedPatternIndex\":333,\"length\":2,\"ddMode\":\"0\",\"parsedOperation\":\"ANDB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\",\"RAM018E:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"BitwiseAnd\",\"type\":\"u8\",\"destination\":{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},\"left\":\"AL\",\"right\":{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"}],\"branchPredicate\":null,\"successors\":[21880],\"provenance\":{\"primaryPdfPage\":76,\"primaryPrintedPage\":\"3-24\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5576\"]}},{\"pc\":21880,\"form\":{\"mnemonic\":\"CMP off N8, #N16\",\"pinnedPatternIndex\":498,\"length\":5,\"ddMode\":\"U\",\"parsedOperation\":\"CMP\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":406,\"widthBits\":16,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"LittleEndian\"},{\"kind\":\"CodeOwnedImmediate\",\"value\":192,\"widthBits\":16}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0196:u16\"],\"outputs\":[],\"flagsRead\":[],\"flagsWritten\":[\"CF\",\"ZF\"],\"flagsPreserved\":[\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"UnsignedCompare\",\"type\":\"u16\",\"left\":{\"kind\":\"CurrentPageRam\",\"address\":406,\"widthBits\":16,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"LittleEndian\"},\"right\":{\"kind\":\"CodeOwnedImmediate\",\"value\":192,\"widthBits\":16},\"carryMeaning\":\"UnsignedBorrow\",\"zeroMeaning\":\"Equal\",\"accumulatorWrite\":false,\"ramWrite\":false,\"extension\":\"None\"}],\"branchPredicate\":null,\"successors\":[21885],\"provenance\":{\"primaryPdfPage\":90,\"primaryPrintedPage\":\"3-38\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5578\"]}},{\"pc\":21885,\"form\":{\"mnemonic\":\"JLT rel8\",\"pinnedPatternIndex\":719,\"length\":2,\"ddMode\":\"U\",\"parsedOperation\":\"JLT\",\"operands\":[]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"CF:bool\"],\"outputs\":[],\"flagsRead\":[\"CF\"],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ConditionalJump\",\"type\":\"pc16\",\"condition\":\"CF\",\"ifTrue\":21951,\"ifFalse\":21887}],\"branchPredicate\":{\"op\":\"FlagIsSet\",\"type\":\"bool\",\"flag\":\"CF\"},\"successors\":[21951,21887],\"provenance\":{\"primaryPdfPage\":120,\"primaryPrintedPage\":\"3-66\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR557D\"]}},{\"pc\":21887,\"form\":{\"mnemonic\":\"MOVB r1, off N8\",\"pinnedPatternIndex\":1504,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"MOVB\",\"operands\":[{\"kind\":\"LocalRegister\",\"name\":\"r1\",\"widthBits\":8,\"address\":265},{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0117:u8\"],\"outputs\":[\"RAM0109:u8\"],\"flagsRead\":[],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"CopyByte\",\"type\":\"u8\",\"source\":{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"destination\":{\"kind\":\"LocalRegister\",\"name\":\"r1\",\"widthBits\":8,\"address\":265},\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"branchPredicate\":null,\"successors\":[21890],\"provenance\":{\"primaryPdfPage\":153,\"primaryPrintedPage\":\"3-99\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR557F\"]}},{\"pc\":21890,\"form\":{\"mnemonic\":\"ANDB off N8, A\",\"pinnedPatternIndex\":349,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"ANDB\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0117:u8\",\"AL:u8\"],\"outputs\":[\"RAM0117:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ReadModifyWriteAnd\",\"type\":\"u8\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"source\":\"AL\",\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"WriteResult\"}],\"branchPredicate\":null,\"successors\":[21893],\"provenance\":{\"primaryPdfPage\":77,\"primaryPrintedPage\":\"3-25\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5582\"]}},{\"pc\":21893,\"form\":{\"mnemonic\":\"JBS off N8.7, rel8\",\"pinnedPatternIndex\":716,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"JBS\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":298,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM012A:u8\"],\"outputs\":[],\"flagsRead\":[],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ConditionalJump\",\"type\":\"pc16\",\"condition\":{\"op\":\"BitIsSet\",\"type\":\"bool\",\"address\":298,\"bit\":7},\"ifTrue\":21906,\"ifFalse\":21896}],\"branchPredicate\":{\"op\":\"BitIsSet\",\"type\":\"bool\",\"address\":298,\"bit\":7},\"successors\":[21906,21896],\"provenance\":{\"primaryPdfPage\":119,\"primaryPrintedPage\":\"3-65\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5585/5588\"]}},{\"pc\":21896,\"form\":{\"mnemonic\":\"JBS off N8.5, rel8\",\"pinnedPatternIndex\":714,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"JBS\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":292,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0124:u8\"],\"outputs\":[],\"flagsRead\":[],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ConditionalJump\",\"type\":\"pc16\",\"condition\":{\"op\":\"BitIsSet\",\"type\":\"bool\",\"address\":292,\"bit\":5},\"ifTrue\":21906,\"ifFalse\":21899}],\"branchPredicate\":{\"op\":\"BitIsSet\",\"type\":\"bool\",\"address\":292,\"bit\":5},\"successors\":[21906,21899],\"provenance\":{\"primaryPdfPage\":119,\"primaryPrintedPage\":\"3-65\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5585/5588\"]}},{\"pc\":21899,\"form\":{\"mnemonic\":\"ANDB off N8, A\",\"pinnedPatternIndex\":349,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"ANDB\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM018F:u8\",\"AL:u8\"],\"outputs\":[\"RAM018F:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ReadModifyWriteAnd\",\"type\":\"u8\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"source\":\"AL\",\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"WriteResult\"}],\"branchPredicate\":null,\"successors\":[21902],\"provenance\":{\"primaryPdfPage\":77,\"primaryPrintedPage\":\"3-25\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR558B/558E\"]}},{\"pc\":21902,\"form\":{\"mnemonic\":\"ORB off N'8, #N8\",\"pinnedPatternIndex\":1678,\"length\":4,\"ddMode\":\"U\",\"parsedOperation\":\"ORB\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":298,\"widthBits\":8,\"selectorField\":\"n8_alt\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},{\"kind\":\"CodeOwnedImmediate\",\"value\":1,\"widthBits\":8}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM012A:u8\"],\"outputs\":[\"RAM012A:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ReadModifyWriteOr\",\"type\":\"u8\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":298,\"widthBits\":8,\"selectorField\":\"n8_alt\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"source\":{\"kind\":\"CodeOwnedImmediate\",\"value\":1,\"widthBits\":8},\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"WriteResult\"}],\"branchPredicate\":null,\"successors\":[21906],\"provenance\":{\"primaryPdfPage\":163,\"primaryPrintedPage\":\"3-110\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR558B/558E\"]}},{\"pc\":21906,\"form\":{\"mnemonic\":\"LB A, off N8\",\"pinnedPatternIndex\":747,\"length\":2,\"ddMode\":\"R\",\"parsedOperation\":\"LB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM018F:u8\",\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\",\"DD\"],\"flagsPreserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"effects\":[{\"op\":\"LoadAccumulatorLow\",\"type\":\"u8\",\"source\":{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"extension\":\"None\",\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"},{\"op\":\"AssignDataDescriptor\",\"type\":\"bool\",\"value\":false}],\"branchPredicate\":null,\"successors\":[21908],\"provenance\":{\"primaryPdfPage\":124,\"primaryPrintedPage\":\"3-70\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5592/5594\"]}},{\"pc\":21908,\"form\":{\"mnemonic\":\"ORB A, #N8\",\"pinnedPatternIndex\":1619,\"length\":2,\"ddMode\":\"0\",\"parsedOperation\":\"ORB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CodeOwnedImmediate\",\"value\":240,\"widthBits\":8}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\",\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"BitwiseOr\",\"type\":\"u8\",\"destination\":{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},\"left\":\"AL\",\"right\":{\"kind\":\"CodeOwnedImmediate\",\"value\":240,\"widthBits\":8},\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"}],\"branchPredicate\":null,\"successors\":[21910],\"provenance\":{\"primaryPdfPage\":160,\"primaryPrintedPage\":\"3-107\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5592/5594\"]}},{\"pc\":21951,\"form\":{\"mnemonic\":\"LB A, #N8\",\"pinnedPatternIndex\":738,\"length\":2,\"ddMode\":\"R\",\"parsedOperation\":\"LB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CodeOwnedImmediate\",\"value\":15,\"widthBits\":8}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\",\"DD\"],\"flagsPreserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"effects\":[{\"op\":\"LoadAccumulatorLow\",\"type\":\"u8\",\"source\":{\"kind\":\"CodeOwnedImmediate\",\"value\":15,\"widthBits\":8},\"extension\":\"None\",\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"},{\"op\":\"AssignDataDescriptor\",\"type\":\"bool\",\"value\":false}],\"branchPredicate\":null,\"successors\":[21953],\"provenance\":{\"primaryPdfPage\":124,\"primaryPrintedPage\":\"3-70\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR55BF/55C1/55C3\"]}},{\"pc\":21953,\"form\":{\"mnemonic\":\"STB A, off N8\",\"pinnedPatternIndex\":2301,\"length\":2,\"ddMode\":\"0\",\"parsedOperation\":\"STB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\"],\"outputs\":[\"RAM0117:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"StoreByte\",\"type\":\"u8\",\"source\":\"AL\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"branchPredicate\":null,\"successors\":[21955],\"provenance\":{\"primaryPdfPage\":208,\"primaryPrintedPage\":\"3-155\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR55BF/55C1/55C3\"]}},{\"pc\":21955,\"form\":{\"mnemonic\":\"STB A, off N8\",\"pinnedPatternIndex\":2301,\"length\":2,\"ddMode\":\"0\",\"parsedOperation\":\"STB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\"],\"outputs\":[\"RAM018F:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"StoreByte\",\"type\":\"u8\",\"source\":\"AL\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"branchPredicate\":null,\"successors\":[21957],\"provenance\":{\"primaryPdfPage\":208,\"primaryPrintedPage\":\"3-155\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR55BF/55C1/55C3\"]}}],\"abstractTransfers\":[{\"nodeId\":\"DirectJ_NotBelow\",\"nodeKind\":\"AbstractTransferSlot\",\"originalLogicalSiteId\":null,\"formId\":\"j-address\",\"length\":3,\"predecessor\":21908,\"target\":21910,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flagsRead\":[],\"flagsWritten\":[],\"functionalDATAReads\":[],\"DATAWrites\":[],\"stackWrites\":[],\"PCReplacement\":\"ExternalProgramTarget\",\"nativeHistoricalObservation\":false},{\"nodeId\":\"DirectJ_Below\",\"nodeKind\":\"AbstractTransferSlot\",\"originalLogicalSiteId\":null,\"formId\":\"j-address\",\"length\":3,\"predecessor\":21955,\"target\":21957,\"dd\":{\"selection\":\"AcceptsBothIncomingDD\",\"transfer\":\"PreservesDD\"},\"flagsRead\":[],\"flagsWritten\":[],\"functionalDATAReads\":[],\"DATAWrites\":[],\"stackWrites\":[],\"PCReplacement\":\"ExternalProgramTarget\",\"nativeHistoricalObservation\":false}],\"geometry\":{\"components\":[\"Common\",\"NotBelow\",\"DirectJ_NotBelow\",\"Below\",\"DirectJ_Below\"],\"lengths\":[16,23,3,6,3],\"denseOffsets\":[[0,16],[16,39],[39,42],[42,48],[48,51]],\"gapOnlyBetween\":[\"DirectJ_NotBelow\",\"Below\"],\"relativeBranches\":[{\"logicalSiteId\":21885,\"targetLogicalSiteId\":21951,\"newDistance\":\"26+gap\",\"historicalReferenceDistance\":64},{\"logicalSiteId\":21893,\"targetLogicalSiteId\":21906,\"newDistance\":10},{\"logicalSiteId\":21896,\"targetLogicalSiteId\":21906,\"newDistance\":7}],\"anchors\":{\"anchors\":[21910,21957],\"test\":\"EachAssignedNodeHalfOpenSpanStart<=Anchor<EndExclusive\",\"envelopeAloneIsCollision\":false,\"unmodeledGapAnchor\":\"RecordUnknownGapAnchor_NotAssignedNodeCollision_NotSafeFreeROM\",\"physicalPlacementAuthorized\":false},\"noWrapPolicy\":{\"instructionStartMinimum\":0,\"instructionStartMaximum\":65535,\"instructionEndExclusiveMaximum\":65536,\"instructionIntervals\":\"HalfOpen_StartIncluded_EndExcluded\",\"relativeNextPCMaximum\":65535,\"relativeTargetMinimum\":0,\"relativeTargetMaximum\":65535,\"externalProgramTargetMinimum\":0,\"externalProgramTargetMaximum\":65535,\"lastDirectJByteAtFFFFAllowed\":true,\"analyticalEnd65536\":\"ExtentOnly_NotInstructionPC_NotExecutedContinuation\",\"wrapRepairAllowed\":false,\"splitInstructionsAllowed\":false,\"overlapAllowed\":false,\"physicalPlacementAuthorized\":false},\"rel8Policy\":{\"equation\":\"assignedTargetPC-(assignedBranchPC+originalExactLength)\",\"signedMinimum\":-128,\"signedMaximum\":127,\"JLTExpectedDelta\":\"26+gap\",\"JBS7ExpectedDelta\":10,\"JBS5ExpectedDelta\":7,\"historicalJLT64IsNewDelta\":false,\"displacementByteConstruction\":false,\"relaxationAllowed\":false,\"trampolineAllowed\":false,\"checkOrder\":\"ActualNextAndTargetBounds_ActualSignedReach_ThenCanonicalDistance\"},\"gapPolicy\":{\"gap\":\"ExactNonnegativeInteger_NoArbitraryCandidateCap\",\"onlyAfterComponent\":\"DirectJ_NotBelow\",\"onlyBeforeComponent\":\"Below\",\"otherComponentOrInternalGapsAllowed\":false,\"assignedGapInstructions\":0,\"gapExecutable\":false,\"gapPadding\":false,\"gapFreeROM\":false,\"fillPolicy\":null,\"gapAnchor\":\"UnknownGapAnchor_NotSafeFreeROM_NotPhysicalPlacement\",\"canonicalReachMaximumGap\":101,\"spanCheckedSeparatelyBeforeReach\":true},\"fallthroughConstraints\":[{\"from\":21871,\"to\":21873,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21873,\"to\":21874,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21874,\"to\":21877,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21877,\"to\":21878,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21878,\"to\":21880,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21880,\"to\":21885,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21885,\"to\":21887,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21887,\"to\":21890,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21890,\"to\":21893,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21893,\"to\":21896,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21896,\"to\":21899,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21899,\"to\":21902,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21902,\"to\":21906,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21906,\"to\":21908,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21908,\"to\":\"DirectJ_NotBelow\",\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21951,\"to\":21953,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21953,\"to\":21955,\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"},{\"from\":21955,\"to\":\"DirectJ_Below\",\"equation\":\"assignedSuccessorPC=assignedPredecessorPC+sourceExactLength\"}]},\"componentPlan\":[{\"name\":\"Common\",\"nodeIds\":[21871,21873,21874,21877,21878,21880,21885],\"expectedLength\":16,\"startConstant\":0,\"endConstant\":16,\"gapCoefficient\":0},{\"name\":\"NotBelow\",\"nodeIds\":[21887,21890,21893,21896,21899,21902,21906,21908],\"expectedLength\":23,\"startConstant\":16,\"endConstant\":39,\"gapCoefficient\":0},{\"name\":\"DirectJ_NotBelow\",\"nodeIds\":[\"DirectJ_NotBelow\"],\"expectedLength\":3,\"startConstant\":39,\"endConstant\":42,\"gapCoefficient\":0},{\"name\":\"Below\",\"nodeIds\":[21951,21953,21955],\"expectedLength\":6,\"startConstant\":42,\"endConstant\":48,\"gapCoefficient\":1},{\"name\":\"DirectJ_Below\",\"nodeIds\":[\"DirectJ_Below\"],\"expectedLength\":3,\"startConstant\":48,\"endConstant\":51,\"gapCoefficient\":1}],\"composedCFG\":[{\"from\":21871,\"to\":21873,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21873,\"to\":21874,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21874,\"to\":21877,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21877,\"to\":21878,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21878,\"to\":21880,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21880,\"to\":21885,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21885,\"to\":21951,\"kind\":\"ConditionalTaken\",\"predicate\":{\"kind\":\"FlagEquals\",\"flag\":\"CF\",\"value\":1}},{\"from\":21885,\"to\":21887,\"kind\":\"Fallthrough\",\"predicate\":{\"kind\":\"FlagEquals\",\"flag\":\"CF\",\"value\":1}},{\"from\":21887,\"to\":21890,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21890,\"to\":21893,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21893,\"to\":21906,\"kind\":\"ConditionalTaken\",\"predicate\":{\"kind\":\"MemoryBitEquals\",\"address\":298,\"bit\":7,\"value\":1}},{\"from\":21893,\"to\":21896,\"kind\":\"Fallthrough\",\"predicate\":{\"kind\":\"MemoryBitEquals\",\"address\":298,\"bit\":7,\"value\":1}},{\"from\":21896,\"to\":21906,\"kind\":\"ConditionalTaken\",\"predicate\":{\"kind\":\"MemoryBitEquals\",\"address\":292,\"bit\":5,\"value\":1}},{\"from\":21896,\"to\":21899,\"kind\":\"Fallthrough\",\"predicate\":{\"kind\":\"MemoryBitEquals\",\"address\":292,\"bit\":5,\"value\":1}},{\"from\":21899,\"to\":21902,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21902,\"to\":21906,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21906,\"to\":21908,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21908,\"to\":\"DirectJ_NotBelow\",\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21951,\"to\":21953,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21953,\"to\":21955,\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":21955,\"to\":\"DirectJ_Below\",\"kind\":\"Fallthrough\",\"predicate\":null},{\"from\":\"DirectJ_NotBelow\",\"to\":21910,\"kind\":\"ExternalTransfer\",\"predicate\":null},{\"from\":\"DirectJ_Below\",\"to\":21957,\"kind\":\"ExternalTransfer\",\"predicate\":null}],\"paths\":[{\"id\":\"A\",\"originalPath\":{\"id\":\"A\",\"pcs\":[21871,21873,21874,21877,21878,21880,21885,21951,21953,21955],\"conditions\":[{\"pc\":21885,\"result\":true}],\"terminal\":21957,\"historical\":\"HistoricalNativeValidated\",\"instructionCount\":10,\"orderedReads\":[{\"pc\":21871,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21877,\"address\":264,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\"},{\"pc\":21878,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21880,\"address\":406,\"widthBits\":16,\"mode\":\"CurrentPage\",\"byteOrder\":\"LittleEndian\"}],\"orderedWrites\":[{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteRotateThroughCarry\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21953,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"StoreByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21955,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"StoreByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"mustNotRead\":[],\"finalAL\":{\"kind\":\"ConstantByte\",\"value\":15},\"finalCF\":1,\"finalZF\":0,\"finalDD\":0},\"nodeIds\":[21871,21873,21874,21877,21878,21880,21885,21951,21953,21955,\"DirectJ_Below\"],\"originalInstructionCount\":10,\"abstractTransferCount\":1,\"composedNodeCount\":11,\"transferNodeId\":\"DirectJ_Below\",\"externalTarget\":21957},{\"id\":\"B\",\"originalPath\":{\"id\":\"B\",\"pcs\":[21871,21873,21874,21877,21878,21880,21885,21887,21890,21893,21906,21908],\"conditions\":[{\"pc\":21885,\"result\":false},{\"pc\":21893,\"result\":true}],\"terminal\":21910,\"historical\":\"HistoricalNativeValidated\",\"instructionCount\":12,\"orderedReads\":[{\"pc\":21871,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21877,\"address\":264,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\"},{\"pc\":21878,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21880,\"address\":406,\"widthBits\":16,\"mode\":\"CurrentPage\",\"byteOrder\":\"LittleEndian\"},{\"pc\":21887,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21893,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21906,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"orderedWrites\":[{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteRotateThroughCarry\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21887,\"address\":265,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\",\"operation\":\"CopyByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"mustNotRead\":[292],\"finalAL\":{\"kind\":\"FinalMemoryOrImmediate\",\"address\":399,\"immediate\":240},\"finalCF\":0,\"finalZF\":0,\"finalDD\":0},\"nodeIds\":[21871,21873,21874,21877,21878,21880,21885,21887,21890,21893,21906,21908,\"DirectJ_NotBelow\"],\"originalInstructionCount\":12,\"abstractTransferCount\":1,\"composedNodeCount\":13,\"transferNodeId\":\"DirectJ_NotBelow\",\"externalTarget\":21910},{\"id\":\"C\",\"originalPath\":{\"id\":\"C\",\"pcs\":[21871,21873,21874,21877,21878,21880,21885,21887,21890,21893,21896,21906,21908],\"conditions\":[{\"pc\":21885,\"result\":false},{\"pc\":21893,\"result\":false},{\"pc\":21896,\"result\":true}],\"terminal\":21910,\"historical\":\"StaticPrimaryAndInventedCoverage\",\"instructionCount\":13,\"orderedReads\":[{\"pc\":21871,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21877,\"address\":264,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\"},{\"pc\":21878,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21880,\"address\":406,\"widthBits\":16,\"mode\":\"CurrentPage\",\"byteOrder\":\"LittleEndian\"},{\"pc\":21887,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21893,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21896,\"address\":292,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21906,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"orderedWrites\":[{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteRotateThroughCarry\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21887,\"address\":265,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\",\"operation\":\"CopyByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"mustNotRead\":[],\"finalAL\":{\"kind\":\"FinalMemoryOrImmediate\",\"address\":399,\"immediate\":240},\"finalCF\":0,\"finalZF\":0,\"finalDD\":0},\"nodeIds\":[21871,21873,21874,21877,21878,21880,21885,21887,21890,21893,21896,21906,21908,\"DirectJ_NotBelow\"],\"originalInstructionCount\":13,\"abstractTransferCount\":1,\"composedNodeCount\":14,\"transferNodeId\":\"DirectJ_NotBelow\",\"externalTarget\":21910},{\"id\":\"D\",\"originalPath\":{\"id\":\"D\",\"pcs\":[21871,21873,21874,21877,21878,21880,21885,21887,21890,21893,21896,21899,21902,21906,21908],\"conditions\":[{\"pc\":21885,\"result\":false},{\"pc\":21893,\"result\":false},{\"pc\":21896,\"result\":false}],\"terminal\":21910,\"historical\":\"HistoricalNativeValidated\",\"instructionCount\":15,\"orderedReads\":[{\"pc\":21871,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21877,\"address\":264,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\"},{\"pc\":21878,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21880,\"address\":406,\"widthBits\":16,\"mode\":\"CurrentPage\",\"byteOrder\":\"LittleEndian\"},{\"pc\":21887,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21893,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21896,\"address\":292,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21899,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21902,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21906,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"orderedWrites\":[{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteRotateThroughCarry\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21887,\"address\":265,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\",\"operation\":\"CopyByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21899,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21902,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteOr\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"mustNotRead\":[],\"finalAL\":{\"kind\":\"FinalMemoryOrImmediate\",\"address\":399,\"immediate\":240},\"finalCF\":0,\"finalZF\":0,\"finalDD\":0},\"nodeIds\":[21871,21873,21874,21877,21878,21880,21885,21887,21890,21893,21896,21899,21902,21906,21908,\"DirectJ_NotBelow\"],\"originalInstructionCount\":15,\"abstractTransferCount\":1,\"composedNodeCount\":16,\"transferNodeId\":\"DirectJ_NotBelow\",\"externalTarget\":21910}],\"context\":{\"classification\":\"StaticObligationRetentionOnly_NotRuntimeAssemblyEquivalence\",\"initialDD\":[0,1],\"DD0AfterLogical556F\":true,\"carryDependencies\":[{\"producerLogicalSiteId\":21873,\"consumerLogicalSiteId\":21874},{\"producerLogicalSiteId\":21880,\"consumerLogicalSiteId\":21885}],\"preserved\":[\"HC\",\"OtherPSW\",\"AH\",\"SCB\",\"LRB\",\"X1\",\"X2\",\"DP\",\"USP\",\"SSP\",\"localr0\",\"localr2..r7\",\"DATA0124\",\"DATA0128\",\"DATA0196\",\"DATA0197\",\"SFUninterpreted\"],\"terminalDD\":0,\"terminalZF\":0,\"terminalCF\":{\"NotBelow\":0,\"Below\":1},\"requiredLRB\":33,\"currentPage\":256,\"localBank\":[264,271],\"word0196\":{\"address\":406,\"highByteAddress\":407,\"widthBits\":16,\"byteOrder\":\"LittleEndian\",\"evenAddressed\":true,\"codeOwnedImmediate\":192,\"hostRebasingAllowed\":false},\"potentialWordAliases\":[[278,279],[292,293],[296,297],[298,299],[398,399],[406,407]],\"unknownStackAliases\":\"PossibleRegistersRAMSFR_NotGloballyExcluded\",\"nativeStackSafety\":\"NotEstablished\",\"nativeSFMeaningStorage\":\"PrimaryConflictUnresolved\",\"sameValueWrites\":\"RetainFreshOrdinal\",\"orderedWriteCounts\":[3,3,3,5],\"firstGateTrueMustNotRead\":292,\"historicalPath13NativeWitnesses\":0,\"adaptersProloguesFlagWritersAllowed\":false},\"continuations\":[{\"id\":\"NotBelow\",\"originalTargetPC\":21910,\"identityClassification\":\"OriginalHistoricalContinuationPC_NotWritableROMPlacement\",\"lastLogicalSiteId\":21908,\"pathIds\":[\"B\",\"C\",\"D\"],\"requiredFinalState\":{\"AL\":{\"kind\":\"FinalMemoryOrImmediate\",\"address\":399,\"immediate\":240},\"AH\":\"IncomingAH\",\"CF\":0,\"ZF\":0,\"DD\":0,\"HC\":\"IncomingHC\",\"OtherPSW\":\"IncomingOtherPSW\",\"LRB\":33,\"SCB\":\"IncomingPSWLowThreeBits\",\"SSP\":\"IncomingSSP\",\"pointingRegisters\":\"RetainAllSelectedAndUnselectedBanks\",\"SF\":\"NoNewWriter_SFMeaningStorageNotEstablished\"},\"requiredPathEffects\":[{\"pathId\":\"B\",\"originalInstructionCount\":12,\"historicalCoverage\":\"HistoricalNativeValidated\",\"orderedReads\":[{\"pc\":21871,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21877,\"address\":264,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\"},{\"pc\":21878,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21880,\"address\":406,\"widthBits\":16,\"mode\":\"CurrentPage\",\"byteOrder\":\"LittleEndian\"},{\"pc\":21887,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21893,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21906,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"orderedWrites\":[{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteRotateThroughCarry\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21887,\"address\":265,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\",\"operation\":\"CopyByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"mustNotRead\":[292]},{\"pathId\":\"C\",\"originalInstructionCount\":13,\"historicalCoverage\":\"StaticPrimaryAndInventedCoverage\",\"orderedReads\":[{\"pc\":21871,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21877,\"address\":264,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\"},{\"pc\":21878,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21880,\"address\":406,\"widthBits\":16,\"mode\":\"CurrentPage\",\"byteOrder\":\"LittleEndian\"},{\"pc\":21887,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21893,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21896,\"address\":292,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21906,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"orderedWrites\":[{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteRotateThroughCarry\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21887,\"address\":265,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\",\"operation\":\"CopyByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"mustNotRead\":[]},{\"pathId\":\"D\",\"originalInstructionCount\":15,\"historicalCoverage\":\"HistoricalNativeValidated\",\"orderedReads\":[{\"pc\":21871,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21877,\"address\":264,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\"},{\"pc\":21878,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21880,\"address\":406,\"widthBits\":16,\"mode\":\"CurrentPage\",\"byteOrder\":\"LittleEndian\"},{\"pc\":21887,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21893,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21896,\"address\":292,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21899,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21902,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21906,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"}],\"orderedWrites\":[{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteRotateThroughCarry\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21887,\"address\":265,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\",\"operation\":\"CopyByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21890,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21899,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteAnd\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21902,\"address\":298,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteOr\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"mustNotRead\":[]}],\"stopMarker\":\"AnalyticalSTOPBefore_NotRT_NotExecutedOpcode\",\"nativeExitIsolation\":\"NotEstablished\",\"actualDownstreamRejoin\":\"NotEstablished\"},{\"id\":\"Below\",\"originalTargetPC\":21957,\"identityClassification\":\"OriginalHistoricalContinuationPC_NotWritableROMPlacement\",\"lastLogicalSiteId\":21955,\"pathIds\":[\"A\"],\"requiredFinalState\":{\"AL\":{\"kind\":\"ConstantByte\",\"value\":15},\"AH\":\"IncomingAH\",\"CF\":1,\"ZF\":0,\"DD\":0,\"HC\":\"IncomingHC\",\"OtherPSW\":\"IncomingOtherPSW\",\"LRB\":33,\"SCB\":\"IncomingPSWLowThreeBits\",\"SSP\":\"IncomingSSP\",\"pointingRegisters\":\"RetainAllSelectedAndUnselectedBanks\",\"SF\":\"NoNewWriter_SFMeaningStorageNotEstablished\"},\"requiredPathEffects\":[{\"pathId\":\"A\",\"originalInstructionCount\":10,\"historicalCoverage\":\"HistoricalNativeValidated\",\"orderedReads\":[{\"pc\":21871,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21877,\"address\":264,\"widthBits\":8,\"mode\":\"LocalRegister\",\"byteOrder\":\"Byte\"},{\"pc\":21878,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\"},{\"pc\":21880,\"address\":406,\"widthBits\":16,\"mode\":\"CurrentPage\",\"byteOrder\":\"LittleEndian\"}],\"orderedWrites\":[{\"pc\":21874,\"address\":398,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"ReadModifyWriteRotateThroughCarry\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21953,\"address\":279,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"StoreByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"pc\":21955,\"address\":399,\"widthBits\":8,\"mode\":\"CurrentPage\",\"byteOrder\":\"Byte\",\"operation\":\"StoreByte\",\"ordered\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"mustNotRead\":[]}],\"stopMarker\":\"AnalyticalSTOPBefore_NotRT_NotExecutedOpcode\",\"nativeExitIsolation\":\"NotEstablished\",\"actualDownstreamRejoin\":\"NotEstablished\"}],\"provenance\":{\"data0196\":\"Native05EBWriterGeneration;Historical54FAAnd5578ReadSameGeneration\",\"data0117\":\"RetainedOnceInitialThenNativeWriteHistory\",\"data018e\":\"InitialScratchThenNative5572History\",\"data018f\":\"InitialScratchThenBranchSpecificNativeWriteHistory\",\"data012a\":\"RetainedNeighborBits;Bit0WriteOnly558E\",\"data0124\":\"UpstreamNativeOwnership\",\"data0128bit2\":\"OnceInitialMaskedHistory;NoScopedAccess\",\"transition05ed54f5\":\"ExplicitHarnessSchedule\",\"nativeOwnerAcceptedFromHost\":false,\"secondMachineHandoff\":false,\"reseedAt556f\":false,\"syntheticSSPFrame\":false,\"extraEventSource\":false,\"physicalMeaning\":\"Unknown\",\"currentWord0196PhysicalRole\":\"Unknown\",\"historicalCompletedObservations\":42,\"historicalSnapshots\":552,\"historicalOrderedWrites\":170,\"historicalNativePath13Witnesses\":0},\"nativeBoundary\":{\"entry\":\"NativeBasicBlockEntry\",\"nativeCFunctionEntry\":\"NotEstablished\",\"calFrameAt556f\":\"NotEstablished\",\"ordinaryReturnAllowed\":false,\"stopBoundariesAreRT\":false,\"preserved\":[\"AH\",\"HC\",\"OtherPSW\",\"SCB\",\"LRB\",\"X1\",\"X2\",\"DP\",\"USP\",\"SSP\",\"SFHostReplay\",\"localr0\",\"localr2..r7\",\"DATA0124\",\"DATA0128\",\"DATA0196\",\"DATA0197\",\"UnrepresentedNativeStateRequiresFutureProof\"],\"exitOutputs\":[\"A_AL_AH\",\"PSW\",\"LRB\",\"SCB\",\"PointingRegisterBanks\",\"SSP\",\"RelevantRAM\",\"OrderedWrites\",\"BranchSelectedContinuation\"],\"adapter\":\"NotImplemented\",\"prologueEpilogueAllowed\":false,\"pushPopAllowed\":false,\"sf\":\"PrimaryConflictUnresolved;NoNativeBooleanInterpretation\",\"stackSafety\":\"NotEstablished\",\"codePlacement\":\"NotEstablished\",\"widerContinuationLiveness\":\"NotEstablished\"},\"unresolved\":{\"targetCompilerABI\":\"NotEstablished\",\"SFMeaningStorageWidth\":\"PrimaryConflictUnresolved\",\"stackSafety\":\"NotEstablished\",\"codePlacement\":\"NotEstablished\",\"targetMachineCodeEquivalence\":\"NotEstablished\",\"nativeProgramEquivalence\":\"NotEstablished\",\"firmwareIntegration\":\"NotEstablished\",\"recoveredECUScheduler\":\"NotEstablished\",\"coherentResetFullbootFlow\":\"NotEstablished\"},\"permissions\":{\"abstractStaticComposition\":true,\"actualTargetProgramGeneration\":false,\"targetCPUExecution\":false,\"codecCallsForComposition\":false,\"nativeExitIsolationVerified\":false,\"actualDownstreamRejoinVerified\":false,\"physicalROMPlacementAuthorized\":false,\"FirmwareReady\":false},\"declaredStaticFacts\":{\"phase\":\"SpecificationOnly_ActualAnalyzerAndIndependentChecksRequired\",\"originalSites\":18,\"originalForms\":15,\"abstractTransferSlots\":2,\"abstractTransferForms\":1,\"totalNodes\":20,\"originalInstructionLength\":45,\"abstractTransferLength\":6,\"denseLength\":51,\"composedTotalLength\":\"51+gap\",\"entryLogicalSiteId\":21871,\"externalTargets\":[21910,21957],\"originalCFGEdges\":21,\"composedCFGEdges\":23,\"fallthroughEdges\":18,\"conditionalTakenEdges\":3,\"externalTransferEdges\":2,\"originalPathCounts\":[10,12,13,15],\"composedPathCounts\":[11,13,14,16],\"oneAbstractTransferPerPath\":true,\"orderedWriteCounts\":[3,3,3,5],\"initialDDDomains\":[[0],[1],[0,1]],\"directJIncomingDD\":0,\"directJOutgoingDD\":0,\"terminalZF\":0,\"terminalCF\":{\"Below\":1,\"NotBelow\":0},\"sameValueWrites\":\"RetainFreshOrdinal\",\"staticWriteOrdinalMeaning\":\"OneBasedPathWriteOrder_NotNativeJournalOrGeneration\",\"originalExcluded41ByteRegion\":\"Unmodeled_NotPadding_NotFreeROM_NotTransferPlacement\",\"JLTDelta\":\"26+gap\",\"JBS7Delta\":10,\"JBS5Delta\":7,\"maximumCanonicalReachGap\":101,\"noArbitraryCandidateGapCap\":true,\"maxDenseBase\":65485,\"maxGap101Base\":65384,\"analyticalEnd65536NotPC16\":true,\"gap0\":26,\"gap41\":67,\"gap101\":127,\"gap102\":128,\"syntheticInternalCFGIsolation\":\"ExpectedStructurallyIsolatedByTwoAbstractExternalTransfers\",\"nativeExitIsolation\":\"NotEstablished\",\"actualDownstreamRejoin\":\"NotEstablished\",\"physicalROMPlacement\":\"NotEstablished\",\"targetProgramEquivalence\":\"NotEstablished\",\"firmwareIntegration\":\"NotEstablished\",\"CompositeMachineCode\":\"NotGenerated\",\"analyzerCodecCalls\":0,\"compositeByteEmissionCalls\":0,\"actualROMExecutions\":0,\"CPUExecutions\":0,\"targetAssemblyFiles\":0,\"targetObjects\":0,\"targetHEX\":0,\"FirmwareBIN\":0,\"GUIHardwareFullBoot\":\"NotRun\",\"historicalRunner\":{\"version\":\"0.43.0\",\"protocol\":1,\"semanticAccountingIdentities\":38}},\"historicalStatuses\":{\"m2bd\":\"TypedLoweringObligationsEstablished\",\"m2bc\":\"DecodeEncodeCompatibilityVerified\",\"m2bb\":\"IndependentEncoderVerified\",\"m2ba\":\"IndependentRouteSpecified\",\"m2az\":\"HistoricalSourceRightsBlocked\",\"m2ay\":\"ASM662BuildEncodingBlocked\",\"m2ax\":\"MAC66KAcquisitionBlocked\",\"m2aw\":\"ArchitectureContextEstablished\",\"m2av\":\"BoundedSourceEquivalenceEstablished\",\"m2au\":\"INTAccountingComplete\",\"m2at\":\"DECDPHCFixComplete\",\"m2an\":\"SLLBFixComplete\",\"WDT3C\":\"ResearchBlocked\",\"JGT_C8\":\"PrimaryConflictUnresolved\",\"m2aqCAL2689_RT5C80\":\"NotRun\",\"m2ap\":\"SSPADCBlocked\",\"m2ao\":\"DATA019BFrontierUnchanged\",\"m2ah\":\"STOPBefore5722\",\"DATA019B2RuntimeOwner\":\"NotEstablished\",\"m2t\":\"JGT233ABlockedUnresolved\",\"StrictM2i\":\"Blocked\",\"IRQ\":\"NotInjected\",\"TimerEvolution\":\"NotModeled\",\"RecoveredECUScheduler\":\"NotEstablished\",\"TargetCompilerABI\":\"NotEstablished\",\"TargetIntegration\":\"NotEstablished\",\"Readiness\":\"PcInspectionOnly_NotFlashReady\",\"PhysicalFuelTimeDegrees\":\"Unavailable\",\"GUIHardwareFullboot\":\"NotRun\",\"ASM662_WDT_C8Inquiries\":\"NotSent\",\"m2bf\":\"ExternalContinuationObligationsAndTransferFormEvidenceEstablished\",\"m2bg\":\"IndependentDirectJSyntheticEncodeDecodeVerified\"}}")
_ORIGINAL_IR = json.loads("{\"schemaVersion\":1,\"classification\":\"ReviewedInstructionFaithfulOfflineIR\",\"entryPc\":21871,\"stopBeforePcs\":[21910,21957],\"context\":{\"lrb\":33,\"currentPage\":256,\"localBank\":264,\"scb\":\"DerivedPSWLowThreeBits\",\"requiredIncomingDD\":\"Either;556FresetsDD0\",\"aliasesOutsideDeclaredFields\":\"NotEstablished\",\"instructionExtents\":\"IndependentlyComparedToProtectedOriginalAndListing\",\"physicalNames\":\"Unknown\",\"cycles\":\"Excluded;NoCycleEquivalenceClaim\"},\"stateTypes\":{\"AL\":\"u8\",\"AH\":\"u8\",\"A\":\"u16\",\"PSW\":\"u16\",\"PC\":\"pc16\",\"RAMByte\":\"u8\",\"RAMWord\":\"u16\",\"CF\":\"bool\",\"ZF\":\"bool\",\"HC\":\"bool\",\"DD\":\"bool\"},\"numericRules\":{\"unsignedOnly\":true,\"byteTruncation\":\"Modulo256\",\"wordAccess\":\"EvenLittleEndian\",\"loadByteExtension\":\"None;AHpreserved\",\"signExtension\":\"NoneInThisFragment\",\"accumulatorByteOperations\":\"DD0;EstablishedBy556F\"},\"retainedState\":[\"AH\",\"HC\",\"OtherPSW\",\"LRB\",\"X1\",\"X2\",\"DP\",\"USP\",\"SSP\",\"SF\",\"Halted\",\"RAM0124\",\"RAM0128\",\"RAM0196\",\"RAM0197\",\"localr0\",\"localr2..r7\"],\"provenanceRestrictions\":{\"nativeOwnerAcceptedFromHost\":false,\"hostContext\":\"OfflineAnnotationOnly\",\"actualRuntimeSource\":\"NotEstablished\",\"word0196PhysicalRole\":\"Unknown\"},\"instructions\":[{\"pc\":21871,\"form\":{\"mnemonic\":\"LB A, off N8\",\"pinnedPatternIndex\":747,\"length\":2,\"ddMode\":\"R\",\"parsedOperation\":\"LB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\"],\"inputs\":[\"RAM018E:u8\",\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\",\"DD\"],\"flagsPreserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"effects\":[{\"op\":\"LoadAccumulatorLow\",\"type\":\"u8\",\"source\":{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"extension\":\"None\",\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"},{\"op\":\"AssignDataDescriptor\",\"type\":\"bool\",\"value\":false}],\"branchPredicate\":null,\"successors\":[21873],\"provenance\":{\"primaryPdfPage\":124,\"primaryPrintedPage\":\"3-70\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR556F\"]}},{\"pc\":21873,\"form\":{\"mnemonic\":\"SLLB A\",\"pinnedPatternIndex\":2198,\"length\":1,\"ddMode\":\"0\",\"parsedOperation\":\"SLLB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[\"CF\"],\"flagsPreserved\":[\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"LogicalShiftLeft\",\"type\":\"u8\",\"source\":\"AL\",\"distance\":1,\"truncation\":\"Modulo256\",\"zeroFill\":true},{\"op\":\"AssignCarryFromOldBit\",\"type\":\"bool\",\"source\":\"AL\",\"bit\":7}],\"branchPredicate\":null,\"successors\":[21874],\"provenance\":{\"primaryPdfPage\":197,\"primaryPrintedPage\":\"3-144\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5571\"]}},{\"pc\":21874,\"form\":{\"mnemonic\":\"ROLB off N8\",\"pinnedPatternIndex\":1862,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"ROLB\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM018E:u8\",\"CF:bool\"],\"outputs\":[\"RAM018E:u8\"],\"flagsRead\":[\"CF\"],\"flagsWritten\":[\"CF\"],\"flagsPreserved\":[\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ReadModifyWriteRotateThroughCarry\",\"type\":\"u8\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"direction\":\"Left\",\"distance\":1,\"carryInput\":\"IncomingCF\",\"carryOutput\":\"OldBit7\",\"truncation\":\"Modulo256\",\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"branchPredicate\":null,\"successors\":[21877],\"provenance\":{\"primaryPdfPage\":173,\"primaryPrintedPage\":\"3-120\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5572\"]}},{\"pc\":21877,\"form\":{\"mnemonic\":\"LB A, r0\",\"pinnedPatternIndex\":739,\"length\":1,\"ddMode\":\"R\",\"parsedOperation\":\"LB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"LocalRegister\",\"name\":\"r0\",\"widthBits\":8,\"address\":264}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0108:u8\",\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\",\"DD\"],\"flagsPreserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"effects\":[{\"op\":\"LoadAccumulatorLow\",\"type\":\"u8\",\"source\":{\"kind\":\"LocalRegister\",\"name\":\"r0\",\"widthBits\":8,\"address\":264},\"extension\":\"None\",\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"},{\"op\":\"AssignDataDescriptor\",\"type\":\"bool\",\"value\":false}],\"branchPredicate\":null,\"successors\":[21878],\"provenance\":{\"primaryPdfPage\":124,\"primaryPrintedPage\":\"3-70\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5575\"]}},{\"pc\":21878,\"form\":{\"mnemonic\":\"ANDB A, off N8\",\"pinnedPatternIndex\":333,\"length\":2,\"ddMode\":\"0\",\"parsedOperation\":\"ANDB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\",\"RAM018E:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"BitwiseAnd\",\"type\":\"u8\",\"destination\":{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},\"left\":\"AL\",\"right\":{\"kind\":\"CurrentPageRam\",\"address\":398,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"}],\"branchPredicate\":null,\"successors\":[21880],\"provenance\":{\"primaryPdfPage\":76,\"primaryPrintedPage\":\"3-24\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5576\"]}},{\"pc\":21880,\"form\":{\"mnemonic\":\"CMP off N8, #N16\",\"pinnedPatternIndex\":498,\"length\":5,\"ddMode\":\"U\",\"parsedOperation\":\"CMP\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":406,\"widthBits\":16,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"LittleEndian\"},{\"kind\":\"CodeOwnedImmediate\",\"value\":192,\"widthBits\":16}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0196:u16\"],\"outputs\":[],\"flagsRead\":[],\"flagsWritten\":[\"CF\",\"ZF\"],\"flagsPreserved\":[\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"UnsignedCompare\",\"type\":\"u16\",\"left\":{\"kind\":\"CurrentPageRam\",\"address\":406,\"widthBits\":16,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"LittleEndian\"},\"right\":{\"kind\":\"CodeOwnedImmediate\",\"value\":192,\"widthBits\":16},\"carryMeaning\":\"UnsignedBorrow\",\"zeroMeaning\":\"Equal\",\"accumulatorWrite\":false,\"ramWrite\":false,\"extension\":\"None\"}],\"branchPredicate\":null,\"successors\":[21885],\"provenance\":{\"primaryPdfPage\":90,\"primaryPrintedPage\":\"3-38\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5578\"]}},{\"pc\":21885,\"form\":{\"mnemonic\":\"JLT rel8\",\"pinnedPatternIndex\":719,\"length\":2,\"ddMode\":\"U\",\"parsedOperation\":\"JLT\",\"operands\":[]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"CF:bool\"],\"outputs\":[],\"flagsRead\":[\"CF\"],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ConditionalJump\",\"type\":\"pc16\",\"condition\":\"CF\",\"ifTrue\":21951,\"ifFalse\":21887}],\"branchPredicate\":{\"op\":\"FlagIsSet\",\"type\":\"bool\",\"flag\":\"CF\"},\"successors\":[21951,21887],\"provenance\":{\"primaryPdfPage\":120,\"primaryPrintedPage\":\"3-66\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR557D\"]}},{\"pc\":21887,\"form\":{\"mnemonic\":\"MOVB r1, off N8\",\"pinnedPatternIndex\":1504,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"MOVB\",\"operands\":[{\"kind\":\"LocalRegister\",\"name\":\"r1\",\"widthBits\":8,\"address\":265},{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0117:u8\"],\"outputs\":[\"RAM0109:u8\"],\"flagsRead\":[],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"CopyByte\",\"type\":\"u8\",\"source\":{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"destination\":{\"kind\":\"LocalRegister\",\"name\":\"r1\",\"widthBits\":8,\"address\":265},\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"branchPredicate\":null,\"successors\":[21890],\"provenance\":{\"primaryPdfPage\":153,\"primaryPrintedPage\":\"3-99\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR557F\"]}},{\"pc\":21890,\"form\":{\"mnemonic\":\"ANDB off N8, A\",\"pinnedPatternIndex\":349,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"ANDB\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0117:u8\",\"AL:u8\"],\"outputs\":[\"RAM0117:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ReadModifyWriteAnd\",\"type\":\"u8\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"source\":\"AL\",\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"WriteResult\"}],\"branchPredicate\":null,\"successors\":[21893],\"provenance\":{\"primaryPdfPage\":77,\"primaryPrintedPage\":\"3-25\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5582\"]}},{\"pc\":21893,\"form\":{\"mnemonic\":\"JBS off N8.7, rel8\",\"pinnedPatternIndex\":716,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"JBS\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":298,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM012A:u8\"],\"outputs\":[],\"flagsRead\":[],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ConditionalJump\",\"type\":\"pc16\",\"condition\":{\"op\":\"BitIsSet\",\"type\":\"bool\",\"address\":298,\"bit\":7},\"ifTrue\":21906,\"ifFalse\":21896}],\"branchPredicate\":{\"op\":\"BitIsSet\",\"type\":\"bool\",\"address\":298,\"bit\":7},\"successors\":[21906,21896],\"provenance\":{\"primaryPdfPage\":119,\"primaryPrintedPage\":\"3-65\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5585/5588\"]}},{\"pc\":21896,\"form\":{\"mnemonic\":\"JBS off N8.5, rel8\",\"pinnedPatternIndex\":714,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"JBS\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":292,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM0124:u8\"],\"outputs\":[],\"flagsRead\":[],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ConditionalJump\",\"type\":\"pc16\",\"condition\":{\"op\":\"BitIsSet\",\"type\":\"bool\",\"address\":292,\"bit\":5},\"ifTrue\":21906,\"ifFalse\":21899}],\"branchPredicate\":{\"op\":\"BitIsSet\",\"type\":\"bool\",\"address\":292,\"bit\":5},\"successors\":[21906,21899],\"provenance\":{\"primaryPdfPage\":119,\"primaryPrintedPage\":\"3-65\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5585/5588\"]}},{\"pc\":21899,\"form\":{\"mnemonic\":\"ANDB off N8, A\",\"pinnedPatternIndex\":349,\"length\":3,\"ddMode\":\"U\",\"parsedOperation\":\"ANDB\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM018F:u8\",\"AL:u8\"],\"outputs\":[\"RAM018F:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ReadModifyWriteAnd\",\"type\":\"u8\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"source\":\"AL\",\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"WriteResult\"}],\"branchPredicate\":null,\"successors\":[21902],\"provenance\":{\"primaryPdfPage\":77,\"primaryPrintedPage\":\"3-25\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR558B/558E\"]}},{\"pc\":21902,\"form\":{\"mnemonic\":\"ORB off N'8, #N8\",\"pinnedPatternIndex\":1678,\"length\":4,\"ddMode\":\"U\",\"parsedOperation\":\"ORB\",\"operands\":[{\"kind\":\"CurrentPageRam\",\"address\":298,\"widthBits\":8,\"selectorField\":\"n8_alt\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},{\"kind\":\"CodeOwnedImmediate\",\"value\":1,\"widthBits\":8}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM012A:u8\"],\"outputs\":[\"RAM012A:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"ReadModifyWriteOr\",\"type\":\"u8\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":298,\"widthBits\":8,\"selectorField\":\"n8_alt\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"source\":{\"kind\":\"CodeOwnedImmediate\",\"value\":1,\"widthBits\":8},\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"WriteResult\"}],\"branchPredicate\":null,\"successors\":[21906],\"provenance\":{\"primaryPdfPage\":163,\"primaryPrintedPage\":\"3-110\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR558B/558E\"]}},{\"pc\":21906,\"form\":{\"mnemonic\":\"LB A, off N8\",\"pinnedPatternIndex\":747,\"length\":2,\"ddMode\":\"R\",\"parsedOperation\":\"LB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"RAM018F:u8\",\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\",\"DD\"],\"flagsPreserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"effects\":[{\"op\":\"LoadAccumulatorLow\",\"type\":\"u8\",\"source\":{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"extension\":\"None\",\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"},{\"op\":\"AssignDataDescriptor\",\"type\":\"bool\",\"value\":false}],\"branchPredicate\":null,\"successors\":[21908],\"provenance\":{\"primaryPdfPage\":124,\"primaryPrintedPage\":\"3-70\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5592/5594\"]}},{\"pc\":21908,\"form\":{\"mnemonic\":\"ORB A, #N8\",\"pinnedPatternIndex\":1619,\"length\":2,\"ddMode\":\"0\",\"parsedOperation\":\"ORB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CodeOwnedImmediate\",\"value\":240,\"widthBits\":8}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\",\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[\"ZF\"],\"flagsPreserved\":[\"CF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"BitwiseOr\",\"type\":\"u8\",\"destination\":{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},\"left\":\"AL\",\"right\":{\"kind\":\"CodeOwnedImmediate\",\"value\":240,\"widthBits\":8},\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"}],\"branchPredicate\":null,\"successors\":[21910],\"provenance\":{\"primaryPdfPage\":160,\"primaryPrintedPage\":\"3-107\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR5592/5594\"]}},{\"pc\":21951,\"form\":{\"mnemonic\":\"LB A, #N8\",\"pinnedPatternIndex\":738,\"length\":2,\"ddMode\":\"R\",\"parsedOperation\":\"LB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CodeOwnedImmediate\",\"value\":15,\"widthBits\":8}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AH:u8\"],\"outputs\":[\"AL:u8\"],\"flagsRead\":[],\"flagsWritten\":[\"ZF\",\"DD\"],\"flagsPreserved\":[\"CF\",\"HC\",\"OtherPSW\"],\"effects\":[{\"op\":\"LoadAccumulatorLow\",\"type\":\"u8\",\"source\":{\"kind\":\"CodeOwnedImmediate\",\"value\":15,\"widthBits\":8},\"extension\":\"None\",\"preserveHighByte\":true},{\"op\":\"AssignZeroFlag\",\"type\":\"bool\",\"value\":\"AL\"},{\"op\":\"AssignDataDescriptor\",\"type\":\"bool\",\"value\":false}],\"branchPredicate\":null,\"successors\":[21953],\"provenance\":{\"primaryPdfPage\":124,\"primaryPrintedPage\":\"3-70\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR55BF/55C1/55C3\"]}},{\"pc\":21953,\"form\":{\"mnemonic\":\"STB A, off N8\",\"pinnedPatternIndex\":2301,\"length\":2,\"ddMode\":\"0\",\"parsedOperation\":\"STB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\"],\"outputs\":[\"RAM0117:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"StoreByte\",\"type\":\"u8\",\"source\":\"AL\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":279,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"branchPredicate\":null,\"successors\":[21955],\"provenance\":{\"primaryPdfPage\":208,\"primaryPrintedPage\":\"3-155\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR55BF/55C1/55C3\"]}},{\"pc\":21955,\"form\":{\"mnemonic\":\"STB A, off N8\",\"pinnedPatternIndex\":2301,\"length\":2,\"ddMode\":\"0\",\"parsedOperation\":\"STB\",\"operands\":[{\"kind\":\"AccumulatorLow\",\"name\":\"AL\",\"widthBits\":8,\"address\":null},{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"}]},\"incomingContext\":[\"LRB0021\",\"ByteModeEstablishedAt556F\"],\"inputs\":[\"AL:u8\"],\"outputs\":[\"RAM018F:u8\"],\"flagsRead\":[\"DD\"],\"flagsWritten\":[],\"flagsPreserved\":[\"CF\",\"ZF\",\"HC\",\"DD\",\"OtherPSW\"],\"effects\":[{\"op\":\"StoreByte\",\"type\":\"u8\",\"source\":\"AL\",\"destination\":{\"kind\":\"CurrentPageRam\",\"address\":399,\"widthBits\":8,\"selectorField\":\"n8\",\"requiredLrb\":33,\"byteOrder\":\"NotApplicable\"},\"orderedWrite\":true,\"sameValueWrite\":\"RetainFreshOrdinal\"}],\"branchPredicate\":null,\"successors\":[21957],\"provenance\":{\"primaryPdfPage\":208,\"primaryPrintedPage\":\"3-155\",\"nativeExtentIndependentlyVerified\":true,\"cStatementTags\":[\"IR55BF/55C1/55C3\"]}}]}")
_STAGES = json.loads("{\"InputShape\":\"Input\",\"OriginalSiteInventory\":\"Inventory\",\"OriginalFormLengthMismatch\":\"Inventory\",\"TransferInventory\":\"Transfer\",\"TransferSpecificationMismatch\":\"Transfer\",\"CFGRelationMismatch\":\"CFG\",\"DDRequirementViolation\":\"DD\",\"FlagDependencyMismatch\":\"Flags\",\"MemoryEffectMismatch\":\"Memory\",\"ContextObligationMismatch\":\"Context\",\"ContinuationMismatch\":\"Continuation\",\"RequestDomain\":\"Request\",\"AssignmentInventory\":\"Assignment\",\"SpanOutsideProfile\":\"Span\",\"InstructionOverlap\":\"Span\",\"FallthroughMismatch\":\"Fallthrough\",\"BranchNextOutsideProfile\":\"Branch\",\"BranchTargetMismatch\":\"Branch\",\"Rel8OutOfRange\":\"Branch\",\"SyntheticExternalAnchorCollision\":\"Anchor\",\"ComponentPlanMismatch\":\"Plan\",\"MetadataMismatch\":\"Metadata\"}")
_FLAGS = ("CF", "ZF", "HC", "DD") + tuple("PSW" + str(i) for i in range(12))
_J_IDS = ("DirectJ_NotBelow", "DirectJ_Below")


class CompositionError(ValueError):
    __slots__ = ("code", "path", "stage")

    def __init__(self, code, path, stage):
        self.code, self.path, self.stage = code, path, stage
        self.args = (code, path, stage)


def _need(condition, code, path):
    if not condition:
        raise CompositionError(code, path, _STAGES[code])


def _equal(actual, expected, code, path):
    _need(type(actual) is type(expected), code, path)
    if type(expected) is dict:
        _need(set(actual) == set(expected), code, path)
        for key in expected:
            _equal(actual[key], expected[key], code, path + "/" + str(key))
    elif type(expected) is list:
        _need(len(actual) == len(expected), code, path)
        for i, item in enumerate(expected):
            _equal(actual[i], item, code, path + "/" + str(i))
    else:
        _need(actual == expected, code, path)


def _json_shape(value, path, depth=0):
    """Exact JSON types before field access; bounded depth also rejects cycles."""
    _need(depth <= 64, "InputShape", path)
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is dict:
        for key in value:
            _need(type(key) is str, "InputShape", path)
            _json_shape(value[key], path + "/" + key, depth + 1)
    elif type(value) is list:
        for index, item in enumerate(value):
            _json_shape(item, path + "/" + str(index), depth + 1)
    else:
        _need(False, "InputShape", path)


def _fields(value, keys, path):
    _need(type(value) is dict and set(keys).issubset(value), "InputShape", path)


def _copy(value):
    return json.loads(json.dumps(value))


def _effect_shape(effect, path):
    """Structural keys/types only; semantic changes reach their real stages."""
    required = {
        "LoadAccumulatorLow": ("source", "extension", "preserveHighByte"),
        "LogicalShiftLeft": ("source", "distance", "truncation", "zeroFill"),
        "AssignCarryFromOldBit": ("source", "bit"),
        "AssignZeroFlag": ("value",), "AssignDataDescriptor": ("value",),
        "ReadModifyWriteRotateThroughCarry": ("destination", "direction", "distance", "carryInput", "carryOutput", "truncation", "orderedWrite", "sameValueWrite"),
        "BitwiseAnd": ("destination", "left", "right", "preserveHighByte"),
        "BitwiseOr": ("destination", "left", "right", "preserveHighByte"),
        "UnsignedCompare": ("left", "right", "carryMeaning", "zeroMeaning", "accumulatorWrite", "ramWrite", "extension"),
        "ConditionalJump": ("condition", "ifTrue", "ifFalse"),
        "CopyByte": ("source", "destination", "orderedWrite", "sameValueWrite"),
        "StoreByte": ("source", "destination", "orderedWrite", "sameValueWrite"),
        "ReadModifyWriteAnd": ("destination", "source", "orderedWrite", "sameValueWrite"),
        "ReadModifyWriteOr": ("destination", "source", "orderedWrite", "sameValueWrite"),
    }
    _need(type(effect["op"]) is str, "InputShape", path + "/op")
    _fields(effect, required.get(effect["op"], ()), path)
    for key in ("source", "destination", "left", "right"):
        if key not in effect:
            continue
        operand = effect[key]
        if operand == "AL" and ((key == "source" and effect["op"] in
                ("LogicalShiftLeft", "AssignCarryFromOldBit", "StoreByte", "ReadModifyWriteAnd"))
                or (key == "left" and effect["op"] in ("BitwiseAnd", "BitwiseOr"))):
            continue
        _fields(operand, ("kind",), path + "/" + key)
        if operand["kind"] == "CodeOwnedImmediate":
            _fields(operand, ("value", "widthBits"), path + "/" + key)
    if effect["op"] == "ConditionalJump":
        _need(type(effect["condition"]) in (str, dict), "InputShape", path + "/condition")


def _inventory(ir, contract):
    for label, value, keys in (
            ("original_ir", ir, _ORIGINAL_IR.keys()),
            ("composition_contract", contract, _REVIEWED.keys())):
        _fields(value, keys, label)
    for label, rows in (("original_ir/instructions", ir["instructions"]),
                        ("originalSiteObligations", contract["originalSiteObligations"]),
                        ("originalIRInstructions", contract["originalIRInstructions"])):
        _need(type(rows) is list, "InputShape", label)
        _need(len(rows) == 18, "OriginalSiteInventory", label)
        ids = []
        for row in rows:
            _fields(row, ("pc",), label)
            _need(type(row["pc"]) is int and 0 <= row["pc"] <= 65535,
                  "OriginalSiteInventory", label + "/pc")
            ids.append(row["pc"])
        _need(ids == [row["pc"] for row in _ORIGINAL_IR["instructions"]],
              "OriginalSiteInventory", label)
    instructions = {row["pc"]: row for row in ir["instructions"]}
    sites = {row["pc"]: row for row in contract["originalSiteObligations"]}
    expected = {row["pc"]: row for row in _REVIEWED["originalSiteObligations"]}
    for node, site in sites.items():
        label = "originalSiteObligations/" + str(node)
        _fields(site, expected[node].keys(), label)
        item = instructions[node]
        _fields(item, _ORIGINAL_IR["instructions"][list(instructions).index(node)].keys(),
                "original_ir/" + str(node))
        _fields(item["form"], ("length", "ddMode", "operands", "parsedOperation"),
                "original_ir/" + str(node) + "/form")
        _need(type(item["form"]["operands"]) is list, "InputShape", "original_ir/" + str(node) + "/operands")
        for operand in item["form"]["operands"]:
            _fields(operand, ("kind",), "original_ir/" + str(node) + "/operands")
        _need(type(site["length"]) is int and site["length"] == expected[node]["length"]
              and type(item["form"]["length"]) is int
              and item["form"]["length"] == site["length"]
              and site["formId"] == expected[node]["formId"],
              "OriginalFormLengthMismatch", label)
        _need(type(item["effects"]) is list, "InputShape", "original_ir/" + str(node) + "/effects")
        for effect in item["effects"]:
            _fields(effect, ("op", "type"), "original_ir/" + str(node) + "/effects")
            _effect_shape(effect, "original_ir/" + str(node) + "/effects")
        _fields(site["dd"], ("selection", "transfer"), label + "/dd")
        _fields(site["flags"], ("functionalRead", "written", "preserved", "selectionRead"), label + "/flags")
        _fields(site["memory"], ("reads", "writes"), label + "/memory")
    transfers = contract["abstractTransfers"]
    _need(type(transfers) is list, "InputShape", "abstractTransfers")
    _need(len(transfers) == 2, "TransferInventory", "abstractTransfers")
    _need(all(type(row) is dict and type(row.get("nodeId")) is str for row in transfers),
          "TransferInventory", "abstractTransfers")
    _need([row["nodeId"] for row in transfers] == list(_J_IDS),
          "TransferInventory", "abstractTransfers")
    for actual, reviewed in zip(transfers, _REVIEWED["abstractTransfers"]):
        _equal(actual, reviewed, "TransferSpecificationMismatch", "abstractTransfers/" + actual["nodeId"])
    _need(type(contract["geometry"]) is dict, "InputShape", "geometry")
    return instructions, sites, expected, transfers


def _predicate(item, site):
    pred = item["branchPredicate"]
    branch = site["branch"]
    if pred is None:
        _need(branch is None, "CFGRelationMismatch", "predicate/" + str(item["pc"]))
        return None
    _need(type(pred) is dict and type(branch) is dict, "CFGRelationMismatch",
          "predicate/" + str(item["pc"]))
    if pred.get("op") == "FlagIsSet":
        translated = {"kind": "FlagEquals", "flag": pred.get("flag"), "value": 1}
    elif pred.get("op") == "BitIsSet":
        translated = {"kind": "MemoryBitEquals", "address": pred.get("address"),
                      "bit": pred.get("bit"), "value": 1}
    else:
        _need(False, "CFGRelationMismatch", "predicate/" + str(item["pc"]))
    _equal(translated, branch["predicate"], "CFGRelationMismatch", "predicate/" + str(item["pc"]))
    jumps = [e for e in item["effects"] if e["op"] == "ConditionalJump"]
    _need(len(jumps) == 1, "CFGRelationMismatch", "jump/" + str(item["pc"]))
    jump = jumps[0]
    _need(item["successors"] == [jump.get("ifTrue"), jump.get("ifFalse")]
          and site["successors"] == [branch.get("trueTarget"), branch.get("falseTarget")],
          "CFGRelationMismatch", "successors/" + str(item["pc"]))
    condition = jump.get("condition")
    if translated["kind"] == "FlagEquals":
        _need(condition == translated["flag"], "CFGRelationMismatch", "jump/" + str(item["pc"]))
    else:
        _equal(condition, pred, "CFGRelationMismatch", "jump/" + str(item["pc"]))
    return translated


def _graph(instructions, sites, expected, transfers, contract):
    edges = []
    terminal_slots = {row["predecessor"]: row["nodeId"] for row in transfers}
    for node, item in instructions.items():
        site = sites[node]
        for actual in (item["successors"], site["successors"]):
            _equal(actual, expected[node]["successors"], "CFGRelationMismatch", "successors/" + str(node))
        _equal(item["branchPredicate"],
               _ORIGINAL_IR["instructions"][list(instructions).index(node)]["branchPredicate"],
               "CFGRelationMismatch", "predicate/" + str(node))
        _equal(site["branch"], expected[node]["branch"], "CFGRelationMismatch", "branch/" + str(node))
        predicate = _predicate(item, site)
        for index, target in enumerate(item["successors"]):
            if node in terminal_slots:
                target = terminal_slots[node]
            edges.append({"from": node, "to": target,
                          "kind": "ConditionalTaken" if predicate is not None and index == 0 else "Fallthrough",
                          "predicate": _copy(predicate)})
    for slot in transfers:
        edges.append({"from": slot["nodeId"], "to": slot["target"],
                      "kind": "ExternalTransfer", "predicate": None})
    _equal(contract["composedCFG"], edges, "CFGRelationMismatch", "composedCFG")
    _equal(edges, _REVIEWED["composedCFG"], "CFGRelationMismatch", "derivedCFG")
    order = [node for component in _REVIEWED["componentPlan"] for node in component["nodeIds"]]
    successors, predecessors = {node: [] for node in order}, {node: [] for node in order}
    for edge in edges:
        source, target = edge["from"], edge["to"]
        _need(source in successors, "CFGRelationMismatch", "composedCFG/source")
        if edge["kind"] == "ExternalTransfer":
            _need(source in _J_IDS and target in (21910, 21957),
                  "CFGRelationMismatch", "composedCFG/external")
        else:
            _need(target in predecessors, "CFGRelationMismatch", "composedCFG/target")
            successors[source].append(target)
            predecessors[target].append(source)
    ready = [node for node in order if not predecessors[node]]
    _need(ready == [ir_entry(instructions)], "CFGRelationMismatch", "composedCFG/entry")
    pending = {node: len(predecessors[node]) for node in order}
    topology = []
    while ready:
        node = ready.pop(0)
        topology.append(node)
        for target in successors[node]:
            pending[target] -= 1
            if pending[target] == 0:
                ready.append(target)
    _need(len(topology) == len(order), "CFGRelationMismatch", "composedCFG/DAG")
    _need(all(successors[node] or node in _J_IDS for node in order),
          "CFGRelationMismatch", "composedCFG/reachableTerminals")
    return edges, order, topology, successors, predecessors


def ir_entry(instructions):
    return next(iter(instructions))


def _dd(instructions, sites, expected, order, topology, predecessors, initial):
    incoming, outgoing = {}, {}
    for node in topology:
        state = set(initial) if not predecessors[node] else set()
        for prior in predecessors[node]:
            state.update(outgoing[prior])
        incoming[node] = set(state)
        if node in instructions:
            requirement = sites[node]["dd"]["selection"]
            _need(requirement in ("RequiresDD0", "AcceptsBothIncomingDD"),
                  "DDRequirementViolation", "dd/" + str(node))
            if requirement == "RequiresDD0":
                _need(state == {0}, "DDRequirementViolation", "dd/" + str(node) + "/incoming")
            resets = [e for e in instructions[node]["effects"] if e["op"] == "AssignDataDescriptor"]
            for reset in resets:
                _need(type(reset.get("value")) is bool, "DDRequirementViolation", "dd/" + str(node) + "/value")
                state = {1} if reset["value"] else {0}
        outgoing[node] = state
    for node in sites:
        _equal(sites[node]["dd"], expected[node]["dd"], "DDRequirementViolation", "dd/" + str(node) + "/obligation")
        expected_effects = [e for e in _ORIGINAL_IR["instructions"][list(instructions).index(node)]["effects"]
                            if e["op"] == "AssignDataDescriptor"]
        actual_effects = [e for e in instructions[node]["effects"] if e["op"] == "AssignDataDescriptor"]
        _equal(actual_effects, expected_effects, "DDRequirementViolation", "dd/" + str(node) + "/transfer")
    for node in _J_IDS:
        _need(incoming[node] == outgoing[node] == {0}, "DDRequirementViolation", "dd/" + node)
    return [{"nodeId": node, "incomingMay": sorted(incoming[node]),
             "incomingMust": next(iter(incoming[node])) if len(incoming[node]) == 1 else None,
             "outgoingMay": sorted(outgoing[node]),
             "outgoingMust": next(iter(outgoing[node])) if len(outgoing[node]) == 1 else None,
             "requiresDD0": node in sites and sites[node]["dd"]["selection"] == "RequiresDD0"}
            for node in order]


def _flags(instructions, sites, expected, order, topology, successors, predecessors):
    writes, reads, selection = {}, {}, {}
    flag_operations = ("AssignZeroFlag", "AssignDataDescriptor", "AssignCarryFromOldBit", "UnsignedCompare")
    for node in order:
        actual_writes, actual_reads = set(), set()
        if node in instructions:
            item = instructions[node]
            for effect in item["effects"]:
                if effect["op"] == "AssignZeroFlag":
                    actual_writes.add("ZF")
                elif effect["op"] == "AssignDataDescriptor":
                    actual_writes.add("DD")
                elif effect["op"] in ("AssignCarryFromOldBit", "ReadModifyWriteRotateThroughCarry"):
                    actual_writes.add("CF")
                    if effect["op"] == "ReadModifyWriteRotateThroughCarry":
                        actual_reads.add("CF")
                elif effect["op"] == "UnsignedCompare":
                    actual_writes.update(("CF", "ZF"))
                elif effect["op"] == "ConditionalJump" and effect.get("condition") == "CF":
                    actual_reads.add("CF")
            spec = expected[node]["flags"]
            _equal(sites[node]["flags"], spec, "FlagDependencyMismatch", "flags/" + str(node) + "/typed")
            _need(actual_writes == set(spec["written"]) and actual_reads == set(spec["functionalRead"]),
                  "FlagDependencyMismatch", "flags/" + str(node) + "/derived")
            _equal(item["flagsWritten"], spec["written"], "FlagDependencyMismatch", "flags/" + str(node) + "/IRWritten")
            _equal(item["flagsRead"], spec["functionalRead"] + spec["selectionRead"],
                   "FlagDependencyMismatch", "flags/" + str(node) + "/IRRead")
            _equal(item["flagsPreserved"], spec["preserved"], "FlagDependencyMismatch", "flags/" + str(node) + "/IRPreserved")
            reviewed_item = _ORIGINAL_IR["instructions"][list(instructions).index(node)]
            _equal([e for e in item["effects"] if e["op"] in flag_operations],
                   [e for e in reviewed_item["effects"] if e["op"] in flag_operations],
                   "FlagDependencyMismatch", "flags/" + str(node) + "/effects")
        writes[node], reads[node] = actual_writes, actual_reads
        selection[node] = {"DD"} if node in sites and sites[node]["dd"]["selection"] == "RequiresDD0" else set()
    writers_in, writers_out = {}, {}
    for node in topology:
        arrivals = {flag: {"Incoming"} if not predecessors[node] else set() for flag in _FLAGS}
        for prior in predecessors[node]:
            for flag in _FLAGS:
                arrivals[flag].update(writers_out[prior][flag])
        departures = {flag: set(arrivals[flag]) for flag in _FLAGS}
        for flag in writes[node]:
            departures[flag] = {node}
        writers_in[node], writers_out[node] = arrivals, departures
    _need(writers_in[21874]["CF"] == {21873} and writers_in[21885]["CF"] == {21880},
          "FlagDependencyMismatch", "flags/carryDependencies")
    live_in, live_out = {}, {}
    for node in reversed(topology):
        needed = set(_FLAGS) if node in _J_IDS else set()
        for target in successors[node]:
            needed.update(live_in[target])
        live_out[node] = set(needed)
        live_in[node] = needed.difference(writes[node]).union(reads[node]).union(selection[node])
    return [{"nodeId": node,
             "reachingWritersIn": {flag: sorted(writers_in[node][flag], key=str) for flag in _FLAGS},
             "reachingWritersOut": {flag: sorted(writers_out[node][flag], key=str) for flag in _FLAGS},
             "liveIn": [flag for flag in _FLAGS if flag in live_in[node]],
             "liveOut": [flag for flag in _FLAGS if flag in live_out[node]]}
            for node in order]


def _access(operand, node):
    _fields(operand, ("kind", "address", "widthBits"), "memory/" + str(node))
    _need(operand["kind"] in ("CurrentPageRam", "LocalRegister"),
          "MemoryEffectMismatch", "memory/" + str(node) + "/operand")
    width = operand["widthBits"]
    _need(type(width) is int and width in (8, 16), "MemoryEffectMismatch", "memory/" + str(node) + "/width")
    if width == 16:
        _need(operand.get("byteOrder") == "LittleEndian", "MemoryEffectMismatch", "memory/" + str(node) + "/wordOrder")
    return {"address": operand["address"], "widthBits": width,
            "mode": "CurrentPage" if operand["kind"] == "CurrentPageRam" else "LocalRegister",
            "byteOrder": "LittleEndian" if width == 16 else "Byte"}


def _memory(instructions, sites, expected):
    accesses = {}
    for node, item in instructions.items():
        rows = []
        for effect in item["effects"]:
            op = effect["op"]
            operands = []
            if op == "LoadAccumulatorLow":
                if effect.get("source", {}).get("kind") != "CodeOwnedImmediate":
                    operands.append(("Read", effect["source"]))
            elif op == "BitwiseAnd":
                operands.append(("Read", effect["right"]))
            elif op == "UnsignedCompare":
                operands.append(("Read", effect["left"]))
            elif op == "CopyByte":
                operands.extend((("Read", effect["source"]), ("Write", effect["destination"])))
            elif op in ("ReadModifyWriteRotateThroughCarry", "ReadModifyWriteAnd", "ReadModifyWriteOr"):
                operands.extend((("Read", effect["destination"]), ("Write", effect["destination"])))
            elif op == "StoreByte":
                operands.append(("Write", effect["destination"]))
            elif op == "ConditionalJump" and type(effect.get("condition")) is dict:
                cond = effect["condition"]
                operand = next((o for o in item["form"]["operands"] if o.get("address") == cond.get("address")), None)
                _need(operand is not None, "MemoryEffectMismatch", "memory/" + str(node) + "/branchRead")
                operands.append(("Read", operand))
            else:
                _need(op in ("AssignZeroFlag", "AssignDataDescriptor", "AssignCarryFromOldBit",
                             "LogicalShiftLeft", "BitwiseOr", "ConditionalJump"),
                      "MemoryEffectMismatch", "memory/" + str(node) + "/operation")
            for kind, operand in operands:
                row = _access(operand, node)
                if kind == "Write":
                    _need(effect.get("orderedWrite") is True
                          and effect.get("sameValueWrite") == "RetainFreshOrdinal",
                          "MemoryEffectMismatch", "memory/" + str(node) + "/writeRetention")
                    row.update(operation=op, ordered=True, sameValueWrite="RetainFreshOrdinal")
                rows.append({"kind": kind, **row})
        memory = {"reads": [{k: v for k, v in row.items() if k != "kind"} for row in rows if row["kind"] == "Read"],
                  "writes": [{k: v for k, v in row.items() if k != "kind"} for row in rows if row["kind"] == "Write"]}
        _equal(memory, sites[node]["memory"], "MemoryEffectMismatch", "memory/" + str(node) + "/typed")
        _equal(memory, expected[node]["memory"], "MemoryEffectMismatch", "memory/" + str(node) + "/reviewed")
        accesses[node] = rows
    return accesses


def _symbolic_final(nodes, conditions, instructions):
    """Fold IR terms and facts only: no numeric CPU/RAM state, timers or cycles."""
    al, dd, cf, zf = ("IncomingAL",), None, None, None
    for node in nodes:
        if node not in instructions:
            continue
        item = instructions[node]
        for effect in item["effects"]:
            op = effect["op"]
            if op == "LoadAccumulatorLow":
                operand = effect["source"]
                al = ("Constant", operand["value"]) if operand["kind"] == "CodeOwnedImmediate" else ("Memory", operand["address"])
            elif op == "LogicalShiftLeft":
                al = ("ShiftTerm", al, effect["distance"])
            elif op == "BitwiseAnd":
                al = ("AndTerm", al, effect["right"]["address"])
            elif op == "BitwiseOr":
                al = ("OrTerm", al, effect["right"]["value"])
            elif op == "AssignDataDescriptor":
                dd = 1 if effect["value"] else 0
            elif op == "UnsignedCompare":
                cf = ("ComparisonBorrow", node)
            elif op == "AssignZeroFlag":
                if effect["value"] == "AL" and al[0] == "Constant" and al[1] != 0:
                    zf = 0
                elif effect["value"] == "AL" and al[0] == "OrTerm" and al[2] != 0:
                    zf = 0
                else:
                    zf = ("ZeroPredicate", node, effect["value"])
        for condition in conditions:
            if condition["pc"] == node and item["branchPredicate"].get("flag") == "CF":
                _need(cf == ("ComparisonBorrow", 21880), "FlagDependencyMismatch", "symbolic/CFProducer")
                cf = 1 if condition["result"] else 0
    if al[0] == "Constant":
        final_al = {"kind": "ConstantByte", "value": al[1]}
    elif al[0] == "OrTerm" and al[1][0] == "Memory":
        final_al = {"kind": "FinalMemoryOrImmediate", "address": al[1][1], "immediate": al[2]}
    else:
        _need(False, "MemoryEffectMismatch", "symbolic/AL")
    return {"AL": final_al, "CF": cf, "ZF": zf, "DD": dd,
            "AH": "IncomingAH", "HC": "IncomingHC", "OtherPSW": "IncomingOtherPSW"}


def _paths(edges, instructions, accesses, contract):
    outgoing = {}
    for edge in edges:
        outgoing.setdefault(edge["from"], []).append(edge)
    # Iterative path expansion differs from the independent oracle recursive DFS.
    work = [(ir_entry(instructions), [], [])]
    completed = []
    while work:
        node, visited, conditions = work.pop()
        if node not in outgoing:
            completed.append((visited, conditions, node))
            continue
        for edge in reversed(outgoing[node]):
            next_conditions = list(conditions)
            if edge["predicate"] is not None:
                next_conditions.append({"pc": node, "result": edge["kind"] == "ConditionalTaken"})
            work.append((edge["to"], visited + [node], next_conditions))
    _need(len(completed) == 4, "CFGRelationMismatch", "paths/alternatives")
    _need(type(contract["paths"]) is list and len(contract["paths"]) == 4,
          "ComponentPlanMismatch", "paths")
    results = []
    for index, (nodes, conditions, target) in enumerate(completed):
        identifier = ("A", "B", "C", "D")[index]
        reviewed_path = _REVIEWED["paths"][index]["originalPath"]
        _fields(contract["paths"][index], ("originalPath",), "paths/" + identifier)
        original = contract["paths"][index].get("originalPath")
        _fields(original, reviewed_path.keys(), "paths/" + identifier + "/originalPath")
        for name in ("orderedReads", "orderedWrites", "mustNotRead"):
            _equal(original[name], reviewed_path[name], "MemoryEffectMismatch", "paths/" + identifier + "/" + name)
        _need(sum(node in _J_IDS for node in nodes) == 1 and nodes[-1] in _J_IDS,
              "CFGRelationMismatch", "paths/" + identifier + "/transfer")
        reads, writes, rows = [], [], []
        for node in nodes:
            for item in accesses.get(node, []):
                row = {"pc": node, **{k: v for k, v in item.items() if k != "kind"}}
                if item["kind"] == "Write":
                    row["staticWriteOrdinal"] = len(writes) + 1
                    writes.append(row)
                else:
                    reads.append(row)
                rows.append({"kind": item["kind"], **row})
        _equal(reads, reviewed_path["orderedReads"], "MemoryEffectMismatch", "paths/" + identifier + "/derivedReads")
        _equal([{k: v for k, v in row.items() if k != "staticWriteOrdinal"} for row in writes],
               reviewed_path["orderedWrites"], "MemoryEffectMismatch", "paths/" + identifier + "/derivedWrites")
        _need(all(row["address"] not in reviewed_path["mustNotRead"] for row in reads),
              "MemoryEffectMismatch", "paths/" + identifier + "/mustNotRead")
        final = _symbolic_final(nodes, conditions, instructions)
        _equal(final["AL"], reviewed_path["finalAL"], "MemoryEffectMismatch", "paths/" + identifier + "/AL")
        for flag in ("CF", "ZF", "DD"):
            _equal(final[flag], reviewed_path["final" + flag], "FlagDependencyMismatch", "paths/" + identifier + "/" + flag)
        results.append({"id": identifier, "nodeIds": nodes, "conditions": conditions,
                        "originalInstructionCount": sum(type(node) is int for node in nodes),
                        "abstractTransferCount": sum(node in _J_IDS for node in nodes),
                        "composedNodeCount": len(nodes), "transferNodeId": nodes[-1], "externalTarget": target,
                        "orderedReads": reads, "orderedWrites": writes, "orderedAccesses": rows,
                        "finalState": final, "historicalCoverage": reviewed_path["historical"]})
    return results


def _context(instructions, contract):
    _equal(contract["context"], _REVIEWED["context"], "ContextObligationMismatch", "context")
    for item in instructions.values():
        for effect in item["effects"]:
            if "preserveHighByte" in effect:
                _need(effect["preserveHighByte"] is True, "ContextObligationMismatch", "context/AH")
        for operand in item["form"]["operands"]:
            if "requiredLrb" in operand:
                _need(operand["requiredLrb"] == 33, "ContextObligationMismatch", "context/LRB")
    _equal(contract["continuations"], _REVIEWED["continuations"], "ContinuationMismatch", "continuations")


def _request(candidate, order):
    _need(type(candidate) is dict and set(candidate) ==
          {"syntheticBase", "gap", "initialDD", "nodeAssignments", "classification"},
          "RequestDomain", "request")
    base, gap, initial = candidate["syntheticBase"], candidate["gap"], candidate["initialDD"]
    _need(type(base) is int and 0 <= base <= 65535, "RequestDomain", "request/syntheticBase")
    _need(type(gap) is int and gap >= 0, "RequestDomain", "request/gap")
    _need(type(initial) is list and all(type(value) is int for value in initial)
          and initial in ([0], [1], [0, 1]), "RequestDomain", "request/initialDD")
    _need(candidate["classification"] == "InventedOnlyStaticComposition",
          "RequestDomain", "request/classification")
    supplied = candidate["nodeAssignments"]
    if supplied is None:
        return base, gap, initial, None
    _need(type(supplied) is list and len(supplied) == len(order),
          "AssignmentInventory", "request/nodeAssignments")
    assignments = {}
    for row in supplied:
        _need(type(row) is dict and set(row) == {"nodeId", "assignedPC"},
              "AssignmentInventory", "request/nodeAssignments")
        node, pc = row["nodeId"], row["assignedPC"]
        _need(type(node) in (str, int) and node in order and node not in assignments
              and type(pc) is int and 0 <= pc <= 65535,
              "AssignmentInventory", "request/nodeAssignments")
        assignments[node] = pc
    _need(set(assignments) == set(order), "AssignmentInventory", "request/nodeAssignments")
    return base, gap, initial, assignments


def _geometry(sites, transfers, edges, order, contract, request):
    base, gap, initial, supplied = _request(request, order)
    lengths = {node: row["length"] for node, row in sites.items()}
    lengths.update({slot["nodeId"]: slot["length"] for slot in transfers})
    canonical, components, cursor = {}, [], base
    for component in _REVIEWED["componentPlan"]:
        if component["name"] == "Below":
            cursor += gap
        start = cursor
        for node in component["nodeIds"]:
            canonical[node] = cursor
            cursor += lengths[node]
        components.append({"name": component["name"], "nodeIds": list(component["nodeIds"]),
                           "assignedStart": start, "endExclusive": cursor, "length": cursor - start,
                           "startOffset": start - base, "endOffset": cursor - base,
                           "gapCoefficient": component["gapCoefficient"]})
    actual = canonical if supplied is None else supplied
    spans = []
    component_names = {node: c["name"] for c in _REVIEWED["componentPlan"] for node in c["nodeIds"]}
    for node in order:
        pc = actual[node]
        end = pc + lengths[node]
        _need(0 <= pc <= 65535 and end <= 65536, "SpanOutsideProfile", "spans/" + str(node))
        spans.append({"nodeId": node, "assignedPC": pc, "endExclusive": end,
                      "length": lengths[node], "component": component_names[node],
                      "nodeKind": "AbstractTransferSlot" if node in _J_IDS else "OriginalLogicalInstruction",
                      "originalLogicalSiteId": None if node in _J_IDS else node})
    for i, left in enumerate(spans):
        for right in spans[i + 1:]:
            _need(left["endExclusive"] <= right["assignedPC"] or right["endExclusive"] <= left["assignedPC"],
                  "InstructionOverlap", "spans/" + str(left["nodeId"]) + "/" + str(right["nodeId"]))
    by_node = {row["nodeId"]: row for row in spans}
    for edge in edges:
        if edge["kind"] == "Fallthrough":
            _need(by_node[edge["from"]]["endExclusive"] == actual[edge["to"]],
                  "FallthroughMismatch", "fallthrough/" + str(edge["from"]) + "/" + str(edge["to"]))
    branches = []
    expected_deltas = (26 + gap, 10, 7)
    for edge in edges:
        if edge["kind"] != "ConditionalTaken":
            continue
        origin, target = by_node[edge["from"]], by_node[edge["to"]]
        next_pc = origin["endExclusive"]
        _need(next_pc <= 65535, "BranchNextOutsideProfile", "branch/" + str(edge["from"]) + "/next")
        _need(0 <= target["assignedPC"] <= 65535, "BranchTargetMismatch", "branch/" + str(edge["from"]) + "/target")
        delta = target["assignedPC"] - next_pc
        _need(-128 <= delta <= 127, "Rel8OutOfRange", "branch/" + str(edge["from"]) + "/delta")
        _need(delta == expected_deltas[len(branches)], "BranchTargetMismatch", "branch/" + str(edge["from"]) + "/expectedDelta")
        branches.append({"nodeId": edge["from"], "targetNodeId": edge["to"], "assignedPC": origin["assignedPC"],
                         "length": origin["length"], "nextPC": next_pc,
                         "assignedTargetPC": target["assignedPC"], "signedDelta": delta})
    hole_start, hole_end = base + 42, base + 42 + gap
    anchors = []
    for anchor in (21910, 21957):
        _need(not any(row["assignedPC"] <= anchor < row["endExclusive"] for row in spans),
              "SyntheticExternalAnchorCollision", "anchor/" + str(anchor))
        inside = hole_start <= anchor < hole_end
        anchors.append({"anchor": anchor, "gapContainsAnchor": inside, "assignedNodeCollision": False,
                        "classification": "UnknownGapAnchor_NotSafeFreeROM_NotPhysicalPlacement" if inside else
                        "OutsideAssignedNodeSpans_NotPhysicalPlacement"})
    _equal(actual, canonical, "ComponentPlanMismatch", "actualAssignments")
    _equal(contract["componentPlan"], _REVIEWED["componentPlan"], "ComponentPlanMismatch", "componentPlan")
    for field in ("components", "lengths", "denseOffsets", "gapOnlyBetween", "relativeBranches"):
        _equal(contract["geometry"].get(field), _REVIEWED["geometry"][field], "ComponentPlanMismatch", "geometry/" + field)
    return spans, components, branches, anchors, initial


def evaluate_composition(original_ir, composition_contract, request):
    """Return only this reviewed invented-only static profile, without mutation."""
    for label, value in (("original_ir", original_ir), ("composition_contract", composition_contract), ("request", request)):
        _json_shape(value, label)
        _need(type(value) is dict, "InputShape", label)
    instructions, sites, expected, transfers = _inventory(original_ir, composition_contract)
    edges, order, topology, successors, predecessors = _graph(instructions, sites, expected, transfers, composition_contract)
    domains = ([0], [1], [0, 1])
    dd_checks = [_dd(instructions, sites, expected, order, topology, predecessors, domain) for domain in domains]
    flag_flow = _flags(instructions, sites, expected, order, topology, successors, predecessors)
    accesses = _memory(instructions, sites, expected)
    paths = _paths(edges, instructions, accesses, composition_contract)
    _context(instructions, composition_contract)
    spans, components, branches, anchors, initial = _geometry(sites, transfers, edges, order, composition_contract, request)
    for index, path in enumerate(paths):
        clause = composition_contract["paths"][index]
        expected_clause = {"id": path["id"], "nodeIds": path["nodeIds"],
                           "originalInstructionCount": path["originalInstructionCount"],
                           "abstractTransferCount": path["abstractTransferCount"],
                           "composedNodeCount": path["composedNodeCount"], "transferNodeId": path["transferNodeId"],
                           "externalTarget": path["externalTarget"]}
        for key, value in expected_clause.items():
            _equal(clause.get(key), value, "ComponentPlanMismatch", "paths/" + path["id"] + "/" + key)
    # Late exact identity guard cannot manufacture relation proof or runtime authority.
    _equal(original_ir, _ORIGINAL_IR, "MetadataMismatch", "original_ir")
    _equal(composition_contract, _REVIEWED, "MetadataMismatch", "composition_contract")
    original_length = sum(row["length"] for row in sites.values())
    transfer_length = sum(row["length"] for row in transfers)
    counts = {"originalSites": len(sites), "originalForms": len(set(row["formId"] for row in sites.values())),
              "abstractTransferSlots": len(transfers), "totalNodes": len(order),
              "originalInstructionLength": original_length, "abstractTransferLength": transfer_length,
              "denseLength": original_length + transfer_length,
              "totalLength": components[-1]["endExclusive"] - components[0]["assignedStart"], "edges": len(edges),
              "fallthroughEdges": sum(e["kind"] == "Fallthrough" for e in edges),
              "conditionalTakenEdges": sum(e["kind"] == "ConditionalTaken" for e in edges),
              "externalTransferEdges": sum(e["kind"] == "ExternalTransfer" for e in edges),
              "originalPathCounts": [p["originalInstructionCount"] for p in paths],
              "composedPathCounts": [p["composedNodeCount"] for p in paths],
              "orderedWriteCounts": [len(p["orderedWrites"]) for p in paths],
              "structuralDDDomains": [list(d) for d in domains], "selectedInitialDD": list(initial),
              "historicalPath13NativeWitnesses": 0, "codecCalls": 0, "compositeByteEmissionCalls": 0,
              "CPUExecutions": 0, "actualROMExecutions": 0, "targetObjects": 0, "targetHEX": 0, "FirmwareBIN": 0}
    edge_rows = [{"from": e["from"], "to": e["to"], "kind": e["kind"], "predicate": _copy(e["predicate"]),
                  "fromAssignedPC": next(row["assignedPC"] for row in spans if row["nodeId"] == e["from"]),
                  "fromEndExclusive": next(row["endExclusive"] for row in spans if row["nodeId"] == e["from"]),
                  "toAssignedPC": e["to"] if e["kind"] == "ExternalTransfer" else
                  next(row["assignedPC"] for row in spans if row["nodeId"] == e["to"])}
                 for e in edges]
    return {"classification": "ReviewedStatic20NodeCompositionSpecification", "nodeSpans": spans,
            "componentSpans": components, "gap": {"assignedStart": request["syntheticBase"] + 42,
              "endExclusive": request["syntheticBase"] + 42 + request["gap"],
              "startOffset": 42, "endOffset": 42 + request["gap"], "length": request["gap"],
              "classification": "Unmodeled_NotPadding_NotFreeROM_NotExecutable_NotPhysicalPlacement"},
            "edgeRows": edge_rows, "branchRows": branches, "paths": paths,
            "ddFlow": dd_checks[list(domains).index(initial)], "flagFlow": flag_flow,
            "contextObligations": _copy(composition_contract["context"]), "anchorObservations": anchors, "counts": counts,
            "isolation": {"abstractTransferEdge": "Specified", "architecturalPCReplacement": "Documented",
              "syntheticInternalCFG": "StructurallyIsolated", "nativeExitIsolation": "NotEstablished",
              "actualDownstreamRejoin": "NotEstablished", "physicalPlacement": "NotAuthorized",
              "targetEquivalence": "NotEstablished", "firmwareIntegration": "NotEstablished"},
            "permissions": {"codecsImportedOrCalled": False, "compositeBytes": False, "instructionStream": False,
              "CPU": False, "ROM": False, "assemblyObjectsFirmware": False, "GUIHardware": False}}
