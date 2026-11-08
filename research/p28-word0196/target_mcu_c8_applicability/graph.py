"""Keep physical custody and opcode applicability on separate proof axes."""
from enclosing_caller_return.state import need, shape

from .isa import c8_revision_evidence
from .provenance import rom_to_hardware_provenance

NODES = (
    'StudiedROM', 'ArchiveAcquisition', 'PrearchiveExtraction', 'ECUPhysicalDonor',
    'ECULabel', 'PCBRevision', 'MCUMarking', 'CatalogMCUPart', 'CustomerCode',
    'SiliconRevision', 'ProgramMemorySelection', 'DataMemoryMapping',
    'ManufacturerISA', 'C8InstructionRule', 'C8SiliconObservation', 'TargetC8Applicability',
)

# Current frozen evidence cannot provide an actual donor or silicon revision.
# Each gap is an independent edge, so a later catalogue or manual cannot
# bridge the missing extraction custody through transitive inference.
GAPS = (
    ('ArchiveAcquisition', 'PrearchiveExtraction', 'Unknown',
     'OriginalExtractionRecordWithExactByteIdentity'),
    ('PrearchiveExtraction', 'ECUPhysicalDonor', 'Unknown',
     'OriginalExtractionRecordLinkedToStableDonor'),
    ('ECUPhysicalDonor', 'ECULabel', 'Unknown', 'SameUnitLabelCustody'),
    ('ECUPhysicalDonor', 'PCBRevision', 'Unknown', 'SameUnitBoardCustody'),
    ('PCBRevision', 'MCUMarking', 'Unknown', 'ReadableSameUnitMarkingAndPackage'),
    ('MCUMarking', 'CatalogMCUPart', 'Unknown', 'ApplicableManufacturerAlias'),
    ('CatalogMCUPart', 'CustomerCode', 'Unknown', 'ApplicableManufacturerCodeMapping'),
    ('CustomerCode', 'SiliconRevision', 'Unknown', 'VerifiedSiliconRevision'),
    ('PCBRevision', 'ProgramMemorySelection', 'Unknown', 'SameUnitProgramDeviceEaAndDecode'),
    ('PCBRevision', 'DataMemoryMapping', 'Unknown', 'SameUnitDataDecodeAndStackMapping'),
    ('SiliconRevision', 'ManufacturerISA', 'Unknown', 'ExactPartRevisionManualApplicability'),
    ('ManufacturerISA', 'C8InstructionRule', 'PrimaryTextWithUnresolvedConflict', 'ApplicableExactC8Clarification'),
    ('SiliconRevision', 'C8SiliconObservation', 'Unknown', 'AuthenticatedExistingCmpAndC8Observation'),
    ('C8InstructionRule', 'TargetC8Applicability', 'Unknown', 'BothProofAxesBoundToSameRevision'),
)


def _edge(start, end, category, missing, accepted):
    archive = start == 'StudiedROM'
    c8 = start == 'ManufacturerISA'
    return {
        'from': start, 'to': end,
        'sourceId': 'M2cmRecordedArchiveAcquisition' if archive else 'Oki1991C8Instruction' if c8 else None,
        'locator': 'M2cmAcquisitionAudit' if archive else 'PrintedPage3-66' if c8 else None,
        'subject': 'StudiedImage' if archive else 'MSM66201Manual' if c8 else None,
        'category': category,
        'provenance': 'RecordedProjectAcquisition' if archive else 'AcceptedManufacturerText' if c8 else 'Unbound',
        'independence': 'AcceptedProjectRecord' if archive else 'OneDocumentIdentity' if c8 else 'NoQualifiedWitness',
        'rationale': 'ExactRecordedByteBinding' if accepted else 'RequiredEdgeUnverified',
        'conflict': 'OR_AND_UNRESOLVED' if c8 else None,
        'applicability': 'ProjectFileOnly' if accepted else 'NotEstablished',
        'missingConfirmation': missing, 'privacy': 'RedactedDocumentaryMetadata',
    }


def target_c8_applicability(query):
    """Join reviewed evidence without assigning a donor from archive or part data."""
    shape(query, ('custody', 'isa', 'claim'), 'ClosedTargetApplicabilityQueryRequired')
    need(query['claim'] in ('Inspect', 'AssertTargetRule', 'AuthorizeExecution'),
         'KnownTargetApplicabilityClaimRequired')
    custody = rom_to_hardware_provenance(query['custody'])
    isa = c8_revision_evidence(query['isa'])
    accepted_archive = custody['projectArchiveAcquisition'] is True
    accepted, rejected = [], []
    first = _edge('StudiedROM', 'ArchiveAcquisition', 'AuthenticatedArchive',
                  None if accepted_archive else 'ExactAcceptedProjectArchiveBinding', accepted_archive)
    (accepted if accepted_archive else rejected).append(first)
    rejected.extend(_edge(*gap, False) for gap in GAPS)
    status = 'IndeterminateObligation' if query['claim'] == 'Inspect' else 'OutsideVerifiedScope'
    return {
        'status': status,
        'reason': {'Inspect': 'TargetMcuAndExactC8ApplicabilityUnresolved',
                   'AssertTargetRule': 'TargetJunctionUnestablished',
                   'AuthorizeExecution': 'DocumentaryEvidenceConfersNoExecutionAuthority'}[query['claim']],
        'hardwareAxis': custody, 'isaAxis': isa, 'nodes': list(NODES),
        'acceptedEdges': accepted, 'rejectedEdges': rejected,
        'actualMcuIdentity': None, 'actualSiliconConfirmed': False,
        'targetC8Applicability': None, 'junctionEstablished': False,
        'unresolvedConstraints': ['OriginalPhysicalExtractionUnbound',
                                  'SameUnitMcuRevisionUnbound', 'ExactC8PrimaryConflictUnresolved'],
        'minimumProofPacket': [
            {'record': 'OriginalExtractionCustody', 'binds': ['ExactStudiedByteIdentity', 'StableDonor']},
            {'record': 'ExistingSameUnitDocumentation', 'binds': ['ECULabel', 'BothPcbSides',
                                                                'FullMcuMarking', 'ProgramDeviceAndSelection']},
            {'record': 'ApplicableManufacturerRevisionEvidence', 'binds': ['ExactPartAndRevision',
                                                                          'ExactC8EqualityAndLowerRule']},
        ],
    }
