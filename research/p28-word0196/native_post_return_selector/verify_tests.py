"""Input-mode/checkpoint refusals precede all source or CPU work."""
from pathlib import Path
import tempfile
import unittest
from .verify import verify_execution
from .resume import verify_ack
from . import oracle
class VerifyTests(unittest.TestCase):
    def test_private_public_inputs_cannot_be_blended_or_omitted(self):
        with tempfile.TemporaryDirectory() as root:
            for x in ({},{'public':True,'rom':'invented'},{'public':True,'profile':'invented'},{'public':False,'rom':'invented'}):
                with self.subTest(x=x),self.assertRaises(ValueError):verify_execution(output=root,runner='not-invoked',**x)
    def test_historical_checkpoint_cannot_be_rebound(self):
        with tempfile.TemporaryDirectory() as root,self.assertRaises(ValueError):
            verify_execution(output=root,runner='not-invoked',public=True,checkpoint_path=Path(root)/'historical.json')
    def test_ack_binds_two_windows_and_no_native_authority(self):
        i=oracle.public_program_identity()
        a={'kind':'program_admitted','schemaVersion':1,'classification':'ExplicitInventedPublicPostReturnSelectorFixture',
            'program_sha256':i['program_sha256'],'entry_pc':0x2000,'body_pc':0x6400,'return_pc':0x2003,'stop_before_pc':0x2011,'selector_address':0x0140,
            'program_node_count':59,'program_windows':i['program_windows'],'native_generation_ownership':False,
            'physical_sf_known':False,'hardware_validated':False}
        verify_ack(a,i,True)
        for k,v in (('entry_pc',0x6400),('return_pc',0x2004),('program_node_count',49),('program_sha256','0'*64),
                    ('native_generation_ownership',True),('physical_sf_known',True)):
            with self.subTest(k=k),self.assertRaises(ValueError):verify_ack({**a,k:v},i,True)
