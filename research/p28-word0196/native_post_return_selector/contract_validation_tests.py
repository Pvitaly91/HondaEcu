"""Closed source/CFG/selector/context relations; no runtime observations."""
import unittest
from . import contract_validation as c
class ContractTests(unittest.TestCase):
    def test_closed_independent_contract_and_zero_execution_authority(self):
        r=c.validate_contract();self.assertTrue(r['passed']);self.assertEqual(r['actualCpuExecutions'],0)
    def test_meaningful_source_budget_selector_flags_generation_and_authority_mutations_refused(self):
        paths=[('program','stopBeforePc'),('program','selectedInstructionSites'),('program','branch064CDecodeOrExecutionAllowed'),
          ('entry','logicalSetupWrites'),('entry','rawSetupWrites'),('entry','perEventSelectorOrExpectedResultAllowed'),
          ('path','totalRetirements'),('path','rtRetirement'),('path','selectorWriterRetirement'),
          ('calRt','logicalFrameWriteOrdinal'),('calRt','sspRestoredBeforePostReturn'),('calRt','historicalFrameImportAllowed'),
          ('selector','writerPc'),('selector','nativeWriteOrdinal'),('selector','logicalWriteOrdinal'),('selector','rawWriteOrdinal'),
          ('selector','nextEventExecutionAllowed'),('history0128','zeroFlag'),('history0128','neighborAndBit2PreservationRequired'),
          ('localR0','hcAfterStrictIncrement'),('localR0','finalR0'),('authority','nativeNextEventSelectorHandoffVerified'),('authority','firmwareReady')]
        for path in paths:
            v=c.facts();n=v
            for key in path[:-1]:n=n[key]
            old=n[path[-1]];n[path[-1]]=not old if type(old) is bool else old+1 if type(old) is int else 'Altered'
            with self.subTest(path=path),self.assertRaises(ValueError):c.validate_contract(v)
