"""Separate catalog naming and documentary ISA scope from produced silicon."""

import re

from enclosing_caller_return.state import input_class, label, need, number, shape


MASK_PARTS = ('MSM66201', 'MSM66207')
OTP_PARTS = {'MSM66P201': 'MSM66201', 'MSM66P207': 'MSM66207'}
PARTS = (*MASK_PARTS, *OTP_PARTS)
JOINT_SPEC = 'Oki1998JointDeviceSpec'
EARLY_207 = 'OkiNov1990_207DeviceSpec'
C8_MANUAL = 'Oki1991C8Instruction'
INSTRUCTION_LIST = 'Oki1998InstructionList'
RELATED_CORE = 'Oki1999Nx8500S'
SOURCE_IDENTITIES = {
    'Oki1998EnDeviceSpec': JOINT_SPEC,
    'Oki1998JaDeviceSpec': JOINT_SPEC,
    EARLY_207: EARLY_207,
    C8_MANUAL: C8_MANUAL,
    'Oki1991C8SameEditionMirror': C8_MANUAL,
    INSTRUCTION_LIST: INSTRUCTION_LIST,
    RELATED_CORE: RELATED_CORE,
    'SearchIndexOnly': 'SearchIndexOnly',
    'EmulatorBehavior': 'EmulatorBehavior',
}
SOURCE_SCOPES = {
    JOINT_SPEC: 'ManufacturerPartFamily',
    EARLY_207: 'PreliminaryManufacturerMnemonicList',
    C8_MANUAL: 'PrimaryDocumentText',
    INSTRUCTION_LIST: 'ManufacturerMnemonicList',
    RELATED_CORE: 'ComparativeFamilyEvidence',
    'SearchIndexOnly': 'SearchIndexOnly',
    'EmulatorBehavior': 'SecondaryTechnicalClaim',
}


def _source_groups(query):
    input_class(query['inputClass'])
    sources = query['sourceIds']
    need(type(sources) is list and len(sources) <= 16
         and all(type(source) is str and source in SOURCE_IDENTITIES for source in sources),
         'ClosedManufacturerSourceInventoryRequired')
    need(all(label(query[key]) for key in ('catalogPart', 'customerCode', 'siliconRevision')),
         'TypedCatalogCodeRevisionRequired')
    groups = {}
    for source in sorted(set(sources)):
        groups.setdefault(SOURCE_IDENTITIES[source], []).append(source)
    return {identity: {'documentId': identity, 'sourceIds': groups[identity], 'scope': SOURCE_SCOPES[identity]}
            for identity in sorted(groups)}


def customer_code_applicability(query):
    """Extract literal notation and identify what the package list documents."""
    shape(query, ('inputClass', 'literalMarking', 'catalogPart', 'customerCode', 'siliconRevision',
                  'sourceIds', 'claim'), 'ClosedCustomerCodeQueryRequired')
    groups = _source_groups(query)
    marking = query['literalMarking']
    need(label(marking) and query['claim'] in ('Inspect', 'ResolveAlias', 'DecodeCustomerCode', 'PromoteRevision'),
         'TypedCustomerCodeClaimRequired')
    part = query['catalogPart']
    asserted_code = query['customerCode']
    literal = re.fullmatch(r'M66207-([0-9]{3})', marking or '')
    digits = literal[1] if literal else None
    has_joint_spec = JOINT_SPEC in groups and part in PARTS
    has_early_207 = EARLY_207 in groups and part in ('MSM66207', 'MSM66P207')
    reason = 'ManufacturerAliasCodeAndRevisionMappingMissing'
    status = 'CustomerCodeSemanticsUnestablished'
    if query['claim'] != 'Inspect':
        reason, status = 'UnsupportedCodeOrRevisionPromotion', 'OutsideVerifiedScope'
    elif part not in PARTS:
        reason = 'ReviewedCatalogPartRequired'
    elif digits is not None and asserted_code not in (None, digits):
        reason = 'LiteralNumberAndAssertedCodeDiffer'
    elif not has_joint_spec and not has_early_207:
        reason = 'ApplicableManufacturerDeviceSpecificationRequired'
    return {
        'status': status, 'reason': reason, 'literalMarking': marking, 'literalNumericSuffix': digits,
        'catalogPart': part, 'assertedCustomerCode': asserted_code, 'assertedRevision': query['siliconRevision'],
        'catalogCodeNumberField': 'xxx' if has_joint_spec and part in MASK_PARTS else None,
        'catalogPackageSuffixes': (['SS', 'GS-BK', 'JS'] if part in MASK_PARTS else ['SS', 'JS'])
        if has_joint_spec else [],
        'catalogProgramTechnology': ('MaskROM' if part in MASK_PARTS else 'OTP')
        if has_joint_spec or has_early_207 else None,
        'manufacturerLiteralAlias': None, 'resolvedCustomerCode': None, 'resolvedSiliconRevision': None,
        'sourceWitnesses': list(groups.values()), 'actualMcuIdentity': None, 'actualSiliconConfirmed': False,
        'unresolvedConstraints': ['ApplicableManufacturerLiteralAlias', 'SpecificCustomerOrMaskCodeMapping',
                                  'ExactSiliconRevisionBinding'],
    }


