.PHONY: verify health status bundle backup help smoke

verify:
	./scripts/verify_digest_policyblock.sh

health:
	./scripts/release_healthcheck.sh

status:
	git status
	git log --oneline --decorate -n 10

bundle:
	git bundle create bot_bridge-$$(date +%Y%m%d-%H%M%S).bundle --all --tags

backup:
	mkdir -p $$HOME/backups/bot_bridge
	cp -f ./*.bundle $$HOME/backups/bot_bridge/ 2>/dev/null || true
	ls -lh $$HOME/backups/bot_bridge/

smoke:
	$(MAKE) verify
	$(MAKE) health

help:
	@echo "Targets:"
	@echo "  make verify   - run digest policy_block verification"
	@echo "  make health   - run release healthcheck"
	@echo "  make smoke    - run verify + health"
	@echo "  make bundle   - create git bundle backup"
	@echo "  make backup   - copy bundles to ~/backups/bot_bridge"
