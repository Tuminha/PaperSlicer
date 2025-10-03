#!/bin/bash
# Quick test runner for PaperSlicer validation tests
#
# Usage:
#   ./scripts/run_validation_tests.sh              # Run priority tests only
#   ./scripts/run_validation_tests.sh --all        # Run all tests including slow
#   ./scripts/run_validation_tests.sh --report     # Generate validation report

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PaperSlicer Validation Test Runner${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Parse arguments
if [ "$1" == "--all" ]; then
    echo -e "${YELLOW}Running ALL validation tests (including slow)...${NC}\n"
    pytest tests/test_extraction_validation.py -v
    
elif [ "$1" == "--report" ]; then
    echo -e "${YELLOW}Generating detailed validation report...${NC}\n"
    python scripts/validate_extractions.py --priority-only -v
    
elif [ "$1" == "--full-report" ]; then
    echo -e "${YELLOW}Generating full validation report (all 38 PDFs)...${NC}\n"
    python scripts/validate_extractions.py -v
    
elif [ "$1" == "--metadata" ]; then
    echo -e "${YELLOW}Testing metadata extraction only...${NC}\n"
    pytest tests/test_extraction_validation.py::TestMetadataExtraction -v
    
elif [ "$1" == "--abstract" ]; then
    echo -e "${YELLOW}Testing abstract extraction only...${NC}\n"
    pytest tests/test_extraction_validation.py::TestAbstractExtraction -v
    
elif [ "$1" == "--sections" ]; then
    echo -e "${YELLOW}Testing section extraction only...${NC}\n"
    pytest tests/test_extraction_validation.py::TestSectionExtraction -v
    
elif [ "$1" == "--figures" ]; then
    echo -e "${YELLOW}Testing figure extraction only...${NC}\n"
    pytest tests/test_extraction_validation.py::TestFigureExtraction -v
    
elif [ "$1" == "--tables" ]; then
    echo -e "${YELLOW}Testing table extraction only...${NC}\n"
    pytest tests/test_extraction_validation.py::TestTableExtraction -v
    
elif [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: ./scripts/run_validation_tests.sh [option]"
    echo ""
    echo "Options:"
    echo "  (none)         Run priority tests only (default, fast)"
    echo "  --all          Run all tests including slow integration tests"
    echo "  --report       Generate validation report for priority PDFs"
    echo "  --full-report  Generate validation report for all 38 PDFs"
    echo "  --metadata     Test only metadata extraction"
    echo "  --abstract     Test only abstract extraction"
    echo "  --sections     Test only section extraction"
    echo "  --figures      Test only figure extraction"
    echo "  --tables       Test only table extraction"
    echo "  --help, -h     Show this help message"
    echo ""
    exit 0
    
else
    # Default: run priority tests only (fast)
    echo -e "${YELLOW}Running priority validation tests (3 BMC Oral Health PDFs)...${NC}\n"
    pytest tests/test_extraction_validation.py -v -m "not slow"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Validation tests completed!${NC}"
echo -e "${GREEN}========================================${NC}\n"

