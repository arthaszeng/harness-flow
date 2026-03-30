# Evaluator Calibration Examples

The following are reference cases for each scoring level to help the Evaluator maintain consistent scoring standards.

## completeness (Feature Completeness)

### Score 5 Example
Contract requires CRUD API + unit tests + documentation. Builder completed everything and added input validation and error handling.

### Score 3 Example
Contract requires CRUD API + tests. Builder completed CR endpoints and some tests, but UD endpoints are missing.

### Score 1 Example
Contract requires a complete feature module. Builder only created an empty skeleton file.

## quality (Code Quality)

### Score 5 Example
Code follows project conventions, consistent naming, no duplicate logic, thorough error handling, complete type annotations.

### Score 3 Example
Code works but has magic numbers, duplicate error handling patterns, and some missing type annotations.

### Score 1 Example
Spaghetti code, single function over 200 lines, no error handling, inconsistent naming.

## regression (Regression Safety)

### Score 5 Example
All 50 existing tests pass, 15 new tests added covering all edge cases.

### Score 3 Example
Existing tests pass, but new tests only cover the happy path.

### Score 1 Example
3 existing tests fail due to interface changes, not fixed.

## design (Design Quality)

### Score 5 Example
New module perfectly follows the project's layered architecture, correct dependency direction, uses project-defined shared contracts.

### Score 3 Example
Feature works correctly but skips the architecture middle layer, directly accessing the lower layer.

### Score 1 Example
Directly imports FastAPI in core/ layer, violating core domain isolation principles.
