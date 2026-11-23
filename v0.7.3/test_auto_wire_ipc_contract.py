"""Ensure all four per-image cable settings reach the isolated AI subprocess."""
from pathlib import Path
root=Path(__file__).parent
ui=(root/'aurenix_pro.py').read_text()
base=(root/'background_remover_pro.py').read_text()
ipc=(root/'isolated_worker.py').read_text()
worker=(root/'inference_worker.py').read_text()
assert "self.auto_wire_checkbox=" not in ui, "Conflicting global wire toggle remains"
assert "self.current_auto_wire_cleanup = True" in ui
assert 'self.worker.auto_wire_cleanup = getattr(self, "current_auto_wire_cleanup", True)' in base
assert "'auto_wire_cleanup': self.auto_wire_cleanup" in ipc
assert "'auto_wire_cleanup'," in worker
assert "'fine_edge_matting', 'wire_policy_overrides')" in worker
assert 'result, removed_pixels = remove_loose_wires(result, mode=policy)' in base
assert 'self.current_wire_policy_overrides = dict(self.wire_policy_overrides)' in ui
assert "'wire_policy_overrides': scoped_policies" in ipc
assert "if source_path not in exact_inputs:" in ipc
assert "if policy not in POLICIES:" in ipc
assert "self.worker.wire_policy_overrides = dict(" in base
assert "def retry_failed(self):" in base
assert "sorted(self.errors)" in base
assert "self.cable_context.addItems([" in ui
for label in ('Auto Context', 'Remove Stray/Background Wires',
              'Keep Attached/Adapter Cables', 'Keep All Cables'):
    assert label in ui, label
assert "self.wire_policy_overrides.pop(path, None)" in ui
assert "self.wire_policy_overrides.pop(source, None)" in ui
assert "def batch_finished(self):" in ui
assert "Apply Wire Cleanup (paint mask first)" in ui
print('PASS four UI modes -> exact-input IPC snapshot -> isolated inference; retry state and manual tool preserved')
