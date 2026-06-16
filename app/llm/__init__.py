"""Real large-language-model integration.

Everything in this package is only imported when ``settings.enable_real_ai`` is
true. Heavy third-party dependencies (langchain, openai, pypdf, ...) are
imported lazily inside functions so the mock backend and the test suite keep
running without them installed.
"""
