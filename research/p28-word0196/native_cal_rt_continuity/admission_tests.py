"""Private output fences and two invented windows; no ROM execution."""
from pathlib import Path
import tempfile
import unittest
from .admission import validate_output_directory
from . import oracle
class AdmissionTests(unittest.TestCase):
    def test_output_cannot_alias_original_or_containing_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();source=root/'canonical.jsonl.gz';source.write_bytes(b'InventedOnly_NotRom')
            for output in (source,root):
                with self.assertRaises(ValueError):validate_output_directory(output,source)
            validate_output_directory(root/'owned-output',source)
            self.assertEqual(source.read_bytes(),b'InventedOnly_NotRom')
    def test_public_closed_two_windows_exclude_return(self):
        i=oracle.public_program_identity();w=i['program_windows']
        self.assertIsNone(i['source_binding']);self.assertEqual([x['byte_count'] for x in w],[3,404])
        self.assertEqual([x['role'] for x in w],['CallerCAL','CalleeBodyAndRT'])
        self.assertLess(w[0]['end_exclusive'],w[1]['base']);self.assertNotIn(str(0x2003),i['selected_extent_sha256'])
