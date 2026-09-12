#!/usr/bin/env python3
"""Check release build failures without running TeX or changing the checkout."""

import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest


REPO_DIR = Path(__file__).resolve().parent.parent
JOBS = (
    "uspace-test-pdflatex",
    "uspace-test-xelatex",
    "uspace-test-lualatex",
    "uspace",
)
SOURCES = (
    "uspace.sty",
    "README.md",
    "LICENSE",
    "uspace-test.tex",
    "uspace.tex",
    "uspace-ctanify.sh",
)
LATEXMK_STUB = r'''#!/bin/bash
set -eu
job=uspace
for argument in "$@"; do
    case "$argument" in
        -jobname=*) job=${argument#*=} ;;
    esac
done
# Keep the final job running long enough to detect an early exit on failure.
if [ "$job" = uspace ]; then
    sleep 0.2
fi
echo "BUILD LOG: $job"
touch "$job.finished"
case " $FAILED_BUILDS " in
    *" $job "*) exit 17 ;;
esac
printf 'fresh PDF for %s\n' "$job" >"$job.pdf"
'''


class PackagingTest(unittest.TestCase):
    def test_build_results(self):
        failure_sets = [(), *((job,) for job in JOBS), (JOBS[0], JOBS[-1])]
        for failures in failure_sets:
            for existing_archive in (False, True):
                with self.subTest(failures=failures, existing_archive=existing_archive):
                    self.check_build(failures, existing_archive)

    def check_build(self, failures, existing_archive):
        with tempfile.TemporaryDirectory(prefix="uspace-packaging-") as directory:
            work_dir = Path(directory)
            for source in SOURCES:
                shutil.copy2(REPO_DIR / source, work_dir / source)
            for job in JOBS:
                (work_dir / f"{job}.pdf").write_text("stale PDF\n")

            bin_dir = work_dir / "bin"
            bin_dir.mkdir()
            stub = bin_dir / "latexmk"
            stub.write_text(LATEXMK_STUB)
            stub.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = str(bin_dir) + os.pathsep + environment["PATH"]
            environment["FAILED_BUILDS"] = " ".join(failures)

            archive = work_dir / "uspace.tar.gz"
            previous_archive = b"previous release archive\n"
            if existing_archive:
                archive.write_bytes(previous_archive)

            result = subprocess.run(
                ["bash", "uspace-ctanify.sh"],
                cwd=work_dir,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if failures:
                self.assertNotEqual(result.returncode, 0, "failed build reported success")
            else:
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for job in JOBS:
                self.assertTrue((work_dir / f"{job}.finished").is_file(), job)
                self.assertIn(f"BUILD LOG: {job}\n", result.stdout)
                self.assertIn(f"{job}.tex.output:\n", result.stdout)

            if failures:
                if existing_archive:
                    self.assertEqual(archive.read_bytes(), previous_archive)
                else:
                    self.assertFalse(archive.exists(), "failed build created an archive")
            else:
                with tarfile.open(archive, "r:gz") as package:
                    members = {
                        member.name.removeprefix("./"): member
                        for member in package.getmembers()
                        if member.isfile()
                    }
                    expected = {f"uspace/{source}" for source in SOURCES}
                    expected.update(f"uspace/{job}.pdf" for job in JOBS)
                    self.assertEqual(set(members), expected)
                    for job in JOBS:
                        with package.extractfile(members[f"uspace/{job}.pdf"]) as pdf:
                            self.assertEqual(pdf.read(), f"fresh PDF for {job}\n".encode())


if __name__ == "__main__":
    unittest.main()
