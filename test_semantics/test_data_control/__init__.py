import os.path


def load_tests(loader, tests, pattern):
    this_dir = os.path.dirname(__file__)
    # Skip any file that doesn't start with 'test_'.
    # This lets us use other names for defining abstract base classes for TestCases.
    package_tests = loader.discover(start_dir=this_dir, pattern='test*.py')
    tests.addTests(package_tests)
    return tests
