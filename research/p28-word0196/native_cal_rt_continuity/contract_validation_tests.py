"""Closed metadata and semantic contract mutations, not execution observations."""
from copy import deepcopy
import unittest
from . import contract_validation as c
class ContractTests(unittest.TestCase):
    def test_closed_static_contract(self):
        value=c.validate_contract();self.assertTrue(value['passed']);self.assertEqual(value['actualCpuExecutions'],0)
    def test_meaningful_relation_mutations_refused(self):
        paths=[('program','entryPc'),('program','stopBeforePc'),('program','postReturnDecodeOrExecutionAllowed'),
            ('entry','logicalSetupWrites'),('entry','rawSetupWrites'),('entry','readyFrameImported'),
            ('cal','returnPc'),('cal','sspAfter'),('frame','freshActualCalWriterRequired'),('frame','logicalWriteOrdinal'),
            ('frame','sameValueWriteIsFreshGeneration'),('rt','sspBeforeRead'),('rt','mustConsumeFreshCalGeneration'),
            ('path','totalRetirements'),('path','postReturn'),('partial','positiveCompleted'),
            ('authority','enclosingIrqFrameEstablished'),('authority','firmwareReady')]
        for path in paths:
            value=c.facts();node=value
            for key in path[:-1]:node=node[key]
            old=node[path[-1]];node[path[-1]]=not old if type(old) is bool else old+1 if type(old) is int else 'Altered'
            with self.subTest(path=path),self.assertRaises(ValueError):c.validate_contract(value)
