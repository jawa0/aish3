# (C) 2023 by Jabavu Adams. All Rights Reserved.

APPNAME = aish3

macos:
	@echo "Generating executable for $(APPNAME)..."
	pyinstaller --onefile $(APPNAME).py
	@echo "Modifying spec file..."
	sed -i '' 's|pathex=\[\]|pathex=\["'$(shell pwd)'"\]|g' $(APPNAME).spec
	@echo "Rebuilding with modified spec file..."
	pyinstaller $(APPNAME).spec

tests:
	@echo "Running tests..."
	python test/test_$(APPNAME).py

clean:
	@echo "Cleaning up..."
	rm -rf dist/ build/ $(APPNAME).spec
