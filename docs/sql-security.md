# SQL security policy

SQL profiles use one of two access modes. `read_only` is the default for
inspection and does not permit `setup` or `cleanup`. Its database principal
must not have DML or DDL permissions.

`isolated_write` is available only for `local` and `staging`. It must declare
a `write_scope` (`dedicated_database`, `schema`, or `prefix`) and the operator
must pass `--allow-isolated-write` to `qa-harness run`. That flag records an
explicit intent; it is not the security boundary. The SQL principal must be
restricted by the database to the declared fixture scope. Never use
administrative roles, `db_owner`, or production credentials.

Every SQL profile declares the expected server, database, and effective
principal. The optional SQL Server preflight runs with `python -m
qa_harness.sqlserver` after installing `pip install .[sqlserver]`. It queries
the real connection for identity, server, database, version, and broad
database-level write permissions. The harness rejects a mismatch.

The preflight never loads dotenv files or writes a connection string to a
report. Staging and CI require `MSSQL_ENCRYPT=yes` and
`MSSQL_TRUST_SERVER_CERTIFICATE=false`. Local may explicitly use development
TLS settings. Production remains an invalid profile for this harness.

The database role is the primary defense. A manifest or a test script can be
reviewed incorrectly; it must not be able to obtain privileges that the SQL
principal does not have.

For local use, `tools/Invoke-QAProfile.ps1` loads an ignored profile only for
the child command and restores the process environment afterwards. It permits
`local` and `staging`; it always rejects `production`. Example:

```powershell
.\tools\Invoke-QAProfile.ps1 -Profile staging qa-harness run --repo <consumer> --profile staging-read
```

Add `--allow-isolated-write` only to a reviewed local or staging profile that
declares `isolated_write` and a safe fixture scope.
