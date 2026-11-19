"""Run the Docker dependency rewrite against the real project manifest."""

import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class DockerDependencyOverrideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dockerfile = (ROOT / "Dockerfile").read_text()
        cls.script = dockerfile.split("RUN python - <<'PY'\n", 1)[1].split("\nPY\n", 1)[
            0
        ]
        cls.project = (ROOT / "backend/pyproject.toml").read_text()

    def rewrite(self, project):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "pyproject.toml"
            manifest.write_text(project)
            result = subprocess.run(
                [sys.executable, "-I", "-c", self.script],
                cwd=directory,
                capture_output=True,
                text=True,
            )
            return result, tomllib.loads(manifest.read_text())

    def test_rewrite_preserves_declared_dm_driver_and_security_constraints(self):
        result, rewritten = self.rewrite(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        original = tomllib.loads(self.project)
        dm_requirement = next(
            dependency
            for dependency in original["project"]["dependencies"]
            if dependency.startswith("dmpython==")
        )
        dependencies = rewritten["project"]["dependencies"]
        self.assertIn(dm_requirement, dependencies)
        self.assertIn("psycopg[c]<4.0.0,>=3.1.13", dependencies)
        self.assertIn("psycopg2 (>=2.9.12,<3.0.0)", dependencies)
        self.assertIn("elasticsearch[requests] (>=7.17.13,<8.0)", dependencies)
        self.assertEqual(
            rewritten["tool"]["uv"]["constraint-dependencies"],
            ["idna>=3.7", "setuptools>=78.1.1", "urllib3>=2.2.2,<3", "pymssql==2.4.6"],
        )

    def test_dm_version_change_does_not_require_a_dockerfile_override(self):
        requirement = next(
            dependency
            for dependency in tomllib.loads(self.project)["project"]["dependencies"]
            if dependency.startswith("dmpython==")
        )
        future_requirement = "dmpython==2.6.2; platform_system != 'Darwin'"
        result, rewritten = self.rewrite(
            self.project.replace(requirement, future_requirement)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(future_requirement, rewritten["project"]["dependencies"])

    def test_other_dependency_rewrite_guards_still_reject_missing_inputs(self):
        project = self.project.replace(
            "psycopg[binary]<4.0.0,>=3.1.13", "psycopg>=3.1.13"
        )
        result, _ = self.rewrite(project)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AssertionError: psycopg[binary]", result.stderr)


if __name__ == "__main__":
    unittest.main()
