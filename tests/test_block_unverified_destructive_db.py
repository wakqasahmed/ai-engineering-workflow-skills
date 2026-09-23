import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = (
    ROOT
    / "skills"
    / "engineering"
    / "docker-db-guardrails"
    / "scripts"
    / "block-unverified-destructive-db.py"
)

ALLOW = 0
BLOCK = 2

# Cases verified as real bypasses during review of PR #200: each one was
# confirmed to exit 0 (allowed) against the pre-fix script.
BLOCKED_CASES = [
    # Invoking-tool detection: path-qualified binaries and nested shells.
    ("incident command, path-qualified artisan",
     "docker exec my-staging-app php /tmp/test-branch/artisan migrate:fresh --env=testing --force"),
    ("bash -c wrapper",
     'docker exec prod-app bash -c "php artisan migrate:fresh --force"'),
    ("sh -c wrapper",
     'docker exec prod-app sh -c "psql -d appdb -c \'DROP TABLE users\'"'),
    # Destructive-verb coverage.
    ("bare TRUNCATE without TABLE", 'docker exec prod-db psql -c "TRUNCATE users"'),
    ("artisan migrate:reset", "docker exec prod-app php artisan migrate:reset --force"),
    ("rails db:reset", "docker exec prod-app rails db:reset"),
    ("rails db:drop", "docker exec prod-app rails db:drop"),
    ("prisma migrate reset", "docker exec prod-app npx prisma migrate reset --force"),
    ("sequelize db:drop", "docker exec prod-app npx sequelize db:drop"),
    ("alembic downgrade base", "docker exec prod-app alembic downgrade base"),
    ("dropdb", "docker exec prod-db dropdb appdb"),
    ("mysqladmin drop", "docker exec prod-db mysqladmin drop appdb"),
    ("mongosh dropDatabase", 'docker exec prod-db mongosh --eval "db.dropDatabase()"'),
    ("redis-cli FLUSHALL", "docker exec prod-cache redis-cli FLUSHALL"),
    ("redis-cli FLUSHDB", "docker exec prod-cache redis-cli FLUSHDB"),
    # Explicit-dbname trust.
    ("artisan --database names a connection, not a database",
     "docker exec prod-app php artisan migrate:fresh --database=testing --force"),
    ("mysql trailing positional outranks -D",
     'docker exec prod-db mysql -D test proddb -e "DROP TABLE x"'),
    ("first safe name must not whitelist a chained command",
     'docker exec prod-db psql -d test -c "DROP TABLE x" '
     '&& docker exec prod-db psql -d appdb -c "DROP TABLE y"'),
    ("chained invocations with unresolvable targets",
     'php artisan migrate:fresh --force && psql -d test -c "DROP TABLE x"'),
    # Safe-name anchoring.
    ("contest_live is not a test database",
     'psql -d contest_live -c "DROP TABLE users"'),
    ("db_latest is not a test database", 'psql -d db_latest -c "DROP TABLE users"'),
    ("demographics is not a demo database",
     'psql -d demographics -c "DROP TABLE users"'),
    ("attestation is not a test database",
     'psql -d attestation -c "DROP TABLE users"'),
    # Prose-flag handling must not swallow a real argument.
    ("glued long-ish flag is still scanned",
     'psql -d proddb -message"DROP TABLE users"'),
    # Existing happy-path block cases.
    ("bare local migrate:fresh", "php artisan migrate:fresh --force"),
    ("unbalanced quotes", 'psql -d proddb -c "DROP TABLE users'),
]

ALLOWED_CASES = [
    ("non-destructive artisan command",
     "docker exec my-staging-app php artisan migrate:status"),
    ("prose mentioning destructive keywords",
     'gh issue create --body "discusses migrate:fresh risk"'),
    ("commit message about this hook",
     'git commit -m "guardrails: block artisan migrate:fresh against psql"'),
    ("explicit disposable database",
     'psql -d signalops_demo -c "DROP TABLE users"'),
    ("explicit testing database", 'psql --dbname=app_testing -c "TRUNCATE users"'),
    ("every explicit name disposable",
     'psql -d app_test -c "DROP TABLE x" && psql -d other_demo -c "DROP TABLE y"'),
]


