"""Small M2bu source/corpus adapter over the separate bounded resume controller."""
from pathlib import Path
import os

from original_rom_execution.verify import (file_binding, local_directory, preservation_exception_context,
                                           require, read_json, source_joins_equal)
from native_entry_continuity import source_guard

ROOT = Path(__file__).resolve().parents[3]


def verify_ack(ack, identity, public):
    fields = {'kind', 'schemaVersion', 'classification', 'program_sha256', 'entry_pc',
              'program_node_count', 'native_generation_ownership', 'physical_sf_known', 'hardware_validated'}
    require(type(ack) is dict and set(ack) == fields, 'ClosedM2buAdmissionRecordRequired')
    require(ack['kind'] == 'program_admitted' and type(ack['schemaVersion']) is int
            and ack['schemaVersion'] == 1 and type(ack['program_node_count']) is int
            and ack['program_node_count'] == 24, 'Closed24NodeM2buAdmissionRequired')
    classification = ('ExplicitInventedPublicEntryFixture' if public else
                      'OriginalRomBytes_TechnicalCallerToExitExecution')
    require(ack['classification'] == classification and ack['program_sha256'] == identity['program_sha256']
            and ack['entry_pc'] == identity['program_base'], 'ExactM2buProgramIdentityRequired')
    require(all(ack[name] is False for name in ('native_generation_ownership', 'physical_sf_known', 'hardware_validated')),
            'TechnicalEntryCannotPromotePhysicalOrNativeOwnership')


def verify_execution(*, output, runner, public=False, rom=None, profile=None,
                     branch_controls=False, checkpoint_path=None):
    from native_entry_continuity import admission, corpus, oracle
    from native_entry_continuity.contract_validation import validate_contract
    from native_entry_continuity.resume import VerificationRun
    require(type(public) is bool and type(branch_controls) is bool
            and ((public and rom is None and profile is None)
                 or (not public and rom is not None and profile is not None)),
            'SeparatePrivateOriginalAndPublicInventedInputsRequired')
    if checkpoint_path is not None:
        checkpoint_path = local_directory(checkpoint_path)
        require(checkpoint_path == ROOT / 'private/reports/m2bu/RESUME_STATE.json',
                'OnlyCurrentLocalM2buGlobalCheckpointPermitted')
    output = local_directory(output)
    admission.validate_output_directory(output, rom)
    supplier = lambda: source_guard.working_source_join(allow_saved_physical=os.environ.get('GITHUB_ACTIONS') != 'true')
    current = supplier()
    supplied = read_json(output / 'sourcejoin.json') if (output / 'sourcejoin.json').exists() else None
    if supplied is not None:
        source_joins_equal(supplied, current)
    join = supplied or current
    protocol = validate_contract(source_bindings=current['sourceBindings'])
    require(protocol.get('passed') is True, 'IndependentM2buContractRequired')
    cases = list(corpus.iter_branch_controls() if branch_controls else corpus.iter_cases())
    require(len(cases) == (2 if branch_controls else 32), 'ClosedM2buCaseInventoryRequired')
    preservation = private_identity = None
    if public:
        program = {'kind': 'public_fixture', 'schemaVersion': 1}
        identity = oracle.public_program_identity()
        fence = lambda: True
    else:
        preservation = preservation_exception_context(ROOT / 'private/reports/m2bt/RESUME_STATE.json')
        admitted = admission.AdmittedEntryOriginal(rom, profile, output)
        program, identity, private_identity = admitted.program_request(), admitted.program_identity(), admitted.private_identity()
        def fence():
            admitted.assert_unchanged()
            require(preservation_exception_context(ROOT / 'private/reports/m2bt/RESUME_STATE.json') == preservation,
                    'InheritedExceptionEvidenceChangedDuringM2bu')
            return True
        if checkpoint_path is None:
            checkpoint_path = ROOT / 'private/reports/m2bu/RESUME_STATE.json'
    kind = 'public_fixture' if public else 'private'
    # These complete independent expectations are formed before the controller
    # publishes its immutable freeze and before any runner process is started.
    expected = [oracle.expected_case(case, program_kind=kind) for case in cases]
    wires = [corpus.wire_case(case, program_kind=kind) for case in cases]
    def compare(case, actual, *, program_identity):
        return oracle.compare_observation(case, actual, program_kind=kind, program_identity=program_identity)
    return VerificationRun(output=output, runner=runner, source_join=join, source_supplier=supplier,
                           cases=cases, wire_cases=wires, expected=expected, program=program,
                           program_identity=identity, compare=compare, public=public,
                           source_fence=fence, private_identity=private_identity,
                           checkpoint_path=checkpoint_path, preservation_binding=preservation,
                           ack_validator=verify_ack,
                           corpus_kind='branch_controls' if branch_controls else 'positive').run()
