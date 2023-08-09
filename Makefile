# Copyright 2023 Jabavu W. Adams

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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
