# RhoSocial ActiveRecord - AI Agent Instructions

See [CLAUDE.md](./CLAUDE.md) for full documentation.

## Quick Commands

```bash
# Run all tests with hybrid parallel/serial + coverage
export PYTHONPATH=src:tests LD_PRELOAD=.sqlite-custom/libsqlite3_custom.so
rm -f .coverage*
coverage run --parallel-mode -m pytest \
  tests/rhosocial/activerecord_test/feature/ tests/providers/ \
  --ignore=tests/rhosocial/activerecord_test/feature/basic/worker \
  --ignore=tests/rhosocial/activerecord_test/feature/query/worker \
  --ignore=tests/rhosocial/activerecord_test/feature/worker \
  -n auto --dist loadscope --tb=line \
  -k "not test_add_unique_constraint_enforces_uniqueness"
coverage run --parallel-mode -m pytest \
  tests/rhosocial/activerecord_test/feature/basic/worker \
  tests/rhosocial/activerecord_test/feature/query/worker \
  tests/rhosocial/activerecord_test/feature/worker \
  -n 0 --tb=line
coverage combine && coverage report

# Run specific feature tests
cd tests/providers && pytest test_ddl_*_compatibility.py -v
```
