"""Independent pre-analysis M2cm reference.

Documentary literals share a separately reviewed input specification; they are
not a second manufacturer acquisition or actual hardware observation. Capacity
premises and claim relations are derived independently below. This module does
not import the analyzer or load the runtime contract.
"""
from copy import deepcopy
import json


EXPECTED_DOCUMENTARY = {'attributionPairs': [{'left': {'exclusive': False,
                                'independenceGroup': 'ArchiveCatalogue',
                                'property': 'EcuAssociation',
                                'sourceRefs': [{'locator': 'Code/model table entry or visible co-located '
                                                           'source-unit photo labels; not studied donor',
                                                'sourceHash': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b',
                                                'sourceId': 'ArchiveCatalogue'}],
                                'subject': 'code304',
                                'unitScope': None,
                                'value': 'P28-A01'},
                       'right': {'exclusive': False,
                                 'independenceGroup': 'HAshop',
                                 'property': 'EcuAssociation',
                                 'sourceRefs': [{'locator': 'Code/model table entry or visible '
                                                            'co-located source-unit photo labels; not '
                                                            'studied donor',
                                                 'sourceHash': '5eb811d9c7de994886b2a269b9fbf617a11d5b14e8d8237d523b16dd6a5118ad',
                                                 'sourceId': 'HALoggedList'}],
                                 'subject': 'code304',
                                 'unitScope': None,
                                 'value': 'P28-A02'}},
                      {'left': {'exclusive': False,
                                'independenceGroup': 'ArchiveCatalogue',
                                'property': 'EcuAssociation',
                                'sourceRefs': [{'locator': 'Code/model table entry or visible co-located '
                                                           'source-unit photo labels; not studied donor',
                                                'sourceHash': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b',
                                                'sourceId': 'ArchiveCatalogue'}],
                                'subject': 'code304',
                                'unitScope': None,
                                'value': 'P28-A01'},
                       'right': {'exclusive': False,
                                 'independenceGroup': 'HAshop',
                                 'property': 'EcuAssociation',
                                 'sourceRefs': [{'locator': 'Code/model table entry or visible '
                                                            'co-located source-unit photo labels; not '
                                                            'studied donor',
                                                 'sourceHash': '5eb811d9c7de994886b2a269b9fbf617a11d5b14e8d8237d523b16dd6a5118ad',
                                                 'sourceId': 'HALoggedList'}],
                                 'subject': 'code304',
                                 'unitScope': None,
                                 'value': 'P28-A52'}},
                      {'left': {'exclusive': False,
                                'independenceGroup': 'ArchiveCatalogue',
                                'property': 'EcuAssociation',
                                'sourceRefs': [{'locator': 'Code/model table entry or visible co-located '
                                                           'source-unit photo labels; not studied donor',
                                                'sourceHash': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b',
                                                'sourceId': 'ArchiveCatalogue'}],
                                'subject': 'code251',
                                'unitScope': None,
                                'value': 'P28-A51'},
                       'right': {'exclusive': False,
                                 'independenceGroup': 'HAshop',
                                 'property': 'EcuAssociation',
                                 'sourceRefs': [{'locator': 'Code/model table entry or visible '
                                                            'co-located source-unit photo labels; not '
                                                            'studied donor',
                                                 'sourceHash': '5eb811d9c7de994886b2a269b9fbf617a11d5b14e8d8237d523b16dd6a5118ad',
                                                 'sourceId': 'HALoggedList'}],
                                 'subject': 'code251',
                                 'unitScope': None,
                                 'value': 'P28-A01'}},
                      {'left': {'exclusive': False,
                                'independenceGroup': 'ArchiveCatalogue',
                                'property': 'EcuAssociation',
                                'sourceRefs': [{'locator': 'Code/model table entry or visible co-located '
                                                           'source-unit photo labels; not studied donor',
                                                'sourceHash': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b',
                                                'sourceId': 'ArchiveCatalogue'}],
                                'subject': 'code251',
                                'unitScope': None,
                                'value': 'P28-A51'},
                       'right': {'exclusive': False,
                                 'independenceGroup': 'HAshop',
                                 'property': 'EcuAssociation',
                                 'sourceRefs': [{'locator': 'Code/model table entry or visible '
                                                            'co-located source-unit photo labels; not '
                                                            'studied donor',
                                                 'sourceHash': '5eb811d9c7de994886b2a269b9fbf617a11d5b14e8d8237d523b16dd6a5118ad',
                                                 'sourceId': 'HALoggedList'}],
                                 'subject': 'code251',
                                 'unitScope': None,
                                 'value': 'P28-A51'}},
                      {'left': {'exclusive': False,
                                'independenceGroup': 'HAshop',
                                'property': 'EcuAssociation',
                                'sourceRefs': [{'locator': 'Code/model table entry or visible co-located '
                                                           'source-unit photo labels; not studied donor',
                                                'sourceHash': '5eb811d9c7de994886b2a269b9fbf617a11d5b14e8d8237d523b16dd6a5118ad',
                                                'sourceId': 'HALoggedList'}],
                                'subject': 'code251',
                                'unitScope': None,
                                'value': 'P28-A01'},
                       'right': {'exclusive': False,
                                 'independenceGroup': 'EbayA01Photo',
                                 'property': 'EcuAssociation',
                                 'sourceRefs': [{'locator': 'Code/model table entry or visible '
                                                            'co-located source-unit photo labels; not '
                                                            'studied donor',
                                                 'sourceHash': '9a2db02fbe46f7195e6647f9b2d78648ac21be6d7c40e99bad3980773c5ab866',
                                                 'sourceId': 'EbayA01Photo'}],
                                 'subject': 'code251',
                                 'unitScope': None,
                                 'value': 'P28-A01'}},
                      {'left': {'exclusive': False,
                                'independenceGroup': 'HAshop',
                                'property': 'EcuAssociation',
                                'sourceRefs': [{'locator': 'Code/model table entry or visible co-located '
                                                           'source-unit photo labels; not studied donor',
                                                'sourceHash': '5eb811d9c7de994886b2a269b9fbf617a11d5b14e8d8237d523b16dd6a5118ad',
                                                'sourceId': 'HALoggedList'}],
                                'subject': 'code304',
                                'unitScope': None,
                                'value': 'P28-A02'},
                       'right': {'exclusive': False,
                                 'independenceGroup': 'DGTuneA02Photo',
                                 'property': 'EcuAssociation',
                                 'sourceRefs': [{'locator': 'Code/model table entry or visible '
                                                            'co-located source-unit photo labels; not '
                                                            'studied donor',
                                                 'sourceHash': '9377ce0ad3d5960b27822be928a6e0471cc1155eed31cd5c2f7e2354575e5aa2',
                                                 'sourceId': 'DGTuneA02Photo'}],
                                 'subject': 'code304',
                                 'unitScope': None,
                                 'value': 'P28-A02'}}],
 'authority': {'actualData03f3Generation': None,
               'actualEcuIdentity': None,
               'actualMcuIdentity': None,
               'actualSiliconConfirmed': False,
               'currentSsp': None,
               'desktop': 'NotRun',
               'executionStatus': 'EXECUTION_BLOCKED',
               'firmwareReady': False,
               'historical17': 'NotRun',
               'iePolarityConflict': 'Unresolved',
               'newCpuRomIrqRtiExecutions': 0,
               'newDisassemblyPerformed': False,
               'physicalPeripheralApplicability': None,
               'runtimeAdmission': False,
               'rxAckReassertion': 'Unknown',
               'safeActualFrame': None},
 'backlog': [{'canEstablishStatically': 'Reuse independently reviewed CFG, unsigned16 CMP0196 vs '
                                        'code-owned00C0, carry5571->5572 and5578->557D, gate read '
                                        'suppression, full intermediate PSW obligations and ordered '
                                        'same-value writes. Define reusable source-level pre/post/effect '
                                        'interface without target execution.',
              'category': 'A',
              'id': 'STATIC-A1',
              'missingForPhysicalPromotion': ['Same-unit MCU/map bridge',
                                              'Actual entry context and owner generations',
                                              'Native upstream/downstream continuity'],
              'mustNotClaim': 'New discovery/equivalence of already-established M2av, actual input '
                              'ownership, physical variable meaning, compilerABI or firmware '
                              'integration.',
              'newDisassemblyPerformed': False,
              'newExecutionAuthorized': False,
              'nextBoundedArtifact': 'Catalogue of reusable proven algorithm obligations and declared '
                                     'cross-block input/output dependencies; no new disassembly or '
                                     'execution.',
              'priority': 1,
              'reviewedScope': '18 sites556F..stop-before5596/55C5;15 forms;four '
                               'paths10/12/13/15;writes3/3/3/5',
              'sourceRefs': [{'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4',
                              'sourceId': 'M2avIR'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3',
                              'sourceId': 'M2avC11'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': 'ba74df64fbb201d2aa6e5577b15262bd1927639c55bbd06effac298bb307d52f',
                              'sourceId': 'M2bdDoc'}],
              'title': 'Source-qualified catalogue and composition interface of the existing word0196 '
                       'algorithm'},
             {'canEstablishStatically': 'Treat received F and retained parser inputs as symbolic '
                                        'unknowns. Prove CMP0264 testsr5 notF;evenF can '
                                        'reach0269;ordered effects0222,0269,026D,026F,0270;this path '
                                        'does not setready0356.7. Separate AL retention after read from '
                                        'later peripheral replacement.',
              'category': 'A',
              'id': 'STATIC-A2',
              'missingForPhysicalPromotion': ['ApplicableSRBUF semantics',
                                              'Actual parser context',
                                              'Actual frame and RAM/write generations'],
              'mustNotClaim': 'An RX completion, IRQ delivery, actual byte/current03F3 owner, ready '
                              'flag, intact physical frame or actualRTI.',
              'newDisassemblyPerformed': False,
              'newExecutionAuthorized': False,
              'nextBoundedArtifact': 'Typed pure source-level Flag path contract with independent '
                                     'symbolic/refusal controls on the existing reviewed sites only.',
              'priority': 2,
              'reviewedScope': 'Existing selected28-site conditional Flag '
                               'path;0262/0264/0267/0269;selected five persistent writes',
              'sourceRefs': [{'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60',
                              'sourceId': 'M2cjDoc'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4209f3abc3676aa3eb89bc9e5182aa2049210b322b7598166981e9559592eb5e',
                              'sourceId': 'M2ckDoc'}],
              'title': 'Conditional Flag byte producer and ordered parser effects'},
             {'canEstablishStatically': 'Prove literal equality and write order forPairA/PairB, mutually '
                                        'exclusive branch selection and consistency ofmode0217.2 '
                                        'withF8/IE/FA under closed uninfluenced assumptions. Show '
                                        'directIE store precedes shadow updates and is not atomic. '
                                        'Preserve bothIE polarity hypotheses.',
              'category': 'A',
              'id': 'STATIC-A3',
              'missingForPhysicalPromotion': ['Actual current mode/mask owners',
                                              'ApplicableIE polarity',
                                              'Interference/nesting evidence'],
              'mustNotClaim': 'Current mode, actual IE/MIE writer generations, concurrentIRQ order, '
                              'interrupt permissibility or actual delivery.',
              'newDisassemblyPerformed': False,
              'newExecutionAuthorized': False,
              'nextBoundedArtifact': 'Small symbolic transition relation and interference obligations '
                                     'over already-reviewed mask-switch sources.',
              'priority': 3,
              'reviewedScope': '3F14/3F16/3F18/3F1D;3F28/3F2A/3F2C/3F31;54DD..54F0;3E81..3E9B',
              'sourceRefs': [{'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60',
                              'sourceId': 'M2cjDoc'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4209f3abc3676aa3eb89bc9e5182aa2049210b322b7598166981e9559592eb5e',
                              'sourceId': 'M2ckDoc'}],
              'title': 'Mode/shadow mask consistency independent of unresolved physical polarity'},
             {'canEstablishStatically': 'Retain competing predicates and prove conditional implications '
                                        'separately;source/mirror counting cannot choose '
                                        'produced-silicon behavior.',
              'category': 'B',
              'id': 'SEM-B1',
              'missingForPhysicalPromotion': ['Independent exact-applicability semantics',
                                              'Affected revision bridge'],
              'mustNotClaim': 'JGT correction or termination proof from conventional mnemonic/program '
                              'intent/emulator output.',
              'newDisassemblyPerformed': False,
              'newExecutionAuthorized': False,
              'nextBoundedArtifact': 'Applicable independent manufacturer erratum/produced-chip '
                                     'observation specification, only if separately authorized;no new '
                                     'inquiry or runtime here.',
              'priority': 4,
              'reviewedScope': 'Known printedOR versus currentAND conflict;equal/less distinguishing '
                               'cases',
              'sourceRefs': [{'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': 'ee5359ff1573e28e7ef2f07151a537ec25332208c85ebdc5eb9ce460c06ad773',
                              'sourceId': 'M2amDoc'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                              'sourceId': 'M2clPublic'}],
              'title': 'ExactJGT C8 comparison predicate'},
             {'canEstablishStatically': 'Enumerate standard candidate-specific locations and numeric '
                                        'aliases as conditional relations. Standard201 externalDATA is '
                                        'supported, not ruled out. Use newerM2cl fullmap qualification '
                                        'over oldM2aw pending207 interval.',
              'category': 'C',
              'id': 'MAP-C1',
              'missingForPhysicalPromotion': ['Same-unit board/MCU/ROM custody',
                                              'ActualEA/population/decode/aliases',
                                              'OwnedSSP/frame storage'],
              'mustNotClaim': 'Physical writableRAM, actualSSP, safe frame,actualEA/external decode or '
                              'same-unitMCU.',
              'newDisassemblyPerformed': False,
              'newExecutionAuthorized': False,
              'nextBoundedArtifact': 'Source-qualified alias/mapping obligations tied to authenticated '
                                     'board evidence, not fabricated state.',
              'priority': 5,
              'reviewedScope': 'Standard201/207 map;DATA03F0..03F7/047E;LRB/SCB selectors and '
                               'potentialframe aliases',
              'sourceRefs': [{'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                              'sourceId': 'M2clPublic'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '122bbb14adcd5718dc3fbb3fefb19dee74a9228099278802254ef6c7d59f8174',
                              'sourceId': 'M2awDoc'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60',
                              'sourceId': 'M2cjDoc'}],
              'title': 'Actual RAM/PR/page/stack alias and external decode applicability'},
             {'canEstablishStatically': 'Retain source-qualified receive completion/MPC-ignore/overrun '
                                        'rules and exact softwareclear54EA cut. Source evidence '
                                        'favorsIEset1 while165/167 contradiction remains.',
              'category': 'D',
              'id': 'PERIPH-D1',
              'missingForPhysicalPromotion': ['Actual customer/peripheral revision',
                                              'Missing applicableACK/arbitration rules',
                                              'ResolvedIE source conflict'],
              'mustNotClaim': 'ACK on0055read, automatic unread reassertion, hardware-set/software-clear '
                              'collision priority, actual pending owner or standardtable applicability '
                              'to unidentifiedsilicon.',
              'newDisassemblyPerformed': False,
              'newExecutionAuthorized': False,
              'nextBoundedArtifact': 'Applicable edition/OEM-linked primary peripheral text and revision '
                                     'bridge;separate from static software reconstruction.',
              'priority': 6,
              'reviewedScope': 'SRCON0054,SRBUF0055,SRSTAT0056,IRQ/IE0018..001B;RXvector000A',
              'sourceRefs': [{'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60',
                              'sourceId': 'M2cjDoc'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4209f3abc3676aa3eb89bc9e5182aa2049210b322b7598166981e9559592eb5e',
                              'sourceId': 'M2ckDoc'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                              'sourceId': 'M2clPublic'}],
              'title': 'Applicable RX lifetime/ACK/reassertion andIE conflict'},
             {'canEstablishStatically': 'Inventory known software writes and qualified standard reset '
                                        'values without assuming current hardwarestate.',
              'category': 'D',
              'id': 'PERIPH-D2',
              'missingForPhysicalPromotion': ['WDT commandsemantics',
                                              'Actualreset event/sourceownership',
                                              'Actualclock/peripheralconfiguration'],
              'mustNotClaim': 'Progress afterWDT3C, safe reset/currentSSP, physical elapsedtime or '
                              'schedulerreconstruction.',
              'newDisassemblyPerformed': False,
              'newExecutionAuthorized': False,
              'nextBoundedArtifact': 'Only targeted applicable primary peripheral/revision evidence;no '
                                     'broad repeatsearch,simulation or hardwareexperiment.',
              'priority': 7,
              'reviewedScope': 'ExistingWDT3C/reset/clock unknowns retained',
              'sourceRefs': [{'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                              'sourceId': 'M2clPublic'}],
              'title': 'WDT/reset and physical peripheral timing'},
             {'canEstablishStatically': 'Specify obligations and alias/nesting hazards. '
                                        'FramePC/A/LRB/PSW generations mustmatch;RTIrestore is not029C '
                                        'or arbitraryhost28AE;IE is not restored byRTI.',
              'category': 'E',
              'id': 'NATIVE-E1',
              'missingForPhysicalPromotion': ['Actualreceivedbyte/history',
                                              'Source-owned current masks/pending',
                                              'Safeeight-byteframe andnesting',
                                              'Matchingreturn/foregroundobservations'],
              'mustNotClaim': 'ActualIRQ/RTI, native owner lineage, safeSSP or foregroundcontinuity from '
                              'inventednumeric nonoverlap.',
              'newDisassemblyPerformed': False,
              'newExecutionAuthorized': False,
              'nextBoundedArtifact': 'Separately authorized owned observations only after '
                                     'identity/map/peripheral prerequisites;not executable inM2cm.',
              'priority': 8,
              'reviewedScope': 'SRBUFgeneration->0262->0269->029CRTI and savedforegroundPC',
              'sourceRefs': [{'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60',
                              'sourceId': 'M2cjDoc'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': '4209f3abc3676aa3eb89bc9e5182aa2049210b322b7598166981e9559592eb5e',
                              'sourceId': 'M2ckDoc'},
                             {'locator': 'Existing bounded research scope; no new execution or '
                                         'disassembly',
                              'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                              'sourceId': 'M2clPublic'}],
              'title': 'Current-generation byte/frame and matchingforeground return'}],
 'baseSha': 'cd5575a32d49dcc4109837fe8a58016889f9f5eb',
 'classification': 'ROM_PROVENANCE_ESTABLISHED_HARDWARE_UNBOUND',
 'classificationQualification': 'Project recorded public-archive acquisition only; prearchive donor, '
                                'extraction and factory originality unknown.',
 'graph': {'actualSiliconConfirmed': False,
           'edges': [{'applicability': 'Recorded project acquisition',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'RecordedArchiveByteBinding',
                      'from': 'studied_rom',
                      'provenance': 'Historical source-bound local audit',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Recorded acquisition and computed source identity; not '
                                                 'donor/extraction custody',
                                      'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb',
                                      'sourceId': 'M1aPublicReport'}],
                      'to': 'acquisition_source',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'studied_rom',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'claimed_ecu_model',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'acquisition_source',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'extraction_custody',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'extraction_custody',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'observed_ecu_label',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'claimed_ecu_model',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'observed_ecu_label',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'observed_ecu_label',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'pcb_revision',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'pcb_revision',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'observed_mcu_marking',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'observed_mcu_marking',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'candidate_mcu',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'observed_mcu_marking',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'candidate_customer_code',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Named standard candidates',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'StandardDeviceOnly',
                      'from': 'candidate_mcu',
                      'provenance': 'Reviewed primary table',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Pages1/2/9/17: named standard parts and memory map',
                                      'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a',
                                      'sourceId': 'JapaneseY3'}],
                      'to': 'manufacturer_document',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Named standard candidates',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'StandardDeviceOnly',
                      'from': 'manufacturer_document',
                      'provenance': 'Reviewed primary table',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Pages1/2/9/17: named standard parts and memory map',
                                      'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a',
                                      'sourceId': 'JapaneseY3'}],
                      'to': 'memory_map',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'pcb_revision',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'board_memory_configuration',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'board_memory_configuration',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'memory_map',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'memory_map',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'peripheral_applicability',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'candidate_customer_code',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'peripheral_applicability',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'observed_mcu_marking',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'actual_hardware_identity',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'extraction_custody',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'actual_hardware_identity',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']},
                     {'applicability': 'Missing same-unit actual hardware relationship',
                      'competingHypotheses': ['Different donor or board revision',
                                              'External memory or modified assembly'],
                      'confidenceRationale': 'High for stated documentary/byte relationship only; no '
                                             'physical inference from this edge.',
                      'evidenceClass': 'UnestablishedPhysicalBridge',
                      'from': 'peripheral_applicability',
                      'provenance': 'Explicit unresolved dependency',
                      'requiredConfirmation': ['Authenticated same-unit records and applicable '
                                               'manufacturer/OEM bridge'],
                      'sameUnitEstablished': False,
                      'sourceRefs': [{'locator': 'Sections What is and is not identified; Native '
                                                 'execution prerequisite graph; Preserved M2cj/M2ck '
                                                 'frontier',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'to': 'actual_hardware_identity',
                      'unresolvedConditions': ['Actual ECU/customer mask/extraction custody unbound']}],
           'executionAdmission': False,
           'nodes': [{'component': 'Studied admitted32768-byte payload',
                      'evidenceClass': 'PrivateLocalAuditDeclared',
                      'nodeId': 'studied_rom',
                      'sourceRefs': [{'locator': 'Recorded acquisition/source identity findings; not '
                                                 'physical donor provenance',
                                      'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb',
                                      'sourceId': 'M1aPublicReport'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': 'Payload32768_ExactFingerprintPrivate'},
                     {'component': 'Recorded project acquisition from pinned public archive',
                      'evidenceClass': 'ProjectAcquisitionOnly',
                      'nodeId': 'acquisition_source',
                      'sourceRefs': [{'locator': 'Recorded acquisition/source identity findings; not '
                                                 'physical donor provenance',
                                      'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb',
                                      'sourceId': 'M1aPublicReport'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': 'RecordedArchiveAcquisition_ByteBlobBound'},
                     {'component': 'Secondary candidate ECU association',
                      'evidenceClass': 'UnlinkedSourceCandidates',
                      'nodeId': 'claimed_ecu_model',
                      'sourceRefs': [{'locator': 'Preamble and251/304 table entries',
                                      'sourceHash': '5eb811d9c7de994886b2a269b9fbf617a11d5b14e8d8237d523b16dd6a5118ad',
                                      'sourceId': 'HALoggedList'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': ['P28-A01', 'P28-A51', 'P28-A02', 'P28-A52']},
                     {'component': 'Same-unit observed case label',
                      'evidenceClass': 'Unknown',
                      'nodeId': 'observed_ecu_label',
                      'sourceRefs': [{'locator': 'Section What is and is not identified; Native '
                                                 'execution prerequisite graph',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': None},
                     {'component': 'Same-unit PCB revision',
                      'evidenceClass': 'Unknown',
                      'nodeId': 'pcb_revision',
                      'sourceRefs': [{'locator': 'Section What is and is not identified; Native '
                                                 'execution prerequisite graph',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': None},
                     {'component': 'Same-unit observed MCU top marking',
                      'evidenceClass': 'Unknown',
                      'nodeId': 'observed_mcu_marking',
                      'sourceRefs': [{'locator': 'Section What is and is not identified; Native '
                                                 'execution prerequisite graph',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': None},
                     {'component': 'Standard MCU candidates, not selected physical part',
                      'evidenceClass': 'StandardCandidates',
                      'nodeId': 'candidate_mcu',
                      'sourceRefs': [{'locator': 'Pages1/2/9/17: named standard parts, code number and '
                                                 'separate memory spaces',
                                      'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a',
                                      'sourceId': 'JapaneseY3'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': ['MSM66201', 'MSM66207', 'MSM66P201', 'MSM66P207']},
                     {'component': 'Unlinked observed/associated code numbers',
                      'evidenceClass': 'CodeNumbers_NotConfirmedMaskRevision',
                      'nodeId': 'candidate_customer_code',
                      'sourceRefs': [{'locator': 'Preamble and251/304 table entries',
                                      'sourceHash': '5eb811d9c7de994886b2a269b9fbf617a11d5b14e8d8237d523b16dd6a5118ad',
                                      'sourceId': 'HALoggedList'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': ['251', '304']},
                     {'component': 'Named standard-device document',
                      'evidenceClass': 'StandardNamedDeviceOnly',
                      'nodeId': 'manufacturer_document',
                      'sourceRefs': [{'locator': 'Pages1/2/9/17: named standard parts, code number and '
                                                 'separate memory spaces',
                                      'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a',
                                      'sourceId': 'JapaneseY3'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': 'J2E1027-27-Y3'},
                     {'component': 'Separate standard candidate memory configurations',
                      'evidenceClass': 'StandardNamedDeviceOnly',
                      'nodeId': 'memory_map',
                      'sourceRefs': [{'locator': 'Pages1/2/9/17: named standard parts, code number and '
                                                 'separate memory spaces',
                                      'sourceHash': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a',
                                      'sourceId': 'JapaneseY3'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': 'Standard201_207_DistinctPROGRAM_DATA'},
                     {'component': 'Physical peripheral applicability',
                      'evidenceClass': 'Unknown',
                      'nodeId': 'peripheral_applicability',
                      'sourceRefs': [{'locator': 'Section What is and is not identified; Native '
                                                 'execution prerequisite graph',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': None},
                     {'component': 'Actual studied ECU/MCU identity',
                      'evidenceClass': 'Unknown',
                      'nodeId': 'actual_hardware_identity',
                      'sourceRefs': [{'locator': 'Section What is and is not identified; Native '
                                                 'execution prerequisite graph',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': None},
                     {'component': 'Original physical extraction to archived payload',
                      'evidenceClass': 'Unknown',
                      'nodeId': 'extraction_custody',
                      'sourceRefs': [{'locator': 'Recorded acquisition/source identity findings; not '
                                                 'physical donor provenance',
                                      'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb',
                                      'sourceId': 'M1aPublicReport'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': None},
                     {'component': 'Actual EA/population/external decode',
                      'evidenceClass': 'Unknown',
                      'nodeId': 'board_memory_configuration',
                      'sourceRefs': [{'locator': 'Section What is and is not identified; Native '
                                                 'execution prerequisite graph',
                                      'sourceHash': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                                      'sourceId': 'M2clPublic'}],
                      'unresolvedConditions': ['Same-unit provenance or actual applicability remains '
                                               'unestablished.'],
                      'value': None}]},
 'hardwareExamples': [{'actualStudiedHardwareObservation': None,
                       'evidenceClass': 'UnlinkedThirdPartyPhotoPixels',
                       'exactPackageCode': None,
                       'externalProgramSelection': None,
                       'factoryUnmodifiedStatus': None,
                       'limitations': ['Downloaded bytes and readable co-located labels only; photograph '
                                       'provenance and donor/extraction custody unproved',
                                       'Distinct image content; original photographer/republishing chain '
                                       'unknown, so not counted as independent manufacturer observations',
                                       'DGTune multiple-example custom/socketed/upgraded ECU product '
                                       'gallery; filename s-l1600 suggests possible republishing, not '
                                       'original-camera provenance',
                                       'External-program socket/chip region visibly populated; '
                                       'unreadable device identity and unknown EA/source selection'],
                       'linkedDumpDigest': None,
                       'observedLabel': '37820-P28-A02',
                       'observedMcuLiteral': 'M66207-304',
                       'observedPcb': '02D011F0-1500 A8Y-E',
                       'originalPhotoDate': None,
                       'packageAppearance': 'ElongatedDIPStyle',
                       'photographer': None,
                       'sameUnitAsStudiedRom': None,
                       'sourceId': 'DGTuneA02Photo',
                       'sourcePage': 'https://dgtune.shop/products/p28-spec-chipped-obd1-ecu-package',
                       'sourceRefs': [{'locator': 'Full photo pixels: connector label, PCB silkscreen '
                                                  'and MCU marking',
                                       'sourceHash': '9377ce0ad3d5960b27822be928a6e0471cc1155eed31cd5c2f7e2354575e5aa2',
                                       'sourceId': 'DGTuneA02Photo'}]},
                      {'actualStudiedHardwareObservation': None,
                       'evidenceClass': 'UnlinkedThirdPartyPhotoPixels',
                       'exactPackageCode': None,
                       'externalProgramSelection': None,
                       'factoryUnmodifiedStatus': None,
                       'limitations': ['Downloaded bytes and readable co-located labels only; photograph '
                                       'provenance and donor/extraction custody unproved',
                                       'Distinct image content; original photographer/republishing chain '
                                       'unknown, so not counted as independent manufacturer observations',
                                       'eBay seller Legendary Auto Performance listing255583922331; '
                                       'multiple quantities sold, so displayed photo not necessarily any '
                                       'specific delivered unit',
                                       'Silkscreen27256 unpopulated outline visible; separate '
                                       'daughterboard elsewhere. Actual internal/external program '
                                       'selection and modifications unknown'],
                       'linkedDumpDigest': None,
                       'observedLabel': '37820-P28-A01',
                       'observedMcuLiteral': 'M66207-251',
                       'observedPcb': '02D01720-1500 A8Y-D',
                       'originalPhotoDate': None,
                       'packageAppearance': 'ElongatedDIPStyle',
                       'photographer': None,
                       'sameUnitAsStudiedRom': None,
                       'sourceId': 'EbayA01Photo',
                       'sourcePage': 'https://www.ebay.com/itm/255583922331',
                       'sourceRefs': [{'locator': 'Full photo pixels: connector label, PCB silkscreen '
                                                  'and MCU marking',
                                       'sourceHash': '9a2db02fbe46f7195e6647f9b2d78648ac21be6d7c40e99bad3980773c5ab866',
                                       'sourceId': 'EbayA01Photo'}]},
                      {'actualStudiedHardwareObservation': None,
                       'evidenceClass': 'InheritedUnlinkedThirdPartyDrawing',
                       'exactPackageCode': None,
                       'externalProgramSelection': None,
                       'factoryUnmodifiedStatus': None,
                       'limitations': ['Optional27256/Demon2 annotations do not establish actual '
                                       'population, EA or dump source.',
                                       'Separate U7ASIC is not a proven custom U1CPU peripheral.'],
                       'linkedDumpDigest': None,
                       'observedLabel': 'DrawingTitle37820-P28-A51_NotCasePhoto',
                       'observedMcuLiteral': 'DrawingMSM66207-251',
                       'observedPcb': 'Drawing02D01720-1500 A8Y-D',
                       'originalPhotoDate': None,
                       'packageAppearance': 'Drawing_NotObservedPackage',
                       'photographer': None,
                       'sameUnitAsStudiedRom': None,
                       'sourceId': 'BomarcSchematic',
                       'sourcePage': 'https://raw.githubusercontent.com/imtheman0313/Honda-Civic-P28-ECU/c5e548d6db09b5d256a6f5a51a9d7bbe029b5a3f/P28_ECU_Civic.pdf',
                       'sourceRefs': [{'locator': 'Sheets3/6/8, acquired and reviewed in M2cl',
                                       'sourceHash': '7d5380ad1341980def330eec6798e98ec0f44268ac44d1c802587da52241a7c5',
                                       'sourceId': 'BomarcSchematic'}]}],
 'milestone': 'M2cm',
 'physicalChecklist': [{'additionalEvidence': 'Same-unit PCB/chip photos and custody record',
                        'id': 'PHYSICAL-1',
                        'material': 'Full existing ECU label photograph and OEM part number',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'Case identification and swapped-case risk',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False},
                       {'additionalEvidence': 'Same-board bottom view and full case linkage',
                        'id': 'PHYSICAL-2',
                        'material': 'Existing PCB top photograph',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'PCB identifier/revision and visible population',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False},
                       {'additionalEvidence': 'Authenticated top view and revision/custody',
                        'id': 'PHYSICAL-3',
                        'material': 'Existing PCB bottom photograph',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'Board continuity, alterations and routing context',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False},
                       {'additionalEvidence': 'Manufacturer/OEM code semantics and same-board linkage',
                        'id': 'PHYSICAL-4',
                        'material': 'Complete existing MCU top-mark photograph',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'Literal part/customer suffix and manufacturer mark',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False},
                       {'additionalEvidence': 'Applicable package/pinout primary source, no electrical '
                                              'intervention',
                        'id': 'PHYSICAL-5',
                        'material': 'MCU package/orientation evidence from existing records',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'Visible pin/package/orientation uncertainty',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False},
                       {'additionalEvidence': 'Existing EA/decode documentation and modification history',
                        'id': 'PHYSICAL-6',
                        'material': 'External memory markings and population records',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'Potential internal/external PROGRAM source and device '
                                          'capacity',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False},
                       {'additionalEvidence': 'Applicable schematic/revision and source-to-function '
                                              'evidence',
                        'id': 'PHYSICAL-7',
                        'material': 'External ASIC identifiers from existing photos',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'Separate ASICs versus unproven CPU peripheral extensions',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False},
                       {'additionalEvidence': 'Private local full hash/blob equality and '
                                              'acquisition-source chain',
                        'id': 'PHYSICAL-8',
                        'material': 'Existing ROM extraction/custody record',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'Original donor to exact admitted bytes',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False},
                       {'additionalEvidence': 'Dated same-unit before/after custody and configuration '
                                              'records',
                        'id': 'PHYSICAL-9',
                        'material': 'Documented hardware modification history',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'Socket/chip/daughterboard and case-swap uncertainty',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False},
                       {'additionalEvidence': 'Exact observed part/revision and documentation '
                                              'applicability bridge',
                        'id': 'PHYSICAL-10',
                        'material': 'Applicable OEM/manufacturer customer-code cross-reference',
                        'physicalInterventionRequested': False,
                        'remainingConditions': 'Current native context, pending/peripheral events and '
                                               'safe frame/return remain separate obligations.',
                        'removesUnknown': 'Suffix meaning, mask/peripheral/reset applicability',
                        'romLinkVerification': 'Verify existing private extraction/custody identity '
                                               'against exact admitted bytes locally; no public payload '
                                               'disclosure.',
                        'sufficientAlone': False}],
 'provenanceChain': {'classificationScope': 'RecordedProjectArchiveAcquisitionAndComputedByteBlobIdentity_HardwareUnbound',
                     'factoryOriginality': 'Unknown',
                     'historicalHttpMetadata': 'RecordedLiteralFields_NoPreservedRawGetTranscriptFound',
                     'initialProfileTiming': 'ProfileAndCatalogueAssociationPredateRecordedAcquisition_NotDonorEvidence',
                     'initialTrust': 'TrustedHashesAndSignaturesEmpty_ExplicitConfirmationRequired',
                     'links': [{'evidenceClass': 'RecordedHistoricalAttachment_OriginUnknown',
                                'from': 'historical-attachment',
                                'qualification': 'Historical attachment assertion precedes archived Git '
                                                 'import; original dumper and donor unknown.',
                                'sameUnitEstablished': False,
                                'sourceRefs': [{'locator': 'Redacted source-qualified archive history '
                                                           'declaration',
                                                'sourceHash': '2cff9cc9391baaaf496fa587e326cb4806f7da775c2b7c1f47671f610655c297',
                                                'sourceId': 'M2cmLocalAuditDeclaration'}],
                                'to': 'archive-import',
                                'unknowns': ['Original donor/extraction custody',
                                             'Factory originality and prearchive alterations']},
                               {'evidenceClass': 'SameBlobArchiveHistory',
                                'from': 'archive-import',
                                'qualification': 'Fresh metadata identifies2024import and2024dedup; '
                                                 'content-address equality is not extraction custody.',
                                'sameUnitEstablished': False,
                                'sourceRefs': [{'locator': 'Redacted source-qualified archive history '
                                                           'declaration',
                                                'sourceHash': '2cff9cc9391baaaf496fa587e326cb4806f7da775c2b7c1f47671f610655c297',
                                                'sourceId': 'M2cmLocalAuditDeclaration'}],
                                'to': 'archive-dedup',
                                'unknowns': ['Original donor/extraction custody',
                                             'Factory originality and prearchive alterations']},
                               {'evidenceClass': 'PinnedArchiveByteIdentity',
                                'from': 'archive-dedup',
                                'qualification': 'Pinned archive transport source retained; '
                                                 'filename/dedup does not prove factory originality or '
                                                 'firmware modification.',
                                'sameUnitEstablished': False,
                                'sourceRefs': [{'locator': 'Redacted source-qualified archive history '
                                                           'declaration',
                                                'sourceHash': '2cff9cc9391baaaf496fa587e326cb4806f7da775c2b7c1f47671f610655c297',
                                                'sourceId': 'M2cmLocalAuditDeclaration'}],
                                'to': 'pinned-archive',
                                'unknowns': ['Original donor/extraction custody',
                                             'Factory originality and prearchive alterations']},
                               {'evidenceClass': 'RecordedProjectAcquisition',
                                'from': 'pinned-archive',
                                'qualification': 'Historical GETtimestamp/status/type are recorded '
                                                 'literals; no independent raw GET transcript preserved '
                                                 'in reviewed compact dossier.',
                                'sameUnitEstablished': False,
                                'sourceRefs': [{'locator': 'Public acquisition/source identity findings; '
                                                           'historical HTTP fields remain recorded, not '
                                                           'raw transcript',
                                                'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb',
                                                'sourceId': 'M1aPublicReport'}],
                                'to': 'project-acquisition',
                                'unknowns': ['Original donor/extraction custody',
                                             'Factory originality and prearchive alterations']},
                               {'evidenceClass': 'ComputedPayloadAndBlobIdentity',
                                'from': 'project-acquisition',
                                'qualification': 'Full32768 bytes and Gitblob identity computed in '
                                                 'historical inspection and retained M1/later bindings; '
                                                 'same physical donor unknown.',
                                'sameUnitEstablished': False,
                                'sourceRefs': [{'locator': 'Public acquisition/source identity findings; '
                                                           'historical HTTP fields remain recorded, not '
                                                           'raw transcript',
                                                'sourceHash': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb',
                                                'sourceId': 'M1aPublicReport'}],
                                'to': 'studied-rom',
                                'unknowns': ['Original donor/extraction custody',
                                             'Factory originality and prearchive alterations']}],
                     'prearchiveDonorCategory': 'E_Unknown',
                     'privateAcquisitionRecordsPublished': False,
                     'privateSourceVerification': 'SeparateLocalAudit_NotPerformedByPublicStaticCI',
                     'projectAcquisitionCategory': 'B_PublicFirmwareArchive',
                     'romBytes': 32768,
                     'sameUnitIdentityEstablished': False,
                     'transportChecks': 'ComputedFullPayloadShaAndGitBlobMatch_NoRomBytesRepublished'},
 'schemaVersion': 1,
 'sourceInventory': [{'bytes': 602102,
                      'independenceGroup': 'JapaneseY3',
                      'scope': 'InheritedSourceQualifiedDocument_NotActualHardware',
                      'sha256': '9da5f4c364fb8aed21c783bc5ad7b1e114c4b8773c7a00b9a7373c261112bf7a',
                      'sourceId': 'JapaneseY3',
                      'sourceKind': 'InheritedDocumentBytes',
                      'url': 'https://datasheet.datasheetarchive.com/originals/library/Datasheets-DAV1/DSADA0015905.pdf'},
                     {'bytes': 583437,
                      'independenceGroup': 'EnglishY4',
                      'scope': 'InheritedSourceQualifiedDocument_NotActualHardware',
                      'sha256': 'fe18068dc496a03f5b6bdefe5818741e572cb7626acfb3d1df427547f8b3264b',
                      'sourceId': 'EnglishY4',
                      'sourceKind': 'InheritedDocumentBytes',
                      'url': 'https://downloads.laboratoryb.org/insight/documents/OKI/MSM66201.pdf'},
                     {'bytes': 4563117,
                      'independenceGroup': 'ISA1991',
                      'scope': 'InheritedSourceQualifiedDocument_NotActualHardware',
                      'sha256': 'f6e423ac0bd15378754e30c35ed426415ec219e360c68e817ab451df72142271',
                      'sourceId': 'ISA1991',
                      'sourceKind': 'InheritedDocumentBytes',
                      'url': 'https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/Oki_66201_Instruction_Manual.pdf'},
                     {'bytes': 16203609,
                      'independenceGroup': 'UserIncomplete',
                      'scope': 'InheritedSourceQualifiedDocument_NotActualHardware',
                      'sha256': 'f061cb5bcbd1804699fb60b543c425646fbb15b939c9bc51b24edbb4da4c6ddf',
                      'sourceId': 'UserIncomplete',
                      'sourceKind': 'InheritedDocumentBytes',
                      'url': 'https://mycomputerninja.com/~jon/www.pgmfi.org/twiki/pub/Library/66kAssemblerDocs/66207usersmanual_incomplete.zip'},
                     {'bytes': 104246,
                      'independenceGroup': 'ArchiveCatalogue',
                      'scope': 'InheritedSourceQualifiedDocument_NotActualHardware',
                      'sha256': '3e2a71a91e3ca05d9bda349b5e4caba0b66a68f6a986c4859e9129a6ab7e473b',
                      'sourceId': 'ArchiveCatalogue',
                      'sourceKind': 'InheritedDocumentBytes',
                      'url': 'https://raw.githubusercontent.com/hondabase/files-archive/06d2eb0d9b37c6b1bd001254203790751457b4a7/pgmfiorg/twiki/bin/view/Library/EcuDefinitionCodes.html'},
                     {'bytes': 9147356,
                      'independenceGroup': 'BomarcSchematic',
                      'scope': 'InheritedSourceQualifiedDocument_NotActualHardware',
                      'sha256': '7d5380ad1341980def330eec6798e98ec0f44268ac44d1c802587da52241a7c5',
                      'sourceId': 'BomarcSchematic',
                      'sourceKind': 'InheritedDocumentBytes',
                      'url': 'https://raw.githubusercontent.com/imtheman0313/Honda-Civic-P28-ECU/c5e548d6db09b5d256a6f5a51a9d7bbe029b5a3f/P28_ECU_Civic.pdf'},
                     {'bytes': 14301,
                      'independenceGroup': 'M1aPublicReport',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': '267f067e2d59b60cb93abf4a4cbfa40d3778da9660fe7c8b2bc60ab95b69f8cb',
                      'sourceId': 'M1aPublicReport',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/docs/M1A_REAL_ROM_FINDINGS.md'},
                     {'bytes': 13085,
                      'independenceGroup': 'M1fPublicReport',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': 'a33caeabd184544b74686110da3a935a91d2dda72e97e60d8f8989c4fbfb5639',
                      'sourceId': 'M1fPublicReport',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/docs/M1F_NATIVE_CHECKSUM_VALIDATION.md'},
                     {'bytes': 22717,
                      'independenceGroup': 'M2clPublic',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': 'd76aff13eebbda3a6a5b482897fe7093dedd9f0786572f903438719d1c317b94',
                      'sourceId': 'M2clPublic',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/docs/M2CL_ACTUAL_ECU_SILICON_APPLICABILITY.md'},
                     {'bytes': 11578,
                      'independenceGroup': 'M2avDoc',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': '438714674f4dbffbc1fa73f3b0b6e67524834d405371f51592e4c1f8833700e0',
                      'sourceId': 'M2avDoc',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/docs/M2AV_WORD0196_STRUCTURED_C_EQUIVALENCE.md'},
                     {'bytes': 32188,
                      'independenceGroup': 'M2avIR',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': '4fdbd6b7dbdd8f48d5a43e123ca93a33a003c22556a0c40b5296d5f409e085c4',
                      'sourceId': 'M2avIR',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/research/p28-word0196/word0196_ir.json'},
                     {'bytes': 8507,
                      'independenceGroup': 'M2avC11',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': '4b189d4ed3e97e0d197f6c558755cf056a89c1dc7122653c5c557e7ab62d76d3',
                      'sourceId': 'M2avC11',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/research/p28-word0196/word0196_equivalent.c'},
                     {'bytes': 14586,
                      'independenceGroup': 'M2bdDoc',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': 'ba74df64fbb201d2aa6e5577b15262bd1927639c55bbd06effac298bb307d52f',
                      'sourceId': 'M2bdDoc',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/docs/M2BD_WORD0196_TYPED_LOWERING_OBLIGATIONS.md'},
                     {'bytes': 13323,
                      'independenceGroup': 'M2cjDoc',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': '4db3384f9be12ede559720262a19376f48dcf3a877bb4841f47ec8bbadd2bf60',
                      'sourceId': 'M2cjDoc',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/docs/M2CJ_RXREADY_IRQ000A_SINGLE_INVOCATION.md'},
                     {'bytes': 18884,
                      'independenceGroup': 'M2ckDoc',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': '4209f3abc3676aa3eb89bc9e5182aa2049210b322b7598166981e9559592eb5e',
                      'sourceId': 'M2ckDoc',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/docs/M2CK_RXREADY_ACKNOWLEDGEMENT_REASSERTION.md'},
                     {'bytes': 10044,
                      'independenceGroup': 'M2amDoc',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': 'ee5359ff1573e28e7ef2f07151a537ec25332208c85ebdc5eb9ce460c06ad773',
                      'sourceId': 'M2amDoc',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/docs/M2AM_C8_EQUALITY_EVIDENCE.md'},
                     {'bytes': 18935,
                      'independenceGroup': 'M2awDoc',
                      'scope': 'InheritedSourceQualifiedResearch_NotNewRuntimeOrManufacturerObservation',
                      'sha256': '122bbb14adcd5718dc3fbb3fefb19dee74a9228099278802254ef6c7d59f8174',
                      'sourceId': 'M2awDoc',
                      'sourceKind': 'FrozenPublicProjectResearch',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/cd5575a32d49dcc4109837fe8a58016889f9f5eb/docs/M2AW_NX8_200_TARGET_ABI_CONTRACT.md'},
                     {'bytes': 303012,
                      'independenceGroup': 'HAshop',
                      'scope': 'UnlinkedPublicSubject_NotStudiedDonor_NotManufacturerMaskAuthority',
                      'sha256': '5eb811d9c7de994886b2a269b9fbf617a11d5b14e8d8237d523b16dd6a5118ad',
                      'sourceId': 'HALoggedList',
                      'sourceKind': 'PublicWebDocumentBytes',
                      'url': 'https://www.hamotorsports.com/pages/obd1-ecu-rom-number-to-ecu-part-number-master-list'},
                     {'bytes': 301916,
                      'independenceGroup': 'HAshop',
                      'scope': 'UnlinkedPublicSubject_NotStudiedDonor_NotManufacturerMaskAuthority',
                      'sha256': 'cedea74376f61484db0ddc8729586b6d9b7b5eda2b6c53815355595c7eb0e34f',
                      'sourceId': 'HaEquivalent',
                      'sourceKind': 'PublicWebDocumentBytes',
                      'url': 'https://www.hamotorsports.com/pages/what-is-a-p28-equivalent-ecu'},
                     {'bytes': 249719,
                      'independenceGroup': 'PartsNowCatalogue',
                      'scope': 'UnlinkedPublicSubject_NotStudiedDonor_NotManufacturerMaskAuthority',
                      'sha256': '7de138f55a44f805f5bf6ba425b0e0dc6e101065e5f07254fab872e5151abf08',
                      'sourceId': 'PartsNowCatalogue',
                      'sourceKind': 'PublicWebDocumentBytes',
                      'url': 'https://www.hondapartsnow.com/oem-1993-honda-civic-engine_control_module.html'},
                     {'bytes': 249065,
                      'independenceGroup': 'DgProductPage',
                      'scope': 'UnlinkedPublicSubject_NotStudiedDonor_NotManufacturerMaskAuthority',
                      'sha256': '9134a4c04671009f632db0289a868e0b5c07a15c7bbce6385b8ffbe6355d7b2c',
                      'sourceId': 'DgProductPage',
                      'sourceKind': 'PublicWebDocumentBytes',
                      'url': 'https://dgtune.shop/products/p28-spec-chipped-obd1-ecu-package'},
                     {'bytes': 478782,
                      'independenceGroup': 'DGTuneA02Photo',
                      'scope': 'UnlinkedPublicSubject_NotStudiedDonor_NotManufacturerMaskAuthority',
                      'sha256': '9377ce0ad3d5960b27822be928a6e0471cc1155eed31cd5c2f7e2354575e5aa2',
                      'sourceId': 'DGTuneA02Photo',
                      'sourceKind': 'UnlinkedCommercialPhotoBytes',
                      'url': 'https://dgtune.shop/cdn/shop/files/s-l1600.jpg?v=1683810058&width=1946'},
                     {'bytes': 400206,
                      'independenceGroup': 'EbayA01Photo',
                      'scope': 'UnlinkedPublicSubject_NotStudiedDonor_NotManufacturerMaskAuthority',
                      'sha256': '9a2db02fbe46f7195e6647f9b2d78648ac21be6d7c40e99bad3980773c5ab866',
                      'sourceId': 'EbayA01Photo',
                      'sourceKind': 'UnlinkedCommercialPhotoBytes',
                      'url': 'https://i.ebayimg.com/images/g/VDAAAOSwGaNkwRt3/s-l1200.jpg'},
                     {'bytes': 1276,
                      'independenceGroup': 'M2cmLocalAudit',
                      'scope': 'SourceQualifiedLocalAuditSummary_PrivateRawBindingsNotReverifiedByPublicCI',
                      'sha256': '2cff9cc9391baaaf496fa587e326cb4806f7da775c2b7c1f47671f610655c297',
                      'sourceId': 'M2cmLocalAuditDeclaration',
                      'sourceKind': 'PublicRedactedLocalAuditDeclaration_NotIndependentAcquisitionTranscript',
                      'url': 'https://github.com/Pvitaly91/HondaEcu/blob/codex/p28-word0196-ecu-rom-provenance-m2cm/research/p28-word0196/ecu_rom_provenance/acquisition_audit.json'}]}


def expected_compatibility(ecu, mcu, configuration):
    capacities = {
        "MSM66201": (16384, 512, False),
        "MSM66207": (32768, 1024, False),
        "MSM66P201": (16384, 512, True),
        "MSM66P207": (32768, 1024, True),
    }
    program, ram, otp = capacities[mcu]
    if configuration == "Unknown":
        status = "Unknown"
        basis = "ActualProgramSelectionAndBoardDecodeUnknown"
    elif configuration == "InternalOnly32K" and program < 32768:
        status = "ConflictsWithStatedStandardPremise"
        basis = "32KiBInternalOnlyPremiseExceedsStandard16KiBCapacity"
    elif configuration == "ExternalProgramSupported":
        status = "ConditionallyCompatible"
        basis = "StandardExternalProgramExists_BoardSelectionUnestablished"
    else:
        status = "ConditionallyCompatible"
        basis = "Standard32KiBCapacityFits_NoActualProgramSelectionProof"
    return {
        "ecuCandidate": ecu, "mcuCandidate": mcu,
        "memoryConfiguration": configuration, "status": status, "basis": basis,
        "studiedPayloadBytes": 32768, "standardInternalProgramBytes": program,
        "standardTotalInternalDataBytes": ram, "externalProgramDocumented": True,
        "otpQualification": "PairedNominalCounterpart_NotProgrammingModeProof" if otp else "NotOtpCandidate",
        "actualEcuRuledOut": False, "physicalUnitBound": False,
        "actualSiliconConfirmed": False, "peripheralApplicability": "Unestablished",
        "executionAdmission": False, "firmwareReady": False,
    }


def expected_claim_comparison(left, right):
    equal_subject = left["subject"] == right["subject"]
    equal_property = left["property"] == right["property"]
    equal_value = left["value"] == right["value"]
    same_group = left["independenceGroup"] == right["independenceGroup"]
    owned_unit = left["unitScope"] is not None and left["unitScope"] == right["unitScope"]
    if not (equal_subject and equal_property):
        relation = "DifferentSubjectsOrProperties"
    elif equal_value:
        relation = "SameValue_NotIndependentIdentityProof"
    elif owned_unit and left["exclusive"] and right["exclusive"] and not same_group:
        relation = "ExclusiveSameUnitConflict_UnderDeclaredPremises"
    elif same_group:
        relation = "DependentSourceDifference_NotIndependentConfirmation"
    else:
        relation = "NonExclusiveAttributionDifference"
    return {"relation": relation, "authenticityEstablishedByComparison": False,
            "studiedUnitIdentityEstablished": False, "executionAdmission": False}


def expected_records():
    d = deepcopy(EXPECTED_DOCUMENTARY)
    relations = []
    fields = ("subject", "property", "value", "unitScope", "exclusive", "independenceGroup")
    for pair in d["attributionPairs"]:
        left = {k:pair["left"][k] for k in fields}
        right = {k:pair["right"][k] for k in fields}
        relations.append({"left": pair["left"], "right": pair["right"],
                          "result": expected_claim_comparison(left, right)})
    compatibility = []
    for ecu in ("P28-A01", "P28-A51", "P28-A02", "P28-A52", "Unknown"):
        for mcu in ("MSM66201", "MSM66207", "MSM66P201", "MSM66P207"):
            for config in ("InternalOnly32K", "ExternalProgramSupported", "Unknown"):
                compatibility.append(expected_compatibility(ecu, mcu, config))
    payloads = (
        ("source-inventory", d["sourceInventory"]),
        ("provenance-chain", d["provenanceChain"]),
        ("hardware-examples", d["hardwareExamples"]),
        ("attribution-relations", relations),
        ("compatibility-matrix", compatibility),
        ("same-unit-graph", d["graph"]),
        ("static-reconstruction-backlog", d["backlog"]),
        ("physical-checklist", d["physicalChecklist"]),
        ("authority", d["authority"]),
    )
    return [{"recordId": name,
             "recordClass": "DocumentaryProvenance_NotActualHardwareObservation",
             "payload": payload, "actualHardwareObservation": None,
             "executionBlocked": True, "firmwareReady": False}
            for name, payload in payloads]


def canonical_bytes(records=None):
    rows = expected_records() if records is None else records
    return b"".join((json.dumps(row, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=True, allow_nan=False) + "\n").encode()
                    for row in rows)
