import sys
import importlib.abc
import importlib.util
from unittest.mock import MagicMock
from contextlib import contextmanager


class MockModule(MagicMock):

    @classmethod
    def __getattr__(cls, name):
        return MockModule()

    def __call__(self, *args, **kwargs):
        return MockModule()


class DependencyMocker(importlib.abc.MetaPathFinder, importlib.abc.Loader):

    def __init__(self, allowed_prefixes):
        self.allowed_prefixes = allowed_prefixes

    def find_spec(self, fullname, path, target=None):
        if fullname.split(
                '.')[0] in self.allowed_prefixes or fullname in sys.modules:
            return None

        return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec):
        return MockModule()

    def exec_module(self, module):
        pass


@contextmanager
def safe_import_context():
    allowed = list(sys.modules.keys()) + ["openstrategy"]

    mocker = DependencyMocker(allowed_prefixes=allowed)
    sys.meta_path.insert(0, mocker)
    try:
        yield
    finally:
        sys.meta_path.remove(mocker)
