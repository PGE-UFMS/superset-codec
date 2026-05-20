import json
import logging
import re

log = logging.getLogger(__name__)


def interpolate(text: str, variables: dict[str, str]) -> str:
    """Replace ``${VAR}`` placeholders with values from *variables*.

    Unknown variables are left as-is and a warning is logged.
    """
    def _replace(m: re.Match) -> str:
        name = m.group(1)
        if name not in variables:
            log.warning("Undefined interpolation variable: ${%s}", name)
            return m.group(0)
        return variables[name]

    return re.sub(r"\$\{([^}]+)\}", _replace, text)


def inverse_interpolate(data: dict, variables: dict[str, str]) -> dict:
    """Replace concrete values with ``${KEY}`` placeholders in all string fields.

    Sorted by value length (descending) to prevent partial replacements.
    Empty values are skipped.
    """
    text = json.dumps(data, ensure_ascii=False)
    for key, value in sorted(variables.items(), key=lambda x: len(x[1]), reverse=True):
        if value:
            text = text.replace(value, f"${{{key}}}")
    return json.loads(text)


def get_by_path(d: dict, path: str, default=None, sep="."):
    """Access nested dict values using dot-notation paths.

    Args:
        d:       Root dictionary.
        path:    Dot-separated key path, e.g. ``"foo.bar.baz"``.
        default: Returned when any key is missing or an intermediate level is
                 not a dict. Defaults to ``None``.
        sep:     Key separator. Defaults to ``"."``.
    """
    value = d
    for key in path.split(sep):
        if not isinstance(value, dict):
            return default
        value = value.get(key, default)
        if value is default:
            return default
    return value
