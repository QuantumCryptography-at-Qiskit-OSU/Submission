# Local submission pipeline

Run before every upload, from this folder's parent:

    PYTHON=~/miniconda3/envs/qsim/bin/python python ci/package.py

It needs `pyyaml` in the same Python (`pip install pyyaml`, or a `--target` folder on PYTHONPATH).

- `--metrics-only` skips the answer hashes (faster).
- `--no-zip` checks only.
- `--require-docs` fails if `WRITEUP.md` or `README.md` is missing.
- `--out PATH` where to write the zip (default: `../Cryptographers.zip`).

It copies the challenge repo to a temp folder, runs `tools/check_submission.py` there, requires every tier to hash-match with a circuit run and metrics, zips this folder as `Cryptographers/` (without caches, `.git`, or `ci/`), then unzips the zip into another fresh copy and checks again. Takes about 40 seconds.

Not run on GitHub on purpose: the challenge rules say not to push solutions anywhere public.
