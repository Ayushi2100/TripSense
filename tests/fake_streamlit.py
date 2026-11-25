"""Minimal stand-in for streamlit, so every page can be executed without the package.
It returns each widget's default value. It checks that pages run; it does not check layout."""
import sys
import types


class _Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, name):
        if name.startswith('__'): raise AttributeError(name)
        return lambda *a, **k: FakeSt.calls.append(name)


class FakeSt(types.ModuleType):
    calls = []
    texts = []              # text passed to info/warning/caption/error/success
    overrides = {}          # {widget label: value}, lets a test pick e.g. the starting city

    def __init__(self):
        super().__init__("streamlit")
        self.sidebar = self
        self.session_state = {}

    def _log(self, name, *a, **k): FakeSt.calls.append(name)

    def __getattr__(self, name):
        if name.startswith("__"): raise AttributeError(name)
        def f(*a, **k):
            self._log(name)
            if name in ("info", "warning", "caption", "error", "success") and a:
                FakeSt.texts.append(str(a[0]))
            if name in ("columns",):
                n = a[0] if isinstance(a[0], int) else len(a[0])
                return [_Ctx() for _ in range(n)]
            if name == "tabs": return [_Ctx() for _ in a[0]]
            if name in ("expander", "container"): return _Ctx()
            if name == "button": return False
            if name == "cache_resource" or name == "cache_data":
                return (lambda fn: fn) if not a or not callable(a[0]) else a[0]
            return None
        return f

    def selectbox(self, label, options, index=0, **k):
        return FakeSt.overrides.get(label, list(options)[index])
    def radio(self, label, options, index=0, **k): return list(options)[index]
    def multiselect(self, label, options, default=None, **k): return list(default or [])
    def slider(self, label, min_value=0, max_value=1, value=0, step=None, **k): return value
    def number_input(self, label, min_value=None, max_value=None, value=0, step=None, **k): return value
    def checkbox(self, label, value=False, **k): return value


def install():
    fake = FakeSt()
    sys.modules["streamlit"] = fake
    return fake
