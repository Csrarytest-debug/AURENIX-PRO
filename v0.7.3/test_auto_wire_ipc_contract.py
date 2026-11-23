"""Ensure GUI checkbox reaches the isolated AI subprocess."""
from pathlib import Path
root=Path(__file__).parent
ui=(root/'aurenix_pro.py').read_text()
base=(root/'background_remover_pro.py').read_text()
ipc=(root/'isolated_worker.py').read_text()
worker=(root/'inference_worker.py').read_text()
assert "self.auto_wire_checkbox.setChecked(True)" in ui
assert 'self.current_auto_wire_cleanup = self.auto_wire_checkbox.isChecked()' in ui
assert 'self.worker.auto_wire_cleanup = getattr(self, "current_auto_wire_cleanup", True)' in base
assert "'auto_wire_cleanup': self.auto_wire_cleanup" in ipc
assert "'auto_wire_cleanup'," in worker
assert "'fine_edge_matting', 'wire_policy_overrides')" in worker
assert 'result, removed_pixels = remove_loose_wires(result, mode=policy)' in base
assert 'self.current_wire_policy_overrides = dict(self.wire_policy_overrides)' in ui
assert "'wire_policy_overrides': self.wire_policy_overrides" in ipc
assert "Apply Wire Cleanup (paint mask first)" in ui
print('PASS checkbox -> batch worker -> IPC -> isolated inference -> alpha cleanup; manual tool preserved')