def c8_revision_evidence(query):
    """Classify documentary witnesses by exact part, opcode and revision scope."""
    shape(query, ('inputClass', 'catalogPart', 'siliconRevision', 'customerCode', 'opcode', 'sourceIds', 'claim'),
          'ClosedC8RevisionQueryRequired')
    groups = _source_groups(query)
    opcode, part = query['opcode'], query['catalogPart']
    need(number(opcode, 0xFF) and query['claim'] in ('Inspect', 'ResolveOr', 'ResolveAnd', 'BindTarget'),
         'TypedC8RevisionClaimRequired')
    exact_opcode = opcode == 0xC8
    has_family = JOINT_SPEC in groups and part in PARTS
    has_early_207 = EARLY_207 in groups and part in ('MSM66207', 'MSM66P207')
    has_mnemonic_list = INSTRUCTION_LIST in groups and part in PARTS
    has_primary_text = exact_opcode and C8_MANUAL in groups
    has_comparative_text = exact_opcode and RELATED_CORE in groups
    status, reason = 'C8_PRIMARY_CONFLICT_UNRESOLVED', 'ExactPredicateWitnessMissing'
    if query['claim'] != 'Inspect':
        status, reason = 'OutsideVerifiedScope', 'TargetOrPredicatePromotionRefused'
    elif not exact_opcode:
        status, reason = 'OutsideVerifiedScope', 'ExactC8OpcodeRequired'
    elif part not in PARTS:
        reason = 'ReviewedCatalogPartRequired'
    elif query['siliconRevision'] is not None:
        reason = 'RevisionSpecificC8ProofMissing'
    elif has_primary_text:
        reason = 'PublishedC8PredicateConflictUnresolved'
    elif has_family or has_early_207 or has_mnemonic_list:
        reason = 'ManufacturerFamilyOrMnemonicOnly'
    elif has_comparative_text:
        reason = 'OnlyComparativeFamilySource'
    return {
        'status': status, 'reason': reason, 'catalogPart': part, 'opcode': opcode,
        'assertedRevision': query['siliconRevision'], 'assertedCustomerCode': query['customerCode'],
        'documentedCore': 'nX-8/200' if has_family and part in MASK_PARTS else None,
        'otpCounterpartOf': OTP_PARTS.get(part) if has_family or has_early_207 else None,
        'familyInstructionListScope': 'JC' if has_mnemonic_list else None,
        'preliminary207Mnemonic': 'JC GT denotes greater comparison' if has_early_207 else None,
        'primaryC8Text': ({'catalogPart': 'MSM66201', 'opcode': 0xC8, 'predicate': 'PrintedOr',
                           'sameCatalogPart': part == 'MSM66201'} if has_primary_text else None),
        'comparativeText': ({'core': 'nX-8/500S', 'opcode': 0xF0, 'predicate': 'ComparativeAnd'}
                            if has_comparative_text else None),
        'sourceWitnesses': list(groups.values()), 'exactRevisionApplicable': None, 'exactSiliconPredicate': None,
        'actualMcuIdentity': None, 'actualSiliconConfirmed': False, 'newDecisiveEvidence': False,
        'unresolvedConstraints': ['ExactPartAndSiliconRevisionApplicability', 'ApplicableExactC8Clarification',
                                  'ApplicableVerifiedSiliconObservation'],
    }
