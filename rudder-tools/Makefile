# List all single files that must be published here
PUBLISH := scripts/rudder-dev/rudder-dev scripts/rudder-setup/rudder-setup scripts/rudder-setup/ncf-setup scripts/technique-files

# This target will be called when we want to build everything
all: $(PUBLISH)

scripts/rudder-dev/rudder-dev:
	# Put commands to build rudder-dev single file here
	cd scripts/rudder-dev && $(MAKE) rudder-dev

scripts/rudder-setup/rudder-setup:
	cd scripts/rudder-setup && $(MAKE) rudder-setup

scripts/rudder-setup/ncf-setup:
	cd scripts/rudder-setup && $(MAKE) ncf-setup

clean:
	rm $(PUBLISH)

# This target will be called to get the list of files to publish
list:
	@echo $(PUBLISH)

.PHONY: all list
