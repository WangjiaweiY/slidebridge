# Plugins

SlideBridge Core exposes a public reader interface and registry. The public core includes only public open-source reader wrappers and a normal image reader.

Private readers should be implemented in separately licensed private packages.

Minimal fake reader example:

```python
from slidebridge.core.registry import register_reader


class FakeReader:
    name = "fake"
    priority = 1

    def can_open(self, path):
        return False

    def open(self, path):
        raise RuntimeError("FakeReader is only an example.")


register_reader(FakeReader())
```

The reader object should implement the `SlideReader` protocol and return a `Slide` object with normalized metadata and `read_region` behavior.