def _clean_env(extra=None):
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("DB_DATABASE", "DB_NAME", "POSTGRES_DB", "MYSQL_DATABASE", "MARIADB_DATABASE")
    }
    if extra:
        env.update(extra)
    return env


def run_hook(payload, env=None):
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env or _clean_env(),
    )


def run_command(command, env=None):
    return run_hook(json.dumps({"tool_input": {"command": command}}), env=env)


class BlockUnverifiedDestructiveDbTest(unittest.TestCase):
    def test_blocks_known_bypasses(self):
        for name, command in BLOCKED_CASES:
            with self.subTest(name):
                result = run_command(command)
                self.assertEqual(result.returncode, BLOCK, f"{name}: {result.stderr}")
                self.assertIn("BLOCKED", result.stderr)

    def test_allows_safe_commands(self):
        for name, command in ALLOWED_CASES:
            with self.subTest(name):
                result = run_command(command)
                self.assertEqual(result.returncode, ALLOW, f"{name}: {result.stderr}")

    def test_blocks_malformed_payload(self):
        for name, payload in [
            ("not json", "{not json"),
            ("payload not an object", '"just a string"'),
            ("tool_input is a string", json.dumps({"tool_input": "migrate:fresh artisan"})),
            ("tool_input is a list", json.dumps({"tool_input": ["artisan", "migrate:fresh"]})),
            ("command is not a string", json.dumps({"tool_input": {"command": 42}})),
        ]:
            with self.subTest(name):
                result = run_hook(payload)
                self.assertEqual(result.returncode, BLOCK, result.stderr)
                self.assertIn("BLOCKED", result.stderr)

    def test_allows_empty_command(self):
        result = run_hook(json.dumps({"tool_input": {}}))
        self.assertEqual(result.returncode, ALLOW, result.stderr)

    def test_local_env_fallback(self):
        result = run_command(
            "php artisan migrate:fresh --force",
            env=_clean_env({"DB_DATABASE": "app_test"}),
        )
        self.assertEqual(result.returncode, ALLOW, result.stderr)

        result = run_command(
            "php artisan migrate:fresh --force",
            env=_clean_env({"DB_DATABASE": "db_latest"}),
        )
        self.assertEqual(result.returncode, BLOCK, result.stderr)


class ContainerResolutionTest(unittest.TestCase):
    """Container-env resolution, driven by a stub `docker` on PATH so the
    allow direction is testable without a real daemon."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin = Path(self.tmp.name)

    def _stub_docker(self, db_database):
        script = self.bin / "docker"
        script.write_text(
            "#!/bin/sh\n"
            f"echo 'DB_DATABASE={db_database}'\n"
        )
        script.chmod(0o755)
        return _clean_env({"PATH": f"{self.bin}:{os.environ.get('PATH', '')}"})

    def test_docker_exec_resolves_container_env(self):
        env = self._stub_docker("app_test")
        result = run_command(
            "docker exec my-app php artisan migrate:fresh --force", env=env
        )
        self.assertEqual(result.returncode, ALLOW, result.stderr)

        env = self._stub_docker("proddb")
        result = run_command(
            "docker exec my-app php artisan migrate:fresh --force", env=env
        )
        self.assertEqual(result.returncode, BLOCK, result.stderr)

    def test_compose_file_flag_still_resolves_container(self):
        """`docker compose -f <file> exec` must be recognized as a container
        invocation: falling through to the local-env branch becomes
        fail-open the moment this shell exports a safe-looking DB_DATABASE."""
        env = self._stub_docker("proddb")
        env["DB_DATABASE"] = "app_test"
        result = run_command(
            "docker compose -f docker-compose.yml exec app php artisan migrate:fresh --force",
            env=env,
        )
        self.assertEqual(result.returncode, BLOCK, result.stderr)
        self.assertIn('container "app"', result.stderr)


if __name__ == "__main__":
    unittest.main()
