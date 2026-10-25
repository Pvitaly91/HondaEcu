"""M2bw source/corpus adapter; actual execution is explicit and source-frozen."""
import os
from pathlib import Path

from original_rom_execution.verify import (file_binding, local_directory, preservation_exception_context,
                                           require, read_json, source_joins_equal)

ROOT = Path(__file__).resolve().parents[3]


def verify_ack(ack, identity, public):
    fields = {'kind', 'schemaVersion', 'classification', 'program_sha256', 'entry_pc',
              'program_node_count', 'native_generation_ownership', 'physical_sf_known', 'hardware_validated'}
    require(type(ack) is dict and set(ack) == fields and type(public) is bool, 'ClosedM2bwAdmissionRecordRequired')
    require(ack['kind'] == 'program_admitted' and type(ack['schemaVersion']) is int and ack['schemaVersion'] == 1
            and type(ack['program_node_count']) is int and ack['program_node_count'] == 31,
            'ClosedThirtyOneNodeP2HandoffAdmissionRequired')
    classification = 'ExplicitInventedPublicPostP2ControlFixture' if public else 'OriginalRomBytes_TechnicalPostP2ControlExecution'
    require(ack['classification'] == classification and ack['program_sha256'] == identity['program_sha256']
            and type(ack['entry_pc']) is int and ack['entry_pc'] == identity['program_base'], 'ExactM2bwProgramIdentityRequired')
    require(all(ack[name] is False for name in ('native_generation_ownership', 'physical_sf_known', 'hardware_validated')),
            'TechnicalP2HandoffCannotPromoteNativeOrPhysicalOwnership')


def verify_execution(*, output, runner, public=False, rom=None, profile=None, checkpoint_path=None):
    from . import admission, corpus, oracle, source_guard
    from .contract_validation import validate_contract
    from .resume import VerificationRun
    require(type(public) is bool and ((public and rom is None and profile is None)
            or (not public and rom is not None and profile is not None)), 'SeparatePrivateOriginalAndPublicInventedInputsRequired')
    if checkpoint_path is not None:
        checkpoint_path = local_directory(checkpoint_path)
        require(checkpoint_path == ROOT / 'private/reports/m2bw/RESUME_STATE.json', 'OnlyCurrentLocalM2bwGlobalCheckpointPermitted')
    output = local_directory(output)
    admission.validate_output_directory(output, rom)
    supplier = lambda: source_guard.working_source_join(allow_saved_physical=os.environ.get('GITHUB_ACTIONS') != 'true')
    current = supplier()
    require(current.get('milestone') == 'M2bw' and current.get('exactBase') == 'b67ea436870fe591f6ae4daca307341806d6f8eb',
            'SeparateCurrentM2bwSourceJoinRequired')
    saved = read_json(output / 'sourcejoin.json') if (output / 'sourcejoin.json').exists() else None
    if saved is not None:
        source_joins_equal(saved, current)
    join = saved or current
    require(validate_contract(source_bindings=current['sourceBindings'])['passed'] is True, 'IndependentM2bwContractRequired')
    cases = list(corpus.iter_cases())
    require(len(cases) == 32, 'ClosedThirtyTwoPositiveP2HandoffCasesRequired')
    preservation = private_identity = None
    if public:
        program = {'kind': 'public_fixture', 'schemaVersion': 1}
        identity, fence = oracle.public_program_identity(), lambda: True
    else:
        preservation = preservation_exception_context(ROOT / 'private/reports/m2bt/RESUME_STATE.json')
        admitted = admission.AdmittedPostP2Original(rom, profile, output)
        program, identity, private_identity = admitted.program_request(), admitted.program_identity(), admitted.private_identity()
        def fence():
            admitted.assert_unchanged()
            require(preservation_exception_context(ROOT / 'private/reports/m2bt/RESUME_STATE.json') == preservation,
                    'InheritedHistoricalExceptionChangedDuringM2bw')
            return True
        if checkpoint_path is None:
            checkpoint_path = ROOT / 'private/reports/m2bw/RESUME_STATE.json'
    kind = 'public_fixture' if public else 'private'
    # All expected state is formed before any process starts. Actual Rust AL,
    # latch or flags never feed back into this independently owned oracle.
    expected = [oracle.expected_case(case, kind) for case in cases]
    wires = [corpus.wire_case(case, kind) for case in cases]
    def compare(case, actual, *, program_identity):
        return oracle.compare_observation(case, actual, kind, program_identity)
    return VerificationRun(output=output, runner=runner, source_join=join, source_supplier=supplier,
        cases=cases, wire_cases=wires, expected=expected, program=program, program_identity=identity,
        compare=compare, public=public, source_fence=fence, private_identity=private_identity,
        checkpoint_path=checkpoint_path, preservation_binding=preservation, ack_validator=verify_ack,
        corpus_kind='positive').run()
