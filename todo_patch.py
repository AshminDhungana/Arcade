import re

with open(r"E:\Ongoing Projects\Arcade\docs\TODO.md", encoding="utf-8") as f:
    content = f.read()

# Find the section using regex to match from "### Epic 8.1" to "#### Feature 8.1.2"
pattern = r"(### Epic 8\.1: Backend Testing \(ENG-A\).*?#### Feature 8\.1\.1: Integration Test Suite .*?All 23 Acceptance Criteria.*?)(- \[ \] \*\*Task: Write integration tests for all SRS acceptance criteria\*\* \(`backend/tests/test_acceptance\.py`\).*?)(#### Feature 8\.1\.2: Load and Performance Tests)"

match = re.search(pattern, content, re.DOTALL)
if match:
    print("Found match!")
    before = match.group(1)
    middle = match.group(2)
    after = match.group(3)
    print(f"Before: {before[:100]}...")
    print(f"Middle length: {len(middle)}")
    print(f"After: {after[:100]}...")
else:
    print("Pattern not found, trying simpler approach...")
    # Try to find the section boundaries
    idx1 = content.find("### Epic 8.1: Backend Testing (ENG-A)")
    idx2 = content.find("#### Feature 8.1.2: Load and Performance Tests")
    if idx1 >= 0 and idx2 >= 0:
        print(f"Found Epic 8.1 at {idx1}, Feature 8.1.2 at {idx2}")
        section = content[idx1:idx2]
        # Find the Feature 8.1.1 section within
        idx_f = section.find("Feature 8.1.1")
        if idx_f >= 0:
            print(f"Feature 8.1.1 at relative {idx_f}")
            print(section[idx_f : idx_f + 300])
