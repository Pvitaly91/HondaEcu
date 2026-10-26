"""Explicit source-frozen CAL/body/RT verification; no automatic build or ROM search."""
import os
from pathlib import Path
from original_rom_execution.verify import (local_directory,preservation_exception_context,
    require,read_json,source_joins_equal)
ROOT=Path(__file__).resolve().parents[3]


def verify_execution(*,output,runner,public=False,rom=None,profile=None,checkpoint_path=None):
    from . import admission,corpus,oracle,source_guard
    from .contract_validation import validate_contract
    from .resume import VerificationRun,verify_ack,BASE
    require(type(public) is bool and ((public and rom is None and profile is None)
            or (not public and rom is not None and profile is not None)),'SeparatePrivateOriginalAndPublicInventedInputsRequired')
    if checkpoint_path is not None:
        checkpoint_path=local_directory(checkpoint_path)
        require(checkpoint_path==ROOT/'private/reports/m2by/RESUME_STATE.json','OnlyCurrentLocalM2byCheckpointPermitted')
    output=local_directory(output); admission.validate_output_directory(output,rom)
    supplier=lambda:source_guard.working_source_join(allow_saved_physical=os.environ.get('GITHUB_ACTIONS')!='true')
    current=supplier()
    require(current.get('milestone')=='M2by' and current.get('exactBase')==BASE,'SeparateCurrentM2bySourceJoinRequired')
    saved=read_json(output/'sourcejoin.json') if (output/'sourcejoin.json').exists() else None
    if saved is not None: source_joins_equal(saved,current)
    join=saved or current
    require(validate_contract(source_bindings=current['sourceBindings'])['passed'] is True,'IndependentM2byContractRequired')
    cases=list(corpus.iter_cases()); preservation=private_identity=None
    require(len(cases)==16,'ExactSixteenCalRtCasesRequired')
    if public:
        program={'kind':'public_fixture','schemaVersion':1}; identity=oracle.public_program_identity(); fence=lambda:True
    else:
        preservation=preservation_exception_context(ROOT/'private/reports/m2bt/RESUME_STATE.json')
        admitted=admission.AdmittedCalRtOriginal(rom,profile,output)
        program,identity,private_identity=admitted.program_request(),admitted.program_identity(),admitted.private_identity()
        def fence():
            admitted.assert_unchanged()
            require(preservation_exception_context(ROOT/'private/reports/m2bt/RESUME_STATE.json')==preservation,
                    'InheritedHistoricalExceptionChangedDuringM2by')
            return True
        if checkpoint_path is None: checkpoint_path=ROOT/'private/reports/m2by/RESUME_STATE.json'
    kind='public_fixture' if public else 'private'
    expected=[oracle.expected_case(case,kind) for case in cases]
    wires=[corpus.wire_case(case,kind) for case in cases]
    def compare(case,actual,*,program_identity):
        return oracle.compare_observation(case,actual,kind,program_identity)
    return VerificationRun(output=output,runner=runner,source_join=join,source_supplier=supplier,cases=cases,
        wire_cases=wires,expected=expected,program=program,program_identity=identity,compare=compare,public=public,
        source_fence=fence,private_identity=private_identity,checkpoint_path=checkpoint_path,
        preservation_binding=preservation,ack_validator=verify_ack,corpus_kind='positive').run()
