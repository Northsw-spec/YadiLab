# Release evidence integrity

Release evidence must be derived from the exact bytes that are sealed. The
package-lock contract is checkpoint-bound:

`working source lock SHA == source checkpoint lock SHA == sealed inner checkpoint lock SHA`

The `verify_checkpoint_lock_binding.mjs` gate extracts `package-lock.json` from
the checkpoint ZIP and, when supplied, from the sealed artifact's inner source
checkpoint. It fails closed on missing files or any mismatch. Audits must run
after checkpoint creation and read back the checkpoint bytes; a hash copied
from an earlier workspace or checkpoint is invalid evidence.
